import copy
import wave

import pytest

from test_localbench_keyboard import fixture
from localbench.keyboard_bridge import bind,bind_timing,compile_walk,key_positions,snapshot,COLOR
from localbench.scene import render_frame,validate_plan
from localbench.spoken_units import synthesize,validate,validate_timing


def measured(scene):
    offset=0
    scene['spoken_unit_timing']=[]
    for unit in scene['spoken_units']:
        scene['spoken_unit_timing'].append({**unit,'start_s':offset,'end_s':offset+2})
        offset+=2
    bind_timing(scene)


def test_bridge_keeps_static_and_animated_speech_identical_and_only_target_brackets():
    original,case=fixture();before=copy.deepcopy(original)
    still,_=bind(original,case,animated=False)
    animated,receipt=bind(original,case,animated=True)
    assert original==before and receipt['changed_narration_scenes']==[1,2,3]
    for index,(a,b) in enumerate(zip(still['scenes'],animated['scenes'])):
        assert {k:v for k,v in a.items() if k!='primitives'}=={k:v for k,v in b.items() if k!='primitives'}
        assert [p for p in b['primitives'] if p['type']!='piano_walk']==a['primitives']
        labels=[p['text'] for p in b['primitives'] if p.get('type')=='text' and 'semitone' in p['text']]
        assert len(labels)==[0,0,1,2,2][index]
        assert all(x.startswith(('E–F:','B–C′:')) for x in labels)
        if b.get('spoken_units'):measured(b)
    validate_plan(animated,case)


def test_move_count_advances_only_after_actual_speech_cued_arrival():
    plan,case=fixture();p,_=bind(plan,case)
    s=p['scenes'][1];measured(s);spec=s['primitives'][-1]
    a,b=spec['intervals'][0]
    assert snapshot(spec,(a-.01)/s['duration_s'])['position']==key_positions()[60]
    mid=snapshot(spec,(a+b)/2/s['duration_s'])
    assert mid['completed_moves']==0 and mid['position']!=key_positions()[61]
    assert snapshot(spec,(b+.01)/s['duration_s'])['completed_moves']==1
    final=snapshot(spec,1)
    assert final['completed_moves']==2 and final['position']==key_positions()[62]
    assert len(final['segments'])==2


@pytest.mark.parametrize('pitches', [[60,62],[64,66],[60,61,60]])
def test_walk_rejects_skipping_or_reversing_keys(pitches):
    with pytest.raises(ValueError,match='neighboring'):
        compile_walk({'pitches':pitches,'cue_ids':['a']*(len(pitches)-1)},timed=False)


def test_units_cannot_change_narration_and_timing_cannot_skip_words():
    plan,case=fixture();p,_=bind(plan,case);s=p['scenes'][1]
    measured(s);validate_timing(s)
    changed=copy.deepcopy(s);changed['spoken_units'][0]['text']='An unsupported different statement.'
    with pytest.raises(ValueError,match='partition'):validate(changed)
    changed=copy.deepcopy(s);changed['spoken_unit_timing'][1]['start_s']+=.4
    with pytest.raises(ValueError,match='no longer'):validate_timing(changed)
    changed=copy.deepcopy(s);changed['spoken_unit_timing'][0]['text']='Stale source.'
    with pytest.raises(ValueError,match='no longer'):validate_timing(changed)


def test_unit_offsets_follow_actual_pcm_samples(tmp_path,monkeypatch):
    import localbench.tts
    lengths=iter([2400,4800])
    def fake(text_path,output,rate,config):
        count=next(lengths)
        with wave.open(str(output),'wb') as wav:
            wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(24000)
            wav.writeframes(b'\x01\x00'*count)
    monkeypatch.setattr(localbench.tts,'synthesize_speech',fake)
    scene={'narration':'Start at C. Move to the black key.',
           'spoken_units':[{'id':'start','text':'Start at C.'},{'id':'move','text':'Move to the black key.'}]}
    output=tmp_path/'joined.wav'
    rows=synthesize(scene,tmp_path,155,{},output)
    assert [(r['start_s'],r['end_s']) for r in rows]==[(0,.1),(.1,.3)]
    with wave.open(str(output)) as wav:assert wav.getnframes()==7200


def test_rendered_marker_avoids_note_labels_through_entire_walk():
    import numpy as np
    plan,case=fixture();p,_=bind(plan,case)
    for index in (1,2,3):
        s=p['scenes'][index];measured(s)
        for step in range(41):
            frame,issues=render_frame(s,step/40,index=index,total=5)
            assert not issues
            rgb=np.asarray(frame)
            marker=np.all(rgb==[255,224,145],axis=2)
            yy,xx=np.where(marker)
            assert len(yy)>0 and yy.max()<345 and yy.min()>240
            assert xx.min()>140 and xx.max()<876
