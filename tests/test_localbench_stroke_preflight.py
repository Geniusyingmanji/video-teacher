import copy

import pytest
from localbench.scene import inspect_layout
from localbench.stroke_preflight import inspect_strokes


def text(x=220, y=200, label='123456789', **extra):
    return {'type': 'text', 'x': (x-64)/896, 'y': (y-112)/302,
            'text': label, 'font_size': 30, **extra}


def line(x1=200, y1=214, x2=450, y2=214, **extra):
    return {'type': 'line', 'x': (x1-64)/896, 'y': (y1-112)/302,
            'x2': (x2-64)/896, 'y2': (y2-112)/302, 'stroke': 4, **extra}


def scene(parts):
    return {'title': 'Check amounts', 'caption': 'Read the amount carefully.',
            'narration': 'Read the amount carefully.', 'duration_s': 10, 'primitives': parts}


@pytest.mark.parametrize('stroke_first', [False, True])
def test_actual_ink_crossing_detected_in_both_draw_orders(stroke_first):
    parts = [text(), line()]
    if stroke_first: parts.reverse()
    findings = inspect_strokes(scene(parts), 1)
    assert len(findings) == 1
    assert findings[0]['overlap_ink_pixels'] > 5
    assert findings[0]['severity'] == ('warning' if stroke_first else 'error')


def test_nearby_underline_leader_and_whitespace_are_not_glyph_collisions():
    for stroke in (line(y1=235,y2=235), line(x1=100,x2=211),
                   line(x1=259,y1=190,x2=259,y2=230)):
        # Last stroke is in the spaces between two glyphs, inside the text bbox.
        label = 'A     B' if stroke['x'] == (259-64)/896 else '123456789'
        assert not inspect_strokes(scene([text(label=label), stroke]), 1)


def test_later_opaque_shape_removes_hidden_stroke_but_unfilled_shape_does_not():
    cover = {'type': 'rect', 'x': (190-64)/896, 'y': (185-112)/302,
             'w': 280/896, 'h': 65/302, 'fill': '#ffffff'}
    assert not inspect_strokes(scene([line(), cover, text()]), 1)
    assert not inspect_strokes(scene([text(), line(), cover]), 1)
    cover['fill'] = None
    assert inspect_strokes(scene([line(), cover, text()]), 1)


def test_appearance_translation_and_layout_integration():
    moving = line(appear=.5, dy=70/302)
    s = scene([text(), moving]); before = copy.deepcopy(s)
    assert not inspect_strokes(s, .25)
    assert inspect_strokes(s, .5)
    assert not inspect_strokes(s, 1)
    findings = inspect_layout({'scenes': [s]}, include_warnings=True)
    selected = [x for x in findings if x['kind'] == 'text_stroke_intersection']
    assert selected and all(x['mode'] == 'code' for x in selected)
    assert s == before


@pytest.mark.parametrize('kind', ['arrow','polyline','arc'])
def test_supported_stroke_shapes_use_their_drawn_paths(kind):
    stroke = line(type=kind)
    if kind == 'polyline':
        stroke['points'] = [[stroke['x'],stroke['y']], [stroke['x2'],stroke['y2']]]
    elif kind == 'arc':
        # Upper semicircle crosses the number interiors around its top.
        stroke.update(x=(310-64)/896, y=(275-112)/302, r=65/302,
                      start_angle=180, end_angle=360)
    assert inspect_strokes(scene([text(), stroke]), 1)


def test_generation_hints_use_only_the_supplied_frame_progress_and_id():
    from localbench.visual_agent import stroke_hints
    plan = {'scenes': [scene([text(), line(appear=.5,dy=70/302)])]}
    records = [{'id': 'before', 'scene': 0, 'progress': .25},
               {'id': 'crossing', 'scene': 0, 'progress': .5},
               {'id': 'after', 'scene': 0, 'progress': 1}]
    hints = stroke_hints(plan, records)
    assert len(hints) == 1
    assert hints[0]['candidate_evidence_id'] == 'crossing'
    assert hints[0]['progress'] == .5
