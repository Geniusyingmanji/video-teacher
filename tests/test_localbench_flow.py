import math

import numpy as np
import pytest

from localbench.flow import compile_flow,path_intersects_box
from localbench.scene import render_frame,validate_plan


def flow():
    return {'type':'flow_path','x':.5,'y':.5,'radius_start':.4,'radius_end':.09,'turns':1,'rotation':'ccw'}


def test_spiral_is_inward_counterclockwise_and_pixel_isotropic():
    c=compile_flow(flow());cx,cy=c['center'];points=c['points']
    radii=[math.hypot(x-cx,y-cy) for x,y in points]
    assert all(a>b for a,b in zip(radii,radii[1:]))
    assert radii[0]==pytest.approx(.4*302) and radii[-1]==pytest.approx(.09*302)
    # Starting at the rightmost ray, mathematical CCW moves upward on the screen.
    assert points[1][1]<points[0][1]
    clockwise=compile_flow({**flow(),'rotation':'cw'})
    assert clockwise['points'][1][1]>clockwise['points'][0][1]
    circle=compile_flow({**flow(),'radius_end':.4})
    xs,ys=zip(*circle['points'])
    assert max(xs)-min(xs)==pytest.approx(max(ys)-min(ys),abs=.1)


def test_flow_is_visible_moves_and_rejects_unbounded_or_ambiguous_inputs():
    scene={'title':'Schematic flow','caption':'Qualitative inward flow.','primitives':[flow()]}
    a,issues=render_frame(scene,0);b,_=render_frame(scene,.2)
    assert not issues and np.any(np.asarray(a)!=np.asarray(b))
    for patch in ({'radius_start':float('nan')},{'x':.01},{'rotation':'maybe'},{'markers':True},{'dx':.1}):
        with pytest.raises(ValueError):compile_flow({**flow(),**patch})


def test_flow_integrates_into_existing_declarative_plan_validation():
    scene={'title':'Flow','caption':'Directed flow.','narration':'Air flows inward along these spiral paths.',
           'duration_s':15,'primitives':[flow()]}
    validate_plan({'case_id':'x','scenes':[scene]*4},{'id':'x','target_duration_s':60})
    for key in ('x','y'):
        missing=flow();missing.pop(key)
        scene['primitives']=[missing]
        with pytest.raises(ValueError,match='explicit x and y'):
            validate_plan({'case_id':'x','scenes':[scene]*4},{'id':'x','target_duration_s':60})


def test_flow_text_check_uses_segments_and_preserves_clear_center_labels():
    p={**flow(),'radius_end':.2}
    scene={'title':'Spiral','caption':'Qualitative flow.','primitives':[
        p,{'type':'text','x':.5,'y':.5,'text':'Eye','align':'center'}]}
    _,issues=render_frame(scene,.2)
    assert not issues
    scene['primitives'][1].update(x=.5+.4*302/896,text='Here')
    _,issues=render_frame(scene,.2)
    assert any(x['kind']=='flow_text_overlap' for x in issues)
    assert path_intersects_box([[0,0],[10,10]],[4,4,6,6],0)
    assert not path_intersects_box([[0,0],[10,10]],[1,8,2,9],0)
