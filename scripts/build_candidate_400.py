"""Assemble a traceable 400-item research pool from existing prompt files.

This is a candidate pool, not a reviewed or redistributable benchmark release.
"""

from __future__ import annotations

from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parent.parent
PROMPTS = ROOT / "data" / "prompts"
OUT = PROMPTS / "candidate_400.jsonl"
REPORT = ROOT / "data" / "curated" / "candidate_400_report.json"
SOURCE_MANIFEST = ROOT / "data" / "curated" / "candidate_400_sources.jsonl"
REPLACEMENT_SOURCES = ROOT / "data" / "curated" / "candidate_400_replacement_sources.json"

# Retire long, underdetermined five-second drafts in favor of individually
# checked source tasks. Keep this mapping explicit for provenance review.
REPLACEMENTS = {
    "math_exp_01": "grade_math_math_95",
    "math_high_01": "grade_math_math_1",
    "phys_high_01": "grade_physics_task_68",
    "cs_high_01": "grade_ComputerScience_task_17",
    "bio_high_01": "disciplinegen_biology_cf797d51a318cd19",
    "cand_hs_civ_06": "grade_math_math_4",
    "bio_exp_01": "grade_biology_task_57",
    "phys_prob_02": "grade_physics_task_12",
    "disciplinegen_chemistry_055480afd7ffa6eb": "grade_chemistry_task_2",
    "disciplinegen_mathematics_2e453c1dd037c7a3": "grade_math_math_41",
    "disciplinegen_mathematics_78168b247580660d": "grade_math_math_40",
    "disciplinegen_biology_cf74ce3ea6ace9e5": "disciplinegen_biology_d463e086c0d85b7b",
}
GRADE_ADDITIONS = {
    "math_math_95": (
        "mathematics", "On the supplied graph, mark its three x-intercepts at x=-2, x=0, and x=1. Hold three points on the x-axis without changing the curve.",
        "zeros at -2, 0, and 1", "the graph crosses at -2 and 1 and touches the x-axis at 0; all three marked points have y=0"),
    "math_math_41": (
        "mathematics", "On the supplied coordinate grid, reflect the polygon across the y-axis x=0. Keep the original fixed and hold the copy with vertices (0,0), (−1,0), (−2,1), and (0,1).",
        "reflection across x=0", "each copied vertex is (−x,y) for its original vertex (x,y)"),
    "math_math_40": (
        "mathematics", "On the supplied grid, reflect the polygon through the origin. Keep the original fixed and hold the copy with vertices (0,0), (−1,0), (−2,−1), and (0,−1).",
        "central symmetry about (0,0)", "each copied vertex is (−x,−y) for its original vertex (x,y)"),
    "chemistry_task_2": (
        "chemistry", "In the supplied acid-catalyzed equation, fill the missing ester product as CH₃C(=O)OCH₂CH₃. Keep the existing H₂O coproduct and hold the balanced product side.",
        "ethyl acetate and water", "ethanol and acetic acid yield CH₃C(=O)OCH₂CH₃ plus H₂O; the ethyl group is attached through oxygen"),
    "biology_task_57": (
        "biology", "On the supplied thioglycolate tube, change growth from bottom-only to growth at all depths, densest near the oxygen-rich surface. Hold the tube with both upper and lower colonies visible.",
        "facultative anaerobe growth pattern", "growth occurs throughout the medium and is denser at the top, unlike an obligate anaerobe"),
    "physics_task_12": (
        "physics", "At point O in the supplied diagram, draw the reflected ray on the opposite side of the normal from the incoming ray. Mark 60° between reflected ray and normal and hold the outgoing arrow.",
        "law of reflection: reflected angle 60°", "reflected ray starts at O, points away from the surface, and makes 60° with the normal"),
    "math_math_4": (
        "mathematics", "On the supplied similar triangles, use the scale factor 14/7=2 to replace x with 10 and y with 18. Hold both values on their corresponding sides.",
        "x=10; y=18", "20/2=10 on the left side and 9×2=18 on the right side"),
    "math_math_1": (
        "mathematics", "On the supplied triangle, replace x on the lower slanted side with 5√13. Reveal 17²+6²=325 and hold the simplified radical.",
        "5√13", "the lower right triangle has perpendicular legs 17 and 6; x=√325=5√13"),
    "physics_task_68": (
        "physics", "On the supplied r-versus-B axes, replace the rising line with a decreasing first-quadrant curve for r=mv/(|q|B), with m, v, and |q| fixed. Hold both axes as asymptotes.",
        "r=mv/(|q|B)", "r is positive for B>0, decreases as 1/B, and touches neither axis"),
    "ComputerScience_task_17": (
        "computer_science", "On the supplied two-state Markov chain, fill S1→S2 with 0.8 and the S2 self-loop with 0.4. Hold both completed outgoing sums equal to 1.",
        "S1→S2=0.8; S2→S2=0.4", "0.2+0.8=1 for S1 and 0.6+0.4=1 for S2"),
}
DISCIPLINEGEN_ADDITIONS = {
    "cf797d51a318cd19": (
        "biology", "Draw one anticoagulated blood tube after centrifugation. Label the upper plasma ①, thin middle buffy coat ②, and lower red-cell layer ③. Hold the three layers in that order.",
        "centrifuged blood separates by density", "three labeled blood layers",
        "plasma above buffy coat above red blood cells; buffy coat contains white cells and platelets",
        "①, ②, and ③ point to the correct layers"),
    "d463e086c0d85b7b": (
        "biology", "Inside one somatic-cell nucleus, draw two homologous chromosomes with the same pigmentation locus. Label one allele B and the other b; hold the paired loci aligned.",
        "a heterozygote has different alleles at corresponding loci on homologous chromosomes",
        "two homologous chromosomes with aligned B and b locus labels",
        "B and b occupy the same locus on different homologues, not two positions on one chromosome",
        "no skin-color phenotype is inferred solely from chromosome shading"),
}

