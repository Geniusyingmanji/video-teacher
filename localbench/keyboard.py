"""Compile a piano C-major diagram from pitches and adjacent-key intervals."""
from __future__ import annotations

import copy
import re

from .common import public_case

VERSION = 'piano-intervals-v1'
NATURALS = (60, 62, 64, 65, 67, 69, 71, 72)
NAMES = ('C', 'D', 'E', 'F', 'G', 'A', 'B', 'C′')


def geometry():
    left, width = 140, 92
    white = [{'pitch': p, 'name': name, 'x': left+i*width, 'width': width}
             for i, (p, name) in enumerate(zip(NATURALS, NAMES))]
    black = [{'pitch': a['pitch']+1, 'x': b['x']-27, 'width': 54}
             for a,b in zip(white,white[1:]) if b['pitch']-a['pitch']==2]
    semitones = [(i,i+1) for i,(a,b) in enumerate(zip(NATURALS,NATURALS[1:])) if b-a==1]
    return white, black, semitones


def diagram(marked):
    white,black,semitones=geometry()
    if any(pair not in semitones for pair in marked) or len(set(marked))!=len(marked):
        raise ValueError('only actual adjacent natural-key semitones can be marked')
    parts=[]
    def xy(x,y):return {'x':(x-64)/896,'y':(y-112)/302}
    def line(x,y,x2,y2):
        return {'type':'line',**xy(x,y),'x2':(x2-64)/896,'y2':(y2-112)/302,'color':'#9e4715','stroke':3}
    for key in white:
        parts.append({'type':'rect',**xy(key['x'],190),'w':key['width']/896,'h':200/302,
                      'fill':'#d9edf7','color':'#294052'})
    for key in black:
        parts.append({'type':'rect',**xy(key['x'],190),'w':key['width']/896,'h':118/302,
                      'fill':'#20303e','color':'#20303e'})
    for key in white:
        parts.append({'type':'text',**xy(key['x']+key['width']/2,362),'text':key['name'],
                      'font_size':27,'align':'center','color':'#183550'})
    for a,b in marked:
        x1,x2=[white[i]['x']+white[i]['width']/2 for i in (a,b)]
        parts.extend([line(x1,163,x2,163),line(x1,163,x1,175),line(x2,163,x2,175)])
        parts.append({'type':'text',**xy((x1+x2)/2,134),
                      'text':NAMES[a]+'–'+NAMES[b]+': semitone','font_size':22,'align':'center','color':'#9e4715'})
    return parts


def bind(plan,case):
    source=public_case(case).get('prompt_text','')
    text=source.lower().replace('–','-').replace('—','-')
    unsupported={'status':'unsupported','version':VERSION}
    result=copy.deepcopy(plan);scenes=result.get('scenes',[])
    if not ('piano' in text and 'octave' in text and 'upper c' in text and 'semitone' in text and
            re.search(r'c\s*,\s*d\s*,\s*e\s*,\s*f\s*,\s*g\s*,\s*a\s*,\s*b',text) and
            re.search(r'e\s*-\s*f',text) and re.search(r'b\s*-\s*c',text) and len(scenes)==5):
        return result,unsupported
    if any(s.get('state_visual') or s.get('source_visual') for s in scenes):
        return result,unsupported
    words=[s['narration'].lower().replace('–','-') for s in scenes]
    if not ('c major' in words[0] and ('whole' in words[1]) and
            ('between e and f' in words[2] or 'e-f' in words[2]) and
            ('between b and' in words[3] or 'b-c' in words[3]) and 'complete' in words[4]):
        return result,unsupported
    stages=[[],[],[(2,3)],[(2,3),(6,7)],[(2,3),(6,7)]]
    for scene,marked in zip(scenes,stages):scene['primitives']=diagram(marked)
    _,black,semitones=geometry()
    return result,{'status':'compiled','version':VERSION,'scene_indices':list(range(5)),
                   'natural_pitches':list(NATURALS),'black_pitches':[k['pitch'] for k in black],
                   'semitone_pairs':[list(pair) for pair in semitones],'marked_by_scene':stages,
                   'scope':'Explicit C-major octave task and five compatible narrated phases; diagram only, no added sound or speech.'}
