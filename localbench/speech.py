"""Reconcile listened speech presence with independent waveform/VAD evidence."""
from __future__ import annotations


def narration_absent(record):
    return bool(record.get('digital_silence') or record.get('narration_presence',{}).get('status')=='observed_absent')


def reconcile(asr, listened):
    presence=listened.get('speech_presence')
    if presence not in {'present','absent','uncertain'}:
        raise ValueError('listener speech_presence must be present, absent or uncertain')
    vad=asr.get('speech_activity',{})
    no_activity=vad.get('status')=='observed' and not vad.get('segments')
    activity=vad.get('status')=='observed' and bool(vad.get('segments'))
    asr_text=(asr.get('transcript') or '').strip()
    listener_text=(listened.get('transcript') or '').strip()
    if presence=='absent' and no_activity and not listener_text and not asr_text:
        return {'status':'observed_absent','reason':'Actual-audio listener reports no speech and independent VAD detects no speech activity.',
                'transcript':'','utterances':[],'transcript_valid':True,'timing_valid':True,
                'source':'listener_and_vad_agree_no_speech'}
    if presence=='uncertain' or (presence=='absent' and (activity or asr_text or listener_text)) or (presence=='present' and no_activity):
        return {'status':'unverified','reason':'Speech-presence evidence is uncertain or the listener and local detector/transcriber disagree.',
                'transcript':None,'utterances':[],'transcript_valid':False,'timing_valid':False,
                'source':'speech_presence_conflict'}
    if presence=='present' and (asr_text or listener_text):
        timed=bool(asr_text and asr.get('utterances'))
        return {'status':'observed_present','reason':'Actual-audio listener reports speech; nonempty transcribed speech is available.',
                'transcript':asr_text or listener_text,'utterances':asr.get('utterances',[]) if timed else [],
                'transcript_valid':True,'timing_valid':timed,
                'source':'local_asr_with_listener' if asr_text else 'listener_transcript_without_local_timing'}
    return {'status':'unverified','reason':'Insufficient corroborated speech-presence evidence.',
            'transcript':None,'utterances':[],'transcript_valid':False,'timing_valid':False,
            'source':'speech_presence_not_established'}
