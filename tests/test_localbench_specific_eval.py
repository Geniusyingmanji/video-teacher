import copy
import json

import pytest

from localbench.common import digest, write_json
from localbench.specific_eval import load_questions, aggregate_assessments, evaluate_specific
from localbench.services import ServicePool, JudgeClient, judge_panel_from
from test_localbench_judge_panel import config, evidence


def entry(case):
    return {'case_hash': digest(case), 'references': {'R1': {'statement': 'A stated task requirement.'}},
            'questions': [{'id': 'S01', 'question': 'Is the requested relation demonstrated?', 'reference_status': 'draft',
                           'targets': [{'criterion': 'The relation is visible.', 'source_ids': ['R1'], 'visual_required': True}]}]}


@pytest.mark.parametrize('bad', ['task_hash', 'duplicate', 'reference', 'empty', 'visual_type'])
def test_fixed_question_binding_and_schema(tmp_path, bad):
    case = {'id': 'a', 'prompt_text': 'A task'}; item = entry(case)
    path = tmp_path/'q.json'
    write_json(path, {'version': 'fixed-specific-v1', 'cases': {'a': item}})
    assert load_questions(str(path), [case], tmp_path)['cases']['a'] == item
    if bad == 'task_hash': item['case_hash'] = 'wrong'
    elif bad == 'duplicate': item['questions'].append(copy.deepcopy(item['questions'][0]))
    elif bad == 'reference': item['questions'][0]['targets'][0]['source_ids'] = ['unknown']
    elif bad == 'empty': item['questions'] = []
    else: item['questions'][0]['targets'][0]['visual_required'] = 'yes'
    write_json(path, {'version': 'fixed-specific-v1', 'cases': {'a': item}})
    with pytest.raises(ValueError): load_questions(str(path), [case], tmp_path)


def test_specific_median_target_conflict_and_missing_judge():
    pool = {'S01': entry({'id': 'a'})['questions'][0]}
    def row(score=4, state='partial'):
        return {'status': 'scored', 'score': score, 'reason': 'A relation is partly visible.',
                'targets': [{'status': state, 'reason': 'Missing link.', 'evidence_ids': ['F00']}]}
    results = [{'id': str(i), 'assessment': {'groups': {'S01': row(s)}}} for i, s in enumerate([3,4,4])]
    assert aggregate_assessments(pool, results)['specific_score'] == 75
    results[0]['assessment']['groups']['S01'] = row(5, 'met')
    results[1]['assessment']['groups']['S01'] = row(4, 'incorrect')
    got = aggregate_assessments(pool, results)
    assert got['specific_score'] is None and got['groups']['S01']['target_conflicts'] == [0]
    results[0]['assessment'] = {'groups': {}}
    assert aggregate_assessments(pool, results)['specific_score'] is None


def test_all_three_receive_identical_frozen_questions_and_observation(tmp_path, monkeypatch):
    from localbench.student_questions import pipeline
    video = tmp_path/'v.mp4'; video.write_bytes(b'fixture'); case = {'id': 'a'}
    out = tmp_path/'out'; evidence(video, out); item = entry(case)
    requests = []
    def assess(pool, questions, observation, refs, destination, client):
        requests.append(digest([pool, questions, observation, refs]))
        assert observation['transcripts'][0]['text'] == 'Actual spoken words.'
        return {'groups': {'S01': {'status': 'scored', 'score': 5, 'reason': 'All targets observed.',
                'targets': [{'status': 'met', 'reason': 'Actual frame shows the relation.', 'evidence_ids': ['F00']}]}}}, []
    monkeypatch.setattr(pipeline, 'assess_frozen', assess)
    pool = ServicePool(tmp_path/'api')
    members = [(s, JudgeClient(pool.client(s.service), None)) for s in judge_panel_from(config())]
    try: got = evaluate_specific(case, item, out, members)
    finally: pool.close()
    assert len(requests) == 3 and len(set(requests)) == 1
    assert got['specific_score'] == 100 and got['question_pack_hash'] == digest(item)
    assert len(list((out/'specific/judges').glob('*/assessment.json'))) == 3
    assert json.loads((out/'specific/scores.json').read_text())['status'] == 'complete'