# Supplemental medicine drafts were authored as multi-stage lessons. Keep their
# IDs and provenance, but ask for one visible claim that can be checked in 5 s.
MEDICINE_REPAIRS = {
    "cand_med_cs_gap_01": ("On a vital-sign card, highlight blood pressure 88/54 mmHg and label it 'low blood pressure'. Hold that single finding without assigning a diagnosis.", "88/54 mmHg is a low adult blood-pressure reading; no disease is inferred"),
    "cand_med_cs_gap_02": ("Show insulin binding to a muscle-cell receptor, then one arrow showing glucose entering the cell. Hold the receptor and inward glucose arrow.", "insulin signaling supports glucose uptake into muscle cells; insulin is not itself glucose"),
    "cand_med_cs_gap_03": ("Show one arrow from the right ventricle through the pulmonary artery to the lungs. Hold the three labels and the direction of flow.", "the right ventricle pumps deoxygenated blood toward the lungs through the pulmonary artery"),
    "cand_med_cs_gap_04": ("Show a narrowed bronchial airway beside the same airway after an inhaled beta-2 agonist. Reveal one arrow showing smooth-muscle relaxation and wider lumen.", "a short-acting beta-2 agonist relaxes bronchial smooth muscle; the clip does not claim immediate removal of inflammation"),
    "cand_med_cs_gap_05": ("On an ECG strip marked at 25 mm/s, show two successive R peaks 10 small boxes apart. Reveal 0.40 s per beat and hold the calculated heart rate of 150/min. Do not name a rhythm from rate and QRS width alone.", "10 small boxes at 25 mm/s equal 0.40 s, giving 60/0.40=150 beats/min; rhythm diagnosis is not established"),
    "cand_med_cs_gap_06": ("Show a diagram with bacterial types A, B, and C. Highlight a hypothetical narrow-spectrum agent acting on A only, and hold B and C unmarked; label this as a schematic of coverage, not a treatment recommendation.", "the illustrated narrow spectrum covers A only in this stipulated example; it does not imply that all narrow-spectrum drugs have the same targets"),
    "cand_med_cs_gap_07": ("At one nephron tubule, draw a glucose arrow from filtrate back to surrounding blood and label the direction 'reabsorption'. Hold the two compartments and arrow.", "tubular reabsorption moves a substance from filtrate toward blood, not the reverse"),
    "cand_med_cs_gap_08": ("Show one face with a newly drooping side next to a clock icon. Reveal the label 'FAST: Face; seek urgent help' and hold the warning sign without diagnosing stroke.", "new facial droop is a FAST warning sign requiring urgent assessment, not a confirmed diagnosis"),
    "cand_med_cs_gap_09": ("Show a labeled memory B cell remaining after vaccination, then reveal an arrow toward a faster response on later matching-antigen exposure. Hold the memory-cell label.", "immune memory can support a faster response to a later matching antigen; protection is not instantaneous or universal"),
    "cand_med_cs_gap_10": ("Show two spirometry cards: A has a low FEV1/FVC ratio; B has a preserved ratio with low FVC. Label A 'obstructive pattern' and B 'possible restriction; confirm with lung volumes'.", "a low FEV1/FVC supports obstruction; low FVC with preserved ratio alone does not prove restriction"),
    "cand_med_cs_gap_11": ("Show pH 7.25, HCO3 10 mEq/L, and PaCO2 24 mmHg. Highlight the low bicarbonate, then hold 'primary metabolic acidosis'; do not infer an anion gap.", "low pH with low bicarbonate supports primary metabolic acidosis; PaCO2 alone does not determine anion gap"),
    "cand_med_cs_gap_12": ("Show two hemodynamic cards: A has low cardiac output and high systemic vascular resistance; B has high output and low resistance. Label only the contrasting flow-resistance patterns, without assigning a shock cause.", "low output with high resistance and high output with low resistance are distinct patterns; neither uniquely identifies a shock cause"),
    "cand_med_cs_gap_13": ("Show urine concentration 100 mg/L, flow 2 mL/min, and plasma concentration 4 mg/L. Substitute once into C=UV/P and hold clearance 50 mL/min.", "100 mg/L times 0.002 L/min divided by 4 mg/L equals 0.05 L/min or 50 mL/min"),
    "cand_med_cs_gap_14": ("Show an intrinsic-pathway arrow and a tissue-factor-pathway arrow converging at factor X. Hold factor X as their shared convergence point without drawing the full cascade.", "the intrinsic and tissue-factor pathways converge at activation of factor X in the simplified coagulation model"),
}
MEDICINE_VISUALS = {
    "cand_med_cs_gap_01": ["88/54 mmHg reading", "low blood-pressure label"],
    "cand_med_cs_gap_02": ["insulin receptor on muscle cell", "inward glucose arrow"],
    "cand_med_cs_gap_03": ["right ventricle", "pulmonary artery", "lungs and directional arrow"],
    "cand_med_cs_gap_04": ["narrowed airway", "relaxed smooth muscle", "wider airway lumen"],
    "cand_med_cs_gap_05": ["25 mm/s scale", "R peaks ten small boxes apart", "150/min result"],
    "cand_med_cs_gap_06": ["bacterial types A, B, C", "agent covering only A"],
    "cand_med_cs_gap_07": ["tubular filtrate", "surrounding blood", "outward reabsorption arrow"],
    "cand_med_cs_gap_08": ["one-sided facial droop", "clock icon", "FAST Face label"],
    "cand_med_cs_gap_09": ["memory B cell", "matching antigen", "later response arrow"],
    "cand_med_cs_gap_10": ["A and B spirometry cards", "FEV1/FVC and FVC values", "qualified pattern labels"],
    "cand_med_cs_gap_11": ["pH 7.25", "HCO3 10", "metabolic acidosis label"],
    "cand_med_cs_gap_12": ["two hemodynamic cards", "opposite output and resistance patterns"],
    "cand_med_cs_gap_13": ["U, V, and P values", "C=UV/P", "50 mL/min result"],
    "cand_med_cs_gap_14": ["two pathway arrows", "factor X convergence point"],
}
MEDICINE_DIFFICULTY_REPAIRS = {
    "cand_med_cs_gap_11": "medium",
    "cand_med_cs_gap_12": "medium",
    "cand_med_cs_gap_13": "medium",
    "cand_med_cs_gap_14": "medium",
}

# Exclude repeated music-measure templates and five near-identical soccer
# formation diagrams; use those slots for distinct subject tasks.
DROP_IDS = {
    "disciplinegen_sports_12ac8cd6e1a56581",
    "disciplinegen_sports_19a4eabd156f5bf0",
    "disciplinegen_sports_34c255cd54821563",
    "disciplinegen_sports_34ffec53916b1a0a",
    "disciplinegen_sports_generated_soccer_formation_dots",
    "disciplinegen_music_2ad2d505e0d64643",
    "disciplinegen_music_88c21d03e4201ffa",
    "disciplinegen_music_90251e36efa679df",
    "disciplinegen_music_c80ec38538b2694a",
    "disciplinegen_music_dc4a9194e2dafb28",
    "disciplinegen_music_e53863cafe1d34ff",
    "disciplinegen_music_e659c41c922d909c",
    "disciplinegen_music_ebc11b723e10ec2a",
    "disciplinegen_music_ec2f444553647eeb",
}
ARCHETYPE_REPAIRS = {
    "disciplinegen_biology_637de7c74ec514f2": (
        "spatial_reasoning", ["five labeled species at distinct trophic levels",
                              "directed energy-flow arrows attached to the correct species"]),
    "disciplinegen_biology_79da49549e98a464": (
        "labeling", ["one animal cell diagram", "unambiguous leader lines for each named structure"]),
    "disciplinegen_biology_ce413ce67a202d21": (
        "labeling", ["one neuron diagram", "distinct labels for cell body, axon, dendrites, and terminals"]),
}
EXTRA_IDS = (
    *(f"cand_med_cs_gap_{i:02d}" for i in range(1, 15)),
    *(f"cand_hs_civ_{i:02d}" for i in range(1, 7)),
    *(f"cand_hs_lang_{i:02d}" for i in range(1, 7)),
    *(f"cand_hs_art_{i:02d}" for i in range(1, 7)),
)

