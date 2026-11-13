"""Replace selected narration slots without moving or truncating later lessons."""
import hashlib
import json
from pathlib import Path
import wave

import imageio_ffmpeg
import numpy as np

from .common import write_json
from .pipeline import spoken_text
from .tts import command, resolve_tts, synthesize_speech

RATE = 24000


def read_pcm(path):
    with wave.open(str(path)) as f:
        if (f.getnchannels(), f.getsampwidth(), f.getframerate()) != (1, 2, RATE):
            raise ValueError('24kHz mono16 PCM required')
        return np.frombuffer(f.readframes(f.getnframes()), dtype='<i2').copy()


def splice(source, slots, replacements, *, pause_s=.2):
    result = source.copy()
    changed = np.zeros(len(source), dtype=bool)
    for scene, speech in replacements.items():
        start, end = slots[scene]
        if not 0 <= start < end <= len(source) or changed[start:end].any():
            raise ValueError('valid nonoverlapping sample slots required')
        if len(speech) + round(pause_s*RATE) > end-start:
            raise ValueError('speech exceeds fixed slot; do not truncate or shift other scenes')
        result[start:end] = 0
        result[start:start+len(speech)] = speech
        changed[start:end] = True
    if not np.array_equal(source[~changed], result[~changed]):
        raise ValueError('unmodified PCM samples changed')
    return result, {'unmodified_samples':int((~changed).sum()),
        'unmodified_pcm_sha256':hashlib.sha256(source[~changed].tobytes()).hexdigest(),
        'unchanged_outside_replacements':True}


def synthesize(plan, source_plan, source_video, scenes, out, *, tts=None):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    if [s['duration_s'] for s in plan['scenes']] != [s['duration_s'] for s in source_plan['scenes']]:
        raise ValueError('fixed speech requires exact source scene boundaries')
    for i, (a,b) in enumerate(zip(plan['scenes'],source_plan['scenes'])):
        if i not in scenes and a != b:
            raise ValueError('non-target scene changed')
    config=resolve_tts(tts)
    source_path=out/'source_decoded.wav'
    command([imageio_ffmpeg.get_ffmpeg_exe(),'-y','-loglevel','error','-i',str(source_video),
             '-vn','-ar',str(RATE),'-ac','1','-c:a','pcm_s16le',str(source_path)])
    source=read_pcm(source_path)
    slots={};boundary=0.
    for i,scene in enumerate(plan['scenes']):
        start=round(boundary*RATE);boundary+=scene['duration_s']
        slots[i]=(start,round(boundary*RATE))
    target=round(boundary*RATE)
    if len(source)<target:
        raise ValueError('source decoded audio shorter than fixed lesson')
    source=source[:target]
    replacements={};records=[]
    for i in scenes:
        scene=plan['scenes'][i]
        dest=out/f'scene_{i:02d}';dest.mkdir(exist_ok=True)
        text=dest/'narration.txt';text.write_text(spoken_text(scene))
        slot_samples=slots[i][1]-slots[i][0]
        attempts=[]
        for speed in (155,170,185,195):
            path=dest/f'speech_{speed}.wav'
            synthesize_speech(text,path,speed,config)
            speech=read_pcm(path)
            fits=len(speech)+round(.2*RATE)<=slot_samples
            attempts.append({'rate':speed,'samples':len(speech),'fits':fits,'path':str(path.resolve())})
            write_json(dest/'attempts.json',attempts)
            if fits:
                replacements[i]=speech
                records.append({'scene':i,'start_sample':slots[i][0],'end_sample':slots[i][1],
                    'rate':speed,'speech_s':len(speech)/RATE,'tail_s':(slot_samples-len(speech))/RATE})
                break
        else:
            raise ValueError(f'scene {i} narration cannot fit fixed slot at allowed rates')
    patched,receipt=splice(source,slots,replacements)
    final=out/'narration.wav'
    with wave.open(str(final),'wb') as f:
        f.setnchannels(1);f.setsampwidth(2);f.setframerate(RATE);f.writeframes(patched.tobytes())
    receipt.update(version='fixed-scene-pcm-v1',scenes=records,sample_rate=RATE,total_samples=target,
        final_pcm_sha256=hashlib.sha256(patched.tobytes()).hexdigest(),
        limitation='Unchanged source PCM before final AAC encoding; this does not assert bit-identical AAC or identical final decoded PCM.')
    write_json(out/'receipt.json',receipt)
    plan['timing_compilation']={'version':'fixed-scene-pcm-v1','scene_frames':[round(s['duration_s']*12) for s in plan['scenes']],
                               'edited_scenes':scenes,'speech_receipt':str((out/'receipt.json').resolve())}
    return final,receipt
