"""2-D numeric diagrams: grid, vectors, matrix and readouts share one state."""
from __future__ import annotations

import math
from PIL import ImageDraw

VERSION = 'computed-linear-algebra-v1'


def number(x):
    if type(x) not in (int,float) or not math.isfinite(x) or abs(x)>100:
        raise ValueError('finite bounded numeric state required')
    return float(x)


def vector(x):
    if not isinstance(x,list) or len(x)!=2:raise ValueError('two-dimensional vector required')
    return [number(v) for v in x]


def matrix(x):
    if not isinstance(x,list) or len(x)!=2:raise ValueError('2x2 matrix required')
    return [vector(r) for r in x]


def mul(a,v):
    return [sum(x*y for x,y in zip(r,v)) for r in a]


def product(b,a):
    return [[sum(b[i][k]*a[k][j] for k in range(2)) for j in range(2)] for i in range(2)]


def compile_state(spec, progress=1):
    if not isinstance(spec,dict) or spec.get('type')!='linear_algebra':raise ValueError('expected linear_algebra')
    mode=spec.get('operation')
    allowed={'dot':{'u','v','v_end'},'map':{'matrix','v'},'composition':{'first','second','v'},'basis':{'basis','v'}}
    if mode not in allowed or set(spec)-({'type','operation'}|allowed[mode]):
        raise ValueError('unsupported operation or independently authored readout/geometry')
    if type(progress) not in (int,float) or not math.isfinite(progress) or not 0<=progress<=1:
        raise ValueError('progress must be in [0,1]')
    t=float(progress);v=vector(spec.get('v'));identity=[[1.,0.],[0.,1.]]
    if mode=='dot':
        u=vector(spec.get('u'));end=vector(spec.get('v_end',spec['v']))
        current=[(1-t)*a+t*b for a,b in zip(v,end)]
        value=sum(a*b for a,b in zip(u,current));norm=sum(a*a for a in u)
        if norm<1e-12:raise ValueError('dot projection requires a nonzero reference vector')
        projection=[value/norm*a for a in u]
        return {'version':VERSION,'operation':mode,'vectors':{'u':u,'v':current,'projection':projection},
                'dot':value,'readout':f'u dot v = {value:.4g}',
                'grid_matrix':identity,'bounds_vectors':[u,v,end,projection]}
    if mode=='map':
        a=matrix(spec.get('matrix'));final=mul(a,v)
        current=[[identity[i][j]*(1-t)+a[i][j]*t for j in range(2)] for i in range(2)]
        return {'version':VERSION,'operation':mode,'vectors':{'v':v,'current':mul(current,v),'target Mv':final},
                'matrix':a,'grid_matrix':current,'determinant':a[0][0]*a[1][1]-a[0][1]*a[1][0],
                'readout':f'Current M(t)v = ({mul(current,v)[0]:.4g}, {mul(current,v)[1]:.4g})',
                'bounds_vectors':[v,final,*zip(*a)]}
    if mode=='composition':
        a=matrix(spec.get('first'));b=matrix(spec.get('second'));ba=product(b,a)
        intermediate=mul(a,v);sequential=mul(b,intermediate);direct=mul(ba,v)
        if any(abs(x-y)>1e-9 for x,y in zip(sequential,direct)):raise ValueError('composition mismatch')
        if t<=.5:
            current=[[identity[i][j]*(1-2*t)+a[i][j]*2*t for j in range(2)] for i in range(2)]
        else:
            local=[[identity[i][j]*(2-2*t)+b[i][j]*(2*t-1) for j in range(2)] for i in range(2)]
            current=product(local,a)
        return {'version':VERSION,'operation':mode,'matrix':ba,'grid_matrix':current,
                'vectors':{'v':v,'current':mul(current,v),'B(Av)':sequential,'(BA)v':direct},
                'readout':(f'B(Av) = (BA)v = ({direct[0]:.4g}, {direct[1]:.4g})' if t==1 else f'Current = ({mul(current,v)[0]:.4g}, {mul(current,v)[1]:.4g})'),
                'bounds_vectors':[v,intermediate,direct,*zip(*a),*zip(*ba)]}
    basis=matrix(spec.get('basis'));det=basis[0][0]*basis[1][1]-basis[0][1]*basis[1][0]
    if abs(det)<1e-8:raise ValueError('change of basis requires an invertible basis')
    inverse=[[basis[1][1]/det,-basis[0][1]/det],[-basis[1][0]/det,basis[0][0]/det]]
    coordinates=mul(inverse,v);reconstructed=mul(basis,coordinates)
    if any(abs(x-y)>1e-8 for x,y in zip(v,reconstructed)):raise ValueError('basis reconstruction mismatch')
    return {'version':VERSION,'operation':mode,'matrix':basis,'grid_matrix':identity,
            'vectors':{'same v':v,'b1':[basis[0][0],basis[1][0]],'b2':[basis[0][1],basis[1][1]]},
            'coordinates':coordinates,'reconstructed':reconstructed,
            'readout':f'New coords = ({coordinates[0]:.4g}, {coordinates[1]:.4g})',
            'bounds_vectors':[v,*zip(*basis)]}


