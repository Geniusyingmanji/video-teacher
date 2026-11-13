"""Fixed-media diagnostic of localized source observations; original scores stay intact."""
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import io
import json
from pathlib import Path

import imageio_ffmpeg
from PIL import Image

from .client import MatrixClient
from .common import ROOT,digest,read_jsonl,write_json
from .provenance import file_hash,freeze_run
from .verification import verify
from .evidence import source_evidence


def verify_saved_frames(packet):
    """Legacy packets lack frame hashes; re-decode the bound video to verify them."""
    expected={f['frame_index']:f for f in packet['frames']};matched={}
    reader=imageio_ffmpeg.read_frames(packet['video_path'],pix_fmt='rgb24')
    metadata=next(reader)
    for index,raw in enumerate(reader):
        if index not in expected:continue
        frame=expected[index];buffer=io.BytesIO()
        Image.frombytes('RGB',metadata['size'],raw).save(buffer,format='JPEG',quality=88)
        sha=hashlib.sha256(buffer.getvalue()).hexdigest()
        if sha!=file_hash(frame['path']):raise ValueError('saved evidence frame does not match actual encoded video')
        matched[frame['id']]=sha
    if len(matched)!=len(expected):raise ValueError('missing decoded evidence frames')
    return matched


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--evaluation',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--workers',type=int,default=3);p.add_argument('--max-calls',type=int,default=15)
    p.add_argument('--final-focused',action='store_true',help='Experimental final-frame and automatically located color-ink crop')
    p.add_argument('--modes',nargs='+',help='Retry explicitly named media without replacing the original cohort')
    p.add_argument('--max-output-tokens',type=int,default=1700)
    args=p.parse_args()
    if args.out.exists():p.error('use a fresh diagnostic directory')
    if not 1<=args.workers<=4:p.error('use 1-4 workers')
    cases={r['id']:r for r in read_jsonl(args.evaluation/'case_snapshot.jsonl')}
    paths=sorted(args.evaluation.glob('*/*/scores.json'))
    if args.modes:
        if set(args.modes)-{p.parent.name for p in paths}:p.error('unknown media mode')
        paths=[p for p in paths if p.parent.name in args.modes]
    if not paths:p.error('no source scores')
    freeze_run(args.out,{'entrypoint':'region_review','adapter':'source_region_shading_final_focus_dev3' if args.final_focused else 'source_region_shading_localized_dev2',
        'source_scores':{str(p.resolve()):file_hash(p) for p in paths},'new_scores':False,
        'workers':args.workers,'max_calls':args.max_calls,'max_output_tokens':args.max_output_tokens})
    client=MatrixClient(args.out,model='qwen3.8-flash',concurrency=args.workers,
                        max_calls=args.max_calls,max_tokens_total=240000,cache_sources=[args.evaluation])
    def work(path):
        score=json.loads(path.read_text());case=cases[score['case_id']]
        packet=json.loads((path.parent/'evidence/packet.json').read_text())
        out=args.out/score['case_id']/path.parent.name
        try:
            if score['case_hash']!=digest(case) or score['video_sha256']!=file_hash(packet['video_path']):
                raise ValueError('source score input or media changed')
            source=source_evidence(case)[0]
            if source!=score.get('public_source'):raise ValueError('public source evidence changed')
            frame_hashes=verify_saved_frames(packet)
            write_json(out/'redecoded_frame_hashes.json',frame_hashes)
            result=verify(client,case,packet,out,localized_source_observations=not args.final_focused,
                          final_focused_source=args.final_focused,max_output_tokens=args.max_output_tokens)
            record={'id':score['case_id'],'mode':path.parent.name,'video_sha256':score['video_sha256'],
                    'source_score_sha256':file_hash(path),'original_checks':score['critical_verification']['checks'],
                    'localized_review':result,'status':'reviewed','new_scores':False}
        except Exception as exc:
            record={'id':score['case_id'],'mode':path.parent.name,'status':'review_error','error':str(exc)[:300]}
        write_json(out/'review.json',record)
        print(record['mode'],record['status'],flush=True)
        return record
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        result=list(pool.map(work,paths))
    write_json(args.out/'summary.json',result)


if __name__=='__main__':main()
