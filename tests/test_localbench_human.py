import json

import numpy as np
import pytest

from localbench.controls import intervention
from localbench.human import rating_task, render_form, summarize
from localbench.rubric import DIMENSIONS, VERSION


def test_audio_interventions_preserve_content_or_silence_as_declared():
    pcm=np.array([1,3,5,-2,-4,0],dtype='<i2')
    assert np.array_equal(intervention(pcm,'clean',2),pcm)
    shifted=intervention(pcm,'shifted',2)
    assert np.array_equal(np.roll(shifted,-2),pcm)
    assert not intervention(pcm,'muted',2).any()


def test_rater_packet_omits_model_paths_and_scores_and_escapes_script():
    case={'id':'secret_case','prompt_text':'Read </script><script>alert(1)</script>',
          'pedagogical_target_audience':'high school','target_duration_s':60,
          'model':'secret_model','video_path':'/private/secret_model/code.mp4',
          'automated_score':99,'discipline':'mathematics','expected_concepts':['valid reference']}
    task=rating_task(case,'v123','rater_01','study_test')
    text=json.dumps(task)
    assert 'secret_model' not in text and '/private/' not in text and 'secret_case' not in text
    form=render_form([task],'study_test','rater_01')
    assert '</script><script>alert' not in form
    assert task['video']=='media/v123.mp4'


def response(assignment,value):
    return {k:assignment[k] for k in ('assignment_id','item_id','rater_id','rubric_version')} | {
        'dimensions':{d:{k:{'score':value,'note':'synthetic unit-test fixture'} for k in spec['criteria']}
                      for d,spec in DIMENSIONS.items()}}


def test_human_analysis_keeps_same_task_variants_separate_and_rejects_duplicates():
    case={'prompt_text':'A task'}
    assignments=[rating_task(case,item,rater,'study') for item in ('v1','v2') for rater in ('r1','r2')]
    responses=[response(a,2 if a['item_id']=='v1' else 5) for a in assignments]
    result=summarize(assignments,responses+[responses[0]])
    cell=result['criteria']['conceptual_correctness']['facts']
    assert cell['n_videos']==2 and cell['n_ratings']==4
    assert cell['ordinal_alpha']==pytest.approx(1)
    assert result['n_accepted']==4 and result['rejected'][0]['reason']=='duplicate response'
    assert summarize(assignments,[])['status']=='no_human_ratings'


def test_human_unverified_and_wrong_rater_are_not_valid_scores():
    task=rating_task({'prompt_text':'question'},'v1','r1','study')
    row=response(task,None)
    result=summarize([task],[row])
    assert result['criteria']['visual_quality']['legibility']['mean'] is None
    row['rater_id']='wrong'
    assert summarize([task],[row])['n_accepted']==0


def test_digital_silence_is_observed_without_hallucinated_transcript(tmp_path):
    import wave
    from localbench.asr import read_pcm,transcribe
    path=tmp_path/'silent.wav'
    with wave.open(str(path),'wb') as wav:
        wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(16000)
        wav.writeframes(np.zeros(16000,dtype='<i2').tobytes())
    _,signal=read_pcm(path)
    assert signal['digital_silence'] and signal['peak_pcm']==0
    result=transcribe(path)
    assert result['transcript']=='' and result['utterances']==[]


def test_alignment_pairs_absolute_speech_time_only_to_local_frames():
    from localbench.alignment import make_probes
    packet={'frames':[{'id':f'F{i}','time_s':i,'path':'unused'} for i in range(40)]}
    audio=[{'id':'A01','start_s':20,'end_s':40,'timing_valid':True,
            'utterances':[{'start_s':1,'end_s':4,'text':'An object moves here.',
                           'words':[{'word':'An object moves here.','start_s':1,'end_s':4}]}]}]
    probes=make_probes(packet,audio)
    assert probes[0]['start_s']==21 and probes[0]['end_s']==24
    assert all(21<=f['time_s']<=24 for f in probes[0]['frames'])
    assert 'F1' not in probes[0]['allowed_ids']
