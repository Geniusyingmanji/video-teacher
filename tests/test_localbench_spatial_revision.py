import copy

import pytest

from localbench.spatial_revision import apply
from test_localbench_spatial_plan import case, lesson
from test_localbench_spatial_solver import symbolic
from test_localbench_spatial_graph import TASK


def inputs():
    plan = lesson()
    plan['scenes'][1] = copy.deepcopy(plan['scenes'][0])
    row = {'scene': 1, 'scope_quote': TASK, 'reason': 'Show the declared spatial approach.',
           'text': {'narration': 'The nucleophile approaches carbon opposite the leaving group.'},
           'spec': symbolic()}
    return plan, {'replacements': [row]}


def test_revision_constructs_without_touching_other_scenes_or_input():
    plan, raw = inputs()
    before = copy.deepcopy(plan)
    result, receipt = apply(plan, case(), raw, [1])
    assert plan == before
    assert receipt['changed_scenes'] == [1]
    assert result['scenes'][1]['primitives'][0]['type'] == 'spatial_graph'
    assert all(result['scenes'][i] == before['scenes'][i] for i in [0, 2, 3])
    assert all(c['satisfied'] for c in receipt['geometry']['constructions'][0]['compiled']['checks'])


@pytest.mark.parametrize('defect', ['scope', 'long_label', 'coordinates', 'protected', 'contradiction'])
def test_revision_rejects_scope_and_geometry_failures(defect):
    plan, raw = inputs()
    row = raw['replacements'][0]
    if defect == 'scope': row['scene'] = 2
    if defect == 'long_label': row['spec']['nodes'][0]['label'] = 'Carbon'
    if defect == 'coordinates': row['spec']['nodes'][0]['xyz'] = [0, 0, 0]
    if defect == 'protected': plan['scenes'][1]['source_visual'] = {'path': 'protected'}
    if defect == 'contradiction': row['spec']['links'][-1].update(source='C', target='Nu')
    with pytest.raises(ValueError):
        apply(plan, case(), raw, [1])
