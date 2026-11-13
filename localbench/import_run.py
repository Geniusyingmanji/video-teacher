"""Register externally generated full lessons in the shared evaluation contract."""
from __future__ import annotations

import argparse
import json
import math
import subprocess
from pathlib import Path

import imageio_ffmpeg

from .common import ROOT, digest, read_jsonl, write_json
from .provenance import file_hash, freeze_run


def inspect_external(row, case):
    video=Path(row['video_path']).expanduser().resolve()
    if not video.is_file():raise ValueError('video file not found')
    reader=imageio_ffmpeg.read_frames(str(video),pix_fmt='rgb24')
    metadata=next(reader)
    count=sum(1 for _ in reader)
    duration=count/metadata['fps']
    if not math.isfinite(duration) or abs(duration-case['target_duration_s'])>1:
        raise ValueError(f"duration {duration:.2f}s differs from target {case['target_duration_s']}s")
    command=[imageio_ffmpeg.get_ffmpeg_exe(),'-v','error','-i',str(video),
             '-map','0:a:0','-f','null','-']
    result=subprocess.run(command,capture_output=True,text=True,timeout=120)
    if result.returncode:raise ValueError('required audio stream missing or undecodable')
    return {'mode':row['mode'],'video_path':str(video),'sha256':file_hash(video),
            'duration_s':duration,'frame_count':count,'fps':metadata['fps'],'size':list(metadata['size']),
            'complete':True,'audio_stream':'decoded; speech language/content requires independent evaluation'}


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--input',type=Path,required=True,help='JSONL: case_id, mode, video_path')
    p.add_argument('--data',type=Path,default=ROOT/'data/tasks.jsonl')
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--label',required=True,help='Provenance label, not supplied to judges')
    args=p.parse_args()
    rows=read_jsonl(args.input)
    cases={r['id']:r for r in read_jsonl(args.data)}
    seen=set()
    for row in rows:
        id_,mode=row['case_id'],row['mode']
        if id_ not in cases:p.error(f'unknown case {id_}')
        if not isinstance(mode,str) or Path(mode).name!=mode or mode in {'','.','..'}:p.error('invalid mode name')
        if (id_,mode) in seen:p.error('duplicate case/mode in external input')
        seen.add((id_,mode))
    if args.out.exists():p.error('choose a fresh output directory')
    freeze_run(args.out,{'entrypoint':'import_run','label':args.label,'input_hash':digest(rows),
                         'dataset_hash':digest([cases[id_] for id_ in sorted({r['case_id'] for r in rows})])})
    records={}
    for row in rows:
        id_=row['case_id']
        record=records.setdefault(id_,{'id':id_,'status':'imported','artifacts':[],'errors':[]})
        try:record['artifacts'].append(inspect_external(row,cases[id_]))
        except Exception as exc:
            record['errors'].append({'mode':row['mode'],'error':str(exc)[:600]})
            record['status']='import_incomplete'
    manifest={'label':args.label,'cases':list(records.values()),'origin':'external_generation',
              'not_verified':'generation inputs, source-image use, narration semantics and correctness are not certified by media import'}
    write_json(args.out/'manifest.json',manifest)
    print(json.dumps({'imported_videos':sum(len(r['artifacts']) for r in records.values()),
                      'failed_videos':sum(len(r['errors']) for r in records.values())}))


if __name__=='__main__':main()
