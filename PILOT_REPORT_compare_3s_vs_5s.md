# rise-teacher model comparison

## Headline

| Metric | Wan5B-3s | Wan5B-5s | Wan1.3B-3s | Wan1.3B-5s |
|---|---|---|---|---|
| N videos eval | 60 | 60 | 60 | 60 |
| Mean aggregate (1-5) | 1.754 | 1.789 | 1.823 | 1.788 |
| Strict accuracy (%) | 0.0 | 0.0 | 0.0 | 0.0 |

## Per dimension

| Dimension | Wan5B-3s | Wan5B-5s | Wan1.3B-3s | Wan1.3B-5s |
|---|---|---|---|---|
| conceptual_correctness | 1.45 | 1.567 | 1.567 | 1.517 |
| narrative_structure | 1.5 | 1.7 | 1.45 | 1.4 |
| visual_quality | 2.896 | 2.479 | 3.021 | 3.05 |

## Per discipline (mean aggregate)

| Discipline | Wan5B-3s | Wan5B-5s | Wan1.3B-3s | Wan1.3B-5s |
|---|---|---|---|---|
| art_music | 2.0 | 2.27 | 2.4 | 2.4 |
| biology | 1.79 | 1.95 | 2.02 | 1.84 |
| chemistry | 1.51 | 1.64 | 1.34 | 1.55 |
| civics | 2.01 | 1.35 | 1.77 | 1.58 |
| computer_science | 1.59 | 1.56 | 1.72 | 1.45 |
| economics | 1.35 | 1.38 | 1.65 | 1.44 |
| geography | 1.88 | 1.97 | 2.13 | 1.93 |
| history | 2.23 | 2.13 | 2.36 | 2.4 |
| language_literature | 1.6 | 1.56 | 1.31 | 1.29 |
| mathematics | 1.8 | 1.83 | 1.87 | 2.06 |
| medicine | 1.51 | 1.71 | 1.32 | 1.52 |
| physics | 1.78 | 2.12 | 1.98 | 2.0 |

## Per task type (mean aggregate)

| Task | Wan5B-3s | Wan5B-5s | Wan1.3B-3s | Wan1.3B-5s |
|---|---|---|---|---|
| explanation | 1.924 | 1.947 | 1.933 | 1.897 |
| problem_solving | 1.5 | 1.552 | 1.656 | 1.625 |

## Per difficulty (mean aggregate)

| Difficulty | Wan5B-3s | Wan5B-5s | Wan1.3B-3s | Wan1.3B-5s |
|---|---|---|---|---|
| k12 | 1.909 | 1.862 | 1.943 | 1.984 |
| professional | 1.51 | 1.71 | 1.32 | 1.52 |
| undergrad | 1.629 | 1.723 | 1.785 | 1.621 |