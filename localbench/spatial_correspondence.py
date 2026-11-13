"""Viewer-facing paired endpoint diagrams from a checked substitution mapping.

Static endpoints share one projection scale and camera; matching retained labels
and colors make correspondence visible. The departure arrow is a schematic motion
cue, not a sampled reaction trajectory. No new chemical roles are inferred.
"""
import math

import numpy as np
from PIL import ImageDraw

from .spatial_graph import compile_graph, projection
from .spatial_inversion import verify_pair

VERSION = 'paired-spatial-correspondence-dev1'
INK = '#14283e'
RETAINED_COLORS = ['#1868ae', '#7748a8', '#995c20']


def compile_pair(spec, public_task):
    if not isinstance(spec,dict) or set(spec)!={'type','version','initial','product','roles'}:
        raise ValueError('paired diagram requires type/version/initial/product/roles')
    if spec['type']!='spatial_correspondence' or spec['version']!=VERSION:
        raise ValueError('unsupported correspondence version')
    roles=spec['roles']
    if not isinstance(roles,dict) or set(roles)!={'center','leaving','incoming','retained'}:
        raise ValueError('explicit correspondence roles required')
    for phase in ['initial','product']:
        compile_graph(spec[phase],public_task)
    check=verify_pair(spec['initial'],spec['product'],**roles)
    before={n['id']:n for n in spec['initial']['nodes']}
    after={n['id']:n for n in spec['product']['nodes']}
    for key in [roles['center'],*roles['retained']]:
        if before[key]['label']!=after[key]['label']:
            raise ValueError('retained identities must keep their displayed labels')
    return check


def geometry(spec):
    """Common metric projection; no separate normalization of the two diagrams."""
    _,basis=projection(spec['initial'])
    roles=spec['roles'];points={};depths={}
    for phase in ['initial','product']:
        nodes={n['id']:n for n in spec[phase]['nodes']}
        center=np.asarray(nodes[roles['center']]['xyz'])
        points[phase]={};depths[phase]={}
        for key,n in nodes.items():
            v=np.asarray(n['xyz'])-center
            points[phase][key]=np.array([np.dot(v,basis['right']),-np.dot(v,basis['up'])])
            depths[phase][key]=float(np.dot(v,basis['toward']))
    values=np.array([v for phase in points.values() for v in phase.values()])
    scale=min(60.,160/max(.1,np.abs(values[:,0]).max()),110/max(.1,np.abs(values[:,1]).max()))
    # A departure endpoint twice the initial C-LG radius is constructed separately
    # from the connected product graph; it is not a fifth product bond.
    dep=2*points['initial'][roles['leaving']]
    scale=min(scale,205/max(.1,abs(dep[0])),110/max(.1,abs(dep[1])))
    offsets={'initial':np.array([260.,270.]),'product':np.array([742.,270.])}
    positions={phase:{k:(p*scale+offsets[phase]).tolist() for k,p in rows.items()} for phase,rows in points.items()}
    departure=(dep*scale+offsets['product']).tolist()
    start=(points['initial'][roles['leaving']]*scale+offsets['product']).tolist()
    return positions,depths,{'camera':spec['initial']['camera'],'basis':basis,'common_scale':float(scale),
                            'departure_position':departure,'departure_start':start}


