# Pilot first-frame repairs (2026-10-31)

This directory tracks the 11 corrected SVG and PNG diagrams. The other 49
opening frames passed the previous visual review and remain in
`data/first_frames/`. To assemble the complete 60-frame input set, run:

```bash
python -m pip install CairoSVG
python scripts/rebuild_pilot_first_frames.py
```

The rebuild copies those 49 unchanged PNGs and renders the 11 SVGs to PNG.
`review_report_visual_20261031.jsonl` records the source and SHA-256 of each
reviewed frame. The 11 replacements were visually checked by the assistant;
this is not an independent human review. The generation preflight verifies
hashes when this review report is supplied.