SOURCE_TEXT_REPAIRS = {
    "grade_computerscience_task_33": (
        "question_the imagey", "question image by",
    ),
}
SOURCE_TARGET_REJECTIONS = {
    "grade_biology_task_22": "target rearranges source-stage pictures although the task asks only to add arrows",
    "grade_biology_task_24": "target adds an unrelated microfilament label along with the three requested mitochondria",
}
DIFFICULTY_REPAIRS = {
    "med_prob_01": "low", "med_prob_02": "medium",
    "chem_high_02": "medium", "bio_high_02": "medium",
    "econ_high_02": "low",
    "chem_high_01": "medium", "econ_high_01": "medium",
    "geo_high_02": "low", "lang_high_02": "medium",
    "civ_high_01": "low", "civ_high_02": "medium",
    "art_high_01": "low", "art_high_02": "low",
}
HISTORY_REPAIRS = {
    "grade_his_task_16": (
        "Explain the Zoroastrian contrast between asha (truth and order) and druj (falsehood and disorder). Show the two labeled ideas, then reveal one choice aligned with asha.",
        "asha and druj are contrasting ethical concepts", "the two concepts are labeled distinctly", "asha is not labeled as falsehood"),
    "grade_his_task_17": (
        "Explain the Buddhist Middle Way as a rejection of both luxury and severe self-denial. Show the two extremes on opposite sides and reveal the middle path between them.",
        "the Middle Way avoids both extremes", "both extremes and the middle path are shown", "the Middle Way is not equated with either extreme"),
    "grade_his_task_18": (
        "Contrast the ancient Olympic Games at Olympia with the modern international Olympics. Show Olympia as one origin point, then reveal a world map with many participating regions.",
        "the ancient games were held at Olympia while modern games are international", "Olympia and the wider modern map are distinct", "ancient games are not portrayed as a global event"),
    "grade_his_task_19": (
        "Show one Maya glyph with a logographic reading and a separate syllabic glyph. Animate the two roles as a contrast and end with the label 'logosyllabic writing'.",
        "Maya writing uses logographic and syllabic signs", "both sign functions are distinguished", "no claim that all glyphs are alphabetic"),
    "grade_his_task_20": (
        "Explain how archaeobotanists infer sorghum domestication. Show wild and domesticated seed heads side by side, highlight one observable trait, and label it as evidence rather than an exact invention date.",
        "domestication is inferred from plant remains", "one trait is compared visibly", "no exact first-domestication year is asserted"),
    "grade_his_task_21": (
        "Explain the difference between Palmyra's expansion under Zenobia and Roman reconquest. On a labeled regional map, reveal Palmyrene control first and Roman reconquest second, then hold the changed boundary.",
        "Palmyrene expansion preceded Roman reconquest", "map states are in the correct order", "Palmyra and Rome are identified"),
    "grade_his_task_22": (
        "Explain one feature of Indus urban planning. Start with a simple street grid, reveal a covered drainage channel beside a street, and label how the drain connects to the built layout.",
        "Indus cities used planned streets and drainage", "drain is attached to the street layout", "no precise emergence year is asserted"),
}
ATOMIC_PILOT_REPAIRS = {
    "chem_high_01": (
        "On a tetrahedral carbon bearing a leaving group, show a nucleophile approaching from the opposite side of that group. Hold the backside approach arrow and the leaving-group bond on opposite sides; label this SN2 attack.",
        "SN2 substitution begins with backside attack", "the approach is opposite the leaving group, not from the same side"),
    "econ_high_01": (
        "Show a two-player prisoner's-dilemma payoff matrix with (C,C)=(3,3), (C,D)=(0,5), (D,C)=(5,0), and (D,D)=(1,1). Highlight only (D,D) as the Nash equilibrium.",
        "defection is each player's best response to either choice", "the highlighted cell is (D,D)=(1,1), not (C,C)"),
    "geo_high_02": (
        "On a labeled Eurasian map, shade the inland Heartland region described by Mackinder. Hold the shaded interior distinct from the surrounding coastal zones; label this as a historical geopolitical model.",
        "Mackinder's Heartland refers to the Eurasian interior", "the shaded area is inland Eurasia, not all of Eurasia or a claim of inevitable world control"),
    "lang_high_02": (
        "Show the written word 'sign' beside two related words, 'signal' and 'signature'. Reveal one arrow from 'sign' to its neighboring terms and label the relation 'meaning through differences'.",
        "one aspect of Derrida's differance is meaning through relations among signs", "the clip illustrates relational difference without claiming that the three words have identical meanings"),
    "civ_high_01": (
        "Show a U.S. statute and the Constitution side by side. Reveal an arrow from a court to the statute labeled 'judicial review' and hold the rule that a conflicting statute may be invalidated.",
        "Marbury v. Madison established judicial review of laws for constitutional conflict", "the court reviews the law against the Constitution, not against the judge's preference"),
    "civ_high_02": (
        "Show NATO's 1949 founding in one labeled timeline box. Add one arrow labeled 'collective defense' from member states toward a shared security commitment; hold the Article 5 idea without claiming automatic war.",
        "NATO's founding treaty includes a collective-defense commitment", "the diagram does not equate an armed attack with automatic identical military action by every member"),
    "art_high_01": (
        "Show a four-note excerpt C, E, F-sharp, B. Reverse the displayed order to B, F-sharp, E, C and label that single operation 'retrograde'.",
        "retrograde reverses pitch order in a tone row", "the final order is B, F-sharp, E, C; pitch values are not inverted"),
    "art_high_02": (
        "Show a neutral outline of a found object moving from an everyday-use box to a gallery-context box. Hold the label 'readymade: context and selection' next to Duchamp's Fountain (1917).",
        "Fountain is a readymade associated with Duchamp", "the object is presented as selected and recontextualized, not sculpted from raw material"),
    "art_exp_02": (
        "On one piano octave, highlight C,D,E,F,G,A,B and the upper C. Mark only the E–F and B–C semitone gaps; hold the completed C-major pattern.",
        "C major uses the natural-note sequence with semitones E–F and B–C", "all eight octave notes are ordered and only E–F and B–C are marked as half steps"),
    "math_high_02": (
        "Show the middle-third Cantor construction as a removed-length sum 1/3+2/9+4/27+…=1. Hold the conclusion that the remaining set has Lebesgue measure 0.",
        "the removed intervals have total length one", "the geometric series sums to 1, so 1−1=0 measure remains"),
    "phys_high_02": (
        "Plot the Maxwell–Boltzmann speed density f(v)∝v²exp[−mv²/(2kT)] for v≥0. Mark its peak at vₚ=√(2kT/m) and hold the labeled curve.",
        "the v² factor and exponential determine the most probable speed", "the plotted peak is at √(2kT/m), not at zero"),
    "chem_high_02": (
        "Show ΔH°=−92 kJ/mol, ΔS°=−0.198 kJ/(mol·K), and T=298 K. Substitute once into ΔG°=ΔH°−TΔS° and hold ΔG°=−32.996 kJ/mol.",
        "Gibbs energy uses consistent kJ units", "−92−298(−0.198)=−32.996 kJ/mol, which is negative"),
    "bio_high_02": (
        "Show recessive genotype frequency q²=0.09. Reveal q=0.30, p=0.70, then hold the heterozygote frequency 2pq=0.42.",
        "Hardy–Weinberg frequencies satisfy p+q=1 and heterozygotes have frequency 2pq", "q=0.30, p=0.70, and 2pq=0.42"),
    "econ_high_02": (
        "With V and Q fixed in MV=PQ, show M rising from 100 to 110 units. Reveal P rising from index 100 to 110 and hold the 10% price-level increase.",
        "with fixed velocity and real output, price is proportional to money supply", "a 10% rise in M gives a 10% rise in P under the stated assumptions"),
    "geo_high_01": (
        "On an equatorial map section, show northern and southern trade winds meeting at the ITCZ. Draw one rising moist-air arrow and one rain cloud above the convergence zone.",
        "surface convergence at the ITCZ supports rising moist air and convection", "trade-wind arrows converge at the surface and the ascent arrow points upward"),
    "hist_high_01": (
        "Show three nested time bands labeled Braudel: longue durée (centuries), conjoncture (decades), and événement (short event). Hold the bands in order from longest to shortest.",
        "Braudel distinguished long structures, medium cycles, and short events", "centuries, decades, and event scale are assigned to the correct bands"),
    "math_prob_02": (
        "Show f(x)=x³+2x. Apply the power rule to each term and hold f′(x)=3x²+2.",
        "the derivative of x³+2x is 3x²+2", "x³ becomes 3x² and 2x becomes 2"),
    "phys_exp_03": (
        "In a beaker heated from below, show one warm parcel rising at the center and a cooler parcel sinking at the side. Hold a single closed convection arrow loop.",
        "heated water is less dense and rises while cooler water sinks", "arrows rise over the heat source and descend away from it"),
    "med_exp_02": (
        "At one heart-cell beta receptor, show a beta blocker occupying the binding site so adrenaline cannot bind. Hold the blocked receptor and label the reduced stimulation.",
        "a beta blocker antagonizes beta-adrenergic receptor activation", "blocker and adrenaline do not occupy the same site simultaneously"),
    "geo_exp_01": (
        "Show a cloud over land releasing rain into a river that flows to the sea. Hold only this precipitation-to-runoff leg of the water cycle with arrows in the correct direction.",
        "precipitation over land can feed runoff to the sea", "rain arrow points down and river arrow points toward the sea"),
    "geo_exp_03": (
        "Over a warm ocean, show moist air spiraling inward and rising around one low-pressure center. Hold a top-view storm with a clear central eye.",
        "tropical cyclones draw warm moist air inward toward low pressure", "inward spiral and eye are distinct; no outward surface inflow"),
    "civ_exp_01": (
        "Show Congress passing a bill and a president vetoing it. Hold two labeled boxes, Legislative and Executive, joined by the veto arrow as one example of checks and balances.",
        "the U.S. president can veto legislation passed by Congress", "the veto arrow runs from president to the bill, not from the judiciary"),
    "civ_exp_02": (
        "At a generic polling station, show a voter marking a ballot privately and placing it in a ballot box. Hold the completed deposit without showing a marked choice to bystanders.",
        "a secret ballot keeps the voter's choice private", "the marked ballot enters the box without revealing the selection"),
    "civ_exp_03": (
        "Show one U.S. bill approved by both chambers of Congress, then an arrow to the president's signature. Hold the signed bill labeled law, with the two chamber approvals visible.",
        "ordinary federal legislation is presented to the president after both chambers pass it", "both chambers precede the presidential signature; signature is not a committee vote"),
    "phys_prob_01": (
        "Show a 2 kg block on a frictionless floor with a 10 N horizontal force. Reveal F=ma, substitute 10=2a, and hold a=5 m/s².",
        "Newton's second law gives a=F/m", "10 N / 2 kg = 5 m/s²"),
    "chem_exp_01": (
        "Show one electron moving from neutral Na to neutral Cl. Label the resulting Na⁺ and Cl⁻ ions and hold their opposite charges side by side.",
        "sodium transfers an electron to chlorine", "Na⁺ and Cl⁻ have the correct charge signs"),
    "cs_exp_02": (
        "Show stack [A,B,C] with C at the top. Perform one pop and reveal C as the removed item while A and B remain in the stack.",
        "a stack removes its last pushed item first", "C is removed and A,B remain in order"),
    "cs_prob_01": (
        "Show two nested loops, each running n times. Reveal one n×n iteration grid and label the total work Θ(n²).",
        "nested n-by-n loops perform n² iterations", "grid has n rows and n columns"),
    "econ_exp_01": (
        "Start with supply S and demand D crossing at E₀. Shift only demand to D₁ on the same price–quantity axes; mark the new intersection E₁ at higher price and quantity.",
        "a rightward demand shift raises equilibrium price and quantity with supply fixed", "S is unchanged and E₁ is up and right of E₀"),
    "bio_exp_03": (
        "Show blood leaving the right ventricle blue, passing through the lungs, then returning to the left atrium red. Hold the two labeled chambers and lung connection.",
        "pulmonary circulation oxygenates blood", "right ventricle to lungs to left atrium is the correct direction"),
}
ATOMIC_VISUALS = {
    "chem_high_01": ["tetrahedral carbon", "leaving group", "opposite-side approach arrow"],
    "econ_high_01": ["four payoff cells", "C and D row and column labels", "highlighted (D,D) cell"],
    "geo_high_02": ["labeled Eurasian map", "shaded inland region", "coastal areas left distinct"],
    "lang_high_02": ["three written words", "relation arrow", "meaning-through-difference label"],
    "civ_high_01": ["Constitution", "statute", "court review arrow"],
    "civ_high_02": ["1949 founding date", "member states", "collective-defense arrow"],
    "art_high_01": ["original four notes", "reversed four notes", "retrograde label"],
    "art_high_02": ["found object", "everyday-use context", "gallery context"],
    "art_exp_02": ["one piano octave", "eight natural notes", "two marked semitone gaps"],
    "math_high_02": ["middle-third removal", "removed-length series", "zero remaining measure"],
    "phys_high_02": ["speed-density curve", "v² exponential formula", "peak at vₚ"],
    "chem_high_02": ["three given quantities", "unit conversion", "−32.996 kJ/mol result"],
    "bio_high_02": ["q²=0.09", "p and q values", "2pq=0.42"],
    "econ_high_02": ["MV=PQ", "fixed V and Q", "100-to-110 index change"],
    "geo_high_01": ["converging trade winds", "rising moist air", "ITCZ rain cloud"],
    "hist_high_01": ["three time bands", "Braudel labels", "long-to-short order"],
    "math_prob_02": ["f(x)=x³+2x", "power-rule substitutions", "f′(x)=3x²+2"],
    "phys_exp_03": ["beaker and heater", "upward warm arrow", "downward cool arrow"],
    "med_exp_02": ["one beta receptor", "bound blocker", "excluded adrenaline"],
    "geo_exp_01": ["rain over land", "river", "sea-directed runoff arrow"],
    "geo_exp_03": ["warm ocean", "inward rising air", "storm eye"],
    "civ_exp_01": ["Congress bill", "presidential veto", "two branch labels"],
    "civ_exp_02": ["private marked ballot", "ballot box", "unrevealed choice"],
    "civ_exp_03": ["House and Senate approvals", "presidential signature", "law label"],
    "phys_prob_01": ["2 kg block", "10 N force arrow", "F=ma and a=5 m/s²"],
    "chem_exp_01": ["Na and Cl atoms", "one moving electron", "Na⁺ and Cl⁻ final labels"],
    "cs_exp_02": ["stack [A,B,C]", "C removed", "A,B remain"],
    "cs_prob_01": ["nested loop code", "n by n grid", "Θ(n²) total"],
    "econ_exp_01": ["labeled price–quantity axes", "fixed supply S", "D₀ and D₁ with E₀ and E₁"],
    "bio_exp_03": ["right ventricle", "lungs", "left atrium", "blue-to-red flow"],
}
HEAP_REPAIRS = {
    "disciplinegen_computer_science_a40d5924f269867b": (
        "Min-heap [11,43,69,91,64]: insert 88 as the next leaf. Its parent is 69, so no sift is needed. Hold [11,43,69,91,64,88].",
        "min-heap insertion", "the final array is [11,43,69,91,64,88]"),
    "disciplinegen_computer_science_b2e601bd851dd0eb": (
        "Max-heap [73,47,37,1]: remove 73, move 1 to the root, then swap it with 47. Hold [47,1,37].",
        "max-heap extraction and sift-down", "the final array is [47,1,37]"),
    "disciplinegen_computer_science_d46008cac268401f": (
        "Max-heap [86,61,20,14]: insert 99 as the next leaf, swap with 61, then with 86. Hold [99,86,20,14,61].",
        "max-heap insertion and sift-up", "the final array is [99,86,20,14,61]"),
}
DISCIPLINEGEN_FACT_REPAIRS = {
    "disciplinegen_mathematics_808f97bb9ff53cb7": (
        "Draw circle U with chords CM and NF crossing at Y. Mark CY=0.29 and NY=0.64 on their respective segments. Hold the intersection diagram without inventing the other segment lengths.",
        "the intersecting-chords relation is CY·YM=NY·YF", "Y lies inside the circle on both chords; CY and NY carry the stated lengths", "the two given lengths alone do not determine YM or YF"),
    "disciplinegen_music_0212b4bf0465225e": (
        "On a treble-clef staff in 4/4, place one B5 quarter note with ff directly beneath it. Hold that single beat and mark the other three beats as unfilled, rather than presenting it as a complete measure.",
        "a quarter note occupies one of four quarter-note beats in 4/4", "B5 quarter note and ff marking aligned beneath it", "one quarter note alone is not a complete 4/4 measure"),
    "disciplinegen_music_832360267f7f1afd": (
        "On a bass-clef staff in B major and 3/4, show one bar with B3 half note, G♯3 eighth, E3 sixteenth, and A♯3 sixteenth. Hold the bar with a 2+½+¼+¼=3 beat count.",
        "one 3/4 bar totals three quarter-note beats", "B3 half, G♯3 eighth, E3 sixteenth, A♯3 sixteenth", "durations sum to three beats and A♯ is in the B-major key signature"),
    "disciplinegen_physics_2a15135dda575b73": (
        "Draw an ideal 10:1 transformer with AC source u on the primary. Across the secondary rails, draw three parallel branches: R1 alone, R2 alone, and R3 in series with capacitor C. Hold the labeled topology.",
        "an ideal 10:1 transformer has ten primary turns per secondary turn", "secondary branches R1, R2, and series R3–C share the same two nodes", "R3 and C share one branch; R1 and R2 are not placed in series"),
    "disciplinegen_biology_27714bd42547f185": (
        "Show reference genes a–b–c–d. Below it, reveal mutant ① as a–b–[deleted c]–d, mutant ② as [deleted a]–b–c–d, and mutant ③ as a–[deleted b]–c–d. Hold the aligned four-position rows.",
        "a deletion removes a specified gene without reordering the others", "four aligned gene positions in reference and three mutants", "only c, a, and b are absent in mutants ①, ②, and ③ respectively; d remains present"),
    "disciplinegen_mathematics_1ace1e12820c6491": (
        "On coordinate axes, plot (−2,0) and (0,−2). Draw the line through them and label its equation y=−x−2. Hold both intercepts and the equation.",
        "the line through (−2,0) and (0,−2) has slope −1", "both plotted intercepts and line y=−x−2", "substituting either point satisfies y=−x−2"),
    "disciplinegen_physics_b119c60de20e2d71": (
        "Draw one loop with a source, ammeter A, fixed resistor R1, and variable resistor R2 in series. Add voltmeter V1 across only R1 and V2 across only R2; hold the completed circuit.",
        "an ammeter measures series current and voltmeters measure component voltage in parallel", "A in the main loop; V1 across R1; V2 across R2", "neither voltmeter is inserted in series and neither spans both resistors"),
    "disciplinegen_physics_bc4a12fab626e154": (
        "Draw one loop with source, switch S, ammeter A, sliding rheostat R1, and fixed resistor R2 in series. Connect voltmeter V only across R2 and hold the completed circuit.",
        "series components share loop current while a voltmeter spans its measured component", "S, A, R1, R2 in the main loop and V across R2", "V is not in the main series loop and does not span R1"),
    "disciplinegen_biology_834d184294c39985": (
        "Draw two separate open polypeptide lines A and B and one closed polypeptide loop C. Add exactly two labeled S–S bridges: A to C and C to B. Hold the topology without implying peptide bonds between the three chains.",
        "disulfide bridges can connect distinct polypeptide chains", "two open chains, one closed loop, and exactly two S–S bridges", "A–C and C–B are disulfide links; the loop is closed by its own peptide backbone"),
    "disciplinegen_biology_a0c5194f49b57fea": (
        "In one mitotic cell, show diffuse chromatin becoming two visible duplicated chromosomes during prophase. Label each centromere and hold the condensed chromosomes inside a breaking nuclear envelope.",
        "prophase includes chromosome condensation and nuclear-envelope breakdown", "two duplicated chromosomes with centromeres and a breaking envelope", "sister chromatids remain joined at each centromere; they do not separate in prophase"),
    "disciplinegen_biology_ed3f36ac8bfdaf80": (
        "Show one peach cross-section. Label the seed inside the hard endocarp, then bracket the exocarp, fleshy mesocarp, and endocarp together as the pericarp. Hold the nested layers.",
        "peach pericarp has exocarp, mesocarp, and endocarp around the seed", "seed inside stone; outer skin, flesh, and hard endocarp labeled", "the hard stone is endocarp, not the seed itself"),
    "disciplinegen_computer_science_27f32f9c77631fac": (
        "Show the Grover diffusion circuit on n qubits as H⊗n, phase flip of |0…0⟩, H⊗n. Label the zero-state phase gate 2|0…0⟩⟨0…0|−I and hold the equivalent operator 2|s⟩⟨s|−I, where |s⟩=H⊗n|0…0⟩.",
        "Grover diffusion reflects amplitudes about the uniform superposition", "H⊗n, zero-state phase gate, H⊗n in that order", "the resulting operator is 2|s⟩⟨s|−I up to a global phase"),
    "disciplinegen_computer_science_4c561e063547ee73": (
        "Fill one 4×4 grid row by row: 0001, 0101, 0100, 0000. Color 0 black and 1 white; hold the completed grid with exactly three white cells.",
        "binary pixels map 0 to black and 1 to white", "four rows 0001 / 0101 / 0100 / 0000", "only cells (0,3), (1,1), and (1,3) are white"),
    "disciplinegen_computer_science_e296d3f109abced1": (
        "Show a 2-bit decoder with inputs X,Y and four outputs. Reveal F1=¬X∧¬Y, F2=¬X∧Y, F3=X∧¬Y, F4=X∧Y, then hold the four labeled AND gates.",
        "each decoder output selects one input combination", "four AND outputs and inverted X,Y lines", "F1,F2,F3,F4 are active for 00,01,10,11 respectively"),
    "disciplinegen_physics_3df388cfbe3545a0": (
        "Show a cube of side L centered at the origin. Reveal its two x-normal faces at x=−L/2 and x=+L/2, then label the distance between them L.",
        "a centered cube of side L has x faces at ±L/2", "x=−L/2 and x=+L/2", "the face separation is L"),
    "disciplinegen_physics_b3612167a11a8e53": (
        "Show a cube with one resistor on each of its 12 edges. Mark opposite vertices A and B, then highlight one actual cube edge as R₁. Do not draw a direct edge from A to B.",
        "opposite cube vertices are not adjacent", "A and B are opposite corners; R₁ is on one cube edge", "there is no direct edge between A and B"),
    "disciplinegen_geography_c9a3377ba4d92309": (
        "Show a cutaway of Earth. Label the crust as the thin outermost shell and the lithosphere as the rigid outer shell including crust and uppermost mantle. Keep the deeper mantle and core inside.",
        "the lithosphere includes the crust and uppermost mantle", "crust is outermost and thinner than lithosphere", "the crust is not shown as a small central circle"),
    "disciplinegen_chemistry_92d1b4b062ce0eff": (
        "Draw the valid four-carbon structure CF₃–CH₂–CH=CH₂. Reveal the terminal C=C bond, then label the CF₃ group at the opposite end. Hold the skeletal formula.",
        "CF₃–CH₂–CH=CH₂ is a terminal alkene with one trifluoromethyl end", "CF₃–CH₂–CH=CH₂", "no carbon exceeds valence four"),
    "disciplinegen_music_6a04a0734f94075b": (
        "On a bass-clef staff in G major and 4/4, build one complete measure: dotted-quarter C5, eighth B4, then half A4. Show 1½+½+2=4 beats under the notes.",
        "a 4/4 measure totals four quarter-note beats", "C5 dotted quarter, B4 eighth, A4 half", "the durations sum to four beats"),
    "disciplinegen_chemistry_4f1bae22d9795083": (
        "Draw benzoylhydrazide Ph–C(=O)–NH–NH₂, then replace one terminal N–H with a para-methoxyphenyl group. Hold Ph–C(=O)–NH–NH–C₆H₄–OCH₃ with the methoxy at the para position.",
        "N′-(4-methoxyphenyl)benzoylhydrazide substitutes the terminal hydrazide nitrogen", "Ph–C(=O)–NH–NH–C₆H₄–OCH₃", "the N–N bond and para methoxy placement are preserved"),
    "disciplinegen_chemistry_c9bc0cd452324a2a": (
        "Start with a benzimidazole ring. Add a methyl group at C2 and a –C(=O)–NH–NH₂ group at C5. Hold the labeled 2-methylbenzimidazole-5-carbohydrazide structure.",
        "2-methylbenzimidazole-5-carbohydrazide has methyl at C2 and carbohydrazide at C5", "C2–CH₃ and C5–C(=O)–NH–NH₂", "the substituents attach at C2 and C5, not to ring nitrogens"),
    "disciplinegen_chemistry_3bcd4ee6511b0b2d": (
        "Show an aniline ring with NH₂ at position 1. Attach a 1H-indazol-3-yl group at position 3 of that ring, then label the meta relation between NH₂ and the new bond.",
        "3-(1H-indazol-3-yl)aniline has a meta-substituted aniline ring", "NH₂ at aniline C1 and indazol-3-yl at C3", "the two aniline substituents are meta, not ortho or para"),
    "disciplinegen_mathematics_5d2a93904a350e35": (
        "From one external point X, draw two tangents XW and XY to a circle. Label XW=2x+3 and XY=5x−6. Set them equal, solve x=3, then replace both lengths with 9.",
        "tangents from one external point have equal lengths", "2x+3=5x−6; x=3; XW=XY=9", "both final tangent lengths are 9"),
    "disciplinegen_mathematics_810e253bdc5e3ed0": (
        "Draw three parallel lines cutting two transversals. On the left, corresponding segments are 2x+3 and 6−x; on the right they are 2y and 6. Show x=1, so the left segments are both 5, then infer 2y=6 and y=3.",
        "equal intercepts on one transversal imply equal corresponding intercepts on another", "x=1 and y=3", "2y is replaced by 6"),
    "disciplinegen_music_190d634715411b6f": (
        "On a treble-clef staff in 2/2, reveal one complete measure: dotted eighth B4, sixteenth C5, dotted eighth D5, sixteenth E5, quarter F5, dotted eighth E5, sixteenth D5. Hold a 4-beat count below the bar.",
        "one 2/2 measure contains four quarter-note beats", "B4 C5 D5 E5 F5 E5 D5 with the stated durations", "durations sum to 4 quarter-note beats"),
    "disciplinegen_music_e78ae729e4ac569a": (
        "On a treble-clef staff, show the A♯ suspended-second chord A♯–B♯–E♯, then move E♯ to the bass for second inversion. Hold E♯–A♯–B♯ as whole notes in one 4/4 measure.",
        "A♯sus2 replaces the third with B♯ and has E♯ as its fifth", "E♯ is the bass below A♯ and B♯", "second inversion places the fifth in the bass"),
    "disciplinegen_geography_a2c1b9b869ca9c5e": (
        "Show a globe with seven meridians from 20°W to 160°E at 30° intervals. Reveal labels 20°W, 10°E, 40°E, 70°E, 100°E, 130°E, 160°E; mark the middle meridian 70°E as A.",
        "seven meridians spanning 180° have six 30° gaps", "20°W through 160°E at 30° intervals", "A labels 70°E, the fourth meridian"),
}


