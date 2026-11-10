"""Collect generated videos without changing originals; preserve a source manifest."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    root, out = args.root.resolve(), args.out.resolve()
    sources = sorted(p for p in root.rglob('*') if p.is_file()
                     and p.suffix.lower() in {'.mp4', '.webm', '.mov', '.mkv'}
                     and out not in p.parents and '.git' not in p.parts)
    out.mkdir(parents=True, exist_ok=True)
    records = []
    for source in sources:
        relative = source.relative_to(root).as_posix()
        name = hashlib.sha256(relative.encode()).hexdigest()[:16] + '__' + source.name
        destination = out / name
        digest = hashlib.file_digest(source.open('rb'), 'sha256').hexdigest()
        if destination.exists():
            if hashlib.file_digest(destination.open('rb'), 'sha256').hexdigest() != digest:
                raise RuntimeError(f'Existing delivery differs: {destination}')
        else:
            shutil.copy2(source, destination)
        records.append({'source': relative, 'file': name, 'bytes': source.stat().st_size,
                        'sha256': digest, 'render_cache_fragment': 'partial_movie_files' in source.parts})
    (out / 'manifest.json').write_text(json.dumps(records, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'directory': str(out), 'files': len(records),
                      'render_cache_fragments': sum(r['render_cache_fragment'] for r in records)}))


if __name__ == '__main__':
    main()
