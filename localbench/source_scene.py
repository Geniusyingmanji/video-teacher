"""Source-image lessons: fixed original pixels with explicit bounded target edits."""
from __future__ import annotations

import math
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageColor
import numpy as np

from .provenance import file_hash
from .scene import font, wrapped

SIZE = (1600, 900)
VIEWPORT = (60, 88, 1540, 642)
SYSTEM = '''Create a complete English-narrated lesson from the PUBLIC task and its supplied source image.
Return JSON {case_id, source_edits:[...], scenes:[...]} with 4..8 scenes.
The renderer keeps the COMPLETE source image fixed in the upper viewport. Only explicitly
authorized target edits may change its pixels. Lower teaching panels explain the reasoning.
Do not redraw the source or change unrelated labels, geometry, arrows, colors, or scale.
source_edits are a small list of {id,kind:"replace_text",old_text,text,bbox:[x0,y0,x1,y1],from_scene}.
Coordinates refer to the ORIGINAL whole image, normalized 0..1. Carefully locate the requested
label in the supplied image. Black/gray label ink in this bbox is erased, colored diagram
lines are preserved, then replacement text is centered in the bbox. Make it large enough without touching diagram lines
or unrelated text. The box must contain less than 4 percent of the source area.
Only edit a white-background label with this backend. If impossible, return source_edits:[];
do not invent a different image. from_scene is the zero-based scene where the edit becomes
visible and persists through the end. Scene 0 must show the unedited original.
Each scene: title (<=65 chars),duration_s,narration,caption (<=120 chars),slide_text (<=140 chars),
teaching_lines (one or two short readable lines, <=65 chars each),
primitives:[{type:"text",x:0.5,y:0.5,text:"source image"}].
Durations sum to the target. Explain givens, why the operations are valid, work through the
solution, verify, and recap; approximately 2.0 spoken words/sec, no unrelated filler.
Use the actual supplied quantities and visual correspondences. No hidden answer images or
private reference are supplied. Do not infer that a numerical answer printed in the task is
correct without checking the shown givens. Separate source edits from temporary teaching text.
Read dimension arrows carefully: an entire length is not the length of one subsegment.
Identify shared sides by actual orientation/endpoints. Discuss only quantities relevant to the
requested solution; do not add an unrelated triangle's unknowns merely to fill lesson time.'''


OVERLAY_SYSTEM = '''Create a complete English-narrated lesson for the PUBLIC task and its original image.
Return JSON {case_id, source_edits:[], scenes:[...]} with 4..8 scenes totaling the target duration.
The renderer preserves the whole source image. Explain the requested reasoning and result in
lower teaching panels and narration. Marks inside the source image must be the exact target
edits authorized by the public task. Put temporary explanations in the lower teaching panel;
do not add decorative checkmarks, boxes, arrows, or status symbols to the source. Scene 0 has
no source_annotations. Repeat completed target marks in every later scene so they persist.
This backend cannot erase or reconstruct source geometry. Do not claim you performed an edit
that is not visible. An annotation is not proof that a source transformation is correct.
Each scene has title (<=65 chars), duration_s (4..24), narration (5..70 words; about 2 words/sec),
caption (<=120 chars), slide_text, teaching_lines (1..2 short lines, <=65 chars each),
primitives:[{type:"text",x:0.5,y:0.5,text:"source"}], and source_annotations (0..12 objects).
Coordinates are normalized 0..1 in the ORIGINAL WHOLE IMAGE. Annotations are independent per scene:
{type:"arrow",x,y,x2,y2,color:"#cf3434"}, {type:"rect",x,y,x2,y2,color},
{type:"circle",x,y,r,color}, or {type:"text",x,y,text:"short label",color}.
Text labels <=32 characters and must stay inside the source. Do not cover existing labels.
For text only, optional font_size is 8..96 pixels in the ORIGINAL source image, align is
left/center/right (default left), and stroke_width is 0..3 output pixels (default 1).
When the task asks to match existing labels, estimate their original-image font size,
use their color, and set stroke_width:0 for ordinary unoutlined text. Do not enlarge a
target label just to match the lower teaching-panel typography.
Use actual givens, quantities and relations. Explain, work through, verify and recap without
unrelated filler. No private answer is supplied. source_edits must be an empty list.'''


