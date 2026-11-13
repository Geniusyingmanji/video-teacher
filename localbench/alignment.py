"""Evaluate speech against contemporaneous frames rather than a bag of video content."""
from __future__ import annotations

import json

from .common import write_json
from .evidence import image_content
from .strict_anchors import STRICT_INSTRUCTIONS
from .rubric import DIMENSIONS, validate_scores, ANCHORS
from .speech import narration_absent


def speech_windows(audio):
    windows=[]
    for record in audio:
        if not record.get('timing_valid'):continue
        for utterance in record.get('utterances',[]):
            words=utterance.get('words',[])
            groups=[];current=[]
            for word in words:
                if not 0<=word['start_s']<=word['end_s']<=record['end_s']-record['start_s']+.1:
                    continue
                if current and (word['start_s']-current[-1]['end_s']>.7 or word['end_s']-current[0]['start_s']>6):
                    groups.append(current);current=[]
                current.append(word)
                if word['word'].strip().endswith(('.', '?', '!')):
                    groups.append(current);current=[]
            if current:groups.append(current)
            if not groups and utterance.get('text'):
                groups=[[{'word':utterance['text'],'start_s':utterance['start_s'],'end_s':utterance['end_s']}]]
            for group in groups:
                text=' '.join(w['word'].strip() for w in group).strip()
                if len(text.split())<4:continue
                window={'audio_id':record['id'],'text':text,
                                'start_s':record['start_s']+group[0]['start_s'],
                                'end_s':record['start_s']+group[-1]['end_s']}
                if record.get('transcript_guard'):
                    window['transcript_uncertainties']=[w['uncertainty_id'] for w in group if w.get('uncertainty_id')]
                    window['timing_note']='ASR intervals; corroborated replacements have approximate span timing.'
                windows.append(window)
    return windows


def make_probes(packet,audio,limit=8):
    windows=speech_windows(audio)
    if len(windows)>limit:
        windows=[windows[round(i*(len(windows)-1)/(limit-1))] for i in range(limit)]
    probes=[]
    for i,window in enumerate(windows):
        start,end=window['start_s'],window['end_s']
        # Use only frames in/near this utterance, not semantically related frames elsewhere.
        candidates=[f for f in packet['frames'] if start-.75<=f['time_s']<=end+.75]
        if not candidates:
            nearest=min(packet['frames'],key=lambda f:abs(f['time_s']-(start+end)/2))
            if abs(nearest['time_s']-(start+end)/2)>1.75:continue
            candidates=[nearest]
        selected=[]
        for t in (start,(start+end)/2,end):
            frame=min(candidates,key=lambda f:abs(f['time_s']-t))
            if frame not in selected:selected.append(frame)
        probes.append({'id':f'P{i:02d}',**window,'frames':selected,
                       'allowed_ids':[window['audio_id']]+[f['id'] for f in selected]})
    return probes


