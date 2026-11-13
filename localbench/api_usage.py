"""Summarize local Matrix ledgers; reservations are not provider usage or money."""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path

from .common import ROOT, write_json


def empty():
    return dict.fromkeys(('requests', 'ok', 'error', 'unclosed', 'reported_input_tokens',
                          'reported_output_tokens', 'reported_total_tokens',
                          'unknown_usage_reservation'), 0)


def summarize(root):
    starts, ends = {}, {}
    files = sorted(root.rglob('usage.jsonl'))
    duplicate_starts = cache_reuse = 0
    for path in files:
        for line in path.read_text().splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if row['event'] == 'cache_reuse':
                cache_reuse += 1
            elif row['event'] == 'start':
                key = row['request_id']
                duplicate_starts += key in starts
                starts.setdefault(key, {**row, 'run': str(path.parent.relative_to(root))})
            elif row['event'] == 'end':
                ends[row['request_id']] = row
    total, models, runs = empty(), defaultdict(empty), defaultdict(empty)
    for key, start in starts.items():
        end = ends.get(key, {})
        usage = end.get('usage') or {}
        for stats in (total, models[start['model']], runs[start['run']]):
            stats['requests'] += 1
            stats[end.get('status', 'unclosed')] += 1
            stats['reported_input_tokens'] += usage.get('prompt_tokens', usage.get('input_tokens', 0))
            stats['reported_output_tokens'] += usage.get('completion_tokens', usage.get('output_tokens', 0))
            stats['reported_total_tokens'] += usage.get('total_tokens', 0)
            if 'total_tokens' not in usage:
                stats['unknown_usage_reservation'] += start.get('reservation', 0)
    return {'scope': 'Recorded local Matrix requests only; excludes Codex/chat, web search, remote history and account-wide billing. Unknown reservations are not measured billed tokens.',
            'captured_utc': datetime.now(timezone.utc).isoformat(), 'ledger_files': len(files),
            'duplicate_start_records': duplicate_starts, 'cache_reuse_records': cache_reuse,
            'totals': total, 'models': dict(models), 'runs': dict(runs)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=ROOT/'results/localbench')
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--baseline', type=Path)
    args = parser.parse_args()
    summary = summarize(args.root)
    if args.baseline:
        baseline = json.loads(args.baseline.read_text())
        summary['baseline_path'] = str(args.baseline)
        summary['increment'] = {k: v-baseline['totals'][k] for k, v in summary['totals'].items()}
    write_json(args.out, summary)
    print(json.dumps({k: summary[k] for k in ('totals', 'models', 'increment') if k in summary}, indent=2))


if __name__ == '__main__':
    main()
