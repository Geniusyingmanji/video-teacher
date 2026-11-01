"""Short, independently checkable replacements for long inherited source briefs.

Rows are ordered to match sorted flagged IDs within each discipline and task type.
Each tuple contains an instructional claim or question, the visible setup, and the
single final condition. These are newly authored candidate tasks, not source GTs.
"""

SCOPE_REPLACEMENTS = {
    ("biology", "explanation"): [
        ("Energy-flow arrows point from food to consumer", "plant, insect and bird icons", "plant → insect → bird, with no reversed arrow"),
        ("A producer makes organic matter that can support a food chain", "plant and insect icons", "the plant is labeled producer and the insect consumer"),
        ("The cell membrane encloses the cytoplasm", "one animal-cell outline", "cytoplasm remains inside the membrane"),
        ("A nucleus is an organelle inside a eukaryotic cell", "one cell with a central oval", "the oval is labeled nucleus inside the membrane"),
        ("A food web may contain more than one food chain", "a plant, two herbivores and a bird", "two arrows leave the plant toward different consumers"),
        ("Mitochondria are located in the cell cytoplasm", "cell membrane, cytoplasm and one mitochondrion", "the mitochondrion is inside the membrane but outside the nucleus"),
        ("A neuron receives signals at dendrites and sends them along an axon", "one neuron silhouette", "dendrite and axon labels point to different structures"),
    ],
    ("chemistry", "explanation"): [
        ("A covalent bond is a shared electron pair between atoms", "two H atoms with one pair of dots", "one shared pair sits between the H atoms"),
        ("A carbonyl group contains a carbon–oxygen double bond", "a simple C=O structural fragment", "the C=O bond is highlighted as a double bond"),
        ("An ester contains the linkage C(=O)–O–C", "a generic ester fragment", "the oxygen is adjacent to the carbonyl carbon"),
        ("A benzene ring has six carbon positions in a cycle", "a numbered six-membered ring", "positions 1 through 6 close into one ring"),
        ("A hydroxyl group is written –OH when bonded to a carbon skeleton", "one carbon and an attached –OH", "the O is bonded to carbon and H"),
        ("A carboxyl group combines C=O and O–H on one carbon", "a generic –COOH fragment", "both oxygen attachments share the same carbon"),
        ("Ionic formulas balance total positive and negative charge", "Na+ and Cl− ion cards", "one of each makes a neutral NaCl unit"),
        ("A reaction coefficient counts molecules, not atoms inside a formula", "2 H2 molecules beside H2O", "the coefficient 2 is outside H2"),
    ],
    ("computer_science", "explanation"): [
        ("A swap exchanges two array elements while preserving the other positions", "array [3, 1, 2] with first two cells highlighted", "the array becomes [1, 3, 2]"),
        ("An inner loop completes its iteration before the outer index advances", "nested i and j counters", "j changes while i remains fixed"),
        ("A binary search halves a sorted search interval after one comparison", "sorted list and a midpoint marker", "one half is crossed out after comparison"),
        ("A stack removes the most recently pushed item first", "stack with A then B on top", "pop reveals B before A"),
        ("A directed graph edge has a source and a destination", "nodes A and B", "the arrowhead points from A to B only"),
        ("A Boolean AND is true only when both inputs are true", "two input switches and one output lamp", "only the 1,1 input lights the lamp"),
    ],
    ("computer_science", "problem_solving"): [
        ("After swapping the first two entries of [4,2,7], what is the array?", "three cells labeled 4, 2, 7", "the answer is [2,4,7]"),
        ("Push A, then B; which item is popped first?", "an empty stack with A and B cards", "B is removed first"),
    ],
    ("economics", "explanation"): [
        ("A price ceiling below equilibrium can create excess quantity demanded", "supply and demand axes with equilibrium marked", "the ceiling line lies below equilibrium and demand exceeds supply"),
        ("Opportunity cost is the value of the best forgone alternative", "two mutually exclusive options A and B", "choosing A places B in the forgone-alternative box"),
        ("A demand curve slopes down in a standard price–quantity diagram", "price vertical and quantity horizontal axes", "the marked demand curve falls as quantity increases"),
        ("A supply curve slopes up in a standard price–quantity diagram", "price vertical and quantity horizontal axes", "the marked supply curve rises as quantity increases"),
        ("A higher nominal price with unchanged quantity raises nominal spending", "price times quantity equation", "P increases while Q stays fixed, so P×Q increases"),
        ("Inflation measures a rise in a price index, not one product price alone", "basket price index and one-item price", "the basket index is highlighted as the measure"),
        ("A budget constraint shows affordable combinations of two goods", "two-good axes and one straight budget line", "a point on the line uses the full budget"),
        ("Marginal cost is the extra cost of one additional unit", "total-cost cards for 2 and 3 units", "the difference is labeled cost of the third unit"),
        ("A positive externality benefits someone outside the transaction", "buyer, seller and third-party icons", "one benefit arrow reaches the third party"),
        ("A percentage-point change differs from a percent change", "rate cards 20% and 25%", "the change is labeled 5 percentage points"),
    ],
    ("geography", "explanation"): [
        ("Calm Beaufort-force-zero conditions have no wind-driven smoke drift", "ship and chimney smoke", "the smoke rises vertically"),
        ("Latitude lines run east–west while measuring north–south position", "globe with equator and one parallel", "the parallel circles the globe horizontally"),
        ("Longitude lines meet at the poles", "globe with two meridians", "both meridians meet at each pole"),
        ("Contour lines join places of equal elevation", "hill map with one labeled contour", "the same height label follows one contour"),
        ("Closer contour spacing indicates a steeper slope", "two hill slopes with contour lines", "the close-spaced side is labeled steeper"),
        ("A river flows from higher to lower elevation", "highland, lowland and one river", "the flow arrow points downhill"),
        ("A watershed divide separates drainage toward different basins", "ridge between two valleys", "arrows leave the ridge toward opposite valleys"),
        ("The equator is zero degrees latitude", "globe with equator", "0° latitude is placed on the equator"),
        ("A map scale converts map distance to ground distance", "1 cm map segment and 1:100000 scale", "the segment is labeled 1 km on the ground"),
        ("A rain shadow can form on the leeward side of a mountain", "windward and leeward mountain slopes", "rain is shown windward and drier air leeward"),
    ],
    ("history", "explanation"): [
        ("The Silk Road was a network of routes rather than one straight road", "three branching Eurasian route lines", "multiple branches connect regions"),
        ("The printing press enabled repeated impressions from reusable type", "one type block and two printed sheets", "the same type block produces both sheets"),
        ("The Industrial Revolution involved greater use of mechanized production", "hand tool and powered machine icons", "the machine is shown performing a repeated production step"),
        ("The Roman Empire preceded the medieval Byzantine continuation in the east", "one west–east timeline", "the eastern continuation extends after the western endpoint"),
        ("Historical chronology orders events by their dates", "three event cards labeled 1800, 1850 and 1900", "the cards are ordered 1800 → 1850 → 1900"),
        ("A primary source was produced in or near the period under study", "dated diary and later textbook cards", "the period diary is marked primary source"),
        ("A historical map legend defines what its colors and symbols mean", "map with two colors and a legend", "each map color matches its legend entry"),
    ],
    ("mathematics", "explanation"): [
        ("The slope of a horizontal line is zero", "two points on a horizontal grid line", "rise is 0 and slope is labeled 0"),
        ("A perpendicular line to a horizontal line is vertical", "coordinate grid with one horizontal line", "the new line crosses at a right angle and is vertical"),
    ],
    ("physics", "explanation"): [
        ("On a spacetime diagram, light rays form 45-degree lines when axes use matching units", "ct and x axes", "two light paths lie on the cone boundary"),
        ("A free-body diagram shows forces acting on one selected object", "one block on a floor", "weight points down and normal force points up from the block"),
        ("A velocity–time graph's slope represents acceleration", "straight rising velocity–time line", "rise over run is labeled acceleration"),
        ("A resistor in series carries the same current as its neighboring series resistor", "one unbranched circuit with two resistors", "equal current arrows pass through both"),
        ("A parallel circuit gives each branch the same voltage across common nodes", "two branches sharing two nodes", "the same voltage label spans each branch"),
        ("Reflection angles are measured from the surface normal", "mirror, normal and incoming ray", "incident and reflected angles are shown on opposite sides of the normal"),
        ("A converging lens bends parallel rays toward a focal point", "lens, optical axis and two parallel rays", "emerging rays meet at one focal point"),
    ],
    ("physics", "problem_solving"): [
        ("A block moves 10 m in 2 s at constant speed; what is its speed?", "10 m arrow and 2 s clock", "10/2 = 5 m/s"),
        ("A 2-ohm resistor carries 3 A; what is its voltage drop?", "R=2 Ω and I=3 A on one resistor", "V=IR=6 V"),
        ("A 1 kg object accelerates at 2 m/s²; what is the net force?", "mass and acceleration cards", "F=ma=2 N"),
        ("A wave has frequency 2 Hz; what is its period?", "two cycles per second on a timeline", "T=1/f=0.5 s"),
        ("A ray meets the normal at 30°; what is its reflection angle?", "mirror, normal and 30° incident angle", "the reflected angle from the normal is 30°"),
        ("A 4 V source drives 2 A through one resistor; what is the resistance?", "V=4 V and I=2 A circuit", "R=V/I=2 Ω"),
    ],
    ("sports", "problem_solving"): [
        ("Which curve represents a lower, slower glucose rise: A with a high sharp peak or B with a low broad peak?", "two clearly labeled response curves", "B is selected"),
        ("A Go stone has one empty adjacent intersection; where can the opponent capture it?", "one stone with one marked liberty", "the opponent stone fills the only liberty"),
        ("Which Xiangqi opening move places the cannon on the center file?", "starting cannon and center-file marker", "the cannon moves horizontally onto the center file"),
    ],
}
