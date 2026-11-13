"""Create explicit spoken-error controls while preserving all encoded video frames."""
from __future__ import annotations

import argparse
import json
import wave
from pathlib import Path

import imageio_ffmpeg
import numpy as np

from .common import write_json
from .controls import decoded_video_hash
from .pipeline import run_command
from .provenance import file_hash,freeze_run


def splice_samples(original,replacement,start,end):
    if type(start) is not int or type(end) is not int or not 0<=start<end<=len(original):
        raise ValueError('invalid audio replacement interval')
    if original.ndim!=1 or replacement.ndim!=1 or original.dtype!=replacement.dtype:
        raise ValueError('matching mono PCM arrays required')
    if len(replacement)>end-start:raise ValueError('replacement speech does not fit; never truncate spoken words')
    out=original.copy();out[start:end]=0;out[start:start+len(replacement)]=replacement
    return out


def build(item,out):
    source=Path(item['video']);plan_path=Path(item['plan'])
    plan=json.loads(plan_path.read_text());case_id=item['id']
    if plan['case_id']!=case_id:raise ValueError('control plan/case mismatch')
    scene=plan['scenes'][item['scene']]
    if scene['narration'].count(item['old'])!=item.get('count',1):raise ValueError('control edit occurrence count mismatch')
    text=scene['narration'].replace(item['old'],item['new'])
    if text==scene['narration']:raise ValueError('control made no spoken change')
    directory=out/case_id;directory.mkdir()
    ffmpeg=imageio_ffmpeg.get_ffmpeg_exe()
    raw=directory/'source.wav'
    run_command([ffmpeg,'-v','error','-i',str(source),'-vn','-ar','24000','-ac','1','-c:a','pcm_s16le',str(raw)])
    with wave.open(str(raw)) as w:
        original=np.frombuffer(w.readframes(w.getnframes()),dtype='<i2')
    duration=sum(s['duration_s'] for s in plan['scenes']);target=round(duration*24000)
    if len(original)<target:raise ValueError('source audio shorter than declared schedule')
    original=original[:target]
    start=round(sum(s['duration_s'] for s in plan['scenes'][:item['scene']])*24000)
    end=start+round(scene['duration_s']*24000)
    script=directory/'control_narration.txt';script.write_text(text)
    aiff=directory/'speech.aiff';speech=directory/'speech.wav'
    rate=plan.get('timing_compilation',{}).get('common_speech_rate',155)
    run_command(['say','-v','Samantha','-r',str(rate),'-f',str(script),'-o',str(aiff)])
    run_command([ffmpeg,'-v','error','-i',str(aiff),'-ar','24000','-ac','1','-c:a','pcm_s16le',str(speech)])
    with wave.open(str(speech)) as w:
        replacement=np.frombuffer(w.readframes(w.getnframes()),dtype='<i2')
    changed=splice_samples(original,replacement,start,end)
    audio=directory/'spoken_error.wav'
    with wave.open(str(audio),'wb') as w:
        w.setnchannels(1);w.setsampwidth(2);w.setframerate(24000);w.writeframes(changed.tobytes())
    output=directory/'spoken_error.mp4'
    run_command([ffmpeg,'-v','error','-i',str(source),'-i',str(audio),'-map','0:v:0','-map','1:a:0',
        '-c:v','copy','-c:a','aac','-b:a','96k','-movflags','+faststart',str(output)])
    before,n,metadata=decoded_video_hash(source);after,m,actual=decoded_video_hash(output)
    if before!=after or n!=m:raise ValueError('spoken control changed the actual video frames')
    receipt={'source_video_sha256':file_hash(source),'output_video_sha256':file_hash(output),
        'scene':item['scene'],'start_s':start/24000,'end_s':end/24000,'source_narration':scene['narration'],
        'control_narration':text,'spoken_duration_s':len(replacement)/24000,
        'pcm_outside_edit_identical':bool(np.array_equal(original[:start],changed[:start]) and np.array_equal(original[end:],changed[end:])),
        'decoded_video_identical':True,'target_duration_s':duration,'not_given_to_judge':True,
        'limitation':'Synthetic diagnostic intervention; edited audio is AAC re-encoded. Verify actual pronunciation independently.'}
    write_json(directory/'control_truth.json',receipt)
    return {'id':case_id,'status':'spoken_control_created','artifacts':[{'mode':'spoken_error','complete':True,
        'video_path':str(output.resolve()),'sha256':file_hash(output),'duration_s':actual['duration'],
        'fps':actual['fps'],'frame_count':m,'size':actual['size'],'decoded_video_sha256':after}]}


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--spec',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    args=p.parse_args()
    if args.out.exists():p.error('use a new control directory')
    spec=json.loads(args.spec.read_text())
    for item in spec:
        if not item['id'] or Path(item['id']).name!=item['id']:p.error('safe case IDs required')
    if len({x['id'] for x in spec})!=len(spec):p.error('one control per case in a run')
    freeze_run(args.out,{'entrypoint':'spoken_controls','spec':spec,'spec_sha256':file_hash(args.spec),
        'source_hashes_by_case':{x['id']:{'video':file_hash(x['video']),'plan':file_hash(x['plan'])} for x in spec},
        'not_a_method_result':True})
    cases=[]
    for item in spec:
        cases.append(build(item,args.out));print(item['id'],'spoken control created',flush=True)
    write_json(args.out/'manifest.json',{'cases':cases,'scope':'Synthetic spoken-error calibration controls'})


if __name__=='__main__':main()
