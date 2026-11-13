"""Shared raster semantics for ordinary solid/dashed lines and arrows."""
from __future__ import annotations

import math


VERSION = 'ordinary-dashed-strokes-v1'


def validate_style(primitive):
    if 'dash' in primitive:
        if primitive.get('type') not in {'line', 'arrow'}:
            raise ValueError('dash is supported only on line/arrow primitives')
        if type(primitive['dash']) is not bool:
            raise ValueError('dash must be boolean')


def draw_linear(draw, primitive, xy, *, fill=None):
    """Draw identical geometry for visible frames and glyph-overlap masks.

    dash=True has 3*stroke (minimum10px) ink and 2*stroke (minimum6px)
    gaps along the segment. The arrowhead remains solid. No chemical meaning
    is inferred: the scene author chooses whether a dashed stroke is appropriate.
    """
    validate_style(primitive)
    x, y, x2, y2 = xy
    width = int(primitive.get('stroke', 4))
    color = primitive.get('color', '#1868ae') if fill is None else fill
    length = math.hypot(x2-x, y2-y)
    if primitive.get('dash') and length:
        ink, gap = max(10, 3*width), max(6, 2*width)
        start = 0.
        while start < length:
            end = min(length, start+ink)
            a, b = start/length, end/length
            draw.line((x+(x2-x)*a, y+(y2-y)*a,
                       x+(x2-x)*b, y+(y2-y)*b), fill=color, width=width)
            start += ink+gap
    else:
        draw.line(xy, fill=color, width=width)
    if primitive['type'] == 'arrow':
        angle = math.atan2(y2-y, x2-x)
        draw.polygon([(x2,y2), (x2-12*math.cos(angle-.5),y2-12*math.sin(angle-.5)),
                      (x2-12*math.cos(angle+.5),y2-12*math.sin(angle+.5))], fill=color)
