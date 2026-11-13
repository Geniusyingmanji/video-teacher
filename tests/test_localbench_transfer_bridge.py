import copy

import pytest

from localbench.transfer_bridge import validate_bridge, compose_narration, ROLES
from localbench.causal_chain import compile_chain


def example():
    refs = [{'id': 'S1', 'kind': 'public_reference'}]
    raw = {'narration': 'Condensation releases heat into rising air and supports continued ascent.',
           'process': 'Vapor condenses', 'transfer': 'Heat', 'recipient': 'rising air',
           'outcome': 'continued ascent', 'evidence_ids': ['S1'],
           'relation_explanations': ['Condensation releases heat into air.', 'Warming helps air rise.']}
    return raw, refs


def test_all_required_roles_are_preserved_in_displayed_node_labels():
    raw, refs = example(); before = copy.deepcopy(raw)
    chain = validate_bridge(raw, refs, 'Original.', 20)
    prims, receipt = compile_chain(chain, refs)
    displayed = ' '.join(p['text'] for p in prims if p['type'] == 'text')
    assert all(raw[k] in displayed for k in ROLES)
    assert raw == before and len(receipt['links']) == 2
    assert receipt['semantic_acceptance'] == 'unverified'


@pytest.mark.parametrize('role', ROLES)
def test_missing_or_blank_role_cannot_silently_disappear(role):
    raw, refs = example(); raw.pop(role)
    with pytest.raises(ValueError, match='four roles'):
        validate_bridge(raw, refs, 'Original.', 20)
    raw[role] = ''
    with pytest.raises(ValueError, match='nonempty'):
        validate_bridge(raw, refs, 'Original.', 20)


def test_citation_and_narration_budget_are_enforced():
    raw, refs = example(); raw['evidence_ids'] = ['not_supplied']
    with pytest.raises(ValueError, match='public references'):
        validate_bridge(raw, refs, 'Original.', 20)
    raw, refs = example()
    with pytest.raises(ValueError, match='5..5 words'):
        validate_bridge(raw, refs, 'Original.', 5)


def test_wrong_role_values_still_require_semantic_review():
    raw, refs = example(); raw['recipient'] = 'wrong recipient'
    chain = validate_bridge(raw, refs, 'Original.', 20)
    assert chain['nodes'][1]['label'] == 'Heat to wrong recipient'
    assert compile_chain(chain, refs)[1]['semantic_acceptance'] == 'unverified'


def test_shared_narration_contains_every_role_without_manual_semantic_substitution():
    raw, refs = example(); before = copy.deepcopy(raw)
    narration, receipt = compose_narration(raw, refs, 'Warm oceans supply moist air.', 32)
    assert narration.startswith('Warm oceans supply moist air.')
    assert all(raw[k] in narration for k in ROLES)
    assert raw == before and receipt['role_values'] == {k: raw[k] for k in ROLES}
    assert not receipt['generated_free_prose_used']
    assert receipt['semantic_acceptance'] == 'unverified'


def test_compiled_narration_cannot_drop_roles_to_fit_budget():
    raw, refs = example()
    with pytest.raises(ValueError, match='no role may be silently dropped'):
        compose_narration(raw, refs, 'Warm oceans supply moist air.', 8)
