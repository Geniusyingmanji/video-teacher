import copy
import math

import pytest

from localbench.scene import render_frame, validate_plan
from localbench.triangle import compile_sequence
from localbench.triangle_examples import classify, compile_examples
from test_localbench_triangle import fixture


def test_opening_categories_match_rendered_coordinate_geometry_and_focus():
    source,_ = compile_sequence(fixture()); before = copy.deepcopy(source)
    result,receipt = compile_examples(source)
    assert receipt['status'] == 'compiled' and source == before
    assert result['scenes'][1:] == before['scenes'][1:]
    assert result['scenes'][0]['narration'] == before['scenes'][0]['narration']
    assert result['scenes'][0]['duration_s'] == before['scenes'][0]['duration_s']
    validate_plan(result, {'id':'triangle','target_duration_s':60})
    polygons = [p for p in result['scenes'][0]['primitives'] if p.get('closed')]
    assert len(polygons) == 3
    for p, expected in zip(polygons, ['Acute','Right','Obtuse']):
        points = [[64+x*896,112+y*302] for x,y in p['points']]
        # Independent side-length classification, after the real renderer map.
        sides = sorted(math.dist(points[i],points[(i+1)%3])**2 for i in range(3))
        delta = sides[2]-sides[0]-sides[1]
        actual = 'Right' if abs(delta)<1e-6 else 'Acute' if delta<0 else 'Obtuse'
        assert actual == expected and classify(points)[0] == expected
    first = receipt['examples'][0]['angles_degrees']
    assert first == pytest.approx(receipt['focus_angles_degrees'])
    for progress in (0,.5,1):
        _, findings = render_frame(result['scenes'][0],progress)
        assert findings == []


def test_opening_repair_rejects_unmatched_narration_or_geometry():
    source,_ = compile_sequence(fixture())
    for words in ('Here are two triangles.', 'An obtuse, right and acute triangle.', 'Look at this equilateral triangle.'):
        bad = copy.deepcopy(source); bad['scenes'][0]['narration'] = words
        result, receipt = compile_examples(bad)
        assert receipt['status'] == 'unsupported' and result == bad
    bad = copy.deepcopy(source)
    bad['scenes'][1]['state_visual']['state']['vertices'] = [[100,300],[500,300],[200,250]]
    assert compile_examples(bad)[1]['status'] == 'unsupported'
