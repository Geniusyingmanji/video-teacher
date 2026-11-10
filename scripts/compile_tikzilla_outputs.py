"""Compile the exact LaTeX document substring, preserving raw model outputs."""
import argparse
import hashlib
import json
from pathlib import Path
import re


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    from detikzify.infer import TikzDocument
    rows = []
    for path in sorted(args.run.glob('*/response.txt')):
        output = path.parent / 'document_only'
        if args.resume and (output / 'result.json').is_file():
            rows.append(json.loads((output / 'result.json').read_text()))
            continue
        output.mkdir(exist_ok=False)
        raw = path.read_text()
        row = {'id': path.parent.name, 'raw_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
               'operation': 'extract exact documentclass through end{document} substring; no code fixes',
               'content_review': 'pending'}
        match = re.search(r'\\documentclass\b[\s\S]*?\\end\{document\}', raw)
        if match:
            document = TikzDocument(match.group())
            document.save(str(output / 'figure.tex'))
            (output / 'compile.log').write_text(document.log)
            row.update(compile_status=document.status, rasterizable=document.is_rasterizable,
                       has_content=document.has_content,
                       prefix_removed=raw[:match.start()], suffix_removed=raw[match.end():])
            if document.is_rasterizable:
                document.save(str(output / 'figure.pdf'))
                document.save(str(output / 'figure.png'), size=1200)
        else:
            row['error'] = 'No complete LaTeX document in original response'
        rows.append(row)
        (output / 'result.json').write_text(json.dumps(row, indent=2) + '\n')
        print(json.dumps(row), flush=True)
    (args.run / 'document_only_report.json').write_text(json.dumps({'cases': rows}, indent=2) + '\n')


if __name__ == '__main__':
    main()
