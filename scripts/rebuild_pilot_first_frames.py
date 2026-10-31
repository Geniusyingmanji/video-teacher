"""Rebuild the eleven rejected pilot opening frames as exact SVG diagrams."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
from xml.sax.saxutils import escape

import cairosvg


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/first_frames"
DEFAULT_OUT = ROOT / "data/first_frames_repaired_v1"
W, H = 832, 480


def svg(body: str, title: str) -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
            f'viewBox="0 0 {W} {H}"><rect width="832" height="480" fill="#f8fbff"/>'
            f'<text x="42" y="55" font-family="Arial" font-size="30" font-weight="bold" '
            f'fill="#15324a">{escape(title)}</text>'
            f'{body}</svg>')


def text(x: int, y: int, value: str, size: int = 22, color: str = "#183249",
         weight: str = "normal", anchor: str = "start") -> str:
    return (f'<text x="{x}" y="{y}" font-family="Arial" font-size="{size}" '
            f'font-weight="{weight}" text-anchor="{anchor}" fill="{color}">'
            f'{escape(value)}</text>')


def rect(x: int, y: int, w: int, h: int, fill: str = "#ffffff",
         stroke: str = "#aac6d9", radius: int = 12, sw: int = 2) -> str:
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')


def line(x1: int, y1: int, x2: int, y2: int, color: str = "#28546d",
         sw: int = 4) -> str:
    return (f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
            f'stroke="{color}" stroke-width="{sw}" stroke-linecap="round"/>')


def arrow(x1: int, y1: int, x2: int, y2: int, color: str = "#e45745",
          sw: int = 5) -> str:
    import math
    angle = math.atan2(y2 - y1, x2 - x1)
    length = 14
    left = (x2 - length * math.cos(angle - .55), y2 - length * math.sin(angle - .55))
    right = (x2 - length * math.cos(angle + .55), y2 - length * math.sin(angle + .55))
    return (line(x1, y1, x2, y2, color, sw) +
            f'<polygon points="{x2},{y2} {left[0]:.1f},{left[1]:.1f} '
            f'{right[0]:.1f},{right[1]:.1f}" fill="{color}"/>')


def circle(x: int, y: int, radius: int, fill: str, stroke: str = "none") -> str:
    return (f'<circle cx="{x}" cy="{y}" r="{radius}" fill="{fill}" '
            f'stroke="{stroke}" stroke-width="2"/>')


def physics() -> str:
    body = rect(42, 94, 338, 340) + rect(405, 94, 385, 340)
    body += text(64, 132, "Frictionless floor · mass = 2 kg", 20)
    body += line(76, 315, 353, 315) + rect(145, 244, 94, 70, "#bde4f7", "#2e7599", 4)
    body += text(192, 287, "2 kg", 22, anchor="middle")
    body += arrow(252, 279, 347, 279) + text(269, 257, "10 N", 22, "#c23a32", "bold")
    body += text(428, 132, "Free-body diagram", 23, weight="bold")
    body += rect(489, 223, 65, 56, "#bde4f7", "#2e7599", 4)
    body += arrow(521, 213, 521, 158, "#2c8c75") + text(533, 177, "N", 21)
    body += arrow(521, 286, 521, 340, "#2c8c75") + text(535, 337, "mg", 21)
    body += arrow(563, 251, 650, 251) + text(580, 229, "10 N", 21, "#c23a32", "bold")
    body += text(431, 372, "F = ma", 20, "#183249", "bold")
    body += text(431, 398, "10 N = (2 kg) a", 20, "#183249", "bold")
    body += text(431, 424, "a = 5 m/s²", 20, "#183249", "bold")
    return svg(body, "Newton's second law: a 2 kg block")


def ionic() -> str:
    body = rect(38, 98, 756, 314)
    body += text(64, 133, "Before: neutral atoms", 22, weight="bold")
    body += circle(185, 238, 64, "#e9f4ff", "#5a9bc2") + text(185, 247, "Na", 32, anchor="middle")
    body += circle(410, 238, 64, "#f3f0ff", "#8776ba") + text(410, 247, "Cl", 32, anchor="middle")
    body += circle(239, 206, 8, "#e45745")
    # Seven chlorine valence electrons, paired around the right-hand atom.
    for x, y in [(410,165),(424,165),(472,218),(472,232),(402,307),(416,307),(347,238)]:
        body += circle(x, y, 5, "#6647a4")
    body += arrow(255, 190, 338, 190) + text(275, 169, "1 electron", 18, "#c23a32")
    body += text(190, 345, "Na: 1 outer electron", 18, anchor="middle")
    body += text(410, 345, "Cl: 7 outer electrons", 18, anchor="middle")
    body += arrow(510, 239, 572, 239, "#5b7b8b")
    body += circle(642, 212, 38, "#e9f4ff", "#5a9bc2") + circle(735, 212, 38, "#f3f0ff", "#8776ba")
    body += text(642, 221, "Na+", 23, anchor="middle") + text(735, 221, "Cl-", 23, anchor="middle")
    body += text(686, 304, "Opposite ions attract → NaCl", 18, anchor="middle")
    return svg(body, "Sodium transfers one electron to chlorine")


def methane() -> str:
    body = rect(38, 104, 756, 300)
    body += text(70, 144, "Reactants", 23, weight="bold")
    body += text(518, 144, "Products", 23, weight="bold")
    body += circle(130, 234, 43, "#d9e4ee", "#52708b") + text(130, 243, "CH4", 25, anchor="middle")
    body += text(189, 243, "+", 30)
    for x in (255, 335):
        body += circle(x, 234, 35, "#ffe0df", "#d45b52") + text(x, 242, "O2", 25, anchor="middle")
    body += arrow(393, 232, 492, 232)
    body += circle(553, 234, 40, "#e5ebf0", "#6d8297") + text(553, 243, "CO2", 24, anchor="middle")
    body += text(605, 243, "+", 30)
    for x in (660, 741):
        body += circle(x, 234, 34, "#dcefff", "#6ba4c9") + text(x, 242, "H2O", 20, anchor="middle")
    body += text(416, 340, "CH4 + 2 O2  →  CO2 + 2 H2O", 29, "#163953", "bold", "middle")
    body += text(416, 377, "C: 1 = 1     H: 4 = 4     O: 4 = 4", 18, "#3a6578", anchor="middle")
    return svg(body, "Balanced methane combustion")


def binary_search() -> str:
    body = rect(38, 103, 756, 307)
    values = [1,3,5,7,9,11,13,15]
    for i, value in enumerate(values):
        x = 72 + i * 87
        body += rect(x, 181, 75, 76, "#fff2d2" if i == 3 else "#ecf5fb",
                     "#e9a22a" if i == 3 else "#95b8cc", 6, 3)
        body += text(x+38, 226, str(value), 28, anchor="middle")
        body += text(x+38, 281, str(i), 17, "#708998", anchor="middle")
    body += arrow(110, 327, 110, 289, "#287fa8") + text(110, 358, "low = 0", 20, anchor="middle")
    body += arrow(720, 327, 720, 289, "#287fa8") + text(720, 358, "high = 7", 20, anchor="middle")
    body += arrow(371, 145, 371, 174, "#d98c00") + text(371, 135, "mid = 3", 20, "#a66900", "bold", "middle")
    body += text(416, 393, "array[3] = 7 = target  →  found", 22, "#1d765d", "bold", "middle")
    return svg(body, "Binary search for 7")


def stack() -> str:
    body = rect(40, 103, 752, 305)
    body += text(71, 146, "Push order", 22, weight="bold")
    body += text(71, 189, "A  →  B  →  C", 28, "#1b7197", "bold")
    body += text(71, 273, "Pop order", 22, weight="bold")
    body += text(71, 317, "C  →  B  →  A", 28, "#a74c40", "bold")
    body += line(500, 171, 500, 368, sw=5) + line(714, 171, 714, 368, sw=5)
    body += line(500, 368, 714, 368, sw=5)
    for label, y in [('A',315),('B',260),('C',205)]:
        body += rect(523,y,168,44,"#dff0f9","#5a9fc1",6)
        body += text(607,y+30,label,26,anchor="middle")
    body += arrow(563, 144, 563, 192, "#2b8b73") + text(513, 134, "push at top", 18)
    body += arrow(660, 195, 660, 146, "#c95348") + text(640, 134, "pop at top", 18)
    return svg(body, "Stack: last in, first out (LIFO)")


def voyage() -> str:
    body = rect(37, 100, 758, 313, "#d9eef9", "#9bc4d7")
    body += text(173, 145, "Caribbean", 26, "#135a7f", "bold", "middle")
    body += text(676, 145, "Spain", 26, "#135a7f", "bold", "middle")
    body += '<path d="M38 170 Q95 156 123 201 L126 412 L38 412 Z" fill="#91bd75"/>'
    body += '<path d="M794 178 Q744 162 704 211 L705 412 L794 412 Z" fill="#91bd75"/>'
    body += arrow(646, 241, 207, 241, "#df5b43", 7)
    for x, y in [(573,280),(455,298),(336,280)]:
        body += '<path d="M%d %d l40 0 l-8 11 l-25 0 Z" fill="#815b42"/>' % (x-20,y)
        body += line(x,y-4,x,y-48,"#674f40",2)
        body += '<path d="M%d %d l0 -37 l24 34 Z" fill="#fffaf0" stroke="#a78b70"/>' % (x+2,y-7)
    body += text(416, 375, "Three ships sail WEST across the Atlantic (1492)", 21,
                 "#1e5068", "bold", "middle")
    return svg(body, "Columbus' first voyage: Spain → Caribbean")


def plates() -> str:
    body = ''
    panels = [(36,"Divergent"),(302,"Convergent"),(568,"Transform")]
    for x, label in panels:
        body += rect(x,101,228,311) + text(x+114,139,label,22,weight="bold",anchor="middle")
    # Divergent: plates move away from a central rift; magma rises.
    body += rect(53,225,89,67,"#b7d7b0","#6a9875",3)
    body += rect(159,225,89,67,"#b7d7b0","#6a9875",3)
    body += arrow(147,204,74,204,"#cf5547") + arrow(154,204,227,204,"#cf5547")
    body += arrow(151,328,151,256,"#ed823b") + text(150,364,"magma rises",17,anchor="middle")
    # Convergent: surface motion inward and a right plate dives under left.
    body += rect(317,225,91,56,"#b7d7b0","#6a9875",3)
    body += '<path d="M423 225 H512 V281 Q475 299 431 346 L416 333 Q459 290 423 281 Z" fill="#b7d7b0" stroke="#6a9875" stroke-width="2"/>'
    body += arrow(346,203,408,203,"#cf5547") + arrow(492,203,432,203,"#cf5547")
    body += text(416,381,"subduction",17,anchor="middle")
    # Transform: fault is vertical; plates slide in opposite directions along it.
    body += rect(585,221,86,107,"#b7d7b0","#6a9875",3)
    body += rect(690,221,86,107,"#b7d7b0","#6a9875",3)
    body += line(680,201,680,350,"#9b6e52",4)
    body += arrow(634,309,634,239,"#cf5547") + arrow(733,239,733,309,"#cf5547")
    body += text(680,381,"slide past",17,anchor="middle")
    return svg(body, "Three plate boundaries")


def iambic() -> str:
    body = rect(40,105,752,307)
    body += text(416,156,"Shall I compare thee to a summer's day?",25,
                 "#183249","bold","middle")
    feet=[("Shall","I"),("com","PARE"),("thee","TO"),("a","SUM"),("mer's","DAY")]
    for i,(weak,strong) in enumerate(feet):
        x=72+i*143
        body += rect(x,205,131,113,"#f1f7fd","#a8c7db",8)
        body += text(x+33,242,"u",22,"#4d7896",anchor="middle")
        body += text(x+98,242,"/",22,"#c85b42",anchor="middle")
        body += text(x+33,284,weak,21,anchor="middle")
        body += text(x+98,284,strong,21,"#c24d37","bold","middle")
        body += text(x+65,347,str(i+1),18,"#607c91",anchor="middle")
    body += text(416,385,"Five iambs: unstressed (u) → stressed (/)",20,
                 "#265b7a",anchor="middle")
    return svg(body, "Iambic pentameter: five weak–strong pairs")


def nouns() -> str:
    body = rect(41,107,750,302)
    words=[("The",80),("brown",155),("dog",268),("ran",365),
           ("quickly",445),("to",578),("the",628),("park.",695)]
    for word,x in words:
        body += text(x,228,word,27,"#14344d","bold" if word in ("dog","park.") else "normal")
    body += '<ellipse cx="296" cy="219" rx="47" ry="42" fill="none" stroke="#e45b48" stroke-width="4"/>'
    body += '<ellipse cx="731" cy="219" rx="59" ry="42" fill="none" stroke="#e45b48" stroke-width="4"/>'
    body += text(416,333,"Nouns name people, places, things, or ideas.",22,
                 "#345d72",anchor="middle")
    body += text(416,375,"Nouns here: dog · park",23,"#b94738","bold","middle")
    return svg(body, "Find all nouns in the sentence")


def color_wheel() -> str:
    import math
    body = rect(39,102,754,309)
    colors=[("red","#e64b49"),("orange","#f49b31"),("yellow","#efd33b"),
            ("green","#50a76d"),("blue","#3f76cf"),("purple","#9460b5")]
    cx,cy,r=212,254,107
    for i,(_,color) in enumerate(colors):
        a1=math.radians(-90+i*60);a2=math.radians(-90+(i+1)*60)
        x1,y1=cx+r*math.cos(a1),cy+r*math.sin(a1)
        x2,y2=cx+r*math.cos(a2),cy+r*math.sin(a2)
        body += f'<path d="M{cx} {cy} L{x1:.1f} {y1:.1f} A{r} {r} 0 0 1 {x2:.1f} {y2:.1f} Z" fill="{color}"/>'
    body += circle(cx,cy,34,"#ffffff")
    body += text(212,388,"Primary: red · yellow · blue",18,anchor="middle")
    equations=[("red + yellow = orange","#f49b31"),("yellow + blue = green","#50a76d"),
               ("blue + red = purple","#9460b5")]
    for i,(label,color) in enumerate(equations):
        y=157+i*87
        body += rect(390,y-31,348,64,"#ffffff","#c8d9e4",8)
        body += circle(419,y,17,color)
        body += text(451,y+8,label,23,"#183249","bold")
    return svg(body, "Primary colors mix into secondary colors")


def triad() -> str:
    body = rect(40,101,752,312)
    names=["C","D","E","F","G","A","B","C"]
    for i,name in enumerate(names):
        x=82+i*84
        fill="#ffecb9" if i in (0,2,4) else "#ffffff"
        body += rect(x,175,81,166,fill,"#638297",3,2)
        body += text(x+40,321,name,22,"#173f56","bold","middle")
    for i in (0,1,3,4,5):
        x=141+i*84
        body += rect(x,175,44,95,"#25394a","#25394a",3)
    for x,label in [(122,"C: root"),(290,"E: third"),(458,"G: fifth")]:
        body += arrow(x,127,x,167,"#d65a40") + text(x,119,label,19,"#bd4935","bold","middle")
    body += text(416,382,"C major triad = C + E + G",25,"#265b76","bold","middle")
    return svg(body, "Build a C major triad")


DRAW = {
    "phys_prob_01": physics, "chem_exp_01": ionic, "chem_exp_03": methane,
    "cs_exp_01": binary_search, "cs_exp_02": stack,
    "hist_exp_02": voyage, "geo_exp_02": plates,
    "lang_exp_02": iambic, "lang_prob_01": nouns,
    "art_exp_03": color_wheel, "art_prob_01": triad,
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    for source in SOURCE.glob("*.png"):
        if source.stem not in DRAW:
            shutil.copy2(source, args.out / source.name)
    records = []
    for case_id, build in DRAW.items():
        markup = build()
        (args.out / f"{case_id}.svg").write_text(markup, encoding="utf-8")
        png = args.out / f"{case_id}.png"
        cairosvg.svg2png(bytestring=markup.encode("utf-8"), write_to=str(png))
        records.append({"id": case_id, "source": "deterministic_svg_v1",
                        "sha256": hashlib.sha256(png.read_bytes()).hexdigest(),
                        "review_status": "needs_visual_review"})
    (args.out / "rebuild_manifest.jsonl").write_text(
        "".join(json.dumps(row) + "\n" for row in records), encoding="utf-8")
    print(f"Built {len(DRAW)} corrected diagrams in {args.out}")


if __name__ == "__main__":
    main()
