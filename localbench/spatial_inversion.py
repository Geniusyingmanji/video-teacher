"""Idealized tetrahedral substitution correspondence, not a reaction simulation.

Roles are explicitly supplied by the caller. Reflect a checked initial tetrahedron
across the plane through its center perpendicular to the leaving-group axis, and
replace the reflected leaving-group vertex by the incoming group. A shared camera
is chosen from a fixed grid for readable before/after diagrams. No CIP/R/S labels
or transition-state mechanics are inferred.
"""
import copy
import itertools

import numpy as np
from PIL import Image

from .common import digest
from .spatial_graph import compile_graph, draw_graph, unit
from .spatial_solver import _clearance

VERSION = 'tetrahedral-substitution-correspondence-dev2-equal-radii'


def signed_volume(points):
    p = np.asarray(points, dtype=float)
    if p.shape != (4,3) or not np.isfinite(p).all():
        raise ValueError('four finite3D ligand positions required')
    return float(np.linalg.det(p[1:]-p[0]))


def verify_pair(initial, product, center, leaving, incoming, retained):
    a = {n['id']:np.asarray(n['xyz'], dtype=float) for n in initial['nodes']}
    b = {n['id']:np.asarray(n['xyz'], dtype=float) for n in product['nodes']}
    if len(retained)!=3 or len({center,leaving,incoming,*retained})!=6:
        raise ValueError('distinct center, leaving, incoming and three retained roles required')
    if set(a)!={center,leaving,*retained} or set(b)!={center,incoming,*retained}:
        raise ValueError('exact initial/product role sets required')
    if not np.allclose(a[center],b[center],atol=1e-9):
        raise ValueError('center moved')
    axis = unit(a[leaving]-a[center])
    va = [a[k]-a[center] for k in [leaving,*retained]]
    vb = [b[k]-b[center] for k in [incoming,*retained]]
    for vectors in [va,vb]:
        radii = np.linalg.norm(vectors, axis=1)
        if not np.isfinite(radii).all() or radii.min()<1e-7 or not np.allclose(radii,radii[0],rtol=1e-7,atol=1e-9):
            raise ValueError('regular tetrahedron requires equal finite nonzero radii')
        if any(abs(float(np.dot(unit(x),unit(y)))+1/3)>1e-7 for x,y in itertools.combinations(vectors,2)):
            raise ValueError('both endpoint geometries must be regular tetrahedra')
    if not np.allclose(vb[0],-va[0],atol=1e-9):
        raise ValueError('incoming group must occupy opposite axis endpoint')
    for x,y in zip(va,vb):
        # Check independent normal and tangential components, not just a det flag.
        if not np.isclose(np.dot(y,axis),-np.dot(x,axis),atol=1e-9):
            raise ValueError('retained normal component failed to invert')
        if not np.allclose(y-np.dot(y,axis)*axis,x-np.dot(x,axis)*axis,atol=1e-9):
            raise ValueError('retained tangential correspondence changed')
    volumes = [signed_volume(v) for v in [va,vb]]
    if abs(volumes[0])<1e-6 or not np.isclose(volumes[1],-volumes[0],atol=1e-8):
        raise ValueError('ordered ligand handedness did not invert')
    for graph, neighbors in [(initial,[leaving,*retained]),(product,[incoming,*retained])]:
        edges={(e['source'],e['target']) for e in graph['links']}
        if len(graph['links'])!=4 or edges!={(center,k) for k in neighbors} or any(e['kind']!='bond' or e.get('dash') for e in graph['links']):
            raise ValueError('four explicit center-to-ligand depth bonds required')
    if initial['camera']!=product['camera']:
        raise ValueError('before/after must share a camera')
    return {'ordered_ligands':[[leaving,*retained],[incoming,*retained]],
            'signed_volumes':volumes,'axis':axis.tolist(),'reflection_verified':True,
            'scope':'Ordered correspondence in an idealized regular tetrahedron; no CIP assignment, reaction path, valence or physical kinetics certification.'}


def construct(initial, public_task, *, center, leaving, incoming, retained, emphasize):
    compile_graph(initial,public_task)
    source=copy.deepcopy(initial)
    nodes={n['id']:n for n in source['nodes']}
    if set(incoming)!={'id','label','color'}:
        raise ValueError('incoming role requires id,label,color')
    if set(nodes)!={center,leaving,*retained} or len(retained)!=3:
        raise ValueError('only one complete initial tetrahedron supported')
    if len({center,leaving,incoming['id'],*retained})!=6 or emphasize not in retained:
        raise ValueError('distinct role IDs and a retained emphasized ligand required')
    c=np.asarray(nodes[center]['xyz'],dtype=float)
    axis=unit(np.asarray(nodes[leaving]['xyz'])-c)
    reflection=np.eye(3)-2*np.outer(axis,axis)
    product=copy.deepcopy(source)
    for n in product['nodes']:
        n['xyz']=(c+reflection@(np.asarray(n['xyz'])-c)).tolist()
        if n['id']==leaving:
            n.update(incoming)
    for e in product['links']:
        if e['target']==leaving:
            e.update(target=incoming['id'],color=incoming['color'])
    # Do not reuse a source-task quote as if it requested this product phase.
    product['constraints']=[]
    verify_pair(source,product,center,leaving,incoming['id'],retained)
    views=[]
    for az in range(-75,76,15):
        for el in [-30,-15,0,15,30]:
            camera={'azimuth_deg':az,'elevation_deg':el}
            source['camera']=product['camera']=camera
            try:
                records=[draw_graph(Image.new('RGB',(1024,576),'white'),g) for g in [source,product]]
                margins=[_clearance(g) for g in [source,product]]
                style=next(e['style'] for e in records[1]['strokes'] if e['source']==center and e['target']==emphasize)
                if min(margins)<=4 or style not in {'solid_wedge','hashed_wedge'}:
                    raise ValueError('pair clearance or emphasized product depth cue inadequate')
                views.append({'camera':camera,'status':'valid','clearance_px':margins,'emphasized_style':style})
            except ValueError as exc:
                views.append({'camera':camera,'status':'rejected','reason':str(exc)})
    valid=[v for v in views if v['status']=='valid']
    if not valid:
        raise ValueError('no shared readable view within fixed search')
    chosen=max(valid,key=lambda v:min(v['clearance_px']))
    source['camera']=copy.deepcopy(chosen['camera'])
    product['camera']=copy.deepcopy(chosen['camera'])
    compile_graph(source,public_task);compile_graph(product,public_task)
    check=verify_pair(source,product,center,leaving,incoming['id'],retained)
    return source,product,{'version':VERSION,'source_hash':digest(initial),
        'initial_hash':digest(source),'product_hash':digest(product),'roles':{
            'center':center,'leaving':leaving,'incoming':incoming,'retained':retained,'emphasize':emphasize},
        'reflection_matrix':reflection.tolist(),'check':check,'selected_view':chosen,
        'view_search':views,'semantic_binding':'Caller-supplied chemistry roles; development schematic, not expert-verified.'}
