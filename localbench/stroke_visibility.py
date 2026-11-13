"""Sampled visibility diagnostics for generated ordinary strokes.

Counterfactual renders locate the pixels a stroke can affect after later
occlusion. Compare its authored pixels with the rendering without it. This
is a method-side diagnostic, not a benchmark metric or a semantic judgement.
Custom/state/source graphics, shape borders, and unsampled motion are outside
coverage. Thresholds are heuristic and not calibrated against human ratings.
"""
from __future__ import annotations

import copy
import colorsys
from collections import Counter
import numpy as np
from PIL import ImageColor

VERSION = 'generated-stroke-visibility-v1'
SUPPORTED = {'line', 'arrow', 'arc', 'polyline'}


def luminance(rgb):
    v=np.asarray(rgb,dtype=float)/255
    linear=np.where(v<=.04045,v/12.92,((v+.055)/1.055)**2.4)
    return linear @ np.array([.2126,.7152,.0722])


def inspect_visibility(scene, progress):
    from .scene import render_frame
    if scene.get('state_visual') or scene.get('source_visual'):
        return []
    eligible=[i for i,p in enumerate(scene.get('primitives',[]))
              if p['type'] in SUPPORTED and not p.get('closed')
              and progress>=p.get('appear',0)]
    if not eligible:return []
    actual=np.asarray(render_frame(scene,progress)[0]);rows=[]
    for index in eligible:
        probes=[]
        for color in ('#000000','#ffffff'):
            candidate=copy.deepcopy(scene);candidate['primitives'][index]['color']=color
            probes.append(np.asarray(render_frame(candidate,progress)[0]))
        # Pixels unchanged by both endpoint colors are fully occluded or outside
        # the primitive; do not diagnose a hidden or not-yet-appeared stroke.
        support=np.max(np.abs(probes[0].astype(int)-probes[1].astype(int)),axis=2)>=192
        count=int(support.sum())
        if count<12:continue
        removed=copy.deepcopy(scene);removed['primitives'].pop(index)
        background=np.asarray(render_frame(removed,progress)[0])
        a=luminance(actual[support]);b=luminance(background[support])
        ratios=(np.maximum(a,b)+.05)/(np.minimum(a,b)+.05)
        near=float(np.mean(ratios<1.5));low=float(np.mean(ratios<3))
        if low<.5:continue
        y,x=np.where(support)
        rows.append({'version':VERSION,'kind':'stroke_low_visibility','severity':'warning',
            'primitive':index,'stroke_type':scene['primitives'][index]['type'],
            'bbox':[int(x.min()),int(y.min()),int(x.max()+1),int(y.max()+1)],
            'visible_support_pixels':count,'contrast_median':round(float(np.median(ratios)),3),
            'fraction_below_1_5':round(near,3),'fraction_below_3':round(low,3),
            'priority':'nearly_invisible' if near>=.8 else 'low_contrast',
            'basis':'Authored stroke versus the same rendered scene without it, restricted to pixels affected by black/white stroke probes after occlusion. Not a score or semantic importance claim.'})
    return rows


def sampled(scene):
    return [{'progress':progress,**row} for progress in (0,.25,.5,.75,1)
            for row in inspect_visibility(scene,progress)]


def regression_report(reference,candidate):
    """Detect newly severe sampled stroke visibility loss, not deleted content.

    Match by scene/progress/stroke kind/visible bounds rather than list index so
    reordering primitives alone is not a regression. Existing unresolved severe
    marks may remain; counts preserve multiplicity. This does not protect
    semantic roles, deletion, unsupported representations or unsampled motion.
    """
    def rows(plan):
        return [{'scene':i,**r} for i,s in enumerate(plan.get('scenes',[]))
                for r in sampled(s) if r['priority']=='nearly_invisible']
    before=rows(reference);after=rows(candidate)
    def key(r):return (r['scene'],r['progress'],r['stroke_type'],tuple(r['bbox']))
    allowed=Counter(key(r) for r in before);regressions=[]
    for r in after:
        k=key(r)
        if allowed[k]:allowed[k]-=1
        else:regressions.append(r)
    return {'version':VERSION,'status':'new_severe_visibility_loss' if regressions else 'no_new_severe_visibility_loss',
            'before':before,'after':after,'regressions':regressions,
            'scope':'Sampled ordinary-stroke contrast loss only; no deletion, semantic-role or complete-video certification.'}


def validate_no_regression(report):
    if report['regressions']:
        first=report['regressions'][0]
        raise ValueError(f"new severe stroke visibility loss: scene {first['scene']} primitive {first['primitive']} at progress {first['progress']}; median contrast {first['contrast_median']}")
    return report


def repair(plan):
    """Change only static stroke colors with severe sampled visibility loss.

    Preserve hue/saturation, geometry, appearance timing and all lesson text.
    Existing layout checks and visibility checks must not gain new issue pairs.
    Color-role semantics and unsampled frames still need final-media review.
    """
    from .label_repair import issues,permitted
    result=copy.deepcopy(plan);edits=[];before_all=[];after_all=[]
    protected=('state_visual','source_visual','bond_cashflows','nephron_path','contact_pair')
    for scene_id,scene in enumerate(result.get('scenes',[])):
        if any(scene.get(k) for k in protected):continue
        before=sampled(scene)
        before_all.extend({'scene':scene_id,**v} for v in before)
        targets=sorted({r['primitive'] for r in before if r['priority']=='nearly_invisible'})
        for index in targets:
            p=scene['primitives'][index]
            if p.get('dx') or p.get('dy'):continue
            h,s,v=colorsys.rgb_to_hsv(*(x/255 for x in ImageColor.getrgb(p.get('color','#1868ae'))[:3]))
            values=[v*f for f in (.8,.6,.4,.25,.1)]+[v+(1-v)*f for f in (.25,.5,.75,1)]
            prior_layout=issues(scene);seen=set()
            for value in values:
                color='#'+''.join(f'{round(x*255):02x}' for x in colorsys.hsv_to_rgb(h,s,value))
                if color in seen:continue
                seen.add(color)
                candidate=copy.deepcopy(scene);candidate['primitives'][index]['color']=color
                after=sampled(candidate)
                if any(r['primitive']==index for r in after):continue
                if not permitted(before+prior_layout,after+issues(candidate),index,'stroke_low_visibility'):continue
                # Preserve the severity of other sampled visibility issues too.
                fractions={(r['primitive'],r['progress']):r['fraction_below_3'] for r in before}
                if any(r['fraction_below_3']>fractions.get((r['primitive'],r['progress']),0) for r in after):continue
                edits.append({'scene':scene_id,'primitive':index,'operation':'same_hue_stroke_contrast',
                              'before':copy.deepcopy(p),'after':copy.deepcopy(candidate['primitives'][index])})
                scene=candidate;before=after;result['scenes'][scene_id]=scene
                break
        after_all.extend({'scene':scene_id,**v} for v in before)
    return result,{'version':VERSION,'status':'changed' if edits else 'unchanged','edits':edits,
                  'before':before_all,'after':after_all,
                  'scope':'Only static ordinary stroke color at five sampled progress points; not semantic color-role validation, continuous visibility proof, or a benchmark score.'}
