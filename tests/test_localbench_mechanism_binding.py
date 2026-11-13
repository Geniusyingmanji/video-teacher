import copy

import pytest

from localbench.common import digest
from localbench.mechanism_binding import bind_extractive, inspect_binding


def fixture():
    scene = {'title': 'Heat transfer', 'caption': 'Existing caption.', 'duration_s': 4,
             'narration': 'Conduction transfers heat to water and causes ascent.',
             'primitives': [{'type': 'circle', 'x': .2, 'y': .5, 'r': .1}]}
    plan = {'case_id': 'fixture', 'scenes': [scene, copy.deepcopy(scene)]}
    return plan, {'plan_hash': digest(plan), 'scene': 0, 'replace_indices': []}


def test_free_region_preserves_original_plan_and_non_target_fields():
    plan, binding = fixture(); old = copy.deepcopy(plan)
    quote = 'Conduction transfers heat.'
    refs = [{'id': 'S1', 'kind': 'public_reference', 'text': quote}]
    raw = {'process': 'Conduction', 'transfer': 'heat', 'recipient': 'water',
           'state_change': None, 'outcome': 'ascent', 'links': [
               {'explanation': 'Fixture only.', 'evidence_ids': ['S1'], 'source_quote': quote} for _ in range(2)]}
    out, receipt = bind_extractive(plan, binding, raw, refs)
    assert plan == old and receipt['status'] == 'bound'
    assert receipt['semantic_acceptance'] == 'unverified'
    assert out['scenes'][1] == old['scenes'][1]
    assert out['scenes'][0]['primitives'][0] == old['scenes'][0]['primitives'][0]
    assert {k: v for k, v in out['scenes'][0].items() if k != 'primitives'} == {
        k: v for k, v in old['scenes'][0].items() if k != 'primitives'}


def test_moving_preserved_object_is_checked_beyond_first_frame():
    plan, binding = fixture()
    plan['scenes'][0]['primitives'][0]['dx'] = .6
    binding['plan_hash'] = digest(plan)
    r = inspect_binding(plan, binding)
    assert r['reason'] == 'preserved_diagram_occupies_region' and r['frame'] > 0


@pytest.mark.parametrize('key', ['state_visual', 'source_visual', 'spoken_units', 'nephron_path'])
def test_protected_backends_never_receive_silently_invisible_primitives(key):
    plan, binding = fixture(); plan['scenes'][0][key] = {}
    binding['plan_hash'] = digest(plan)
    assert inspect_binding(plan, binding)['reason'] == 'protected_scene_backend'


def test_explicit_deletion_cannot_remove_left_spatial_diagram():
    plan, binding = fixture(); binding['replace_indices'] = [0]
    assert inspect_binding(plan, binding)['reason'] == 'replacement_would_remove_outside_region'


def test_a_source_edit_invalidates_binding():
    plan, binding = fixture(); plan['scenes'][1]['caption'] = 'Changed.'
    with pytest.raises(ValueError, match='different source'):
        inspect_binding(plan, binding)


def test_frame_count_uses_encoder_cumulative_boundaries():
    plan, binding = fixture()
    plan['scenes'][0]['duration_s'] = 4.04
    plan['scenes'][1]['duration_s'] = 4.04
    binding.update(plan_hash=digest(plan), scene=1)
    assert inspect_binding(plan, binding)['checked_frames_including_terminal'] == 50


def test_late_appearing_object_also_blocks_insertion():
    plan, binding = fixture()
    plan['scenes'][0]['primitives'].append({'type': 'text', 'x': .7, 'y': .5,
        'text': 'Do not cover this', 'appear': .95})
    binding['plan_hash'] = digest(plan)
    assert inspect_binding(plan, binding)['reason'] == 'preserved_diagram_occupies_region'


def test_unsupported_extraction_does_not_create_a_video_plan():
    plan, binding = fixture()
    out, receipt = bind_extractive(plan, binding, {'unsupported': 'No supported transfer.'}, [])
    assert out is None and receipt['status'] == 'not_applicable'
