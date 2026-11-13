import numpy as np
import pytest

from localbench.controls import intervention
from localbench.requirements import output_checks
from localbench.speech import reconcile


def test_tones_are_nonzero_audio_but_not_copied_speech():
    x=np.arange(24000,dtype=np.int16)
    tones=intervention(x,'tones',0)
    assert np.max(np.abs(tones))>1000
    assert not np.array_equal(tones,x)
    assert tones[0]==0


def test_listener_and_vad_agreement_establishes_no_narration_not_silence():
    decision=reconcile({'transcript':'','speech_activity':{'status':'observed','segments':[]}},
                       {'speech_presence':'absent','transcript':''})
    assert decision['status']=='observed_absent'
    assert decision['transcript_valid'] and decision['timing_valid']
    record={'id':'A00','digital_silence':False,'narration_presence':decision}
    assert 'spoken_narration_presence' in output_checks({},[record])['failed']


def test_detector_listener_conflict_does_not_invent_or_discard_speech():
    decision=reconcile({'transcript':'','speech_activity':{'status':'observed','segments':[]}},
                       {'speech_presence':'present','transcript':'Actual words'})
    assert decision['status']=='unverified' and not decision['transcript_valid']
    decision=reconcile({'transcript':'Hallucinated words','speech_activity':{'status':'observed','segments':[]}},
                       {'speech_presence':'absent','transcript':''})
    assert decision['status']=='unverified'


def test_vad_failure_cannot_prove_no_speech_and_listener_cannot_invent_timing():
    decision=reconcile({'error':'ASR unavailable'}, {'speech_presence':'absent','transcript':''})
    assert decision['status']=='unverified'
    decision=reconcile({'error':'ASR unavailable'}, {'speech_presence':'present','transcript':'Real speech'})
    assert decision['transcript_valid'] and not decision['timing_valid']
    with pytest.raises(ValueError):reconcile({}, {'transcript':''})
