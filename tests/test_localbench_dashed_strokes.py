import copy
import math

import numpy as np
from PIL import Image, ImageDraw
import pytest

from localbench.scene import render_frame, validate_plan
from localbench.stroke_preflight import inspect_strokes
from localbench.stroke_style import draw_linear


def line(**extra):
    return {'type': 'line', 'x': (100-64)/896, 'y': (213-112)/302,
            'x2': (940-64)/896, 'y2': (213-112)/302,
            'color': '#000000', 'stroke': 10, **extra}


def scene(parts):
    return {'title': 'Bond representation', 'caption': 'Compare the strokes.',
            'slide_text': 'Compare the strokes.', 'narration': 'Compare these two different line representations.',
            'duration_s': 10, 'primitives': parts}


@pytest.mark.parametrize('kind', ['line', 'arrow'])
def test_solid_strokes_preserve_legacy_pixels(kind):
    p = line(type=kind); xy = (30,40,180,130)
    old = Image.new('RGB',(220,180),'white'); d = ImageDraw.Draw(old)
    d.line(xy,fill='#000000',width=10)
    if kind == 'arrow':
        x,y,x2,y2=xy; a=math.atan2(y2-y,x2-x)
        d.polygon([(x2,y2),(x2-12*math.cos(a-.5),y2-12*math.sin(a-.5)),
                   (x2-12*math.cos(a+.5),y2-12*math.sin(a+.5))],fill='#000000')
    for dash in (None, False):
        p2 = dict(p)
        if dash is not None: p2['dash'] = dash
        new = Image.new('RGB',old.size,'white')
        draw_linear(ImageDraw.Draw(new),p2,xy)
        assert np.array_equal(np.asarray(old),np.asarray(new))


@pytest.mark.parametrize('kind', ['line', 'arrow'])
def test_encoded_scene_has_real_gaps_and_keeps_arrowhead(kind):
    s = scene([line(type=kind,dash=True)])
    original = copy.deepcopy(s)
    image = np.asarray(render_frame(s,.5)[0])
    # First authored30px stroke and following20px gap, in actual panel pixels.
    assert (image[213,110] == 0).all()
    assert (image[213,140] == 255).all()
    assert (image[213,160] == 0).all()
    if kind == 'arrow':
        assert (image[213,940] == 0).all()
        assert (image[211,935] == 0).all()
    assert s == original


def test_preflight_uses_visible_dash_ink_not_a_fictitious_solid_line():
    label = {'type':'text','x':(140-64)/896,'y':(213-112)/302,
             'text':'I','font_size':30,'align':'center','color':'#000000'}
    dashed = scene([label,line(dash=True)])
    solid = scene([label,line(dash=False)])
    assert not inspect_strokes(dashed,.5)
    assert inspect_strokes(solid,.5)


@pytest.mark.parametrize('bad', ['true', 1, None, [10,6]])
def test_bad_dash_type_is_rejected_instead_of_silently_ignored(bad):
    plan = {'case_id':'test','scenes':[scene([line(dash=bad)]) for _ in range(4)]}
    with pytest.raises(ValueError,match='dash must be boolean'):
        validate_plan(plan,{'id':'test','target_duration_s':40})


def test_dash_on_unsupported_shape_is_rejected():
    plan = {'case_id':'test','scenes':[scene([
        {'type':'circle','x':.5,'y':.5,'r':.1,'dash':True}]) for _ in range(4)]}
    with pytest.raises(ValueError,match='only on line/arrow'):
        validate_plan(plan,{'id':'test','target_duration_s':40})
