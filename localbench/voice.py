"""Identity-preserving diagrams for explicit simple active/passive sentence pairs.

Bounded compiler: one regular past-tense transitive clause, explicit by-agent.
It does not certify general grammar or infer missing participants.
"""
from __future__ import annotations

import copy
import math
import re
from PIL import ImageDraw
from .common import digest, public_case

VERSION='voice-correspondence-v1'
COLORS={'agent':'#1868ae','patient':'#aa4b18','verb':'#39704b'}


def compile_voice(spec):
    if not isinstance(spec,dict) or set(spec)!={'type','active_sentence','passive_sentence'} or spec['type']!='voice_mapping':
        raise ValueError('voice mapping accepts two sentences only; endpoints and role labels are computed')
    active,passive=spec['active_sentence'],spec['passive_sentence']
    if any(not isinstance(s,str) or not 5<=len(s)<=110 or '\n' in s for s in (active,passive)):
        raise ValueError('voice sentence must be a short single clause')
    a,p=active.strip().rstrip('.'),passive.strip().rstrip('.')
    m=re.fullmatch(r'(.+?)\s+(was|were)\s+([A-Za-z]+ed)\s+by\s+(.+)',p,re.I)
    if not m:raise ValueError('simple regular-past passive with explicit by-agent required')
    patient,aux,verb,agent=m.groups()
    original=re.fullmatch('('+re.escape(agent)+r')\s+('+re.escape(verb)+r')\s+('+re.escape(patient)+')',a,re.I)
    if not original or agent.casefold()==patient.casefold():
        raise ValueError('active/passive participants or action do not match')
    active_agent,active_verb,active_patient=original.groups()
    nodes=[
        {'id':'active.agent','entity':'agent','stage':'active','role':'subject','text':active_agent,'role_text':'subject / actor','box':[116,140,364,184]},
        {'id':'active.patient','entity':'patient','stage':'active','role':'object','text':active_patient,'role_text':'object / receiver','box':[660,140,908,184]},
        {'id':'passive.patient','entity':'patient','stage':'passive','role':'subject','text':patient,'role_text':'subject / receiver','box':[116,332,364,376]},
        {'id':'passive.agent','entity':'agent','stage':'passive','role':'by_agent','text':'by '+agent,'role_text':'by-phrase / actor','box':[660,332,908,376]},
    ]
    links=[]
    for entity in ('agent','patient'):
        source=next(n for n in nodes if n['entity']==entity and n['stage']=='active')
        target=next(n for n in nodes if n['entity']==entity and n['stage']=='passive')
        links.append({'source':source['id'],'target':target['id'],'entity':entity,
                      'points':[((source['box'][0]+source['box'][2])/2,222),
                                ((target['box'][0]+target['box'][2])/2,326)]})
    return {'version':VERSION,'active_sentence':active,'passive_sentence':passive,'nodes':nodes,'links':links,
            'active_verb':active_verb,'passive_verb':aux+' '+verb,
            'invariants':['same participant identity across stages','same supplied regular-past action',
                          'active object maps to passive subject','active subject maps to explicit by-agent'],
            'scope':'Schematic mapping of the supplied simple sentence pair, not general grammar certification.'}


def from_public_case(case):
    prompt=public_case(case).get('prompt_text','')
    active=re.search(r"['\"]([^'\"\n]+)['\"]\s*\(active\)",prompt,re.I)
    passive=re.search(r"['\"]([^'\"\n]+)['\"]\s*\(passive\)",prompt,re.I)
    if not active or not passive:return None
    spec={'type':'voice_mapping','active_sentence':active[1],'passive_sentence':passive[1]}
    try:compile_voice(spec)
    except ValueError:return None
    return spec


def bind(plan, case):
    """Replace explicitly named conversion scenes; preserve narration and duration."""
    spec=from_public_case(case)
    if spec is None:return plan, {'status':'unsupported_public_sentence_pair'}
    selected=[i for i,s in enumerate(plan['scenes']) if
              re.search(r'\b(swap|transformation|transform|convert|conversion)\b',s['title'],re.I)
              and not s.get('source_visual') and not s.get('state_visual')]
    if not selected:return plan, {'status':'no_explicit_conversion_scene'}
    revised=copy.deepcopy(plan)
    for i in selected:
        s=revised['scenes'][i]
        s['title']='Active to Passive: Track the Same Participants'
        s['caption']='Word order and grammatical roles change; the actor and receiver stay the same.'
        s['primitives']=[copy.deepcopy(spec)]
    return revised, {'status':'compiled','version':VERSION,'scene_indices':selected,
                     'public_input_hash':digest(public_case(case)), 'compiled':compile_voice(spec),
                     'narration_changed':False,'scene_durations_changed':False}


def draw_voice(image,spec):
    from .scene import font
    c=compile_voice(spec);draw=ImageDraw.Draw(image);boxes=[]
    def text(x,y,value,color='#183550',size=24,max_width=None):
        if max_width:
            while size>20 and draw.textlength(value,font=font(size))>max_width:size-=1
            if draw.textlength(value,font=font(size))>max_width:raise ValueError('voice phrase too long for readable rendering')
        face=font(size);bounds=list(draw.textbbox((x,y),value,font=face,anchor='mm'))
        boxes.append({'text':value,'bbox':bounds})
        draw.text((x,y),value,font=face,anchor='mm',fill=color)
    text(104,112,'ACTIVE',size=19);text(104,305,'PASSIVE',size=19)
    for n in c['nodes']:
        b=n['box'];color=COLORS[n['entity']]
        draw.rounded_rectangle(tuple(b),radius=9,fill='#f5f8fc',outline=color,width=2)
        text((b[0]+b[2])/2,(b[1]+b[3])/2,n['text'],color,size=27,max_width=b[2]-b[0]-20)
        text((b[0]+b[2])/2,201 if n['stage']=='active' else 402,n['role_text'],color,size=21)
    for verb,y in [(c['active_verb'],162),(c['passive_verb'],354)]:text(512,y,verb,COLORS['verb'],size=28,max_width=264)
    for link in c['links']:
        a,b=link['points'];color=COLORS[link['entity']]
        draw.line((tuple(a),tuple(b)),fill=color,width=3)
        angle=math.atan2(b[1]-a[1],b[0]-a[0])
        draw.polygon([tuple(b),(b[0]-12*math.cos(angle-.4),b[1]-12*math.sin(angle-.4)),
                      (b[0]-12*math.cos(angle+.4),b[1]-12*math.sin(angle+.4))],fill=color)
    return boxes
