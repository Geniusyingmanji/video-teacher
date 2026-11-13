import numpy as np
import pytest

from localbench.spoken_controls import splice_samples


def test_spoken_control_only_replaces_declared_pcm_interval_and_never_truncates_speech():
    source=np.arange(100,dtype=np.int16);replacement=np.full(10,200,dtype=np.int16)
    changed=splice_samples(source,replacement,20,40)
    assert len(changed)==len(source) and np.array_equal(source,np.arange(100,dtype=np.int16))
    assert np.array_equal(changed[:20],source[:20]) and np.array_equal(changed[40:],source[40:])
    assert np.array_equal(changed[20:30],replacement) and not np.any(changed[30:40])
    with pytest.raises(ValueError,match='never truncate'):splice_samples(source,replacement,20,25)
    with pytest.raises(ValueError):splice_samples(source,replacement,-1,10)
