"""Build a harder visual-evidence TeachQuiz pilot.

Unlike the concept quiz in build_teachquiz_pilot.py, these questions ask about
what the video shows. They should be difficult without seeing the generated
frames, making them better suited for the "student originally cannot answer"
learning-gain setup.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


OUT_PATH = Path("data/teachquiz/pilot_v0_1_visual_probe.jsonl")


def q(qid: str, question: str, choices: list[str], answer: str, rationale: str) -> dict[str, Any]:
    assert answer in {"A", "B", "C", "D"}
    assert len(choices) == 4
    return {
        "id": qid,
        "question": question,
        "choices": choices,
        "answer": answer,
        "tested_concepts": ["video evidence", "visual grounding"],
        "rationale": rationale,
    }


QUIZ: list[dict[str, Any]] = [
    {
        "case_id": "math_exp_02",
        "quiz": [
            q(
                "math_exp_02_v1",
                "In the shown video frames, what geometric object is most central?",
                ["Triangles", "A battery circuit", "A beaker of water", "A DNA double helix"],
                "A",
                "The prompt asks for a visual proof using triangles.",
            ),
            q(
                "math_exp_02_v2",
                "Which visual cue should indicate the angle-sum idea in the video?",
                ["Colored angle pieces arranged near a straight line", "A sodium electron transfer", "A camel caravan", "A binary search list"],
                "A",
                "The expected video rearranges angle pieces along a line.",
            ),
        ],
    },
    {
        "case_id": "phys_exp_01",
        "quiz": [
            q(
                "phys_exp_01_v1",
                "What interaction should the video visually depict?",
                ["A person pushing a wall", "A lens focusing rays", "Molecules forming NaCl", "Dice showing a sum"],
                "A",
                "Newton's third law prompt uses a person-wall interaction.",
            ),
            q(
                "phys_exp_01_v2",
                "Which annotation would be most relevant in the video?",
                ["Two opposite force arrows", "A pH logarithm", "A benzene hexagon", "A hurricane eye"],
                "A",
                "The prompt asks for equal-and-opposite force arrows.",
            ),
        ],
    },
    {
        "case_id": "phys_prob_01",
        "quiz": [
            q(
                "phys_prob_01_v1",
                "What problem setup should appear in the video?",
                ["A 2 kg block with a 10 N horizontal force", "A triangle angle proof", "A Silk Road caravan", "A color-mixing palette"],
                "A",
                "The problem asks for acceleration of a 2 kg block under 10 N.",
            ),
            q(
                "phys_prob_01_v2",
                "Which equation should the worked solution show?",
                ["F = ma", "pH = -log[H+]", "I = V/R for two resistors", "P = 6/36"],
                "A",
                "The solution should use Newton's second law.",
            ),
        ],
    },
    {
        "case_id": "chem_exp_01",
        "quiz": [
            q(
                "chem_exp_01_v1",
                "Which atoms should be shown in the video?",
                ["Sodium and chlorine", "Carbon and oxygen only", "Hydrogen and helium", "Silicon and gold"],
                "A",
                "NaCl formation requires sodium and chlorine.",
            ),
            q(
                "chem_exp_01_v2",
                "What visual event should happen between the atoms?",
                ["One electron transfers from Na to Cl", "A tangent line slides on a curve", "A hurricane rotates", "A binary list is split"],
                "A",
                "The prompt asks for electron transfer from sodium to chlorine.",
            ),
        ],
    },
    {
        "case_id": "bio_exp_01",
        "quiz": [
            q(
                "bio_exp_01_v1",
                "What biological process should the video show?",
                ["Mitosis in a cell", "Combustion of methane", "Convex lens refraction", "Demand curve movement"],
                "A",
                "The video prompt is about mitosis.",
            ),
            q(
                "bio_exp_01_v2",
                "Which visual sequence is most relevant?",
                ["Chromosomes align and separate", "A price rises from 10 to 12", "Red and yellow paint mix", "A caravan crosses a desert"],
                "A",
                "Mitosis requires chromosome alignment and separation.",
            ),
        ],
    },
    {
        "case_id": "cs_prob_01",
        "quiz": [
            q(
                "cs_prob_01_v1",
                "What algorithm should the video illustrate?",
                ["Binary search", "Newton's third law", "Ionic bonding", "Mitosis"],
                "A",
                "The case asks for a binary-search problem-solving video.",
            ),
            q(
                "cs_prob_01_v2",
                "Which visual would best match the intended solution?",
                ["A sorted list with a highlighted middle element", "A beaker with convection arrows", "A benzene ring", "A hurricane spiral"],
                "A",
                "Binary search should inspect the middle of a sorted interval.",
            ),
        ],
    },
    {
        "case_id": "hist_exp_03",
        "quiz": [
            q(
                "hist_exp_03_v1",
                "Which scene should the video show?",
                ["A Silk Road caravan or trade route", "A free-body diagram", "A pH calculation", "A cell division diagram"],
                "A",
                "The prompt asks for a Silk Road explanation.",
            ),
            q(
                "hist_exp_03_v2",
                "Which object would best support historical accuracy here?",
                ["Pack animals or traders", "Modern trucks", "A microscope chromosome", "A convex lens"],
                "A",
                "Ancient trade-route visuals should avoid modern vehicles.",
            ),
        ],
    },
    {
        "case_id": "geo_exp_03",
        "quiz": [
            q(
                "geo_exp_03_v1",
                "What weather system should appear in the video?",
                ["A hurricane", "A triangle proof", "A sodium chloride crystal", "A sorted array"],
                "A",
                "The case is about hurricane structure.",
            ),
            q(
                "geo_exp_03_v2",
                "Which feature should be visible in the hurricane diagram?",
                ["A central eye with spiral bands", "A DNA base pair", "A resistor in series", "A tangent line"],
                "A",
                "The expected visual has an eye and spiral rotation.",
            ),
        ],
    },
    {
        "case_id": "econ_prob_02",
        "quiz": [
            q(
                "econ_prob_02_v1",
                "What graph should the video contain?",
                ["A demand curve with price and quantity", "A benzene ring", "A mitosis phase chart", "A convex lens ray diagram"],
                "A",
                "The economics case asks about a demand curve response.",
            ),
            q(
                "econ_prob_02_v2",
                "Which axes should be most relevant?",
                ["Price and quantity", "Force and mass", "pH and hydrogen only", "Chromosome and spindle only"],
                "A",
                "Demand diagrams use price and quantity axes.",
            ),
        ],
    },
    {
        "case_id": "art_exp_01",
        "quiz": [
            q(
                "art_exp_01_v1",
                "What should the video visually demonstrate?",
                ["Paint colors being mixed", "A physics block accelerating", "A sorted-list search", "A Silk Road route"],
                "A",
                "The case is about color mixing.",
            ),
            q(
                "art_exp_01_v2",
                "Which resulting color should appear from red plus yellow?",
                ["Orange", "Green", "Purple", "Blue"],
                "A",
                "The expected visual includes red+yellow=orange.",
            ),
        ],
    },
]


def main() -> None:
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    rotate_answers(QUIZ)
    with OUT_PATH.open("w", encoding="utf-8") as f:
        for row in QUIZ:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    n_q = sum(len(row["quiz"]) for row in QUIZ)
    print(f"wrote {OUT_PATH} ({len(QUIZ)} cases, {n_q} questions)")


def rotate_answers(rows: list[dict[str, Any]]) -> None:
    """Move the correct option across A/B/C/D to reduce position bias."""
    targets = list("ABCD")
    flat = [item for row in rows for item in row["quiz"]]
    for i, item in enumerate(flat):
        target = targets[i % len(targets)]
        current = item["answer"]
        if current == target:
            continue
        cur_idx = "ABCD".index(current)
        target_idx = "ABCD".index(target)
        item["choices"][cur_idx], item["choices"][target_idx] = (
            item["choices"][target_idx],
            item["choices"][cur_idx],
        )
        item["answer"] = target


if __name__ == "__main__":
    main()
