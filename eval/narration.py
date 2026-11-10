"""Actual-track ASR and evidence-backed audio/visual consistency review.

ASR is fallible and is not a human listening test. Never trust a planned script
as proof of the audio that was actually encoded in the submitted video.
"""
import json
from eval.evidence_prompt import prompt_json
import math
import os
import hashlib
from functools import lru_cache
from pathlib import Path

from eval.judges.gpt55 import chat
from eval.judges.structured_json import response_format,obj,array
from eval.instructional_video import _ask, ledger_for_judge

VERSION='spoken-teaching-v1'
CRITERIA=['speech_accuracy','explanatory_coverage','visual_alignment','speech_pacing']


@lru_cache(maxsize=1)
def asr_config():
    quality=os.environ.get('VIDEO_TEACHER_SCORING_POLICY') in ('quality-v12', 'quality-v13')
    default='small.en' if quality else 'base'
    local=Path(__file__).resolve().parents[2]/('models/faster-whisper-small.en' if quality else 'models/faster-whisper-base')
    name=os.environ.get('VIDEO_TEACHER_ASR_MODEL',str(local) if (local/'model.bin').is_file() else default)
    weight=Path(name)/'model.bin'
    digest=None
    if weight.is_file():
        h=hashlib.sha256()
        with weight.open('rb') as handle:
            for chunk in iter(lambda:handle.read(1024*1024),b''):h.update(chunk)
        digest=h.hexdigest()
    return {'model':name,'weight_sha256':digest,'device':'cpu','compute_type':'int8','version':VERSION}


def transcribe(path):
    from faster_whisper import WhisperModel
    model_name=asr_config()['model']
    model=WhisperModel(model_name,device='cpu',compute_type='int8',cpu_threads=4,num_workers=1)
    raw,info=model.transcribe(str(path),beam_size=3,vad_filter=True,word_timestamps=True)
    if not math.isfinite(info.language_probability) or info.language_probability<.5:
        raise ValueError('spoken language could not be identified confidently')
    segments=[{'id':index,'start_s':float(r.start),'end_s':float(r.end),'text':r.text.strip(),
               'avg_logprob':r.avg_logprob,'no_speech_prob':r.no_speech_prob,
               'words':[{'start_s':float(w.start),'end_s':float(w.end),'word':w.word,'probability':w.probability} for w in (r.words or [])]}
              for index,r in enumerate(raw) if r.text.strip()]
    if not segments:raise ValueError('no intelligible speech recognized in actual audio track')
    reliable=[r for r in segments if r['no_speech_prob']<.8 and r['avg_logprob']> -1.2]
    if len(reliable)<max(1,len(segments)*.8):raise ValueError('ASR confidence is insufficient to verify spoken content')
    return {'version':VERSION,'valid':True,'asr_model':model_name,'asr_device':'cpu',
            'language':info.language,'language_probability':info.language_probability,'segments':segments,
            'meaning':'recognized actual speech; ASR may misrecognize technical terms and pronunciation'}


def window_transcript(transcript,start,end):
    records=[]
    for segment in transcript.get('segments',[]):
        words=[w for w in segment.get('words',[]) if w['end_s']>start and w['start_s']<end]
        if words:
            records.append({'speech_segment_id':segment['id'],'start_s':words[0]['start_s'],
                            'end_s':words[-1]['end_s'],'text':''.join(w['word'] for w in words)})
        elif not segment.get('words') and segment['end_s']>start and segment['start_s']<end:
            records.append({**{k:segment[k] for k in ('start_s','end_s','text')},'speech_segment_id':segment['id'],'timing_precision':'coarse_ASR_segment'})
    return records


