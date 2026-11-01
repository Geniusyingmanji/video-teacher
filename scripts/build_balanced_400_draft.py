"""Rebalance the 400 candidates with source-linked, review-required adaptations.

This creates a research draft, never a release set. It preserves the original pool.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from copy import deepcopy
import json
from pathlib import Path
try:
    from scripts.balanced_rewrites import REWRITES, MEDICINE_REFERENCES
    from scripts.scope_replacements import SCOPE_REPLACEMENTS
except ModuleNotFoundError:  # direct `python scripts/build_balanced_400_draft.py`
    from balanced_rewrites import REWRITES, MEDICINE_REFERENCES
    from scope_replacements import SCOPE_REPLACEMENTS

ROOT = Path(__file__).resolve().parent.parent
INPUT = ROOT / "data/prompts/candidate_400_agent_ready.jsonl"
OUTPUT = ROOT / "data/prompts/candidate_400_balanced_draft.jsonl"
REPORT = ROOT / "data/curated/candidate_400_balanced_draft_report.json"

SPORTS_CONCEPTS = [
    ("a lower glycemic-index food usually produces a lower, slower post-meal glucose rise than the high-GI example", "two labeled response curves", "the low-GI curve has a lower peak than the high-GI curve"),
    ("a Go stone's liberty is an empty orthogonally adjacent intersection", "one stone and its neighboring intersections", "diagonal intersections are not counted as liberties"),
    ("the central-cannon opening develops a cannon onto the central file", "the starting Xiangqi cannon and center file", "the cannon ends on the center file"),
    ("the Polish Opening begins with White's b-pawn advancing to b4", "an initial chessboard with the b-pawn highlighted", "the white pawn is on b4"),
    ("opening development brings a minor piece off its starting square while keeping the king safe", "a chessboard with one knight highlighted", "one knight moves to a legal developing square"),
    ("a Xiangqi rook travels along an unobstructed rank or file", "the red rook and open lines", "highlighted destinations lie on its rank or file without jumping a piece"),
    ("a Xiangqi pawn advances one point forward before crossing the river", "the seventh-file pawn and forward point", "the pawn advances exactly one point forward"),
    ("the Queen's Gambit begins 1.d4 d5 2.c4", "a chessboard showing the d-pawns", "White's c-pawn reaches c4 after the two d-pawn moves"),
    ("a chess knight moves two squares in one direction and one perpendicular square", "a knight and an L-shaped path", "the endpoint is a legal knight destination"),
    ("a legal chess move must not leave the moving side's king in check", "the king and an attacked line", "an illegal king-exposing move is marked and rejected"),
    ("a Go group is captured when its last liberty is filled", "a group with one remaining liberty", "the group is removed only after the final liberty is occupied"),
    ("Go liberties are shared by connected stones of the same color", "two orthogonally connected stones", "their surrounding empty intersections are counted once each"),
    ("a bodyweight squat primarily recruits the quadriceps and gluteal muscles", "a squat silhouette with thigh and hip regions", "quadriceps and glutes are highlighted without labeling arms as primary movers"),
    ("in a one-on-one basketball wing drive, the attacker moves toward the basket from the wing", "wing, defender, and basket positions", "the movement arrow points from wing toward basket"),
]

PREFERRED_ANCHORS = {
    ("mathematics", "explanation"): ["math_prob_01", "math_prob_02", "grade_math_math_43",
                                    "grade_math_math_56", "grade_math_math_90", "grade_math_math_92", "grade_math_math_97"],
    ("history", "explanation"): ["grade_his_task_18", "grade_his_task_19", "grade_his_task_22"],
}

SUBJECT_CONCEPTS = {
    "mathematics": [
        ("an equation stays equivalent when the same operation is applied to both sides", "a balance with equal expressions", "both sides change together and remain equal"),
        ("the derivative of x cubed plus 2x is 3x squared plus 2", "the polynomial and its derivative", "the power rule is applied term by term"),
        ("translation moves every point by the same vector", "a shape, vector arrow, and translated copy", "corresponding vertices have equal displacement arrows"),
        ("a triangle median joins one vertex to the midpoint of the opposite side", "a triangle with a marked side midpoint", "the segment starts at the opposite vertex and ends at the midpoint"),
        ("central symmetry maps each point through one fixed center", "a point, symmetry center, and image point", "the center bisects the segment joining each pair"),
        ("reflection across x equals zero maps (x,y) to (-x,y)", "a coordinate grid and mirrored point pair", "the two points have opposite x coordinates and equal y coordinates"),
        ("a zero of a function is an x value where its graph meets the x axis", "a function graph and x axis", "each marked zero lies on the x axis"),
    ],
    "music": [
        ("tempo measured in beats per minute increases when beats occur closer together", "a beat timeline with two tempi", "the faster pattern has shorter beat intervals"),
        ("lower beats per minute means a longer interval between beats", "two labeled beat timelines", "the slower pattern has wider beat spacing"),
        ("a rest indicates silence for the part that carries it", "a bass staff with a rest", "the bass note is silent during the marked rest"),
        ("a forte marking instructs a performer to play loudly", "a score with an f dynamic marking", "the f symbol is attached to the intended passage"),
        ("a 4/4 time signature groups four quarter-note beats in each measure", "a staff with a 4/4 signature and bar lines", "one measure contains four quarter-note beats"),
        ("a dotted half note lasts three quarter-note beats", "a dotted half note beside three quarter-note pulses", "the note spans all three pulses"),
        ("a clef determines which pitches staff lines represent", "the same staff under treble and bass clefs", "the reference line labels change with the clef"),
        ("rhythm describes the timing pattern of notes and rests", "a short note-and-rest pattern with beat markers", "the beat spacing matches the shown durations"),
    ],
    "history": [
        ("ancient Olympic Games were held at Olympia, whereas the modern Games rotate among host cities", "an Olympia map marker and modern host-city markers", "the ancient site and modern host locations are distinct"),
        ("Maya writing combined logographic and syllabic signs", "two labeled examples of sign functions", "one sign represents a word and another a syllable"),
        ("planned streets and drainage are features documented at some Indus cities", "a simple city-plan diagram", "street grid and drainage channel are both labeled"),
    ],
}

SCOPE_REWRITES = {
    "cand_hs_art_05": ("Show a hallway with one horizon point. Animate just two floor edges converging to that point; hold the single vanishing point.", "two floor edges converge at one point on the horizon"),
    "cand_hs_art_01": ("On two labeled chord cards G–B–D and C–E–G, reveal V then I in C major and hold the V–I cadence.", "G–B–D is V and C–E–G is I"),
    "cand_hs_art_02": ("Show one painting detail with visibly broken brushstrokes. Highlight that visual clue and reveal 'Impressionist brushwork'; do not claim an artist identity.", "the highlighted clue is the broken brushwork"),
    "cand_hs_art_03": ("On a C-major keyboard octave, reveal the notes C D E F G A B C, then mark only the two half-step pairs E–F and B–C.", "only E–F and B–C are marked as half steps"),
    "cand_hs_art_04": ("Show scale degree 2 above a G-major chord. Move the melody to scale degree 1 above C major and hold the two-chord V–I ending.", "the melody resolves 2 to 1 while harmony moves V to I"),
    "cand_hs_art_06": ("Show three voice lanes. Repeat one short subject in the lanes at staggered entrances and label the pattern 'fugue exposition'.", "the same subject enters separate voices successively"),
    "cand_hs_civ_04": ("Show a bill moving from Congress to the U.S. president. Reveal one veto arrow returning the bill toward Congress; hold that branch relationship.", "the veto action is assigned to the president"),
    "cand_hs_civ_01": ("Show a public park and a speech icon. Label the park a traditional public forum; hold that one classification without deciding a hypothetical restriction.", "the public park is classified as a traditional public forum"),
    "cand_hs_civ_02": ("On an Electoral College tally at 254, reveal the majority line at 270 and animate the remaining 16 votes filling the gap.", "270 minus 254 equals 16"),
    "cand_hs_civ_03": ("Compare two policy cards on the same cost and access axes. Reveal one criterion at a time; stop before ranking because no weights are given.", "both policies are judged by the same two named criteria"),
    "cand_hs_civ_05": ("On two theory cards, attach 'power and threat balancing' to Realism and 'institutions and interdependence' to Liberalism.", "the two theory labels are attached to their corresponding mechanisms"),
    "cand_hs_lang_05": ("Place the printed word TREE beside a tree drawing and a concept bubble. Label the printed word 'signifier' and the concept bubble 'signified'.", "the physical tree drawing is not labeled signifier"),
    "cand_hs_lang_01": ("Show one speaker-credential cue and one emotion cue. Label the credibility cue 'ethos' and the emotional cue 'pathos'.", "ethos maps to credibility and pathos to emotion"),
    "cand_hs_lang_02": ("Display 'The bell rang, the class left.' Split it into two complete clauses and replace the comma with a period.", "the corrected text is 'The bell rang. The class left.'"),
    "cand_hs_lang_03": ("Show one pre-scanned five-foot line. Reveal five weak–strong stress groups one at a time and hold the label 'iambic pentameter'.", "exactly five weak–strong groups are shown"),
    "cand_hs_lang_04": ("Show one third-person sentence followed by a character-colored evaluative phrase without quotation marks. Highlight the viewpoint shift as free indirect discourse.", "the grammar remains third person and no direct quotation is added"),
    "cand_hs_lang_06": ("Replace the topic label 'Hamlet's delay' with the arguable claim 'Hamlet's soliloquies make delay a form of self-scrutiny'. Hold both before and after cards.", "the revised card states a disputable claim and names soliloquies"),
}


def adapt(source: dict, task: str, index: int) -> dict:
    row = deepcopy(source)
    concept = next((c for c in source["expected_concepts"] if len(c) > 12), source["expected_concepts"][0])
    visual = source["expected_visual_elements"][0]
    evidence = source["discipline_specific_rubric"][0]
    row["id"] = f"adapt_{source['discipline']}_{'concept' if task == 'explanation' else 'problem'}_{index:02d}"
    row["task_type"] = task
    row["video_goal"] = "knowledge_point" if task == "explanation" else "solve_problem"
    if task == "explanation":
        row["prompt_text"] = (f"Create a five-second knowledge-point video about {concept}. "
                              f"Begin with {visual}; animate the relationship one step at a time; "
                              f"end on a frame demonstrating: {evidence}. Do not display the source task's answer image.")
        row["expected_narrative_order"] = [f"introduce {visual}", f"show how {concept} works", f"hold evidence: {evidence}"]
    else:
        row["prompt_text"] = (f"Create a five-second worked-problem video. Show {visual} and ask which "
                              f"principle or result it demonstrates. Reveal {concept} after the visual cue, "
                              f"then verify the answer with this observable condition: {evidence}.")
        row["expected_narrative_order"] = [f"pose the visual question using {visual}",
                                            f"highlight the deciding cue", f"reveal {concept}",
                                            f"verify: {evidence}"]
    row["expected_concepts"] = [concept]
    row["discipline_specific_rubric"] = [evidence, f"the video explicitly teaches {concept}"]
    row["curation"] = {"status": "draft_needs_subject_review", "conversion": "task_reframing_v1",
                       "source_anchor_id": source["id"], "source_fact_review": "required",
                       "visual_review": "required", "near_duplicate_review": "required"}
    # A source image may be used as an optional opening frame, never as a required answer image.
    row.pop("first_frame", None)
    if task == "explanation" and source["discipline"] in {"sports", "mathematics", "music", "history"}:
        table = SPORTS_CONCEPTS if source["discipline"] == "sports" else SUBJECT_CONCEPTS[source["discipline"]]
        concept, visual, evidence = table[index - 1]
        row["prompt_text"] = (f"Create a five-second knowledge-point video explaining that {concept}. "
                              f"Show {visual}, reveal the key relationship, then hold the final state. "
                              f"Visible check: {evidence}.")
        row["expected_concepts"] = [concept]
        row["expected_visual_elements"] = [visual]
        row["expected_narrative_order"] = [f"show {visual}", "reveal the rule", f"hold: {evidence}"]
        row["discipline_specific_rubric"] = [evidence, concept]
        row["curation"]["conversion"] = "subject_specific_rewrite_v1"
    rewrite_table = REWRITES.get(source["discipline"], {}).get("concept" if task == "explanation" else "problem")
    if rewrite_table:
        claim_or_question, visual, evidence = rewrite_table[index - 1]
        if task == "explanation":
            row["prompt_text"] = (f"Create a five-second knowledge-point video: {claim_or_question}. "
                                  f"Open on {visual}; reveal one visible relationship; hold the result. "
                                  f"Check: {evidence}.")
            row["expected_narrative_order"] = [f"show {visual}", "animate the relationship", f"hold {evidence}"]
        else:
            row["prompt_text"] = (f"Create a five-second worked-problem video. Ask: {claim_or_question} "
                                  f"Open on {visual}; pause on the choice or blank; reveal and verify the answer. "
                                  f"Correct result: {evidence}.")
            row["expected_narrative_order"] = [f"pose: {claim_or_question}", f"show {visual}", f"reveal {evidence}"]
        row["expected_concepts"] = [claim_or_question if task == "explanation" else evidence]
        row["expected_visual_elements"] = [visual]
        row["discipline_specific_rubric"] = [evidence, "the visual and narration do not contradict the stated result"]
        row["curation"]["conversion"] = "subject_specific_rewrite_v1"
        # The reworked opening scene can differ from its source image. Use T2V
        # until a matching opening frame is created and checked for this prompt.
        row.pop("first_frame_path", None)
        row["first_frame_policy"] = "none"
        row["curation"]["first_frame_alignment"] = "source_image_detached_after_rewrite"
        if source["discipline"] == "medicine":
            row["curation"]["fact_reference_url"] = MEDICINE_REFERENCES["concept" if task == "explanation" else "problem"][index - 1]
    order = row["expected_narrative_order"]
    ranges = ([1, 3], [3, 6], [6, 8]) if len(order) == 3 else ([1, 2], [2, 4], [4, 6], [6, 8])
    row["narrative_beats"] = [{"beat": beat, "expected_frame_range": frame_range}
                              for beat, frame_range in zip(order, ranges)]
    row["target_duration_s"] = 5
    return row


def build() -> dict:
    rows = [json.loads(line) for line in INPUT.read_text(encoding="utf-8").splitlines() if line.strip()]
    groups = defaultdict(list)
    for row in rows:
        groups[(row["discipline"], row["task_type"])].append(row)
    disciplines = sorted({r["discipline"] for r in rows})
    # 14 x 28 = 392; allocate the remaining eight to image-rich disciplines.
    extras = sorted(disciplines, key=lambda d: (-sum(r["first_frame_policy"] == "available_optional"
                                                     for r in rows if r["discipline"] == d), d))[:8]
    target = {(d, t): 14 for d in disciplines for t in ("explanation", "problem_solving")}
    for d in extras:
        t = max(("explanation", "problem_solving"), key=lambda kind: len(groups[(d, kind)]))
        target[(d, t)] += 1
    selected, added, retired = [], [], []
    for d in disciplines:
        for task in ("explanation", "problem_solving"):
            existing = groups[(d, task)]
            quota = target[(d, task)]
            if len(existing) >= quota:
                # Keep every image-backed item before dropping image-free surplus.
                ranked = sorted(existing, key=lambda r: (r["first_frame_policy"] != "available_optional",
                                                        r.get("curation", {}).get("status") != "reviewed_release_ready", r["id"]))
                selected.extend(ranked[:quota])
                retired.extend(r["id"] for r in ranked[quota:])
                continue
            selected.extend(existing)
            need = quota - len(existing)
            opposite = "problem_solving" if task == "explanation" else "explanation"
            anchors = [r for r in groups[(d, opposite)] if r.get("expected_concepts")
                       and r.get("expected_visual_elements") and r.get("discipline_specific_rubric")]
            if not anchors:
                raise ValueError(f"No source anchors for {d}/{task}")
            anchors.sort(key=lambda r: (r["first_frame_policy"] != "available_optional", r["id"]))
            preferred = PREFERRED_ANCHORS.get((d, task))
            if preferred:
                by_id = {r["id"]: r for r in anchors}
                anchors = [by_id[item_id] for item_id in preferred]
            for i in range(need):
                row = adapt(anchors[i % len(anchors)], task, i + 1)
                flags = []
                if "�" in row["prompt_text"] or "��" in row["prompt_text"]:
                    flags.append("encoding_corruption")
                if "ground truth" in row["prompt_text"].lower():
                    flags.append("generic_ground_truth_wording")
                if len(row["expected_concepts"][0]) < 12:
                    flags.append("underspecified_concept")
                row["curation"]["review_flags"] = flags
                selected.append(row)
                added.append({"id": row["id"], "anchor": anchors[i % len(anchors)]["id"]})
    if len(selected) != 400 or len({r["id"] for r in selected}) != 400:
        raise ValueError("Balanced set must have 400 unique IDs")
    selected.sort(key=lambda r: (r["discipline"], r["task_type"], r["id"]))
    for row in selected:
        if row["id"] in SCOPE_REWRITES:
            prompt, evidence = SCOPE_REWRITES[row["id"]]
            row["prompt_text"] = "Create a five-second teaching video. " + prompt
            row["expected_narrative_order"] = ["show the given visual", "reveal one change", "hold the checkable result"]
            row["narrative_beats"] = [{"beat": b, "expected_frame_range": fr} for b, fr in
                                      zip(row["expected_narrative_order"], ([1, 3], [3, 6], [6, 8]))]
            row["discipline_specific_rubric"] = [evidence]
            row["curation"] = {**row.get("curation", {}), "scope_rewrite": "one_checkable_beat_v1"}
        if row["id"] in {"med_prob_01", "med_prob_02"}:
            row["difficulty"] = "low"
            row["curation"] = {**row.get("curation", {}), "difficulty_review": "one_step_calculation"}
        if row["id"] in {"grade_biology_task_10", "grade_biology_task_22", "grade_biology_task_24"}:
            row.get("source", {}).pop("target_image_path", None)
            row["curation"] = {**row.get("curation", {}), "source_target_use": "rejected_do_not_score"}
    broad = defaultdict(list)
    for row in selected:
        if len(row.get("expected_narrative_order", [])) > 4 or \
                "manual_atomic_scope_required" in row.get("curation", {}).get("quality_flags", []):
            broad[(row["discipline"], row["task_type"])].append(row)
    if {key: len(value) for key, value in broad.items()} != \
            {key: len(value) for key, value in SCOPE_REPLACEMENTS.items()}:
        raise ValueError("Scope rewrite inventory changed; review the item mapping")
    scope_replaced = []
    for key, cases in sorted(broad.items()):
        for row, (claim_or_question, visual, evidence) in zip(cases, SCOPE_REPLACEMENTS[key]):
            old_id = row["id"]
            row["id"] = "authored_" + old_id
            task = row["task_type"]
            if task == "explanation":
                row["prompt_text"] = (f"Create a five-second knowledge-point video explaining: {claim_or_question}. "
                                      f"Open on {visual}; reveal one relationship; hold the result. Check: {evidence}.")
                row["expected_concepts"] = [claim_or_question]
                order = [f"show {visual}", "reveal the relationship", f"hold: {evidence}"]
            else:
                row["prompt_text"] = (f"Create a five-second worked-problem video. Ask: {claim_or_question} "
                                      f"Show {visual}; pause before revealing the answer; then hold: {evidence}.")
                row["expected_concepts"] = [evidence]
                order = [f"ask: {claim_or_question}", f"show {visual}", f"reveal: {evidence}"]
            row["expected_visual_elements"] = [visual]
            row["expected_narrative_order"] = order
            row["narrative_beats"] = [{"beat": beat, "expected_frame_range": fr} for beat, fr in
                                      zip(order, ([1, 3], [3, 6], [6, 8]))]
            row["discipline_specific_rubric"] = [evidence]
            row["source"] = {"dataset": "project_authored", "replaces_source_id": old_id,
                             "source_relation": "new task after rejecting overbroad source conversion"}
            row["curation"] = {"status": "draft_needs_subject_review", "conversion": "authored_atomic_replacement_v1",
                               "review_required": "subject_truth_and_visual"}
            row.pop("first_frame_path", None)
            row["first_frame_policy"] = "none"
            row["target_duration_s"] = 5
            scope_replaced.append({"id": row["id"], "replaces": old_id})
    frame_ranges = {
        1: [[1, 8]], 2: [[1, 4], [4, 8]],
        3: [[1, 3], [3, 6], [6, 8]],
        4: [[1, 2], [2, 4], [4, 6], [6, 8]],
    }
    for row in selected:
        order = row["expected_narrative_order"]
        if len(order) not in frame_ranges:
            raise ValueError(f"{row['id']}: cannot fit {len(order)} beats in five seconds")
        row["target_duration_s"] = 5
        row["narrative_beats"] = [{"beat": beat, "expected_frame_range": span}
                                  for beat, span in zip(order, frame_ranges[len(order)])]
    OUTPUT.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in selected), encoding="utf-8")
    counts = Counter((r["discipline"], r["task_type"]) for r in selected)
    report = {"count": len(selected), "image_optional_count": sum(r["first_frame_policy"] == "available_optional" for r in selected),
              "adapted_count": len(added), "retired_count": len(retired), "adaptations": added,
              "scope_replacement_count": len(scope_replaced), "scope_replacements": scope_replaced,
              "adaptation_review_flags": dict(Counter(flag for r in selected if r.get("curation", {}).get("conversion") in
                                               {"task_reframing_v1", "subject_specific_rewrite_v1"}
                                               for flag in r["curation"].get("review_flags", []))),
              "retired_ids": retired, "by_discipline_and_task": {d: {t: counts[(d, t)] for t in ("explanation", "problem_solving")} for d in disciplines},
              "release_ready": False,
              "review_warning": "Adaptations are source-linked drafts. Subject truth, answer specificity, near duplicates and visual assets need item-level review before evaluation."}
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    print(json.dumps(build(), ensure_ascii=False, indent=2))
