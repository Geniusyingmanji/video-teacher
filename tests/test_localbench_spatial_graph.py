import copy
import math

import numpy as np
import pytest
from PIL import Image

from localbench.spatial_graph import compile_graph,draw_graph,projection

TASK='Show a tetrahedral carbon, with an approaching nucleophile on the opposite side of the leaving group.'

def graph():
    points={'C':[0,0,0],'LG':[1,0,0],
            'R1':[-1/3,math.sqrt(8)/3,0],
            'R2':[-1/3,-math.sqrt(2)/3,math.sqrt(6)/3],
            'R3':[-1/3,-math.sqrt(2)/3,-math.sqrt(6)/3],
            'Nu':[-1.7,0,0]}
    return {'nodes':[{'id':k,'label':k,'xyz':v} for k,v in points.items()],
            'links':[{'source':'C','target':k,'kind':'bond'} for k in ['LG','R1','R2','R3']]+[
                {'source':'Nu','target':'C','kind':'arrow','color':'#237943'}],
            'constraints':[
                {'kind':'tetrahedral','nodes':['C','LG','R1','R2','R3'],'prompt_quote':'tetrahedral carbon'},
                {'kind':'opposite_sides','nodes':['C','LG','Nu'],'prompt_quote':'opposite side'},
                {'kind':'directed_link','nodes':['Nu','C'],'prompt_quote':'approaching nucleophile'}],
            'camera':{'azimuth_deg':45,'elevation_deg':0}}


def test_regular_tetrahedron_and_antipodal_approach_are_checked():
    g=graph();before=copy.deepcopy(g);result=compile_graph(g,TASK)
    assert len(result['checks'][0]['cosines'])==6
    assert all(v==pytest.approx(-1/3) for v in result['checks'][0]['cosines'])
    assert result['checks'][1]['cosines'][0]==pytest.approx(-1)
    assert g==before


def test_planar_connectivity_alone_cannot_satisfy_tetrahedral_geometry():
    g=graph()
    for n in g['nodes']:n['xyz'][2]=0
    with pytest.raises(ValueError,match='unsatisfied.*tetrahedral'):
        compile_graph(g,TASK)


def test_same_side_approach_rejected_and_reversed_arrow_rejected():
    g=graph();g['nodes'][-1]['xyz']=[1.7,0,0]
    with pytest.raises(ValueError,match='opposite_sides'):compile_graph(g,TASK)
    g=graph();g['links'][-1].update(source='C',target='Nu')
    with pytest.raises(ValueError,match='directed_link'):compile_graph(g,TASK)


def test_rigid_rotation_and_translation_preserve_geometry_checks():
    g=graph();a=.8;rotation=np.array([[math.cos(a),0,math.sin(a)],[0,1,0],[-math.sin(a),0,math.cos(a)]])
    for n in g['nodes']:n['xyz']=(rotation@np.array(n['xyz'])+np.array([.2,.3,.1])).tolist()
    assert all(c['satisfied'] for c in compile_graph(g,TASK)['checks'])


def test_bad_ids_quotes_and_ignored_fields_are_rejected():
    for change,match in [(lambda g:g['links'][0].update(target='unknown'),'endpoints'),
                         (lambda g:g['constraints'][0].update(prompt_quote='private key'),'public-task'),
                         (lambda g:g['camera'].update(zoom=8),'camera'),
                         (lambda g:g['nodes'][0].update(xyz=[0,0,float('nan')]),'finite')]:
        g=graph();change(g)
        with pytest.raises(ValueError,match=match):compile_graph(g,TASK)


def test_two_views_change_projection_but_keep_world_coordinates():
    g=graph();before=copy.deepcopy(g);compile_graph(g,TASK)
    first,_=projection(g);other,_=projection(g,{'azimuth_deg':-45,'elevation_deg':0})
    assert not np.allclose(first['R2'][:2],other['R2'][:2])
    for camera in [None,{'azimuth_deg':-45,'elevation_deg':0}]:
        image=Image.new('RGB',(1024,576),'white');receipt=draw_graph(image,g,camera=camera)
        assert len([r for r in receipt['labels'] if 'node' in r])==6
        assert {'solid_wedge','hashed_wedge'}<={r['style'] for r in receipt['strokes']}
        assert np.count_nonzero(np.any(np.asarray(image)!=255,axis=2))>1000
    assert g==before


def test_camera_with_overlapping_unconnected_nodes_is_rejected():
    g=graph()
    with pytest.raises(ValueError,match='projected nodes overlap'):
        draw_graph(Image.new('RGB',(1024,576),'white'),g,camera={'azimuth_deg':0,'elevation_deg':0})


def test_spatial_labels_use_dark_ink_even_for_light_object_colors():
    g=graph()
    for n in g['nodes']:n['color']='#eeeeee'
    receipt=draw_graph(Image.new('RGB',(1024,576),'white'),g)
    labels=[r for r in receipt['labels'] if 'node' in r]
    assert all(r['label_color']=='#14283e' and r['object_color']=='#eeeeee' for r in labels)
    assert not receipt['layout_issues']


def test_spatial_contrast_findings_reach_scene_layout(monkeypatch):
    from localbench.scene import render_frame
    monkeypatch.setattr('localbench.layout_geometry.text_contrast',
                        lambda image,mask,color,record: [{'kind':'text_low_contrast','severity':'error',**record}])
    _,issues=render_frame({'title':'View','caption':'View','primitives':[{'type':'spatial_graph','graph':graph()}]},0)
    rows=[i for i in issues if i['kind']=='text_low_contrast']
    assert len(rows)==6 and all(i['primitive']==0 for i in rows)


def test_scene_compiles_only_validated_whole_panel_graph_and_layout_is_readable():
    from localbench.scene import validate_plan,inspect_layout
    s={'title':'Backside attack','caption':'Follow the attack arrow opposite the leaving group.',
       'slide_text':'Backside attack','narration':'The nucleophile approaches from opposite the leaving group.',
       'duration_s':10,'primitives':[{'type':'spatial_graph','graph':graph()}]}
    plan={'case_id':'x','scenes':[copy.deepcopy(s) for _ in range(4)]}
    validate_plan(plan,{'id':'x','prompt_text':TASK,'target_duration_s':40})
    assert not inspect_layout(plan)
    bad=copy.deepcopy(plan);bad['scenes'][0]['primitives'].append({'type':'text','x':.5,'y':.5,'text':'hidden'})
    with pytest.raises(ValueError,match='owns the diagram panel'):
        validate_plan(bad,{'id':'x','prompt_text':TASK,'target_duration_s':40})