def validate_annotations(rows):
    if not isinstance(rows, list) or len(rows) > 12:
        raise ValueError('source_annotations must contain 0..12 objects')
    for row in rows:
        if not isinstance(row, dict) or row.get('type') not in {'arrow', 'rect', 'circle', 'text'}:
            raise ValueError('unsupported source annotation type; only arrow, rect, circle, text are supported, and each must be a task-authorized target edit')
        fields = ['x', 'y'] + (['x2', 'y2'] if row['type'] in {'arrow', 'rect'} else ['r'] if row['type'] == 'circle' else [])
        for key in fields:
            value = row.get(key)
            if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 1:
                raise ValueError('source annotation coordinates must be finite normalized values')
        if row['type'] == 'circle' and not 0 < row['r'] <= .25:
            raise ValueError('source circle radius must be within (0,.25]')
        if row['type'] == 'rect' and (row['x2'] <= row['x'] or row['y2'] <= row['y']):
            raise ValueError('source annotation rectangle is empty or reversed')
        if row['type'] == 'text' and (not isinstance(row.get('text'), str) or not 1 <= len(row['text']) <= 32):
            raise ValueError('source annotation text must have 1..32 characters')
        if row['type'] == 'text':
            if 'font_size' in row and (type(row['font_size']) not in (int, float)
                    or not math.isfinite(row['font_size']) or not 8 <= row['font_size'] <= 96):
                raise ValueError('source label font_size must be 8..96 original-image pixels')
            if row.get('align', 'left') not in {'left', 'center', 'right'}:
                raise ValueError('source label align must be left/center/right')
            if type(row.get('stroke_width', 1)) is not int or not 0 <= row.get('stroke_width', 1) <= 3:
                raise ValueError('source label stroke_width must be integer 0..3')
        ImageColor.getrgb(row.get('color', '#c62f40'))


