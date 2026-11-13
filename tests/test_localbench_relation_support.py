import copy

import pytest

from localbench.relation_support import summarize, validate, review_frame


def row():
    return {'frame_id': 'F00', 'screen_claims': ['A -> B -> C'],
        'comparison_claim': 'A -> B -> C', 'claim_kind': 'static_relation',
        'observed_relations': [{'region': 'diagram', 'objects': 'A, B and one arrow',
                              'geometry': 'Arrowhead at B with other endpoint at A.'}],
        'relation_checks': [
            {'id': 'R1', 'claim_fragment': 'A -> B', 'expected': 'A connects to B',
             'status': 'supported', 'diagram_relation_indices': [0],
             'observed': 'The drawn arrow connects A to B.', 'reason': 'Both endpoints and direction agree.'},
            {'id': 'R2', 'claim_fragment': 'B -> C', 'expected': 'B connects to C',
             'status': 'not_depicted', 'diagram_relation_indices': [],
             'observed': 'No C node or B-to-C link is drawn.', 'reason': 'Absence does not establish an opposed relation.'}]}


def check(value):
    return validate({'frames': [value]}, [{'id': 'F00'}])[0]


def test_partial_chain_preserves_missing_support_without_becoming_a_contradiction():
    value = row(); before = copy.deepcopy(value)
    result = summarize(check(value))
    assert value == before
    assert result['model_listed_relations'] == {'supported': 1, 'opposed': 0, 'not_depicted': 1, 'unreadable': 0}
    assert result['opposed_relation_reported'] is False
    assert result['claim_extraction_completeness'] == 'unverified'
    assert not {'score', 'overall', 'fully_supported'} & set(result)


@pytest.mark.parametrize('status', ['supported', 'opposed'])
def test_support_and_opposition_both_require_independent_diagram_reference(status):
    value = row(); value['relation_checks'][0]['status'] = status
    value['observed_relations'][0]['region'] = 'caption'
    with pytest.raises(ValueError, match='corroborate'): check(value)
    value['observed_relations'][0]['region'] = 'diagram'
    value['relation_checks'][0]['diagram_relation_indices'] = []
    with pytest.raises(ValueError, match='both need'): check(value)


def test_invented_or_duplicate_indices_and_claim_fragments_fail():
    for indices in [[True], [-1], [1], [0, 0]]:
        value = row(); value['relation_checks'][0]['diagram_relation_indices'] = indices
        with pytest.raises(ValueError, match='indices'): check(value)
    value = row(); value['relation_checks'][0]['claim_fragment'] = 'A -> C'
    with pytest.raises(ValueError, match='substring'): check(value)


def test_no_claim_and_temporal_uncertainty_do_not_become_support():
    value = row(); value.update(claim_kind='no_claim', comparison_claim='', relation_checks=[])
    assert summarize(check(value))['model_listed_relations']['supported'] == 0
    value = row(); value['claim_kind'] = 'ongoing_process'
    with pytest.raises(ValueError, match='temporal'): check(value)
    for c in value['relation_checks']: c['status'] = 'unreadable'
    assert summarize(check(value))['model_listed_relations']['unreadable'] == 2


def test_structurally_valid_observation_is_not_a_semantic_guarantee():
    value = row()
    value['observed_relations'][0]['geometry'] = 'A rectangular box has no relation to this claim.'
    # Deliberate limit: type/index checks cannot establish semantic support.
    assert check(value)['relation_checks'][0]['status'] == 'supported'


def test_live_request_meets_provider_explicit_json_mode_contract(tmp_path):
    frame = tmp_path / 'frame.jpg'
    from PIL import Image
    Image.new('RGB', (32, 32), 'white').save(frame)

    class ProviderContract:
        def chat(self, messages, **kwargs):
            text = ' '.join(m['content'] if isinstance(m['content'], str) else
                ' '.join(p.get('text', '') for p in m['content']) for m in messages)
            # Observed HTTP400 requirement for response_format=json_object.
            if 'json' not in text.casefold():
                raise RuntimeError('messages must contain the word json')
            return {'frames': [row()]}

    result = review_frame(ProviderContract(), {'id': 'F00', 'time_s': 0, 'path': str(frame)}, tmp_path / 'out')
    assert result['relation_checks'][1]['status'] == 'not_depicted'
