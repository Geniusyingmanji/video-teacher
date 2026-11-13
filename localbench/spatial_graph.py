"""Bounded 3D graph prototype. Geometry checks do not certify subject semantics."""
from __future__ import annotations

import copy
import math
import re

import numpy as np
from PIL import Image, ImageColor, ImageDraw

VERSION='spatial-graph-geometry-v2-readable-labels'


def unit(vector):
    v=np.asarray(vector,dtype=float);n=float(np.linalg.norm(v))
    if n<1e-7:raise ValueError('nonzero relation vector required')
    return v/n


def compile_graph(raw, public_task):
    if not isinstance(raw,dict) or set(raw)!={'nodes','links','constraints','camera'}:
        raise ValueError('graph requires nodes, links, constraints and camera')
    if not isinstance(raw['nodes'],list) or not 2<=len(raw['nodes'])<=12:
        raise ValueError('2..12 nodes required')
    nodes={}
    for n in raw['nodes']:
        if not isinstance(n,dict) or set(n)-{'id','label','xyz','color'} or not {'id','label','xyz'}<=set(n):
            raise ValueError('node requires id, label and xyz; optional color')
        id_=n['id']
        if not isinstance(id_,str) or not re.fullmatch('[A-Za-z][A-Za-z0-9_]{0,23}',id_) or id_ in nodes:
            raise ValueError('distinct bounded node IDs required')
        if not isinstance(n['label'],str) or not 1<=len(n['label'])<=12 or '\n' in n['label']:
            raise ValueError('node labels require1..12characters, no newline')
        if not isinstance(n['xyz'],list) or len(n['xyz'])!=3 or any(type(v) not in (int,float) or not math.isfinite(v) or abs(v)>4 for v in n['xyz']):
            raise ValueError('xyz must contain three finite coordinates within -4..4')
        ImageColor.getrgb(n.get('color','#14283e'));nodes[id_]=n
    if not isinstance(raw['links'],list) or not 1<=len(raw['links'])<=24:
        raise ValueError('1..24 links required')
    for link in raw['links']:
        if not isinstance(link,dict) or set(link)-{'source','target','kind','dash','color'} or not {'source','target','kind'}<=set(link):
            raise ValueError('link requires source, target, kind; optional dash/color')
        if any(link[k] not in nodes for k in ('source','target')) or link['source']==link['target']:
            raise ValueError('link endpoints must reference distinct existing nodes')
        if link['kind'] not in {'bond','arrow'} or type(link.get('dash',False)) is not bool:
            raise ValueError('link kind bond/arrow and boolean dash required')
        unit(np.asarray(nodes[link['target']]['xyz'])-np.asarray(nodes[link['source']]['xyz']))
        ImageColor.getrgb(link.get('color','#14283e'))
    camera=raw['camera']
    if not isinstance(camera,dict) or set(camera)!={'azimuth_deg','elevation_deg'}:
        raise ValueError('camera requires azimuth_deg and elevation_deg')
    for k,bound in [('azimuth_deg',180),('elevation_deg',80)]:
        if type(camera[k]) not in (int,float) or not math.isfinite(camera[k]) or abs(camera[k])>bound:
            raise ValueError('invalid bounded camera angle')
    if not isinstance(raw['constraints'],list) or len(raw['constraints'])>12:
        raise ValueError('at most12 constraints required')
    checks=[]
    for row in raw['constraints']:
        if not isinstance(row,dict) or set(row)!={'kind','nodes','prompt_quote'}:
            raise ValueError('constraint requires kind, nodes and prompt_quote')
        kind=row['kind'];ids=row['nodes'];arity={'tetrahedral':5,'opposite_sides':3,'perpendicular':3,'directed_link':2}
        if kind not in arity or not isinstance(ids,list) or len(ids)!=arity[kind] or any(i not in nodes for i in ids) or len(set(ids))!=len(ids):
            raise ValueError('constraint needs the correct number of distinct existing nodes')
        if not isinstance(row['prompt_quote'],str) or not row['prompt_quote'].strip() or row['prompt_quote'] not in public_task:
            raise ValueError('exact nonempty public-task quote required')
        values=[]
        if kind=='directed_link':
            passed=any(e['kind']=='arrow' and [e['source'],e['target']]==ids for e in raw['links'])
        else:
            center=np.asarray(nodes[ids[0]]['xyz']);vectors=[unit(np.asarray(nodes[i]['xyz'])-center) for i in ids[1:]]
            if kind=='tetrahedral':
                values=[float(a@b) for j,a in enumerate(vectors) for b in vectors[j+1:]]
                passed=all(abs(v+1/3)<.02 for v in values)
            else:
                values=[float(vectors[0]@vectors[1])]
                passed=values[0]<-.999 if kind=='opposite_sides' else abs(values[0])<.02
        checks.append({**copy.deepcopy(row),'cosines':values,'satisfied':passed})
    failed=[c for c in checks if not c['satisfied']]
    if failed:raise ValueError('unsatisfied spatial geometry: '+','.join(c['kind'] for c in failed))
    return {'version':VERSION,'graph':copy.deepcopy(raw),'checks':checks,
            'semantic_binding_status':'model_proposed_unverified',
            'scope':'Coordinates, topology and declared geometry only. No valence, chemical reaction, knowledge truth or learner outcome certification.'}


