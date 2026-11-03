"""Source-pixel primitives; no model-authored letterbox conversion is needed."""
import numpy as np
from manim import Text, Rectangle, VGroup, VMobject, SurroundingRectangle, config, WHITE, BLACK
from PIL import Image


class SourcePrimitives:
    def __init__(self, source, allowed_boxes, viewport=None):
        self.image = Image.open(source).convert('RGB')
        self.size = self.image.size
        self.boxes = allowed_boxes
        x0,y0,x1,y1 = viewport or [0,0,1,1]
        self.scale = min(config.frame_width*(x1-x0)/self.size[0], config.frame_height*(y1-y0)/self.size[1])
        self.offset = np.array([((x0+x1)/2-.5)*config.frame_width, (.5-(y0+y1)/2)*config.frame_height,0])
        self.inset = max(3, 3/(self.scale*config.pixel_width/config.frame_width))

    def point(self, x, y):
        return self.offset + np.array([(x-self.size[0]/2)*self.scale, (self.size[1]/2-y)*self.scale, 0])

    def authorize(self, box):
        x0, y0, x1, y1 = box
        if not (0 <= x0 < x1 <= self.size[0] and 0 <= y0 < y1 <= self.size[1]):
            raise ValueError('source primitive outside image')
        if not any(a <= x0 and b <= y0 and c >= x1 and d >= y1 for a,b,c,d in self.boxes):
            raise ValueError('source primitive outside frozen target boxes')

    def text(self, text, box, color=BLACK, replace=True):
        self.authorize(box)
        x0, y0, x1, y1 = box
        width, height = (x1-x0-2*self.inset)*self.scale, (y1-y0-2*self.inset)*self.scale
        if width <= 0 or height <= 0:
            raise ValueError('source label box too small')
        label = Text(str(text), font_size=32, color=color)
        label.scale(min(width/label.width, height/label.height, 1))
        if label.height/config.frame_height*config.pixel_height < 16:
            raise ValueError('source label would be below 16 rendered pixels; improve localization/layout')
        label.move_to(self.point((x0+x1)/2, (y0+y1)/2))
        if not replace:
            return label
        crop = np.array(self.image.crop((x0+3, y0+3, x1-3, y1-3)))
        median = np.median(crop.reshape(-1,3), axis=0).astype(int)
        background = '#' + ''.join(f'{v:02x}' for v in median)
        patch = Rectangle(width=width, height=height, stroke_width=0, fill_color=background, fill_opacity=1)
        patch.move_to(label)
        return VGroup(patch, label)

    def curve(self, points, box, color='#D62728', stroke_width=3):
        self.authorize(box)
        if len(points) < 2 or stroke_width > 6 or stroke_width < 2:
            raise ValueError('invalid source curve')
        if any(not (box[0]+self.inset <= x <= box[2]-self.inset and box[1]+self.inset <= y <= box[3]-self.inset) for x,y in points):
            raise ValueError('curve leaves its authorized source box')
        curve = VMobject(stroke_color=color, stroke_width=stroke_width)
        curve.set_points_as_corners([self.point(x,y) for x,y in points])
        return curve

    def highlight(self, box, color='#D62728'):
        self.authorize(box)
        x0,y0,x1,y1 = box
        mark = Rectangle(width=(x1-x0-2*self.inset)*self.scale, height=(y1-y0-2*self.inset)*self.scale,
                         stroke_color=color, stroke_width=3)
        return mark.move_to(self.point((x0+x1)/2, (y0+y1)/2))
