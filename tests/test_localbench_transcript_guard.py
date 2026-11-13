import copy

import pytest
import numpy as np

from localbench.transcript_guard import tokens,timed_tokens,differences,choose_candidate,corroborate_local,assemble
from localbench.alignment import speech_windows
from localbench.judge import evaluation_version


def words(text,start=10):
    return [{'word':w,'start_s':start+i*.3,'end_s':start+(i+1)*.3} for i,w in enumerate(tokens(text))]


def disagreement():
    a=words('we see the clear central ice surrounded by cloud bands')
    ds=differences(a,'we see the clear central eye surrounded by cloud bands',10,20)
    assert len(ds)==1
    return a,ds[0]


def test_numeric_typography_is_normalized_without_correcting_facts_or_negation():
    assert tokens('5,250 mL and 5.25 liters')==tokens('five thousand two hundred fifty milliliters and five point two five liters')
    assert tokens('6.25')!=tokens('5.25')
    assert tokens("doesn't become law")==tokens('does not become law')
    assert tokens('not valid')!=tokens('valid')
    assert tokens('ice')!=tokens('eye')
    assert tokens('-5')!=tokens('5') and tokens('-5')==tokens('minus five')
    assert tokens('50%')==tokens('fifty percent')
    assert tokens('1/2')==tokens('one divided by two')
    assert tokens('3 × 2 = 6')==tokens('three times two equals six')
    assert tokens('counter-clockwise')==tokens('counter clockwise')


def test_blind_audio_can_preserve_real_error_or_corroborate_alternative():
    _,d=disagreement()
    assert choose_candidate(d,{'speech_presence':'present','transcript':'We see the clear central eye surrounded by cloud bands.'})=='listener'
    # The listener hears the wrong word: no task or frame can silently correct it.
    assert choose_candidate(d,{'speech_presence':'present','transcript':'We see the clear central ice surrounded by cloud bands.'})=='asr'
    assert choose_candidate(d,{'speech_presence':'uncertain','transcript':'eye'})=='unresolved'
    assert choose_candidate(d,{'speech_presence':'present','transcript':'A completely different sentence about the eye.'})=='unresolved'
    assert choose_candidate(d,{'speech_presence':'present','transcript':'the clear central eye surrounded by cloud then the clear central ice surrounded by cloud'})=='unresolved'


def test_unsupported_disputed_words_do_not_reenter_scoring_or_alignment_context():
    a,d=disagreement();d.update(id='A00_U00',decision='unresolved')
    snapshot=copy.deepcopy(a)
    text,utterances,uncertain=assemble(a,[d],10,20)
    assert a==snapshot and 'ice' not in text and 'eye' not in text
    assert '[uncertain speech]' in text and 'surrounded by cloud bands' in text
    assert uncertain[0]['id']=='A00_U00'
    probes=speech_windows([{'id':'A00','start_s':10,'end_s':20,'timing_valid':True,
        'utterances':utterances,'transcript_guard':{'status':'partial'}}])
    assert any('A00_U00' in p['transcript_uncertainties'] for p in probes)
    assert all('ice' not in p['text'] and 'eye' not in p['text'] for p in probes)


def test_corroborated_replacement_keeps_approximate_observed_span_and_surrounding_speech():
    a,d=disagreement();d.update(id='A00_U00',decision='listener')
    text,utterances,uncertain=assemble(a,[d],10,20)
    assert 'central eye surrounded' in text and not uncertain
    replacement=next(w for w in utterances[0]['words'] if w.get('corroboration_id'))
    assert replacement['start_s']==pytest.approx(d['start_s']-10)
    assert replacement['end_s']==pytest.approx(d['end_s']-10)
    assert replacement['time_source'].startswith('approximate')


def test_timing_is_not_invented_when_continuous_asr_has_no_word_evidence():
    with pytest.raises(ValueError,match='word timestamps'):
        timed_tokens({'duration_s':10,'utterances':[{'text':'words without timing'}]})
    assert evaluation_version()=='localbench-ten-dimensions-dev13-integer-r3'
    assert '+transcript-guard-dev3+' in evaluation_version(transcript_guard=True)


def test_corroboration_window_includes_anchors_across_actual_silence_gaps():
    a=words('volume per beets per minute substituting the values')
    for w in a[5:]:w['start_s']+=6;w['end_s']+=6
    ds=differences(a,'volume per beats per minute substituting the values',10,30)
    assert ds[0]['context_end_s']>ds[0]['end_s']+6


def test_extra_heard_word_needs_positive_corroboration_but_absence_needs_both_anchors():
    a=words('convert it to')
    d=differences(a,'convert it to liters',10,20)[0]
    assert choose_candidate(d,{'speech_presence':'present','transcript':'convert it to liters'})=='listener'
    assert choose_candidate(d,{'speech_presence':'present','transcript':'convert it to'})=='unresolved'


def test_fresh_asr_numpy_timestamps_and_json_cache_timestamps_have_same_semantics():
    raw={'duration_s':10,'utterances':[{'words':[{'word':'hello','start_s':np.float64(.4),'end_s':np.float64(.8)}]}]}
    result=timed_tokens(raw)
    assert result[0]['start_s']==.4 and type(result[0]['start_s']) is float
    raw['utterances'][0]['words'][0]['start_s']=True
    with pytest.raises(ValueError,match='timing'):timed_tokens(raw)


def test_context_sensitive_rewrite_does_not_erase_a_potential_real_spoken_error():
    _,d=disagreement()
    assert corroborate_local(d,'listener',{'speech_presence':'present','transcript':'central ice surround'})=='unresolved'
    assert corroborate_local(d,'listener',{'speech_presence':'present','transcript':'central eye surround'})=='listener'
    assert corroborate_local(d,'asr',{'speech_presence':'present','transcript':'central ice surround'})=='asr'
    assert corroborate_local(d,'listener',{'speech_presence':'present','transcript':'centralized'})=='unresolved'
    numeric={'a_tokens':['five','point','two','five'],'b_tokens':['six','point','two','five']}
    assert corroborate_local(numeric,'listener',{'speech_presence':'present','transcript':'6.25 liters'})=='listener'
    assert corroborate_local(numeric,'listener',{'speech_presence':'present','transcript':'5.25 liters'})=='unresolved'
