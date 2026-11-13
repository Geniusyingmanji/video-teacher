import copy

import pytest
from localbench.stroke_visibility import inspect_visibility


def scene(parts):
    return {'title':'Air movement','caption':'Observe the arrow.',
            'narration':'Observe how the arrow represents movement.',
            'duration_s':10,'primitives':parts}


def arrow(**kw):
    return {'type':'arrow','x':.4,'y':.7,'x2':.4,'y2':.3,'color':'#ffffff',**kw}


def test_white_arrow_on_white_is_detected_without_mutating_source():
    s=scene([arrow()]);before=copy.deepcopy(s)
    rows=inspect_visibility(s,.5)
    assert len(rows)==1 and rows[0]['priority']=='nearly_invisible'
    assert rows[0]['contrast_median']==1 and rows[0]['fraction_below_1_5']==1
    assert s==before
    assert not inspect_visibility(scene([arrow(color='#1868ae')]),.5)


def test_same_white_arrow_is_visible_on_dark_background():
    bg={'type':'rect','x':.2,'y':.1,'w':.4,'h':.8,'color':'#14283e','fill':'#14283e'}
    assert not inspect_visibility(scene([bg,arrow()]),.5)


def test_appearance_motion_and_later_occlusion_are_respected():
    p=arrow(appear=.5,dx=.2)
    assert not inspect_visibility(scene([p]),.25)
    first=inspect_visibility(scene([p]),.5)[0]
    later=inspect_visibility(scene([p]),1)[0]
    assert later['bbox'][0]>first['bbox'][0]+170
    cover={'type':'rect','x':.1,'y':.1,'w':.8,'h':.8,'fill':'#ffffff','color':'#14283e'}
    assert not inspect_visibility(scene([p,cover]),1)


@pytest.mark.parametrize('kind',['line','arc','polyline'])
def test_supported_strokes_detected_and_closed_shapes_excluded(kind):
    p=arrow(type=kind)
    if kind=='arc':p.update(r=.15,start_angle=0,end_angle=180)
    if kind=='polyline':p.update(points=[[.2,.2],[.5,.5],[.8,.2]],closed=False)
    assert inspect_visibility(scene([p]),1)
    if kind=='polyline':
        p.update(closed=True,fill='#ffffff')
        assert not inspect_visibility(scene([p]),1)


def test_visible_dark_line_over_white_line_does_not_false_alarm_hidden_white():
    assert not inspect_visibility(scene([arrow(),arrow(color='#14283e')]),1)


def test_repair_changes_only_invisible_arrow_color_and_is_idempotent():
    from localbench.stroke_visibility import repair,sampled
    source={'scenes':[scene([arrow(appear=.2),{'type':'text','x':.6,'y':.4,'text':'Rising air','color':'#14283e'}])]}
    before=copy.deepcopy(source);result,receipt=repair(source)
    assert source==before and receipt['status']=='changed'
    old=source['scenes'][0]['primitives'][0];new=result['scenes'][0]['primitives'][0]
    assert {k:v for k,v in old.items() if k!='color'}=={k:v for k,v in new.items() if k!='color'}
    assert not sampled(result['scenes'][0])
    assert result['scenes'][0]['primitives'][1]==source['scenes'][0]['primitives'][1]
    assert result['scenes'][0]['narration']==source['scenes'][0]['narration']
    assert repair(result)[0]==result and repair(result)[1]['status']=='unchanged'


def test_repair_preserves_visible_white_on_dark_and_skips_moving_strokes():
    from localbench.stroke_visibility import repair
    bg={'type':'rect','x':.2,'y':.1,'w':.4,'h':.8,'color':'#14283e','fill':'#14283e'}
    for s in (scene([bg,arrow()]),scene([arrow(dx=.1)])):
        source={'scenes':[s]};out,receipt=repair(source)
        assert out==source and receipt['status']=='unchanged'


def test_repair_does_not_create_a_new_text_crossing_contrast_failure():
    from localbench.stroke_visibility import repair
    # The white arrow is invisible across a dark label; making it dark would
    # put dark stroke ink behind the label. Existing layout checks veto this.
    source={'scenes':[scene([arrow(),{'type':'text','x':.4,'y':.5,'text':'AIR','align':'center','color':'#14283e'}])]}
    out,receipt=repair(source)
    assert receipt['status']=='unchanged' and out==source


def test_new_visibility_guard_blocks_color_regression_but_allows_actual_improvement():
    from localbench.stroke_visibility import regression_report,validate_no_regression
    good={'scenes':[scene([arrow(color='#666666')])]}
    bad={'scenes':[scene([arrow()])]}
    with pytest.raises(ValueError,match='new severe stroke visibility loss'):
        validate_no_regression(regression_report(good,bad))
    assert not validate_no_regression(regression_report(bad,good))['regressions']
    assert not validate_no_regression(regression_report(bad,bad))['regressions']


def test_regression_matching_ignores_index_reordering_and_documents_deletion_limit():
    from localbench.stroke_visibility import regression_report
    text={'type':'text','x':.8,'y':.3,'text':'Air'}
    original={'scenes':[scene([arrow(),text])]}
    reordered={'scenes':[scene([text,arrow()])]}
    assert not regression_report(original,reordered)['regressions']
    assert not regression_report(original,{'scenes':[scene([text])]})['regressions']
