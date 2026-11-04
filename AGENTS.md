# User execution constraints

- Use only GPU 0 and GPU 1. Keep GPU 2 and GPU 3 completely free, including model services and residual workers. This is the user's explicit standing instruction from 2026-11-03.
- Complete code changes and relevant checks before starting the ten-case model validation. Use the frozen representative ten-case set, including one-, two- and three-minute videos, knowledge explanations and worked solutions, simple and advanced tasks. Do not replace failed cases.
- Current lessons require English spoken narration matching the English tasks and labels. Background music is optional and disabled by default. Tones or music alone do not satisfy speech requirements.
- Preserve legacy tasks, failed runs, original constraints and previous scores. Distinguish render success, verified evaluation, and teaching-quality acceptance.
- Current priority (2026-11-03): deliver playable narrated videos first using `--generation-profile draft`. Treat label size, layout, coverage metadata, and small timing deviations as review warnings; defer full quality evaluation. Preserve strict results and label draft delivery separately from quality acceptance. Keep four case workers on GPU 0/1.
