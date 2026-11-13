import copy

import pytest

from localbench.visual_agent import validate_feedback, validate_memory, validate_blind
from localbench.refine import apply_diagrams
from localbench.rerender import diagram_only_plan


def feedback():
    return {'issues': [{'id': 'i1', 'group': 'expression', 'scene': 0,
                        'evidence_ids': ['F00'], 'observation': 'curve rises',
                        'requested_change': 'check the plotted quantity', 'visual_edit_sufficient': True}]}


def test_feedback_requires_real_evidence_and_scene():
    assert validate_feedback(feedback(), [{'id': 'F00'}], 1)
    for key, value in [('evidence_ids', ['F99']), ('scene', 1), ('group', 'fake'), ('visual_edit_sufficient', 'true')]:
        bad = feedback();bad['issues'][0][key] = value
        with pytest.raises(ValueError):
            validate_feedback(bad, [{'id': 'F00'}], 1)


def test_feedback_normalizes_integer_ids_without_mutating_raw_or_hiding_collisions():
    raw = feedback();raw['issues'][0]['id'] = 1
    assert validate_feedback(raw, [{'id': 'F00'}], 1)['issues'][0]['id'] == '1'
    assert raw['issues'][0]['id'] == 1
    raw['issues'].append({**raw['issues'][0], 'id': '1'})
    with pytest.raises(ValueError, match='unique'):
        validate_feedback(raw, [{'id': 'F00'}], 1)


def test_memory_cannot_claim_unsourced_experience():
    rule = {'id': 'r1', 'group': 'expression', 'trigger': 'numeric trend',
            'action': 'Derive positions from numbers and declared axes.', 'evidence_issue_ids': ['i1']}
    assert validate_memory({'rules': [rule]}, feedback())
    bad = copy.deepcopy(rule);bad['evidence_issue_ids'] = ['another_case']
    with pytest.raises(ValueError):
        validate_memory({'rules': [bad]}, feedback())
    with pytest.raises(ValueError):
        validate_memory({'rules': [rule, rule]}, feedback())


def test_visual_patch_preserves_nonvisual_fields_and_cannot_override_trusted_states():
    scene = {'narration': 'An explanation.', 'duration_s': 10, 'caption': 'Relationship',
             'primitives': [{'type': 'text', 'x': .5, 'y': .5, 'text': 'before'}]}
    original = {'case_id': 'x', 'scenes': [scene]}
    replacement = {'replacements': [{'scene': 0, 'primitives': [{'type': 'text', 'x': .4, 'y': .4, 'text': 'after'}]}]}
    fixed = apply_diagrams(original, replacement)
    assert diagram_only_plan(original, fixed)[1] == [0]
    assert fixed['scenes'][0]['narration'] == original['scenes'][0]['narration']
    fixed['scenes'][0]['duration_s'] = 11
    with pytest.raises(ValueError):
        diagram_only_plan(original, fixed)
    original['scenes'][0]['state_visual'] = {'state': {}}
    with pytest.raises(ValueError):
        apply_diagrams(original, replacement)


def test_blind_comparison_requires_both_video_evidence_and_valid_scores():
    value = {'A': 2, 'B': 4, 'evidence_ids': ['A00', 'B00'], 'reason': 'The visual relationship differs.'}
    raw = {'winner': 'B', 'dimensions': {k: copy.deepcopy(value) for k in
           ['visual_correctness', 'visual_coverage', 'visual_explanation', 'readability']}}
    assert validate_blind(raw, {'A00', 'B00'})
    raw['dimensions']['readability']['evidence_ids'] = ['A00']
    with pytest.raises(ValueError):
        validate_blind(raw, {'A00', 'B00'})


def test_diagnostic_review_failure_does_not_drop_valid_candidate(monkeypatch, tmp_path):
    import localbench.visual_agent as agent
    original = {'case_id': 'x', 'scenes': [{'primitives': []}]}
    proposed = copy.deepcopy(original)
    proposed['scenes'][0]['primitives'] = [{'type': 'text', 'text': 'revised'}]
    artifact = {'video_path': 'source.mp4', 'sha256': 'original'}
    output = {'video_path': 'revised.mp4', 'sha256': 'revised', 'complete': True}
    monkeypatch.setattr(agent, 'patch', lambda *a, **kw: (proposed, []))
    monkeypatch.setattr(agent, 'evidence', lambda *a, **kw: [])
    def fail_review(*args, **kwargs):
        raise ValueError('bounded issue list required')
    monkeypatch.setattr(agent, 'review', fail_review)
    monkeypatch.setattr(agent, 'encode', lambda *a, **kw: output)
    monkeypatch.setattr(agent, 'decoded_audio_hash', lambda *a: 'identical_pcm')
    result = agent.run_variant(None, {'id': 'x'}, original, artifact, feedback(), [],
                               {'rules': []}, tmp_path, 'feedback_memory')
    assert result['status'] == 'rendered'
    assert result['artifact'] == output
    assert result['feedback_after'] is None
    assert 'bounded issue list required' in result['feedback_after_error']
    assert result['decoded_audio_identical']


