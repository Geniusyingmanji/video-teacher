# rise-teacher model comparison

## Headline

| Metric | Wan5B-3s | Wan1.3B-3s |
|---|---|---|
| N videos eval | 60 | 60 |
| Mean aggregate (1-5) | 1.754 | 1.823 |
| Strict accuracy (%) | 0.0 | 0.0 |

## Per dimension

| Dimension | Wan5B-3s | Wan1.3B-3s |
|---|---|---|
| conceptual_correctness | 1.45 | 1.567 |
| narrative_structure | 1.5 | 1.45 |
| visual_quality | 2.896 | 3.021 |

## Per discipline (mean aggregate)

| Discipline | Wan5B-3s | Wan1.3B-3s |
|---|---|---|
| art_music | 2.0 | 2.4 |
| biology | 1.79 | 2.02 |
| chemistry | 1.51 | 1.34 |
| civics | 2.01 | 1.77 |
| computer_science | 1.59 | 1.72 |
| economics | 1.35 | 1.65 |
| geography | 1.88 | 2.13 |
| history | 2.23 | 2.36 |
| language_literature | 1.6 | 1.31 |
| mathematics | 1.8 | 1.87 |
| medicine | 1.51 | 1.32 |
| physics | 1.78 | 1.98 |

## Per task type (mean aggregate)

| Task | Wan5B-3s | Wan1.3B-3s |
|---|---|---|
| explanation | 1.924 | 1.933 |
| problem_solving | 1.5 | 1.656 |

## Per difficulty (mean aggregate)

| Difficulty | Wan5B-3s | Wan1.3B-3s |
|---|---|---|
| k12 | 1.909 | 1.943 |
| professional | 1.51 | 1.32 |
| undergrad | 1.629 | 1.785 |