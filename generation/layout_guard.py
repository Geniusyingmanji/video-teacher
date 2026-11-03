"""Check settled rendered text boxes; intentional animation motion is evaluated separately."""
import numpy as np


def check_layout(scene):
    from manim import Text, MarkupText, Tex, ImageMobject, config
    texts = []
    for obj in scene.get_mobject_family_members():
        if not isinstance(obj, (Text, MarkupText, Tex)) or obj.width <= 0 or obj.height <= 0:
            continue
        # Exclude invisible objects retained by animation bookkeeping.
        if not np.any(obj.get_fill_opacity() > 0.05):
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
    for i, obj in enumerate(texts):
        label = str(getattr(obj, 'text', getattr(obj, 'tex_string', 'text')))[:100]
        x0, x1 = obj.get_left()[0], obj.get_right()[0]
        y0, y1 = obj.get_bottom()[1], obj.get_top()[1]
        if x0 < -config.frame_width/2+.05 or x1 > config.frame_width/2-.05 or y0 < -config.frame_height/2+.05 or y1 > config.frame_height/2-.05:
            failures.append({'kind': 'text_outside_frame', 'text': label})
        if obj.height/config.frame_height*config.pixel_height < 16:
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
    return {'valid': not failures, 'text_count': len(texts), 'failures': failures[:12]}
