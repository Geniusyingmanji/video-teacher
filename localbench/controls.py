"""Fixed audio interventions for judge calibration; never mixed into task data."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import wave
from pathlib import Path

import imageio_ffmpeg
import numpy as np

from .common import write_json
from .provenance import file_hash, freeze_run


def decoded_video_hash(path):
    reader=imageio_ffmpeg.read_frames(str(path),pix_fmt='rgb24')
    metadata=next(reader);digest=hashlib.sha256();count=0
    for frame in reader:
        digest.update(frame);count+=1
    return digest.hexdigest(),count,metadata


def intervention(samples, kind, shift_samples, sample_rate=24000):
    if kind=='clean':return samples.copy()
    if kind=='muted':return np.zeros_like(samples)
    if kind=='shifted':return np.roll(samples,shift_samples)
    if kind=='tones':
        time=np.arange(len(samples))/sample_rate
        envelope=np.minimum(1,np.minimum(time,np.maximum(0,len(samples)/sample_rate-time))/.25)
        signal=2000*envelope*(np.sin(2*np.pi*440*time)+.5*np.sin(2*np.pi*660*time))
        return np.rint(signal).astype(samples.dtype)
    raise ValueError('unknown intervention')


def build(case, out, modes=('clean','muted','shifted')):
    artifact=next(a for a in case['artifacts'] if a['mode']=='code' and a.get('complete'))
    source=Path(artifact['video_path'])
    if file_hash(source)!=artifact['sha256']:raise ValueError('source video hash mismatch')
    directory=out/case['id'];directory.mkdir(parents=True)
    ffmpeg=imageio_ffmpeg.get_ffmpeg_exe()
    original=directory/'original_audio.wav'
    subprocess.run([ffmpeg,'-y','-v','error','-i',str(source),'-vn','-ar','24000','-ac','1',
                    '-c:a','pcm_s16le',str(original)],check=True)
    with wave.open(str(original)) as wav:
        rate=wav.getframerate();samples=np.frombuffer(wav.readframes(wav.getnframes()),dtype='<i2')
    target_samples=round(artifact['duration_s']*rate)
    samples=np.pad(samples,(0,max(0,target_samples-len(samples))))[:target_samples]
    shift_samples=target_samples//3
    source_hash,frames,metadata=decoded_video_hash(source)
    artifacts=[];control_records=[]
    for kind in modes:
        audio=directory/(kind+'.wav')
        changed=intervention(samples,kind,shift_samples,rate)
        with wave.open(str(audio),'wb') as wav:
            wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(rate);wav.writeframes(changed.tobytes())
        output=directory/(kind+'.mp4')
        subprocess.run([ffmpeg,'-y','-v','error','-i',str(source),'-i',str(audio),
                        '-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','aac','-b:a','96k',
                        '-movflags','+faststart',str(output)],check=True)
        actual_hash,actual_frames,actual=decoded_video_hash(output)
        if actual_hash!=source_hash or actual_frames!=frames:
            raise ValueError('audio control unexpectedly changed decoded video frames')
        artifacts.append({**artifact,'mode':kind,'video_path':str(output.resolve()),
                          'sha256':file_hash(output),'decoded_video_sha256':actual_hash})
        control_records.append({'mode':kind,'audio_pcm_sha256':hashlib.sha256(changed.tobytes()).hexdigest(),
             'peak_pcm':int(np.max(np.abs(changed.astype(np.int32)))),'samples':len(changed),
             'shift_s':shift_samples/rate if kind=='shifted' else 0,
             'exact_video_frames_preserved':True})
        print(case['id'],kind,'created',flush=True)
    return {'id':case['id'],'status':'control_media_created','artifacts':artifacts},control_records


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--run',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--ids',nargs='+',default=['chem_exp_01','math_exp_02'])
    p.add_argument('--modes',nargs='+',choices=['clean','muted','shifted','tones'],default=['clean','muted','shifted'])
    args=p.parse_args()
    if args.out.exists():p.error('choose a fresh output directory')
    run=json.loads((args.run/'manifest.json').read_text())
    cases={c['id']:c for c in run['cases']}
    if set(args.ids)-set(cases):p.error('unknown control case')
    if len(set(args.modes))!=len(args.modes):p.error('duplicate control mode')
    freeze_run(args.out,{'entrypoint':'controls','ids':args.ids,'source_manifest_sha256':file_hash(args.run/'manifest.json'),
                         'interventions':args.modes,'shift_fraction':1/3})
    output=[];records={}
    for id_ in args.ids:
        case,receipt=build(cases[id_],args.out,args.modes);output.append(case);records[id_]=receipt
    write_json(args.out/'manifest.json',{'cases':output,'purpose':'fixed audio-control development corpus'})
    write_json(args.out/'control_truth.json',{'records':records,'not_given_to_judge':True,
        'expected_direction':{'muted':'absent spoken narration; low audio intelligibility/delivery and narration task completion',
                              'shifted':'speech content retained but time shifted; worse audio-visual synchrony',
                              'tones':'audible 440/660 Hz signal without speech; usable signal is not spoken narration',
                              'video':'all variants have exactly identical decoded frames'},
        'limitation':'cyclic shift introduces one audio wrap boundary; not a claim of perfectly invariant audio delivery'})


if __name__=='__main__':main()
