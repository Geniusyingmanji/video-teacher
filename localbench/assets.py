"""Fetch bounded batches of public source images, never target/answer images."""
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import io
from pathlib import Path, PurePosixPath
from urllib.parse import quote

import httpx
from PIL import Image

from .common import ROOT, read_jsonl, write_json


def asset_path(source):
    relative=PurePosixPath(source['source_image_path'])
    if relative.is_absolute() or '..' in relative.parts or not relative.parts[:2]==('image','before'):
        raise ValueError('only declared relative GRADE input images are allowed')
    return ROOT/'data/sources/grade/selected_assets'/relative


def fetch(row):
    source=row['source'];path=asset_path(source)
    url='https://huggingface.co/datasets/VisionXLab/GRADE/resolve/main/'+quote(source['source_image_path'],safe='/')
    try:
        cached=path.exists()
        if cached:content=path.read_bytes()
        else:
            with httpx.Client(timeout=40,follow_redirects=True) as client:
                with client.stream('GET',url) as response:
                    response.raise_for_status()
                    content=bytearray()
                    for chunk in response.iter_bytes():
                        content.extend(chunk)
                        if len(content)>20_000_000:raise ValueError('image exceeds 20 MB budget')
            content=bytes(content)
        im=Image.open(io.BytesIO(content));im.verify()
        if not cached:
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(content)
        result={'id':row['id'],'status':'cached' if cached else 'downloaded','source_url':url,
                'path':str(path.relative_to(ROOT)),'bytes':len(content),
                'sha256':hashlib.sha256(content).hexdigest(),'role':'public_source_not_answer',
                'license_status':source.get('license_status','unverified')}
    except Exception as exc:
        result={'id':row['id'],'status':'error','source_url':url,'error':str(exc)[:300]}
    print(row['id'],result['status'],flush=True)
    return result


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--limit',type=int,default=16)
    p.add_argument('--workers',type=int,default=4)
    p.add_argument('--out',type=Path,required=True)
    args=p.parse_args()
    rows=[r for r in read_jsonl(ROOT/'data/source_tasks.jsonl')
          if r.get('source',{}).get('dataset')=='GRADE' and r['source'].get('source_image_path')]
    selected=[]
    for d in sorted({r['discipline'] for r in rows}):
        selected.append(next(r for r in rows if r['discipline']==d))
    for row in rows:
        if len(selected)>=args.limit:break
        if row not in selected:selected.append(row)
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        results=list(pool.map(fetch,selected[:args.limit]))
    write_json(args.out,{'n':len(results),'results':results,'target_images_downloaded':0})


if __name__=='__main__':main()
