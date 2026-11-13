import copy
import math

import numpy as np
import pytest

from localbench.spatial_inversion import construct, signed_volume, verify_pair


def initial():
    points={'c':[0,0,0],'lg':[2,0,0],'r1':[-2/3,2*math.sqrt(8)/3,0],
            'r2':[-2/3,-2*math.sqrt(2)/3,2*math.sqrt(6)/3],
            'r3':[-2/3,-2*math.sqrt(2)/3,-2*math.sqrt(6)/3]}
    return {'nodes':[{'id':k,'label':k,'xyz':v} for k,v in points.items()],
        'links':[{'source':'c','target':k,'kind':'bond'} for k in ['lg','r1','r2','r3']],
        'constraints':[],'camera':{'azimuth_deg':-45,'elevation_deg':30}}


def pair(g=None):
    return construct(g or initial(),'Tetrahedral substitution',center='c',leaving='lg',
                     incoming={'id':'nu','label':'Nu','color':'#28a745'},
                     retained=['r1','r2','r3'],emphasize='r3')


def test_reflection_preserves_ligands_and_reverses_signed_handedness_with_shared_readable_camera():
    g=initial();before=copy.deepcopy(g);a,b,r=pair(g)
    assert g==before
    assert r['check']['signed_volumes'][0]==pytest.approx(-r['check']['signed_volumes'][1])
    assert min(r['selected_view']['clearance_px'])>4
    assert r['selected_view']['emphasized_style'] in {'solid_wedge','hashed_wedge'}
    assert a['camera']==b['camera']
    assert [n for n in a['nodes'] if n['id'].startswith('r')]==[n for n in g['nodes'] if n['id'].startswith('r')]


@pytest.mark.parametrize('mutation',['same_handedness','swap_labels','move_center','camera','plain_dash'])
def test_checker_rejects_plausible_but_invalid_pairs(mutation):
    a,b,_=pair();nodes={n['id']:n for n in b['nodes']}
    if mutation=='same_handedness':
        for n in b['nodes']:n['xyz'][0]*=-1
    elif mutation=='swap_labels':nodes['r1']['xyz'],nodes['r2']['xyz']=nodes['r2']['xyz'],nodes['r1']['xyz']
    elif mutation=='move_center':nodes['c']['xyz'][1]+=.1
    elif mutation=='camera':b['camera']['azimuth_deg']+=15
    else:b['links'][0]['dash']=True
    with pytest.raises(ValueError):verify_pair(a,b,'c','lg','nu',['r1','r2','r3'])


def test_signed_volume_distinguishes_rotation_from_reflection():
    p=np.array([[1,0,0],[0,1,0],[0,0,1],[-1,-1,-1]],dtype=float)
    rotation=np.array([[0,-1,0],[1,0,0],[0,0,1]])
    assert signed_volume(p)==pytest.approx(-4)
    assert signed_volume(p@rotation.T+3)==pytest.approx(signed_volume(p))
    p[:,0]*=-1
    assert signed_volume(p)==pytest.approx(4)


def test_distinct_roles_required():
    with pytest.raises(ValueError,match='distinct role'):
        construct(initial(),'task',center='c',leaving='lg',incoming={'id':'lg','label':'Nu','color':'green'},
                  retained=['r1','r2','r3'],emphasize='r3')


def test_directionally_tetrahedral_but_unequal_radii_are_rejected():
    g=initial()
    for n in g['nodes']:
        if n['id']=='r3':n['xyz']=(np.asarray(n['xyz'])*1.25).tolist()
    with pytest.raises(ValueError,match='equal finite nonzero radii'):
        pair(g)