def draw_pair(image,spec,progress=0):
    from .scene import font
    from .stroke_style import draw_linear
    from .layout_geometry import text_contrast
    from PIL import Image
    if not isinstance(progress,(int,float)) or not math.isfinite(progress) or not 0<=progress<=1:
        raise ValueError('finite scene progress within0..1 required')
    draw=ImageDraw.Draw(image);positions,depths,projection_record=geometry(spec)
    roles=spec['roles'];boxes=[];issues=[];strokes=[]
    initial_labels={n['id']:n['label'] for n in spec['initial']['nodes']}
    color_map={key:color for key,color in zip(roles['retained'],RETAINED_COLORS)}
    color_map.update({roles['center']:INK,roles['leaving']:'#ba3d39',roles['incoming']:'#238746'})
    face=font(24)

    def text(x,y,value,size=22,anchor='mm',**metadata):
        f=font(size);box=list(draw.textbbox((x,y),value,font=f,anchor=anchor))
        record={'text':value,'bbox':box,**metadata}
        mask=Image.new('L',image.size,0)
        ImageDraw.Draw(mask).text((x,y),value,font=f,anchor=anchor,fill=255)
        issues.extend(text_contrast(image,mask,INK,record))
        draw.text((x,y),value,font=f,anchor=anchor,fill=INK)
        boxes.append(record)

    text(260,112,'Initial substrate')
    text(742,112,'Product + departing '+initial_labels[roles['leaving']])
    text(502,112,'Same view',18)
    for phase in ['initial','product']:
        graph=spec[phase];nodes={n['id']:n for n in graph['nodes']}
        radii={key:max(23,draw.textlength(n['label'],font=face)/2+8) for key,n in nodes.items()}
        for key,point in positions[phase].items():
            x,y=point;r=radii[key]
            if x-r<55 or x+r>977 or y-r<132 or y+r>376:
                raise ValueError('paired node outside reserved diagram area')
            for other,q in positions[phase].items():
                if key<other and np.linalg.norm(np.array(point)-q)<=r+radii[other]+6:
                    raise ValueError('paired labels overlap')
        for edge in graph['links']:
            a,b=edge['source'],edge['target'];p=np.array(positions[phase][a]);q=np.array(positions[phase][b])
            axis=q-p;length=np.linalg.norm(axis)
            if length<=radii[a]+radii[b]+10:raise ValueError('paired bond too short to inspect')
            axis/=length;p+=axis*radii[a];q-=axis*radii[b]
            normal=np.array([-axis[1],axis[0]])
            radius=np.linalg.norm(np.array(nodes[b]['xyz'])-nodes[a]['xyz'])
            depth=(depths[phase][b]-depths[phase][a])/radius
            color=color_map[b];style='line'
            if abs(depth)>.45:
                if depth>0:
                    style='solid_wedge';draw.polygon([tuple(p),tuple(q+11*normal),tuple(q-11*normal)],fill=color)
                else:
                    style='hashed_wedge'
                    for t in np.linspace(.05,1,max(5,int(np.linalg.norm(q-p)/7))):
                        middle=p+(q-p)*t;half=1+10*t
                        draw.line((*tuple(middle-half*normal),*tuple(middle+half*normal)),fill=color,width=2)
            else:
                draw.line((*p,*q),fill=color,width=3)
            strokes.append({'phase':phase,'source':a,'target':b,'source_label':nodes[a]['label'],
                            'target_label':nodes[b]['label'],'style':style,'view_depth_cosine':float(depth),
                            'visible_endpoints':[p.tolist(),q.tolist()]})
        for key,n in nodes.items():
            x,y=positions[phase][key];r=radii[key]
            draw.ellipse((x-r,y-r,x+r,y+r),fill='white',outline=color_map[key],width=3)
            text(x,y,n['label'],24,phase=phase,node=key)
    # The schematic departure cue has no line connecting LG to the product carbon.
    p=np.array(projection_record['departure_start']);q=np.array(projection_record['departure_position'])
    axis=q-p;axis/=np.linalg.norm(axis);end=q-axis*25
    draw_linear(draw,{'type':'arrow','stroke':3,'color':color_map[roles['leaving']]},(*p,*end))
    draw.ellipse((q[0]-24,q[1]-24,q[0]+24,q[1]+24),fill='white',outline=color_map[roles['leaving']],width=3)
    label=next(n['label'] for n in spec['initial']['nodes'] if n['id']==roles['leaving'])
    text(*q,label,24,phase='departed',node=roles['leaving'])
    for key,xy in positions['product'].items():
        if np.linalg.norm(q-np.array(xy))<55:raise ValueError('departure cue overlaps product node')
    draw_linear(draw,{'type':'arrow','stroke':3,'color':INK},(453,267,551,267))
    text(502,239,'SN2',22)
    text(502,297,'Match labels',17)
    # Draw literal stroke examples rather than relying on words alone.
    draw.polygon([(87,398),(128,387),(128,409)],fill=INK)
    text(144,398,'Solid: toward you',20,anchor='lm')
    for t in np.linspace(.08,1,7):
        x=523+40*t;half=1+10*t
        draw.line((x,398-half,x,398+half),fill=INK,width=2)
    text(581,398,'Hashed: away',20,anchor='lm')
    retained_names=[initial_labels[k] for k in roles['retained']]
    text(512,430,'Same colors and labels track '+', '.join(retained_names)+'.',19)
    return {'labels':boxes,'layout_issues':issues,'positions':positions,'strokes':strokes,
            'projection':projection_record,'scope':'Static paired endpoint schematic with a separate LG motion cue; not a reaction trajectory.'}


def view_facts(spec,public_task):
    from PIL import Image
    check=compile_pair(spec,public_task)
    record=draw_pair(Image.new('RGB',(1024,576),'white'),spec)
    return record,check
