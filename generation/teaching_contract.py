"""Cross-discipline teaching-state contracts for short video generation.

Contracts are authored or reviewed before generation. This module checks their
internal consistency and compiles one observable teaching beat into a prompt.
It cannot establish that an arbitrary scientific claim is true; that remains
an expert/data curation responsibility, and the final video needs review.
"""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Callable

from PIL import ImageFont


class ContractError(ValueError):
    pass


class RefinementExhausted(ContractError):
    def __init__(self, message: str, attempts: list[dict]):
        super().__init__(message)
        self.attempts = attempts


def load_contracts(path: str | Path) -> dict[str, dict]:
    contracts: dict[str, dict] = {}
    for number, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            contract = json.loads(line)
            case_id = contract["id"]
        except (ValueError, KeyError, TypeError) as exc:
            raise ContractError(f"{path}:{number}: invalid contract: {exc}") from exc
        if not isinstance(case_id, str) or not case_id:
            raise ContractError(f"{path}:{number}: id must be a nonempty string")
        if case_id in contracts:
            raise ContractError(f"{path}:{number}: duplicate id {case_id}")
        contracts[case_id] = contract
    return contracts


def _nonempty_strings(value: object, name: str) -> list[str]:
    if not isinstance(value, list) or not value or any(
        not isinstance(item, str) or not item.strip() for item in value
    ):
        raise ContractError(f"{name} must be a nonempty list of strings")
    return value


def _validate_layout(layout: object, width: int, height: int) -> None:
    if not isinstance(layout, list) or not layout:
        raise ContractError("layout must contain at least one element")
    boxes: list[tuple[str, str, tuple[float, float, float, float]]] = []
    ids: set[str] = set()
    for element in layout:
        if not isinstance(element, dict):
            raise ContractError("layout elements must be objects")
        name = element.get("id")
        if not isinstance(name, str) or not name or name in ids:
            raise ContractError("layout ids must be unique nonempty strings")
        ids.add(name)
        rect = element.get("rect")
        if not isinstance(rect, list) or len(rect) != 4 or any(
            not isinstance(n, (int, float)) or isinstance(n, bool) for n in rect
        ):
            raise ContractError(f"{name}: rect must be [left, top, right, bottom]")
        left, top, right, bottom = map(float, rect)
        if not (0.025 <= left < right <= 0.975 and 0.025 <= top < bottom <= 0.975):
            raise ContractError(f"{name}: rect is outside safe margins or inverted")
        if element.get("kind") == "text":
            font_px = element.get("font_px")
            if not isinstance(font_px, (int, float)) or font_px < max(20, height * 0.045):
                raise ContractError(f"{name}: text is below minimum readable size")
            if (right - left) * width < font_px or (bottom - top) * height < font_px:
                raise ContractError(f"{name}: text box is smaller than its font")
            if not isinstance(element.get("text"), str) or not element["text"].strip():
                raise ContractError(f"{name}: text element needs exact text")
            font = ImageFont.load_default(size=round(font_px))
            glyph_box = font.getbbox(element["text"])
            if glyph_box[2] - glyph_box[0] > (right - left) * width - 12 or (
                glyph_box[3] - glyph_box[1] > (bottom - top) * height - 8
            ):
                raise ContractError(f"{name}: text exceeds its measured layout box")
        phase = element.get("phase", "all")
        if not isinstance(phase, str) or not phase:
            raise ContractError(f"{name}: phase must be a nonempty string")
        boxes.append((name, phase, (left, top, right, bottom)))

    for index, (name_a, phase_a, a) in enumerate(boxes):
        for name_b, phase_b, b in boxes[index + 1:]:
            if phase_a != "all" and phase_b != "all" and phase_a != phase_b:
                continue
            if min(a[2], b[2]) > max(a[0], b[0]) and min(a[3], b[3]) > max(a[1], b[1]):
                raise ContractError(f"layout overlap: {name_a} and {name_b}")


def _operand(value: object, beat: dict) -> object:
    if not isinstance(value, dict) or len(value) != 1:
        raise ContractError("check operands must be {path: ...} or {value: ...}")
    if "value" in value:
        return value["value"]
    path = value.get("path")
    if not isinstance(path, str) or not path:
        raise ContractError("check path must be a nonempty string")
    parts = path.split(".")
    if parts[0] not in ("pre", "post") or len(parts) < 2:
        raise ContractError(f"check path must start with pre. or post.: {path}")
    current: object = beat["pre_state"] if parts[0] == "pre" else beat["post_state"]
    try:
        for part in parts[1:]:
            current = current[int(part)] if isinstance(current, list) else current[part]
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise ContractError(f"check path does not exist: {path}") from exc
    return current