def bind_source(plan, attachment, *, allow_regions=False, allow_graphs=False, allow_overlays=False):
    path = Path(attachment['local_path'])
    source_hash = file_hash(path)
    original_size=Image.open(path).size
    plan['canvas_size'] = list(SIZE)
    edits = plan.get('source_edits')
    if not isinstance(edits,list) or not (0 if allow_overlays else 1) <= len(edits) <= 8:
        raise ValueError('source-image backend needs authorized edits (empty allowed for annotations)')
    if allow_overlays and edits:
        raise ValueError('general annotation backend preserves source pixels; source_edits must be empty')
    ids = set()
    allowed = {'replace_text'} | ({'fill_between'} if allow_regions else set()) | ({'highlight_path'} if allow_graphs else set())
    for edit in edits:
        if edit.get('kind') not in allowed or not isinstance(edit.get('id'),str) or edit['id'] in ids:
            raise ValueError('invalid or duplicate source edit')
        ids.add(edit['id'])
        if type(edit.get('from_scene')) is not int or not 1<=edit['from_scene']<len(plan['scenes']):
            raise ValueError('source edits must begin after the original scene and before the end')
        if edit['kind']=='fill_between':
            from .source_region import check_curve_fit,validate_spec
            validate_spec(edit['spec'])
            fit=check_curve_fit(Image.open(path),edit['spec'])
            plan['source_region_fit']=fit
            if not fit['passed']:raise ValueError('source-region mapping does not align with actual curve pixels: '+str(fit))
            continue
        if edit['kind']=='highlight_path':
            from .source_graph import recover_segments,shortest_path_facts
            segments=recover_segments(Image.open(path),edit['spec'])
            if {tuple(s['edge']) for s in segments}!={tuple(sorted(e)) for e in edit['spec']['edges']}:
                raise ValueError('graph state edges differ from source-pixel geometry')
            if edit['path_edges']!=shortest_path_facts(edit['spec'])['path_edges']:
                raise ValueError('source marks differ from computed shortest path')
            continue
        bbox = edit.get('bbox')
        if not isinstance(bbox,list) or len(bbox)!=4 or any(type(x) not in (int,float) or not math.isfinite(x) or not 0<=x<=1 for x in bbox):
            raise ValueError('source edit bbox must have four normalized finite coordinates')
        x0,y0,x1,y1 = bbox
        if x0>=x1 or y0>=y1 or (x1-x0)*(y1-y0)>.04:
            raise ValueError('source edit bbox is empty or too large')
        if not isinstance(edit.get('text'),str) or not 1<=len(edit['text'])<=24 or not isinstance(edit.get('old_text'),str):
            raise ValueError('source edit needs short replacement and old label text')
        # Fitting text is deterministic. Preserve the authored erase region while
        # extending the replacement's bounds; any neighboring ink remains protected.
        w,h=original_size
        scale=min((VIEWPORT[2]-VIEWPORT[0]-12)/w,(VIEWPORT[3]-VIEWPORT[1]-12)/h)
        min_size=math.ceil(23/scale)
        measure=ImageDraw.Draw(Image.new('RGB',(1,1)))
        needed_w=(measure.textlength(edit['text'],font=font(min_size))+8)/w
        needed_h=(min_size/.78+4)/h
        if x1-x0<needed_w or y1-y0<needed_h:
            edit.setdefault('erase_bbox',list(bbox))
            cx,cy=(x0+x1)/2,(y0+y1)/2
            bw,bh=max(needed_w,x1-x0),max(needed_h,y1-y0)
            edit['bbox']=[max(0,cx-bw/2),max(0,cy-bh/2),min(1,cx+bw/2),min(1,cy+bh/2)]
            if (edit['bbox'][2]-edit['bbox'][0])*(edit['bbox'][3]-edit['bbox'][1])>.04:
                raise ValueError('legible replacement requires too much source-image area')
            edit['layout_adjustment']='expanded replacement to >=23px; erase restricted to original label box'
    for i,scene in enumerate(plan['scenes']):
        scene.pop('state_visual',None)
        lines = scene.get('teaching_lines')
        if not isinstance(lines,list) or not 1<=len(lines)<=4 or any(not isinstance(x,str) or not x or len(x)>200 for x in lines):
            raise ValueError(f'scene {i}: one to four short teaching statements required')
        # Line breaking is a renderer responsibility, not a semantic-model retry.
        if len(lines)>2 or any(len(x)>65 for x in lines):
            scene['authored_teaching_lines']=lines
            draw=ImageDraw.Draw(Image.new('RGB',(1,1)))
            scene['teaching_lines']=wrapped('   |   '.join(lines),draw,font(32),1440)
            if len(scene['teaching_lines'])>2:
                raise ValueError(f'scene {i}: teaching text exceeds two full-width lines; shorten it')
        annotations = scene.get('source_annotations', []) if allow_overlays else []
        validate_annotations(annotations)
        if allow_overlays and i == 0 and annotations:
            raise ValueError('scene 0 must show the unedited original; no source_annotations')
        scene['source_visual'] = {'path':str(path.resolve()),'sha256':source_hash, 'annotations': annotations,
                                  'edits':[{**e,'reveal':i==e['from_scene']} if e['kind'] in {'fill_between','highlight_path'} else e for e in edits if i>=e['from_scene']]}
    plan['source_preservation'] = {'source_sha256':source_hash,'viewport':list(VIEWPORT),
        'policy':('original image with model-proposed target annotations; no geometric transformation guarantee' if allow_overlays else
                  'original image with recoloring of source ink along computed shortest-path edges' if allow_graphs else
                  'original image with bounded background shading between declared curves' if allow_regions else
                  'original image with explicit target replacement rectangles only'),
        'authorization_and_location':'model proposed; requires independent comparison to source and task'}
    return plan


