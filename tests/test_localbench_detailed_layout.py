import copy

import pytest
from PIL import Image

from localbench.layout_audit import build_views,validate_observations
from localbench.layout_geometry import blocking_issues
from localbench.rubric import DIMENSIONS,validate_scores
from localbench.scene import render_frame,inspect_layout


def scene():
    return {'title':'Label control','caption':'A readable label','primitives':[
        {'type':'rect','x':.25,'y':.3,'w':.45,'h':.3,'color':'#1868ae','fill':'#eef8ff'},
        {'type':'text','x':.475,'y':.45,'align':'center','text':'VERB (was chased)','font_size':26,'color':'#14283e'}]}


def test_container_overflow_detected_without_rejecting_inferred_association():
    clean=scene();assert render_frame(clean,0)[1]==[]
    bad=copy.deepcopy(clean);bad['primitives'][0].update(x=.42,w=.1)
    _,issues=render_frame(bad,0)
    assert any(i['kind']=='text_container_overflow' for i in issues)
    assert not blocking_issues(issues)
    assert inspect_layout({'scenes':[bad]},include_warnings=True)
    external=scene();external['primitives'][1]['y']=.8
    assert not any('container' in i['kind'] for i in render_frame(external,0)[1])


def test_local_contrast_uses_background_under_glyphs():
    light=scene();light['primitives'][1]['color']='#eaf3fa'
    assert any(i['kind']=='text_low_contrast' and i['fraction_below_3']>.9 for i in render_frame(light,0)[1])
    dark=scene();dark['primitives'][0]['fill']='#14283e';dark['primitives'][1]['color']='#ffffff'
    assert not any(i['kind']=='text_low_contrast' for i in render_frame(dark,0)[1])


def test_later_fill_covering_existing_glyphs_is_reported():
    occluded=scene();occluded['primitives'].append({'type':'rect','x':.4,'y':.3,'w':.12,'h':.3,'fill':'#1868ae'})
    assert any(i['kind']=='text_occluded_by_later_shape' for i in render_frame(occluded,0)[1])
    safe=scene();safe['primitives'].append({'type':'rect','x':.01,'y':.7,'w':.1,'h':.1,'fill':'#1868ae'})
    assert not any(i['kind']=='text_occluded_by_later_shape' for i in render_frame(safe,0)[1])


def test_half_scores_supported_but_out_of_range_and_false_precision_rejected():
    dims={d:{'criteria':{k:{'status':'observed','score':3.5,'reason':'specific fixture','evidence_ids':['F00']}
            for k in spec['criteria']}} for d,spec in DIMENSIONS.items()}
    assert all(v['score']==62.5 for v in validate_scores({'dimensions':dims},{'F00'}).values())
    for invalid in (3.1,True,float('inf'),float('nan'),0,5.5):
        bad=copy.deepcopy(dims);bad['visual_quality']['criteria']['contrast']['score']=invalid
        with pytest.raises(ValueError):validate_scores({'dimensions':bad},{'F00'})


def test_crop_mapping_covers_native_edges_and_reports_original_coordinates(tmp_path):
    im=Image.new('RGB',(100,60),'white');im.putpixel((0,0),(0,0,0));im.putpixel((99,59),(0,0,0))
    path=tmp_path/'frame.png';im.save(path)
    records=build_views({'frames':[{'id':'F00','time_s':2,'path':str(path)}]},tmp_path/'views')
    a,b=records[0]['crops']
    assert a['bbox_native']==[0,0,65,60] and b['bbox_native']==[35,0,100,60]
    raw={'frames':[{'frame_id':'F00','issues':[{'kind':'container_overflow','severity':'minor',
        'bbox':[1,1,80,50],'affected_text':'label','observation':'label crosses its small box'}]}]}
    assert validate_observations(raw,records)
    raw['frames'][0]['issues'][0]['bbox']=[1,1,101,50]
    with pytest.raises(ValueError,match='original frame'):validate_observations(raw,records)
    raw={'frames':[{'frame_id':'F01','issues':[]}]}
    with pytest.raises(ValueError,match='frame ID'):validate_observations(raw,records)


def test_real_final_video_small_containers_are_localized_without_scene_metadata():
    from pathlib import Path
    from localbench.pixel_regions import rectangular_regions
    image=Image.open(Path(__file__).parent/'fixtures/layout_language_overflow.jpg')
    regions=rectangular_regions(image)
    # The green VERB box in a previously missed real failure, located from final pixels only.
    assert any(max(abs(x-y) for x,y in zip(box,[467,218,603,294]))<=3 for box in regions)
    assert len(regions)==3


def test_multiline_text_that_actually_fits_circle_is_not_rejected_by_empty_bbox_corners():
    sample={'title':'A circular node','caption':'Two lines inside a circular node.','primitives':[
        {'type':'circle','x':.3,'y':.5,'r':.15,'fill':'#eef8ff'},
        {'type':'text','x':.3,'y':.5,'align':'center','text':'DOER\n(Cat)','font_size':24,'color':'#14283e'}]}
    assert not any(i['kind']=='text_container_overflow' for i in render_frame(sample,0)[1])


def test_layout_array_envelope_normalization_keeps_observations_unchanged():
    records=[{'frame':{'id':'F00'},'native_size':[1024,576]}]
    raw=[{'frame_id':'F00','issues':[]}]
    assert validate_observations(raw,records)==raw
    with pytest.raises(ValueError):validate_observations(raw*2,records)


def test_human_ratings_accept_integer_levels_and_reject_false_precision():
    from localbench.human import rating_task,validate_rating
    from tests.test_localbench_human import response
    task=rating_task({'prompt_text':'A task'},'v1','r1','study')
    assert validate_rating(response(task,3),task)
    with pytest.raises(ValueError):validate_rating(response(task,3.5),task)
    with pytest.raises(ValueError):validate_rating(response(task,3.1),task)