def draw(image,spec,progress):
    from .scene import font
    state=compile_state(spec,progress);final=compile_state(spec,1)
    origin=(610,270);radius=110
    bounds=[*state['bounds_vectors'],*final['bounds_vectors']]
    # Transformed grid uses half-unit extent, so it stays inside the same scale.
    scale=radius/max(1,max(math.hypot(*v) for v in bounds))
    painter=ImageDraw.Draw(image);boxes=[]
    def point(v):return (origin[0]+v[0]*scale,origin[1]-v[1]*scale)
    def label(position,text,color='#183550',size=20):
        face=font(size);boxes.append({'text':text,'bbox':list(painter.textbbox(position,text,font=face))})
        painter.text(position,text,font=face,fill=color)
    for i in range(-2,3):
        for a,b in [([i/4,-.5],[i/4,.5]),([-.5,i/4],[.5,i/4])]:
            painter.line([point(mul(state['grid_matrix'],a)),point(mul(state['grid_matrix'],b))],fill='#c3d0dc',width=2)
    painter.line([(405,270),(815,270)],fill='#8295a6',width=2)
    painter.line([(610,125),(610,395)],fill='#8295a6',width=2)
    label((615,275),'O',size=18)
    for (name,v),color in zip(state['vectors'].items(),['#2265a0','#d36a20','#218064','#8e4ba5','#b23c50']):
        x,y=point(v);painter.line([origin,(x,y)],fill=color,width=3)
        angle=math.atan2(y-origin[1],x-origin[0])
        if math.hypot(x-origin[0],y-origin[1])>1:
            painter.polygon([(x,y),(x-10*math.cos(angle-.4),y-10*math.sin(angle-.4)),
                             (x-10*math.cos(angle+.4),y-10*math.sin(angle+.4))],fill=color)
        index=list(state['vectors']).index(name)
        label((75,140+index*36),f'{name}: ({v[0]:.3g}, {v[1]:.3g})',color,size=20)
    label((380,412),state['readout'],size=22)
    if 'matrix' in state:
        m=state['matrix'] if state['operation']=='basis' else state['grid_matrix'];label((380,100),f'Current matrix = [{m[0][0]:.3g}, {m[0][1]:.3g}; {m[1][0]:.3g}, {m[1][1]:.3g}]',size=21)
    return boxes


def receipts(plan):
    return [{'scene':i,'primitive':j,'initial':compile_state(p,0),'final':compile_state(p,1)}
            for i,s in enumerate(plan.get('scenes',[])) for j,p in enumerate(s.get('primitives',[]))
            if p.get('type')=='linear_algebra']
