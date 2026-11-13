"""Bounded generated-label repair using existing layout checks, without a judge.

Moves static direct labels by at most 24 px per axis to clear stroke crossings,
then tries darker shades of the same hue for remaining low-contrast text. Text,
geometry, timing and narration are otherwise preserved. It is not a semantic
layout solver, a native-video editor, or proof of unobserved-frame correctness.
"""
from __future__ import annotations

import colorsys
import copy

from PIL import ImageColor

VERSION = 'bounded-static-label-repair-v1'


def issues(scene):
    from .scene import inspect_layout
    return inspect_layout({'scenes': [scene]}, include_warnings=True)


def key(issue):
    return (issue['kind'], issue.get('primitive'), str(issue.get('primitives', '')),
            issue.get('stroke_primitive'), issue.get('mode'))


def eligible(scene, primitive):
    return (not any(scene.get(k) for k in ('state_visual','source_visual','bond_cashflows','nephron_path','contact_pair'))
            and primitive.get('type') == 'text'
            and not any(primitive.get(k) for k in ('appear','dx','dy')))


def permitted(before, after, primitive, target):
    # Never introduce a new issue category/object pair or worsen a previously
    # nonblocking one; unchanged issues elsewhere remain visible in the receipt.
    if any(i['kind'] == target and i.get('primitive') == primitive for i in after):
        return False
    prior = {}
    for i in before:
        prior[key(i)] = max(prior.get(key(i), 0), int(i.get('severity','error') != 'warning'))
    return all(key(i) in prior and (i.get('severity','error') == 'warning' or prior[key(i)] == 1)
               for i in after)


def repair(plan):
    result=copy.deepcopy(plan);edits=[];before_all=[];after_all=[]
    for scene_id, scene in enumerate(result.get('scenes', [])):
        if any(scene.get(k) for k in ('state_visual','source_visual','bond_cashflows','nephron_path','contact_pair')):
            continue
        before=issues(scene);before_all.extend({'scene':scene_id,**{k:v for k,v in i.items() if k!='scene'}} for i in before)
        for primitive_id in sorted({i['primitive'] for i in before if i['kind']=='text_stroke_intersection'}):
            p=scene['primitives'][primitive_id]
            if not eligible(scene,p):continue
            # Vertical displacement preserves the horizontal role association in
            # arrow/amount layouts. Try horizontal shifts only if that fails.
            offsets=[(0,d) for d in (-8,8,-16,16,-24,24)]+[(d,0) for d in (-8,8,-16,16,-24,24)]
            for dx,dy in offsets:
                candidate=copy.deepcopy(scene)
                q=candidate['primitives'][primitive_id]
                q.update(x=p['x']+dx/896,y=p['y']+dy/302)
                if not 0<=q['x']<=1 or not 0<=q['y']<=1:continue
                after=issues(candidate)
                if permitted(before,after,primitive_id,'text_stroke_intersection'):
                    edits.append({'scene':scene_id,'primitive':primitive_id,'operation':'offset_label',
                                  'dx_px':dx,'dy_px':dy,'before':copy.deepcopy(p),'after':copy.deepcopy(q)})
                    scene=candidate;before=after;result['scenes'][scene_id]=scene
                    break
        # Keep semantic hue; crossing labels must move instead of camouflaging a
        # line by changing foreground colors. Color repair is a distinct step.
        contrast_ids=sorted({i['primitive'] for i in before if i['kind']=='text_low_contrast'
                             and i.get('severity','error')!='warning'})
        for primitive_id in contrast_ids:
            p=scene['primitives'][primitive_id]
            if not eligible(scene,p) or any(i['kind']=='text_stroke_intersection' and i.get('primitive')==primitive_id for i in before):continue
            rgb=ImageColor.getrgb(p.get('color','#1868ae'))
            h,s,v=colorsys.rgb_to_hsv(*(c/255 for c in rgb[:3]))
            for factor in (.8,.6,.4,.25,.1):
                color='#'+''.join(f'{round(c*255):02x}' for c in colorsys.hsv_to_rgb(h,s,v*factor))
                candidate=copy.deepcopy(scene);q=candidate['primitives'][primitive_id];q['color']=color
                after=issues(candidate)
                if permitted(before,after,primitive_id,'text_low_contrast'):
                    edits.append({'scene':scene_id,'primitive':primitive_id,'operation':'darken_same_hue',
                                  'before':copy.deepcopy(p),'after':copy.deepcopy(q)})
                    scene=candidate;before=after;result['scenes'][scene_id]=scene
                    break
        after_all.extend({'scene':scene_id,**{k:v for k,v in i.items() if k!='scene'}} for i in before)
    return result, {'version':VERSION,'status':'changed' if edits else 'unchanged','edits':edits,
                    'before':before_all,'after':after_all,
                    'scope':'Generated static labels and sampled progress only; final media and role associations require inspection.'}
