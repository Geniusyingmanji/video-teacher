# Quality repair and reproduction protocol

## Verified implementation changes

The legacy ten-video run and v11 evaluations remain untouched. The new public
benchmark CLI and multi-GPU runner default to `quality-v12`; `legacy-v11`
remains selectable for historical reproduction.

The v12 score averages applicable, evidenced criterion ratings within each
axis, then averages the three video axes and five teaching axes. Narrated
lessons use video/teaching/speech weights 40/40/20; silent tasks use 50/50.
These are explicit policy weights, not an empirically validated learning
measure. External human calibration is still required. A local defect no
longer imposes unrelated numeric caps or a weakest-item veto on the total.
Acceptance failures remain visible and independent of the numeric score.
Missing, malformed or uncertain required evidence yields an unknown score,
not zero or renormalized partial credit. Actual measured failure may score zero.

MathTex participates in layout checks; anchored labels stay tied to their
objects. Opaque foreground geometry is checked for caption obstruction.
Reusable array/formula owners prevent stale object references after swaps,
replacement and cleanup. Geometric helpers provide exact Cantor intervals,
triangle angles and connected flow paths. Generation prompts require these
helpers where relevant. Strict chapter allocation uses exact chapter frame
budgets, preserving source holds. Reviewed source-image operations execute
automatically and must remain visible. Draft generation can explicitly enable
quality repair instead of stopping on render success.

The optional local visual Critic examines ordered actual frames and preserves
its requests, responses and video hash. This is a local-model adaptation of
Code2Video, not the author's native video API. It does not inspect audio.
The quality policy uses faster-whisper-small.en by default; a real crosscheck
recovered the original semiotics narration's “signified”, previously confused
by base ASR. Ambiguous transcript claims must remain unverified.

## Validation and limits

- Full suite: 265 tests and 24 subtests passed; one upstream audioop warning.
- Actual Manim regression videos verify consecutive array swaps, formula
  replacement/cleanup and two answers on the original Markov source image.
  Encoded-source preservation also passes. These are fixtures, not successful
  model-generated benchmark lessons.
- A live Qwen visual-Critic request successfully inspected the sorting clip.
- `results/quality_policy_v12_calibration_20261109` only recomputes arithmetic
  over old judgments. It is neither a fresh evaluation nor evidence that video
  defects were repaired. Every old lesson still fails acceptance.
- Fresh full ten-case generation, content review and iterative repair remain
  required before claiming the original teaching problems are resolved.

## Research selection

Prioritize editable educational figures and executable animation over literal
code screenshots. Compare matched prompts, compilation, label readability,
geometry/topology, required teaching steps and actual rendered output. Keep
author-model runs separate from backbone replacements, and pilot results
separate from full published-benchmark replication.

1. [Code2Video](https://github.com/showlab/Code2Video): closest fit for complete
   narrated teaching animation. Reproduce Planner/Coder/Critic with the local
   Qwen endpoint; explicitly record replacement of original API models.
2. [TikZero / DeTikZify](https://github.com/potamides/DeTikZify): released code
   and weights for editable TikZ scientific graphics. Start with the author's
   end-to-end `nllg/tikzero-plus-10b` text-conditioned checkpoint.
3. [DiagramAgent](https://github.com/DiagramAgent/DiagramAgent_official):
   structured diagrams relevant to flowcharts and scientific explanations.
   The public repository contains README inference snippets and weights links,
   not the complete published multi-agent framework. Report checkpoint
   reproduction separately from a full framework reproduction.

No cross-paper metric establishes a universal “highest quality” method for
our teaching tasks. Selection will use the same educational prompts and
preserved outputs. Missing published artifacts are reported explicitly.

### Access checks and runnable baseline

The author TikZero+ main checkpoint downloaded successfully (revision
`857956cb5dd540b048984f724bd0cf8c45fe2a7a`), and its upstream environment and
TikZ compilation/rasterization smoke check pass. However, its text adapter
also loads `meta-llama/Llama-3.2-1B`: this dependency returns a gated-repository
401 in the current unauthenticated environment. DiagramAgent's Code_Agent
weights likewise return 401. Public README access does not imply weight
access. Authorized Hugging Face access is required for those author-model
experiments; do not report them as completed or substitute another backbone
under the author's model name.

`research/code2image_prompts.jsonl` freezes six matched educational diagram
tasks and concrete checks. `scripts/reproduce_tikzero.py` runs the author
checkpoint once access is available. `scripts/reproduce_code2image_qwen.py`
runs a separately labeled local Qwen SVG baseline on the same prompts. Both
preserve actual prompts, generated code, rendered artifacts and failures.
The current image pilot is not a published-benchmark reproduction.