def read_rows(name: str) -> list[dict]:
    path = PROMPTS / name
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def source_additions() -> list[dict]:
    selected = json.loads(REPLACEMENT_SOURCES.read_text(encoding="utf-8"))
    grade_records = {item["task_id"]: item for item in selected["grade"]}
    dg_records = {item["_source_key"]: item for item in selected["disciplinegen"]}
    rows = []
    for source_id, (discipline, instruction, answer, truth) in GRADE_ADDITIONS.items():
        item = grade_records[source_id]
        if not item.get("image_path") or not item.get("gt") or not item.get("questions"):
            raise ValueError(f"GRADE source incomplete: {source_id}")
        rows.append({
            "id": f"grade_{source_id}", "discipline": discipline, "task_type": "problem_solving",
            "difficulty": "medium", "prompt_text": "Create a five-second teaching clip. " + instruction,
            "expected_concepts": [answer], "expected_visual_elements": [answer, truth],
            "expected_narrative_order": ["show source image", "reveal one answer", "hold result"],
            "discipline_specific_rubric": [truth, "the original diagram remains identifiable"],
            "audio_narration_required": False, "target_duration_s": 5,
            "source": {"dataset": "GRADE", "source_id": source_id,
                       "source_url": "https://huggingface.co/datasets/VisionXLab/GRADE",
                       "source_image_path": item["image_path"], "target_image_path": item["gt"],
                       "original_instruction": item["text"], "original_questions": item["questions"],
                       "license_status": "unverified"},
            "curation": {"status": "draft_needs_subject_review",
                         "quality_flags": ["source_verified_replacement"],
                         "visual_pair_screening": {"status": "manually_checked", "method": "before/gt inspection"}},
        })
    for source_id, (discipline, instruction, concept, visual, truth, failure) in DISCIPLINEGEN_ADDITIONS.items():
        item = dg_records[source_id]
        source_text = json.loads(item["conversations"])[0]["value"]
        rows.append({
            "id": f"disciplinegen_{discipline}_{source_id}", "discipline": discipline,
            "task_type": "explanation", "difficulty": "low",
            "prompt_text": "Create a five-second educational clip from this written brief. " + instruction,
            "expected_concepts": [concept], "expected_visual_elements": [visual],
            "expected_narrative_order": ["show source concept", "reveal labels", "hold final diagram"],
            "discipline_specific_rubric": [truth, failure],
            "audio_narration_required": False, "target_duration_s": 5,
            "source": {"dataset": "DisciplineGen-1M", "source_id": source_id,
                       "source_url": "https://huggingface.co/datasets/VisionXLab/DisciplineGen-1M",
                       "source_file": item["_source_file"], "row_group": item["_row_group"],
                       "row_index": item["_row_index"], "original_annotation": source_text,
                       "license_status": "verified_redistributable", "license": "CC BY 4.0"},
            "curation": {"status": "draft_needs_subject_review",
                         "quality_flags": ["source_verified_replacement"],
                         "prompt_focus": "text_only_source_brief"},
        })
    return rows


