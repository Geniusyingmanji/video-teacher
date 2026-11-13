"""Address public task text by stable local span IDs instead of retyping quotes."""
import re

from .common import digest,public_case


def inventory(case):
    public=public_case(case);text=public['prompt_text'];start=0;spans=[]
    boundaries=[m.span() for m in re.finditer(r'(?<=[.!?])\s+|\n+',text)]+[(len(text),len(text))]
    for end,next_start in boundaries:
        segment=text[start:end];left=len(segment)-len(segment.lstrip());right=len(segment.rstrip())
        if right>left:
            a,b=start+left,start+right
            spans.append({'id':f'P{len(spans)}','start_char':a,'end_char':b,'text':text[a:b]})
        start=next_start
    return {'public_task_hash':digest(public),'spans':spans,'offset_unit':'Unicode characters in prompt_text'}


def resolve(case,span_id):
    if not isinstance(span_id,str):raise ValueError('public requirement ID must be a string')
    matches=[r for r in inventory(case)['spans'] if r['id']==span_id]
    if len(matches)!=1:raise ValueError('unknown public requirement ID')
    return matches[0]['text']
