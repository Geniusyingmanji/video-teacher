"""Hand-authored replacements for weak automatically reframed candidate items.

Each tuple: learning claim or explicit question, opening visual, checkable answer.
The source anchor remains in each item's curation record for provenance review.
"""

REWRITES = {
    "art_music": {
        "concept": [
            ("A C-major triad stacks C, E and G", "three labeled piano keys C, E and G", "only C, E and G sound together"),
            ("Yellow and blue pigments mix to make green in this classroom color model", "two labeled paint swatches", "the overlap is green, not a third unmixed swatch"),
            ("A readymade is an existing object selected and reframed as art", "an ordinary object moving into a gallery frame", "the object remains recognizably the same object"),
            ("The dominant triad in C major is G–B–D and is labeled V", "C-major scale degrees and three highlighted notes", "G, B and D receive the V label"),
            ("Broken brushstrokes and outdoor light are useful visual clues for Impressionist painting", "two brushwork samples under the same light", "the broken-stroke sample is identified by visible marks"),
            ("The C-major scale follows whole–whole–half–whole–whole–whole–half", "one keyboard octave with C through C", "half steps fall at E–F and B–C"),
            ("In a simple V–I cadence, scale degree 2 can move to scale degree 1", "two-note melody above G and C harmony", "the melodic line ends on tonic above I"),
            ("A fugue subject can enter successively in different voices", "three labeled voice lanes", "the same short motif enters the lanes at different times"),
            ("One-point perspective aligns receding parallel edges toward one vanishing point", "a road and horizon with one marked point", "both road edges converge at the marked point"),
        ],
        "problem": [
            ("Which sample uses broken outdoor-light brushwork: A or B?", "two labeled painting-detail samples, A smooth and B visibly broken", "B is selected and its broken marks are highlighted"),
            ("Where are the two half-step pairs in C major?", "C through C on a labeled keyboard", "E–F and B–C alone are marked"),
            ("Which pigment pair makes green in the classroom color wheel?", "red, yellow and blue pigment swatches", "yellow plus blue is selected and green is shown"),
            ("What is the retrograde of C, E, F-sharp, B?", "four labeled notes in the original order", "the revealed order is B, F-sharp, E, C without changing pitches"),
            ("Where should the vanishing point be placed for this road?", "two straight road edges receding toward the horizon", "one point is placed at their shared intersection"),
            ("Which chord completes a V–I cadence in C major after G–B–D?", "G–B–D followed by an empty chord slot", "C–E–G is revealed as I"),
        ],
    },
    "civics": {
        "concept": [
            ("A percentage expresses a part per hundred", "60 highlighted votes among 100 dots", "60/100 is labeled 60%"),
            ("Three quarters of 50 U.S. states is at least 38 states", "a 50-cell state counter", "37.5 is rounded up to 38 whole states"),
            ("A public park is a traditional public forum for speech in U.S. constitutional doctrine", "a park sign and speech icon", "the park is labeled traditional public forum"),
            ("An Electoral College majority requires at least 270 of 538 votes", "a 538-cell tally bar", "the majority threshold is marked at 270"),
            ("Policy comparison should state the criteria before ranking options", "two policies and cost/access columns", "both options are compared on the same two criteria"),
            ("A security-alliance diagram distinguishes a commitment from a specific response", "members connected by a treaty line", "the treaty commitment and each member's action are separate labels"),
            ("NATO Article 5 addresses an armed attack through collective assistance", "an attack icon and separate member-response arrows", "responses are not drawn as identical automatic troop deployments"),
            ("A secret ballot keeps a voter's selected choice private", "a marked ballot folding into a box", "the mark is hidden once the ballot enters the box"),
            ("A presidential veto returns a passed bill to Congress in the U.S. federal process", "Congress, bill and president boxes", "the veto arrow runs from president back toward Congress"),
        ],
        "problem": [
            ("A bill passed both chambers; who may veto it?", "House and Senate arrows feeding a bill", "the president is selected, not the court"),
            ("Which ballot protects the voter's choice: exposed or folded?", "an exposed ballot A and folded ballot B", "B enters the box with its mark hidden"),
            ("After both chambers pass the same federal bill, where is it presented?", "House and Senate feeding an unlabeled next box", "the next box is labeled president"),
            ("Which branch exercises the veto in this three-branch diagram?", "legislative, executive and judicial boxes", "the executive branch is highlighted"),
            ("Which document is the reference for judicial review of a federal law?", "a law card beside a Constitution card", "the Constitution card is selected as the comparison standard"),
            ("A candidate has 254 electoral votes; how many more reach 270?", "a tally at 254 and a goal line at 270", "the gap is shown as 16"),
            ("In a 100-vote poll, option A receives 60; what is its share?", "100 dots with 60 marked A", "60/100 is simplified to 60%"),
        ],
    },
    "language_literature": {
        "concept": [
            ("A noun can name an animal or a place", "the sentence 'The dog ran through the park'", "dog and park alone receive noun labels"),
            ("A theme is an interpretive claim supported by story events, not a one-word topic", "a topic card 'power' and a claim card about power", "the claim card is paired with one event as evidence"),
            ("Ethos appeals to a speaker's credibility", "a claim beside a speaker's relevant expertise", "the expertise is linked to ethos, not to a numerical statistic"),
            ("An independent clause has a subject and predicate and can stand alone", "two short complete clauses joined by 'and'", "each clause remains a sentence when separated"),
            ("Iambic pentameter has five weak–strong metrical feet", "one line divided into five two-beat groups", "five weak–strong groups are marked"),
            ("Free indirect discourse blends third-person narration with a character's viewpoint", "a neutral narrator sentence followed by a character-colored thought", "the narrator grammar remains third person while viewpoint shifts"),
            ("An arguable thesis makes a claim that evidence could support or challenge", "a topic label and a specific claim", "the claim, not the topic label, is marked thesis"),
            ("Words gain part of their meaning through differences from related words", "the words hot, warm and cool on a scale", "warm is placed between hot and cool rather than equated with either"),
            ("A metaphor identifies one thing with another without using 'like' or 'as'", "the line 'Time is a thief'", "time and thief are linked with a metaphor label"),
        ],
        "problem": [
            ("Which sentence is passive: 'Mia opened the gate' or 'The gate was opened by Mia'?", "two labeled sentence cards", "the second card is selected and the receiving subject is marked"),
            ("How many weak–strong feet appear in the displayed five-foot line?", "one line already divided into five metrical groups", "five groups are counted once each"),
            ("Is 'Time is a thief' a metaphor or simile?", "the quoted sentence and two choice labels", "metaphor is selected because no like/as comparison appears"),
            ("In the word 'tree', which is the signifier: the written word or the plant?", "the printed word beside a tree drawing", "the printed word is selected as signifier"),
            ("Which card gives the signified for 'tree': the letters or the concept?", "letters T-R-E-E and a concept card", "the concept card is selected"),
            ("Change 'The chef baked the cake' into passive voice", "the active sentence and an empty answer line", "the answer reads 'The cake was baked by the chef'"),
        ],
    },
    "medicine": {
        "concept": [
            ("In an alveolus, oxygen moves into nearby blood while carbon dioxide moves into the air space", "one alveolus next to a capillary", "O2 arrow points toward blood and CO2 arrow toward alveolar air"),
            ("The sinoatrial node starts the electrical impulse of a normal heartbeat", "a simplified right atrium with an SA-node dot", "the first impulse arrow starts at the SA node"),
            ("Blood type A has A antigen on red-cell surfaces", "one red-cell outline with surface markers", "A markers appear on the red cell, without adding B markers"),
        ],
        "problem": [
            ("Where does glomerular filtrate first enter after crossing the filtration barrier?", "glomerular capillary and Bowman's space", "the arrow enters Bowman's space"),
            ("A red cell carries the Rh D antigen; is its Rh type positive or negative?", "red cell with a labeled D surface marker", "Rh positive is selected"),
            ("Which blood component first forms a plug at this vessel injury: platelets or red cells?", "small vessel-wall break and two cell types", "platelets collect at the break"),
            ("During inhalation, does the diaphragm move down or up?", "chest outline with diaphragm and two direction arrows", "the downward arrow is selected"),
            ("Which valve lies between the left ventricle and aorta?", "left ventricle and aorta with an unlabeled valve", "the valve is labeled aortic valve"),
            ("A blood sample has A and B surface antigens; what is its ABO type?", "red cell with separate A and B markers", "AB is selected"),
        ],
    },
}

MEDICINE_REFERENCES = {
    "concept": [
        "https://www.nhlbi.nih.gov/health/lungs/breathing-benefits",
        "https://www.msdmanuals.com/professional/cardiovascular-disorders/overview-of-arrhythmias-and-conduction-disorders/overview-of-arrhythmias",
        "https://medlineplus.gov/ency/article/003345.htm",
    ],
    "problem": [
        "https://www.ncbi.nlm.nih.gov/books/NBK500032/",
        "https://medlineplus.gov/ency/article/003345.htm",
        "https://www.nhlbi.nih.gov/health/clotting-disorders/how-blood-clots",
        "https://www.nhlbi.nih.gov/health/lungs/breathing-benefits",
        "https://www.nhlbi.nih.gov/health/heart/blood-flow",
        "https://medlineplus.gov/ency/article/003345.htm",
    ],
}