def _validate_checks(checks: object, beat: dict) -> None:
    if not isinstance(checks, list) or not checks:
        raise ContractError("checks must be a nonempty list of executable assertions")
    for index, check in enumerate(checks):
        if not isinstance(check, dict):
            raise ContractError(f"check {index}: expected object")
        kind = check.get("type")
        if kind in ("equals", "less_than", "greater_than"):
            left = _operand(check.get("left"), beat)
            right = _operand(check.get("right"), beat)
            if kind == "equals":
                passed = left == right
            else:
                if not isinstance(left, (int, float)) or not isinstance(right, (int, float)):
                    raise ContractError(f"check {index}: ordered comparison requires numbers")
                passed = left < right if kind == "less_than" else left > right
        elif kind == "all_equal":
            values = _operand(check.get("values"), beat)
            if not isinstance(values, list) or not values:
                raise ContractError(f"check {index}: all_equal requires a nonempty list")
            passed = all(value == values[0] for value in values)
        elif kind == "sum_equal":
            left = _operand(check.get("left"), beat)
            right = _operand(check.get("right"), beat)
            if not all(isinstance(values, list) and values and all(
                isinstance(value, (int, float)) and not isinstance(value, bool) for value in values
            ) for values in (left, right)):
                raise ContractError(f"check {index}: sum_equal requires numeric lists")
            passed = sum(left) == sum(right)
        else:
            raise ContractError(f"check {index}: unsupported type {kind!r}")
        if not passed:
            raise ContractError(f"check {index}: {kind} failed")


def validate_contract(contract: dict, case: dict, width: int, height: int,
                      output_duration_s: float) -> None:
    """Validate one atomic beat and layout before loading an expensive model."""
    case_id = case.get("id")
    if contract.get("id") != case_id:
        raise ContractError(f"{case_id}: contract id mismatch")
    target = contract.get("target_duration_s")
    if not isinstance(target, (int, float)) or not 0.5 <= target <= 30:
        raise ContractError(f"{case_id}: target_duration_s must be 0.5..30")
    if abs(float(target) - output_duration_s) > max(0.2, output_duration_s * 0.1):
        raise ContractError(
            f"{case_id}: target {target}s differs from requested video {output_duration_s:.2f}s"
        )
    if not isinstance(contract.get("learning_objective"), str) or not contract["learning_objective"].strip():
        raise ContractError(f"{case_id}: learning_objective is required")
    beat = contract.get("beat")
    if not isinstance(beat, dict):
        raise ContractError(f"{case_id}: exactly one beat object is required")
    if not isinstance(beat.get("claim"), str) or not beat["claim"].strip():
        raise ContractError(f"{case_id}: beat.claim is required")
    pre, post = beat.get("pre_state"), beat.get("post_state")
    if not isinstance(pre, dict) or not isinstance(post, dict) or not pre:
        raise ContractError(f"{case_id}: pre_state and post_state must be nonempty objects")
    if pre.keys() != post.keys() or any(not isinstance(key, str) for key in pre):
        raise ContractError(f"{case_id}: state keys must persist across the beat")
    changes = _nonempty_strings(beat.get("changes"), "beat.changes")
    if len(changes) != len(set(changes)) or set(changes) - pre.keys():
        raise ContractError(f"{case_id}: beat.changes names missing or duplicate state keys")
    observed_changes = {key for key in pre if pre[key] != post[key]}
    if set(changes) != observed_changes:
        raise ContractError(
            f"{case_id}: declared changes {sorted(changes)} differ from actual {sorted(observed_changes)}"
        )
    _nonempty_strings(beat.get("visible_evidence"), "beat.visible_evidence")
    invariants = contract.get("invariants", {})
    if not isinstance(invariants, dict) or any(
        key not in pre or pre[key] != value or post[key] != value
        for key, value in invariants.items()
    ):
        raise ContractError(f"{case_id}: invariant changed or is absent from state")
    _validate_checks(contract.get("checks"), beat)
    _validate_layout(contract.get("layout"), width, height)
    for element in contract["layout"]:
        if "text_path" in element:
            value = _operand(element["text_path"], beat)
            expected = element.get("prefix", "") + str(value)
            if element.get("text") != expected:
                raise ContractError(f"{case_id}: {element['id']} text differs from bound knowledge state")


