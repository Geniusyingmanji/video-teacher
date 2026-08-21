# Human-evaluation handoff directory

No real ratings are stored in Git. Generate a study directory on the machine
that has the selected video manifest and automated per-case results:

```bash
python scripts/human_eval.py export \
  --prompts data/prompts/pilot_v0_1.jsonl \
  --manifest /data/zyf/rise-teacher/generations/SELECTED_RUN/manifest.jsonl \
  --judge /data/zyf/rise-teacher/outputs/SELECTED_RUN/per_case.jsonl \
  --out data/human_eval/pilot_01 \
  --n-cases 60 --raters 3 --seed 20260806
```

Before distribution, the study owner must:

1. Freeze the selected generation run and record its manifest hash.
2. Open every rater packet with `human_eval/index.html` and confirm all videos
   resolve and play.
3. Give each rater only `raters/rater_NN.jsonl`; never distribute the combined
   `assignments.jsonl` or automated judge output.
4. Record qualification outcome, consent, compensation, exclusions, and any
   reassignment in a separate access-controlled audit log.
5. Collect one JSON object per assignment in the response format shown in
   `response.example.jsonl`. Preserve the raw export before cleaning.

After collection closes:

```bash
python scripts/human_eval.py analyse \
  --assignments data/human_eval/pilot_01/assignments.jsonl \
  --responses data/human_eval/pilot_01/responses.jsonl \
  --judge /data/zyf/rise-teacher/outputs/SELECTED_RUN/per_case.jsonl \
  --out docs/analysis/human_validation.md --seed 20260806
```

The protocol and reporting rules are in `docs/HUMAN_EVAL_PROTOCOL.md`. Raw
responses may contain research-participant data and are intentionally ignored
by Git; publish only a reviewed anonymized derivative when consent permits.
