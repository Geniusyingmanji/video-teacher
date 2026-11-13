import copy

import numpy as np
from PIL import Image
import pytest

from localbench.spatial_correspondence import VERSION, compile_pair, draw_pair, geometry
from localbench.scene import render_frame, validate_plan
from localbench.spatial_view_narration import apply, view_facts
from test_localbench_spatial_inversion import pair


def spec():
    a,b,_=pair()
    return {'type':'spatial_correspondence','version':VERSION,'initial':a,'product':b,
            'roles':{'center':'c','leaving':'lg','incoming':'nu','retained':['r1','r2','r3']}}


def lesson():
    s={'title':'Compare the structures','caption':'Follow the matching groups.',
       'narration':'Compare the retained group labels before and after substitution.',
       'duration_s':10,'primitives':[spec()]}
    return {'case_id':'case','scenes':[copy.deepcopy(s) for _ in range(4)]}


CASE={'id':'case','prompt_text':'Tetrahedral substitution','target_duration_s':40}


def test_pair_has_common_metric_projection_and_separate_departure_cue():
    s=spec();compile_pair(s,CASE['prompt_text'])
    positions,_,r=geometry(s)
    initial_c=np.array(positions['initial']['c']);product_c=np.array(positions['product']['c'])
    axis=np.array(positions['initial']['lg'])-initial_c
    assert np.allclose(np.array(r['departure_position'])-product_c,2*axis)
    assert np.allclose(np.array(positions['product']['nu'])-product_c,-axis)
    assert len(s['product']['links'])==4 and 'lg' not in {n['id'] for n in s['product']['nodes']}


@pytest.mark.parametrize('change',['renamed','different_camera','new_bond'])
def test_pair_rejects_false_identity_and_camera_or_topology_changes(change):
    s=spec()
    if change=='renamed':next(n for n in s['product']['nodes'] if n['id']=='r3')['label']='R2'
    elif change=='different_camera':s['product']['camera']['azimuth_deg']+=15
    else:s['product']['links'].append({'source':'r1','target':'r2','kind':'bond'})
    with pytest.raises(ValueError):compile_pair(s,CASE['prompt_text'])


def test_render_keeps_both_panels_and_depth_examples_visible_without_layout_overlap():
    p=lesson();validate_plan(p,CASE)
    im,issues=render_frame(p['scenes'][3],.5,index=3,total=4,mode='code')
    assert not issues
    r=draw_pair(Image.new('RGB',im.size,'white'),spec())
    assert {'initial','product'}=={e['phase'] for e in r['strokes']}
    assert any(e['phase']=='product' and e['target']=='r3' and e['style'] in {'solid_wedge','hashed_wedge'} for e in r['strokes'])
    assert {'Solid: toward you','Hashed: away'}<={x['text'] for x in r['labels']}
    assert any(x.get('phase')=='departed' for x in r['labels'])


def test_view_binding_exposes_each_panel_and_rejects_geometry_rewrites():
    p=lesson();facts=view_facts(p,CASE,[3]);before=copy.deepcopy(p)
    assert {'initial','product'}=={v['phase'] for v in facts.values() if 'phase' in v}
    raw={'edits':[{'scene':3,'text':{'narration':'Match the retained groups in the two diagrams.'},
                   'fact_ids':['S3.correspondence'],'reason':'Explain visible correspondence.'}]}
    changed,_=apply(p,CASE,raw,[3],facts,scene_word_limits={3:32})
    assert p==before and changed['scenes'][3]['primitives']==p['scenes'][3]['primitives']
    raw['edits'][0]['text']['primitives']=[]
    with pytest.raises(ValueError):apply(p,CASE,raw,[3],facts)


def test_text_uses_actual_ligand_labels():
    s=spec()
    for phase in ['initial','product']:
        for n in s[phase]['nodes']:
            if n['id']=='r3':n['label']='Me'
            if n['id']=='lg':n['label']='Cl'
    compile_pair(s,CASE['prompt_text'])
    r=draw_pair(Image.new('RGB',(1024,576),'white'),s)
    texts={x['text'] for x in r['labels']}
    assert 'Product + departing Cl' in texts
    assert any(t.endswith('Me.') for t in texts)