def focus_multisource(row: dict) -> dict:
    """Remove generic template text only when the complete source fits.

    Long source records keep their full original prompt and are held for manual
    scoping; truncating them could silently change the correct answer.
    """
    row = deepcopy(row)
    source = row["source"]
    instruction = source.get("original_instruction") or source.get("original_annotation") or ""
    flags = []
    if "<image>" in instruction and source.get("dataset") == "DisciplineGen-1M":
        instruction = instruction.replace("<image>", "").strip()
        flags.append("unresolved_image_token_removed_from_text_prompt")
    if row["id"] in SOURCE_TEXT_REPAIRS:
        old, new = SOURCE_TEXT_REPAIRS[row["id"]]
        if old not in instruction:
            raise ValueError(f"Source text repair no longer matches: {row['id']}")
        instruction = instruction.replace(old, new)
        flags.append("source_instruction_typo_repaired_in_prompt")
    if len(instruction) <= 300 and instruction.strip():
        row["original_prompt_text"] = row["prompt_text"]
        if source.get("dataset") == "DisciplineGen-1M" and not source.get("local_before_path"):
            row["prompt_text"] = (
                "Create a five-second educational clip from this written brief. "
                f"Show one clear visual result: {instruction.strip()} "
                "Reveal the required elements in order, then hold the final diagram for inspection."
            )
            row["expected_visual_elements"] = [instruction.strip()]
            row["expected_narrative_order"] = [
                "introduce the visual target", "reveal the required elements", "hold the final diagram",
            ]
            row["curation"]["prompt_focus"] = "text_only_source_brief"
        else:
            row["prompt_text"] = (
                "Create a five-second teaching clip using the supplied source image. "
                f"Show one checkable visual change: {instruction.strip()} "
                "Keep unrelated content fixed and hold the result for inspection."
            )
            row["curation"]["prompt_focus"] = "source_instruction_complete"
        row["expected_concepts"] = [f"Source-defined target: {instruction.strip()}"]
        if row["curation"]["prompt_focus"] == "source_instruction_complete":
            row["expected_narrative_order"] = [
                "Show the unchanged source state", "Make the requested visual change",
                "Hold the resulting state for inspection",
            ]
    else:
        flags.append("manual_atomic_scope_required")
        row["curation"]["prompt_focus"] = "original_full_instruction_preserved"
    if len(instruction) > 300:
        flags.append("source_instruction_over_300_chars")
    if len(row["prompt_text"]) > 500:
        flags.append("prompt_over_500_chars")
    if row["curation"].get("pedagogical_archetype") == "comparison" and not re.search(
        r"compar|versus|\bvs\b|differ|two cases", instruction, re.I
    ):
        flags.append("comparison_template_needs_review")
    if row["id"] in ARCHETYPE_REPAIRS:
        archetype, visual_elements = ARCHETYPE_REPAIRS[row["id"]]
        row.setdefault("original_prompt_text", row["prompt_text"])
        row["prompt_text"] = (
            "Create a five-second educational clip from this written brief. "
            f"Show one checkable change: {instruction.strip()} "
            "Reveal the requested arrows or labels, then hold the result."
        )
        row["expected_visual_elements"] = visual_elements
        row["expected_narrative_order"] = [
            "Show the source diagram", "Add the requested arrows or labels",
            "Hold the completed diagram for inspection",
        ]
        row["curation"]["archetype_corrected_from"] = "comparison"
        row["curation"]["pedagogical_archetype"] = archetype
        flags = [flag for flag in flags if flag != "comparison_template_needs_review"]
        if len(row["prompt_text"]) > 500 and "prompt_over_500_chars" not in flags:
            flags.append("prompt_over_500_chars")
    row["curation"]["quality_flags"] = flags
    if row["id"] == "grade_biology_task_10":
        row["original_prompt_text"] = row["prompt_text"]
        row["prompt_text"] = (
            "Create a five-second teaching clip from the supplied diagram. "
            "Add energy-flow arrows acorn → squirrel → fox, one at a time. "
            "Explain that each arrow points from food to consumer. "
            "Leave the bear unconnected: the diagram gives no evidence for a fox → bear feeding link."
        )
        row["expected_concepts"] = ["energy flows from food to consumer", "do not infer unsupported feeding links"]
        row["expected_visual_elements"] = ["acorn, squirrel, fox and bear", "acorn → squirrel → fox arrows", "bear without invented arrow"]
        row["expected_narrative_order"] = ["show source diagram", "add acorn → squirrel", "add squirrel → fox", "hold result"]
        row["discipline_specific_rubric"] = [
            "arrows point from food to consumer", "acorn → squirrel and squirrel → fox are shown",
            "no fox → bear arrow is invented", "organisms remain correctly identified",
        ]
        row["curation"]["quality_flags"].append("source_target_food_chain_corrected")
        row["curation"]["visual_pair_screening"] = {
            "status": "target_rejected",
            "reason": "original target adds unsupported fox-to-bear arrow; use the written rubric, not this target, for scoring",
        }
    if row["id"] in SOURCE_TARGET_REJECTIONS:
        row["curation"]["visual_pair_screening"] = {
            "status": "target_rejected", "reason": SOURCE_TARGET_REJECTIONS[row["id"]],
        }
        row["curation"]["quality_flags"].append("source_target_extra_edit_rejected")
    if row["id"] in {"grade_engineering_task_2", "grade_engineering_task_3"}:
        row["curation"]["visual_pair_screening"] = {
            "status": "source_and_target_inspected_scope_rejected",
            "reason": "the two source solids differ, but drawing all three orthographic views is too much for one five-second clip; target geometry needs separate subject verification",
        }
        if "manual_atomic_scope_required" not in row["curation"]["quality_flags"]:
            row["curation"]["quality_flags"].append("manual_atomic_scope_required")
    if row["id"] == "disciplinegen_biology_26fdde9159c8433d":
        row["original_prompt_text"] = row["prompt_text"]
        row["prompt_text"] = (
            "Create a five-second educational clip showing one meiosis-II cell with two "
            "replicated, nonhomologous chromosomes. Point to the sister chromatids and "
            "centromere of one chromosome, then hold the labeled state. "
            "Do not infer a mutation from unequal allele labels."
        )
        row["expected_concepts"] = ["a replicated chromosome has sister chromatids joined at a centromere"]
        row["expected_visual_elements"] = ["one cell", "two nonhomologous replicated chromosomes", "one labeled centromere and pair of sister chromatids"]
        row["expected_narrative_order"] = ["show meiosis-II cell", "label sister chromatids and centromere", "hold result"]
        row["discipline_specific_rubric"] = [
            "sister chromatids belong to one replicated chromosome",
            "centromere joins the sister chromatids", "no mutation claim is inferred from the diagram",
        ]
        row["curation"]["quality_flags"] = ["meiosis_source_claim_repaired"]
    if row["id"] in HISTORY_REPAIRS:
        prompt, concept, visual_check, truth_check = HISTORY_REPAIRS[row["id"]]
        row["original_prompt_text"] = row["prompt_text"]
        row["prompt_text"] = "Create a five-second educational clip. " + prompt
        row["expected_concepts"] = [concept]
        row["expected_visual_elements"] = [visual_check]
        row["expected_narrative_order"] = ["show the initial state", "reveal one contrast or change", "hold and label the result"]
        row["discipline_specific_rubric"] = [visual_check, truth_check]
        row["curation"]["quality_flags"].append("authored_history_rewrite_from_source_theme")
    if row["id"] in HEAP_REPAIRS:
        prompt, concept, truth_check = HEAP_REPAIRS[row["id"]]
        row["original_prompt_text"] = row["prompt_text"]
        row["prompt_text"] = "Create a five-second worked visual trace. " + prompt
        row["expected_concepts"] = [concept]
        row["expected_visual_elements"] = ["indexed array", "heap tree", "final array shown in prompt"]
        row["expected_narrative_order"] = ["show original heap", "perform the specified update", "hold final array"]
        row["discipline_specific_rubric"] = [truth_check, "parent–child heap order holds in the final tree"]
        row["curation"]["quality_flags"] = ["heap_result_explicitly_verified"]
    if row["id"] in DISCIPLINEGEN_FACT_REPAIRS:
        prompt, concept, visual, truth_check = DISCIPLINEGEN_FACT_REPAIRS[row["id"]]
        row["original_prompt_text"] = row["prompt_text"]
        row["prompt_text"] = "Create a five-second educational clip. " + prompt
        row["expected_concepts"] = [concept]
        row["expected_visual_elements"] = [visual]
        row["expected_narrative_order"] = ["show initial visual", "reveal the corrected relation", "hold final state"]
        row["discipline_specific_rubric"] = [visual, truth_check]
        row["curation"]["quality_flags"] = ["source_factual_inconsistency_repaired"]
    return row


