import numpy as np
import pytest

from localbench.fixed_scene_speech import RATE,splice


def test_edit_preserves_later_pcm_and_exact_boundaries():
    source=np.arange(3*RATE,dtype=np.int16)
    slots={0:(0,RATE),1:(RATE,2*RATE),2:(2*RATE,3*RATE)}
    speech=np.full(RATE//2,123,dtype=np.int16)
    changed,receipt=splice(source,slots,{1:speech})
    assert np.array_equal(changed[:RATE],source[:RATE])
    assert np.array_equal(changed[2*RATE:],source[2*RATE:])
    assert (changed[RATE:RATE+len(speech)]==123).all()
    assert (changed[RATE+len(speech):2*RATE]==0).all()
    assert len(changed)==len(source) and receipt['unmodified_samples']==2*RATE


def test_overlong_speech_rejected_without_truncating_or_mutating_source():
    source=np.ones(RATE,dtype=np.int16);before=source.copy()
    with pytest.raises(ValueError,match='do not truncate'):
        splice(source,{0:(0,RATE)},{0:np.ones(RATE,dtype=np.int16)})
    assert np.array_equal(source,before)


def test_overlapping_replacements_rejected():
    with pytest.raises(ValueError,match='nonoverlapping'):
        splice(np.ones(2*RATE,dtype=np.int16),{0:(0,RATE),1:(RATE//2,2*RATE)},
               {0:np.ones(5000,dtype=np.int16),1:np.ones(5000,dtype=np.int16)})
