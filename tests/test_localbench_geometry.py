import pytest

from localbench.geometry import parallel_rays_to_focus
from localbench.state import derive_state


def test_three_incident_rays_stay_parallel_and_all_outgoing_lines_cross_one_focus():
    rays=parallel_rays_to_focus([-2,0,2],start_x=-4,lens_x=0,focus_x=3,end_x=6,axis_y=0)
    assert len(rays)==3
    for ray,y in zip(rays,[-2,0,2]):
        assert ray['incoming']==[[-4,y],[0,y]]
        a,b=ray['outgoing']
        at_focus=a[1]+(b[1]-a[1])*(3-a[0])/(b[0]-a[0])
        assert at_focus==pytest.approx(0)
        assert b[1]==pytest.approx(-y)


def test_invalid_lens_geometry_is_not_silently_rendered():
    with pytest.raises(ValueError):parallel_rays_to_focus([0,1],start_x=0,lens_x=2,focus_x=1,end_x=3,axis_y=0)
    assert derive_state({'prompt_text':'A convex lens focuses 3 parallel rays to a focal point.'})['kind']=='converging_lens'
    assert derive_state({'prompt_text':'A convex lens focuses 5 parallel rays to a focal point.'}) is None