def focus_pilot(row: dict) -> dict:
    row = deepcopy(row)
    flags = []
    if row["id"] in DIFFICULTY_REPAIRS:
        row["original_difficulty"] = row["difficulty"]
        row["difficulty"] = DIFFICULTY_REPAIRS[row["id"]]
        flags.append("difficulty_recalibrated_from_high")
    if row["id"] in ATOMIC_PILOT_REPAIRS:
        prompt, concept, truth_check = ATOMIC_PILOT_REPAIRS[row["id"]]
        row["original_prompt_text"] = row["prompt_text"]
        row["prompt_text"] = "Create a five-second educational clip. " + prompt
        row["expected_concepts"] = [concept]
        row["expected_visual_elements"] = ATOMIC_VISUALS[row["id"]]
        row["expected_narrative_order"] = ["show initial state", "perform one step", "hold correct result"]
        row["discipline_specific_rubric"] = [truth_check, "the final state remains visible"]
        flags.append("atomic_step_rewrite")
    if row["id"] == "math_high_01":
        row["original_prompt_text"] = row["prompt_text"]
        row["prompt_text"] = (
            "Generate a five-second clip illustrating compactness for subsets of the real line. "
            "Show a sequence in [0,1] with a subsequence converging to a point inside [0,1]. "
            "Contrast it with the sequence 1/n in (0,1), whose limit 0 lies outside (0,1). "
            "Label the excluded endpoint; do not generalize this sequence criterion to arbitrary topological spaces."
        )
        row["expected_concepts"] = [
            "compact subsets of the real line", "sequential compactness in metric spaces",
            "limit inside versus outside the set",
        ]
        row["expected_narrative_order"] = [
            "show [0,1] and a convergent subsequence",
            "show 1/n in (0,1)", "mark its excluded limit 0",
        ]
        flags.append("topology_claim_scoped_to_real_line")
    if row["id"] == "cs_high_02":
        row["original_prompt_text"] = row["prompt_text"]
        row["prompt_text"] = (
            "Create a five-second worked comparison of two replicas during a network partition. "
            "Show one write: the CP choice rejects or delays it to preserve consistency; "
            "the AP choice accepts it but replicas may temporarily disagree. "
            "State that the consistency/availability tradeoff applies during a partition."
        )
        row["expected_concepts"] = ["consistency versus availability during a partition"]
        row["expected_narrative_order"] = ["show partition", "compare one write under CP and AP", "hold outcome"]
        row["discipline_specific_rubric"] = [
            "CP may reject or delay the write during the partition",
            "AP may accept the write while replicas temporarily differ",
            "does not claim a universal two-of-three rule outside partitions",
        ]
        flags.append("cap_theorem_claim_corrected")
    if row["id"] == "hist_high_02":
        row["original_prompt_text"] = row["prompt_text"]
        row["prompt_text"] = (
            "Create a five-second comparison of two explanations of revolution. "
            "Show Skocpol's emphasis on state breakdown and international pressure, "
            "then Brinton's sequence from moderate to radical rule. "
            "Label these as different analytical emphases."
        )
        row["expected_concepts"] = ["Skocpol's structural explanation", "Brinton's staged pattern of revolution"]
        row["expected_narrative_order"] = ["show Skocpol's structural factors", "show Brinton's stages", "compare labels"]
        row["discipline_specific_rubric"] = [
            "Skocpol is tied to state breakdown and international pressure",
            "Brinton is tied to the moderate-to-radical sequence",
            "the J-curve is not attributed to Brinton",
        ]
        flags.append("brinton_j_curve_misattribution_corrected")
    if "10-second" in row["prompt_text"] and row.get("target_duration_s") == 5:
        row["original_prompt_text"] = row["prompt_text"]
        row["prompt_text"] = row["prompt_text"].replace("10-second", "5-second")
        flags.append("duration_wording_corrected_from_10_to_5")
    if len(row.get("expected_narrative_order", [])) > 4:
        flags.append("manual_atomic_scope_required")
    if flags:
        row.setdefault("curation", {})["quality_flags"] = flags
    return row


