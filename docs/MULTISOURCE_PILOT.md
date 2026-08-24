# GRADE + DisciplineGen-1M pilot

This pilot converts source records from GRADE and DisciplineGen-1M into the
video-teacher prompt schema. It contains 100 draft cases:

- 10 disciplines
- 10 cases per discipline
- 5 GRADE and 5 DisciplineGen-1M cases per discipline

An expanded, diversity-filtered candidate set is also available:

- `data/prompts/multisource_pilot_300.jsonl`
- 300 cases across the same 10 disciplines (27--32 per discipline)
- selection-time near-duplicate rejection at source-text Jaccard >= 0.72
- source shortages are backfilled from the other paper instead of cloning a
  template; the final source mix is recorded in the report

The 300 cases are **paper candidates, not release-ready benchmark items**.
Automated schema/provenance/diversity checks do not replace subject-matter and
paired-image review. See `data/curated/multisource_pilot_300_report.json` for
the exact remaining curation and licensing gates.

The disciplines are mathematics, physics, chemistry, biology, geography,
computer science, economics, history, music, and sports.

## Outputs

- `data/prompts/multisource_pilot_100.jsonl`: runnable prompt records
- `data/curated/multisource_pilot_100_report.json`: balance and schema report
- `data/sources/grade/metadata/data.json`: upstream GRADE metadata
- `data/sources/disciplinegen/metadata/sampled_rows.jsonl`: sampled text metadata
- `data/sources/disciplinegen/metadata/schemas.json`: remote Parquet inventory
- `data/sources/grade/selected_assets/`: local GRADE before/target image pairs

The selected GRADE images are ignored by Git because the upstream redistribution
license is not explicit. The local asset manifest is retained. DisciplineGen
images are not downloaded: its Parquet files use one large row group, so reading
an embedded image column would pull gigabytes. The pilot uses its text
annotations and records the original file, row group, and row index.

## Rebuild

The GRADE metadata file must exist before building. The commands below inspect
and sample DisciplineGen with HTTP byte ranges; they do not download full
Parquet files.

```bash
python scripts/build_multisource_pilot.py inspect-disciplinegen
python scripts/build_multisource_pilot.py sample-disciplinegen --per-file 20
python scripts/build_multisource_pilot.py build
python scripts/build_multisource_pilot.py build --target-per-discipline 30 \
  --out data/prompts/multisource_pilot_300.jsonl \
  --report data/curated/multisource_pilot_300_report.json
python scripts/build_multisource_pilot.py fetch-grade-assets
python scripts/build_multisource_pilot.py validate
```

The seed defaults to `20260803`. Selection is deterministic for an unchanged
upstream dataset. With no `--files` argument, the sampler uses the complete
curated file list (science, CS, chemistry, music, history, math, and both
sports renderers); limiting it to three files does not provide enough source
coverage for a reproducible rebuild.

## Curation status

This dataset is schema-valid but **not release-ready**. Use the explicit release
gate; a plain validation only checks structure and balance:

```bash
python scripts/build_multisource_pilot.py validate --release
```

The release gate additionally verifies provenance, redistribution status,
near-duplicate prompts, and that every record already marked
`reviewed_release_ready` has a complete local before/ground-truth asset pair.

GRADE pairs received a contact-sheet visual screening on 2026-08-04 and remain
`draft_needs_subject_review`. DisciplineGen rows remain
`draft_needs_visual_review`, because their embedded images have not been
retrieved. Content review excluded known factually inconsistent, overly dense,
and near-duplicate records; exclusions are retained in the builder so a rebuild
cannot silently restore them.

The DisciplineGen-1M GitHub repository declares CC BY 4.0, so its records carry
that license and source URL. GRADE remains `unverified`: its Hugging Face page
was rechecked on 2026-08-05 and has no dataset card or displayed license terms.
Its local images therefore remain ignored by Git until redistribution terms are
explicitly confirmed.

Before promoting cases into a benchmark release:

1. Visually inspect each selected source image.
2. Rewrite overly dense prompts into a teachable 4–6 beat sequence.
3. Verify equations, dates, labels, answer conditions, and difficulty.
4. Remove near-duplicates across source datasets.
5. Confirm GRADE redistribution terms or distribute only download scripts and
   source IDs.
