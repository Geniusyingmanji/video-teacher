"""Heuristic rectangular panel localization from final pixels, without scene metadata."""
from __future__ import annotations

import numpy as np
from scipy import ndimage


def rectangular_regions(image,limit=8):
    rgb=np.asarray(image.convert('RGB')).astype(int);h,w=rgb.shape[:2]
    # Saturated/dark strokes. Light fills are excluded so their borders remain separable.
    ink=(rgb.max(2)<235)&((rgb.max(2)-rgb.min(2)>25)|(rgb.max(2)<125))
    def spans(mask):
        labeled,count=ndimage.label(mask)
        return [[s[1].start,s[0].start,s[1].stop,s[0].stop] for s in ndimage.find_objects(labeled) if s]
    horizontal=spans(ndimage.binary_opening(ink,structure=np.ones((1,max(25,w//40)),bool)))
    vertical=spans(ndimage.binary_opening(ink,structure=np.ones((max(18,h//32),1),bool)))
    found=[];tol=max(12,w//64)
    for top in horizontal:
        if top[3]-top[1]>8:continue
        for bottom in horizontal:
            if bottom[3]-bottom[1]>8 or not 24<bottom[1]-top[3]<h*.65:continue
            if abs(top[0]-bottom[0])>tol or abs(top[2]-bottom[2])>tol:continue
            sides=[v for v in vertical if v[2]-v[0]<=8 and v[1]<=top[3]+tol and v[3]>=bottom[1]-tol]
            left=[v for v in sides if abs(v[0]-top[0])<=tol]
            right=[v for v in sides if abs(v[2]-top[2])<=tol]
            if not left or not right:continue
            box=[min(v[0] for v in left),top[1],max(v[2] for v in right),bottom[3]]
            if box[2]-box[0]<30 or (box[2]-box[0])*(box[3]-box[1])>w*h*.45:continue
            if any(max(abs(a-b) for a,b in zip(box,old))<8 for old in found):continue
            found.append(box)
    # Small containers first; a bounded supplementary view, never exhaustive detection.
    return sorted(found,key=lambda b:(b[2]-b[0])*(b[3]-b[1]))[:limit]