def compile_prompt(contract: dict, case: dict | None = None) -> str:
    """Use the selected beat, rather than a possibly over-scoped legacy prompt."""
    beat = contract["beat"]
    layout = [
        {"id": item["id"], "kind": item.get("kind", "diagram"),
         "rect": item["rect"], "text": item.get("text"), "phase": item.get("phase", "all")}
        for item in contract["layout"]
    ]
    placements = "; ".join(
        f"{item['id']}: {item.get('text', item.get('kind', 'diagram'))} "
        f"within {item['rect']}" for item in layout
    )
    audience = (case or {}).get("pedagogical_target_audience", "the intended learner")
    return (
        f"Create a {contract['target_duration_s']}-second instructional video showing ONE "
        f"observable step for {audience}. Learning objective: {contract['learning_objective']}. "
        f"Step: {beat['claim']}. Initial state: {json.dumps(beat['pre_state'], ensure_ascii=False)}. "
        f"Final state: {json.dumps(beat['post_state'], ensure_ascii=False)}. "
        f"Required visible evidence: {json.dumps(beat['visible_evidence'], ensure_ascii=False)}. "
        f"Facts that must remain fixed: {json.dumps(contract.get('invariants', {}), ensure_ascii=False)}. "
        f"Screen layout reservations (normalized coordinates): {placements}. "
        "Keep labels readable and stable. Show the final state clearly. Do not add other steps."
    )


def prepare_cases(cases: list[dict], contracts: dict[str, dict], width: int,
                  height: int, num_frames: int, fps: int) -> list[dict]:
    """Return copied cases with validated prompts; fail all cases before generation."""
    if width <= 0 or height <= 0 or num_frames <= 0 or fps <= 0:
        raise ContractError("positive width, height, frame count and fps are required")
    duration = num_frames / fps
    prepared = []
    for case in cases:
        case_id = case["id"]
        if case_id not in contracts:
            raise ContractError(f"{case_id}: missing teaching contract")
        contract = contracts[case_id]
        validate_contract(contract, case, width, height, duration)
        if any(element.get("draw") for element in contract["layout"]):
            # Resolve every state-bound primitive before loading the video model.
            from generation.contract_frame import render_first_frame
            render_first_frame(contract, width, height)
            render_first_frame(contract, width, height, phase="result")
        record = dict(case)
        record["video_prompt"] = compile_prompt(contract, case)
        record["target_duration_s"] = contract["target_duration_s"]
        record["teaching_contract_sha256"] = hashlib.sha256(
            json.dumps(contract, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest()
        prepared.append(record)
    return prepared


def refine_contract(
    initial: dict, case: dict, width: int, height: int, output_duration_s: float,
    revise: Callable[[dict, str, int], dict], max_rounds: int = 3,
) -> tuple[dict, list[dict]]:
    """Run a bounded, auditable contract-revision loop without changing frozen truth.

    ``revise`` is supplied by a human editor or an agent. It receives a copy of
    the current draft, diagnostic text, and the next round number. Pixel-video
    feedback is a separate loop after generation and is not implied here.
    """
    if max_rounds < 1:
        raise ValueError("max_rounds must be positive")
    current = deepcopy(initial)
    frozen = {
        "learning_objective": deepcopy(initial.get("learning_objective")),
        "claim": deepcopy(initial.get("beat", {}).get("claim")),
        "pre_state": deepcopy(initial.get("beat", {}).get("pre_state")),
        "post_state": deepcopy(initial.get("beat", {}).get("post_state")),
    }
    attempts: list[dict] = []
    for round_number in range(1, max_rounds + 1):
        digest = hashlib.sha256(json.dumps(
            current, ensure_ascii=False, sort_keys=True
        ).encode("utf-8")).hexdigest()
        truth = {
            "learning_objective": current.get("learning_objective"),
            "claim": current.get("beat", {}).get("claim"),
            "pre_state": current.get("beat", {}).get("pre_state"),
            "post_state": current.get("beat", {}).get("post_state"),
        }
        if truth != frozen:
            reason = "revision changed frozen learning objective, claim, or knowledge state"
        else:
            try:
                validate_contract(current, case, width, height, output_duration_s)
            except ContractError as exc:
                reason = str(exc)
            else:
                attempts.append({"round": round_number, "sha256": digest, "status": "accepted"})
                return current, attempts
        attempts.append({"round": round_number, "sha256": digest,
                         "status": "rejected", "reason": reason})
        if reason.startswith("revision changed frozen") or round_number == max_rounds:
            raise RefinementExhausted(reason, attempts)
        candidate = revise(deepcopy(current), reason, round_number + 1)
        if not isinstance(candidate, dict):
            raise RefinementExhausted("revision must return a contract object", attempts)
        current = candidate
    raise AssertionError("unreachable")
