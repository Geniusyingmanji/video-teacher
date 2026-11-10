"""Run the released DeTikZify image-to-TikZ model, without a replacement backbone."""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import shutil
import time


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--model', default='/root/models/detikzify-v2.5-8b')
    p.add_argument('--inputs', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--seed', type=int, default=42)
    p.add_argument('--max-new-tokens', type=int, default=4096)
    args = p.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    from transformers import set_seed
    from detikzify.model import load
    from detikzify.infer import DetikzifyPipeline
    report = {'method': 'author DeTikZify v2.5 8B image-to-TikZ single sampling',
              'scope': 'image reconstruction pilot; neither text-to-image nor paper benchmark replication',
              'model': args.model, 'seed': args.seed, 'max_new_tokens': args.max_new_tokens,
              'sampling': {'temperature': .8, 'top_p': .95, 'top_k': 0},
              'environment': {k: importlib.metadata.version(k) for k in ['detikzify', 'torch', 'transformers']},
              'cases': []}
    def save():
        (args.out / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    save()
    start = time.monotonic()
    try:
        pipeline = DetikzifyPipeline(*load(args.model, device_map='auto', torch_dtype='bfloat16'), metric='fast')
    except Exception as exc:
        report['load_error'] = repr(exc)
        save()
        raise
    report['load_seconds'] = time.monotonic() - start
    for index, path in enumerate(sorted(args.inputs.glob('*/figure.png'))):
        directory = args.out / path.parent.name
        directory.mkdir()
        shutil.copy2(path, directory / 'input.png')
        row = {'id': path.parent.name, 'input_source': str(path.resolve()),
               'input_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
               'input_origin': 'previous Qwen SVG pilot raster; reconstruction target, not ground truth',
               'seed': args.seed + index, 'content_review': 'pending'}
        start = time.monotonic()
        set_seed(args.seed + index)
        try:
            figure = pipeline.sample(image=str(directory / 'input.png'), max_new_tokens=args.max_new_tokens)
            figure.save(str(directory / 'figure.tex'))
            (directory / 'compile.log').write_text(figure.log)
            row.update(compile_status=figure.status, rasterizable=figure.is_rasterizable,
                       has_content=figure.has_content)
            if figure.is_rasterizable:
                figure.save(str(directory / 'figure.pdf'))
                figure.save(str(directory / 'figure.png'), size=1200)
        except Exception as exc:
            row['error'] = repr(exc)
        row['seconds'] = time.monotonic() - start
        report['cases'].append(row)
        save()
        print(json.dumps(row), flush=True)


if __name__ == '__main__':
    main()
