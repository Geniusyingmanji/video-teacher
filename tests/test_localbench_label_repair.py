import copy
import colorsys

from PIL import ImageColor

from localbench.label_repair import repair
from localbench.scene import inspect_layout


def scene(parts):
    return {'title':'A diagram','caption':'Read the labels.','narration':'The same explanation is preserved throughout.',
            'duration_s':10,'primitives':parts}


def test_crossing_moves_label_and_preserves_scientific_geometry_and_speech():
    s=scene([{'type':'arrow','x':.1,'y':.5,'x2':.5,'y2':.5},
             {'type':'text','x':.2,'y':.45,'text':'High P','font_size':24,'color':'#14283e'}])
    original={'scenes':[s]};before=copy.deepcopy(original)
    out,receipt=repair(original)
    assert original==before and receipt['status']=='changed'
    assert out['scenes'][0]['primitives'][0]==s['primitives'][0]
    assert out['scenes'][0]['narration']==s['narration']
    assert out['scenes'][0]['primitives'][1]['text']=='High P'
    assert abs(out['scenes'][0]['primitives'][1]['y']-.45)*302<=24
    assert not any(i['kind']=='text_stroke_intersection' for i in inspect_layout(out,include_warnings=True))


def test_low_contrast_darkens_hue_without_changing_text_or_shape():
    s=scene([{'type':'rect','x':.2,'y':.2,'w':.5,'h':.5,'fill':'#d5f5e3','color':'#27ae60'},
             {'type':'text','x':.4,'y':.4,'text':'FACT','color':'#27ae60'}])
    out,r=repair({'scenes':[s]});p=out['scenes'][0]['primitives'][1]
    assert p['color']!='#27ae60' and p['text']=='FACT'
    hue=lambda c:colorsys.rgb_to_hsv(*(x/255 for x in ImageColor.getrgb(c)))[0]
    assert abs(hue(p['color'])-hue('#27ae60'))<.01
    assert not any(i['kind']=='text_low_contrast' and i.get('primitive')==1 for i in r['after'])
    assert out['scenes'][0]['primitives'][0]==s['primitives'][0]


def test_locked_or_animated_labels_are_not_silently_moved():
    s=scene([{'type':'line','x':.1,'y':.5,'x2':.5,'y2':.5},
             {'type':'text','x':.2,'y':.45,'text':'Moving','dy':.1}])
    p={'scenes':[s]};out,r=repair(p)
    assert out==p and not r['edits']
    s['bond_cashflows']={'version':'protected'}
    assert repair(p)[0]==p


def test_method_keeps_rendered_label_stage_if_later_stroke_stage_and_review_fail(monkeypatch,tmp_path):
    import json
    import localbench.pipeline as pipeline
    import localbench.rerender as rerender
    import localbench.visual_agent as agent
    import localbench.stroke_visibility as visibility
    from localbench.run import improve
    s=scene([{'type':'arrow','x':.1,'y':.5,'x2':.5,'y2':.5},
             {'type':'text','x':.2,'y':.45,'text':'High P','font_size':24,'color':'#14283e'}])
    p={'case_id':'fixture','scenes':[copy.deepcopy(s) for _ in range(4)]}
    for item in p['scenes']:
        item['arithmetic_checks']=[]
    source=tmp_path/'original';source.mkdir();(source/'plan.json').write_text(json.dumps(p))
    artifact={'mode':'code','video_path':str(source/'code.mp4'),'sha256':'source'}
    rendered={'mode':'code','video_path':str(tmp_path/'new/code.mp4'),'sha256':'new'}
    monkeypatch.setattr(pipeline,'encode',lambda *args,**kwargs:rendered)
    monkeypatch.setattr(rerender,'decoded_audio_hash',lambda *args:'same')
    monkeypatch.setattr(agent,'evidence',lambda *args,**kwargs:[])
    def fail(*args,**kwargs):raise ValueError('invalid feedback schema')
    monkeypatch.setattr(agent,'review',fail)
    monkeypatch.setattr(visibility,'repair',fail)
    result=improve({'id':'fixture','prompt_text':'Describe this diagram.','target_duration_s':40},
                   {'artifacts':[artifact]},tmp_path/'repair',None)
    assert result['artifacts']==[rendered] and result['original_artifacts']==[artifact]
    assert result['visual_repair']['status']=='review_failed'
    assert result['label_repair']['decoded_audio_identical']
    assert result['preflight_repair_failures'][0]['stage']=='stroke_visibility_repair'
    assert result['visual_repair']['retained_stage'].startswith('rendered_label_repair')
    assert json.loads((source/'plan.json').read_text())==p