def assess_alignment(client,packet,audio,case_id,out):
    keys=DIMENSIONS['crossmodal_alignment']['criteria']
    if audio and all(narration_absent(a) for a in audio):
        return assess_absent_speech_alignment(client,packet,audio,case_id,out)
    probes=make_probes(packet,audio)
    write_json(out/'alignment_probes.json',probes)
    if not probes or any(not a.get('timing_valid') for a in audio):
        return {'score':None,'criteria':{k:{'score':None,'status':'unverified','evidence_ids':[],
                    'reason':'Insufficient valid timed speech evidence for local audio-frame matching.'} for k in keys}}
    content=[{'type':'text','text':'''Assess audio-visual alignment using only the time-paired probes below.
Each probe contains speech actually transcribed at its stated video time, followed ONLY by
frames near that speech. Judge each probe against its OWN frames. The same event appearing
elsewhere in the video does not establish synchrony. For example, an explanation of moving
an object while the current frame shows an unrelated setup or conclusion is misaligned,
even when both the speech and visual are individually correct.
ASR timing is approximate; allow ordinary within-step timing, not multi-scene offsets.
Return JSON {observations:[{probe_id,verdict:"aligned"|"misaligned"|"unverified",
evidence_ids,spoken_claim,visible_content,reason}],
dimensions:{crossmodal_alignment:{criteria:{criterion_id:{status,score,evidence_ids,reason,
severity,limitation,high_score_evidence}}}}}.
Every probe needs one observation, citing only its own allowed IDs. Describe current visible
content literally before judging. Score 1 severe/absent, 2 major mismatch, 3 noticeable problems,
4 minor problems, 5 consistently aligned in the observed probes. Use null/unverified when
evidence is insufficient. Do not assess generic conceptual correctness or aesthetic quality.
Criterion status MUST be exactly "observed" or "unverified", never a quality label.
Return all six rubric criteria. Observed criteria need scores in integer levels 1,2,3,4,5; unverified criteria need score=null.
completion_claims covers substantive conclusions and recaps, not only literal words such as
"done" or "complete". Inspect the final available probes and compare the actual closing claim
with its visible outcome. If a required outcome is observably missing, record an omission.
Do not give free full credit for the absence of a completion phrase, and do not mark a visible
recap unverified merely because it lacks that phrase. Name an actual evidence gap for null.
Criterion evidence_ids may cite probe IDs P00 etc. or actual F/A IDs; observations themselves
must cite actual F/A IDs from their own probe. Each observed mismatch needs both audio and frame evidence.
Rubric: '''+ANCHORS+'\n'+STRICT_INSTRUCTIONS+'\n'+json.dumps(DIMENSIONS['crossmodal_alignment'],ensure_ascii=False)}]
    for probe in probes:
        content.append({'type':'text','text':json.dumps({k:v for k,v in probe.items() if k!='frames'},ensure_ascii=False)})
        for frame in probe['frames']:content.extend(image_content(frame))
    if any(a.get('transcript_guard') for a in audio):
        content.append({'type':'text','text':'''Transcription policy: an [uncertain speech] span is an
evidence gap, not a spoken error, omission or mismatched referent. Never infer its intended words
from the frame. Mark a probe unverified when the apparent discrepancy depends on that span;
known speech and genuine corroborated mistakes still count normally. Numeric typography is
normalized to spoken words. Replacement timing is approximate, not forced word alignment.'''})
    messages=[{'role':'user','content':content}]
    allowed={x for p in probes for x in p['allowed_ids']}
    by_id={p['id']:p for p in probes}
    for attempt in range(2):
        raw=client.chat(messages,purpose='time_paired_alignment:'+case_id,max_tokens=6500)
        write_json(out/f'raw_alignment_{attempt}.json',raw)
        try:
            observations=raw.get('observations') if isinstance(raw,dict) else None
            if not isinstance(observations,list) or len(observations)!=len(probes):raise ValueError('one observation required for every probe')
            seen=set()
            for row in observations:
                if row.get('probe_id') not in by_id or row['probe_id'] in seen:raise ValueError('invalid/duplicate probe id')
                seen.add(row['probe_id'])
                if row.get('verdict') not in {'aligned','misaligned','unverified'}:raise ValueError('invalid alignment verdict')
                ids=row.get('evidence_ids',[])
                if not ids or any(x not in by_id[row['probe_id']]['allowed_ids'] for x in ids):raise ValueError('probe cited a frame/audio from another time window')
                if row['verdict']!='unverified' and (not any(x.startswith('A') for x in ids) or not any(x.startswith('F') for x in ids)):
                    raise ValueError('observed alignment requires both audio and local frame citations')
                if not row.get('visible_content') or not row.get('reason'):raise ValueError('literal current-frame content and reason required')
            normalized=json.loads(json.dumps(raw))
            observed={r['probe_id']:r for r in observations}
            # Probe IDs are an evidence hierarchy, not invented frames. Expand
            # them only to the already validated observations' actual F/A IDs.
            criteria=normalized.get('dimensions',{}).get('crossmodal_alignment',{}).get('criteria',{})
            for item in criteria.values():
                citations=[]
                for id_ in item.get('evidence_ids',[]):
                    citations.extend(observed[id_]['evidence_ids'] if id_ in observed else [id_])
                item['evidence_ids']=list(dict.fromkeys(citations))
            result=validate_scores(normalized,allowed,['crossmodal_alignment'],strict=True)['crossmodal_alignment']
            result['observations']=observations;result['source']='actual_speech_paired_with_contemporaneous_frames'
            return result
        except ValueError as exc:
            if attempt:raise
            messages.extend([{'role':'assistant','content':json.dumps(raw,ensure_ascii=False)},
                             {'role':'user','content':'Fix schema/citations while preserving evidence-based judgments. Criterion status must be exactly observed or unverified, NOT a quality label. Observed score is one of 1,2,3,4,5; unverified score is null. Cite real F/A IDs in observations. Error: '+str(exc)}])


def assess_absent_speech_alignment(client,packet,audio,case_id,out):
    keys=DIMENSIONS['crossmodal_alignment']['criteria']
    content=[{'type':'text','text':"Final audio is verified to contain no spoken narration. Evaluate only text_visual_consistency from actual frames; the remaining speech-dependent criteria are observed omissions and must be 1. Return JSON {dimensions:{crossmodal_alignment:{criteria:{criterion_id:{status,score,evidence_ids,reason,severity,limitation,high_score_evidence}}}}}. Return all six criteria, with observed/unverified status and null for insufficient evidence. Cite actual frame IDs for text/diagram consistency, actual audio IDs for speech absence. "+ANCHORS+"\n"+STRICT_INSTRUCTIONS+"\nRubric: "+json.dumps(keys)+"\nAudio IDs: "+json.dumps([a['id'] for a in audio])}]
    for frame in packet['frames']:content.extend(image_content(frame))
    raw=client.chat([{'role':'user','content':content}],purpose='silent_video_alignment:'+case_id,max_tokens=3200)
    write_json(out/'raw_silent_alignment.json',raw)
    result=validate_scores(raw,{f['id'] for f in packet['frames']}|{a['id'] for a in audio},['crossmodal_alignment'],strict=True)['crossmodal_alignment']
    for key,row in result['criteria'].items():
        if key!='text_visual_consistency' and (row['score']!=1 or row['status']!='observed'):
            raise ValueError('verified missing narration must be recorded as an observed omission')
    result['source']='verified_absence_of_required_narration_and_actual_screen_pixels'
    return result
