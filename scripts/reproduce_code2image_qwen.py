"""Local Qwen text-to-SVG pilot; a project baseline, not DiagramAgent weights."""
import argparse
import concurrent.futures
import hashlib
import json
from pathlib import Path
import re
import time


def run(task):
    case,port,out=task
    from openai import OpenAI
    import cairosvg
    directory=out/case['id'];directory.mkdir(parents=True,exist_ok=True)
    prompt=(case['text']+'\nReturn only a complete self-contained SVG document with a white background, '
            'viewBox="0 0 1200 800", readable English text and no external assets. '
            'Use mathematically correct coordinates and preserve every required structure. '
            'No JavaScript, embedded HTML, images or external links.')
    (directory/'prompt.json').write_text(json.dumps({'case':case,'actual_prompt':prompt},indent=2))
    t=time.time();row={'id':case['id'],'port':port,'method':'Qwen3.8-27B direct SVG project baseline',
                           'content_review':'pending'}
    try:
        result=OpenAI(base_url=f'http://127.0.0.1:{port}/v1',api_key='local',timeout=600,max_retries=1).chat.completions.create(
            model='qwen3.8-27b',messages=[{'role':'user','content':prompt}],temperature=.2,max_tokens=8192,
            extra_body={'chat_template_kwargs':{'enable_thinking':False}})
        (directory/'response.json').write_text(result.model_dump_json(indent=2))
        if result.choices[0].finish_reason=='length':raise ValueError('truncated response')
        text=result.choices[0].message.content
        match=re.search(r'<svg\b[\s\S]*?</svg>',text)
        if not match:raise ValueError('No complete SVG')
        svg=match.group()
        if re.search(r'<(?:script|image|foreignObject)\b|(?:href|url)\s*[:=(]',svg,re.I):
            # Local marker URL references are needed for arrowheads.
            stripped=re.sub(r'url\(#[\w-]+\)','',svg)
            if re.search(r'<(?:script|image|foreignObject)\b|(?:href|url)\s*[:=(]',stripped,re.I):
                raise ValueError('SVG contains unsupported active/external content')
        (directory/'figure.svg').write_text(svg)
        cairosvg.svg2png(bytestring=svg.encode(),write_to=str(directory/'figure.png'),output_width=1200,output_height=800)
        row.update(rendered=True,svg_sha256=hashlib.sha256(svg.encode()).hexdigest(),usage=result.usage.model_dump())
    except Exception as exc:row.update(rendered=False,error=repr(exc))
    row['seconds']=time.time()-t
    (directory/'result.json').write_text(json.dumps(row,indent=2))
    print(json.dumps(row),flush=True)
    return row


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True)
    p.add_argument('--ports',type=int,nargs='+',default=[8000,8001,8002,8003])
    p.add_argument('--prompts',type=Path,default=Path(__file__).resolve().parents[1]/'research/code2image_prompts.jsonl')
    args=p.parse_args();args.out.mkdir(parents=True,exist_ok=True)
    cases=[json.loads(s) for s in args.prompts.read_text().splitlines()]
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(args.ports)) as pool:
        rows=list(pool.map(run,[(c,args.ports[i%len(args.ports)],args.out) for i,c in enumerate(cases)]))
    (args.out/'report.json').write_text(json.dumps({'scope':'matched educational pilot, not paper benchmark replication',
        'temperature':.2,'max_tokens':8192,'prompt_sha256':hashlib.sha256(args.prompts.read_bytes()).hexdigest(),'cases':rows},indent=2))


if __name__=='__main__':main()
