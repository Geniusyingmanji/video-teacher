# Six-by-six teaching-video scoring

`eval.run_eval --rubric-6x6` scores six existing teaching dimensions with six
observable criteria each. This follows FORGE's use of named quality axes,
explicit evidence and failure gates, while keeping this project's teaching
targets and original dimension weights. It is a new rubric version; scores
must not be pooled with the legacy six-dimension results.

| Dimension | Six criteria |
| --- | --- |
| Conceptual correctness | core fact; relationships; symbols; steps; final state; no contradiction |
| Narrative structure | setup; target; sequence; transition; completion; pace |
| Visual quality | legibility; text stability; shape stability; artifact control; composition; motion |
| Pedagogical clarity | single focus; attention; explanation; readability; ambiguity; takeaway |
| Didactic affordances | observable change; step evidence; reference anchor; alignment; inspectability; diagnosability |
| Audience appropriateness | prerequisites; vocabulary; complexity; speed; accessibility; task fit |

Every criterion returns an applicability flag, a 1–5 score when applicable,
sampled frame indices, and a concrete finding. Missing visible evidence gets
a low score; inapplicable is reserved for a genuinely absent task element.
Code rejects missing criterion IDs, invalid scores, invalid frame indices and
positive scores without frame evidence. At least four criteria per dimension
must apply. A dimension passes only when its mean is at least 4 and every
applicable criterion scores at least 3. Existing dimension weights produce
the aggregate; the report also includes each criterion's mean and count of
scores at 1 or 2.

The rubric judges sampled frames, so a subtle event between samples can be
missed. Pair it with full-video review and the motion audit. The first runtime
probe had no valid score because the remote Azure CLI grant was revoked;
`scripts.pipeline_artifacts` will reject that result as incomplete.
