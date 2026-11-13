"""Evidence is extracted from final encoded media, not generation internals."""
from __future__ import annotations

import base64
import hashlib
import io
import math
import subprocess
from pathlib import Path

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw

from .common import write_json


def source_evidence(case):
    """Public input image only; target/answer images are never loaded."""
    from .common import public_case
    attachments = public_case(case).get('public_attachments',[])
    if not attachments:
        return None,[]
    path = attachments[0].get('local_path')
    if not path:
        raise ValueError('required public source image unavailable for evaluation')
    path = Path(path)
    im=Image.open(path).convert('RGB')
    buffer=io.BytesIO();im.save(buffer,format='PNG')
    record={'id':'S00','role':'original_public_input_not_generated_frame',
            'path':str(path.resolve()),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    return record,[{'type':'text','text':'S00: ORIGINAL PUBLIC SOURCE IMAGE. Compare against generated frames for preservation and requested target changes. This is NOT generated-video evidence or an answer image.'},
                   {'type':'image_url','image_url':{'url':'data:image/png;base64,'+base64.b64encode(buffer.getvalue()).decode()}}]


def probe_audio(video):
    """Positive stream inventory only; probing failures never establish absence."""
    try:
        process=subprocess.run(['ffprobe','-v','error','-select_streams','a',
            '-show_entries','stream=index,codec_name','-of','json',str(video)],
            capture_output=True,text=True,timeout=30)
        if process.returncode:
            return {'status':'probe_failed','error':process.stderr[-500:]}
        import json
        raw=json.loads(process.stdout)
        if not isinstance(raw.get('streams'),list):raise ValueError('missing stream inventory')
        return {'status':'present' if raw['streams'] else 'absent','streams':raw['streams'],
                'source':'ffprobe_stream_inventory'}
    except (OSError,ValueError,subprocess.TimeoutExpired) as exc:
        return {'status':'probe_failed','error':str(exc)[:500]}


def extract(video, directory, *, audio_fractions=None, review_every_frame=False):
    video, directory = Path(video), Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    reader = imageio_ffmpeg.read_frames(str(video),pix_fmt='rgb24')
    metadata = next(reader)
    duration, fps = metadata['duration'], metadata['fps']
    width,height=metadata['size']
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError('invalid encoded duration')
    indices = set(round(t*fps) for t in np.linspace(0,max(0,duration-1/fps),24))
    # Short dense windows supplement the whole-video overview.
    for center in (duration*.22,duration*.5,duration*.78):
        indices.update(round((center+delta)*fps) for delta in (-.25,0,.25))
    frames=[];review_frames={}
    count=0;previous=None;previous_small=None
    def save_review(index,raw):
        if index in review_frames:return
        image=Image.frombytes('RGB',(width,height),raw)
        path=directory/f'review_{index:05d}.jpg';image.save(path,quality=88)
        review_frames[index]={'id':f'F{index:06d}','frame_index':index,
            'time_s':round(index/fps,4),'path':str(path.resolve())}
    stride=max(1,int(fps*.5))
    for i,raw in enumerate(reader):
        count+=1
        small=np.asarray(Image.frombytes('RGB',(width,height),raw).resize((160,90)),dtype=np.int16)
        # Inspect every decoded frame for abrupt changes, including brief flashes.
        changed=(previous_small is not None and
                 np.mean(np.abs(small-previous_small)>35)>.015)
        if review_every_frame or i%stride==0 or changed:
            if changed and previous is not None:save_review(i-1,previous)
            save_review(i,raw)
        previous=raw;previous_small=small
        if i not in indices:continue
        image=Image.frombytes('RGB',(width,height),raw)
        path=directory/f'frame_{i:05d}.jpg'
        image.save(path,quality=88)
        frames.append({'id':f'F{len(frames):02d}','frame_index':i,'time_s':round(i/fps,4),'path':str(path.resolve())})
    metadata.update(decoded_frame_count=count,decoded_duration_s=count/fps)
    if count<=0:raise ValueError('no decoded frames')
    save_review(count-1,previous)
    stream_probe=probe_audio(video)
    # Independent audio extraction also verifies that an audio stream is decodable.
    audio=[]
    ffmpeg=imageio_ffmpeg.get_ffmpeg_exe()
    count_chunks=math.ceil(duration/24)
    boundaries=[i*duration/count_chunks for i in range(count_chunks+1)]
    if audio_fractions is not None:
        fractions=list(audio_fractions)
        if not fractions or fractions != sorted(set(fractions)) or any(not 0 < f < 1 for f in fractions):
            raise ValueError('audio fractions must be distinct, increasing and inside (0,1)')
        boundaries=[0]+[duration*f for f in fractions]+[duration]
        count_chunks=len(boundaries)-1
    for i in range(count_chunks):
        start=boundaries[i]
        end=boundaries[i+1]
        path=directory/f'audio_{i:02d}.wav'
        command=[ffmpeg,'-y','-loglevel','error','-i',str(video),'-ss',str(start),'-t',str(end-start),
                 '-vn','-ar','16000','-ac','1','-c:a','pcm_s16le',str(path)]
        if stream_probe['status']=='absent':
            audio.append({'id':f'A{i:02d}','status':'audio_stream_missing','start_s':start,
                          'end_s':end,'stream_probe':stream_probe})
            continue
        process=subprocess.run(command,capture_output=True,text=True)
        if process.returncode:
            audio.append({'id':f'A{i:02d}','status':'extraction_failed','start_s':start,'end_s':end,
                          'error':process.stderr[-500:]})
        else:
            audio.append({'id':f'A{i:02d}','status':'extracted','start_s':round(start,4),'end_s':round(end,4),
                          'path':str(path.resolve()),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                          'is_video_start':i==0,'is_video_end':i==count_chunks-1})
    packet={'video_path':str(video.resolve()),'video_sha256':hashlib.sha256(video.read_bytes()).hexdigest(),
            'metadata':metadata,'frames':frames,'audio':audio,'audio_stream_probe':stream_probe,
            'review_frames':[review_frames[i] for i in sorted(review_frames)],
            'review_sampling':{'version':'timeline-every-frame-v1' if review_every_frame else 'timeline-2fps-change-boundaries-v1',
                'required_scope':'all_decoded_frames' if review_every_frame else 'selected_frames',
                'interval_s':1/fps if review_every_frame else stride/fps,
                'selected_frames':len(review_frames),'decoded_frames':count,
                'scope':'Every decoded frame supplied for window review.' if review_every_frame else 'Every frame decoded for change detection; subthreshold changes between selected samples may be missed.'},
            'source':'final_encoded_video_only',
            'sampling':'24 uniform overview frames + 3 three-frame dense windows',
            'temporal_limit':'Sparse windows do not rule out defects between sampled frames.'}
    write_json(directory/'packet.json',packet)
    thumbs=[]
    for record in frames:
        im=Image.open(record['path']).convert('RGB');im.thumbnail((320,180))
        thumb=Image.new('RGB',(320,204),'white');thumb.paste(im,(0,0))
        ImageDraw.Draw(thumb).text((5,185),f"{record['id']}   {record['time_s']:.2f}s",fill='black')
        thumbs.append(thumb)
    sheet=Image.new('RGB',(320*4,204*math.ceil(len(thumbs)/4)),'#e6eaf0')
    for i,thumb in enumerate(thumbs):sheet.paste(thumb,((i%4)*320,(i//4)*204))
    sheet.save(directory/'contact_sheet.jpg',quality=88)
    return packet


def image_content(record):
    payload = Path(record['path']).read_bytes()
    with Image.open(io.BytesIO(payload)) as picture:
        media_type = {'JPEG':'image/jpeg', 'PNG':'image/png', 'WEBP':'image/webp'}.get(picture.format)
    if media_type is None:
        raise ValueError('image evidence must contain JPEG, PNG or WebP bytes')
    return [{'type':'text','text':f"{record['id']} at {record['time_s']:.3f} seconds"},
            {'type':'image_url','image_url':{'url':f'data:{media_type};base64,'+
              base64.b64encode(payload).decode()}}]


def audio_content(record):
    return {'type':'input_audio','input_audio':{'data':'data:audio/wav;base64,'+
            base64.b64encode(Path(record['path']).read_bytes()).decode(),'format':'wav'}}
