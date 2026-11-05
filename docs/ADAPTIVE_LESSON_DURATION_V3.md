# Task-sized lesson durations (v3)

New lesson prompts use `instructional-lesson-v3`. The original tasks and the v1/v2 lesson files remain available for historical runs. The v3 builder chooses a 30–150 second target in five-second increments from the requested narrative steps, concepts, visual elements, task type and difficulty. Source-image edits are capped at 85 seconds. The same target is passed to the storyboard, renderer, narration and exact frame check, so those stages cannot silently disagree.

The target is a production budget, not a requirement to invent content. Storyboard chapters must have distinct goals and visible evidence; generated code must show the requested steps and cannot use repeated effects or empty holds to fill time. The fixed ten case IDs remain unchanged, while their v3 targets span 55–95 seconds. Historical v2 inputs and results are not relabeled as v3.

`generation/quality_gate.py` now explicitly checks task completion and instructional presentation for scoring v10/v11 and recognizes the v3 contract. A playable file alone does not pass quality acceptance.

These durations are engineering estimates. They still need full ten-case generation and visual review; no new success rate is claimed from the prompt rebuild or unit tests.
