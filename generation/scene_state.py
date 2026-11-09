"""Stateful instructional primitives with inspectable object ownership.

These helpers expose operations, not task answers. Scene code still selects
the original inputs, transformations and explanations from its task contract.
"""
from fractions import Fraction
import math
import numpy as np
from manim import BLUE,WHITE,PI,VGroup,Square,Text,MathTex,Swap,ReplacementTransform,FadeIn,FadeOut,VMobject,Dot,MoveAlongPath
from generation.layout_policy import tag


class ArraySlots:
    def __init__(self, values, *, center=(0,.5,0), width=1.5, gap=.3):
        if not values:raise ValueError('array must not be empty')
        self.values=list(values);self.boxes=[];self.labels=[];self.history=[list(values)]
        start=np.asarray(center,dtype=float)-np.array([(len(values)-1)*(width+gap)/2,0,0])
        for index,value in enumerate(values):
            box=Square(side_length=width,color=BLUE).move_to(start+[index*(width+gap),0,0])
            label=tag(Text(str(value),font_size=40,color=WHITE).move_to(box),'anchored')
            self.boxes.append(box);self.labels.append(label)
        self.group=VGroup(*self.boxes,*self.labels)

    def verify(self):
        if len({id(label) for label in self.labels})!=len(self.values):raise ValueError('duplicate number object')
        for index,(value,label,box) in enumerate(zip(self.values,self.labels,self.boxes)):
            if str(value)!=label.text or np.linalg.norm(label.get_center()-box.get_center())>.02:
                raise ValueError(f'array slot {index} does not contain its declared value')
        return {'valid':True,'values':list(self.values),'one_value_per_slot':True}

    def swap(self,scene,i,j,*,run_time=2):
        if i==j or min(i,j)<0 or max(i,j)>=len(self.values):raise ValueError('invalid array swap')
        self.verify()
        scene.play(Swap(self.labels[i],self.labels[j],path_arc=PI/2),run_time=run_time)
        self.values[i],self.values[j]=self.values[j],self.values[i]
        self.labels[i],self.labels[j]=self.labels[j],self.labels[i]
        self.history.append(list(self.values));return self.verify()


class FormulaSlot:
    def __init__(self,*,position=(0,.5,0),font_size=40):
        self.position=position;self.font_size=font_size;self.current=None;self.history=[]

    def replace(self,scene,tex,*,run_time=1.5):
        new=tag(MathTex(tex,font_size=self.font_size).move_to(self.position),'anchored')
        old=self.current
        scene.play(FadeIn(new) if old is None else ReplacementTransform(old,new),run_time=run_time)
        self.current=new;self.history.append(tex)
        if old is not None and any(obj is old for obj in scene.get_mobject_family_members()):
            raise ValueError('old formula remained after replacement')
        return new

    def clear(self,scene,*,run_time=1):
        if self.current is not None:
            old=self.current;scene.play(FadeOut(old),run_time=run_time);scene.remove(old);self.current=None


def cantor_intervals(level):
    if type(level) is not int or not 0<=level<=12:raise ValueError('invalid Cantor level')
    intervals=[(Fraction(0),Fraction(1))]
    for _ in range(level):
        intervals=[part for a,b in intervals for part in [(a,a+(b-a)/3),(b-(b-a)/3,b)]]
    assert sum(b-a for a,b in intervals)==Fraction(2,3)**level
    return intervals


def interior_angles(vertices):
    points=np.asarray(vertices,dtype=float)
    if points.shape not in ((3,2),(3,3)):raise ValueError('three vertices required')
    angles=[]
    for i,p in enumerate(points):
        a=points[(i+1)%3]-p;b=points[(i-1)%3]-p
        if np.linalg.norm(a)*np.linalg.norm(b)<1e-8:raise ValueError('degenerate triangle')
        angles.append(math.acos(float(np.clip(a@b/(np.linalg.norm(a)*np.linalg.norm(b)),-1,1))))
    if min(angles)<1e-6 or abs(sum(angles)-math.pi)>1e-6:raise ValueError('degenerate triangle')
    return angles


def assert_closed_path(points,tolerance=1e-6):
    points=np.asarray(points,dtype=float)
    if len(points)<4 or np.linalg.norm(points[0]-points[-1])>tolerance:
        raise ValueError('instruction requires a single continuous closed flow path')
    return True


class FlowPath:
    """One connected path drives both the visible line and its moving marker."""
    def __init__(self,points,*,closed=False,color=BLUE):
        self.points=np.asarray(points,dtype=float)
        if self.points.ndim!=2 or self.points.shape[1]!=3 or len(self.points)<2:
            raise ValueError('flow path needs three-coordinate vertices')
        if closed:assert_closed_path(self.points)
        if any(np.linalg.norm(a-b)<1e-8 for a,b in zip(self.points,self.points[1:])):
            raise ValueError('zero-length flow segment')
        self.closed=closed
        self.shape=VMobject(stroke_color=color,stroke_width=4).set_points_as_corners(self.points)

    def trace(self,scene,*,run_time=3,color=WHITE):
        marker=Dot(self.shape.get_start(),radius=.08,color=color)
        scene.add(marker);scene.play(MoveAlongPath(marker,self.shape),run_time=run_time)
        if np.linalg.norm(marker.get_center()-self.shape.get_end())>.02:raise ValueError('flow marker did not follow the diagram')
        return marker
