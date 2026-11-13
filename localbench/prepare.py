"""Non-destructive normalized candidate export and missing-input checks."""
from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path

from .common import ROOT, digest, public_case, read_jsonl, write_json, write_jsonl


def normalize(row):
    result=dict(row)
    fixes=json.loads((ROOT/'configs/data_fixes.json').read_text(encoding='utf-8'))
    edits=[]
    if not row.get('pedagogical_target_audience') and row['id'] in fixes['audiences']:
        result['pedagogical_target_audience']=fixes['audiences'][row['id']]
        edits.append({'field':'pedagogical_target_audience','reason':'explicit editorial audience assignment','expert_verified':False})
    replacement=fixes['boilerplate_replacement']
    for key in ('prompt_text','expected_narrative_order','discipline_specific_rubric'):
        value=result.get(key)
        if isinstance(value,str) and replacement['from'] in value:
            result[key]=value.replace(replacement['from'],replacement['to']);edits.append({'field':key,'reason':'make quantities/units conditional on applicability'})
        elif isinstance(value,list):
            changed=[v.replace(replacement['from'],replacement['to']) if isinstance(v,str) else v for v in value]
            if changed!=value:result[key]=changed;edits.append({'field':key,'reason':'same applicability clarification'})
    specific=fixes['prompt_replacements'].get(row['id'])
    if specific and specific['from'] in result['prompt_text']:
        result['prompt_text']=result['prompt_text'].replace(specific['from'],specific['to'])
        edits.append({'field':'prompt_text','reason':'avoid implying spontaneous change of bacterial oxygen-response category'})
    raw_disc=row['discipline']
    result['discipline_canonical']='art_music' if raw_disc=='music' else raw_disc
    result['benchmark_scope']='candidate'
    raw_difficulty=row.get('difficulty')
    result['task_difficulty']=raw_difficulty if raw_difficulty in {'low','medium','high'} else None
    audience=result.get('pedagogical_target_audience')
    result['audience_specification']=audience or None
    issues=[]
    if not audience:issues.append('missing_target_audience')
    if result['task_difficulty'] is None:issues.append('difficulty_needs_independent_annotation')
    source=row.get('source',{})
    attachment=None
    if source.get('source_image_path'):
        source_path=Path(source['source_image_path'])
        candidates=[ROOT/'data/sources/grade/selected_assets'/source_path,
                    ROOT/'data/sources/grade/selected_assets/before'/source_path.name]
        path=next((p for p in candidates if p.is_file()),None)
        if path is None:issues.append('required_source_image_missing_locally')
        attachment={'role':'public_source_image','declared_source_path':source['source_image_path'],
                    'local_path':str(path.relative_to(ROOT)) if path else None,'available':path is not None}
    result['local_review']={'input_hash':digest(row),'issues':issues,
                            'applied_edits':edits,'editorial_version':fixes['version'],
                            'expert_content_verified':False,
                            'generation_ready':bool(audience) and (attachment is None or attachment['available']),
                            'status':'candidate_not_frozen'}
    generation=public_case(result)
    if attachment:generation['public_attachments']=[attachment]
    result['generation_input']=generation
    return result


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--data',type=Path,default=ROOT/'data/source_tasks.jsonl')
    p.add_argument('--out',type=Path,default=ROOT/'data/tasks.jsonl')
    args=p.parse_args()
    rows=read_jsonl(args.data);normalized=[normalize(r) for r in rows]
    write_jsonl(args.out,normalized)
    summary={'n':len(rows),'source_hash':digest(rows),'expert_approved':0,
             'structurally_generation_ready':sum(r['local_review']['generation_ready'] for r in normalized),
             'scope':dict(collections.Counter(r['benchmark_scope'] for r in normalized)),
             'issues':dict(collections.Counter(x for r in normalized for x in r['local_review']['issues']))}
    write_json(args.out.with_suffix('.summary.json'),summary)
    print(summary)


if __name__=='__main__':main()
