"""Report observed requirement failures separately from weighted quality scores.

This is a diagnostic layer, not a score cap or a claim of human acceptance.
It may also read old scores without changing their immutable run artifacts.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from .speech import narration_absent

VERSION = 'localbench-output-checks-dev2'


def output_checks(result, audio=(), packet=None, case=None):
    checks=[]
    def add(id_, status, reason, evidence_ids=()):
        checks.append({'id':id_, 'status':status, 'reason':reason,
                       'evidence_ids':list(evidence_ids)})

    audio_ids=[a['id'] for a in audio]
    if audio and all(narration_absent(a) for a in audio):
        add('spoken_narration_presence','fail',
            'Final-audio checks establish no speech throughout; required narration is absent.',audio_ids)
    elif any(a.get('transcript_valid') and (a.get('transcript') or '').strip() for a in audio):
        add('spoken_narration_presence','observed',
            'Speech was transcribed. This establishes presence only, not language accuracy or full-lesson coverage.',audio_ids)
    else:
        add('spoken_narration_presence','unverified',
            'No reliable positive speech evidence or verified whole-video silence is available.',audio_ids)

    if result.get('dimensions',{}).get('audio_quality',{}).get('score') is None:
        add('audio_quality_scoring','unverified','Actual-audio quality scoring is incomplete; a usable transcript does not establish audio quality.',audio_ids)

    duration=(packet or {}).get('metadata',{}).get('decoded_duration_s')
    target=(case or {}).get('target_duration_s')
    if all(type(x) in (int,float) and math.isfinite(x) and x>0 for x in (duration,target)):
        add('target_duration','observed' if abs(duration-target)<=1 else 'fail',
            f'Decoded duration {duration:.3f}s; target {target:.3f}s; tolerance 1s.')
    else:
        add('target_duration','unverified','Decoded duration and frozen task target are both required.')

    alignment=result.get('dimensions',{}).get('crossmodal_alignment',{})
    sync=alignment.get('criteria',{}).get('synchrony',{})
    mismatches=[r for r in alignment.get('observations',[]) if r.get('verdict')=='misaligned'
                and any(x.startswith('F') for x in r.get('evidence_ids',[]))
                and any(x.startswith('A') for x in r.get('evidence_ids',[]))]
    if audio and all(narration_absent(a) for a in audio):
        add('sampled_speech_visual_synchrony','fail','Required speech is absent, so no narrated synchronization is delivered.',audio_ids)
    elif sync.get('status')=='observed' and sync.get('score') in (1,2) and mismatches:
        add('sampled_speech_visual_synchrony','fail',
            'Judge reports major/severe synchrony problems with paired speech-frame evidence; requires adjudication.',
            dict.fromkeys(x for r in mismatches for x in r['evidence_ids']))
    elif mismatches:
        add('sampled_speech_visual_synchrony','review',
            'At least one time-paired probe reports a mismatch; inspect its severity.',
            dict.fromkeys(x for r in mismatches for x in r['evidence_ids']))
    elif sync.get('status')=='observed' and alignment.get('observations') and all(
            r.get('verdict')=='aligned' for r in alignment['observations']):
        add('sampled_speech_visual_synchrony','no_failure_detected',
            'No mismatch was reported in sampled probes; unsampled intervals remain unchecked.',sync.get('evidence_ids',[]))
    else:
        add('sampled_speech_visual_synchrony','unverified','No sufficiently grounded time-paired decision is available.')

    for check in result.get('critical_verification',{}).get('checks',[]):
        if check.get('verdict')=='fail':
            add('content:'+check['id'],'fail',check['reason'],check.get('evidence_ids',[]))
    layout=result.get('dimensions',{}).get('visual_quality',{}).get('layout_audit')
    if layout:
        if layout.get('status')!='reviewed':add('layout_review_coverage','unverified','Some sampled-frame layout reviews failed.')
        for row in layout.get('frames',[]):
            for i,issue in enumerate(row.get('issues',[])):
                add(f'layout:{row["frame_id"]}:{i}', 'fail' if issue.get('severity')=='major' else 'review',
                    issue['observation'],[row['frame_id']])
    relations=result.get('critical_verification',{}).get('screen_relation_review')
    if relations and relations.get('status')!='reviewed':
        add('screen_relation_review_coverage','unverified','Some sampled-frame relation reviews failed.')
    if result.get('reference_contract_hash'):
        # These are evidence-backed model findings, not automatic score deductions.
        # Keep unmet public outcomes visible beside a potentially high weighted mean.
        for finding in result.get('requirement_findings',[]):
            state={'met':'observed','missing':'fail','unverified':'unverified'}[finding['verdict']]
            add('public_requirement:'+finding['requirement_id'],state,finding['reason'],finding['evidence_ids'])
    timeline=result.get('timeline_review')
    if timeline is not None:
        if timeline.get('status')!='reviewed':
            add('timeline_review_coverage','unverified','Not every dense/change-boundary window was reviewed.')
        for check in timeline.get('checks',[]):
            add('timeline:'+check['id'], 'fail' if check['verdict']=='fail' and check.get('severity') in {'major','critical'}
                else 'review' if check['verdict']=='fail' else 'unverified',check['reason'],check.get('evidence_ids',[]))
    for name,dimension in result.get('dimensions',{}).items():
        if dimension.get('score_validity',{}).get('status')=='unverified':
            add('dimension_evidence:'+name,'unverified','; '.join(dimension['score_validity'].get('reasons',[])) or 'Dimension evidence incomplete.')
    if result.get('verification_conflicts'):
        add('score_verification_consistency','review','Unresolved disagreement between dimension scores and specific verification checks.')
    failed=[c['id'] for c in checks if c['status']=='fail']
    review=[c['id'] for c in checks if c['status']=='review']
    unknown=[c['id'] for c in checks if c['status']=='unverified']
    status=('observed_requirement_failure' if failed else 'review_required' if review else
            'incomplete_evidence' if unknown else 'no_failure_detected_in_checked_requirements')
    version='localbench-output-checks-dev3' if result.get('reference_contract_hash') else VERSION
    return {'version':version,'status':status,'failed':failed,'review':review,'unverified':unknown,
            'checks':checks,'changes_weighted_scores':False,
            'scope':'Development diagnostics; no human acceptance, full coverage or language certification.'}


def checks_from_score_file(path, *, refresh=False):
    path=Path(path)
    result=json.loads(path.read_text())
    if 'output_checks' in result and not refresh:return result['output_checks']
    audio_path=path.parent/'actual_audio.json'
    packet_path=path.parent/'evidence/packet.json'
    snapshot=path.parents[2]/'case_snapshot.jsonl'
    case=None
    if snapshot.exists():
        case=next((r for line in snapshot.read_text().splitlines() if line.strip()
                   for r in [json.loads(line)] if r['id']==result['case_id']),None)
    return output_checks(result,json.loads(audio_path.read_text()) if audio_path.exists() else [],
                         json.loads(packet_path.read_text()) if packet_path.exists() else None,case)
