"""CPU ASR timestamps from encoded audio; no generation script is supplied."""
from __future__ import annotations

import hashlib
import json
import threading
import wave
from pathlib import Path

import numpy as np

from .common import ROOT, digest, write_json

_lock=threading.Lock()
_model=None
CONFIG={'model':'base.en','compute_type':'int8','beam_size':3,'language':'en','condition_on_previous_text':False,
        'evidence_version':'speech-presence-guard-v2',
        'vad':{'threshold':0.5,'min_speech_duration_ms':250,'min_silence_duration_ms':300,'speech_pad_ms':100}}


def read_pcm(path):
    with wave.open(str(path)) as wav:
        if (wav.getframerate(),wav.getnchannels(),wav.getsampwidth())!=(16000,1,2):
            raise ValueError('ASR requires the normalized 16 kHz mono PCM evidence WAV')
        samples=np.frombuffer(wav.readframes(wav.getnframes()),dtype='<i2')
    if not len(samples):raise ValueError('empty decoded audio data')
    peak=int(np.max(np.abs(samples.astype(np.int32))))
    return samples,{'peak_pcm':peak,'rms_pcm':float(np.sqrt(np.mean(samples.astype(np.float64)**2))),
                    'duration_s':len(samples)/16000,'digital_silence':peak<=1}


def transcribe(path):
    global _model
    path=Path(path)
    key=digest({'audio_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'config':CONFIG})
    cache=ROOT/'results/localbench/asr_cache'/f'{key}.json'
    with _lock:
        if cache.exists():return json.loads(cache.read_text())
        pcm,signal=read_pcm(path)
        if signal['digital_silence']:
            result={'transcript':'','utterances':[],'duration_s':signal['duration_s'],'signal':signal,
                    'config':CONFIG,'audio_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                    'source':'digitally_silent_final_audio_no_asr_inference'}
            write_json(cache,result)
            return result
        from faster_whisper import WhisperModel
        from faster_whisper.vad import get_speech_timestamps,VadOptions
        samples=pcm.astype(np.float32)/32768.0
        try:
            detected=get_speech_timestamps(samples,VadOptions(**CONFIG['vad']),sampling_rate=16000)
            speech_activity={'status':'observed','detector':'faster_whisper_silero_vad',
                             'segments':[{'start_s':d['start']/16000,'end_s':d['end']/16000} for d in detected],
                             'speech_duration_s':sum(d['end']-d['start'] for d in detected)/16000,
                             'config':CONFIG['vad']}
        except Exception as exc:
            speech_activity={'status':'unverified','error_type':type(exc).__name__}
        if speech_activity.get('status')=='observed' and not speech_activity['segments']:
            result={'transcript':'','utterances':[],'duration_s':signal['duration_s'],'signal':signal,
                    'speech_activity':speech_activity,'config':CONFIG,
                    'audio_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                    'source':'vad_no_speech_asr_skipped_requires_listener_crosscheck'}
            write_json(cache,result)
            return result
        if _model is None:
            _model=WhisperModel(CONFIG['model'],device='cpu',compute_type=CONFIG['compute_type'],
                                cpu_threads=4,download_root=str(ROOT/'.local-cache/asr'))
        # Evidence extractor guarantees 16 kHz mono PCM WAV. Decode directly to
        # avoid PyAV API differences across supported local Python versions.
        segments,info=_model.transcribe(samples,language='en',beam_size=3,
                                        condition_on_previous_text=False,word_timestamps=True)
        rows=[]
        for segment in segments:
            if not 0<=segment.start<=segment.end<=signal['duration_s']+.05:
                raise ValueError('ASR timestamp outside the observed audio duration')
            rows.append({'start_s':segment.start,'end_s':segment.end,'text':segment.text.strip(),
                         'words':[{'start_s':w.start,'end_s':w.end,'word':w.word,'probability':w.probability} for w in (segment.words or [])],
                         'avg_logprob':segment.avg_logprob,'no_speech_prob':segment.no_speech_prob})
        result={'transcript':' '.join(s['text'] for s in rows),'utterances':rows,'duration_s':info.duration,
                'config':CONFIG,'signal':signal,'speech_activity':speech_activity,
                'audio_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                'source':'local_asr_on_final_encoded_audio'}
        write_json(cache,result)
        return result
