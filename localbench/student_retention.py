"""Prospective tolerant decoding with exact observation preservation, not new facts."""
from __future__ import annotations

from collections import defaultdict, deque

VERSION = 'student-diagnostics-dev6-retention'
MAX_UNDERSTANDINGS = 12
NOMINAL_UNDERSTANDINGS = 4

GUIDANCE = '''Keep every original claim and question verbatim, in its original order.
Do not summarize, merge, delete or add observations. Preserve the original nonempty
state_update verbatim. You may repair object fields and evidence references using
only the same supplied prefix. The decoder accepts up to 12 understandings; the
1-4 instruction is the preferred response length, not permission to discard later
observations. Do not add observations merely to reach a count. Reviewer responses
must still cover every supplied student observation exactly once.'''


def identity(raw):
    if not isinstance(raw, dict):
        raise ValueError('cannot preserve observations from a non-object response')
    result = {}
    for key, field, low, high in [('understandings','claim',1,MAX_UNDERSTANDINGS),
                                  ('questions','question',0,2)]:
        rows = raw.get(key)
        if not isinstance(rows,list) or not low <= len(rows) <= high:
            raise ValueError('cannot repair observation count without deletion or invention')
        if any(not isinstance(r,dict) or not isinstance(r.get(field),str) or not r[field].strip() for r in rows):
            raise ValueError('cannot preserve a missing observation text')
        result[key] = [r[field] for r in rows]
    if isinstance(raw.get('state_update'),str) and raw['state_update'].strip():
        result['state_update'] = raw['state_update']
    return result


def ensure_preserved(original, proposed):
    before, after = identity(original), identity(proposed)
    if any(after.get(key) != value for key,value in before.items()):
        raise ValueError('schema repair changed, dropped, reordered or invented student observations/state')


def audit(original, proposed, *, accepted, repaired):
    """An exact textual mapping; matching strings do not certify their truth."""
    report = {'version':VERSION,'accepted':accepted,'repair_attempted':repaired,
              'scope':'Exact text/count preservation audit, not correctness or learning evidence.',
              'sections':{}}
    for key,field in [('understandings','claim'),('questions','question')]:
        old = original.get(key) if isinstance(original,dict) else None
        new = proposed.get(key) if isinstance(proposed,dict) else None
        if not isinstance(old,list) or not isinstance(new,list):
            report['sections'][key]={'status':'unmappable'};continue
        available=defaultdict(deque)
        for j,row in enumerate(new):
            if isinstance(row,dict) and isinstance(row.get(field),str):available[row[field]].append(j)
        matches=[];dropped=[];used=set()
        for i,row in enumerate(old):
            text=row.get(field) if isinstance(row,dict) else None
            if not isinstance(text,str) or not available[text]:dropped.append(i);continue
            j=available[text].popleft();used.add(j)
            before=row.get('evidence_ids');after=new[j].get('evidence_ids')
            matches.append({'original_index':i,'result_index':j,'text_unchanged':True,
                            'original_evidence_ids':before,'result_evidence_ids':after,
                            'evidence_ids_unchanged':before==after})
        added=[j for j in range(len(new)) if j not in used]
        report['sections'][key]={'status':'mapped','original_count':len(old),'result_count':len(new),
            'mapping':matches,'dropped_original_indices':dropped,'added_or_changed_result_indices':added,
            'all_text_preserved':not dropped and not added,
            'order_preserved':not dropped and not added and all(m['original_index']==m['result_index'] for m in matches)}
    report['state_text_unchanged']=(original.get('state_update')==proposed.get('state_update')
        if isinstance(original,dict) and isinstance(proposed,dict) else None)
    n=report['sections']['understandings'].get('original_count')
    report['original_exceeded_preferred_count']=n>NOMINAL_UNDERSTANDINGS if n is not None else None
    return report
