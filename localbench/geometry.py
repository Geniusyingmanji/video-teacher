"""Reusable geometric constructions with explicit units and invariant checks."""
from __future__ import annotations

import math


def parallel_rays_to_focus(heights, *, start_x, lens_x, focus_x, end_x, axis_y):
    """Ideal thin converging lens: parallel incident segments, one shared focus.

    Coordinates are diagram units, not measured physical lengths. A ray keeps
    its straight outgoing trajectory beyond the focus; it does not stop there.
    """
    values=[*heights,start_x,lens_x,focus_x,end_x,axis_y]
    if not heights or any(type(v) not in (int,float) or not math.isfinite(v) for v in values):
        raise ValueError('finite nonempty ray geometry required')
    if not start_x<lens_x<focus_x<=end_x:raise ValueError('converging-lens x coordinates must be ordered')
    if len(set(heights))!=len(heights):raise ValueError('incident ray heights must be distinct')
    rays=[]
    for y in heights:
        slope=(axis_y-y)/(focus_x-lens_x)
        rays.append({'incoming':[[start_x,y],[lens_x,y]],
                     'outgoing':[[lens_x,y],[end_x,y+slope*(end_x-lens_x)]],
                     'focus':[focus_x,axis_y],'slope':slope})
    return rays