def review(case,transcript,ledger):
    from generation.task_requirements import requirements
    if transcript.get('valid') is not True:raise ValueError('actual speech transcript is unverified')
    language=case.get('narration_language','en-US').split('-')[0]
    if transcript['language']!=language:
        return {'version':VERSION,'valid':True,'passed':False,'score':0,'failures':['wrong_spoken_language']}
    speech=[{k:r[k] for k in ('id','start_s','end_s','text','avg_logprob')} for r in transcript['segments']]
    if not ledger:raise ValueError('audio/visual alignment requires inspected video windows')
    prompt=('Audit SPOKEN teaching against the actual ASR transcript and independently inspected video windows. '
        'This is an ASR proxy, not direct audio listening: do not claim verified pronunciation or voice quality. '
        'Check correct givens, numerical quantities, units, causal statements and final answers. '
        'The narration must EXPLAIN key relationships or operation reasons, not read labels or repeat the answer. '
        'Check that statements refer to the corresponding visible step at their actual times, and that they do not '
        'run substantially ahead of operations or contradict diagrams. Allow natural reading and inspection pauses. '
        'Missing crucial explanations, unresolved ASR ambiguity and visual/spoken contradiction prevent passing. '
        'Do not require unrelated syllabus content. Speech cannot replace required visible operations. '
        'Score each criterion 1..5 in half-point increments between explicit adjacent anchors: absent/wrong, weak, adequate/uncertain, strong, exceptional. '
        'Cite actual speech IDs and video-window IDs. Give concrete observations before scores. '
        'Do not trust intended narration scripts as proof of what was spoken. '
        'Do not aim for a predetermined high or low score. Every deduction needs a concrete rubric failure '
        'with cited actual speech and visual windows. Signal silence and word timing are diagnostic '
        'proxies; reading or reflection pauses are not automatically defects.\n'
        +prompt_json({'task_requirements':requirements(case),
                    'criteria':CRITERIA,'actual_speech':speech,'video_windows':ledger_for_judge(ledger),
                    'measured_pacing_evidence':case.get('delivery_pacing_evidence',{})}))
    quality=os.environ.get('VIDEO_TEACHER_SCORING_POLICY') in ('quality-v12', 'quality-v13')
    if quality:
        prompt += ('\nDo not target low or high scores. If a near-homophone technical term may be an ASR error, '
            'record the ambiguity in uncertainties with its speech IDs. Do not assert that the speaker made '
            'a factual mistake based on that ambiguous recognition. Use an empty uncertainty array when none exists.')
    schema=response_format('spoken_teaching',{'criteria':array(obj({
        'id':{'type':'string','enum':CRITERIA},'finding':{'type':'string','minLength':1,'maxLength':480},
        'speech_ids':array({'type':'integer','enum':[r['id'] for r in speech]}),
        'window_ids':array({'type':'integer','enum':[r['id'] for r in ledger]}),
        'score':{'type':'number','enum':[1,1.5,2,2.5,3,3.5,4,4.5,5]}}),minItems=4,maxItems=4),
        'summary':{'type':'string','minLength':1,'maxLength':700},
        **({'uncertainties':array(obj({'speech_ids':array({'type':'integer','enum':[r['id'] for r in speech]},minItems=1),
              'finding':{'type':'string','minLength':1,'maxLength':480}}))} if quality else {})})
    def validate(raw):
        rows=raw.get('criteria',[])
        if len(rows)!=4 or {r.get('id') for r in rows}!=set(CRITERIA):raise ValueError('all four spoken-teaching criteria required')
        for row in rows:
            if type(row.get('score')) not in (int,float) or not 1<=row['score']<=5 or row['score']*2 != round(row['score']*2):raise ValueError('invalid spoken-teaching score')
            for field,allowed in (('speech_ids',{r['id'] for r in speech}),('window_ids',{r['id'] for r in ledger})):
                ids=row.get(field)
                if not isinstance(ids,list) or any(type(i) is not int or i not in allowed for i in ids):raise ValueError('invalid spoken evidence citation')
                if not ids:raise ValueError('every spoken rating, including deductions, needs actual speech and visual evidence')
            if not isinstance(row.get('finding'),str) or not row['finding'].strip():raise ValueError('spoken review finding missing')
        return raw
    raw=_ask([{'role':'user','content':prompt}],schema,validate,tokens=2500)
    if quality and raw.get('uncertainties'):
        return {**raw,'version':VERSION,'valid':False,'passed':False,'score':None,
                'failures':['spoken_evidence_uncertain'],'interpretation':'ASR disagreement requires independent verification, not a zero score'}
    weakest=min(r['score'] for r in raw['criteria'])
    score=(weakest-1)*25
    return {**raw,'version':VERSION,'valid':True,'passed':weakest>=4,'score':score,
            'failures':[] if weakest>=4 else ['spoken_explanation_or_alignment_weak'],
            'interpretation':'ASR_and_inspected_visual_evidence_not_direct_listening'}


def apply(scoring,review):
    result={**scoring,'pre_audio_score':scoring.get('score'),'spoken_teaching_score':review.get('score')}
    value=review.get('score')
    if review.get('valid') is not True or type(value) not in (int,float) or not math.isfinite(value) or not 0<=value<=100:
        return {**result,'valid':False,'strict_pass':False,'score':None,
                'errors':list(result.get('errors',[]))+['spoken_teaching_unverified']}
    if result.get('valid'):result['score']=min(result['score'],value)
    result['strict_pass']=bool(result.get('strict_pass') and review.get('passed'))
    result['gates']=list(result.get('gates',[]))+review.get('failures',[])
    return result
