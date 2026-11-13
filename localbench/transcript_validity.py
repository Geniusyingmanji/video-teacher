"""Make unresolved transcript evidence visible without rewriting raw model ratings."""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path

from .common import write_json
from .provenance import file_hash,freeze_run

VERSION='transcript-evidence-validity-v1'


def apply_validity(result,audio):
    guarded=[a for a in audio if a.get('transcript_guard')]
    if not guarded:return copy.deepcopy(result)
    out=copy.deepcopy(result)
    spans=[{'audio_id':a['id'],**u} for a in guarded for u in a['transcript_guard'].get('unresolved_spans',[])]
    unavailable=[a['id'] for a in guarded if a['transcript_guard'].get('status')=='listener_evidence_unavailable']
    out['transcript_evidence_validity']={'version':VERSION,'unresolved_spans':spans,
        'unavailable_audio_ids':unavailable,'all_transcript_evidence_resolved':not(spans or unavailable),
        'scope':'Dimension ratings still describe observed evidence; model unanimity does not certify transcription or teaching correctness.'}
    if spans or unavailable:
        scoring=out['scoring']
        scoring.setdefault('observed_evidence_mean',scoring.get('overall'))
        scoring['overall']=None
        reasons=list(scoring.get('incomplete_reasons',[]))
        if 'unresolved_transcript_evidence' not in reasons:reasons.append('unresolved_transcript_evidence')
        scoring['incomplete_reasons']=reasons
        scoring['prior_status']=scoring.get('status')
        scoring['status']='unresolved_transcript_evidence'
        out['prior_evaluation_status']=out.get('evaluation_status')
        out['evaluation_status']='partial_transcript_evidence'
    return out


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--evaluation',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    args=p.parse_args()
    if args.out.exists():p.error('use a new derivation directory')
    sources=sorted(args.evaluation.glob('*/*/scores.json'))
    if not sources:p.error('no scored source records')
    freeze_run(args.out,{'entrypoint':'transcript_validity_derivation','version':VERSION,
        'source_scores':{str(p.resolve()):file_hash(p) for p in sources},'new_model_calls':0,
        'policy':'Retain all original dimension ratings; withhold the overall total for unresolved transcript evidence.'})
    results=[]
    for source in sources:
        raw=json.loads(source.read_text());audio=json.loads((source.parent/'actual_audio.json').read_text())
        score=apply_validity(raw,audio)
        score['rubric_version']=raw['rubric_version']+'+'+VERSION
        score['scoring']['version']=score['rubric_version']
        score['derivation']={'source_score_file':str(source.resolve()),'source_score_sha256':file_hash(source),
            'source_protocol':raw['rubric_version'],'new_model_ratings':False}
        target=args.out/source.parent.parent.name/source.parent.name
        write_json(target/'scores.json',score);write_json(target/'actual_audio.json',audio)
        guard=source.parent/'transcript_guard'
        if guard.exists():
            for name in ('summary.json','disputes.json'):
                write_json(target/'transcript_guard'/name,json.loads((guard/name).read_text()))
        # Keep the original frame/audio paths and hashes; do not synthesize new evidence.
        write_json(target/'evidence/packet.json',json.loads((source.parent/'evidence/packet.json').read_text()))
        results.append(score)
    write_json(args.out/'summary.json',results)
    print({'records':len(results),'overall_available':sum(r['scoring']['overall'] is not None for r in results),
        'new_model_calls':0})


if __name__=='__main__':main()
