"""Agreement statistics for current human calibration."""
import math
from collections import Counter


def krippendorff_alpha_ordinal(matrix: list[list[float | None]]) -> float:
    """Krippendorff alpha for ordinal 1--5 ratings; handles missing values."""
    units = [[value for value in row if value is not None] for row in matrix]
    units = [row for row in units if len(row) >= 2]
    values = [value for row in units for value in row]
    if len(units) < 2 or len(set(values)) < 2:
        return float("nan")
    counts = Counter(values)
    n = len(values)
    # Ordinal distance based on cumulative category counts (Krippendorff 2018).
    categories = sorted(counts)
    cumulative = {c: sum(counts[x] for x in categories if x <= c) for c in categories}
    def delta(a: float, b: float) -> float:
        lo, hi = sorted((a, b))
        return (sum(counts[c] for c in categories if lo <= c <= hi) - (counts[lo] + counts[hi]) / 2) ** 2
    observed_num = sum(sum(delta(a, b) for a in row for b in row if a != b) / (len(row) - 1) for row in units)
    observed = observed_num / len(values)
    expected = sum(counts[a] * counts[b] * delta(a, b) for a in categories for b in categories if a != b) / (n * (n - 1))
    return 1 - observed / expected if expected else float("nan")


def json_number(value: float) -> float | None:
    """Return a strict-JSON representation for a possibly non-finite statistic."""
    return value if math.isfinite(value) else None