def main() -> None:
    groups = [
        ("pilot_v0_2.jsonl", [focus_pilot(row) for row in read_rows("pilot_v0_2.jsonl")
                             if row["id"] not in REPLACEMENTS]),
        ("multisource_pilot_300.jsonl", [focus_multisource(row) for row in
            read_rows("multisource_pilot_300.jsonl") if row["id"] not in DROP_IDS
            and row["id"] not in REPLACEMENTS]),
    ]
    extras = {}
    extra_sources = {}
    for name in ("candidates_subagent_medicine_cs_gaps.jsonl", "candidates_subagent_humanities_social.jsonl"):
        for row in read_rows(name):
            if row["id"] in EXTRA_IDS and row["id"] not in REPLACEMENTS:
                if row["id"] in extras:
                    raise ValueError(f"Duplicate extra ID: {row['id']}")
                if row["id"] in MEDICINE_REPAIRS:
                    prompt, truth = MEDICINE_REPAIRS[row["id"]]
                    row = deepcopy(row)
                    row["original_prompt_text"] = row["prompt_text"]
                    row["prompt_text"] = "Create a five-second educational clip. " + prompt
                    row["expected_concepts"] = [truth]
                    row["expected_visual_elements"] = MEDICINE_VISUALS[row["id"]]
                    row["expected_narrative_order"] = ["show initial condition", "reveal one change", "hold result"]
                    row["discipline_specific_rubric"] = [truth]
                    row.setdefault("curation", {}).setdefault("quality_flags", []).append("atomic_step_rewrite")
                    if row["id"] in MEDICINE_DIFFICULTY_REPAIRS:
                        row["original_difficulty"] = row["difficulty"]
                        row["difficulty"] = MEDICINE_DIFFICULTY_REPAIRS[row["id"]]
                        row["curation"]["quality_flags"].append("difficulty_recalibrated_from_high")
                extras[row["id"]] = row
                extra_sources[row["id"]] = name
    selected_extra_ids = tuple(key for key in EXTRA_IDS if key not in REPLACEMENTS)
    if set(extras) != set(selected_extra_ids):
        raise ValueError(f"Missing extras: {sorted(set(selected_extra_ids) - set(extras))}")

    rows = []
    manifest = []
    ids = set()
    texts = set()
    for name, batch in groups + [("selected_draft_extras", [extras[key] for key in selected_extra_ids]),
                                 ("verified_source_additions", source_additions())]:
        for row in batch:
            case_id = row["id"]
            normalized = re.sub(r"\s+", " ", row["prompt_text"].strip().casefold())
            if case_id in ids or normalized in texts:
                raise ValueError(f"Duplicate ID or exact prompt: {case_id}")
            ids.add(case_id)
            texts.add(normalized)
            rows.append(row)
            source_file = (extra_sources[case_id] if name == "selected_draft_extras" else
                           ("data/sources/grade/data/sources/grade/full/data.json" if
                            row.get("source", {}).get("dataset") == "GRADE" else
                            "data/sources/disciplinegen/metadata/sampled_rows.jsonl") if
                           name == "verified_source_additions" else name)
            curation = row.get("curation", {})
            manifest.append({
                "id": case_id,
                "source_file": (source_file if name == "verified_source_additions" else
                                f"data/prompts/{source_file}"),
                "source_dataset": row.get("source", {}).get("dataset", "project_draft"),
                "curation_status": curation.get("status", "draft_needs_subject_review"),
                "redistribution_license": row.get("source", {}).get("license", "not_verified"),
            })

    if len(rows) != 400:
        raise ValueError(f"Expected 400 cases, found {len(rows)}")
    if len(DROP_IDS) != 14 or set(DROP_IDS) & ids:
        raise ValueError("The intended near-duplicate exclusions were not applied")
    required = {"id", "discipline", "task_type", "prompt_text", "expected_concepts", "expected_visual_elements", "expected_narrative_order"}
    for row in rows:
        missing = required - row.keys()
        if missing:
            raise ValueError(f"{row['id']}: missing {sorted(missing)}")

    report = {
        "candidate_count": len(rows),
        "release_ready": False,
        "by_source_file": dict(Counter(item["source_file"] for item in manifest)),
        "by_discipline": dict(sorted(Counter(row["discipline"] for row in rows).items())),
        "by_difficulty_label": dict(sorted(Counter(row.get("difficulty", "missing") for row in rows).items())),
        "difficulty_label_note": "undergrad and k12 are audience levels in inherited rows, not calibrated task difficulty; do not combine them with low/medium/high.",
        "difficulty_review_required_count": sum(row.get("difficulty") in {"undergrad", "k12"} for row in rows),
        "discipline_count_range": [min(Counter(row["discipline"] for row in rows).values()),
                                   max(Counter(row["discipline"] for row in rows).values())],
        "by_task_type": dict(sorted(Counter(row["task_type"] for row in rows).items())),
        "by_pedagogical_archetype": dict(sorted(Counter(row.get("curation", {}).get("pedagogical_archetype", "unlabeled") for row in rows).items())),
        "by_discipline_and_task_type": {
            discipline: dict(sorted(Counter(row["task_type"] for row in rows if row["discipline"] == discipline).items()))
            for discipline in sorted({row["discipline"] for row in rows})
        },
        "by_curation_status": dict(sorted(Counter(item["curation_status"] for item in manifest).items())),
        "quality_flags": dict(sorted(Counter(flag for row in rows for flag in
            row.get("curation", {}).get("quality_flags", [])).items())),
        "excluded_source_ids": sorted(DROP_IDS),
        "replaced_draft_ids": REPLACEMENTS,
        "known_limitations": [
            "Only the existing four reviewed multisource rows have completed visual and subject review.",
            "GRADE redistribution rights remain unverified; keep upstream IDs and assets separate.",
            "The 27 supplemental rows are earlier generated drafts, not new expert-authored items.",
            "Sports and music remain separate taxonomy labels from the original 12-discipline pilot.",
            "No videos, first frames, or frozen learner quizzes are provided for every item.",
            "A 3-5 second task-feasibility and near-duplicate semantic review is still required.",
        ],
    }
    OUT.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
    SOURCE_MANIFEST.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in manifest), encoding="utf-8")
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(rows)} candidates to {OUT.relative_to(ROOT)}")
    print(f"source counts: {report['by_source_file']}")


if __name__ == "__main__":
    main()
