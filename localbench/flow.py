"""Directed schematic spiral paths computed in pixel-isotropic coordinates."""
from __future__ import annotations

import math

from PIL import ImageColor,ImageDraw

VERSION='localbench-directed-flow-v1'
PANEL=(64,112,896,302)


def compile_flow(spec):
    allowed={'type','x','y','radius_start','radius_end','turns','start_angle','rotation','color','stroke','markers'}
    if set(spec)-allowed:raise ValueError('flow_path has unsupported fields; no independent translation/appearance')
    if 'x' not in spec or 'y' not in spec:raise ValueError('flow_path requires explicit x and y coordinates')
    def number(key,default,lo,hi):
        v=spec.get(key,default)
        if type(v) not in (int,float) or not math.isfinite(v) or not lo<=v<=hi:raise ValueError('invalid flow '+key)
        return v
    x=number('x',.5,0,1);y=number('y',.5,0,1)
    r0=number('radius_start',.4,.01,.49);r1=number('radius_end',.09,.01,.49)
    turns=number('turns',1,.05,3);angle=number('start_angle',0,-360,360)
    rotation=spec.get('rotation','ccw')
    if rotation not in {'ccw','cw'}:raise ValueError('flow rotation must be ccw or cw')
    markers=spec.get('markers',2)
    if type(markers) is not int or not 0<=markers<=4:raise ValueError('flow markers must be integer 0..4')
    stroke=number('stroke',3,1,6)
    color=spec.get('color','#1868ae');ImageColor.getrgb(color)
    px,py,w,h=PANEL;cx=px+x*w;cy=py+y*h
    count=max(129,math.ceil(turns*100)+1)
    points=[]
    for i in range(count):
        t=i/(count-1);r=(r0+(r1-r0)*t)*h
        a=math.radians(angle)+(1 if rotation=='ccw' else -1)*2*math.pi*turns*t
        points.append([cx+r*math.cos(a),cy-r*math.sin(a)])
    bounds=[min(p[0] for p in points)-6,min(p[1] for p in points)-6,
            max(p[0] for p in points)+6,max(p[1] for p in points)+6]
    if bounds[0]<px or bounds[1]<py or bounds[2]>px+w or bounds[3]>py+h:
        raise ValueError('flow path/arrows exceed diagram panel')
    return {'version':VERSION,'points':points,'center':[cx,cy],'bounds':bounds,
            'radius_start_px':r0*h,'radius_end_px':r1*h,'rotation':rotation,
            'radial_direction':'inward' if r1<r0 else 'outward' if r1>r0 else 'constant',
            'stroke':stroke,'color':color,'markers':markers,
            'scope':'Qualitative directed path; not measured fluid dynamics or a calibrated velocity field.'}


def draw_flow(image,spec,progress):
    c=compile_flow(spec);points=c['points'];draw=ImageDraw.Draw(image)
    draw.line([tuple(p) for p in points],fill=c['color'],width=int(c['stroke']))
    for fraction in (.2,.5,.8):
        i=round(fraction*(len(points)-1));x,y=points[i];a,b=points[i-1],points[min(i+1,len(points)-1)]
        angle=math.atan2(b[1]-a[1],b[0]-a[0])
        # Arrow tips follow increasing path parameter, including radial motion.
        draw.polygon([(x,y),(x-10*math.cos(angle-.45),y-10*math.sin(angle-.45)),
                      (x-10*math.cos(angle+.45),y-10*math.sin(angle+.45))],fill=c['color'])
    for j in range(c['markers']):
        t=(progress+j/c['markers'])%1;i=t*(len(points)-1);lo=int(i);alpha=i-lo
        a,b=points[lo],points[min(lo+1,len(points)-1)];x=a[0]+alpha*(b[0]-a[0]);y=a[1]+alpha*(b[1]-a[1])
        draw.ellipse((x-4,y-4,x+4,y+4),fill=c['color'])
    return c['bounds']


def plan_flow_receipts(plan):
    return [{'scene':i,'primitive':j,**compile_flow(p)} for i,s in enumerate(plan['scenes'])
            for j,p in enumerate(s.get('primitives',[])) if p.get('type')=='flow_path']


def path_intersects_box(points,box,padding=5):
    """Check actual line segments, not the whole spiral's enclosing rectangle."""
    x0,y0,x1,y1=box;bounds=((x0-padding,x1+padding),(y0-padding,y1+padding))
    for a,b in zip(points,points[1:]):
        lo,hi=0.,1.
        for axis,(start,end) in enumerate(bounds):
            delta=b[axis]-a[axis]
            if abs(delta)<1e-12:
                if not start<=a[axis]<=end:lo,hi=1.,0.;break
            else:
                t0,t1=sorted(((start-a[axis])/delta,(end-a[axis])/delta))
                lo=max(lo,t0);hi=min(hi,t1)
                if lo>hi:break
        if lo<=hi:return True
    return False
