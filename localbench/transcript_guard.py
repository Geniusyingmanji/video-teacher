"""Experimental audio-only corroboration of lexical transcript disagreements.

No task, reference, scene plan, or video frame is given to the blind listener.
Original transcripts and all decisions remain in the run directory.
"""
from __future__ import annotations

import copy
import difflib
import math
import re
import subprocess
import wave
from numbers import Real
from pathlib import Path

import imageio_ffmpeg

from .asr import read_pcm,transcribe
from .common import write_json
from .evidence import audio_content
from .provenance import file_hash
from .speech import narration_absent

VERSION='transcript-guard-dev3'
SYSTEM='''Transcribe only the actual spoken English in this audio excerpt, verbatim.
You are not given the topic, the intended script, a diagram, or candidate words. Preserve
spoken factual mistakes and unusual words; do not rewrite them into a more plausible lesson.
Do not complete words or sentences that are cut off. Do not infer words from silence/noise.
Return JSON {speech_presence:"present"|"absent"|"uncertain",transcript:"actual words"}.
If a word is unintelligible, write [unintelligible], not a guessed word. No timestamps.'''


def integer_words(n):
    ones='zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen'.split()
    tens='zero ten twenty thirty forty fifty sixty seventy eighty ninety'.split()
    if n<20:return [ones[n]]
    if n<100:return [tens[n//10]]+(integer_words(n%10) if n%10 else [])
    if n<1000:return [ones[n//100],'hundred']+(integer_words(n%100) if n%100 else [])
    for value,name in ((10**9,'billion'),(10**6,'million'),(1000,'thousand')):
        if n>=value:return integer_words(n//value)+[name]+(integer_words(n%value) if n%value else [])
    raise AssertionError('unreachable')


def tokens(text):
    """Lexical comparison only: punctuation/case and numeric typography are not audio errors."""
    result=[]
    contractions={"don't":['do','not'],"doesn't":['does','not'],"isn't":['is','not'],
                  "can't":['can','not'],"cannot":['can','not'],"it's":['it','is'],
                  "they're":['they','are'],"we're":['we','are']}
    aliases={'ml':'milliliters','millilitres':'milliliters','litres':'liters','litre':'liter'}
    symbols={'+':['plus'],'-':['minus'],'−':['minus'],'/':['divided','by'],
             '*':['times'],'×':['times'],'=':['equals'],'%':['percent'],'°':['degrees']}
    pattern=r"[a-z]+(?:'[a-z]+)?|[-+−]?\d+(?:,\d{3})*(?:\.\d+)?|[×*/%=°]|(?<![a-z])[-+−](?![a-z])"
    for word in re.findall(pattern,text.lower().replace('’',"'")):
        if word in symbols:result.extend(symbols[word]);continue
        if word.lstrip('-+−')[0].isdigit():
            if word[0] in '-+−':result.extend(symbols[word[0]]);word=word[1:]
            value=word.replace(',','');whole,_,fraction=value.partition('.')
            if int(whole)<10**12:
                result.extend(integer_words(int(whole)))
                if fraction:result.extend(['point',*(integer_words(int(x))[0] for x in fraction)])
            else:result.append(value)
        else:result.extend(contractions.get(word,[aliases.get(word,word.replace("'",''))]))
    return result


def timed_tokens(asr):
    records=[]
    duration=asr['duration_s']
    for utterance in asr.get('utterances',[]):
        words=utterance.get('words',[])
        if not words and utterance.get('text'):raise ValueError('continuous ASR needs actual word timestamps')
        for word in words:
            start,end=word['start_s'],word['end_s']
            if any(isinstance(t,bool) or not isinstance(t,Real) or not math.isfinite(t) for t in (start,end)) or not 0<=start<=end<=duration+.05:
                raise ValueError('invalid continuous ASR word timing')
            start,end=float(start),float(end)
            for token in tokens(word['word']):
                records.append({'word':token,'start_s':start,'end_s':end,
                    'probability':word.get('probability'),'time_source':'continuous_asr_word_interval'})
    return records


def differences(words,listener_text,chunk_start,chunk_end):
    a=[w['word'] for w in words];b=tokens(listener_text)
    opcodes=difflib.SequenceMatcher(None,a,b,autojunk=False).get_opcodes()
    output=[]
    for index,(kind,i,j,k,l) in enumerate(opcodes):
        if kind=='equal':continue
        previous=opcodes[index-1] if index else None
        following=opcodes[index+1] if index+1<len(opcodes) else None
        left=a[max(i-3,previous[1]):i] if previous and previous[0]=='equal' else []
        right=a[j:min(j+3,following[2])] if following and following[0]=='equal' else []
        start=words[i]['start_s'] if i<len(words) else words[-1]['end_s'] if words else chunk_start
        end=words[j-1]['end_s'] if j>i else start
        start=min(chunk_end,max(chunk_start,start));end=min(chunk_end,max(start,end))
        context_start=words[max(0,i-len(left))]['start_s'] if words and i-len(left)<len(words) else start
        context_end=words[min(len(words)-1,j+len(right)-1)]['end_s'] if words and j+len(right)>0 else end
        output.append({'a_range':[i,j],'a_tokens':a[i:j],'b_tokens':b[k:l],
            'left_anchor':left,'right_anchor':right,
            'start_s':start,'end_s':end,'context_start_s':context_start,'context_end_s':context_end,
            'eligible':len(left)+len(right)>=3 and max(j-i,l-k)<=40})
    return output


def choose_candidate(dispute,blind):
    """Only exact contextual corroboration can settle one of the two observed readings."""
    if blind.get('speech_presence')!='present' or not isinstance(blind.get('transcript'),str):return 'unresolved'
    if not dispute['eligible']:return 'unresolved'
    observed=tokens(blind['transcript'])
    def present(candidate):
        phrase=dispute['left_anchor']+candidate+dispute['right_anchor']
        return bool(phrase) and any(observed[i:i+len(phrase)]==phrase for i in range(len(observed)-len(phrase)+1))
    a,b=present(dispute['a_tokens']),present(dispute['b_tokens'])
    # Hearing an extra word twice is positive evidence. A shorter, single-ended
    # phrase alone cannot establish the absence of that word.
    if not dispute['a_tokens'] and dispute['b_tokens'] and b:return 'listener'
    if not dispute['b_tokens'] and dispute['a_tokens'] and a:return 'asr'
    if (not dispute['a_tokens'] or not dispute['b_tokens']) and not (dispute['left_anchor'] and dispute['right_anchor']):
        return 'unresolved'
    return 'asr' if a and not b else 'listener' if b and not a else 'unresolved'


def corroborate_local(dispute,context_decision,local):
    """Changing context must not reverse the perceived word; disagreement stays open."""
    if context_decision=='unresolved' or local.get('speech_presence')!='present' or not isinstance(local.get('transcript'),str):
        return 'unresolved'
    chosen=dispute['a_tokens' if context_decision=='asr' else 'b_tokens']
    other=dispute['b_tokens' if context_decision=='asr' else 'a_tokens']
    if not chosen:
        # Removing words requires the same anchored omission evidence in both views.
        return context_decision if choose_candidate(dispute,local)==context_decision else 'unresolved'
    observed=tokens(local['transcript'])
    def contains(phrase):
        return bool(phrase) and any(observed[i:i+len(phrase)]==phrase for i in range(len(observed)-len(phrase)+1))
    return context_decision if contains(chosen) and not contains(other) else 'unresolved'


def assemble(words,disputes,chunk_start,chunk_end):
    merged=[];cursor=0;uncertain=[]
    for d in disputes:
        i,j=d['a_range'];merged.extend(copy.deepcopy(words[cursor:i]));cursor=j
        decision=d['decision']
        if decision=='asr':merged.extend(copy.deepcopy(words[i:j]))
        elif decision=='listener':
            if d['b_tokens']:
                merged.append({'word':' '.join(d['b_tokens']),'start_s':d['start_s'],'end_s':d['end_s'],
                    'time_source':'approximate_replacement_span_not_forced_word_alignment','corroboration_id':d['id']})
        else:
            merged.append({'word':'[uncertain speech]','start_s':d['start_s'],'end_s':d['end_s'],
                           'uncertainty_id':d['id'],'time_source':'disputed_asr_span'})
            uncertain.append({'id':d['id'],'start_s':d['start_s'],'end_s':d['end_s']})
    merged.extend(copy.deepcopy(words[cursor:]))
    duration=chunk_end-chunk_start
    for w in merged:
        w['start_s']=min(duration,max(0,w['start_s']-chunk_start))
        w['end_s']=min(duration,max(w['start_s'],w['end_s']-chunk_start))
    text=' '.join(w['word'] for w in merged)
    utterances=[{'text':text,'start_s':merged[0]['start_s'],'end_s':max(w['end_s'] for w in merged),'words':merged}] if merged else []
    return text,utterances,uncertain


def guard_audio(video,packet,audio,client,out,max_rechecks=24):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    if max_rechecks<0:raise ValueError('nonnegative recheck budget required')
    if all(narration_absent(a) for a in audio):
        write_json(out/'summary.json',{'version':VERSION,'status':'verified_no_narration','rechecks':0})
        return copy.deepcopy(audio)
    if file_hash(video)!=packet['video_sha256']:raise ValueError('guard video changed since evidence extraction')
    full=out/'full_final_audio.wav'
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-y','-v','error','-i',str(video),'-vn',
        '-ar','16000','-ac','1','-c:a','pcm_s16le',str(full)],check=True,capture_output=True)
    continuous=transcribe(full);write_json(out/'continuous_asr.json',continuous)
    all_words=timed_tokens(continuous);pcm,signal=read_pcm(full)
    rechecks=0;results=copy.deepcopy(audio);all_disputes=[];blocks=[];current=[]
    for index,record in enumerate(audio):
        valid=not narration_absent(record) and record.get('transcript_valid') and isinstance(record.get('omni_transcript'),str)
        if valid:current.append(index)
        else:
            if current:blocks.append(current);current=[]
            results[index]['transcript_guard']={'version':VERSION,'status':'verified_no_narration' if narration_absent(record) else 'listener_evidence_unavailable'}
            if not narration_absent(record):results[index].update(transcript=None,utterances=[],transcript_valid=False,timing_valid=False)
    if current:blocks.append(current)
    for block_index,indices in enumerate(blocks):
        start=audio[indices[0]]['start_s'];end=audio[indices[-1]]['end_s']
        words=[w for w in all_words if start<=(w['start_s']+w['end_s'])/2<end]
        listener_text=' '.join(audio[i]['omni_transcript'] for i in indices)
        ds=differences(words,listener_text,start,end)
        write_json(out/f'block_{block_index:02d}_input.json',{'audio_ids':[audio[i]['id'] for i in indices],
            'continuous_asr_tokens':[w['word'] for w in words],'audio_listener_transcripts':listener_text})
        for index,d in enumerate(ds):
            d['id']=f"B{block_index:02d}_U{index:02d}"
            d['decision']='unresolved'
            directory=out/d['id'];directory.mkdir()
            write_json(directory/'disagreement.json',d)
            if not d['eligible'] or rechecks>=max_rechecks:
                d['reason']='Insufficient matching context anchors or bounded recheck budget exhausted.'
                continue
            ws=max(0,min(d['start_s']-2,d['context_start_s']-.6))
            we=min(signal['duration_s'],max(d['end_s']+2,d['context_end_s']+.6))
            if we-ws>24:
                d['reason']='Context needed for exact lexical corroboration exceeds the bounded 24-second window.'
                continue
            path=directory/'blind_window.wav'
            with wave.open(str(path),'wb') as wav:
                wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(16000)
                wav.writeframes(pcm[round(ws*16000):round(we*16000)].tobytes())
            d['window']={'start_s':ws,'end_s':we,'path':str(path.resolve()),'sha256':file_hash(path)}
            rechecks+=1
            try:
                # Candidates and context anchors are deliberately NOT sent to this listener.
                raw=client.chat([{'role':'system','content':SYSTEM},
                    {'role':'user','content':[audio_content({'path':str(path)})]}],
                    model='qwen3.5-omni-flash',purpose='blind_transcript_window',max_tokens=1200)
                write_json(directory/'blind_response.json',raw)
                if not isinstance(raw,dict):raise ValueError('invalid blind listener response')
                d['context_decision']=choose_candidate(d,raw)
                if d['context_decision']!='unresolved' and rechecks<max_rechecks:
                    ls=max(0,d['start_s']-.75);le=min(signal['duration_s'],max(d['end_s'],d['start_s']+.15)+.75)
                    local_path=directory/'local_window.wav'
                    with wave.open(str(local_path),'wb') as wav:
                        wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(16000)
                        wav.writeframes(pcm[round(ls*16000):round(le*16000)].tobytes())
                    d['local_window']={'start_s':ls,'end_s':le,'path':str(local_path.resolve()),'sha256':file_hash(local_path)}
                    rechecks+=1
                    local=client.chat([{'role':'system','content':SYSTEM},
                        {'role':'user','content':[audio_content({'path':str(local_path)})]}],
                        model='qwen3.5-omni-flash',purpose='local_blind_transcript_window',max_tokens=500)
                    write_json(directory/'local_response.json',local)
                    if not isinstance(local,dict):raise ValueError('invalid local listener response')
                    d['decision']=corroborate_local(d,d['context_decision'],local)
                elif d['context_decision']!='unresolved':
                    d['reason']='Recheck budget exhausted before the second audio view; no candidate accepted.'
            except Exception as exc:
                d['error']={'type':type(exc).__name__,'message':str(exc)[:400]}
            write_json(directory/'decision.json',d)
        _,utterances,uncertain=assemble(words,ds,start,end)
        merged=utterances[0]['words'] if utterances else []
        for word in merged:word['start_s']+=start;word['end_s']+=start
        for index in indices:
            record=audio[index];rs,re=record['start_s'],record['end_s']
            # Assign a cross-boundary word once, based on its observed midpoint.
            chunk_words=[w for w in merged if rs<=(w['start_s']+w['end_s'])/2<re]
            text,chunk_utterances,_=assemble(chunk_words,[],rs,re)
            local_uncertain=[u for u in uncertain if rs<=(u['start_s']+u['end_s'])/2<re]
            results[index].update(transcript=text,utterances=chunk_utterances,
                transcriber=VERSION,transcript_valid=True,timing_valid=bool(chunk_utterances),
                transcript_guard={'version':VERSION,'status':'partial' if local_uncertain else 'corroborated',
                    'unresolved_spans':local_uncertain,
                    'resolved_changes':sum(d['decision']=='listener' and rs<=(d['start_s']+d['end_s'])/2<re for d in ds),
                    'timing_scope':'ASR word intervals; replacements retain approximate original span intervals.'})
        all_disputes.extend(ds)
    write_json(out/'disputes.json',all_disputes)
    write_json(out/'summary.json',{'version':VERSION,'video_sha256':packet['video_sha256'],
        'full_audio_sha256':file_hash(full),'rechecks':rechecks,
        'disagreements':len(all_disputes),'resolved_asr':sum(d['decision']=='asr' for d in all_disputes),
        'resolved_listener':sum(d['decision']=='listener' for d in all_disputes),
        'unresolved':sum(d['decision']=='unresolved' for d in all_disputes),
        'scope':'Same-family audio-listener corroboration, not independent human validation. No task or visual text used.'})
    return results
