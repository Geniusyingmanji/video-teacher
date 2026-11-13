import copy

import pytest

from localbench.semantic_speech import compile_speech, compile_edits, SLOTS


def fixture():
    text = 'In the beaker, conduction heats bottom water, lowering its density and supporting buoyant ascent.'
    quotes = ['In the beaker', 'conduction', 'heats', 'bottom water', 'buoyant ascent', 'lowering its density']
    raw = {'narration': text, 'witnesses': {s:{'quote':q,'evidence_ids':[] if s=='context' else ['S1']}
                                          for s,q in zip(SLOTS,quotes)}}
    return raw, [{'id':'S1','kind':'public_reference'}]


def test_omitted_causal_warrant_cannot_be_accepted_as_complete_coverage():
    raw,refs=fixture();raw['witnesses'].pop('mechanism')
    with pytest.raises(ValueError,match='mechanism witnesses'):compile_speech(raw,refs,32)
    raw,refs=fixture();raw['narration']=raw['narration'].replace('lowering its density and ','')
    with pytest.raises(ValueError,match='mechanism: quote'):compile_speech(raw,refs,32)


def test_speech_and_source_ids_are_bound_without_paraphrasing():
    raw,refs=fixture();before=copy.deepcopy(raw)
    text,receipt=compile_speech(raw,refs,32)
    assert raw==before and text==raw['narration']
    for value in receipt['witnesses'].values():
        assert all(text[a:b]==value['quote'] for a,b in value['character_spans'])
    raw['witnesses']['recipient']['evidence_ids']=['not_supplied']
    with pytest.raises(ValueError,match='unknown'):compile_speech(raw,refs,32)


def test_length_failure_preserves_all_source_text():
    raw,refs=fixture();before=copy.deepcopy(raw)
    with pytest.raises(ValueError,match='word budget'):compile_speech(raw,refs,5)
    assert raw==before


def test_wrong_semantic_binding_is_not_certified_by_span_existence():
    raw,refs=fixture();raw['witnesses']['mechanism']['quote']='In the beaker'
    _,receipt=compile_speech(raw,refs,32)
    assert receipt['semantic_acceptance']=='unverified'
    assert receipt['witnesses']['mechanism']['semantic_support']=='unverified'


def test_duplicate_occurrences_are_retained_for_review():
    raw,refs=fixture();raw['narration']+=' Bottom water remains bottom water.'
    _,receipt=compile_speech(raw,refs,32)
    assert len(receipt['witnesses']['recipient']['character_spans'])==2


def edit_fixture():
    roles={'narration':'Vapor condenses, releasing heat that supports continued ascent.',
        'process':'Vapor condenses','transfer':'heat','recipient':'rising air','outcome':'continued ascent',
        'relation_explanations':['Condensation releases heat.', 'Warmer air is less dense, promoting further upward motion.']}
    program=[{'op':'replace','before':'releasing {transfer} that supports {outcome}',
              'after':'releasing {transfer} to {recipient}, supporting {outcome}'},
             {'op':'append_relation','index':1}]
    return roles,program


def test_exact_span_edit_retains_frozen_warrant_and_source_record():
    roles,program=edit_fixture();before=copy.deepcopy(roles)
    text,receipt=compile_edits(roles,program,32)
    assert 'heat to rising air' in text and text.endswith(roles['relation_explanations'][1])
    assert roles==before and receipt['original_narration']==roles['narration']
    assert receipt['semantic_acceptance']=='unverified'


def test_ambiguous_span_and_unknown_fields_fail_without_guessing():
    roles,program=edit_fixture();roles['narration']+=' '+roles['narration']
    with pytest.raises(ValueError,match='exactly once'):compile_edits(roles,program,90)
    roles,program=edit_fixture();program[0]['after']='{recipient.__class__}'
    with pytest.raises(ValueError,match='exact frozen role names'):compile_edits(roles,program,90)


def test_edit_budget_cannot_silently_discard_added_warrant():
    roles,program=edit_fixture();before=copy.deepcopy(roles)
    with pytest.raises(ValueError,match='no relation may be dropped'):compile_edits(roles,program,10)
    assert roles==before


def test_empty_program_is_reported_as_unchanged_not_a_repair_success():
    roles,_=edit_fixture();text,receipt=compile_edits(roles,[],32)
    assert text==roles['narration'] and not receipt['changed']
