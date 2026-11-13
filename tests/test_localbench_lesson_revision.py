import copy
import pytest

from localbench.lesson_revision import apply_revision


def inputs():
    case = {'id': 'fixture', 'target_duration_s': 32}
    plan = {'case_id': 'fixture', 'scenes': [
        {'title': f'Part {i}', 'caption': 'A visible step.', 'slide_text': 'Step',
         'narration': 'A clear explanation of this visible step.', 'duration_s': 8,
         'primitives': [{'type': 'arrow', 'x': .3, 'y': .7, 'x2': .3, 'y2': .4, 'color': '#1868ae'}]}
        for i in range(4)], 'timing_compilation': {'stale': True}}
    scope = {'scene_indices': [0, 1], 'max_total_words': 60, 'objective': 'Explain the missing causal bridge.',
             'evidence': [{'id': 'S1', 'kind': 'public_reference', 'text': 'Public explanation.', 'source': 'fixture source'}]}
    raw = {'replacements': [{'scene': 0, 'updates': {'narration': 'Here is a more explicit explanation of this step.',
        'primitives': [{'type': 'arrow', 'x': .4, 'y': .7, 'x2': .4, 'y2': .3, 'color': '#1868ae'}]},
        'evidence_ids': ['S1'], 'reason': 'Add the requested bridge.'}]}
    return case, plan, scope, raw


def test_coupled_revision_preserves_unselected_scenes_timing_and_source_input():
    case, plan, scope, raw = inputs(); before = copy.deepcopy(plan)
    fixed, receipt = apply_revision(plan, raw, case, scope)
    assert plan == before
    assert fixed['scenes'][1:] == plan['scenes'][1:]
    assert fixed['scenes'][0]['duration_s'] == 8
    assert 'timing_compilation' not in fixed
    assert receipt['changed_scenes'] == [0] and receipt['semantic_acceptance'] == 'unverified'


@pytest.mark.parametrize('field,value', [('duration_s', 10), ('state_visual', {}), ('arithmetic_checks', [])])
def test_revision_cannot_overwrite_protected_fields(field, value):
    case, plan, scope, raw = inputs(); raw['replacements'][0]['updates'][field] = value
    with pytest.raises(ValueError, match='protected'): apply_revision(plan, raw, case, scope)


def test_fabricated_citations_unselected_scenes_and_uncoupled_changes_fail():
    for kind in ['citation', 'scene', 'coupling']:
        case, plan, scope, raw = inputs()
        if kind == 'citation': raw['replacements'][0]['evidence_ids'] = ['fabricated']
        elif kind == 'scene': raw['replacements'][0]['scene'] = 3
        else: del raw['replacements'][0]['updates']['narration']
        with pytest.raises(ValueError): apply_revision(plan, raw, case, scope)


def test_budget_and_compiled_backend_protection():
    case, plan, scope, raw = inputs(); scope['max_total_words'] = 20
    with pytest.raises(ValueError, match='word budget'): apply_revision(plan, raw, case, scope)
    case, plan, scope, raw = inputs(); plan['scenes'][0]['spoken_units'] = [{'text': 'timed'}]
    with pytest.raises(ValueError, match='compiled'): apply_revision(plan, raw, case, scope)


def test_empty_edit_preserves_exact_plan_and_is_not_semantic_acceptance():
    case, plan, scope, raw = inputs()
    candidate, receipt = apply_revision(plan, {'replacements': []}, case, scope)
    assert candidate == plan and receipt['status'] == 'unchanged'
    assert receipt['semantic_acceptance'] == 'unverified'


def test_copying_original_scene_is_not_counted_as_a_revision():
    case, plan, scope, raw = inputs()
    raw['replacements'][0]['updates'] = {k: copy.deepcopy(plan['scenes'][0][k]) for k in ['narration', 'primitives']}
    with pytest.raises(ValueError, match='unchanged replacement'): apply_revision(plan, raw, case, scope)
