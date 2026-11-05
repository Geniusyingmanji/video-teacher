"""Shared scene geometry: source ownership, separate panels and label clearance."""
import math


def source_panels(size):
    """Use height for portrait references and width for landscape references."""
    width, height = size
    if height >= width * .85:
        return [0.04, 0.16, 0.48, 0.92], [0.54, 0.19, 0.96, 0.88]
    return [0.05, 0.16, 0.95, 0.61], [0.05, 0.67, 0.95, 0.94]


def overlaps(a, b, gap=0.):
    return a[0] < b[2]+gap and a[2] > b[0]-gap and a[1] < b[3]+gap and a[3] > b[1]-gap


def place_box(box, bounds, occupied, gap=.12):
    """Find the nearest clear position without shrinking a label or leaving its panel."""
    width, height = box[2]-box[0], box[3]-box[1]
    if width > bounds[2]-bounds[0] or height > bounds[3]-bounds[1]:
        return None
    xs={box[0],bounds[0],bounds[2]-width}
    ys={box[1],bounds[1],bounds[3]-height}
    for other in occupied:
        xs.update((other[0]-gap-width,other[2]+gap))
        ys.update((other[1]-gap-height,other[3]+gap))
    choices=[]
    for x in xs:
        for y in ys:
            candidate=[x,y,x+width,y+height]
            if x < bounds[0]-1e-7 or y < bounds[1]-1e-7 or candidate[2] > bounds[2]+1e-7 or candidate[3] > bounds[3]+1e-7:
                continue
            if any(overlaps(candidate,other,gap-1e-7) for other in occupied):
                continue
            choices.append((math.hypot(x-box[0],y-box[1]),abs(x-box[0]),candidate))
    return min(choices,key=lambda row:row[:2])[2] if choices else None


def tag(obj, role):
    for child in obj.get_family():
        child._layout_role=role
    return obj


def scene_box(obj):
    return [float(obj.get_left()[0]),float(obj.get_bottom()[1]),float(obj.get_right()[0]),float(obj.get_top()[1])]


def panel_box(viewport, width, height):
    x0,y0,x1,y1=viewport
    return [(x0-.5)*width,(.5-y1)*height,(x1-.5)*width,(.5-y0)*height]


def prepare_text(obj, maximum_width, minimum_pixels=18):
    """Wrap prose and enlarge undersized glyphs; never crop or shrink to fit."""
    import textwrap
    from manim import Text,config
    if type(obj) is not Text or getattr(obj,'_layout_prepared',None)==maximum_width:
        return
    text=getattr(obj,'original_text',obj.text)
    original=text
    line_count=max(1,len(text.splitlines()))
    line_pixels=obj.height/line_count/config.frame_height*config.pixel_height
    if line_pixels < minimum_pixels:
        obj.scale(minimum_pixels/max(line_pixels,.001))
    if obj.width > maximum_width:
        longest=max(map(len,text.splitlines()),default=1)
        limit=max(1,int(longest*maximum_width/obj.width))
        while limit>=1:
            wrapped='\n'.join(part for line in text.splitlines()
                               for part in (textwrap.wrap(line,width=limit,break_long_words=False,break_on_hyphens=False) or ['']))
            replacement=Text(wrapped,font_size=obj.font_size,font=obj.font,color=obj.get_color(),
                             slant=obj.slant,weight=obj.weight,t2c=obj.t2c)
            if replacement.width <= maximum_width+1e-7:
                replacement.move_to(obj)
                obj.become(replacement)
                for key in ('text','original_text','initial_height','_font_size'):
                    if hasattr(replacement,key):setattr(obj,key,getattr(replacement,key))
                break
            if limit==1:break
            limit-=1
    obj._layout_original_text=original
    obj._layout_prepared=maximum_width


def arrange_labels(scene, contract, pending=()):
    """Resolve text collisions before reveals; source edits retain pixel coordinates.

    Each existing label keeps its current location if there is room. New labels
    move the shortest possible distance inside the same semantic panel. No text
    is deleted, truncated or reduced to make a crowded scene pass.
    """
    import numpy as np
    from manim import Text, MarkupText, Tex, config
    objects=list(scene.get_mobject_family_members())
    for obj in pending:
        if hasattr(obj,'get_family'):objects.extend(obj.get_family())
    texts=[];seen=set()
    for obj in objects:
        if id(obj) in seen or not isinstance(obj,(Text,MarkupText,Tex)) or obj.width<=0 or obj.height<=0:
            continue
        seen.add(id(obj));texts.append(obj)
    occupied=[];movable=[]
    for obj in texts:
        role=getattr(obj,'_layout_role',None)
        if role=='source':continue
        if role in ('title','caption') or obj is getattr(scene,'title',None):occupied.append(scene_box(obj))
        else:movable.append(obj)
    bounds=panel_box(contract.get('teaching_panel') or [.05,.18,.95,.73],config.frame_width,config.frame_height)
    changes=[]
    for obj in movable:
        prepare_text(obj,bounds[2]-bounds[0])
        original=scene_box(obj)
        placed=place_box(original,bounds,occupied)
        if placed is not None:
            delta=np.array([placed[0]-original[0],placed[1]-original[1],0.])
            if np.linalg.norm(delta)>.001:
                obj.shift(delta)
                changes.append({'text':getattr(obj,'text',getattr(obj,'tex_string','')),'from':original,'to':placed})
        occupied.append(scene_box(obj))
    return changes
