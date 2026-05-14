"""High-difficulty (graduate/professional) cases for v0.2 expansion.

2 cases per non-medicine discipline = 22 new cases.
These target researchers / advanced practitioners / graduate students.

Run:
    python scripts/build_v0_2_high_difficulty.py
Writes:
    data/prompts/high_difficulty_addon.jsonl
Then re-run:
    python scripts/migrate_to_v0_2.py  # regenerates pilot_v0_2.jsonl
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
    prompt: str,
    concepts: list[str],
    visuals: list[str],
    order: list[str],
    audience: str,
    rubric: list[str],
    audio: bool = False,
) -> dict[str, Any]:
    return {
        "id": cid,
        "discipline": discipline,
        "subdomain": subdomain,
        "task_type": task,
        "difficulty": "professional",  # will become "high" in v0.2
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
# MATHEMATICS  — graduate level
# ============================================================================
CASES += [
    case("math_high_01", "mathematics", "topology", "explanation",
         "Generate an educational video explaining the concept of a compact space in "
         "topology. Show a sequence in a bounded closed interval on the real line that "
         "must have a convergent subsequence (Bolzano–Weierstrass), contrast with an "
         "open interval where a sequence can escape. Label all set boundaries clearly.",
         ["compactness", "Bolzano–Weierstrass", "sequential compactness", "limit point"],
         ["closed bounded interval [a,b]", "open interval (a,b)", "sequence of points",
          "converging subsequence highlighted"],
         ["show closed interval", "plot diverging sequence in open interval",
          "plot sequence with convergent subsequence in closed interval",
          "state Bolzano–Weierstrass"],
         "graduate mathematics student",
         ["closed vs open interval visually distinct",
          "convergent subsequence arrows point to correct limit",
          "no claim that open intervals are compact"]),

    case("math_high_02", "mathematics", "measure_theory", "problem_solving",
         "Generate a video solving: 'Show that the Cantor set has Lebesgue measure zero.' "
         "Visualize the iterative removal of middle thirds from [0,1], show the total "
         "measure removed = 1/3 + 2/9 + 4/27 + … = 1, conclude measure(Cantor) = 0.",
         ["Lebesgue measure", "Cantor set", "geometric series", "measure zero"],
         ["unit interval [0,1]", "middle-third removal steps 1-4",
          "geometric series sum formula", "empty set measure = 0"],
         ["show [0,1]", "remove middle third → measure 1/3",
          "remove two middle thirds → additional 2/9",
          "sum the series → total removed = 1",
          "conclude measure 0"],
         "graduate mathematics student",
         ["first 3 removal steps visually correct",
          "series written correctly: 1/3 + 2/9 + 4/27 = 1",
          "final statement: Lebesgue measure of Cantor set = 0"]),
]

# ============================================================================
# PHYSICS  — graduate level
# ============================================================================
CASES += [
    case("phys_high_01", "physics", "quantum_mechanics", "explanation",
         "Generate an educational video explaining the double-slit experiment and "
         "wave-particle duality. Show: (1) particles hitting a screen through a single "
         "slit → broad band; (2) two slits, no detector → interference fringes; "
         "(3) two slits, which-path detector → fringes disappear. Label all setups.",
         ["wave-particle duality", "interference pattern", "quantum measurement",
          "which-path information"],
         ["single slit + screen", "double slit + interference pattern",
          "detector icon at slits", "no-fringe single-band pattern"],
         ["show single slit setup", "show double slit → interference fringes",
          "add detector → fringes collapse to two bands",
          "explain measurement collapses superposition"],
         "graduate physics student",
         ["interference fringes shown correctly for double slit",
          "fringes disappear when detector is added",
          "single slit result is a broad smooth band, not interference pattern"]),

    case("phys_high_02", "physics", "statistical_mechanics", "problem_solving",
         "Generate a video deriving the Maxwell–Boltzmann speed distribution shape. "
         "Start from the 3D velocity space, show that P(v) dv ∝ v^2 exp(−mv²/2kT) dv, "
         "identify the peak (most probable speed v_p = sqrt(2kT/m)), and plot the "
         "distribution, labeling v_p, mean speed, and rms speed.",
         ["Maxwell–Boltzmann distribution", "velocity space", "most probable speed",
          "mean speed", "rms speed"],
         ["3D velocity sphere", "P(v) curve", "three speed markers on x-axis",
          "formula on screen"],
         ["draw 3D velocity space spherical shell",
          "integrate → P(v) ∝ v^2 exp(−mv²/2kT)",
          "plot curve", "mark v_p < v_mean < v_rms",
          "compare curves at two temperatures"],
         "graduate physics student",
         ["v_p < v_mean < v_rms ordering correct",
          "formula P(v) ∝ v^2 exp(−mv²/2kT) appears on screen",
          "higher temperature curve is broader and peak shifts right"]),
]

# ============================================================================
# CHEMISTRY  — graduate level
# ============================================================================
CASES += [
    case("chem_high_01", "chemistry", "organic_mechanisms", "explanation",
         "Generate an educational video explaining the SN2 reaction mechanism. "
         "Show: nucleophile approaching the electrophilic carbon from the back side, "
         "the transition state with 5 bonds (partial), Walden inversion of configuration, "
         "and the leaving group departing. Use 3D perspective and label all species.",
         ["SN2 mechanism", "backside attack", "transition state", "Walden inversion",
          "leaving group"],
         ["electrophilic carbon center", "nucleophile arrow", "5-coordinate transition state",
          "inverted product", "leaving group"],
         ["show starting material + nucleophile",
          "draw backside attack arrow",
          "show trigonal bipyramidal transition state",
          "show inversion + leaving group departure",
          "compare starting and product stereochemistry"],
         "graduate chemistry student",
         ["nucleophile approaches from opposite side to leaving group",
          "transition state is trigonal bipyramidal with partial bonds",
          "Walden inversion shown correctly (umbrella flip)",
          "leaving group on correct side"]),

    case("chem_high_02", "chemistry", "thermodynamics", "problem_solving",
         "Generate a video solving: 'Calculate ΔG° for a reaction where ΔH° = −92 kJ/mol "
         "and ΔS° = −198 J/(mol·K) at T = 298 K.' Apply ΔG° = ΔH° − TΔS°, "
         "convert units carefully, and identify whether the reaction is spontaneous.",
         ["Gibbs free energy", "enthalpy", "entropy", "spontaneity", "unit conversion"],
         ["equation ΔG° = ΔH° − TΔS°", "unit conversion step J → kJ",
          "numerical result", "sign interpretation"],
         ["write ΔG° = ΔH° − TΔS°",
          "substitute values: −92 − 298 × (−0.198)",
          "compute TΔS° = −59.0 kJ/mol",
          "ΔG° = −92 − (−59.0) = −33 kJ/mol",
          "negative ΔG° → spontaneous"],
         "graduate chemistry student",
         ["ΔH correctly listed as −92 kJ/mol",
          "ΔS converted from J to kJ before subtracting",
          "final answer ΔG° ≈ −33 kJ/mol",
          "spontaneity conclusion correct (negative ΔG° = spontaneous)"]),
]

# ============================================================================
# BIOLOGY  — graduate level
# ============================================================================
CASES += [
    case("bio_high_01", "biology", "molecular_biology", "explanation",
         "Generate an educational video explaining the process of RNA splicing via the "
         "spliceosome. Show pre-mRNA with introns and exons labeled, the spliceosome "
         "assembling at splice sites (5' donor, 3' acceptor, branch point), the two "
         "transesterification steps, lariat intermediate formation, and final mature mRNA.",
         ["RNA splicing", "spliceosome", "introns", "exons", "lariat intermediate",
          "transesterification"],
         ["pre-mRNA with introns/exons", "spliceosome complex", "lariat loop",
          "mature mRNA with exons joined", "branch point A"],
         ["show pre-mRNA with exon1–intron–exon2",
          "spliceosome assembles at 5' splice site",
          "branch point A attacks 5' site → lariat",
          "3'-OH attacks 3' splice site → exons joined",
          "lariat debranched + degraded"],
         "graduate molecular biology student",
         ["branch point A nucleophile shown correctly",
          "lariat intermediate depicted with correct 2'-5' linkage",
          "final product is exon1–exon2 joined",
          "intron is removed as lariat"]),

    case("bio_high_02", "biology", "evolutionary_biology", "problem_solving",
         "Generate a video solving: 'In a Hardy–Weinberg population, the frequency of "
         "the recessive homozygote aa is 0.09. What are the allele frequencies p and q, "
         "and the frequency of heterozygotes Aa?' Apply HWE equations step by step.",
         ["Hardy–Weinberg equilibrium", "allele frequency", "genotype frequency",
          "homozygous recessive", "heterozygote"],
         ["HWE formulas p²+2pq+q²=1", "q² = 0.09", "q = 0.3", "p = 0.7",
          "2pq = 0.42"],
         ["write HWE genotype frequencies",
          "identify q² = 0.09 → q = 0.3",
          "compute p = 1 − q = 0.7",
          "compute 2pq = 2(0.7)(0.3) = 0.42",
          "summarize all three genotype frequencies"],
         "graduate biology student",
         ["q = 0.3 derived correctly from q² = 0.09",
          "p = 0.7 stated",
          "2pq = 0.42 computed correctly",
          "no violation of HWE assumptions stated"]),
]

# ============================================================================
# COMPUTER SCIENCE  — graduate level
# ============================================================================
CASES += [
    case("cs_high_01", "computer_science", "algorithm_complexity", "explanation",
         "Generate an educational video explaining why the P vs NP problem matters. "
         "Show: P (decision problems solvable in polynomial time), NP (problems verifiable "
         "in polynomial time), NP-completeness via reduction (show SAT → 3-SAT → Clique "
         "reduction chain), and what P=NP would mean for cryptography.",
         ["P class", "NP class", "polynomial-time reduction", "NP-completeness",
          "SAT problem", "implications for cryptography"],
         ["Venn diagram P ⊆ NP", "reduction arrow chain SAT→3-SAT→Clique",
          "padlock icon for cryptography", "unknown P vs NP boundary"],
         ["show P and NP circles",
          "example problem: Boolean satisfiability",
          "show reduction SAT → 3-SAT",
          "show NP-completeness definition",
          "discuss P=NP cryptography impact"],
         "graduate computer science student",
         ["P shown as subset of NP (or equal, labeled unknown)",
          "SAT correctly identified as NP-complete",
          "reduction direction is correct (SAT reduces to another problem, not vice versa)",
          "cryptography implication stated correctly"]),

    case("cs_high_02", "computer_science", "distributed_systems", "problem_solving",
         "Generate a video explaining the CAP theorem and solving: 'In a distributed "
         "database, a network partition occurs. Explain what happens if you choose "
         "Consistency over Availability vs Availability over Consistency, with a "
         "concrete two-node example.'",
         ["CAP theorem", "consistency", "availability", "partition tolerance",
          "network partition"],
         ["two database nodes", "network partition icon (broken link)",
          "CA vs CP vs AP triangle", "rejected write on one node"],
         ["show two nodes with replicated data",
          "introduce network partition",
          "CP choice: block writes → consistent but unavailable",
          "AP choice: allow writes → available but inconsistent",
          "state CAP: can only have 2 of 3"],
         "graduate computer science student / software engineer",
         ["CAP theorem triangle shown correctly",
          "CP path: nodes return error or block rather than stale data",
          "AP path: nodes return possibly stale data but stay alive",
          "partition tolerance is always required in practice"]),
]

# ============================================================================
# ECONOMICS  — graduate level
# ============================================================================
CASES += [
    case("econ_high_01", "economics", "game_theory", "explanation",
         "Generate an educational video explaining the Prisoner's Dilemma and Nash "
         "Equilibrium. Show the 2×2 payoff matrix, identify each player's dominant "
         "strategy, derive the Nash Equilibrium (both defect), and compare it with the "
         "Pareto-optimal outcome (both cooperate).",
         ["Prisoner's Dilemma", "dominant strategy", "Nash Equilibrium",
          "Pareto optimality", "payoff matrix"],
         ["2×2 payoff matrix", "arrows showing dominant strategies",
          "Nash Equilibrium cell highlighted", "Pareto-optimal cell highlighted"],
         ["introduce two players + strategies cooperate/defect",
          "fill in payoff matrix",
          "show each player's dominant strategy → defect",
          "highlight Nash Equilibrium (defect, defect)",
          "show Pareto-optimal outcome (cooperate, cooperate) = better for both"],
         "graduate economics student",
         ["payoff matrix values consistent with standard Prisoner's Dilemma",
          "defect shown as dominant strategy for both players",
          "Nash Equilibrium correctly identified as (defect, defect)",
          "Pareto-optimal shown as (cooperate, cooperate)"]),

    case("econ_high_02", "economics", "monetary_policy", "problem_solving",
         "Generate a video solving: 'Central bank increases the money supply by 10%. "
         "Using the Quantity Theory of Money (MV = PQ), and assuming velocity V and "
         "real output Q are constant, what happens to the price level P?' "
         "Derive the result and discuss the inflation implication.",
         ["Quantity Theory of Money", "MV = PQ", "price level", "inflation",
          "monetary neutrality"],
         ["equation MV = PQ on screen", "arrow showing M × 1.10",
          "P × 1.10 result", "inflation percentage"],
         ["write MV = PQ",
          "state V and Q constant",
          "M increases by 10%",
          "solve: P must increase by 10%",
          "discuss: monetary growth = inflation under these assumptions"],
         "graduate economics student",
         ["MV = PQ written correctly",
          "V and Q stated as constant",
          "correct conclusion: P increases by 10%",
          "inflation interpretation stated"]),
]

# ============================================================================
# GEOGRAPHY  — graduate level
# ============================================================================
CASES += [
    case("geo_high_01", "geography", "climate_science", "explanation",
         "Generate an educational video explaining the ITCZ (Intertropical Convergence "
         "Zone) and its role in tropical precipitation patterns. Show the Hadley Cell "
         "circulation, surface trade winds converging at the equator, rising air creating "
         "convective rainfall, and seasonal migration of the ITCZ following the sun.",
         ["ITCZ", "Hadley Cell", "trade winds", "convective rainfall",
          "seasonal ITCZ migration"],
         ["Earth cross-section with Hadley cells",
          "ITCZ band at equator", "trade wind arrows",
          "rising air and cloud/rain at ITCZ",
          "ITCZ position shift in January vs July"],
         ["show Earth with equator",
          "draw Hadley cell circulation",
          "show trade winds converging",
          "show rising air → clouds → rain at ITCZ",
          "show seasonal migration of ITCZ"],
         "graduate geography / climate science student",
         ["Hadley cells shown symmetrically about equator",
          "trade winds converging at ITCZ from correct directions",
          "rising air at ITCZ associated with rainfall",
          "ITCZ in correct hemisphere in each season"]),

    case("geo_high_02", "geography", "geopolitics", "problem_solving",
         "Generate a video analyzing: 'Why did the Heartland Theory (Mackinder 1904) "
         "argue that whoever controls Eurasia controls the world? Identify the Heartland "
         "region on a map, the World-Island concept, and one 21st-century critique of "
         "the theory (e.g., sea power / technology).'",
         ["Heartland Theory", "Mackinder", "Eurasia", "World-Island",
          "geopolitical critique"],
         ["world map with Heartland shaded", "World-Island label (Eurasia+Africa)",
          "sea power vs land power icons", "modern critique annotation"],
         ["show Mackinder's Heartland on map",
          "explain World-Island concept",
          "show why land control = resource + manpower base",
          "present sea-power critique",
          "note: technology (missiles, cyber) challenges geographic determinism"],
         "graduate geography / international relations student",
         ["Heartland correctly placed in central Eurasia",
          "World-Island correctly identified as Eurasia + Africa",
          "sea-power critique mentioned",
          "no claims that Heartland theory is undisputed truth"]),
]

# ============================================================================
# HISTORY  — graduate level
# ============================================================================
CASES += [
    case("hist_high_01", "history", "historiography", "explanation",
         "Generate an educational video explaining the Annales School of historiography. "
         "Show the three levels of historical time (Braudel): longue durée (geography, "
         "centuries), conjoncture (social/economic cycles, decades), événement "
         "(individual events, short term). Use a timeline with labeled bands.",
         ["Annales School", "Braudel", "longue durée", "conjoncture",
          "événement", "historical time"],
         ["three-band timeline", "geographical layer", "economic cycle layer",
          "event layer (shortest)", "Braudel's name"],
         ["introduce Annales School",
          "show longue durée band (centuries, geography/environment)",
          "show conjoncture band (decades, economic/social cycles)",
          "show événement band (years/days, individual events)",
          "compare traditional event-history vs Annales approach"],
         "graduate history student",
         ["three time bands shown with correct relative lengths",
          "longue durée is longest band",
          "Annales contrasted with event-only history",
          "Braudel credited"]),

    case("hist_high_02", "history", "revolution_theory", "problem_solving",
         "Generate a video comparing Theda Skocpol's structural theory of revolutions "
         "with Crane Brinton's 'anatomy of revolution' model. Identify 2 key differences "
         "in causal emphasis (state breakdown vs. J-curve / rising expectations) and "
         "apply each framework to the French Revolution as a test case.",
         ["Skocpol", "Brinton", "structural theory", "state breakdown",
          "rising expectations", "French Revolution"],
         ["two-column comparison table", "J-curve diagram",
          "state collapse arrow (Skocpol)", "French Revolution timeline"],
         ["present Skocpol: state breakdown + international pressure",
          "present Brinton: rising expectations + J-curve",
          "apply Skocpol to French Revolution: fiscal crisis + peasant revolt",
          "apply Brinton: reform → disappointment → revolution",
          "show key structural difference"],
         "graduate history student",
         ["Skocpol framework: state-centered causal factor mentioned",
          "Brinton J-curve correctly depicted (rising then sudden drop)",
          "French Revolution used as concrete test case for both frameworks",
          "at least 2 genuine differences between the frameworks stated"]),
]

# ============================================================================
# LANGUAGE / LITERATURE  — graduate level
# ============================================================================
CASES += [
    case("lang_high_01", "language_literature", "linguistics", "explanation",
         "Generate an educational video explaining Saussurean semiotics: signifier "
         "(sound-image) vs signified (concept), the arbitrary nature of the sign, "
         "synchronic vs diachronic analysis, and langue vs parole. Use split-screen "
         "diagrams for each concept pair.",
         ["Saussure", "sign", "signifier", "signified", "arbitrary nature",
          "langue", "parole", "synchronic", "diachronic"],
         ["signifier/signified diagram", "arbitrary nature diagram",
          "langue vs parole contrast", "time axis for synchronic/diachronic"],
         ["show sign = signifier + signified",
          "demonstrate arbitrary nature (different words same concept across languages)",
          "explain synchronic (snapshot) vs diachronic (change over time)",
          "explain langue (system) vs parole (individual utterance)"],
         "graduate linguistics student",
         ["sign correctly split into signifier and signified",
          "arbitrary nature shown with cross-language example",
          "synchronic/diachronic correctly contrasted",
          "langue/parole correctly contrasted"]),

    case("lang_high_02", "language_literature", "critical_theory", "problem_solving",
         "Generate a video applying Derrida's concept of différance to the word 'sign'. "
         "Show: (1) meaning deferred (never fully present), (2) meaning through difference "
         "from other signs, (3) trace structure, (4) deconstruction of sign/presence "
         "binary. Use text-on-screen to show the play of differences.",
         ["Derrida", "différance", "trace", "deconstruction", "binary opposition",
          "deferral"],
         ["word 'sign' on screen", "chain of other signs pointing outward",
          "crossed-out presence icon", "trace annotation"],
         ["show 'sign' on screen",
          "meaning deferred: arrows to other signs indefinitely",
          "meaning through difference: 'sign' ≠ 'symbol' ≠ 'word'",
          "trace: remainder of absent signs",
          "deconstruct sign/presence: presence always deferred"],
         "graduate critical theory / literary studies student",
         ["différance (with 'a') spelled correctly and distinguished from différence",
          "deferral and difference both shown as aspects of différance",
          "trace concept mentioned",
          "no naive claim that sign has fixed present meaning"]),
]

# ============================================================================
# CIVICS  — graduate level
# ============================================================================
CASES += [
    case("civ_high_01", "civics", "constitutional_law", "explanation",
         "Generate an educational video explaining the US doctrine of judicial review "
         "established in Marbury v. Madison (1803). Show: the political context, "
         "Marshall's three-part argument (constitutional supremacy → judicial role → "
         "power to strike down laws), and one later landmark application (e.g., "
         "Brown v. Board of Education).",
         ["judicial review", "Marbury v. Madison", "constitutional supremacy",
          "Marshall Court", "Brown v. Board"],
         ["Constitution document icon", "Marshall's name on screen",
          "three-part argument diagram", "Brown v. Board year 1954"],
         ["introduce Marbury v. Madison 1803",
          "show political context: Jefferson vs Adams appointments",
          "Marshall's argument: constitution is supreme law",
          "courts must enforce constitution → power to void laws",
          "apply: Brown v. Board used judicial review to strike down Plessy"],
         "graduate law / political science student",
         ["Marbury v. Madison year 1803 stated",
          "three-part logic clearly shown",
          "judicial review = court can void unconstitutional statutes",
          "Brown v. Board correctly applied as an example"]),

    case("civ_high_02", "civics", "international_relations", "problem_solving",
         "Generate a video analyzing: 'How does the Realist vs Liberal paradigm explain "
         "the formation of NATO? Apply each theory: (1) Realism — balance of power vs "
         "Soviet threat; (2) Liberalism — institutions reduce uncertainty + promote "
         "cooperation.' Show a comparison table and one key empirical fact per theory.",
         ["Realism", "Liberalism", "NATO", "balance of power", "international institution",
          "Soviet threat"],
         ["comparison table: Realism | Liberalism | NATO application",
          "USSR threat icon (Realism)", "NATO logo / cooperation icon (Liberalism)"],
         ["introduce NATO 1949 formation",
          "Realist explanation: balance Soviet power",
          "Liberal explanation: institution reduces transaction costs + uncertainty",
          "comparison table",
          "empirical support for each: Soviet expansion vs NATO dispute resolution mechanism"],
         "graduate international relations student",
         ["Realist explanation mentions power balancing or Soviet threat",
          "Liberal explanation mentions institutional benefits or collective security",
          "comparison is fair to both theories",
          "NATO correctly dated to 1949"]),
]

# ============================================================================
# ART / MUSIC  — graduate level
# ============================================================================
CASES += [
    case("art_high_01", "art_music", "music_theory", "explanation",
         "Generate an educational video explaining serialism and the twelve-tone "
         "technique (Schoenberg). Show: (1) the chromatic scale's 12 pitches, "
         "(2) constructing a tone row with all 12 pitches, "
         "(3) the four row forms: P (prime), I (inversion), R (retrograde), RI. "
         "Label each transformation on a notation grid.",
         ["serialism", "twelve-tone technique", "Schoenberg", "tone row",
          "prime", "inversion", "retrograde", "retrograde-inversion"],
         ["chromatic scale", "tone row grid P0", "inversion I0",
          "retrograde R0", "retrograde-inversion RI0"],
         ["show chromatic scale 12 notes",
          "construct a tone row",
          "show Prime form",
          "invert intervals → I form",
          "retrograde → R form",
          "retrograde of inversion → RI form"],
         "graduate music theory student",
         ["12 distinct pitches in the row (no repeats)",
          "inversion correctly reverses intervals (up↔down)",
          "retrograde correctly reverses pitch order",
          "all four forms labeled P, I, R, RI"]),

    case("art_high_02", "art_music", "contemporary_art_theory", "problem_solving",
         "Generate a video analyzing Duchamp's 'Fountain' (1917) through three critical "
         "lenses: (1) Institutional Theory of Art (Dickie) — art world context makes it "
         "art; (2) Expression Theory — where is the emotion?; (3) Formalism — formal "
         "properties. Conclude which theory best explains readymades.",
         ["Duchamp", "Fountain", "readymade", "Institutional Theory",
          "George Dickie", "formalism", "expression theory"],
         ["image/icon of Fountain (urinal)", "three theory labels on screen",
          "art world circle (Institutional)", "emotion question mark (Expression)",
          "form/shape analysis (Formalism)"],
         ["show Fountain 1917",
          "apply Institutional Theory: Duchamp submitted to art world → art",
          "apply Expression Theory: no obvious emotion → struggles to explain",
          "apply Formalism: arbitrary form → struggles to explain",
          "conclude: Institutional Theory best explains readymades"],
         "graduate art history / critical theory student",
         ["Fountain correctly attributed to Duchamp and dated ~1917",
          "Institutional Theory correctly credits art world context",
          "Expression Theory shown as inadequate for readymades",
          "clear conclusion about which theory fits best"]),
]


def main() -> None:
    out_path = Path(__file__).resolve().parent.parent / "data" / "prompts" / "high_difficulty_addon.jsonl"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w") as f:
        for c in CASES:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    from collections import Counter
    print(f"Wrote {len(CASES)} high-difficulty prompts to {out_path}")
    by_disc = Counter(c["discipline"] for c in CASES)
    print("By discipline:", dict(by_disc))


if __name__ == "__main__":
    main()