def projection(graph, camera=None):
    camera=camera or graph['camera'];az=math.radians(camera['azimuth_deg']);el=math.radians(camera['elevation_deg'])
    right=np.array([math.cos(az),0,-math.sin(az)])
    up=np.array([-math.sin(az)*math.sin(el),math.cos(el),-math.cos(az)*math.sin(el)])
    toward=np.cross(right,up)
    points={n['id']:np.array([np.dot(n['xyz'],right),-np.dot(n['xyz'],up),np.dot(n['xyz'],toward)]) for n in graph['nodes']}
    xy=np.array([p[:2] for p in points.values()]);lo,hi=xy.min(0),xy.max(0)
    span=np.maximum(hi-lo,.3);scale=min(760/span[0],220/span[1]);center=(lo+hi)/2
    projected={k:((p[:2]-center)*scale+np.array([512,265])).tolist()+[float(p[2])] for k,p in points.items()}
    return projected,{'right':right.tolist(),'up':up.tolist(),'toward':toward.tolist(),'scale':float(scale)}


def draw_graph(image,graph,*,camera=None):
    from localbench.scene import font
    from localbench.stroke_style import draw_linear
    draw=ImageDraw.Draw(image);positions,basis=projection(graph,camera)
    face=font(22);nodes={n['id']:n for n in graph['nodes']};radii={}
    for id_,n in nodes.items():
        bbox=draw.textbbox((0,0),n['label'],font=face);radii[id_]=max(18,(bbox[2]-bbox[0])/2+8)
    ids=list(nodes)
    for index,id_ in enumerate(ids):
        x,y,_=positions[id_];r=radii[id_]
        if x-r<64 or x+r>960 or y-r<112 or y+r>414:
            raise ValueError('projected label circle exceeds diagram panel')
        for other in ids[index+1:]:
            distance=float(np.linalg.norm(np.array(positions[id_][:2])-np.array(positions[other][:2])))
            if distance<=r+radii[other]+4:
                raise ValueError('projected nodes overlap; change view or layout')
    # Draw links first, shorten them at the visible node labels. Graph coordinates
    # are the checked quantities; label circles do not change their semantics.
    strokes=[]
    for e in sorted(graph['links'],key=lambda e:(positions[e['source']][2]+positions[e['target']][2])/2):
        a,b=e['source'],e['target'];p=np.array(positions[a][:2]);q=np.array(positions[b][:2]);delta=q-p
        length=float(np.linalg.norm(delta))
        if length<=radii[a]+radii[b]+4:raise ValueError('projected nodes overlap; change view or layout')
        direction=delta/length;p=p+direction*radii[a];q=q-direction*radii[b]
        primitive={'type':'arrow' if e['kind']=='arrow' else 'line','stroke':3,'dash':e.get('dash',False),
                   'color':e.get('color','#14283e')}
        world_length=float(np.linalg.norm(np.array(nodes[b]['xyz'])-np.array(nodes[a]['xyz'])))
        depth_cosine=(positions[b][2]-positions[a][2])/world_length
        style='line'
        if e['kind']=='bond' and not e.get('dash') and abs(depth_cosine)>.45:
            normal=np.array([-direction[1],direction[0]])
            if depth_cosine>0:
                style='solid_wedge'
                draw.polygon([tuple(p),tuple(q+7*normal),tuple(q-7*normal)],fill=primitive['color'])
            else:
                style='hashed_wedge'
                # Narrow end at source, broad end at target, away from viewer.
                steps=max(4,int(np.linalg.norm(q-p)/7))
                for t in np.linspace(.06,1,steps):
                    center=p+(q-p)*t;half=1+6*t
                    draw.line((*tuple(center-half*normal),*tuple(center+half*normal)),fill=primitive['color'],width=2)
        else:
            draw_linear(draw,primitive,(*p,*q))
            if e.get('dash'):style='dashed'
            elif e['kind']=='arrow':style='arrow'
        strokes.append({'source':a,'target':b,'style':style,'view_depth_cosine':depth_cosine})
    boxes=[]
    layout_issues=[]
    for id_ in sorted(nodes,key=lambda i:positions[i][2]):
        n=nodes[id_];x,y,_=positions[id_];r=radii[id_];color=n.get('color','#14283e')
        draw.ellipse((x-r,y-r,x+r,y+r),fill='#ffffff',outline=color,width=2)
        # Object outlines retain model colors; text uses a fixed high-contrast
        # ink. Check the real background before drawing, just like plain text.
        label_color='#14283e'
        record={'node':id_,'text':n['label'],'bbox':list(draw.textbbox((x,y),n['label'],font=face,anchor='mm')),
                'label_color':label_color,'object_color':color}
        mask=Image.new('L',image.size,0)
        ImageDraw.Draw(mask).text((x,y),n['label'],font=face,fill=255,anchor='mm')
        from .layout_geometry import text_contrast
        layout_issues.extend(text_contrast(image,mask,label_color,record))
        draw.text((x,y),n['label'],font=face,fill=label_color,anchor='mm')
        boxes.append(record)
    # Explicit axes make the displayed orientation inspectable rather than
    # implying screen-left/right are intrinsic molecular directions.
    draw.text((75,350),'3D view',font=font(18),fill='#14283e')
    origin=np.array([112,403]);axis_colors=['#a32d2d','#237943','#285aa0']
    for j,label in enumerate('XYZ'):
        tip=origin+30*np.array([basis['right'][j],-basis['up'][j]])
        draw.line((*origin,*tip),fill=axis_colors[j],width=2)
        draw.text(tuple(tip+np.array([3,-4])),label,font=font(16),fill=axis_colors[j])
    if any(r['style'].endswith('wedge') for r in strokes):
        legend='Solid wedge: toward you. Hashed wedge: away.'
        draw.text((220,416),legend,font=font(16),fill='#14283e')
        boxes.append({'text':legend,'bbox':list(draw.textbbox((220,416),legend,font=font(16)))})
    return {'positions':positions,'labels':boxes,'basis':basis,'strokes':strokes,
            'layout_issues':layout_issues,'text_color_policy':'fixed dark ink; object outline retains authored color'}
