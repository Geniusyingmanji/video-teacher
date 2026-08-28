"""Build a balanced video-teacher pilot from GRADE and DisciplineGen-1M.

The script deliberately separates source acquisition from prompt conversion:

1. ``inspect-disciplinegen`` reads Parquet metadata with HTTP byte ranges.
2. ``build`` stratifies GRADE and DisciplineGen source rows and converts them
   into the repository's prompt JSONL schema.
3. ``validate`` performs deterministic schema and balance checks.

Large DisciplineGen Parquet files are never downloaded in full.  The remote
reader requests only the footer and the selected non-image column chunks.
Generated prompts are drafts and retain complete source provenance.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import random
import re
import struct
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

import requests

try:
    import pyarrow.parquet as pq
except ImportError:  # pragma: no cover - reported cleanly by CLI
    pq = None


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_GRADE = ROOT / "data" / "sources" / "grade" / "metadata" / "data.json"
DEFAULT_DG_CACHE = (
    ROOT / "data" / "sources" / "disciplinegen" / "metadata" / "sampled_rows.jsonl"
)
DEFAULT_OUT = ROOT / "data" / "prompts" / "multisource_pilot_100.jsonl"
DEFAULT_REPORT = ROOT / "data" / "curated" / "multisource_pilot_100_report.json"
DEFAULT_GRADE_ASSETS = ROOT / "data" / "sources" / "grade" / "selected_assets"
DEFAULT_REPLACEMENTS = [
    ROOT / "data" / "curated" / "disciplinegen_math_replacements.jsonl",
    ROOT / "data" / "curated" / "disciplinegen_sports_replacements.jsonl",
]

HF_REPO = "https://huggingface.co/datasets/VisionXLab/DisciplineGen-1M/resolve/main"
DG_FILES = [
    "science_t2i.parquet",
    "t2i_CS.parquet",
    "t2i_chemistry.parquet",
    "t2i_music.parquet",
    "edit_histrory_timeline_pairs.parquet",
    "edit_math_math_textedit.parquet",
    "edit_sports_data_soccer_formation_dots.parquet",
    "edit_sports_data_soccer_formation_jerseys.parquet",
]

DISCIPLINES = [
    "mathematics",
    "physics",
    "chemistry",
    "biology",
    "geography",
    "computer_science",
    "economics",
    "history",
    "music",
    "sports",
]

GRADE_DOMAIN_MAP = {
    "math": "mathematics",
    "physics": "physics",
    "chemistry": "chemistry",
    "biology": "biology",
    "geography": "geography",
    "ComputerScience": "computer_science",
    "eco": "economics",
    "his": "history",
    "music": "music",
    "sports": "sports",
}

SUBJECT_ALIASES = {
    "math": "mathematics",
    "mathematics": "mathematics",
    "physics": "physics",
    "chemistry": "chemistry",
    "biology": "biology",
    "geography": "geography",
    "computer science": "computer_science",
    "computerscience": "computer_science",
    "computer_science": "computer_science",
    "cs": "computer_science",
    "economics": "economics",
    "economic": "economics",
    "economy": "economics",
    "history": "history",
    "music": "music",
    "sports": "sports",
    "sport": "sports",
}

REQUIRED_FIELDS = [
    "id",
    "discipline",
    "subdomain",
    "task_type",
    "difficulty",
    "prompt_text",
    "expected_concepts",
    "expected_visual_elements",
    "expected_narrative_order",
    "pedagogical_target_audience",
    "discipline_specific_rubric",
    "audio_narration_required",
    "source",
]

RELEASE_STATUS = "reviewed_release_ready"

# The --target-per-discipline build mode caps DisciplineGen at half of each
# discipline's quota and backfills any shortfall from GRADE (see the
# stratified selection loop in `build()`). When a discipline's DisciplineGen
# pool runs short, GRADE ends up supplying most of that discipline's rows,
# which skews the discipline's task style toward GRADE's editing tasks. This
# default bounds how lopsided a single (discipline, source) split may become
# before `validate_rows()` flags it.
DEFAULT_MAX_SOURCE_SHARE_PER_DISCIPLINE = 0.65

# Content-review rejects.  Keep reasons beside the IDs so a rebuild cannot
# silently reintroduce known factual, timing, or near-duplicate failures.
EXCLUDED_IDS = {
    # Too complex to teach or verify in a five-second clip.
    "disciplinegen_chemistry_245572b09063a32f",
    "disciplinegen_chemistry_81f9cbe2717863de",
    "disciplinegen_chemistry_88be750c92b230ab",
    "disciplinegen_chemistry_bc61e816743691bc",
    "disciplinegen_chemistry_c67d6eaa7cf58594",
    "disciplinegen_mathematics_216c15c8c2ff5e9b",
    "disciplinegen_mathematics_3415d53f66ba7ce5",
    "disciplinegen_mathematics_9fabc0a33bc9a82b",
    "disciplinegen_mathematics_a98ebeda698c2e68",
    "disciplinegen_mathematics_c87eccf0c0b469fb",
    # Underspecified/non-instructional or strongly redundant.
    "disciplinegen_computer_science_3a22b78e664d98d1",
    "disciplinegen_computer_science_4532f3fd4cd4b0f2",
    "disciplinegen_computer_science_e56b69e457da21b4",
    "disciplinegen_sports_42a1301b90e5c235",
    "disciplinegen_sports_582b60dadefc313e",
    "disciplinegen_sports_a8bcd52f404166f7",
    "disciplinegen_sports_f9daeeb11d798c3f",
    # Internally inconsistent or factually unsafe source annotations.
    "disciplinegen_economics_aff3f8f7569edaca",
    "disciplinegen_economics_bb6e84327a81cfff",
    "disciplinegen_economics_e1bda9785a4efb87",
    "disciplinegen_history_d551740f09aba6d5",
    "disciplinegen_music_e8874a08749c62f3",
    "disciplinegen_music_f22fa408d03378f2",
    "grade_his_task_26",
}


class HttpRangeReader(io.RawIOBase):
    """Seekable HTTP file backed by byte-range requests."""

    def __init__(
        self,
        url: str,
        *,
        size: int | None = None,
        timeout: int = 90,
        block_size: int = 1 << 20,
    ) -> None:
        self.url = url
        self.timeout = timeout
        self.block_size = block_size
        self.session = requests.Session()
        self.pos = 0
        self._closed = False
        self._cache_start = -1
        self._cache = b""
        self.size = size or self._discover_size()

    def _discover_size(self) -> int:
        response = self.session.get(
            self.url,
            headers={"Range": "bytes=0-0"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        content_range = response.headers.get("Content-Range", "")
        match = re.search(r"/(\d+)$", content_range)
        if not match:
            raise OSError(f"server did not return file size for {self.url}")
        return int(match.group(1))

    def readable(self) -> bool:
        return True

    def seekable(self) -> bool:
        return True

    def tell(self) -> int:
        return self.pos

    def seek(self, offset: int, whence: int = io.SEEK_SET) -> int:
        if whence == io.SEEK_SET:
            new_pos = offset
        elif whence == io.SEEK_CUR:
            new_pos = self.pos + offset
        elif whence == io.SEEK_END:
            new_pos = self.size + offset
        else:
            raise ValueError(f"unsupported whence: {whence}")
        if new_pos < 0:
            raise ValueError("negative seek position")
        self.pos = min(new_pos, self.size)
        return self.pos

    def read(self, size: int = -1) -> bytes:
        if self.pos >= self.size:
            return b""
        if size is None or size < 0:
            size = self.size - self.pos
        size = min(size, self.size - self.pos)
        if size == 0:
            return b""

        cache_end = self._cache_start + len(self._cache)
        if self._cache_start <= self.pos and self.pos + size <= cache_end:
            start = self.pos - self._cache_start
            out = self._cache[start : start + size]
            self.pos += len(out)
            return out

        fetch_start = self.pos
        fetch_size = max(size, self.block_size)
        fetch_end = min(self.size - 1, fetch_start + fetch_size - 1)
        response = self.session.get(
            self.url,
            headers={"Range": f"bytes={fetch_start}-{fetch_end}"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        if response.status_code != 206:
            raise OSError(f"server ignored range request for {self.url}")
        self._cache_start = fetch_start
        self._cache = response.content
        out = self._cache[:size]
        self.pos += len(out)
        return out

    def readinto(self, buffer: bytearray) -> int:
        data = self.read(len(buffer))
        buffer[: len(data)] = data
        return len(data)

    def close(self) -> None:
        if not self._closed:
            self.session.close()
            self._closed = True
        super().close()


def jsonl_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def clean_text(value: Any, limit: int = 800) -> str:
    if value is None:
        return ""
    if isinstance(value, str) and value.lstrip().startswith(("{", "[")):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            pass
    if isinstance(value, (list, tuple)):
        human_values = [
            item.get("value")
            for item in value
            if isinstance(item, dict)
            and str(item.get("from", "")).lower() in {"human", "user"}
            and item.get("value")
        ]
        selected = human_values or value
        value = " ".join(clean_text(item, limit=limit) for item in selected)
    elif isinstance(value, dict):
        for key in ("text", "value", "caption", "prompt", "instruction"):
            if key in value:
                return clean_text(value[key], limit=limit)
        value = json.dumps(value, ensure_ascii=False)
    text = re.sub(r"\s+", " ", str(value)).strip()
    # A small number of upstream annotations contain a consistent encoding
    # artifact for degree and less-than-or-equal symbols.
    text = text.replace("Ёу", "°").replace("Ём", "≤")
    return text[:limit]


def stable_key(row: dict[str, Any]) -> str:
    payload = json.dumps(row, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def normalize_subject(value: Any, filename: str = "") -> str | None:
    text = clean_text(value, limit=100).lower().replace("-", " ").replace("_", " ")
    for alias, discipline in SUBJECT_ALIASES.items():
        if text == alias or re.search(rf"\b{re.escape(alias)}\b", text):
            return discipline
    lower_name = filename.lower()
    for alias, discipline in SUBJECT_ALIASES.items():
        if alias.replace(" ", "_") in lower_name or alias.replace(" ", "") in lower_name:
            return discipline
    return None


def parquet_schema(filename: str) -> dict[str, Any]:
    if pq is None:
        raise RuntimeError("pyarrow is required: pip install pyarrow")
    url = f"{HF_REPO}/{filename}"
    with HttpRangeReader(url) as remote:
        parquet = pq.ParquetFile(remote)
        compressed_bytes = Counter()
        for row_group_id in range(parquet.metadata.num_row_groups):
            row_group = parquet.metadata.row_group(row_group_id)
            for column_id in range(row_group.num_columns):
                column = row_group.column(column_id)
                compressed_bytes[column.path_in_schema] += column.total_compressed_size
        return {
            "filename": filename,
            "url": url,
            "size": remote.size,
            "num_rows": parquet.metadata.num_rows,
            "num_row_groups": parquet.metadata.num_row_groups,
            "columns": [
                {
                    "name": field.name,
                    "type": str(field.type),
                    "compressed_bytes": compressed_bytes[field.name],
                }
                for field in parquet.schema_arrow
            ],
        }


def inspect_disciplinegen(args: argparse.Namespace) -> None:
    files = args.files or DG_FILES
    report = []
    for index, filename in enumerate(files, 1):
        print(f"[inspect] {index}/{len(files)} {filename}", flush=True)
        try:
            report.append(parquet_schema(filename))
        except Exception as exc:  # continue so one huge/broken file does not hide others
            report.append({"filename": filename, "error": f"{type(exc).__name__}: {exc}"})
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[inspect] wrote {output}")


def useful_columns(schema_names: list[str]) -> list[str]:
    """Select metadata columns while excluding embedded image/code blobs."""
    preferred = [
        "id",
        "task_id",
        "subject",
        "discipline",
        "domain",
        "subdomain",
        "category",
        "type",
        "task_type",
        "prompt",
        "text",
        "caption",
        "instruction",
        "edit_instruction",
        "conversations",
        "metadata",
    ]
    by_lower = {name.lower(): name for name in schema_names}
    selected = [by_lower[name] for name in preferred if name in by_lower]
    if not selected:
        selected = [
            name
            for name in schema_names
            if not any(token in name.lower() for token in ("image", "bytes", "code"))
        ][:12]
    return selected


def sample_remote_parquet(
    filename: str,
    *,
    per_file: int,
    seed: int,
) -> list[dict[str, Any]]:
    if pq is None:
        raise RuntimeError("pyarrow is required: pip install pyarrow")
    rng = random.Random(f"{seed}:{filename}")
    url = f"{HF_REPO}/{filename}"
    with HttpRangeReader(url) as remote:
        parquet = pq.ParquetFile(remote)
        schema_names = parquet.schema_arrow.names
        columns = useful_columns(schema_names)
        # DisciplineGen currently stores each file in one very large row group.
        # Use its small metadata column to find rare subjects before fetching
        # the conversations column; naive random sampling misses Geography and
        # Economics almost every time.
        if "metadata" in schema_names and parquet.metadata.num_row_groups == 1:
            metadata_values = (
                parquet.read(columns=["metadata"]).column("metadata").to_pylist()
            )
            indices_by_subject: dict[str, list[int]] = defaultdict(list)
            for row_index, metadata in enumerate(metadata_values):
                discipline = None
                try:
                    parsed = json.loads(metadata) if isinstance(metadata, str) else metadata
                except json.JSONDecodeError:
                    parsed = None
                if isinstance(parsed, dict):
                    discipline = normalize_subject(parsed.get("subject"), filename)
                discipline = discipline or normalize_subject("", filename)
                if discipline:
                    indices_by_subject[discipline].append(row_index)
            chosen_indices = []
            for discipline in sorted(indices_by_subject):
                candidates = indices_by_subject[discipline]
                rng.shuffle(candidates)
                chosen_indices.extend(candidates[:per_file])
            if chosen_indices:
                table = parquet.read(columns=columns).take(chosen_indices)
                output = []
                for row_index, row in zip(chosen_indices, table.to_pylist()):
                    row["_source_file"] = filename
                    row["_row_group"] = 0
                    row["_row_index"] = row_index
                    row["_source_key"] = stable_key(row)
                    output.append(row)
                return output

        group_ids = list(range(parquet.metadata.num_row_groups))
        rng.shuffle(group_ids)
        output: list[dict[str, Any]] = []
        for group_id in group_ids:
            table = parquet.read_row_group(group_id, columns=columns)
            records = table.to_pylist()
            rng.shuffle(records)
            for row in records:
                row["_source_file"] = filename
                row["_row_group"] = group_id
                row["_row_index"] = None
                row["_source_key"] = stable_key(row)
                output.append(row)
                if len(output) >= per_file:
                    return output
        return output


def sample_disciplinegen(args: argparse.Namespace) -> None:
    rows: list[dict[str, Any]] = []
    files = args.files or DG_FILES
    for index, filename in enumerate(files, 1):
        print(f"[sample] {index}/{len(files)} {filename}", flush=True)
        try:
            sampled = sample_remote_parquet(
                filename,
                per_file=args.per_file,
                seed=args.seed,
            )
            rows.extend(sampled)
            print(f"[sample] {filename}: {len(sampled)} metadata rows", flush=True)
        except Exception as exc:
            print(f"[sample] {filename}: ERROR {type(exc).__name__}: {exc}", file=sys.stderr)
    write_jsonl(Path(args.out), rows)
    print(f"[sample] wrote {len(rows)} rows to {args.out}")


def row_text_fields(row: dict[str, Any]) -> list[str]:
    fields = []
    for key in (
        "prompt",
        "text",
        "caption",
        "instruction",
        "edit_instruction",
        "conversations",
        "description",
        "metadata",
    ):
        if key in row:
            value = clean_text(row[key])
            if value:
                fields.append(value)
    return fields


def infer_dg_discipline(row: dict[str, Any]) -> str | None:
    filename = clean_text(row.get("_source_file"), limit=200)
    # Upstream ships the history file with this misspelling in its filename.
    if "histrory" in filename.lower() or "history" in filename.lower():
        return "history"
    for key in ("subject", "discipline", "domain", "category", "subdomain"):
        discipline = normalize_subject(row.get(key), filename)
        if discipline:
            return discipline
    metadata = row.get("metadata")
    if isinstance(metadata, str):
        try:
            metadata = json.loads(metadata)
        except json.JSONDecodeError:
            metadata = None
    if isinstance(metadata, dict):
        for key in ("subject", "discipline", "domain", "category", "subdomain"):
            discipline = normalize_subject(metadata.get(key), filename)
            if discipline:
                return discipline
    joined = " ".join(row_text_fields(row))
    return normalize_subject(joined, filename)


def has_usable_text(row: dict[str, Any]) -> bool:
    text = " ".join(row_text_fields(row))
    # Very short records lack a teachable target; very long records routinely
    # require illegible multi-panel scenes in a five-second benchmark clip.
    return 35 <= len(text) <= 1200


def source_tokens(row: dict[str, Any]) -> set[str]:
    """Content tokens used for selection-time diversity checks."""
    return set(re.findall(r"[a-z0-9]+", " ".join(row_text_fields(row)).lower()))


def diverse_take(
    candidates: list[dict[str, Any]],
    count: int,
    *,
    max_jaccard: float = 0.62,
) -> list[dict[str, Any]]:
    """Greedily keep content-distinct rows, relaxing only to fill the quota.

    Selection is deterministic because callers establish candidate order first.
    Exact and very close variants are never admitted during the relaxation pass.
    """
    selected: list[dict[str, Any]] = []
    selected_tokens: list[set[str]] = []
    deferred: list[tuple[float, dict[str, Any], set[str]]] = []
    for row in candidates:
        tokens = source_tokens(row)
        highest = max(
            (
                len(tokens & prior) / len(tokens | prior)
                for prior in selected_tokens
                if tokens | prior
            ),
            default=0.0,
        )
        if highest < max_jaccard:
            selected.append(row)
            selected_tokens.append(tokens)
            if len(selected) == count:
                return selected
        else:
            deferred.append((highest, row, tokens))
    for highest, row, tokens in sorted(deferred, key=lambda item: item[0]):
        if highest < 0.72:
            selected.append(row)
            selected_tokens.append(tokens)
            if len(selected) == count:
                break
    return selected


def stratified_grade(rows: list[dict[str, Any]], per_discipline: int, seed: int) -> list[dict[str, Any]]:
    pools: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        discipline = GRADE_DOMAIN_MAP.get(row.get("domain"))
        if discipline:
            pools[discipline].append(row)
    output = []
    for discipline in DISCIPLINES:
        candidates = [
            row
            for row in pools[discipline]
            if f"grade_{clean_text(row.get('task_id'), 120)}".lower()
            not in EXCLUDED_IDS
        ]
        rng = random.Random(f"{seed}:grade:{discipline}")
        rng.shuffle(candidates)
        # Cycle through subdomains first for breadth.
        buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in candidates:
            buckets[clean_text(row.get("sub_task"), 100) or "general"].append(row)
        ordered = []
        while buckets:
            for name in sorted(list(buckets)):
                ordered.append(buckets[name].pop())
                if not buckets[name]:
                    del buckets[name]
        output.extend(diverse_take(ordered, per_discipline))
    return output


def stratified_dg(rows: list[dict[str, Any]], per_discipline: int, seed: int) -> list[dict[str, Any]]:
    pools: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        discipline = infer_dg_discipline(row)
        if discipline and has_usable_text(row):
            row = dict(row)
            row["_inferred_discipline"] = discipline
            pools[discipline].append(row)
    output = []
    for discipline in DISCIPLINES:
        candidates = [
            row
            for row in pools[discipline]
            if (
                f"disciplinegen_{discipline}_"
                f"{clean_text(row.get('_source_key'), 40) or stable_key(row)}"
            ).lower()
            not in EXCLUDED_IDS
        ]
        rng = random.Random(f"{seed}:dg:{discipline}")
        rng.shuffle(candidates)
        # Prefer annotations that fit a short teaching video while retaining
        # deterministic random tie-breaking from the shuffle above.
        candidates.sort(key=lambda row: abs(len(" ".join(row_text_fields(row))) - 360))
        # Cycle through upstream files so a large templated edit subset cannot
        # crowd out a smaller but topically broader source partition. The
        # history timeline partition is especially repetitive at task level.
        buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in candidates:
            filename = clean_text(row.get("_source_file"), 200) or "unknown"
            buckets[filename].append(row)
        if discipline == "history":
            timeline_name = "edit_histrory_timeline_pairs.parquet"
            buckets[timeline_name] = buckets.get(timeline_name, [])[:5]
        ordered = []
        while buckets:
            for name in sorted(list(buckets)):
                ordered.append(buckets[name].pop(0))
                if not buckets[name]:
                    del buckets[name]
        output.extend(diverse_take(ordered, per_discipline))
    return output


def timed_beats(beats: list[str]) -> list[dict[str, Any]]:
    output = []
    count = max(len(beats), 1)
    for index, beat in enumerate(beats):
        start = max(1, round(index / count * 7 + 1))
        end = min(8, round((index + 1) / count * 7 + 1))
        output.append({"beat": beat, "expected_frame_range": [start, end]})
    return output


def pedagogical_archetype(text: str, subdomain: str = "") -> str:
    """Infer a source-grounded teaching operation without inventing an answer."""
    joined = f"{subdomain} {text}".lower()
    rules = [
        ("quantitative_reasoning", r"calculate|equation|formula|graph|plot|curve|axis|scale|vector|angle|probability"),
        ("comparison", r"compare|contrast|difference|versus| vs\.? |distinguish|before and after"),
        ("temporal_sequence", r"timeline|sequence|cycle|stages?|steps?|route|path|process|flow|progression"),
        ("causal_mechanism", r"mechanism|cause|effect|because|interaction|transmission|reaction|force|inheritance"),
        ("classification", r"classify|category|group|sort|type of|taxonomy|hierarchy"),
        ("spatial_reasoning", r"map|location|region|formation|geometry|spatial|direction|position|anatom"),
        ("evidence_inference", r"infer|evidence|determine|diagnos|deduce|interpret|identify the correct"),
        ("labeling", r"label|annotat|name|mark the|point to|numbered"),
    ]
    for name, pattern in rules:
        if re.search(pattern, joined):
            return name
    return "visual_transformation"


def archetype_spec(archetype: str, focus: str) -> tuple[list[str], list[str], list[str]]:
    short_focus = clean_text(focus, 420)
    specs = {
        "quantitative_reasoning": (
            ["the given quantities, axes, or symbolic constraints", "a visible intermediate calculation or construction", "the source-specified quantitative result"],
            [f"frame the quantitative task from the source: {short_focus}", "highlight only the values, axes, or constraints needed", "show one checkable calculation or geometric operation", "reveal the result and verify units, scale, direction, or invariant"],
            ["all displayed quantities and symbols come from the source record", "the intermediate operation is mathematically valid and visually checkable", "the final state satisfies the source-specified constraint"],
        ),
        "comparison": (
            ["the two source-defined cases in a stable side-by-side layout", "matched callouts on the same comparison dimensions", "a concise visual statement of the decisive difference"],
            [f"pose the source-grounded comparison: {short_focus}", "align the two cases so like features occupy comparable positions", "highlight one shared feature and one discriminating feature", "state the supported contrast without adding facts absent from the source"],
            ["both cases are represented faithfully", "the comparison uses equivalent visual criteria", "the conclusion follows from the highlighted difference"],
        ),
        "temporal_sequence": (
            ["an ordered timeline, route, cycle, or process path", "directional arrows and readable stage labels", "a visibly verified ordering or endpoint"],
            [f"show the incomplete or untraced sequence specified by the source: {short_focus}", "anchor the start state and direction of progression", "reveal the key stages or route segments in source order", "check the final order, continuity, and endpoint"],
            ["the order and direction match the source", "no stage or route segment is silently invented", "the final sequence is continuous and readable"],
        ),
        "causal_mechanism": (
            ["the source-defined components before interaction", "arrows that encode the stated causal or mechanistic direction", "the resulting state separated from the initiating condition"],
            [f"identify the mechanism to be shown: {short_focus}", "isolate the initiating component or condition", "animate the interaction in causal order", "connect the resulting state only to relationships supported by the source"],
            ["components and causal direction are source-faithful", "cause and outcome are visually distinguishable", "the explanation does not introduce an unsupported mechanism"],
        ),
        "classification": (
            ["the source items before grouping", "clearly bounded categories with one visible criterion", "a final placement that can be checked item by item"],
            [f"present the classification task from the source: {short_focus}", "make the grouping criterion explicit", "place or reveal items according to that single criterion", "audit each placement against the stated category rule"],
            ["the classification criterion is explicit", "each item is placed using the same rule", "category labels and boundaries remain unambiguous"],
        ),
        "spatial_reasoning": (
            ["the unchanged source map, anatomy, formation, or geometry", "a localized spatial cue for the relevant region or relation", "the completed placement, direction, or construction"],
            [f"orient the viewer to the source layout: {short_focus}", "highlight the fixed landmarks or reference geometry", "add the requested spatial relation without moving unrelated elements", "verify position, direction, adjacency, or alignment"],
            ["reference landmarks remain unchanged", "the requested spatial relation is correctly positioned", "the result is verifiable from the final frame"],
        ),
        "evidence_inference": (
            ["the source evidence before annotation", "two or more localized evidence callouts", "a conclusion panel linked back to those callouts"],
            [f"state the inference question supported by the source: {short_focus}", "mark the first relevant visual clue", "combine it with a second independent clue", "show the narrowest conclusion supported by those clues"],
            ["the conclusion cites visible source evidence", "at least two relevant clues are spatially grounded", "the conclusion does not exceed what the evidence supports"],
        ),
        "labeling": (
            ["the unlabeled or partially labeled source visual", "leader lines that terminate on exact targets", "a completed label set with no ambiguous attachment"],
            [f"show the labeling target from the source: {short_focus}", "locate each target before revealing its name", "attach labels one at a time with non-crossing leader lines", "check spelling, one-to-one attachment, and completeness"],
            ["labels reproduce the source terminology", "every label points to exactly one intended target", "labels remain readable without covering evidence"],
        ),
        "visual_transformation": (
            ["the unchanged input visual", "a highlighted edit region and source-defined operation", "the final state beside or overlaid on the input"],
            [f"state the precise source-defined transformation: {short_focus}", "freeze unrelated content and mark the allowed edit region", "perform the requested change in one inspectable progression", "compare input and output against the source condition"],
            ["the transformation follows the source instruction exactly", "unrelated content is preserved", "the final change is visible and independently checkable"],
        ),
    }
    return specs[archetype]


def grade_to_prompt(row: dict[str, Any]) -> dict[str, Any]:
    discipline = GRADE_DOMAIN_MAP[row["domain"]]
    subdomain = clean_text(row.get("sub_task"), 100) or "general"
    instruction = clean_text(row.get("text"))
    rubrics = [clean_text(question.get("question")) for question in row.get("questions", [])]
    rubrics = [item for item in rubrics if item]
    for fallback in (
        "the requested change is completed",
        "the final state is disciplinarily correct",
        "unrelated visual content remains unchanged",
    ):
        if len(rubrics) >= 3:
            break
        if fallback not in rubrics:
            rubrics.append(fallback)
    archetype = pedagogical_archetype(instruction, subdomain)
    visuals, beats, archetype_rubrics = archetype_spec(archetype, instruction)
    concepts = [
        subdomain,
        archetype.replace("_", " "),
        f"source-defined target: {clean_text(instruction, 180)}",
    ]
    rubrics.extend(item for item in archetype_rubrics if item not in rubrics)
    source_id = clean_text(row["task_id"], 120)
    return {
        "id": f"grade_{source_id}".lower(),
        "discipline": discipline,
        "subdomain": subdomain,
        "task_type": "problem_solving",
        "difficulty": "undergrad",
        "prompt_text": (
            "Generate a 5-second educational video using the supplied source diagram. "
            f"Teach this source-grounded {archetype.replace('_', ' ')} task without "
            f"introducing facts not present in the source: {instruction} End with a "
            "visually checkable result."
        ),
        "expected_concepts": concepts,
        "expected_visual_elements": visuals,
        "expected_narrative_order": beats,
        "pedagogical_target_audience": f"introductory {discipline.replace('_', ' ')} student",
        "discipline_specific_rubric": rubrics[:6],
        "audio_narration_required": False,
        "target_duration_s": 5,
        "narrative_beats": timed_beats(beats),
        "source": {
            "dataset": "GRADE",
            "source_id": source_id,
            "source_url": "https://huggingface.co/datasets/VisionXLab/GRADE",
            "source_image_path": row.get("image_path"),
            "target_image_path": row.get("gt"),
            "original_instruction": instruction,
            "license_status": "unverified",
        },
        "curation": {
            "status": "draft_needs_subject_review",
            "conversion": "source_grounded_archetype_v2",
            "pedagogical_archetype": archetype,
            "automatic_quality_checks": {
                "source_grounded": True,
                "visually_checkable_endpoint": True,
                "unsupported_fact_generation_forbidden": True,
                "subject_matter_review": "required",
            },
            "visual_pair_screening": {
                "status": "passed",
                "method": "paired contact-sheet review",
                "review_date": "2026-08-04",
            },
        },
    }


def dg_to_prompt(row: dict[str, Any]) -> dict[str, Any]:
    discipline = row["_inferred_discipline"]
    filename = clean_text(row.get("_source_file"), 200)
    source_texts = row_text_fields(row)
    source_text = source_texts[0]
    subdomain = (
        clean_text(row.get("subdomain"), 100)
        or clean_text(row.get("category"), 100)
        or Path(filename).stem
    )
    is_edit = filename.startswith("edit_") or any(
        key in row for key in ("instruction", "edit_instruction")
    )
    task_type = "problem_solving" if is_edit else "explanation"
    source_key = clean_text(row.get("_source_key"), 40) or stable_key(row)
    archetype = pedagogical_archetype(source_text, subdomain)
    visuals, beats, rubrics = archetype_spec(archetype, source_text)
    concepts = [
        subdomain,
        archetype.replace("_", " "),
        f"source-defined relationship: {clean_text(source_text, 180)}",
    ]
    return {
        "id": f"disciplinegen_{discipline}_{source_key}".lower(),
        "discipline": discipline,
        "subdomain": subdomain,
        "task_type": task_type,
        "difficulty": "undergrad",
        "prompt_text": (
            "Generate a 5-second educational video from this DisciplineGen source "
            f"annotation as a {archetype.replace('_', ' ')} task. Use only relationships "
            f"stated or visibly specified by the source. Source annotation: {source_text}"
        ),
        "expected_concepts": concepts,
        "expected_visual_elements": visuals,
        "expected_narrative_order": beats,
        "pedagogical_target_audience": f"introductory {discipline.replace('_', ' ')} student",
        "discipline_specific_rubric": rubrics,
        "audio_narration_required": False,
        "target_duration_s": 5,
        "narrative_beats": timed_beats(beats),
        "source": {
            "dataset": "DisciplineGen-1M",
            "source_id": source_key,
            "source_url": (
                "https://huggingface.co/datasets/VisionXLab/"
                f"DisciplineGen-1M/blob/main/{filename}"
            ),
            "source_file": filename,
            "row_group": row.get("_row_group"),
            "row_index": row.get("_row_index"),
            "original_annotation": source_text,
            # Declared by the upstream GitHub repository README.
            "license_status": "verified_redistributable",
            "license": "CC BY 4.0",
            "license_source": "https://github.com/VisionXLab/DisciplineGen-1M",
        },
        "curation": {
            "status": "draft_needs_visual_review",
            "conversion": "source_grounded_archetype_v2",
            "pedagogical_archetype": archetype,
            "automatic_quality_checks": {
                "source_grounded": True,
                "visually_checkable_endpoint": True,
                "unsupported_fact_generation_forbidden": True,
                "subject_matter_review": "required",
            },
        },
    }


def validate_rows(
    rows: list[dict[str, Any]],
    *,
    expected_per_source_discipline: int | None = None,
    expected_per_discipline: int | None = None,
    expected_total: int | None = None,
    max_source_share_per_discipline: float = DEFAULT_MAX_SOURCE_SHARE_PER_DISCIPLINE,
) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    ids = Counter(row.get("id") for row in rows)
    for row in rows:
        row_issues = []
        for field in REQUIRED_FIELDS:
            if field not in row:
                row_issues.append(f"missing field: {field}")
        if row.get("discipline") not in DISCIPLINES:
            row_issues.append("invalid discipline")
        if row.get("task_type") not in {"explanation", "problem_solving"}:
            row_issues.append("invalid task_type")
        if ids[row.get("id")] != 1:
            row_issues.append("duplicate id")
        for field in (
            "expected_concepts",
            "expected_visual_elements",
            "expected_narrative_order",
            "discipline_specific_rubric",
        ):
            if not isinstance(row.get(field), list) or len(row.get(field, [])) < 3:
                row_issues.append(f"{field} must contain at least 3 items")
        source = row.get("source")
        if not isinstance(source, dict):
            row_issues.append("source must be an object")
        else:
            if source.get("dataset") not in {"GRADE", "DisciplineGen-1M"}:
                row_issues.append("source.dataset must be GRADE or DisciplineGen-1M")
            for field in ("source_id", "source_url", "license_status"):
                if not clean_text(source.get(field), 1000):
                    row_issues.append(f"source.{field} is required")
        if not isinstance(row.get("curation"), dict):
            row_issues.append("curation must be an object")
        if row_issues:
            issues.append({"id": row.get("id"), "issues": row_issues})

    by_source = Counter(row.get("source", {}).get("dataset") for row in rows)
    by_discipline = Counter(row.get("discipline") for row in rows)
    by_source_discipline = Counter(
        (row.get("source", {}).get("dataset"), row.get("discipline")) for row in rows
    )
    if expected_per_source_discipline is not None:
        for source in ("GRADE", "DisciplineGen-1M"):
            for discipline in DISCIPLINES:
                actual = by_source_discipline[(source, discipline)]
                if actual != expected_per_source_discipline:
                    issues.append(
                        {
                            "scope": f"{source}/{discipline}",
                            "issues": [
                                f"expected {expected_per_source_discipline} rows, got {actual}"
                            ],
                        }
                    )
    # Independent of the equality check above (which only applies to the
    # fixed-per-source-discipline build mode), always flag a discipline whose
    # two-source split is heavily skewed toward one paper. This catches the
    # --target-per-discipline mode, where no equality target is passed but a
    # DisciplineGen shortfall can still let GRADE dominate a discipline.
    source_share_issues: list[dict[str, Any]] = []
    for discipline in DISCIPLINES:
        discipline_total = by_discipline[discipline]
        if discipline_total == 0:
            continue
        for source in ("GRADE", "DisciplineGen-1M"):
            share = by_source_discipline[(source, discipline)] / discipline_total
            if share > max_source_share_per_discipline:
                source_share_issues.append(
                    {
                        "scope": f"{source}/{discipline}",
                        "issues": [
                            f"{source} supplies {share:.0%} of {discipline} rows, "
                            f"exceeding the {max_source_share_per_discipline:.0%} cap"
                        ],
                    }
                )
    issues.extend(source_share_issues)
    if expected_per_discipline is not None:
        for discipline in DISCIPLINES:
            actual = by_discipline[discipline]
            if actual != expected_per_discipline:
                issues.append(
                    {
                        "scope": discipline,
                        "issues": [
                            f"expected {expected_per_discipline} total rows, got {actual}"
                        ],
                    }
                )
    if expected_total is not None and len(rows) != expected_total:
        issues.append(
            {"scope": "total", "issues": [f"expected {expected_total} rows, got {len(rows)}"]}
        )
    status_counts = Counter(
        row.get("curation", {}).get("status", "missing") for row in rows
    )
    unverified_licenses = [
        row.get("id")
        for row in rows
        if row.get("source", {}).get("license_status") != "verified_redistributable"
    ]
    missing_release_assets = []
    for row in rows:
        # A release-ready synthetic pair must be reproducible from the checked-in
        # local assets.  Draft rows intentionally may point only to upstream
        # records, so do not require downloaded files for them.
        if row.get("curation", {}).get("status") != RELEASE_STATUS:
            continue
        source = row.get("source", {})
        declared_assets = [
            source.get("local_before_path"),
            source.get("local_gt_path"),
        ]
        if any(declared_assets):
            if not all(isinstance(asset, str) and asset for asset in declared_assets):
                missing_release_assets.append(
                    {"id": row.get("id"), "reason": "incomplete local asset pair"}
                )
                continue
            absent = [asset for asset in declared_assets if not (ROOT / asset).is_file()]
            if absent:
                missing_release_assets.append(
                    {"id": row.get("id"), "reason": "missing local asset", "paths": absent}
                )
    release_issues: list[dict[str, Any]] = []
    token_sets = []
    for row in rows:
        text = (
            row.get("source", {}).get("original_annotation")
            or row.get("source", {}).get("original_instruction")
            or row.get("prompt_text", "")
        )
        token_sets.append(set(re.findall(r"[a-z0-9]+", str(text).lower())))
    near_duplicates = []
    for left in range(len(rows)):
        for right in range(left + 1, len(rows)):
            union = token_sets[left] | token_sets[right]
            score = len(token_sets[left] & token_sets[right]) / len(union) if union else 0
            if score >= 0.72:
                near_duplicates.append(
                    {
                        "left": rows[left].get("id"),
                        "right": rows[right].get("id"),
                        "jaccard": round(score, 3),
                    }
                )
    if status_counts != Counter({RELEASE_STATUS: len(rows)}):
        release_issues.append(
            {
                "scope": "curation",
                "issues": [
                    f"all rows must have curation.status={RELEASE_STATUS}; "
                    f"observed {dict(status_counts)}"
                ],
            }
        )
    if unverified_licenses:
        release_issues.append(
            {
                "scope": "licensing",
                "issues": [
                    f"{len(unverified_licenses)} rows have no verified redistribution license"
                ],
            }
        )
    if missing_release_assets:
        release_issues.append(
            {
                "scope": "release_assets",
                "issues": [
                    f"{len(missing_release_assets)} release-ready rows lack a complete local source/ground-truth pair"
                ],
                "rows": missing_release_assets,
            }
        )
    if near_duplicates:
        release_issues.append(
            {
                "scope": "near_duplicates",
                "issues": [f"{len(near_duplicates)} high-similarity pairs require review"],
                "pairs": near_duplicates,
            }
        )
    archetype_counts = Counter(
        row.get("curation", {}).get("pedagogical_archetype", "legacy_reviewed")
        for row in rows
    )
    narrative_template_counts = Counter(
        tuple(row.get("expected_narrative_order", [])) for row in rows
    )
    candidate_gate_issues = []
    active_archetypes = [name for name in archetype_counts if name != "legacy_reviewed"]
    if len(active_archetypes) < 8:
        candidate_gate_issues.append("fewer than 8 pedagogical archetypes")
    largest_archetype_share = (
        max(archetype_counts.values(), default=0) / len(rows) if rows else 0.0
    )
    if largest_archetype_share > 0.35:
        candidate_gate_issues.append("one pedagogical archetype exceeds 35% of cases")
    largest_plan_count = max(narrative_template_counts.values(), default=0)
    if largest_plan_count > 5:
        candidate_gate_issues.append("one exact narrative plan occurs more than 5 times")
    if near_duplicates:
        candidate_gate_issues.append("source-text near duplicates remain")
    return {
        "valid": not issues,
        "release_ready": not issues and not release_issues,
        "row_count": len(rows),
        "by_source": dict(sorted(by_source.items())),
        "by_discipline": dict(sorted(by_discipline.items())),
        "by_source_discipline": {
            f"{source}/{discipline}": count
            for (source, discipline), count in sorted(by_source_discipline.items())
        },
        "issues": issues,
        "release_issues": release_issues,
        "curation_status": dict(sorted(status_counts.items())),
        "source_balance": {
            "max_source_share_per_discipline": max_source_share_per_discipline,
            "violations": source_share_issues,
        },
        "diversity": {
            "pedagogical_archetypes": dict(sorted(archetype_counts.items())),
            "unique_narrative_plans": len(narrative_template_counts),
            "largest_exact_narrative_plan_count": largest_plan_count,
            "largest_pedagogical_archetype_share": round(largest_archetype_share, 4),
            "source_text_near_duplicate_pairs_at_0_72": len(near_duplicates),
        },
        "paper_candidate_gate": {
            "automated_pass": not candidate_gate_issues,
            "issues": candidate_gate_issues,
            "manual_subject_review_required": True,
            "paired_visual_review_required": True,
            "license_review_required": True,
        },
    }


def build(args: argparse.Namespace) -> None:
    grade_rows = json.loads(Path(args.grade).read_text(encoding="utf-8"))
    dg_rows = jsonl_rows(Path(args.disciplinegen))
    for extra_path in args.disciplinegen_extra:
        dg_rows.extend(jsonl_rows(Path(extra_path)))
    selection_quota = args.target_per_discipline or args.per_source_discipline
    selected_grade = stratified_grade(grade_rows, selection_quota, args.seed)
    selected_dg = stratified_dg(dg_rows, selection_quota, args.seed)
    prompts = [grade_to_prompt(row) for row in selected_grade]
    prompts.extend(dg_to_prompt(row) for row in selected_dg)
    replacement_paths = [Path(path) for path in args.replacements]
    replacement_rows = [
        row
        for path in replacement_paths
        if path.exists()
        for row in jsonl_rows(path)
    ]
    replacement_disciplines = {row.get("discipline") for row in replacement_rows}
    if replacement_rows and args.target_per_discipline is None:
        prompts = [
            row
            for row in prompts
            if not (
                row.get("source", {}).get("dataset") == "DisciplineGen-1M"
                and row.get("discipline") in replacement_disciplines
            )
        ]
    prompts.extend(replacement_rows)
    # The 300-case build fixes the discipline quota, not an artificial 50/50
    # source quota. Prefer up to half DisciplineGen, then fill sparse disciplines
    # from GRADE. This retains both papers without duplicating scarce source rows.
    if args.target_per_discipline is not None:
        all_prompts = list({row["id"]: row for row in prompts}.values())
        balanced = []
        balanced_tokens: list[set[str]] = []

        def add_if_distinct(row: dict[str, Any]) -> bool:
            source = row.get("source", {})
            text = (
                source.get("original_annotation")
                or source.get("original_instruction")
                or row.get("prompt_text", "")
            )
            tokens = set(re.findall(r"[a-z0-9]+", str(text).lower()))
            if any(
                len(tokens & prior) / len(tokens | prior) >= 0.72
                for prior in balanced_tokens
                if tokens | prior
            ):
                return False
            balanced.append(row)
            balanced_tokens.append(tokens)
            return True

        for discipline in DISCIPLINES:
            dg_pool = [
                row for row in prompts
                if row["discipline"] == discipline
                and row["source"]["dataset"] == "DisciplineGen-1M"
            ]
            grade_pool = [
                row for row in prompts
                if row["discipline"] == discipline
                and row["source"]["dataset"] == "GRADE"
            ]
            dg_count = min(len(dg_pool), args.target_per_discipline // 2)
            for row in dg_pool[:dg_count]:
                add_if_distinct(row)
            need = args.target_per_discipline - sum(
                row["discipline"] == discipline for row in balanced
            )
            for row in grade_pool:
                if need <= 0:
                    break
                if add_if_distinct(row):
                    need -= 1
        # Do not pad a weak discipline with template variants. Redistribute a
        # small shortage across content-rich disciplines while keeping the
        # benchmark nearly balanced (at most two above the nominal quota).
        wanted_total = args.target_per_discipline * len(DISCIPLINES)
        selected_ids = {row["id"] for row in balanced}
        for row in all_prompts:
            if len(balanced) >= wanted_total:
                break
            discipline_count = sum(
                item["discipline"] == row["discipline"] for item in balanced
            )
            if row["id"] not in selected_ids and discipline_count < args.target_per_discipline + 2:
                if add_if_distinct(row):
                    selected_ids.add(row["id"])
        prompts = balanced
    prompts.sort(key=lambda row: (row["discipline"], row["source"]["dataset"], row["id"]))

    write_jsonl(Path(args.out), prompts)
    report = validate_rows(
        prompts,
        expected_per_source_discipline=(
            args.per_source_discipline if args.target_per_discipline is None else None
        ),
        expected_per_discipline=None,
        expected_total=(
            args.target_per_discipline * len(DISCIPLINES)
            if args.target_per_discipline is not None else None
        ),
        max_source_share_per_discipline=args.max_source_share_per_discipline,
    )
    report["inputs"] = {
        "grade_metadata": str(Path(args.grade)),
        "grade_available": len(grade_rows),
        "disciplinegen_metadata": str(Path(args.disciplinegen)),
        "disciplinegen_sampled_available": len(dg_rows),
        "disciplinegen_extra": list(args.disciplinegen_extra),
        "seed": args.seed,
        "per_source_discipline": args.per_source_discipline,
        "target_per_discipline": args.target_per_discipline,
        "content_review_exclusions": len(EXCLUDED_IDS),
        "replacement_files": [str(path) for path in replacement_paths],
        "replacement_rows": len(replacement_rows),
    }
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"[build] wrote {len(prompts)} prompts to {args.out}")
    schema_state = "PASS" if report["valid"] else "FAIL"
    release_state = "PASS" if report["release_ready"] else "BLOCKED"
    print(
        f"[build] schema validation {schema_state}; release {release_state}: "
        f"{args.report}"
    )
    if not report["valid"]:
        raise SystemExit(2)


def fetch_grade_assets(args: argparse.Namespace) -> None:
    rows = jsonl_rows(Path(args.prompts))
    selected = [
        row for row in rows if row.get("source", {}).get("dataset") == "GRADE"
    ]
    out_dir = Path(args.out)
    session = requests.Session()
    downloaded = 0
    skipped = 0
    failures = []
    for index, row in enumerate(selected, 1):
        source = row["source"]
        for role, source_key in (("before", "source_image_path"), ("gt", "target_image_path")):
            remote_path = source.get(source_key)
            if not remote_path:
                failures.append({"id": row["id"], "role": role, "error": "missing path"})
                continue
            suffix = Path(remote_path).suffix or ".png"
            local_path = out_dir / role / f"{row['id']}{suffix}"
            local_path.parent.mkdir(parents=True, exist_ok=True)
            if local_path.exists() and local_path.stat().st_size > 0 and not args.overwrite:
                skipped += 1
                continue
            url = (
                "https://huggingface.co/datasets/VisionXLab/GRADE/resolve/main/"
                + remote_path
            )
            try:
                response = session.get(url, timeout=90)
                response.raise_for_status()
                local_path.write_bytes(response.content)
                downloaded += 1
            except Exception as exc:
                failures.append(
                    {"id": row["id"], "role": role, "error": f"{type(exc).__name__}: {exc}"}
                )
        print(f"[grade-assets] {index}/{len(selected)} {row['id']}", flush=True)
    session.close()
    manifest = {
        "selected_cases": len(selected),
        "downloaded_files": downloaded,
        "skipped_files": skipped,
        "failures": failures,
        "license_status": "unverified; do not redistribute until clarified",
    }
    manifest_path = out_dir / "manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"[grade-assets] wrote {manifest_path}")
    if failures:
        raise SystemExit(2)


def validate(args: argparse.Namespace) -> None:
    rows = jsonl_rows(Path(args.input))
    report = validate_rows(
        rows,
        expected_per_source_discipline=args.per_source_discipline,
        max_source_share_per_discipline=args.max_source_share_per_discipline,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["valid"] or (args.release and not report["release_ready"]):
        raise SystemExit(2)


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="command", required=True)

    inspect = sub.add_parser("inspect-disciplinegen")
    inspect.add_argument("--files", nargs="*")
    inspect.add_argument(
        "--out",
        default=str(
            ROOT / "data" / "sources" / "disciplinegen" / "metadata" / "schemas.json"
        ),
    )
    inspect.set_defaults(func=inspect_disciplinegen)

    sample = sub.add_parser("sample-disciplinegen")
    sample.add_argument("--files", nargs="*")
    sample.add_argument("--per-file", type=int, default=80)
    sample.add_argument("--seed", type=int, default=20260803)
    sample.add_argument("--out", default=str(DEFAULT_DG_CACHE))
    sample.set_defaults(func=sample_disciplinegen)

    build_cmd = sub.add_parser("build")
    build_cmd.add_argument("--grade", default=str(DEFAULT_GRADE))
    build_cmd.add_argument("--disciplinegen", default=str(DEFAULT_DG_CACHE))
    build_cmd.add_argument("--disciplinegen-extra", nargs="*", default=[])
    build_cmd.add_argument("--per-source-discipline", type=int, default=5)
    build_cmd.add_argument(
        "--target-per-discipline",
        type=int,
        help="build a fixed total per discipline; source shortages are backfilled",
    )
    build_cmd.add_argument(
        "--max-source-share-per-discipline",
        type=float,
        default=DEFAULT_MAX_SOURCE_SHARE_PER_DISCIPLINE,
        help=(
            "flag a discipline if one source dataset supplies more than this "
            "fraction of its rows (default: %(default)s)"
        ),
    )
    build_cmd.add_argument("--seed", type=int, default=20260803)
    build_cmd.add_argument("--out", default=str(DEFAULT_OUT))
    build_cmd.add_argument("--report", default=str(DEFAULT_REPORT))
    build_cmd.add_argument(
        "--replacements",
        nargs="+",
        default=[str(path) for path in DEFAULT_REPLACEMENTS],
    )
    build_cmd.set_defaults(func=build)

    validate_cmd = sub.add_parser("validate")
    validate_cmd.add_argument("--input", default=str(DEFAULT_OUT))
    validate_cmd.add_argument("--per-source-discipline", type=int, default=5)
    validate_cmd.add_argument(
        "--max-source-share-per-discipline",
        type=float,
        default=DEFAULT_MAX_SOURCE_SHARE_PER_DISCIPLINE,
        help=(
            "flag a discipline if one source dataset supplies more than this "
            "fraction of its rows (default: %(default)s)"
        ),
    )
    validate_cmd.add_argument(
        "--release",
        action="store_true",
        help="fail unless every record has completed review and verified redistribution terms",
    )
    validate_cmd.set_defaults(func=validate)

    assets = sub.add_parser("fetch-grade-assets")
    assets.add_argument("--prompts", default=str(DEFAULT_OUT))
    assets.add_argument("--out", default=str(DEFAULT_GRADE_ASSETS))
    assets.add_argument("--overwrite", action="store_true")
    assets.set_defaults(func=fetch_grade_assets)
    return ap


if __name__ == "__main__":
    parsed = parser().parse_args()
    parsed.func(parsed)