@lru_cache(maxsize=8)
def source_image(path, sha256):
    if file_hash(path)!=sha256:
        raise ValueError('source image content changed after binding')
    return Image.open(path).convert('RGB')


def edited_reference(visual, apply_edits=True, progress=1.):
    original = source_image(visual['path'],visual['sha256'])
    image = original.copy()
    draw = ImageDraw.Draw(image)
    issues = []
    for edit in visual['edits'] if apply_edits else []:
        if edit.get('kind')=='highlight_path':
            from .source_graph import apply_path
            image=apply_path(image,edit['spec'],edit['path_edges'],min(1.,progress/.75) if edit.get('reveal') else 1.)
            draw=ImageDraw.Draw(image)
            continue
        if edit.get('kind','replace_text')=='fill_between':
            from .source_region import apply_region
            image=apply_region(image,edit['spec'],min(1.,progress/.75) if edit.get('reveal') else 1.,
                               edit.get('restriction','all'))
            draw=ImageDraw.Draw(image)
            continue
        w,h=image.size
        x0,y0,x1,y1=[round(x*scale) for x,scale in zip(edit['bbox'],(w,h,w,h))]
        size=max(8,int((y1-y0)*.78))
        while size>8 and draw.textlength(edit['text'],font=font(size))>x1-x0-4:
            size-=1
        face=font(size)
        text_box=draw.textbbox((0,0),edit['text'],font=face)
        glyph_w,glyph_h=text_box[2]-text_box[0],text_box[3]-text_box[1]
        if glyph_w>x1-x0-2 or glyph_h>y1-y0-2:
            issues.append({'kind':'source_edit_text_overflow','edit':edit['id']})
        # Preserve colored geometry even when the model's target rectangle overlaps it.
        # Black geometry cannot be distinguished from black text by this backend;
        # border-touching dark ink is rejected as a possible truncated label/line.
        patch=np.array(image.crop((x0,y0,x1,y1)))
        low,high=patch.min(axis=2),patch.max(axis=2)
        gray_ink=(high.astype(int)-low.astype(int)<12)&(low<245)
        erase=edit.get('erase_bbox',edit['bbox'])
        ex0,ey0,ex1,ey1=[round(x*scale) for x,scale in zip(erase,(w,h,w,h))]
        erase_mask=np.zeros_like(gray_ink)
        erase_mask[max(0,ey0-y0):min(y1-y0,ey1-y0),max(0,ex0-x0):min(x1-x0,ex1-x0)]=True
        gray_ink &= erase_mask
        protected=(low<245)&~gray_ink
        border=np.zeros_like(gray_ink);border[[0,-1],:]=True;border[:,[0,-1]]=True
        if np.count_nonzero(gray_ink & border)>2:
            issues.append({'kind':'source_target_box_intersects_dark_ink_boundary','edit':edit['id']})
        overlay=Image.new('RGBA',(x1-x0,y1-y0),(0,0,0,0))
        ImageDraw.Draw(overlay).text(((overlay.width-glyph_w)/2-text_box[0],(overlay.height-glyph_h)/2-text_box[1]),edit['text'],font=face,fill='#125d84')
        if np.count_nonzero((np.asarray(overlay)[:,:,3]>32)&protected)>2:
            issues.append({'kind':'source_replacement_overlaps_colored_geometry','edit':edit['id']})
        patch[gray_ink]=255
        composed=Image.fromarray(patch).convert('RGBA')
        composed.alpha_composite(overlay)
        image.paste(composed.convert('RGB'),(x0,y0))
        scale=min((VIEWPORT[2]-VIEWPORT[0])/w,(VIEWPORT[3]-VIEWPORT[1])/h)
        if size*scale<21:
            issues.append({'kind':'source_edit_too_small','edit':edit['id'],'final_font_px':round(size*scale,1)})
    return image,issues