def test_layout_retry_retains_previous_scene_edit_and_refreshes_preview(monkeypatch, tmp_path):
    import json
    import localbench.visual_agent as agent
    original = {'case_id': 'x', 'scenes': [
        {'title': 'A scene', 'caption': 'A caption', 'narration': 'Same speech', 'duration_s': 10,
         'primitives': [{'type': 'text', 'text': str(i), 'x': .1, 'y': .1}]}
        for i in range(4)]}
    inputs, previews = [], []
    class Client:
        def chat(self, messages, **kwargs):
            inputs.append(json.loads(messages[1]['content'][0]['text']))
            i = len(inputs)-1
            return json.dumps({'replacements': [{'scene': i, 'primitives': [
                {**original['scenes'][i]['primitives'][0], 'y': .5}]}]})
    monkeypatch.setattr(agent, 'validate_plan', lambda p, c: None)
    monkeypatch.setattr(agent, 'inspect_layout', lambda p: (
        [{'scene': 1, 'kind': 'text_overlap'}] if p['scenes'][1]['primitives'][0]['y'] < .5 else []))
    def preview(plan, out):
        previews.append(copy.deepcopy(plan))
        return []
    monkeypatch.setattr(agent, 'evidence', preview)
    result, errors = agent.patch(Client(), {'id': 'x'}, original, feedback(), {'rules': []}, [], tmp_path, 'test')
    assert len(inputs) == 2 and len(errors) == 1 and len(previews) == 1
    assert inputs[1]['current_plan']['scenes'][0]['primitives'][0]['y'] == .5
    assert inputs[1]['frame_source'] == 'current_candidate_preview'
    assert [s['primitives'][0]['y'] for s in result['scenes']] == [.5, .5, .1, .1]
    assert all(s['primitives'][0]['y'] == .1 for s in original['scenes'])
    assert (tmp_path/'working_plan_0.json').exists()


def test_schema_invalid_patch_never_becomes_current_plan(monkeypatch, tmp_path):
    import json
    import localbench.visual_agent as agent
    original = {'case_id': 'x', 'scenes': [{'primitives': [{'type': 'text', 'text': 'old', 'x': .2, 'y': .2}]}]}
    inputs = []
    class Client:
        def chat(self, messages, **kwargs):
            inputs.append(json.loads(messages[1]['content'][0]['text']))
            if len(inputs) == 1:
                return json.dumps({'replacements': [{'scene': 0, 'primitives': [{'type': 'text', 'text': 'bad'}]}]})
            return json.dumps({'replacements': []})
    def invalid(*args): raise ValueError('invalid coordinates')
    monkeypatch.setattr(agent, 'validate_plan', invalid)
    result, errors = agent.patch(Client(), {'id': 'x'}, original, feedback(), {'rules': []}, [], tmp_path, 'test')
    assert result == original and len(errors) == 1
    assert inputs[1]['current_plan'] == original
    assert not (tmp_path/'working_plan_0.json').exists()


def test_identical_valid_patch_abstains_without_pressuring_a_second_change(tmp_path):
    import json
    import localbench.visual_agent as agent
    original = {'case_id': 'x', 'scenes': [{'primitives': [
        {'type': 'arrow', 'x': .2, 'y': .4, 'x2': .4, 'y2': .4},
        {'type': 'arrow', 'x': .8, 'y': .6, 'x2': .6, 'y2': .6}]}]}
    class Client:
        calls = 0
        def chat(self, *args, **kwargs):
            self.calls += 1
            assert self.calls == 1, 'A no-change proposal must not trigger another requested mutation'
            return json.dumps({'replacements': [{'scene': 0, 'primitives': original['scenes'][0]['primitives']}]})
    client = Client()
    result, errors = agent.patch(client, {'id': 'x'}, original, feedback(), {'rules': []}, [], tmp_path, 'test')
    assert client.calls == 1 and result == original and errors == []
    receipt = json.loads((tmp_path/'no_change.json').read_text())
    assert receipt['quality_acceptance'] is False
    assert receipt['feedback_issues_resolved'] is False


def test_noop_permission_still_rejects_invalid_or_protected_replacements():
    plan = {'case_id': 'x', 'scenes': [{'primitives': [{'type': 'text', 'text': 'Same'}]}]}
    raw = {'replacements': [{'scene': 0, 'primitives': copy.deepcopy(plan['scenes'][0]['primitives'])}]}
    assert apply_diagrams(plan, raw, allow_noop=True) == plan
    with pytest.raises(ValueError, match='no diagram change'):
        apply_diagrams(plan, raw)
    plan['scenes'][0]['state_visual'] = {'protected': True}
    with pytest.raises(ValueError, match='backends'):
        apply_diagrams(plan, raw, allow_noop=True)
    with pytest.raises(ValueError):
        apply_diagrams({'scenes': [{}]}, {'replacements': [{'scene': True, 'primitives': [{}]}]}, allow_noop=True)


def test_visibility_regression_is_rejected_without_poisoning_current_plan(monkeypatch,tmp_path):
    import json
    import localbench.visual_agent as agent
    original={'case_id':'x','scenes':[{'title':'Rising air','caption':'Observe the rising air.',
        'narration':'Air rises from the ocean surface.','duration_s':10,
        'primitives':[{'type':'arrow','x':.4,'y':.7,'x2':.4,'y2':.3,'color':'#666666'}]}]}
    inputs=[]
    class Client:
        def chat(self,messages,**kwargs):
            inputs.append(json.loads(messages[1]['content'][0]['text']))
            if len(inputs)==1:
                return json.dumps({'replacements':[{'scene':0,'primitives':[
                    {**original['scenes'][0]['primitives'][0],'color':'#ffffff'}]}]})
            return json.dumps({'replacements':[]})
    monkeypatch.setattr(agent,'validate_plan',lambda *args:None)
    result,errors=agent.patch(Client(),{'id':'x'},original,feedback(),{'rules':[]},[],tmp_path,'test')
    assert result==original and len(errors)==1
    assert 'new severe stroke visibility loss' in errors[0]['error']
    assert inputs[1]['current_plan']==original
    assert not (tmp_path/'working_plan_0.json').exists()
    assert json.loads((tmp_path/'stroke_visibility_0.json').read_text())['regressions']
