import copy
import json

import pytest
from PIL import Image

from localbench import student_knowledge as sk


@pytest.fixture
def inputs(tmp_path):
    image = tmp_path/'f.jpg'
    Image.new('RGB', (32, 32), 'white').save(image)
    pack = {'version': sk.VERSION, 'case_id': 'case', 'reference_status': 'draft_not_expert_verified',
            'points': {'P1': {'kind': 'grounding', 'prompt': 'Describe the relation in the diagram.',
                'references': {'R1': {'statement': 'HIDDEN_REFERENCE_SENTINEL', 'source': 'private annotation', 'scope': 'only this point'}}}}}
    profile = {'id': 'basic', 'description': 'Reads arrows.', 'known': {'K0': 'Can follow an arrowhead.'}, 'not_assumed': []}
    obs = {'is_final': True, 'evidence_ids': ['F0', 'T0'], 'frames': [{'id': 'F0', 'path': str(image), 'time_s': 0}],
           'transcripts': [{'id': 'T0', 'text': 'Two objects move.'}]}
    return pack, profile, obs


def answer():
    return {'points': {'P1': {'explanation': 'The narrator claims convergence.', 'visual_observation': 'I cannot resolve the arrowheads.',
                              'narration_claim': 'The narrator says they meet.', 'uncertainty': 'The drawing is unclear.',
                              'evidence_ids': ['T0', 'F0']}}, 'prerequisite_used': ['K0']}


def review():
    return {'points': {'P1': {'knowledge_status': 'partial', 'media_support': 'supported',
                             'visual_grounding': 'narration_only', 'reference_ids': ['R1'],
                             'evidence_ids': ['T0'], 'reason': 'Restates narration without resolving arrows.'}}}


def test_learner_reference_firewall_and_no_task_prompt(inputs):
    pack, profile, obs = inputs
    learner = sk.messages(pack, profile, obs)
    assert 'HIDDEN_REFERENCE_SENTINEL' not in json.dumps(learner)
    assert 'references' not in json.loads(learner[1]['content'][0]['text'])
    judge = sk.messages(pack, profile, obs, response=answer())
    assert 'HIDDEN_REFERENCE_SENTINEL' in json.dumps(judge)
    assert set(json.loads(learner[1]['content'][0]['text'])) == {'profile', 'knowledge_prompts', 'media', 'required_output_template'}
    for request in (learner, judge):
        assert 'JSON' in request[0]['content']
        assert set(json.loads(request[1]['content'][0]['text'])['required_output_template']['points']) == {'P1'}


def test_distinct_correctness_and_media_support(inputs):
    pack, profile, obs = inputs
    raw = review()
    raw['points']['P1']['knowledge_status'] = 'incorrect'
    # Faithful reproduction of a wrong video may be supported AND incorrect.
    assert sk.validate_review(raw, pack, obs) == raw
    raw['points']['P1']['reference_ids'] = []
    with pytest.raises(ValueError, match='reference IDs'):
        sk.validate_review(raw, pack, obs)


@pytest.mark.parametrize('change', ['drop', 'future', 'visual_from_transcript'])
def test_required_coverage_and_evidence(inputs, change):
    pack, profile, obs = inputs
    raw = review()
    if change == 'drop':
        raw['points'] = {}
    elif change == 'future':
        raw['points']['P1']['evidence_ids'] = ['FUTURE']
    else:
        raw['points']['P1']['visual_grounding'] = 'demonstrated'
    with pytest.raises(ValueError):
        sk.validate_review(raw, pack, obs)


def test_explicit_uncertainty_does_not_require_invented_citation(inputs):
    pack, profile, obs = inputs
    raw = answer()
    raw['points']['P1']['evidence_ids'] = []
    assert sk.validate_response(raw, pack, profile, obs) == raw
    raw['points']['P1']['uncertainty'] = ''
    with pytest.raises(ValueError, match='uncertainty'):
        sk.validate_response(raw, pack, profile, obs)


def test_schema_repair_cannot_improve_or_drop_knowledge_answer(inputs, tmp_path):
    pack, profile, obs = inputs
    class Student:
        count = 0
        def chat(self, *args, **kwargs):
            self.count += 1
            raw = answer()
            if self.count == 1:
                raw['extra'] = 1
            else:
                raw['points']['P1']['explanation'] = 'A newly correct answer.'
            return raw
    class Judge:
        def chat(self, *args, **kwargs):
            raise AssertionError('lossy response must not reach review')
    result = sk.run_session(pack, profile, obs, tmp_path/'run', Student(), Judge())
    assert result['status'] == 'student_error'
    assert 'schema repair changed' in result['error']
    assert (tmp_path/'run/student_raw_0.json').exists()
    assert (tmp_path/'run/student_raw_1.json').exists()


def test_complete_session_and_failures_remain_in_denominator(inputs, tmp_path):
    pack, profile, obs = inputs
    class Student:
        def chat(self, *args, **kwargs):
            return answer()
    class Judge:
        def chat(self, *args, **kwargs):
            return review()
    result = sk.run_session(pack, profile, obs, tmp_path/'run', Student(), Judge())
    assert result['status'] == 'complete' and result['score'] is None
    profiles = {'case': [profile, {**profile, 'id': 'failed'}]}
    summary = sk.summarize([result, {'status': 'student_error'}], {'case': pack}, profiles)
    assert summary['planned_point_responses'] == 2
    assert summary['reviewed_point_responses'] == 1
    assert summary['complete_sessions'] == 1
    assert summary['score'] is None
    with pytest.raises(ValueError, match='complete sampled lesson'):
        sk.run_session(pack, profile, {**obs, 'is_final': False}, tmp_path/'partial', Student(), Judge())
