"""Pilot prompt set for rise-teacher v0.1.

Hand-curated ~60 prompts covering 12 disciplines × {explanation, problem_solving}
to prove the end-to-end pipeline (data -> gen -> eval).

Run:
    python scripts/build_pilot_prompts.py
Writes:
    data/prompts/pilot_v0_1.jsonl
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def case(
    cid: str,
    discipline: str,
    subdomain: str,
    task: str,
    difficulty: str,
    prompt: str,
    concepts: list[str],
    visuals: list[str],
    order: list[str],
    audience: str,
    rubric: list[str],
    audio: bool = False,
) -> dict[str, Any]:
    assert task in {"explanation", "problem_solving"}
    assert difficulty in {"k12", "undergrad", "professional"}
    return {
        "id": cid,
        "discipline": discipline,
        "subdomain": subdomain,
        "task_type": task,
        "difficulty": difficulty,
        "prompt_text": prompt.strip(),
        "expected_concepts": concepts,
        "expected_visual_elements": visuals,
        "expected_narrative_order": order,
        "pedagogical_target_audience": audience,
        "discipline_specific_rubric": rubric,
        "audio_narration_required": audio,
    }


CASES: list[dict[str, Any]] = []

# ============================================================================
# 1. MATHEMATICS  (5 cases)
# ============================================================================
CASES += [
    case("math_exp_01", "mathematics", "calculus", "explanation", "undergrad",
         "Generate a 10-second educational video explaining the geometric meaning of "
         "the derivative of a function at a point, using a smooth curve and a tangent "
         "line that slides along it. Show clear x-y axes, label the curve y=f(x), and "
         "highlight the tangent line touching one moving point. Narration should "
         "describe the derivative as the slope of the tangent line.",
         ["derivative as slope", "tangent line", "limit definition"],
         ["coordinate axes labeled x and y", "smooth curve labeled f(x)", "tangent line touching curve"],
         ["show curve", "place point on curve", "draw tangent at point", "slide point and tangent together"],
         "undergrad calculus student",
         ["axes are labeled", "tangent line actually touches the curve at one point",
          "tangent slope visually matches local curve slope"],
         audio=True),
    case("math_exp_02", "mathematics", "geometry", "explanation", "k12",
         "Generate a short educational video showing that the sum of the three interior "
         "angles of any triangle equals 180 degrees. Start with three different triangles, "
         "then for one of them detach the three angle pieces and arrange them along a "
         "straight line to form 180 degrees.",
         ["interior angles of a triangle", "angle sum = 180", "straight angle"],
         ["three different triangles", "colored angle markers", "a straight reference line"],
         ["show triangles", "highlight three interior angles", "detach angles", "arrange along a line"],
         "K-12 (grades 6-8)",
         ["triangles have visibly different shapes", "angle pieces visibly add up to a straight line",
          "no contradiction with Euclidean geometry"]),
    case("math_exp_03", "mathematics", "probability", "explanation", "k12",
         "Generate a short educational video explaining how rolling two fair six-sided "
         "dice can give a sum of 7 in six different ways. Show all six pairings clearly.",
         ["sample space", "favorable outcomes", "probability fraction"],
         ["two six-sided dice", "table or list of (a,b) pairs", "sum highlighted"],
         ["show dice", "enumerate (1,6),(2,5),(3,4),(4,3),(5,2),(6,1)", "state P=6/36=1/6"],
         "K-12 (grades 7-9)",
         ["exactly 6 valid pairings shown", "P=1/6 stated correctly", "no invalid pair like (1,7)"]),
    case("math_prob_01", "mathematics", "algebra", "problem_solving", "k12",
         "Generate a video that solves step by step: 'Find x such that 2x + 5 = 17'. "
         "Show each manipulation visually on screen and end with the final answer.",
         ["linear equation", "isolate variable", "inverse operations"],
         ["the equation written on board", "subtract-5 step", "divide-by-2 step", "final x=6"],
         ["write 2x+5=17", "subtract 5 -> 2x=12", "divide by 2 -> x=6", "verify"],
         "K-12 (grades 6-8)",
         ["arithmetic is correct at each step", "final answer x=6", "operations applied to both sides"]),
    case("math_prob_02", "mathematics", "calculus", "problem_solving", "undergrad",
         "Generate a video that walks through finding the derivative of f(x) = x^3 + 2x "
         "using the power rule. Write each rule application visually.",
         ["power rule", "sum rule", "derivative notation"],
         ["original function", "power rule applied to x^3", "power rule applied to 2x", "result 3x^2+2"],
         ["state f(x)=x^3+2x", "differentiate term by term", "x^3 -> 3x^2", "2x -> 2", "combine"],
         "undergrad calculus student",
         ["3x^2+2 final answer correct", "no missing terms", "power rule applied with correct exponents"]),
]

# ============================================================================
# 2. PHYSICS  (5 cases)
# ============================================================================
CASES += [
    case("phys_exp_01", "physics", "mechanics", "explanation", "k12",
         "Generate a 10-second educational video showing Newton's third law: a person "
         "pushes a wall and visibly receives an equal-and-opposite push back. Use arrow "
         "annotations for the two forces, labeled with equal magnitude and opposite direction.",
         ["action-reaction pair", "equal magnitude", "opposite direction", "Newton's 3rd law"],
         ["person", "wall", "two force arrows with labels"],
         ["person approaches wall", "push contact", "draw force arrows", "label them F and -F"],
         "K-12 (grades 8-10)",
         ["two arrows are equal in length", "arrows point in opposite directions",
          "arrows are on the two distinct bodies (one on wall, one on person)"]),
    case("phys_exp_02", "physics", "optics", "explanation", "k12",
         "Generate a short video showing how a convex lens focuses parallel rays of "
         "light to a focal point on the principal axis. Draw 3 parallel rays entering "
         "the lens and converging to one point F on the right side.",
         ["convex lens", "focal point", "principal axis", "ray convergence"],
         ["lens cross-section", "3 parallel rays entering", "rays converging to F"],
         ["draw lens and axis", "send in 3 parallel rays", "rays refract", "all rays meet at F"],
         "K-12 (grades 9-10)",
         ["rays are parallel BEFORE the lens", "rays converge AFTER the lens",
          "all 3 rays meet at a single point F on the axis"]),
    case("phys_exp_03", "physics", "thermodynamics", "explanation", "undergrad",
         "Generate an educational video showing convection in a beaker of water heated "
         "from below: hot water rises along the center, cools at the top, then sinks "
         "along the sides, forming convection cells.",
         ["density-driven flow", "convection cells", "heat transfer"],
         ["beaker with water", "flame or heater below", "circulation arrows"],
         ["heat applied", "water at bottom heats and rises", "cools at surface", "sinks along walls", "loop continues"],
         "undergrad thermodynamics student",
         ["upward flow is in the center (above heat source)", "downward flow is along the sides",
          "circulation is continuous, not random"]),
    case("phys_prob_01", "physics", "mechanics", "problem_solving", "k12",
         "Generate a video that solves: 'A 2 kg block sits on a frictionless floor. A 10 N "
         "horizontal force is applied. What is its acceleration?' Show free-body diagram, "
         "apply F = m*a, and present the answer.",
         ["Newton's 2nd law", "free body diagram", "F=ma"],
         ["block on surface", "applied force arrow labeled 10 N", "free body diagram", "equation F=ma"],
         ["draw setup", "draw FBD", "write F=ma", "substitute 10=2a", "solve a=5 m/s^2"],
         "K-12 (grades 9-11)",
         ["a = 5 m/s^2 final answer correct", "FBD shows only horizontal force (no friction)",
          "units shown as m/s^2"]),
    case("phys_prob_02", "physics", "electricity", "problem_solving", "undergrad",
         "Generate a video solving: 'Two resistors R1=4 ohm and R2=6 ohm are connected in "
         "series across a 10 V battery. What is the current?' Draw the circuit, sum the "
         "resistances, apply Ohm's law.",
         ["series resistors", "Ohm's law", "equivalent resistance"],
         ["circuit diagram with battery and two resistors in series", "R_eq = 10 ohm", "I = V/R"],
         ["draw circuit", "compute R_eq = 4+6 = 10", "apply I = V/R_eq", "I = 10/10 = 1 A"],
         "undergrad physics student",
         ["I = 1 A final answer correct", "resistors drawn in series (single loop)",
          "battery symbol with + and - polarity"]),
]

# ============================================================================
# 3. CHEMISTRY  (5 cases)
# ============================================================================
CASES += [
    case("chem_exp_01", "chemistry", "inorganic", "explanation", "k12",
         "Generate a short educational video showing how sodium (Na) and chlorine (Cl) atoms "
         "form NaCl by transferring one electron from Na to Cl, resulting in Na+ and Cl- "
         "ions that attract.",
         ["ionic bonding", "electron transfer", "cation and anion", "electrostatic attraction"],
         ["Na atom with one valence electron", "Cl atom with 7 valence electrons", "electron jumping over", "Na+ and Cl- final state"],
         ["show two atoms", "highlight Na's 1 valence electron", "transfer it to Cl",
          "label Na+ and Cl-", "ions snap together"],
         "K-12 (grades 9-10)",
         ["electron count is correct (Na loses 1, Cl gains 1)", "charges are labeled correctly",
          "products are Na+ and Cl-, not Na2 or Cl2"]),
    case("chem_exp_02", "chemistry", "organic", "explanation", "undergrad",
         "Generate a video explaining the structure of a benzene ring, showing 6 carbons in "
         "a hexagonal ring with alternating single and double bonds (Kekule) and then the "
         "delocalized electron cloud representation.",
         ["benzene", "Kekule structure", "delocalized pi electrons", "aromaticity"],
         ["hexagonal ring of 6 C atoms", "alternating C=C/C-C bonds", "circle inside hexagon for delocalization"],
         ["draw hexagon", "place 6 carbons", "show Kekule single/double pattern",
          "transition to circle representation"],
         "undergrad organic chemistry student",
         ["ring has exactly 6 carbons", "alternating bond pattern is correct (3 doubles, 3 singles)",
          "final representation includes a delocalization symbol"]),
    case("chem_exp_03", "chemistry", "reactions", "explanation", "k12",
         "Generate a short video showing the combustion of methane: CH4 + 2 O2 -> CO2 + 2 H2O. "
         "Visualize molecules before and after reaction, with balancing made obvious.",
         ["combustion", "stoichiometry", "balanced equation"],
         ["1 CH4 molecule", "2 O2 molecules", "1 CO2 molecule", "2 H2O molecules"],
         ["show reactants", "react", "show products"],
         "K-12 (grades 10-11)",
         ["atom count is conserved (C:1->1, H:4->4, O:4->4)",
          "exactly 2 O2 on left and 2 H2O on right",
          "no extra or missing atoms"]),
    case("chem_prob_01", "chemistry", "stoichiometry", "problem_solving", "k12",
         "Generate a video solving: 'How many moles of H2O are produced when 2 moles of H2 "
         "react completely with O2?' Show 2H2 + O2 -> 2H2O, and walk through the mole ratio.",
         ["mole ratio", "limiting reactant", "balanced equation"],
         ["equation 2H2+O2->2H2O", "mole ratio 2:2", "answer 2 mol H2O"],
         ["state balanced equation", "identify mole ratio H2:H2O = 2:2 = 1:1",
          "apply ratio to 2 mol H2", "answer 2 mol H2O"],
         "K-12 (grades 10-11)",
         ["final answer 2 mol H2O", "equation is balanced", "ratio applied correctly"]),
    case("chem_prob_02", "chemistry", "acid-base", "problem_solving", "undergrad",
         "Generate a video solving: 'A solution has [H+] = 1e-3 M. What is its pH?' "
         "Show the pH = -log[H+] formula and compute the result.",
         ["pH definition", "logarithm", "acidity"],
         ["formula pH = -log[H+]", "substitution", "pH = 3"],
         ["state formula", "substitute 1e-3", "compute -log(1e-3) = 3", "answer pH=3"],
         "undergrad general chemistry student",
         ["pH = 3 final answer correct", "log identity used correctly",
          "explicit -log(1e-3) computation"]),
]

# ============================================================================
# 4. BIOLOGY  (5 cases)
# ============================================================================
CASES += [
    case("bio_exp_01", "biology", "cell_biology", "explanation", "k12",
         "Generate a short educational video showing the four phases of mitosis "
         "(prophase, metaphase, anaphase, telophase) in a single animal cell, with "
         "clear chromosome behavior at each phase.",
         ["mitosis", "chromosome separation", "spindle fibers"],
         ["cell membrane", "chromosomes", "spindle apparatus", "labeled phase name"],
         ["prophase: chromosomes condense", "metaphase: align at midline",
          "anaphase: sisters separate", "telophase: two nuclei form"],
         "K-12 (grades 9-10)",
         ["all 4 phases appear and are labeled", "chromosomes visibly separate in anaphase",
          "two daughter nuclei at the end"]),
    case("bio_exp_02", "biology", "genetics", "explanation", "k12",
         "Generate a short video showing DNA double-helix structure: two antiparallel "
         "sugar-phosphate strands twisted around each other, with base pairs A-T and "
         "G-C connecting them.",
         ["DNA structure", "base pairing", "double helix", "antiparallel strands"],
         ["two backbone strands", "rungs labeled A-T or G-C", "helical twist"],
         ["show two strands", "highlight base pairing", "twist into helix"],
         "K-12 (grades 9-11)",
         ["A pairs only with T and G with C", "two strands are antiparallel (5' to 3' shown both ways)",
          "double helix has visible twist"]),
    case("bio_exp_03", "biology", "physiology", "explanation", "undergrad",
         "Generate a short educational video showing the path of blood through the heart: "
         "right atrium -> right ventricle -> lungs -> left atrium -> left ventricle -> body. "
         "Use color blue for deoxygenated and red for oxygenated.",
         ["pulmonary circulation", "systemic circulation", "oxygenation"],
         ["heart with 4 chambers labeled", "color-coded blood flow", "lungs"],
         ["blood enters right atrium", "to right ventricle", "to lungs (gets oxygen)",
          "back to left atrium", "to left ventricle", "out to body"],
         "undergrad biology student",
         ["chamber order correct (RA->RV->lungs->LA->LV->body)",
          "blue depicts deoxygenated, red oxygenated, transition at lungs",
          "no incorrect shunts (e.g., RA->LA)"]),
    case("bio_prob_01", "biology", "genetics", "problem_solving", "k12",
         "Generate a video solving a Punnett square: 'Cross Aa x Aa. What fraction of "
         "offspring are homozygous recessive (aa)?' Draw the 2x2 Punnett square and count.",
         ["Punnett square", "Mendelian inheritance", "genotype ratio"],
         ["2x2 grid", "parental alleles labeled", "offspring genotypes filled in"],
         ["set up grid", "fill AA, Aa, Aa, aa", "count aa fraction = 1/4"],
         "K-12 (grades 9-10)",
         ["grid is 2x2", "all four cells filled correctly (AA, Aa, Aa, aa)", "final fraction 1/4 correct"]),
    case("bio_prob_02", "biology", "ecology", "problem_solving", "undergrad",
         "Generate a video solving: 'A population of 100 deer grows at 5% per year. "
         "What will the population be in 1 year?' Apply N = N0 * (1+r).",
         ["exponential growth", "growth rate", "compound interest analogy"],
         ["formula N = N0(1+r)", "substitution 100*1.05", "answer 105"],
         ["state formula", "substitute N0=100, r=0.05", "compute", "answer 105 deer"],
         "undergrad ecology student",
         ["answer = 105 deer", "formula applied correctly", "growth rate as fraction not percentage"]),
]

# ============================================================================
# 5. MEDICINE  (5 cases)
# ============================================================================
CASES += [
    case("med_exp_01", "medicine", "anatomy", "explanation", "professional",
         "Generate an educational video showing the structure of a human nephron, the "
         "functional unit of the kidney. Label glomerulus, proximal tubule, loop of Henle, "
         "distal tubule, and collecting duct.",
         ["nephron anatomy", "filtration unit", "kidney"],
         ["glomerulus", "proximal convoluted tubule", "loop of Henle", "distal tubule", "collecting duct"],
         ["show whole nephron schematic", "label each part in sequence",
          "indicate filtrate direction"],
         "medical student",
         ["all 5 components present and correctly labeled",
          "geometric arrangement matches textbook (loop of Henle dips down)",
          "flow direction follows the anatomical order"]),
    case("med_exp_02", "medicine", "pharmacology", "explanation", "professional",
         "Generate a short educational video showing how a beta-blocker drug binds to "
         "beta-adrenergic receptors on heart cells, preventing adrenaline from binding "
         "and thereby slowing heart rate.",
         ["receptor antagonism", "beta-adrenergic receptor", "competitive inhibition"],
         ["heart cell with receptor", "adrenaline molecule blocked", "beta-blocker bound at receptor"],
         ["show receptor on cell", "adrenaline approaches", "blocker also approaches",
          "blocker binds instead", "no heart-rate signal"],
         "medical / pharmacy student",
         ["blocker visibly occupies the same receptor site that adrenaline would bind",
          "adrenaline is shown not binding while blocker is bound",
          "outcome (slower heart rate) is at least implied"]),
    case("med_exp_03", "medicine", "pathology", "explanation", "professional",
         "Generate an educational video showing atherosclerosis progression in a coronary "
         "artery: from healthy endothelium, to fatty streak, to fibrous plaque, to occlusion.",
         ["atherosclerosis", "plaque formation", "lumen narrowing"],
         ["healthy artery cross-section", "fatty streak", "fibrous plaque", "occluded lumen"],
         ["show healthy artery", "show fatty streak deposition", "plaque thickens",
          "lumen narrows to near-occlusion"],
         "medical student",
         ["progression in correct order (healthy -> streak -> plaque -> occlusion)",
          "lumen diameter visibly decreases over stages",
          "endothelial layer is shown"]),
    case("med_prob_01", "medicine", "clinical_calculations", "problem_solving", "professional",
         "Generate a video solving a clinical dose calculation: 'A patient needs 15 mg/kg "
         "of a drug. The patient weighs 70 kg. What is the total dose?' Show the formula "
         "and arithmetic.",
         ["weight-based dosing", "unit handling"],
         ["formula dose = weight * dose-per-kg", "substitution", "answer 1050 mg"],
         ["state formula", "substitute 70 kg * 15 mg/kg", "compute 1050 mg"],
         "nursing or medical student",
         ["final answer 1050 mg", "units handled correctly (kg cancels)",
          "no unit confusion (mg vs g)"]),
    case("med_prob_02", "medicine", "physiology", "problem_solving", "professional",
         "Generate a video solving: 'Stroke volume = 70 mL, heart rate = 75 bpm. What "
         "is cardiac output in L/min?' Apply CO = SV * HR with unit conversion.",
         ["cardiac output", "stroke volume", "heart rate", "unit conversion"],
         ["formula CO = SV * HR", "computation 70*75 = 5250 mL/min", "convert to 5.25 L/min"],
         ["state formula", "multiply", "convert mL to L", "answer 5.25 L/min"],
         "medical student",
         ["final answer 5.25 L/min (or 5250 mL/min equivalently)",
          "unit conversion shown explicitly",
          "no order-of-magnitude error"]),
]

# ============================================================================
# 6. COMPUTER SCIENCE  (5 cases)
# ============================================================================
CASES += [
    case("cs_exp_01", "computer_science", "algorithms", "explanation", "undergrad",
         "Generate an educational video showing how binary search finds the value 7 in "
         "the sorted array [1, 3, 5, 7, 9, 11, 13, 15]. Highlight low/high pointers at "
         "each step and the middle element being compared.",
         ["binary search", "divide and conquer", "log n complexity"],
         ["sorted array as boxes", "low/high pointers", "midpoint highlighted", "comparison result shown"],
         ["initial array with low=0 high=7", "mid=3 -> arr[3]=7 -> found"],
         "undergrad CS student",
         ["array stays sorted throughout", "midpoint computation is correct",
          "search converges to index 3 where value=7"]),
    case("cs_exp_02", "computer_science", "data_structures", "explanation", "undergrad",
         "Generate a short video explaining how a stack works using push/pop operations. "
         "Push 3 elements (A, B, C in order), then pop them.",
         ["LIFO", "stack push and pop", "abstract data type"],
         ["stack drawn vertically", "elements pushed one by one", "elements popped in reverse"],
         ["push A", "push B", "push C", "pop -> C", "pop -> B", "pop -> A"],
         "undergrad CS student",
         ["pop order is reverse of push order (C, B, A)",
          "stack shrinks and grows correctly",
          "no random reordering"]),
    case("cs_exp_03", "computer_science", "networks", "explanation", "undergrad",
         "Generate an educational video showing the TCP 3-way handshake between a client "
         "and a server. Show SYN, SYN-ACK, ACK packets traveling between them.",
         ["TCP handshake", "SYN", "SYN-ACK", "ACK", "connection establishment"],
         ["client box on left", "server box on right", "3 labeled arrows for packets"],
         ["client -> server: SYN", "server -> client: SYN-ACK", "client -> server: ACK"],
         "undergrad networking student",
         ["3 packets in correct order", "labels SYN / SYN-ACK / ACK correct",
          "direction arrows match standard handshake"]),
    case("cs_prob_01", "computer_science", "complexity", "problem_solving", "undergrad",
         "Generate a video solving: 'What is the time complexity of nested for-loops where "
         "outer runs n times and inner runs n times?' Show the code and derive O(n^2).",
         ["Big-O notation", "nested loops", "multiplicative complexity"],
         ["code snippet of double for-loop", "iteration count n*n", "answer O(n^2)"],
         ["show code", "outer iterates n times", "inner iterates n times each", "total n*n", "O(n^2)"],
         "undergrad CS student",
         ["final answer O(n^2)", "n*n derivation shown",
          "no confusion with O(n) or O(n log n)"]),
    case("cs_prob_02", "computer_science", "algorithms", "problem_solving", "undergrad",
         "Generate a video that traces bubble sort on the array [3, 1, 2]. Show each "
         "comparison and swap until the array is sorted.",
         ["bubble sort", "in-place swap", "pass-based sorting"],
         ["array as boxes", "comparison highlights", "swap animations"],
         ["compare 3,1 -> swap -> [1,3,2]", "compare 3,2 -> swap -> [1,2,3]",
          "second pass no swaps", "sorted"],
         "undergrad CS student",
         ["final sorted array [1,2,3]",
          "swaps happen only when out of order",
          "no values appear or disappear"]),
]

# ============================================================================
# 7. HISTORY  (5 cases) — humanities — totally new territory
# ============================================================================
CASES += [
    case("hist_exp_01", "history", "ancient", "explanation", "k12",
         "Generate a short educational video showing the construction of the Great "
         "Pyramid of Giza in ancient Egypt: workers transporting limestone blocks on "
         "sleds and ramps, with the pyramid growing course by course.",
         ["Old Kingdom Egypt", "pyramid construction", "labor organization"],
         ["partially built pyramid", "limestone blocks", "workers", "ramps and sleds"],
         ["show base of pyramid", "workers drag blocks up ramps", "pyramid grows taller", "near completion"],
         "K-12 (grades 6-8)",
         ["pyramid shape is square-based with 4 triangular faces",
          "construction is on ramps, not cranes",
          "no obvious anachronisms (no machinery, modern people, etc.)"]),
    case("hist_exp_02", "history", "modern", "explanation", "undergrad",
         "Generate a short educational video depicting Christopher Columbus' first "
         "1492 voyage: three ships (Santa Maria, Pinta, Niña) sailing west from Spain "
         "across the Atlantic to the Caribbean.",
         ["Age of Discovery", "Columbus 1492", "transatlantic voyage"],
         ["three sailing ships", "ocean", "map of Atlantic", "Spanish flag"],
         ["depart Spain", "Atlantic crossing", "arrive Caribbean"],
         "undergrad world-history student",
         ["three ships visible (not two, not four)",
          "ships are 15th-century sailing vessels (no steam, no modern hulls)",
          "no anachronistic flags or technology"]),
    case("hist_exp_03", "history", "geography_history", "explanation", "k12",
         "Generate a short educational video showing the Silk Road trade route across "
         "Asia: a camel caravan moving from China through Central Asia toward the "
         "Mediterranean, carrying silk and spices.",
         ["Silk Road", "Eurasian trade", "camel caravan"],
         ["map of Asia with route drawn", "camel caravan", "trade goods"],
         ["caravan in eastern China", "crosses Central Asia", "reaches Mediterranean port"],
         "K-12 (grades 6-8)",
         ["caravan uses camels, not horses for long stretches",
          "geographic direction roughly west from China",
          "no airplanes or cars"]),
    case("hist_prob_01", "history", "chronology", "problem_solving", "k12",
         "Generate a video that solves a chronology question: 'Place these 4 events in "
         "order: World War I begins, French Revolution, Moon landing, Industrial "
         "Revolution starts.' Show them on a timeline.",
         ["historical chronology", "timeline ordering"],
         ["horizontal timeline", "4 events placed on it", "years labeled"],
         ["Industrial Revolution starts (c.1760)", "French Revolution (1789)",
          "WWI begins (1914)", "Moon landing (1969)"],
         "K-12 (grades 7-9)",
         ["correct order: Industrial Rev -> French Rev -> WWI -> Moon",
          "years are approximately correct",
          "events not reordered"]),
    case("hist_prob_02", "history", "cause_effect", "problem_solving", "undergrad",
         "Generate a video walking through the immediate causes of World War I in 1914: "
         "(1) assassination of Archduke Franz Ferdinand, (2) Austria-Hungary's ultimatum "
         "to Serbia, (3) alliance system activation, (4) major powers mobilize.",
         ["WWI causes", "July Crisis", "alliance system"],
         ["Sarajevo assassination scene", "diplomatic documents", "European map with alliances", "mobilization"],
         ["assassination (June 28)", "ultimatum to Serbia (July)",
          "alliances pull powers in", "August mobilizations"],
         "undergrad European-history student",
         ["sequence is correct (assassination first, then ultimatum, then alliance, then mobilization)",
          "year 1914 only — no events from before or after",
          "no factual reversal (e.g., Serbia attacking first)"]),
]

# ============================================================================
# 8. GEOGRAPHY  (5 cases)
# ============================================================================
CASES += [
    case("geo_exp_01", "geography", "physical", "explanation", "k12",
         "Generate a short educational video showing the water cycle: evaporation from "
         "ocean, cloud formation, precipitation over land, river flow back to sea.",
         ["water cycle", "evaporation", "condensation", "precipitation", "runoff"],
         ["ocean", "rising water vapor arrows", "cloud", "rain", "river", "labels for each phase"],
         ["evaporation from ocean", "vapor rises", "clouds form", "precipitation",
          "runoff via river back to ocean"],
         "K-12 (grades 5-7)",
         ["cycle is closed (water returns)", "all 4 phases shown and labeled",
          "rain falls from cloud onto land, not from clear sky"]),
    case("geo_exp_02", "geography", "tectonics", "explanation", "undergrad",
         "Generate an educational video showing the three main types of plate boundaries: "
         "divergent (plates move apart, magma rises), convergent (one plate dives under "
         "the other), and transform (plates slide past each other).",
         ["plate tectonics", "divergent boundary", "convergent boundary", "transform boundary"],
         ["3 panels or 3 sub-scenes", "arrows on plates", "magma at divergent", "subduction at convergent"],
         ["show divergent (arrows apart, magma)", "show convergent (one plate dives)",
          "show transform (sliding past)"],
         "undergrad geology student",
         ["each of 3 boundary types correctly depicted",
          "arrows match the type (away, toward, parallel)",
          "no swap (e.g., transform shown with subduction)"]),
    case("geo_exp_03", "geography", "climate", "explanation", "k12",
         "Generate a short educational video showing the formation of a hurricane: warm "
         "ocean water evaporates, rises into a rotating storm system, and develops an "
         "eye in the center.",
         ["hurricane formation", "Coriolis effect", "warm water energy source"],
         ["ocean surface", "rotating spiral cloud system", "eye in center", "rain bands"],
         ["warm ocean", "vapor rises", "rotation begins", "system intensifies", "eye forms"],
         "K-12 (grades 7-9)",
         ["spiral rotation visible", "eye is in the center and visibly calmer",
          "system is over warm water (not ice or desert)"]),
    case("geo_prob_01", "geography", "cartography", "problem_solving", "k12",
         "Generate a video solving: 'A map scale is 1:50,000. Two points on the map are "
         "4 cm apart. What is their real-world distance?' Show the scale formula and "
         "compute the answer in km.",
         ["map scale", "unit conversion"],
         ["map with two points", "scale formula", "computation"],
         ["distance_map = 4 cm", "real = 4 * 50,000 cm = 200,000 cm = 2 km", "answer 2 km"],
         "K-12 (grades 6-8)",
         ["answer = 2 km", "scale applied correctly", "unit conversion cm -> km correct"]),
    case("geo_prob_02", "geography", "climate", "problem_solving", "undergrad",
         "Generate a video that walks through interpreting a climograph (monthly average "
         "temperature line + monthly precipitation bars) of a tropical rainforest: high "
         "temperatures all year, high rainfall every month.",
         ["climograph", "tropical rainforest climate", "Koppen classification"],
         ["climograph chart with temp line and precip bars", "12 months on x-axis"],
         ["show chart", "observe temperature flat ~25-28C", "observe precipitation high every month",
          "conclude tropical rainforest (Af)"],
         "undergrad climatology student",
         ["temperature line stays roughly constant high",
          "precipitation bars are tall every month",
          "classification is tropical (not desert or temperate)"]),
]

# ============================================================================
# 9. ECONOMICS & FINANCE  (5 cases)
# ============================================================================
CASES += [
    case("econ_exp_01", "economics", "micro", "explanation", "undergrad",
         "Generate an educational video showing supply and demand curves on a standard "
         "price-quantity diagram. The demand curve slopes down, supply slopes up, they "
         "cross at the equilibrium point. Then shift the demand curve right and show "
         "the new equilibrium has higher price and higher quantity.",
         ["supply and demand", "equilibrium", "demand shift"],
         ["P-Q axes labeled", "downward demand curve", "upward supply curve", "equilibrium dot", "shifted demand"],
         ["draw axes", "draw curves", "mark equilibrium",
          "shift demand right", "mark new higher P and Q"],
         "undergrad micro-econ student",
         ["demand slopes down, supply slopes up (not reversed)",
          "new equilibrium has higher P AND higher Q after demand shifts right",
          "axes are labeled (P on y, Q on x)"]),
    case("econ_exp_02", "economics", "macro", "explanation", "undergrad",
         "Generate a short educational video explaining how inflation erodes purchasing "
         "power: show $100 buying a basket of goods today, and the same $100 buying a "
         "smaller basket 10 years later due to 3% annual inflation.",
         ["inflation", "purchasing power", "compound erosion"],
         ["dollar bills", "basket of goods today", "smaller basket later", "year labels"],
         ["today: $100 -> full basket", "10 years later: $100 -> smaller basket",
          "show shrinkage"],
         "undergrad macro-econ student",
         ["later basket is visibly smaller (not larger)",
          "time gap of about 10 years shown",
          "amount of money stays at $100"]),
    case("econ_exp_03", "economics", "finance", "explanation", "k12",
         "Generate a short educational video explaining compound interest: a $100 deposit "
         "growing at 10% per year for 3 years, showing each year's balance compounded "
         "on the previous one.",
         ["compound interest", "exponential growth"],
         ["year-by-year ledger", "growing stack of coins/bills", "balance numbers"],
         ["start $100", "year 1: $110", "year 2: $121", "year 3: $133.10"],
         "K-12 (grades 9-10)",
         ["each year compounds on the prior balance, not on the original $100",
          "final balance is approximately $133.10",
          "arithmetic correct at each step"]),
    case("econ_prob_01", "economics", "finance", "problem_solving", "undergrad",
         "Generate a video solving: 'A bond pays $50 per year for 10 years and $1000 at "
         "the end. If the discount rate is 5%, what is its present value?' Walk through "
         "the discounted-cash-flow approach (just enough to show structure, exact value "
         "approx $1000).",
         ["present value", "discounted cash flow", "bond pricing"],
         ["timeline of cash flows", "discount factors", "PV formula"],
         ["state cash flows ($50/yr + $1000 face)", "apply discount 1/(1.05)^t",
          "sum PVs", "answer ~$1000 (par-priced bond)"],
         "undergrad finance student",
         ["PV approximately matches par ($1000) since coupon = discount rate",
          "summation of discounted cash flows shown",
          "no negative or runaway numbers"]),
    case("econ_prob_02", "economics", "micro", "problem_solving", "k12",
         "Generate a video solving: 'A store sells 100 units at $20 each. The cost is "
         "$15 per unit. What is the total profit?' Show revenue, cost, and profit "
         "computation.",
         ["profit", "revenue", "cost"],
         ["revenue = 100*$20", "cost = 100*$15", "profit = R - C = $500"],
         ["compute revenue $2000", "compute cost $1500", "profit = 2000-1500 = $500"],
         "K-12 (grades 7-9)",
         ["final profit = $500", "arithmetic correct", "profit = revenue minus cost (not divided)"]),
]

# ============================================================================
# 10. SOCIAL STUDIES & CIVICS  (5 cases)
# ============================================================================
CASES += [
    case("civ_exp_01", "civics", "government", "explanation", "k12",
         "Generate a short educational video showing the three branches of the U.S. "
         "federal government (Legislative, Executive, Judicial) and how checks and "
         "balances connect them.",
         ["separation of powers", "checks and balances"],
         ["3 boxes labeled Legislative / Executive / Judicial", "arrows showing checks"],
         ["introduce 3 branches", "show legislative (Congress)", "executive (President)",
          "judicial (Supreme Court)", "draw checks arrows"],
         "K-12 (grades 8-10)",
         ["exactly 3 branches labeled correctly",
          "checks arrows go both ways (not one-way dictatorship)",
          "no extra fake branches"]),
    case("civ_exp_02", "civics", "elections", "explanation", "k12",
         "Generate a short educational video showing how a citizen votes in a polling "
         "station: walking in, checking in, marking a ballot, depositing it in a box.",
         ["voting process", "secret ballot", "democratic participation"],
         ["polling station", "voter", "ballot", "ballot box"],
         ["enter", "check in", "go to private booth", "mark ballot", "drop in box"],
         "K-12 (grades 5-8)",
         ["ballot is marked in private (booth)",
          "ballot goes into a sealed box",
          "process is orderly, no obvious anachronisms"]),
    case("civ_exp_03", "civics", "law_process", "explanation", "undergrad",
         "Generate a short educational video showing how a bill becomes a law in the U.S.: "
         "introduced in Congress, committee review, floor vote in both chambers, "
         "presidential signature.",
         ["legislative process", "Congress", "bicameralism", "presidential signature"],
         ["bill document", "Congress chamber", "vote tally", "President signing"],
         ["bill introduced", "committee", "House vote", "Senate vote", "President signs"],
         "undergrad political-science student",
         ["both chambers vote (House and Senate)",
          "President signs at the end (not at the start)",
          "order respects U.S. process"]),
    case("civ_prob_01", "civics", "elections", "problem_solving", "k12",
         "Generate a video solving an election problem: 'Candidate A got 1200 votes, "
         "candidate B got 800 votes. What percentage did A win?' Show fraction, "
         "percentage, and which candidate won.",
         ["percentage", "vote share"],
         ["vote totals", "fraction 1200/2000", "percent 60%", "winner labeled A"],
         ["sum total = 2000", "A's share = 1200/2000", "= 60%", "A wins"],
         "K-12 (grades 6-8)",
         ["A's share = 60% correct", "A is the winner", "total adds up to 2000"]),
    case("civ_prob_02", "civics", "government", "problem_solving", "undergrad",
         "Generate a video walking through a constitutional-amendment question: 'How "
         "many states are needed to ratify a U.S. constitutional amendment?' Explain "
         "the 3/4 rule and give the number out of 50.",
         ["constitutional amendment", "ratification", "3/4 of states"],
         ["U.S. map", "states highlighted", "number 38 of 50"],
         ["state the 3/4 rule", "compute 3/4 of 50 = 37.5", "round up to 38",
          "highlight 38 states"],
         "undergrad U.S.-government student",
         ["final answer = 38 states",
          "explanation cites Article V's 3/4 rule",
          "no factual error like 'majority' or 'all 50'"]),
]

# ============================================================================
# 11. LANGUAGE & LITERATURE  (5 cases)
# ============================================================================
CASES += [
    case("lang_exp_01", "language_literature", "grammar", "explanation", "k12",
         "Generate a short educational video explaining the difference between active "
         "and passive voice in English, using the sentences 'The cat chased the mouse' "
         "(active) and 'The mouse was chased by the cat' (passive). Highlight subject "
         "and object positions.",
         ["active voice", "passive voice", "subject-object swap"],
         ["both sentences shown on screen", "subject and object color-coded",
          "arrows showing the swap"],
         ["show active sentence", "label subject and object", "transform to passive",
          "show object becomes subject"],
         "K-12 (grades 7-9)",
         ["both sentences appear correctly", "subject/object labeling is consistent",
          "transformation is visually clear (positions swap)"]),
    case("lang_exp_02", "language_literature", "poetry", "explanation", "k12",
         "Generate a short educational video explaining iambic pentameter using the "
         "opening line of Shakespeare's Sonnet 18: 'Shall I compare thee to a summer's "
         "day?' Mark the 5 unstressed-stressed pairs.",
         ["iambic pentameter", "meter", "stressed/unstressed syllables"],
         ["text on screen", "syllables marked with u (unstressed) and / (stressed)",
          "groupings into 5 iambs"],
         ["display line", "mark syllables", "highlight 5 iambs"],
         "K-12 (grades 9-11)",
         ["exactly 5 stress patterns shown",
          "alternation is u/u/u/u/u/ (unstressed-stressed)",
          "text is accurate to Shakespeare's line"]),
    case("lang_exp_03", "language_literature", "literary_analysis", "explanation", "undergrad",
         "Generate a short educational video explaining what a metaphor is, contrasting "
         "with a simile, using examples 'Time is a thief' (metaphor) and 'Time is like "
         "a thief' (simile).",
         ["metaphor", "simile", "figurative language"],
         ["two example sentences", "labels metaphor and simile",
          "highlight the word 'like' in the simile"],
         ["display both sentences", "identify the difference (presence of 'like'/'as')",
          "label each correctly"],
         "undergrad literature student",
         ["metaphor labeled without 'like'", "simile labeled with 'like'",
          "no mislabeling"]),
    case("lang_prob_01", "language_literature", "grammar", "problem_solving", "k12",
         "Generate a video solving: 'Identify all nouns in the sentence: The brown dog "
         "ran quickly to the park.' Walk through each word and circle the nouns.",
         ["parts of speech", "noun identification"],
         ["sentence displayed", "each word highlighted in turn", "nouns circled"],
         ["display sentence", "evaluate each word", "circle 'dog' and 'park'",
          "state result"],
         "K-12 (grades 4-6)",
         ["exactly the nouns 'dog' and 'park' identified",
          "no false positives (e.g., 'brown' as noun)",
          "no missed nouns"]),
    case("lang_prob_02", "language_literature", "literary_analysis", "problem_solving", "undergrad",
         "Generate a video walking through identifying the theme of George Orwell's "
         "Animal Farm: 'Power corrupts.' Show key plot points and how they support the "
         "theme.",
         ["theme identification", "allegory", "political satire"],
         ["pigs taking over the farm scenes", "key plot moments captioned", "theme statement"],
         ["intro plot", "Snowball banishment", "pigs walking on two legs",
          "state theme: power corrupts"],
         "undergrad literature student",
         ["theme statement matches a recognized reading of Animal Farm",
          "supporting evidence drawn from the actual book",
          "no plot fabrication"]),
]

# ============================================================================
# 12. ART & MUSIC THEORY  (5 cases)
# ============================================================================
CASES += [
    case("art_exp_01", "art_music", "art_periods", "explanation", "k12",
         "Generate a short educational video contrasting Renaissance art (realistic "
         "perspective, classical themes) with Impressionist art (visible brushstrokes, "
         "outdoor light), showing one representative painting style for each.",
         ["Renaissance", "Impressionism", "art history periods"],
         ["one Renaissance-style scene", "one Impressionist-style scene", "labels"],
         ["show Renaissance painting style", "label features", "show Impressionist style", "label features"],
         "K-12 (grades 8-10)",
         ["the two styles are visibly different",
          "Renaissance side shows more linear/realistic style",
          "Impressionist side shows softer brushwork / outdoor light"]),
    case("art_exp_02", "art_music", "music_theory", "explanation", "undergrad",
         "Generate an educational video showing the C major scale on a piano keyboard, "
         "highlighting the 7 white keys C-D-E-F-G-A-B in order, with the whole-whole-"
         "half-whole-whole-whole-half step pattern annotated.",
         ["major scale", "whole and half steps", "key signatures"],
         ["piano keyboard with C major keys highlighted", "step pattern W-W-H-W-W-W-H labels"],
         ["highlight C", "step to D (W)", "to E (W)", "to F (H)", "to G (W)",
          "to A (W)", "to B (W)", "to C (H)"],
         "undergrad music-theory student",
         ["7 white keys correctly highlighted starting from C",
          "step pattern W-W-H-W-W-W-H accurate",
          "no black keys included in C major"]),
    case("art_exp_03", "art_music", "color_theory", "explanation", "k12",
         "Generate a short educational video showing the color wheel with primary colors "
         "(red, yellow, blue) and how mixing two primaries gives a secondary color "
         "(red+yellow=orange, yellow+blue=green, blue+red=purple).",
         ["color wheel", "primary colors", "secondary colors"],
         ["color wheel", "3 primary swatches", "3 mixing demonstrations"],
         ["show 3 primaries", "mix pairs", "show 3 secondaries", "place on color wheel"],
         "K-12 (grades 5-7)",
         ["red+yellow=orange (not brown or other)",
          "blue+yellow=green",
          "blue+red=purple"]),
    case("art_prob_01", "art_music", "music_theory", "problem_solving", "undergrad",
         "Generate a video solving: 'Build a C major triad. Which 3 notes does it "
         "contain?' Show piano keys and mark the root, third, and fifth.",
         ["triad construction", "root-third-fifth", "major chord"],
         ["piano keyboard", "C, E, G keys highlighted"],
         ["root C", "major third up to E", "perfect fifth up to G", "label as C major triad"],
         "undergrad music-theory student",
         ["exactly C, E, G highlighted",
          "intervals are major third + minor third",
          "named correctly as C major"]),
    case("art_prob_02", "art_music", "color_theory", "problem_solving", "k12",
         "Generate a video solving: 'Which two primary colors do I mix to get green?' "
         "Walk through the candidates and demonstrate mixing yellow and blue.",
         ["primary colors", "color mixing"],
         ["yellow paint", "blue paint", "mixing into green"],
         ["consider options", "select yellow + blue", "demonstrate mixing", "result is green"],
         "K-12 (grades 3-5)",
         ["correct answer yellow + blue = green",
          "no incorrect pair claimed to make green",
          "mixing demo visually produces green, not another color"]),
]


def main() -> None:
    out_path = Path(__file__).resolve().parent.parent / "data" / "prompts" / "pilot_v0_1.jsonl"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w") as f:
        for c in CASES:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    # Summary
    by_disc: dict[str, int] = {}
    by_task: dict[str, int] = {}
    by_diff: dict[str, int] = {}
    for c in CASES:
        by_disc[c["discipline"]] = by_disc.get(c["discipline"], 0) + 1
        by_task[c["task_type"]] = by_task.get(c["task_type"], 0) + 1
        by_diff[c["difficulty"]] = by_diff.get(c["difficulty"], 0) + 1
    print(f"Wrote {len(CASES)} prompts to {out_path}")
    print("By discipline:", by_disc)
    print("By task_type :", by_task)
    print("By difficulty:", by_diff)


if __name__ == "__main__":
    main()
