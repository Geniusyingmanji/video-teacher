import copy
import json

import pytest
from PIL import Image
import numpy as np

from localbench.common import ROOT
from localbench.scene import render_frame
from localbench.teaching_cues import POLICY, bind, caption, state_at, validate


def scene(kind='triangle_sum', phase='rearrange'):
    return {'title': 'Moving angles', 'caption': 'Pieces moved to a common vertex.',
            'duration_s': 10, 'narration': 'Move these three angles without changing their size.',
            'primitives': [{'type': 'text', 'text': 'placeholder', 'x': .1, 'y': .1}],
            'state_visual': {'state': {'kind': kind}, 'phase': phase}}


def test_completion_language_uses_same_clock_as_geometry():
    original = {'scenes': [scene()]}
    plan = bind(original); s = plan['scenes'][0]
    assert 'teaching_cues' not in original['scenes'][0]
    for t in [0, .1, .3, .719]:
        assert state_at(s, t)[1] < 1
        assert 'now meet' not in caption(s, t)
    for t in [.72, .85, 1]:
        assert state_at(s, t)[1] == 1
        assert 'now meet' in caption(s, t)
    # Holding the completed diagram changes only the footer progress marker.
    a, _ = render_frame(s, .72)
    b, _ = render_frame(s, .95)
    assert a.crop((28, 87, 996, 447)).tobytes() == b.crop((28, 87, 996, 447)).tobytes()


def test_legacy_scenes_and_narration_are_preserved():
    s = scene(); before = copy.deepcopy(s)
    assert state_at(s, .6) == (s['state_visual'], .6)
    assert caption(s, .6) == before['caption']
    result = bind({'scenes': [s]})['scenes'][0]
    assert {k: v for k, v in result.items() if k != 'teaching_cues'} == before


def test_invalid_motion_window_rejected():
    for change in [{'motion_end': .05}, {'motion_start': float('nan')}, {'version': 'untrusted'}]:
        with pytest.raises(ValueError): validate({**POLICY, **change})


def test_equation_render_shows_operations_on_both_sides():
    s = scene('linear_equation', 'subtract')
    s['state_visual']['state'].update(a=3, b=-4, c=11, solution='5')
    s = bind({'scenes': [s]})['scenes'][0]
    from localbench.state import draw_state
    spec, progress = state_at(s, .5)
    inspection = draw_state(Image.new('RGB', (1024, 576)), spec, progress)
    text = json.dumps(inspection, ensure_ascii=False)
    assert '3x − 4 − (-4)  =  11 − (-4)' in text
    assert '3x = 15' in text
    assert 'BOTH' in caption(s, .5)


def test_countable_particle_layout_preserves_visible_electron_counts():
    from collections import deque
    def count_blue(region):
        pixels = np.asarray(region)
        mask = (pixels[:, :, 0] < 90) & (pixels[:, :, 1] > 70) & (pixels[:, :, 2] > 130)
        seen = set(); components = 0
        for y, x in zip(*np.where(mask)):
            if (y, x) in seen: continue
            queue = deque([(y, x)]); seen.add((y, x)); size = 0
            while queue:
                yy, xx = queue.popleft(); size += 1
                for dy, dx in [(0,1),(0,-1),(1,0),(-1,0)]:
                    p = (yy+dy, xx+dx)
                    if 0 <= p[0] < mask.shape[0] and 0 <= p[1] < mask.shape[1] and mask[p] and p not in seen:
                        seen.add(p); queue.append(p)
            if size > 20: components += 1
        return components
    for phase, expected in [('neutral', [11,17]), ('ions', [10,18]), ('check', [10,18])]:
        s = scene('electron_transfer', phase)
        s = bind({'scenes': [s]}, countable_particles=True)['scenes'][0]
        image, issues = render_frame(s, .8)
        assert issues == []
        assert [count_blue(image.crop(box)) for box in [(160,150,400,355),(620,150,854,355)]] == expected


def test_trajectory_check_detects_old_collision_and_new_label_clears_every_rendered_step():
    s = scene('electron_transfer', 'transfer')
    old = bind({'scenes':[s]}, countable_particles=True)['scenes'][0]
    new = bind({'scenes':[s]}, countable_particles=True, clear_particle_labels=True)['scenes'][0]
    _, defects = render_frame(old, .35)
    assert any(d['kind']=='moving_object_text_overlap' and d['text']=='one electron →' for d in defects)
    for i in range(99):
        _, defects = render_frame(new, i/98)
        assert not defects
    assert new['narration'] == old['narration']
