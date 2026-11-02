"""Render the complete event timeline as exactly 75 frames; validate source preservation."""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import sys
import types


class SourceFrameGuard:
    """Compare every unencoded frame with the pristine rendered source frame."""

    def __init__(self, regions, initial_hold_frames=0):
        self.regions = regions
        self.baseline = None
        self.frames = 0
        self.changed_pixels = 0
        self.boxes = []
        self.initial_hold_frames = initial_hold_frames

    def check(self, frame, num_frames=1):
        import numpy as np
        import cv2
        pixels = np.asarray(frame)[..., :3]
        if self.baseline is None:
            self.baseline = pixels.copy()
            h, w = pixels.shape[:2]
            self.mask = np.ones((h, w), bool)
            for x0, y0, x1, y1 in self.regions:
                self.mask[int(np.ceil(y0*h)):int(np.floor(y1*h)),
                          int(np.ceil(x0*w)):int(np.floor(x1*w))] = False
        changed = np.any(pixels != self.baseline, axis=2)
        if self.frames >= self.initial_hold_frames:
            changed &= self.mask
        self.frames += num_frames
        self.changed_pixels = max(self.changed_pixels, int(changed.sum()))
        if changed.any():
            _, _, stats, _ = cv2.connectedComponentsWithStats(changed.astype('uint8'))
            self.boxes = [list(map(int, s[:4])) for s in stats[1:]]

    def report(self):
        return {'valid': self.frames > 0 and self.changed_pixels == 0,
                'checked_frames': self.frames, 'max_changed_pixels': self.changed_pixels,
                'unexpected_change_boxes_pixels': self.boxes}


def allocate_frames(weights, total=75, minimum=1):
    minima = [minimum]*len(weights) if isinstance(minimum, int) else minimum
    if not weights or len(minima) != len(weights) or sum(minima) > total or any(w <= 0 for w in weights):
        raise ValueError('invalid or overly complex timeline')
    budget = total - sum(minima)
    raw = [w / sum(weights) * budget for w in weights]
    frames = [m + int(x) for m,x in zip(minima, raw)]
    for i in sorted(range(len(raw)), key=lambda i: raw[i] % 1, reverse=True)[:total-sum(frames)]:
        frames[i] += 1
    return frames


def inspect_exact(path: Path) -> dict:
    import cv2
    cap = cv2.VideoCapture(str(path))
    fps = cap.get(cv2.CAP_PROP_FPS)
    count = 0
    while True:
        ok, _ = cap.read()
        if not ok:
            break
        count += 1
    cap.release()
    valid = count == 75 and abs(fps-15) < 1e-6
    return {'valid': valid, 'decoded_frames': count, 'fps': fps,
            'duration_seconds': count/fps if fps else None}


