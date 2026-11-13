import copy

import pytest

from localbench.mechanism_chain import compile_extractive, compile_mechanism, ROLES
from localbench.scene import render_frame


def fixture():
    raw = dict(process='Heating at the base', recipient_effect='Water warms',
               mechanism='Lower density', outcome='Buoyant ascent',
               links=[{'explanation': 'Fixture relation.', 'evidence_ids': ['S1']} for _ in range(3)])
    return raw, [{'id': 'S1', 'kind': 'public_reference', 'text': 'Fixture source.'}]


def test_every_mechanism_stage_is_visible_and_connected_without_content_rewriting():
    raw, refs = fixture(); before = copy.deepcopy(raw)
    prims, receipt = compile_mechanism(raw, refs)
    assert [p['text'] for p in prims if p['type'] == 'text'] == [raw[k] for k in ROLES]
    assert len([p for p in prims if p['type'] == 'arrow']) == 3
    assert not render_frame({'title': 'A mechanism', 'caption': 'A bounded explanation.', 'primitives': prims}, .5)[1]
    assert raw == before and receipt['semantic_acceptance'] == 'unverified'


@pytest.mark.parametrize('mutation', ['missing_mechanism', 'private_source', 'new_narration'])
def test_missing_stage_or_nonpublic_source_or_speech_edit_fails(mutation):
    raw, refs = fixture()
    if mutation == 'missing_mechanism': raw.pop('mechanism')
    if mutation == 'private_source': raw['links'][1]['evidence_ids'] = ['hidden_answer']
    if mutation == 'new_narration': raw['narration'] = 'Rewrite the lesson.'
    with pytest.raises(ValueError): compile_mechanism(raw, refs)


def test_layout_failure_does_not_silently_shrink_or_drop_a_mechanism():
    raw, refs = fixture(); raw['mechanism'] = 'W' * 30
    before = copy.deepcopy(raw)
    with pytest.raises(ValueError, match='too wide'): compile_mechanism(raw, refs)
    assert raw == before


def test_geometric_acceptance_does_not_establish_narration_or_source_entailment():
    raw, refs = fixture(); raw['mechanism'] = 'The magic explanation'
    _, receipt = compile_mechanism(raw, refs)
    assert receipt['semantic_acceptance'] == 'unverified'


def extraction():
    narration = 'Conduction transfers heat to the base water, lowering its density and causing buoyant ascent.'
    quote = 'Hotter water expands, decreases in density, and rises.'
    refs = [{'id': 'S1', 'kind': 'public_reference', 'verbatim_excerpt': quote}]
    raw = dict(process='Conduction', transfer='heat', recipient='base water',
               state_change='lowering its density', outcome='buoyant ascent',
               links=[{'explanation': 'Fixture relation.', 'evidence_ids': ['S1'], 'source_quote': quote} for _ in range(3)])
    return raw, narration, refs


def test_extractive_labels_are_bound_to_narration_and_displayed():
    raw, narration, refs = extraction()
    prims, receipt = compile_extractive(raw, narration, refs)
    assert [p['text'] for p in prims if p['type'] == 'text'] == [
        'Conduction', 'heat to base water', 'lowering its density', 'buoyant ascent']
    assert receipt['status'] == 'compiled'
    assert receipt['semantic_acceptance'] == 'unverified'
    assert not render_frame({'title': 'Transfer', 'caption': 'Same explanation.', 'primitives': prims}, .5)[1]


def test_extraction_rejects_unspoken_mechanism_without_editing_it():
    raw, narration, refs = extraction(); raw['state_change'] = 'Buoyant force exceeds weight'
    before = copy.deepcopy(raw)
    with pytest.raises(ValueError, match='state_change is absent'):
        compile_extractive(raw, narration, refs)
    assert raw == before


def test_missing_intermediate_change_can_be_omitted_without_invention():
    raw, narration, refs = extraction(); raw['state_change'] = None; raw['links'].pop()
    prims, receipt = compile_extractive(raw, narration, refs)
    assert len(receipt['chain']['nodes']) == 3
    assert len([p for p in prims if p['type'] == 'arrow']) == 2
    raw['links'].append(copy.deepcopy(raw['links'][0]))
    with pytest.raises(ValueError, match='exactly 2'):
        compile_extractive(raw, narration, refs)


def test_unsupported_extraction_produces_no_diagram():
    _, narration, refs = extraction()
    prims, receipt = compile_extractive({'unsupported': 'No faithful receiving entity.'}, narration, refs)
    assert prims is None and receipt['status'] == 'not_applicable'


def test_source_quote_must_occur_in_a_cited_source():
    raw, narration, refs = extraction()
    raw['links'][0]['source_quote'] = 'Different exact quotation.'
    refs.append({'id': 'S2', 'kind': 'public_reference', 'text': 'Different exact quotation.'})
    with pytest.raises(ValueError, match='source_quote must be an exact passage'):
        compile_extractive(raw, narration, refs)


def test_exact_spans_still_do_not_establish_correct_role_assignment():
    raw, narration, refs = extraction()
    raw['state_change'], raw['outcome'] = raw['outcome'], raw['state_change']
    _, receipt = compile_extractive(raw, narration, refs)
    assert receipt['semantic_acceptance'] == 'unverified'
