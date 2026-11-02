"""Single source of truth for asset lookup and source-pixel/letterbox geometry."""
from pathlib import Path
import re


def needs_source(case):
    source = case.get('source', {})
    if not source.get('source_image_path'):
        return False
    flags = case.get('curation', {}).get('quality_flags', [])
    authored = any('authored' in flag and 'rewrite' in flag for flag in flags)
    explicit = re.search(r'\b(supplied|provided|source image|original diagram|existing diagram)\b', case['prompt_text'], re.I)
    return bool(explicit or not authored)


def resolve_source(case, asset_dir):
    if not needs_source(case):
        return None
    expected = 'grade_' + case['source']['source_id'] + '.png'
    matches = [p for p in Path(asset_dir).glob('*.png') if p.name.casefold() == expected.casefold()]
    if len(matches) != 1:
        raise ValueError(f'{case["id"]}: expected one unambiguous source asset for {expected}; found {len(matches)}')
    return matches[0].resolve()


def canvas_box(box, source_size, canvas_size=(854, 480)):
    sw, sh = source_size
    cw, ch = canvas_size
    if sw <= 0 or sh <= 0:
        raise ValueError('invalid source size')
    x0, y0, x1, y1 = box
    if not (0 <= x0 < x1 <= sw and 0 <= y0 < y1 <= sh):
        raise ValueError('box outside source image')
    scale = min(cw/sw, ch/sh)
    ox, oy = (cw-sw*scale)/2, (ch-sh*scale)/2
    return [(ox+x0*scale)/cw, (oy+y0*scale)/ch, (ox+x1*scale)/cw, (oy+y1*scale)/ch]


def rectangle_candidates(source):
    import cv2
    image = cv2.imread(str(source))
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    contours, _ = cv2.findContours((gray < 80).astype('uint8')*255, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    boxes = []
    for contour in contours:
        polygon = cv2.approxPolyDP(contour, .02*cv2.arcLength(contour, True), True)
        x, y, w, h = cv2.boundingRect(contour)
        # Arrows touching an answer box can notch an inner contour, so a
        # four-vertex approximation alone misses a real target. Verify edges.
        ink = gray < 100
        def covered_edges(padding):
            left, top = max(0,x-padding), max(0,y-padding)
            right, bottom = min(gray.shape[1],x+w+padding), min(gray.shape[0],y+h+padding)
            strips = [ink[top:min(top+3,bottom),left:right].any(axis=0),
                      ink[max(top,bottom-3):bottom,left:right].any(axis=0),
                      ink[top:bottom,left:min(left+3,right)].any(axis=1),
                      ink[top:bottom,max(left,right-3):right].any(axis=1)]
            return all(strip.size and strip.mean() >= .65 for strip in strips)
        rectangular = len(polygon)==4 or covered_edges(2)
        if rectangular and w >= 16 and h >= 12 and w*h < gray.size*.2:
            padding = 2 if len(polygon)!=4 else 0
            box = [max(0,x-padding), max(0,y-padding), min(gray.shape[1],x+w+padding), min(gray.shape[0],y+h+padding)]
            if not any(max(abs(a-b) for a,b in zip(box, old)) < 5 for old in boxes):
                boxes.append(box)
    return [{'id': i, 'source_pixel_box': box} for i, box in enumerate(sorted(boxes))]
