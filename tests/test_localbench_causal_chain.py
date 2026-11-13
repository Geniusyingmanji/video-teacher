import copy

import pytest

from localbench.causal_chain import compile_chain, validate_chain, validate_narrated_chain
from localbench.common import digest
from localbench.scene import render_frame


def example():
    refs = [{'id': 'S1', 'kind': 'public_reference', 'text': 'Fixture facts', 'source': 'fixture'}]
    chain = {'nodes': [{'id': 'A', 'label': 'Vapor condenses'},
                       {'id': 'B', 'label': 'Heat warms the air'},
                       {'id': 'C', 'label': 'Air keeps rising'}],
             'links': [{'source': 'A', 'target': 'B', 'explanation': 'Releases heat.', 'evidence_ids': ['S1']},
                       {'source': 'B', 'target': 'C', 'explanation': 'Supports ascent.', 'evidence_ids': ['S1']}]}
    return chain, refs


def test_actual_render_has_separate_labels_and_connectors_between_identified_nodes():
    chain, refs = example(); original = copy.deepcopy(chain)
    prims, receipt = compile_chain(chain, refs)
    scene = {'title': 'A mechanism', 'caption': 'A bounded explanation.', 'primitives': prims}
    _, layout = render_frame(scene, .5)
    assert not layout
    for i, edge in enumerate(receipt['links']):
        a, b = receipt['nodes'][i:i+2]
        arrow = prims[edge['primitive_index']]
        assert a['bbox'][3] < arrow['y'] < arrow['y2'] < b['bbox'][1]
        assert arrow['x'] == arrow['x2'] == (a['bbox'][0] + a['bbox'][2]) / 2
    assert chain == original and receipt['primitives_hash'] == digest(prims)
    assert receipt['semantic_acceptance'] == 'unverified'


@pytest.mark.parametrize('mutation', ['reverse', 'missing', 'cycle', 'duplicate', 'diagnostic_citation'])
def test_invalid_edges_are_rejected(mutation):
    chain, refs = example()
    if mutation == 'reverse': chain['links'][0].update(source='B', target='A')
    if mutation == 'missing': chain['links'].pop()
    if mutation == 'cycle': chain['links'][1]['target'] = 'A'
    if mutation == 'duplicate': chain['nodes'][1]['id'] = 'A'
    if mutation == 'diagnostic_citation':
        refs.append({'id': 'D1', 'kind': 'development_diagnostic'})
        chain['links'][0]['evidence_ids'] = ['D1']
    with pytest.raises(ValueError): validate_chain(chain, refs)


def test_long_labels_or_small_regions_fail_without_silent_truncation():
    chain, refs = example()
    with pytest.raises(ValueError, match='region too short'): compile_chain(chain, refs, region=(.55, .1, .4, .35))
    chain['nodes'][0]['label'] = 'W' * 40
    with pytest.raises(ValueError, match='too wide'): compile_chain(chain, refs)


def test_geometric_validation_does_not_certify_factually_false_chain():
    chain, refs = example()
    chain['nodes'][0]['label'] = 'False factual premise'
    _, receipt = compile_chain(chain, refs)
    assert receipt['semantic_acceptance'] == 'unverified'


def test_narrated_edit_enforces_budget_and_retains_model_semantics_verbatim():
    chain, refs = example()
    raw = {**chain, 'narration': 'Water vapor condenses and releases heat to the air.'}
    before = copy.deepcopy(raw)
    assert validate_narrated_chain(raw, refs, 'The original introductory explanation.', 12) == chain
    assert raw == before
    with pytest.raises(ValueError, match='5..6 words'):
        validate_narrated_chain(raw, refs, 'Original.', 6)
    with pytest.raises(ValueError, match='no-op'):
        validate_narrated_chain(raw, refs, raw['narration'], 12)


def test_narrated_output_cannot_inject_scene_overrides_or_unbound_edges():
    chain, refs = example()
    raw = {**chain, 'narration': 'Water vapor condenses and releases heat to the air.', 'duration_s': 12}
    with pytest.raises(ValueError, match='exact narration'):
        validate_narrated_chain(raw, refs, 'Original.', 12)
    raw.pop('duration_s'); raw['links'][0]['source'] = 'unknown'
    with pytest.raises(ValueError, match='adjacent'):
        validate_narrated_chain(raw, refs, 'Original.', 12)


def test_one_wrapped_label_gets_extra_space_without_shrinking_all_labels():
    chain, refs = example()
    chain['nodes'][0]['label'] = 'Condensation releases thermal energy'
    prims, receipt = compile_chain(chain, refs)
    boxes = [n['bbox'] for n in receipt['nodes']]
    assert boxes[0][3] - boxes[0][1] > boxes[1][3] - boxes[1][1]
    assert not render_frame({'title': 'A mechanism', 'caption': 'A bounded explanation.', 'primitives': prims}, .5)[1]
    assert all(p['font_size'] == 24 for p in prims if p['type'] == 'text')


def four_nodes():
    chain,refs=example()
    chain['nodes'].insert(2,{'id':'M','label':'Warmer air is less dense'})
    chain['links'][1]={'source':'B','target':'M','explanation':'Warming reduces density.','evidence_ids':['S1']}
    chain['links'].append({'source':'M','target':'C','explanation':'Buoyancy supports ascent.','evidence_ids':['S1']})
    return chain,refs


def test_four_node_expansion_is_opt_in_and_keeps_readable_connectors():
    chain,refs=four_nodes()
    with pytest.raises(ValueError,match='two to 3'):compile_chain(chain,refs)
    with pytest.raises(ValueError,match='region too short'):compile_chain(chain,refs,max_nodes=4)
    prims,receipt=compile_chain(chain,refs,region=(.54,.02,.42,.94),max_nodes=4)
    assert len(receipt['nodes'])==4 and len(receipt['links'])==3
    assert not render_frame({'title':'A mechanism','caption':'A bounded explanation.','primitives':prims},.5)[1]
    for i,edge in enumerate(receipt['links']):
        a,b=receipt['nodes'][i:i+2]
        assert a['bbox'][3]<edge['start'][1]<edge['end'][1]<b['bbox'][1]
    assert all(p['font_size']==24 for p in prims if p['type']=='text')


def test_four_nodes_that_wrap_fail_instead_of_losing_reason_text():
    chain,refs=four_nodes();chain['nodes'][1]['label']='Thermal energy to water near the beaker base'
    with pytest.raises(ValueError,match='region too short'):
        compile_chain(chain,refs,region=(.54,.02,.42,.94),max_nodes=4)
