"""Synthesize real speech per chapter and mux it without retiming video frames."""
import asyncio
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import wave

import numpy as np

VERSION='chapter-narration-v1'
RATE=24000
VOICES={'en-US':'en-US-AriaNeural','zh-CN':'zh-CN-XiaoxiaoNeural'}


def ffmpeg():
    executable=shutil.which('ffmpeg') or str(Path(sys.executable).parent/'ffmpeg')
    return executable


def pcm(path):
    data=subprocess.run([ffmpeg(),'-v','error','-i',str(path),'-vn','-ac','1','-ar',str(RATE),
                         '-f','s16le','pipe:1'],capture_output=True,check=True,timeout=120).stdout
    return np.frombuffer(data,dtype='<i2').copy()


async def synthesize(text,voice,path):
    import edge_tts
    await asyncio.wait_for(edge_tts.Communicate(text,voice,rate='+0%').save(str(path)),90)


def fit_status(samples, slot_seconds):
    seconds=len(samples)/RATE
    if not samples.size or np.sqrt(np.mean((samples.astype(float)/32768)**2))<.003:
        return 'silent'
    if seconds>slot_seconds-.3:return 'too_long'
    if seconds<max(slot_seconds*.60, slot_seconds-4):return 'too_short'
    return 'fits'


def fit_draft_speech(samples, slot_seconds):
    """Preserve all speech; allow at most 35% tempo increase for small overruns."""
    seconds = len(samples)/RATE
    factor = max(1., seconds/max(.1, slot_seconds-.4))
    if factor > 1.35:
        raise ValueError('speech overrun exceeds draft tempo allowance')
    if factor == 1:
        return samples, factor
    data = subprocess.run([ffmpeg(), '-v', 'error', '-f', 's16le', '-ar', str(RATE), '-ac', '1',
        '-i', 'pipe:0', '-af', f'atempo={factor:.8f}', '-f', 's16le', 'pipe:1'],
        input=samples.tobytes(), capture_output=True, check=True, timeout=120).stdout
    fitted = np.frombuffer(data, dtype='<i2').copy()
    if len(fitted)/RATE > slot_seconds-.2:
        raise ValueError('tempo-adjusted speech still crosses chapter boundary')
    return fitted, factor


def repair_text(api,chapter,measured,status,language):
    response,_=api('Rewrite ONLY the spoken narration of this teaching chapter. Return JSON {"narration":string}. '
        'Preserve the current task, quantities, answer, mathematical reasoning and the chapter visual evidence. '
        'Do not invent facts, change the question or add unrelated material. Use genuine explanation, not repetitions. '
        'The speech must naturally occupy about 65..90 percent of the chapter at normal speaking speed, '
        'ending no more than four seconds before the chapter boundary. Explain each visible reasoning step; '
        'never add repeated filler to fill time. '
        f'Language: {language}. Previous speech measured {measured:.2f} seconds and was {status}. '
        f'The chapter lasts {chapter["end_s"]-chapter["start_s"]:.2f} seconds. '
        f'For English, use at most {max(8,int((chapter["end_s"]-chapter["start_s"])*2.2))} words; express the key reason concisely. '
        'Do not include stage directions or SSML.\nCHAPTER:\n'+json.dumps(chapter,ensure_ascii=False),max_tokens=1500)
    text=response.choices[0].message.content.strip()
    if text.startswith('```'):text=text.split('\n',1)[1].rsplit('```',1)[0]
    value=json.loads(text).get('narration')
    if not isinstance(value,str) or not value.strip():raise ValueError('narration repair produced no speech')
    return value


def srt_time(seconds):
    milliseconds=round(seconds*1000)
    return f'{milliseconds//3600000:02}:{milliseconds//60000%60:02}:{milliseconds//1000%60:02},{milliseconds%1000:03}'