def render_source(scene, progress, *, index, total, mode):
    image=Image.new('RGB',SIZE,'#f5f7fb')
    draw=ImageDraw.Draw(image)
    draw.text((48,24),scene['title'],font=font(38),fill='#14283e')
    draw.rounded_rectangle(VIEWPORT,radius=15,fill='white',outline='#dce4ef',width=2)
    reference,issues=edited_reference(scene['source_visual'],apply_edits=mode=='code',progress=progress)
    original_width = reference.width
    reference.thumbnail((VIEWPORT[2]-VIEWPORT[0]-12,VIEWPORT[3]-VIEWPORT[1]-12),Image.Resampling.LANCZOS)
    if mode == 'code':
        overlay = ImageDraw.Draw(reference)
        w, h = reference.size
        for row in scene['source_visual'].get('annotations', []):
            x, y = row['x']*w, row['y']*h
            color = row.get('color', '#c62f40')
            kind = row['type']
            if kind == 'text':
                size = max(1, round(row['font_size'] * w / original_width)) if 'font_size' in row else 25
                face = font(size)
                align = row.get('align', 'left')
                extent = overlay.textlength(row['text'], font=face)
                x -= extent * (0.5 if align == 'center' else 1 if align == 'right' else 0)
                stroke = row.get('stroke_width', 1)
                box = overlay.textbbox((x, y), row['text'], font=face, stroke_width=stroke)
                if box[0] < 0 or box[1] < 0 or box[2] > w or box[3] > h:
                    issues.append({'kind': 'source_annotation_text_overflow', 'text': row['text']})
                overlay.text((x, y), row['text'], fill=color, font=face, stroke_width=stroke, stroke_fill='white')
            elif kind == 'circle':
                r = row['r']*min(w, h)
                overlay.ellipse((x-r, y-r, x+r, y+r), outline=color, width=3)
            elif kind == 'rect':
                overlay.rectangle((x, y, row['x2']*w, row['y2']*h), outline=color, width=3)
            else:
                x2, y2 = row['x2']*w, row['y2']*h
                overlay.line((x, y, x2, y2), fill=color, width=3)
                angle = math.atan2(y2-y, x2-x)
                overlay.polygon([(x2, y2), (x2-12*math.cos(angle-.5), y2-12*math.sin(angle-.5)),
                                 (x2-12*math.cos(angle+.5), y2-12*math.sin(angle+.5))], fill=color)
    image.paste(reference,((SIZE[0]-reference.width)//2,VIEWPORT[1]+(VIEWPORT[3]-VIEWPORT[1]-reference.height)//2))
    lines=scene['teaching_lines'] if mode=='code' else wrapped(scene.get('slide_text') or scene['caption'],draw,font(32),1440)
    if len(lines)>2:issues.append({'kind':'source_teaching_panel_overflow'})
    for j,line in enumerate(lines[:2]):
        if draw.textlength(line,font=font(32))>1450:issues.append({'kind':'source_teaching_line_overflow','line':line})
        draw.text((75,669+j*43),line,font=font(32),fill='#203b55')
    captions=wrapped(scene['caption'],draw,font(27),1480)
    if len(captions)>2:issues.append({'kind':'source_caption_overflow'})
    for j,line in enumerate(captions[:2]):draw.text((60,782+j*34),line,font=font(27),fill='#243d54')
    draw.text((48,865),f'{index+1:02d} / {total:02d}',font=font(18),fill='#64788c')
    draw.rectangle((180,876,1540,881),fill='#d9e4ed')
    draw.rectangle((180,876,180+1360*(index+progress)/total,881),fill='#1868ae')
    return image,issues
