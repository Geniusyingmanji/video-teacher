"""Generator preflight only. Never use generator metadata for benchmark scores."""
from __future__ import annotations

import numpy as np
from PIL import ImageColor


def contrast_ratios(color, backgrounds):
    rgb=np.asarray(ImageColor.getrgb(color)[:3],dtype=float)/255
    bg=np.asarray(backgrounds,dtype=float)/255
    def luminance(x):
        linear=np.where(x<=.04045,x/12.92,((x+.055)/1.055)**2.4)
        return linear@np.array([.2126,.7152,.0722])
    a,b=luminance(rgb),luminance(bg)
    return (np.maximum(a,b)+.05)/(np.minimum(a,b)+.05)


def text_contrast(image, mask, color, record):
    """Sample pre-text background under actual glyph interiors, avoiding antialias pixels."""
    crop=mask.getbbox()
    if not crop:return []
    ink=np.asarray(mask.crop(crop))>=192
    if not ink.any():return []
    backgrounds=np.asarray(image.crop(crop).convert('RGB'))[ink]
    ratios=contrast_ratios(color,backgrounds)
    # 3:1 is the large-text floor; 4.5:1 is a conservative advisory target.
    failing=float(np.mean(ratios<3));advisory=float(np.mean(ratios<4.5))
    if failing<.1 and advisory<.1:return []
    return [{'kind':'text_low_contrast','severity':'error' if failing>=.1 else 'warning',
             **record,'contrast_p10':round(float(np.quantile(ratios,.1)),2),
             'fraction_below_3':round(failing,3),'fraction_below_4_5':round(advisory,3),
             'basis':'pre-text local background at glyph interiors; large-text floor 3:1'}]


def contains(shape, point, padding=0):
    x,y=point;a,b,c,d=shape['bbox']
    if shape['kind']=='rect':return a+padding<=x<=c-padding and b+padding<=y<=d-padding
    rx=(c-a)/2-padding;ry=(d-b)/2-padding
    return rx>0 and ry>0 and ((x-(a+c)/2)/rx)**2+((y-(b+d)/2)/ry)**2<=1


def container_issues(texts,containers,text_masks=()):
    issues=[]
    masks={r["primitive"]:m for r,m in text_masks}
    for text in texts:
        if 'primitive' not in text:continue
        a,b,c,d=text['bbox'];center=((a+c)/2,(b+d)/2)
        candidates=[s for s in containers if s['primitive']<text['primitive'] and contains(s,center)]
        if not candidates:continue  # external labels are not automatically container text
        shape=min(candidates,key=lambda s:(s['bbox'][2]-s['bbox'][0])*(s['bbox'][3]-s['bbox'][1]))
        corners=((a,b),(a,d),(c,b),(c,d))
        outside=not all(contains(shape,p) for p in corners)
        tight=not all(contains(shape,p,4) for p in corners)
        if shape['kind']=='circle' and text['primitive'] in masks:
            ys,xs=np.where(np.asarray(masks[text['primitive']])>=192)
            x0,y0,x1,y1=shape['bbox'];cx,cy=(x0+x1)/2,(y0+y1)/2;rx,ry=(x1-x0)/2,(y1-y0)/2
            outside=bool(np.any(((xs-cx)/rx)**2+((ys-cy)/ry)**2>1))
            tight=bool(np.any(((xs-cx)/max(1,rx-4))**2+((ys-cy)/max(1,ry-4))**2>1))
        if tight:
            issues.append({'kind':'text_container_overflow' if outside else 'text_container_padding',
                           'severity':'warning','association':'inferred_from_text_center_in_smallest_prior_shape',
                           **text,'container_primitive':shape['primitive'],'container_bbox':shape['bbox'],
                           'reason':'Text crosses its inferred box/circle boundary.' if outside else 'Less than 4 px inner padding.'})
    return issues


def blocking_issues(issues):
    return [i for i in issues if i.get('severity','error')!='warning']