def attach(video,contract,output,api=None):
    """Fail closed on absent, truncated, overlong or largely empty chapter speech."""
    from generation.lesson_spec import validate_timeline
    chapters=contract.get('teaching_timeline',[])
    validate_timeline({'teaching_timeline':chapters},contract)
    language=contract['task'].get('narration_language','en-US')
    if language not in VOICES:raise ValueError('unsupported narration language')
    voice=VOICES[language];output=Path(output);output.mkdir(parents=True,exist_ok=True)
    duration=contract['duration_seconds']
    draft = contract.get('generation_profile') == 'draft'
    delivery_warnings = []
    mixed=np.zeros(round(duration*RATE),dtype='<i2');records=[]
    try:
        for index,chapter in enumerate(chapters):
            text=chapter.get('narration','').strip()
            if not text:raise ValueError('chapter is missing spoken explanation')
            slot=chapter['end_s']-chapter['start_s']
            raw=output/f'chapter_{index:03}.mp3'
            tempo = 1.
            for attempt in range(3 if draft else 2):
                asyncio.run(synthesize(text,voice,raw))
                samples=pcm(raw);status=fit_status(samples,slot)
                if status=='fits':break
                if draft and status == 'too_long' and len(samples)/RATE <= (slot-.4)*1.35:
                    samples, tempo = fit_draft_speech(samples, slot)
                    delivery_warnings.append(f'{chapter["id"]}: speech tempo adjusted by {tempo:.3f}x')
                    break
                if attempt==(2 if draft else 1) or api is None:raise ValueError(f'chapter {chapter["id"]} speech {status}: {len(samples)/RATE:.2f}s for {slot}s')
                text=repair_text(api,{**chapter,'narration':text},len(samples)/RATE,status,language)
            start=round((chapter['start_s']+.15)*RATE);end=start+len(samples)
            if end>round(chapter['end_s']*RATE) or end>len(mixed):raise ValueError('speech crosses its chapter boundary')
            mixed[start:end]=samples
            records.append({'chapter_id':chapter['id'],'start_s':start/RATE,'end_s':end/RATE,'text':text,
                            'voice':voice,'synthesis_attempt':attempt+1,'tempo_factor':tempo,
                            'audio_sha256':hashlib.sha256(raw.read_bytes()).hexdigest()})
        speech_seconds=sum(r['end_s']-r['start_s'] for r in records)
        if speech_seconds/duration<.60:
            raise ValueError('insufficient real narration coverage')
        music=contract['task'].get('background_music_path')
        if music:
            music=Path(music)
            if not music.is_file():raise ValueError('optional background music asset is missing')
            bed=pcm(music)
            if not bed.size:raise ValueError('background music asset is empty')
            bed=np.resize(bed,len(mixed)).astype(float)*.025
            combined=mixed.astype(float)+bed
            combined*=min(1,32000/max(1,float(np.abs(combined).max())))
            mixed=combined.astype('<i2')
        wav=output/'narration.wav'
        with wave.open(str(wav),'wb') as handle:
            handle.setnchannels(1);handle.setsampwidth(2);handle.setframerate(RATE);handle.writeframes(mixed.tobytes())
        subtitles=output/'narration.srt'
        subtitles.write_text('\n\n'.join(f'{i}\n{srt_time(r["start_s"])} --> {srt_time(r["end_s"])}\n{r["text"]}' for i,r in enumerate(records,1))+'\n')
        target=output/'narrated.mp4'
        subprocess.run([ffmpeg(),'-v','error','-y','-i',str(video),'-i',str(wav),'-map','0:v:0','-map','1:a:0',
                        '-c:v','copy','-c:a','aac','-b:a','128k','-t',str(duration),str(target)],check=True,timeout=180)
        report={'version':VERSION,'valid':True,'language':language,'voice':voice,'speech_seconds':speech_seconds,
                'generation_profile':contract.get('generation_profile','strict'),'delivery_warnings':delivery_warnings,
                'speech_coverage':speech_seconds/duration,'chapters':records,'subtitles':str(subtitles),
                'video':str(target),'background_music':bool(music),'music_gain':.025 if music else 0,'video_stream_copied':True,
                'meaning':'synthesis and timing checks; semantic audio review is separate'}
    except Exception as exc:
        report={'version':VERSION,'valid':False,'chapters':records,'error':f'{type(exc).__name__}: {exc}'}
        (output/'narration.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
        raise
    (output/'narration.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    return target,report
