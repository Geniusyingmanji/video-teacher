"""Generator-only stroke/glyph preflight; not a benchmark score or OCR detector.

Uses generated primitives at sampled progress values, matching the current
1024x576 renderer. Direct text against line/arrow/open-polyline/arc only;
custom chart/state labels and intervals between samples are outside coverage.
Warnings flag both draw orders; a later stroke covering substantial glyph ink
is blocking. Intentional crossings still need inspection of the final pixels.
"""
from __future__ import annotations

import numpy as np
from PIL import Image, ImageChops, ImageDraw

VERSION = 'generated-stroke-glyph-v2-dashed'


def inspect_strokes(scene, progress):
    from .scene import font
    if scene.get('source_visual') or scene.get('state_visual'):
        return []
    texts, strokes = [], []
    size = (1024, 576)
    for index, primitive in enumerate(scene.get('primitives', [])):
        p = primitive; kind = p['type']; appear = p.get('appear', 0)
        if progress < appear:
            continue
        local = min(1, max(0, (progress-appear)/max(.01, 1-appear)))
        tx, ty = p.get('dx', 0)*local, p.get('dy', 0)*local
        x, y = 64+(p.get('x', 0)+tx)*896, 112+(p.get('y', 0)+ty)*302
        mask = Image.new('L', size, 0); draw = ImageDraw.Draw(mask)
        if kind == 'text':
            anchor = {'center': 'mm', 'right': 'rt', 'left': 'lt'}[p.get('align', 'left')]
            face = font(int(max(18, min(38, p.get('font_size', 26)))))
            draw.text((x, y), p['text'], font=face, fill=255, anchor=anchor)
            texts.append(({'primitive': index, 'text': p['text']}, mask))
            continue
        if kind in {'line', 'arrow'}:
            x2, y2 = 64+(p.get('x2', p['x'])+tx)*896, 112+(p.get('y2', p['y'])+ty)*302
            from .stroke_style import draw_linear
            draw_linear(draw, p, (x, y, x2, y2), fill=255)
        elif kind == 'polyline' and not p.get('closed'):
            points = [(64+(a+tx)*896, 112+(b+ty)*302) for a,b in p['points']]
            draw.line(points, fill=255, width=int(p.get('stroke', 4)), joint='curve')
        elif kind == 'arc':
            r = p.get('r', .08)*302
            draw.arc((x-r,y-r,x+r,y+r),p['start_angle'],p['end_angle'],fill=255,width=int(p.get('stroke',4)))
        elif kind in {'rect', 'circle', 'sector', 'polyline'} and p.get('fill', '#e6f0fa'):
            # Filled later shapes obscure earlier text/strokes. Their borders have
            # separate container checks; do not treat hidden strokes as collisions.
            if kind == 'rect':
                draw.rounded_rectangle((x,y,x+p.get('w',.12)*896,y+p.get('h',.2)*302),radius=8,fill=255)
            elif kind in {'circle', 'sector'}:
                r = p.get('r',.08)*302; bounds = (x-r,y-r,x+r,y+r)
                if kind == 'circle': draw.ellipse(bounds,fill=255)
                else: draw.pieslice(bounds,p['start_angle'],p['end_angle'],fill=255)
            elif len(p['points']) >= 3:
                draw.polygon([(64+(a+tx)*896,112+(b+ty)*302) for a,b in p['points']],fill=255)
            texts = [(r,ImageChops.subtract(m,mask)) for r,m in texts]
            strokes = [(r,ImageChops.subtract(m,mask)) for r,m in strokes]
            continue
        else:
            continue
        strokes.append(({'stroke_primitive': index, 'stroke_type': kind}, mask))
    findings = []
    for record, text_mask in texts:
        bounds = text_mask.getbbox()
        if not bounds:
            continue
        ink = np.asarray(text_mask.crop(bounds)) >= 192
        for stroke, stroke_mask in strokes:
            overlap = ink & (np.asarray(stroke_mask.crop(bounds)) > 0)
            count = int(overlap.sum()); total = int(ink.sum())
            if count < 5 or count/max(1,total) < .03:
                continue
            middle = overlap[int(overlap.shape[0]*.2):max(1,int(overlap.shape[0]*.8))]
            later = stroke['stroke_primitive'] > record['primitive']
            findings.append({'version': VERSION, 'kind': 'text_stroke_intersection',
                'severity': 'error' if later and count/max(1,total) >= .08 and middle.sum() >= 5 else 'warning',
                **record, **stroke, 'bbox': list(bounds), 'stroke_drawn_after_text': later,
                'overlap_ink_pixels': count, 'overlap_ink_fraction': round(count/max(1,total),3),
                'basis': 'Generated stroke mask crosses glyph interiors after accounting for later opaque fills; inspect intent and final pixels. Not benchmark scoring.'})
    return findings
