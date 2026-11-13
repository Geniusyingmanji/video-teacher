"""Bounded numeric series and a fixed Cartesian mapping, independent of subject."""
from __future__ import annotations

import math

from PIL import ImageColor, ImageDraw

VERSION = 'localbench-chart-v2'
PLOT = (154, 195, 925, 350)  # x-left, y-top, x-right, y-bottom, in final-video pixels


def number(value):
    if type(value) not in (int, float) or not math.isfinite(value) or abs(value) > 1e12:
        raise ValueError('chart requires finite bounded numbers')
    return value


def bounds(values, declared=None):
    if declared is not None:
        if not isinstance(declared, list) or len(declared) != 2:
            raise ValueError('axis range needs two endpoints')
        lo, hi = map(number, declared)
        if not lo < hi or min(values) < lo or max(values) > hi:
            raise ValueError('axis range must increase and enclose all plotted values')
    else:
        lo, hi = min(values), max(values)
        if lo == hi:
            pad = max(1, abs(lo) * .05)
            lo, hi = lo - pad, hi + pad
    return [lo, hi]


def compile_chart(spec):
    from .scene import arithmetic
    if spec.get('type') != 'chart':
        raise ValueError('expected chart')
    allowed = {'type','x','y','x_values','x_label','x_unit','y_label','y_unit','series','x_range','y_range'}
    if set(spec) - allowed or spec.get('x') != 0 or spec.get('y') != 0:
        raise ValueError('chart uses a fixed panel; unsupported chart options')
    for key, limit in [('x_label',35),('y_label',35),('x_unit',10),('y_unit',10)]:
        if not isinstance(spec.get(key), str) or len(spec[key]) > limit or (key.endswith('label') and not spec[key].strip()):
            raise ValueError(f'chart {key} must be a bounded explicit label/unit')
    xs = spec.get('x_values')
    if not isinstance(xs, list) or not 2 <= len(xs) <= 100:
        raise ValueError('chart needs 2..100 x values')
    xs = [number(x) for x in xs]
    if any(a >= b for a, b in zip(xs, xs[1:])):
        raise ValueError('chart x values must strictly increase')
    series = spec.get('series')
    if not isinstance(series, list) or not 1 <= len(series) <= 3:
        raise ValueError('chart needs 1..3 series')
    compiled = []
    for i, s in enumerate(series):
        if not isinstance(s, dict) or set(s) - {'label','color','expression','parameters','y_values'}:
            raise ValueError('invalid chart series options')
        if not isinstance(s.get('label'), str) or not 1 <= len(s['label']) <= 26:
            raise ValueError('chart series requires a label of 1..26 characters')
        if ('expression' in s) == ('y_values' in s):
            raise ValueError('series needs either expression or y_values, exclusively')
        if 'expression' in s:
            params = s.get('parameters', {})
            if not isinstance(params, dict) or 'x' in params:
                raise ValueError('series parameters cannot override x')
            ys = [number(arithmetic(s['expression'], {**params, 'x': x})) for x in xs]
        else:
            if 'parameters' in s or not isinstance(s['y_values'], list) or len(s['y_values']) != len(xs):
                raise ValueError('series y values must match x length, without parameters')
            ys = [number(y) for y in s['y_values']]
        color = s.get('color', ['#1868ae','#b3481c','#288052'][i])
        if not isinstance(color, str):
            raise ValueError('chart color must be a CSS string')
        ImageColor.getrgb(color)
        compiled.append({'label':s['label'], 'color':color, 'y_values':ys})
    xr = bounds(xs, spec.get('x_range'))
    yr = bounds([y for s in compiled for y in s['y_values']], spec.get('y_range'))
    left, top, right, bottom = PLOT
    for s in compiled:
        s['pixel_points'] = [[left+(x-xr[0])/(xr[1]-xr[0])*(right-left),
                              bottom-(y-yr[0])/(yr[1]-yr[0])*(bottom-top)]
                             for x, y in zip(xs, s['y_values'])]
    return {'version':VERSION, 'x_values':xs, 'x_range':xr, 'y_range':yr,
            'plot_box':list(PLOT), 'series':compiled,
            'mapping':'x increases right; y increases up; no data clipping'}


def axis_ticks(chart, axis):
    """Show actual sample positions on x and readable round values on y."""
    if axis == 'x':
        xs=chart['x_values']
        if len(xs)<=10:return xs
        return [xs[round(i*(len(xs)-1)/4)] for i in range(5)]
    lo,hi=chart['y_range']
    raw=(hi-lo)/4
    power=10**math.floor(math.log10(raw))
    step=next(m*power for m in (1,2,2.5,5,10) if m*power>=raw)
    start=math.ceil(lo/step)*step
    ticks=[start+i*step for i in range(6) if lo<=start+i*step<=hi]
    return ticks if len(ticks)>=2 else [lo,hi]


def draw_chart(image, spec):
    from .scene import font
    chart = compile_chart(spec)
    draw = ImageDraw.Draw(image)
    boxes = []
    def label(x, y, text, size=20, anchor='lt', color='#243d54'):
        face = font(size)
        boxes.append({'text':text, 'bbox':list(draw.textbbox((x,y),text,font=face,anchor=anchor))})
        draw.text((x,y),text,font=face,anchor=anchor,fill=color)
    def axis_text(name):
        return spec[name+'_label'] + (f" ({spec[name+'_unit']})" if spec[name+'_unit'] else '')
    left, top, right, bottom = PLOT
    label(90,119,axis_text('y'),24)
    for i, s in enumerate(chart['series']):
        x = 90+i*294
        draw.line((x,164,x+21,164),fill=s['color'],width=4)
        label(x+29,153,s['label'],19,color=s['color'])
    for axis in ('x','y'):
        lo, hi = chart[axis+'_range']
        for value in axis_ticks(chart,axis):
            f=(value-lo)/(hi-lo)
            # At most six significant digits; never replace data with these tick labels.
            text = f'{value:.6g}'
            if axis == 'x':
                x = left+f*(right-left)
                draw.line((x,top,x,bottom+4),fill='#dce4ef',width=1)
                label(x,bottom+10,text,19,'mt')
            else:
                y = bottom-f*(bottom-top)
                draw.line((left-4,y,right,y),fill='#dce4ef',width=1)
                label(left-12,y,text,19,'rm')
    draw.line((left,top,left,bottom,right,bottom),fill='#506a80',width=2)
    label((left+right)/2,408,axis_text('x'),23,'mm')
    for s in chart['series']:
        points = [tuple(p) for p in s['pixel_points']]
        draw.line(points,fill=s['color'],width=4)
        for x,y in points:
            draw.ellipse((x-3,y-3,x+3,y+3),fill=s['color'])
    return boxes


def plan_chart_receipts(plan):
    return [{'scene':i,'primitive':j,'spec':p,'computed':compile_chart(p)}
            for i,s in enumerate(plan['scenes']) for j,p in enumerate(s.get('primitives',[]))
            if p.get('type') == 'chart']
