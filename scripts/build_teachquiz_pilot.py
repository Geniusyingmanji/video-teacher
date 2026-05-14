"""Build a small hand-curated TeachQuiz-T pilot set.

The MVP intentionally starts with explicit multiple-choice questions instead
of LLM-generated quiz items. This keeps the first signal check independent of
question-generation noise.

Run:
    python scripts/build_teachquiz_pilot.py

Writes:
    data/teachquiz/pilot_v0_1_quiz.jsonl
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


OUT_PATH = Path("data/teachquiz/pilot_v0_1_quiz.jsonl")


def q(
    qid: str,
    question: str,
    choices: list[str],
    answer: str,
    concepts: list[str],
    rationale: str,
) -> dict[str, Any]:
    assert answer in {"A", "B", "C", "D"}
    assert len(choices) == 4
    return {
        "id": qid,
        "question": question,
        "choices": choices,
        "answer": answer,
        "tested_concepts": concepts,
        "rationale": rationale,
    }


QUIZ: list[dict[str, Any]] = [
    {
        "case_id": "math_exp_02",
        "quiz": [
            q(
                "math_exp_02_q1",
                "What is the sum of the three interior angles of any Euclidean triangle?",
                ["90 degrees", "120 degrees", "180 degrees", "360 degrees"],
                "C",
                ["triangle angle sum", "straight angle"],
                "The detached angles can be rearranged into a straight angle, which is 180 degrees.",
            ),
            q(
                "math_exp_02_q2",
                "In the visual proof, what should the three angle pieces form when placed together?",
                ["A straight line", "A circle", "A right angle", "A new triangle"],
                "A",
                ["triangle angle sum", "visual proof"],
                "The angle pieces are arranged along one straight reference line.",
            ),
            q(
                "math_exp_02_q3",
                "Does the 180-degree angle-sum rule depend on the triangle being equilateral?",
                ["Yes, only equilateral triangles", "Yes, only right triangles", "No, it applies to all Euclidean triangles", "No, it applies only to obtuse triangles"],
                "C",
                ["generality", "Euclidean geometry"],
                "The rule holds for any Euclidean triangle.",
            ),
        ],
    },
    {
        "case_id": "phys_exp_01",
        "quiz": [
            q(
                "phys_exp_01_q1",
                "Newton's third law says the forces between two interacting bodies are:",
                ["Equal in magnitude and opposite in direction", "Equal in direction and different in magnitude", "Only on the lighter body", "Always vertical"],
                "A",
                ["Newton's third law", "action-reaction"],
                "Action-reaction forces are equal in magnitude and opposite in direction.",
            ),
            q(
                "phys_exp_01_q2",
                "If a person pushes a wall, which body also experiences a force?",
                ["Only the wall", "Only the person", "Both the wall and the person", "Neither body"],
                "C",
                ["force pairs", "interacting bodies"],
                "The person pushes the wall and the wall pushes back on the person.",
            ),
            q(
                "phys_exp_01_q3",
                "Where should the two force arrows be drawn for a correct third-law diagram?",
                ["Both arrows on the person", "Both arrows on the wall", "One on each interacting body", "Only on the ground"],
                "C",
                ["force diagram", "action-reaction"],
                "A third-law pair acts on two different bodies.",
            ),
        ],
    },
    {
        "case_id": "phys_prob_01",
        "quiz": [
            q(
                "phys_prob_01_q1",
                "A 2 kg block has a 10 N horizontal net force on a frictionless floor. What is its acceleration?",
                ["2 m/s^2", "5 m/s^2", "10 m/s^2", "20 m/s^2"],
                "B",
                ["Newton's second law", "F=ma"],
                "Using F=ma, a=F/m=10/2=5 m/s^2.",
            ),
            q(
                "phys_prob_01_q2",
                "Which equation directly connects net force, mass, and acceleration?",
                ["pH = -log[H+]", "F = ma", "V = IR", "P = 6/36"],
                "B",
                ["Newton's second law"],
                "Newton's second law is F=ma.",
            ),
            q(
                "phys_prob_01_q3",
                "On a frictionless floor, what horizontal friction force should appear in the free-body diagram?",
                ["10 N left", "10 N right", "0 N", "2 N downward"],
                "C",
                ["free-body diagram", "frictionless surface"],
                "Frictionless means no horizontal friction force.",
            ),
        ],
    },
    {
        "case_id": "chem_exp_01",
        "quiz": [
            q(
                "chem_exp_01_q1",
                "In forming NaCl, what happens to sodium's valence electron?",
                ["It is transferred to chlorine", "It is shared equally with chlorine", "It disappears", "It moves to a hydrogen atom"],
                "A",
                ["ionic bonding", "electron transfer"],
                "NaCl forms by electron transfer from Na to Cl.",
            ),
            q(
                "chem_exp_01_q2",
                "After electron transfer in NaCl formation, sodium and chlorine become:",
                ["Na- and Cl+", "Na+ and Cl-", "Na2 and Cl2", "Neutral Na and neutral Cl only"],
                "B",
                ["ions", "charge labels"],
                "Sodium loses one electron and becomes Na+; chlorine gains one and becomes Cl-.",
            ),
            q(
                "chem_exp_01_q3",
                "What force holds Na+ and Cl- together in ionic bonding?",
                ["Electrostatic attraction", "Gravity only", "Magnetic induction", "Nuclear fusion"],
                "A",
                ["ionic bonding", "electrostatic attraction"],
                "Oppositely charged ions attract electrostatically.",
            ),
        ],
    },
    {
        "case_id": "bio_exp_01",
        "quiz": [
            q(
                "bio_exp_01_q1",
                "During which mitosis phase do sister chromatids separate?",
                ["Prophase", "Metaphase", "Anaphase", "Telophase"],
                "C",
                ["mitosis", "chromosome separation"],
                "Sister chromatids separate during anaphase.",
            ),
            q(
                "bio_exp_01_q2",
                "In metaphase, chromosomes are typically shown:",
                ["Aligned at the cell midline", "Already in two nuclei", "Outside the cell membrane", "As dissolved bases"],
                "A",
                ["mitosis", "metaphase"],
                "Metaphase aligns chromosomes at the middle of the cell.",
            ),
            q(
                "bio_exp_01_q3",
                "What forms near the end of telophase?",
                ["Two daughter nuclei", "A benzene ring", "A convex lens", "A battery loop"],
                "A",
                ["mitosis", "telophase"],
                "Telophase reforms nuclei around separated chromosomes.",
            ),
        ],
    },
    {
        "case_id": "cs_prob_01",
        "quiz": [
            q(
                "cs_prob_01_q1",
                "In binary search on a sorted list, which element is inspected first?",
                ["The middle element", "The last element only", "Every element from left to right", "A random element that is never changed"],
                "A",
                ["binary search", "algorithm steps"],
                "Binary search begins by checking the middle of the sorted search interval.",
            ),
            q(
                "cs_prob_01_q2",
                "If the target is smaller than the middle element in binary search, what should happen next?",
                ["Search the left half", "Search the right half", "Stop with success", "Reverse the list"],
                "A",
                ["binary search", "branching"],
                "For a sorted ascending list, smaller-than-middle means the target can only be in the left half.",
            ),
            q(
                "cs_prob_01_q3",
                "Binary search requires the input list to be:",
                ["Sorted", "Encrypted", "Circular", "Made only of negative numbers"],
                "A",
                ["binary search", "preconditions"],
                "Binary search relies on sorted order.",
            ),
        ],
    },
    {
        "case_id": "hist_exp_03",
        "quiz": [
            q(
                "hist_exp_03_q1",
                "A historically appropriate Silk Road scene should mainly show:",
                ["Caravans moving along trade routes", "Modern cars on highways", "Spacecraft launch pads", "A stock exchange screen"],
                "A",
                ["Silk Road", "historical setting"],
                "Silk Road teaching visuals often depict caravans and overland trade routes.",
            ),
            q(
                "hist_exp_03_q2",
                "Which item would be an obvious anachronism in an ancient Silk Road video?",
                ["Camel caravan", "Market goods", "Modern truck", "Desert route"],
                "C",
                ["anachronism", "historical accuracy"],
                "A modern truck would not belong in an ancient Silk Road depiction.",
            ),
            q(
                "hist_exp_03_q3",
                "The Silk Road is best understood as:",
                ["A network of trade routes", "A single modern subway line", "A law of motion", "A chemical bond"],
                "A",
                ["Silk Road", "trade network"],
                "The Silk Road refers to linked trade routes across regions.",
            ),
        ],
    },
    {
        "case_id": "geo_exp_03",
        "quiz": [
            q(
                "geo_exp_03_q1",
                "In a hurricane diagram, where is the eye located?",
                ["At the calm center", "At the outermost rain band only", "Below the ocean floor", "At both poles"],
                "A",
                ["hurricane structure", "eye"],
                "The eye is the calmer central region of a hurricane.",
            ),
            q(
                "geo_exp_03_q2",
                "A hurricane's rotating cloud bands should generally be shown as:",
                ["A spiral around the eye", "A straight vertical ruler", "A triangle angle proof", "A static benzene ring"],
                "A",
                ["hurricane structure", "spiral bands"],
                "Hurricane cloud bands spiral around the center.",
            ),
            q(
                "geo_exp_03_q3",
                "What powers hurricanes over warm oceans?",
                ["Heat and moisture from warm ocean water", "A battery in a circuit", "Electron transfer from sodium", "A sorted list"],
                "A",
                ["hurricane formation", "warm ocean water"],
                "Warm ocean water supplies heat and moisture to storms.",
            ),
        ],
    },
    {
        "case_id": "econ_prob_02",
        "quiz": [
            q(
                "econ_prob_02_q1",
                "If price rises from $10 to $12 and quantity demanded falls from 100 to 80, what is the direction of demand response?",
                ["Quantity demanded falls", "Quantity demanded rises", "Quantity is unchanged", "Price becomes negative"],
                "A",
                ["demand curve", "price-quantity relationship"],
                "The prompt states demand falls from 100 to 80 as price rises.",
            ),
            q(
                "econ_prob_02_q2",
                "On a standard demand curve graph, price is usually on the:",
                ["Vertical axis", "Horizontal axis", "Color legend only", "Time axis only"],
                "A",
                ["demand graph", "axes"],
                "Economics diagrams usually put price on the vertical axis and quantity on the horizontal axis.",
            ),
            q(
                "econ_prob_02_q3",
                "A downward-sloping demand curve means that, all else equal:",
                ["Higher price is associated with lower quantity demanded", "Higher price always raises quantity demanded", "Quantity cannot change", "Demand is unrelated to price"],
                "A",
                ["demand curve", "law of demand"],
                "A standard demand curve slopes downward: price up, quantity demanded down.",
            ),
        ],
    },
    {
        "case_id": "art_exp_01",
        "quiz": [
            q(
                "art_exp_01_q1",
                "Mixing red and yellow paint usually produces:",
                ["Orange", "Green", "Purple", "Black only"],
                "A",
                ["color mixing", "primary colors"],
                "In subtractive paint mixing, red plus yellow commonly makes orange.",
            ),
            q(
                "art_exp_01_q2",
                "Mixing blue and yellow paint usually produces:",
                ["Green", "Orange", "White", "Red"],
                "A",
                ["color mixing", "primary colors"],
                "Blue and yellow paint mix to green.",
            ),
            q(
                "art_exp_01_q3",
                "A useful teaching video on paint mixing should visually show:",
                ["The starting colors and resulting mixed color", "Only a blank wall", "An unrelated circuit", "Only text with no colors"],
                "A",
                ["didactic visualization", "color mixing"],
                "The learner needs to see both input colors and the resulting mixture.",
            ),
        ],
    },
]


def main() -> None:
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", encoding="utf-8") as f:
        for row in QUIZ:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    n_q = sum(len(row["quiz"]) for row in QUIZ)
    print(f"wrote {OUT_PATH} ({len(QUIZ)} cases, {n_q} questions)")


if __name__ == "__main__":
    main()
