"""Resolve a plan beside the actual selected artifact; verify by decoded pixels."""
import hashlib
import json
from pathlib import Path

import imageio_ffmpeg

from .common import digest, write_json
from .provenance import file_hash


def load(artifact):
    video = Path(artifact['video_path'])
    if file_hash(video) != artifact['sha256']:
        raise ValueError('source artifact hash changed')
    path = video.parent/'plan.json'
    if not path.is_file():
        raise ValueError('selected artifact has no sibling plan; do not fall back to an ancestor plan')
    plan = json.loads(path.read_text())
    if abs(sum(s['duration_s'] for s in plan['scenes']) - artifact['duration_s']) > 1/artifact['fps']:
        raise ValueError('sibling plan duration disagrees with artifact')
    return plan, {'plan_path':str(path.resolve()),'plan_sha256':file_hash(path),
        'video_path':str(video.resolve()),'video_sha256':artifact['sha256'],
        'status':'located_not_render_verified'}


def decoded_rgb(path):
    reader = imageio_ffmpeg.read_frames(str(path), pix_fmt='rgb24')
    metadata = next(reader)
    hasher, count = hashlib.sha256(), 0
    for raw in reader:
        hasher.update(raw)
        count += 1
    return {'size':list(metadata['size']),'fps':metadata['fps'],'frame_count':count,
            'rgb_sha256':hasher.hexdigest()}


def verify(artifact, plan, out):
    """Exact render binding for a reproducible code backend; failure is explicit.

    A changed backend/codec can also fail equality. Do not infer a semantic defect
    solely from a mismatch, or silently accept an unverified source plan.
    """
    from .pipeline import encode
    out = Path(out)
    if out.exists():
        raise ValueError('fresh render verification directory required')
    if artifact['mode'] != 'code':
        raise ValueError('exact plan verification supports the code renderer only')
    if file_hash(artifact['video_path']) != artifact['sha256']:
        raise ValueError('source artifact hash changed')
    out.mkdir(parents=True)
    write_json(out/'plan.json',plan)
    rebuilt = encode(plan,out,Path(artifact['video_path']),mode='code',copy_audio=True)
    source, replay = decoded_rgb(artifact['video_path']), decoded_rgb(rebuilt['video_path'])
    receipt = {'status':'verified' if source == replay else 'mismatch',
        'scope':'All decoded RGB frames/timing of source vs current code rerender; no semantic certification.',
        'plan_hash':digest(plan),'source_video_sha256':artifact['sha256'],
        'rerender_artifact':rebuilt,'source_decoded':source,'rerender_decoded':replay}
    write_json(out/'binding.json',receipt)
    return receipt