def check_source(path: Path, source: Path, regions: list) -> dict:
    import cv2
    import numpy as np
    from PIL import Image
    cap = cv2.VideoCapture(str(path))
    ok, first = cap.read()
    if not ok:
        raise ValueError('source preservation: unreadable video')
    h, w = first.shape[:2]
    src = Image.open(source).convert('RGB')
    scale = min(w/src.width, h/src.height)
    size = (round(src.width*scale), round(src.height*scale))
    expected = Image.new('RGB', (w, h), 'black')
    expected.paste(src.resize(size, Image.Resampling.BICUBIC), ((w-size[0])//2, (h-size[1])//2))
    expected = cv2.cvtColor(np.array(expected), cv2.COLOR_RGB2BGR)
    initial_error = float(np.mean(np.abs(first.astype(float)-expected)))
    mask = np.ones((h, w), bool)
    for x0, y0, x1, y1 in regions:
        mask[max(0, int(y0*h)-3):min(h, int(y1*h)+4), max(0, int(x0*w)-3):min(w, int(x1*w)+4)] = False
    worst = 0.0
    changed = np.zeros((h,w), bool)
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        diff = np.max(cv2.absdiff(first, frame), axis=2)
        changed |= (diff > 20) & mask
        worst = max(worst, float(np.mean(diff[mask] > 20)))
    cap.release()
    result = {'valid': initial_error <= 6 and worst <= .005,
              'initial_source_mean_pixel_error': initial_error,
              'max_changed_fraction_outside_edit_regions': worst, 'edit_regions': regions}
    count, _, stats, _ = cv2.connectedComponentsWithStats(changed.astype('uint8'))
    result['unexpected_change_boxes_pixels'] = [list(map(int, s[:4])) for s in stats[1:] if s[4] >= 6]
    return result


def render(code: Path, scene_name: str, contract_path: Path):
    from manim import BLACK, ImageMobject, config, tempconfig
    from generation.strict_video_contract import validate_regions
    from generation.source_geometry import canvas_box
    contract = json.loads(contract_path.read_text())
    source = Path(contract['source_image']) if contract.get('source_image') else None
    storyboard = json.loads((code.parent / 'storyboard.json').read_text())
    size = contract.get('source_size_pixels')
    source_regions = validate_regions(storyboard.get('source_edit_regions', []), required=bool(source), source_size=size)
    regions = [canvas_box(box, size) for box in source_regions] if source else []
    spec = importlib.util.spec_from_file_location('generated_scene', code)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    cls = getattr(module, scene_name)
    recorded = []
    measured_weights = []
    paths = []
    layout_reports = []
    for phase in ('measure', 'final'):
        options = dict(pixel_width=854, pixel_height=480, frame_rate=15,
                       media_dir=str(code.parent / 'media'), disable_caching=True,
                       output_file=scene_name if phase == 'final' else scene_name + '_timing',
                       background_color=BLACK, write_to_movie=True, save_last_frame=False,
                       verbosity='WARNING')
        with tempconfig(options):
            scene = cls()
            guard = SourceFrameGuard(regions, initial_hold_frames=15) if source and phase == 'final' else None
            if guard:
                original_add_frame = scene.renderer.add_frame
                def guarded_add_frame(frame, num_frames=1):
                    if not scene.renderer.skip_animations:
                        guard.check(frame, num_frames)
                    return original_add_frame(frame, num_frames)
                scene.renderer.add_frame = guarded_add_frame
            if source:
                from generation.source_primitives import SourcePrimitives
                primitives = SourcePrimitives(source, source_regions)
                scene.source_text, scene.source_curve, scene.source_highlight = primitives.text, primitives.curve, primitives.highlight
            verified_calls = set()
            if contract.get('verified_assets'):
                def verified_structure(highlighted=False):
                    key = 'classified' if highlighted else 'initial'
                    verified_calls.add(key)
                    return ImageMobject(contract['verified_assets']['paths'][key]).scale_to_fit_width(9).move_to([0, -.25, 0])
                scene.verified_structure = verified_structure
            old_setup, old_construct = scene.setup, scene.construct
            old_play, old_wait = scene.play, scene.wait
            index, nested = 0, False
            if phase == 'final':
                from tqdm import tqdm
                def exact_progression(run_time, description, n_iterations=None, override_skip_animations=False):
                    count = scene._strict_event_frames
                    return tqdm((i/15 for i in range(count)), total=count, disable=True)
                scene.get_time_progression = exact_progression
                scene.renderer.freeze_current_frame = lambda duration: scene.renderer.add_frame(scene.renderer.get_frame(), num_frames=scene._strict_event_frames)
            observed = []
            def setup(self):
                old_setup()
                if source:
                    image = ImageMobject(str(source))
                    image.scale(min(config.frame_width/image.width, config.frame_height/image.height))
                    image.set_z_index(-1000)
                    self.add(image)
                    if guard:
                        self.camera.capture_mobjects([image])
                        guard.check(self.renderer.get_frame(), 0)
            def event(kind, function, *args, **kwargs):
                nonlocal index, nested
                if nested:
                    return function(*args, **kwargs)
                start = scene.time
                if phase == 'final':
                    if index >= len(recorded) or recorded[index][0] != kind:
                        raise ValueError('non-deterministic timeline; event sequence changed')
                    scene._strict_event_frames = measured_weights[index]
                    duration = measured_weights[index] / 15
                    if kind == 'wait':
                        args, kwargs = (duration,), {'frozen_frame': True}
                    else:
                        kwargs['run_time'] = duration
                nested = True
                try:
                    result = function(*args, **kwargs)
                finally:
                    nested = False
                if phase == 'final' and not source:
                    from generation.layout_guard import check_layout
                    layout_reports.append(check_layout(scene))
                observed.append((kind, max(1/15, scene.time-start)))
                index += 1
                return result
            scene.setup = types.MethodType(setup, scene)
            scene.play = lambda *a, **kw: event('play', old_play, *a, **kw)
            scene.wait = lambda *a, **kw: event('wait', old_wait, *a, **kw)
            def construct(self):
                if source:
                    self.wait(1)
                old_construct()
                self.wait(1)
            scene.construct = types.MethodType(construct, scene)
            scene.render()
            if contract.get('verified_assets') and verified_calls != {'initial', 'classified'}:
                raise ValueError('Verified molecule must be shown with self.verified_structure(False) then self.verified_structure(True); never redraw a guessed structure')
            paths.append(Path(scene.renderer.file_writer.movie_file_path))
            if phase == 'measure':
                recorded = observed
                hold_indices = {len(recorded)-1} | ({0} if source else set())
                body = [i for i in range(len(recorded)) if i not in hold_indices]
                if not body:
                    raise ValueError('scene has no educational animation events')
                body_frames = allocate_frames([recorded[i][1] for i in body], 75-15*len(hold_indices),
                                              [6 if recorded[i][0] == 'play' else 3 for i in body])
                measured_weights = [15] * len(recorded)
                for i, n in zip(body, body_frames):
                    measured_weights[i] = n
            elif index != len(recorded):
                raise ValueError('non-deterministic timeline; missing events')
    diagnostics = {'timing': inspect_exact(paths[-1]), 'event_frames': measured_weights,
                   'events': [dict(kind=kind, frames=n) for (kind,_),n in zip(recorded, measured_weights)]}
    diagnostics['layout'] = {'valid': all(r['valid'] for r in layout_reports),
                             'checks': layout_reports}
    if source:
        diagnostics['source_preservation'] = check_source(paths[-1], source, regions)
        diagnostics['source_preservation']['pre_encoding'] = guard.report()
        diagnostics['source_preservation']['valid'] &= guard.report()['valid']
    diagnostics['rendered_video'] = str(paths[-1])
    (code.parent / 'strict_diagnostics.json').write_text(json.dumps(diagnostics, indent=2))
    if (not diagnostics['timing']['valid'] or not diagnostics['layout']['valid']
            or not diagnostics.get('source_preservation', {'valid': True})['valid']):
        from generation.repair_feedback import compact
        raise ValueError('strict video contract failed: ' + json.dumps(compact(diagnostics)))
    print(json.dumps(diagnostics))


if __name__ == '__main__':
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    parser = argparse.ArgumentParser()
    parser.add_argument('--code', type=Path, required=True)
    parser.add_argument('--scene', required=True)
    parser.add_argument('--contract', type=Path, required=True)
    args = parser.parse_args()
    render(args.code.resolve(), args.scene, args.contract.resolve())
