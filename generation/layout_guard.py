"""Check settled rendered text boxes; intentional animation motion is evaluated separately."""
import numpy as np


def check_layout(scene):
    from manim import ImageMobject, VMobject, config
    from generation.layout_policy import text_objects
    texts = []
    for obj in text_objects(scene.get_mobject_family_members()):
        # Exclude invisible objects retained by animation bookkeeping.
        if not any(np.any(child.get_fill_opacity() > 0.05) for child in obj.get_family()):
            continue
        if any(obj is old for old in texts):
            continue
        texts.append(obj)
    # Cairo orders by z-index and then scene insertion order. An opaque image
    # drawn above a label can hide it even when text boxes never intersect.
    family = scene.get_mobject_family_members()
    order = {id(obj): i for i, obj in enumerate(family)}
    images = [obj for obj in family if isinstance(obj, ImageMobject)
              and np.asarray(obj.get_pixel_array()).shape[-1] == 4
              and np.mean(np.asarray(obj.get_pixel_array())[:, :, 3] >= 250) > .95]
    failures = []
    from generation.layout_policy import scene_box, overlaps
    all_images=images  # Transparent annotation layers may intentionally share a footprint.
    for i,obj in enumerate(all_images):
        for other in all_images[:i]:
            if overlaps(scene_box(obj),scene_box(other)):
                failures.append({'kind':'image_overlap','bbox':scene_box(obj),'other_bbox':scene_box(other)})
    source=getattr(scene,'source_image',None)
    text_family={id(child) for text in texts for child in text.get_family()}
    geometry=[obj for obj in family if isinstance(obj,VMobject) and id(obj) not in text_family
              and obj.width>0 and obj.height>0 and getattr(obj,'_layout_role',None)!='source'
              and obj.width*obj.height < config.frame_width*config.frame_height*.8]

    for i, obj in enumerate(texts):
        label = str(getattr(obj, 'text', getattr(obj, 'tex_string', 'text')))[:100]
        if source is not None and getattr(obj,'_layout_role',None) != 'source' and overlaps(scene_box(obj),scene_box(source)):
            failures.append({'kind':'text_over_source','text':label,'bbox':scene_box(obj)})
        panel=getattr(scene,'layout_contract',{}).get('teaching_panel')
        if panel and getattr(obj,'_layout_role',None) != 'source' and obj is not getattr(scene,'title',None):
            from generation.layout_policy import panel_box
            bounds=panel_box(panel,config.frame_width,config.frame_height)
            box=scene_box(obj)
            if box[0]<bounds[0]-.001 or box[1]<bounds[1]-.001 or box[2]>bounds[2]+.001 or box[3]>bounds[3]+.001:
                failures.append({'kind':'text_outside_teaching_panel','text':label,'bbox':box})
        x0, x1 = obj.get_left()[0], obj.get_right()[0]
        y0, y1 = obj.get_bottom()[1], obj.get_top()[1]
        if getattr(obj,'_layout_role',None) in ('caption','external_label'):
            for shape in geometry:
                sx0,sy0,sx1,sy1=scene_box(shape)
                area=max(0,min(x1,sx1)-max(x0,sx0))*max(0,min(y1,sy1)-max(y0,sy0))
                if (area>.12*obj.width*obj.height and np.any(shape.get_fill_opacity()>.9)):
                    failures.append({'kind':'text_occluded_by_geometry','text':label,'geometry':type(shape).__name__})
                    break
        if x0 < -config.frame_width/2+.05 or x1 > config.frame_width/2-.05 or y0 < -config.frame_height/2+.05 or y1 > config.frame_height/2-.05:
            visible_area = max(0., min(x1, config.frame_width/2)-max(x0, -config.frame_width/2))*max(0., min(y1, config.frame_height/2)-max(y0, -config.frame_height/2))
            failures.append({'kind': 'text_outside_frame', 'text': label,
                             'outside_fraction': max(0., 1-visible_area/(obj.width*obj.height)),
                             'bbox': [float(x0),float(y0),float(x1),float(y1)]})
        line_count=max(1,len(getattr(obj,'original_text','').splitlines()))
        if obj.height/line_count/config.frame_height*config.pixel_height < 16:
            failures.append({'kind': 'text_too_small', 'text': label})
        for image in images:
            if (image.z_index, order[id(image)]) <= (obj.z_index, order[id(obj)]):
                continue
            dx = min(x1, image.get_right()[0])-max(x0, image.get_left()[0])
            dy = min(y1, image.get_top()[1])-max(y0, image.get_bottom()[1])
            if dx > 0 and dy > 0 and dx*dy > .12*obj.width*obj.height:
                failures.append({'kind': 'text_occluded_by_image', 'text': label})
        for other in texts[:i]:
            dx = min(x1, other.get_right()[0])-max(x0, other.get_left()[0])
            dy = min(y1, other.get_top()[1])-max(y0, other.get_bottom()[1])
            if dx > 0 and dy > 0 and dx*dy > .12*min(obj.width*obj.height, other.width*other.height):
                failures.append({'kind': 'text_overlap', 'text': label,
                                 'other': str(getattr(other, 'text', 'text'))[:100]})
    return {'time_s': float(scene.time), 'valid': not failures, 'text_count': len(texts), 'failures': failures[:12]}
