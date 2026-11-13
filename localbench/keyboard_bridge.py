"""Narrated chromatic-key movement compiler; no inferred pitch from screen spacing."""
from __future__ import annotations

import copy
import math

from .keyboard import bind as base_bind, geometry

VERSION = 'piano-key-moves-v1'
COLOR = '#9a3c00'


def key_positions():
    white,black,_ = geometry()
    return {**{k['pitch']:(k['x']+k['width']/2,330) for k in white},
            **{k['pitch']:(k['x']+k['width']/2,259) for k in black}}


def compile_walk(spec, *, timed=True):
    pitches, cues = spec.get('pitches'), spec.get('cue_ids')
    positions=key_positions()
    if not isinstance(pitches,list) or not 2<=len(pitches)<=3 or any(type(p) is not int or p not in positions for p in pitches):
        raise ValueError('walk must traverse 2..3 keys in the rendered octave')
    differences=[b-a for a,b in zip(pitches,pitches[1:])]
    if len(set(differences))!=1 or abs(differences[0])!=1:
        raise ValueError('walk must visit every neighboring chromatic key in order')
    if not isinstance(cues,list) or len(cues)!=len(pitches)-1 or len(set(cues))!=len(cues) or any(not isinstance(x,str) or not x for x in cues):
        raise ValueError('one speech cue per key move required')
    intervals=spec.get('intervals')
    if timed:
        duration=spec.get('duration_s')
        if type(duration) not in (int,float) or not math.isfinite(duration) or duration<=0:
            raise ValueError('walk needs measured scene duration')
        if not isinstance(intervals,list) or len(intervals)!=len(cues):
            raise ValueError('walk needs measured movement intervals')
        previous=0
        for row in intervals:
            if not isinstance(row,list) or len(row)!=2 or any(type(x) not in (int,float) or not math.isfinite(x) for x in row):
                raise ValueError('invalid movement interval')
            a,b=row
            if not 0<=previous<=a<b<=duration:
                raise ValueError('movement intervals overlap or exceed scene')
            previous=b
    return [positions[p] for p in pitches]


def bind(plan,case, *, animated=True):
    result,receipt=base_bind(plan,case)
    if receipt['status']!='compiled':
        return copy.deepcopy(plan),{'status':'unsupported','version':VERSION}
    scripts={
        1:[('definition','A semitone is one move to the next key, counting either color.'),
           ('start','A whole step takes two moves. Start at C.'),
           ('move_1','Move to the black key.'),
           ('move_2','Then to D: two moves in total.')],
        2:[('start','Now start at E. F is the very next key.'),
           ('move_1','One move reaches F, with no black key between them.')],
        3:[('start','Start at B. The upper C is its next key.'),
           ('move_1','One move reaches the upper C: another semitone.')],
    }
    paths={1:[60,61,62],2:[64,65],3:[71,72]}
    captions={1:'Count neighboring keys of either color: two moves make a whole step.',
              2:'E to F: one neighboring-key move, with no intervening black key.',
              3:'B to upper C: one neighboring-key move, with no intervening black key.'}
    for index,script in scripts.items():
        scene=result['scenes'][index]
        scene['spoken_units']=[{'id':name,'text':text} for name,text in script]
        scene['narration']=' '.join(text for _,text in script)
        scene['caption']=captions[index]
        scene['slide_text']=captions[index]
        if animated:
            scene['primitives'].append({'type':'piano_walk','pitches':paths[index],
                'cue_ids':['move_'+str(i+1) for i in range(len(paths[index])-1)]})
    result.pop('timing_compilation',None)
    return result,{'status':'compiled','version':VERSION,'animated':animated,
        'changed_narration_scenes':[1,2,3],'requested_total_duration_s':sum(s['duration_s'] for s in plan['scenes']),
        'base_receipt':receipt,'paths':paths,
        'scope':'Explicit C-major task only. New speech and measured timing; arrows show moves, only E-F/B-C receive semitone brackets.'}


def bind_timing(scene):
    from .spoken_units import validate_timing
    records={r['id']:r for r in validate_timing(scene)}
    for spec in scene['primitives']:
        if spec['type']!='piano_walk':continue
        compile_walk(spec,timed=False)
        if any(cue not in records for cue in spec['cue_ids']):
            raise ValueError('walk references missing spoken unit')
        # Hold the source during the instruction onset; reach the target during
        # that same actual speech unit, then retain it through the remaining audio.
        spec['intervals']=[[records[k]['start_s']+.2*(records[k]['end_s']-records[k]['start_s']),
                            records[k]['start_s']+.7*(records[k]['end_s']-records[k]['start_s'])]
                           for k in spec['cue_ids']]
        spec['duration_s']=scene['duration_s']
        compile_walk(spec)


def snapshot(spec,progress):
    points=compile_walk(spec)
    if type(progress) not in (int,float) or not math.isfinite(progress) or not 0<=progress<=1:
        raise ValueError('walk progress must be 0..1')
    t=progress*spec['duration_s']
    position=points[0];count=0;segments=[]
    for i,(a,b) in enumerate(spec['intervals']):
        if t<a:break
        f=min(1,(t-a)/(b-a));f=f*f*(3-2*f)
        position=tuple(x+(y-x)*f for x,y in zip(points[i],points[i+1]))
        segments.append((points[i],position))
        if t>=b:count+=1
        else:break
    return {'position':position,'completed_moves':count,'total_moves':len(points)-1,'segments':segments}


def draw_walk(image,spec,progress):
    from PIL import ImageDraw
    from .scene import font
    state=snapshot(spec,progress);draw=ImageDraw.Draw(image)
    for start,end in state['segments']:
        draw.line([start,end],fill=COLOR,width=4)
        if math.dist(start,end)>12:
            angle=math.atan2(end[1]-start[1],end[0]-start[0])
            draw.polygon([end,(end[0]-10*math.cos(angle-.45),end[1]-10*math.sin(angle-.45)),
                          (end[0]-10*math.cos(angle+.45),end[1]-10*math.sin(angle+.45))],fill=COLOR)
    x,y=state['position'];draw.ellipse((x-9,y-9,x+9,y+9),fill='#ffe091',outline=COLOR,width=3)
    text=f'Moves made: {state["completed_moves"]} / {state["total_moves"]}'
    box=draw.textbbox((512,417),text,font=font(22),anchor='mm')
    draw.text((512,417),text,font=font(22),anchor='mm',fill=COLOR)
    return [{'text':text,'bbox':list(box)}]
