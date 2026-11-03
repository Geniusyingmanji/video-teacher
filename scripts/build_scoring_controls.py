"""Build original short teaching-video controls for evaluator regression.

No external videos, paper code, prompts or rating tables are copied. Variants
are native Manim scenes or temporal resamplings of our own rendered scene.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from generation.strict_video_contract import make_contract

GOOD='''from manim import *
class Section1Scene(Scene):
    def construct(self):
        title=Text("Bubble sort: [3, 1, 2]",font_size=34).to_edge(UP,buff=.35)
        slots=[LEFT*2,ORIGIN,RIGHT*2]
        boxes=VGroup(*[Square(side_length=1.2).move_to(p) for p in slots])
        digits=[Text(str(v),font_size=42).move_to(p) for v,p in zip([3,1,2],slots)]
        self.add(title,boxes,*digits)
        cue=Text("3 > 1: swap neighbors",font_size=30).move_to(DOWN*1.6)
        arrows=VGroup(ArcBetweenPoints(slots[0]+UP*.6,slots[1]+UP*.6,angle=-PI/2).add_tip(),
                      ArcBetweenPoints(slots[1]+DOWN*.6,slots[0]+DOWN*.6,angle=-PI/2).add_tip()).set_color(YELLOW)
        self.play(FadeIn(cue),Create(arrows),run_time=.7)
        self.play(Swap(digits[0],digits[1],path_arc=PI/2),run_time=1)
        digits[0],digits[1]=digits[1],digits[0]
        cue2=Text("3 > 2: swap neighbors",font_size=30).move_to(DOWN*1.6)
        arrows2=arrows.copy().shift(RIGHT*2)
        self.play(ReplacementTransform(cue,cue2),ReplacementTransform(arrows,arrows2),run_time=.5)
        self.play(Swap(digits[1],digits[2],path_arc=PI/2),run_time=1)
        digits[1],digits[2]=digits[2],digits[1]
        done=Text("1 < 2 < 3: sorted",font_size=30,color=GREEN).move_to(DOWN*1.6)
        self.play(FadeOut(arrows2),ReplacementTransform(cue2,done),run_time=.4)
'''


def encode(path,frames,fps=15):
    import cv2
    height,width=frames[0].shape[:2]
    writer=cv2.VideoWriter(str(path),cv2.VideoWriter_fourcc(*'mp4v'),fps,(width,height))
    if not writer.isOpened():raise RuntimeError('control video encoder unavailable')
    for frame in frames:writer.write(frame)
    writer.release()


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=True)
    case={'id':'control_sort','prompt_text':'Demonstrate bubble sort on [3, 1, 2]. Show the two adjacent comparisons and swaps, preserve each original value, and finish with [1, 2, 3].',
          'expected_visual_elements':['three original number objects and three fixed slots','visible comparisons and adjacent swaps','final sorted state'],
          'expected_narrative_order':['show [3, 1, 2]','compare and swap 3 with 1','compare and swap 3 with 2','hold [1, 2, 3]'],
          'target_duration_s':5,'audio_narration_required':False}
    for name,code in [('good',GOOD),('overlap',GOOD.replace('self.add(title,boxes,*digits)',
         'self.add(title,boxes,*digits)\n        self.add(Text("Wrongly overlapping caption",font_size=38).move_to(UP*3.3))'))]:
        directory=args.out/name;directory.mkdir(exist_ok=True)
        (directory/'scene.py').write_text(code);(directory/'contract.json').write_text(json.dumps(make_contract(case)))
        (directory/'storyboard.json').write_text('{"source_edit_regions":[]}')
        with (directory/'render.log').open('w') as log:
            result=subprocess.run([sys.executable,'-m','generation.strict_manim','--code',str(directory/'scene.py'),
                '--scene','Section1Scene','--contract',str(directory/'contract.json')],cwd=ROOT,
                env=dict(os.environ,PATH=str(Path(sys.executable).parent)+os.pathsep+os.environ.get('PATH','')),
                stdout=log,stderr=subprocess.STDOUT,timeout=120)
        if name=='good' and result.returncode:raise RuntimeError((directory/'render.log').read_text()[-3000:])
        diagnostics=json.loads((directory/'strict_diagnostics.json').read_text())
        if name=='overlap' and diagnostics['layout']['valid']:raise RuntimeError('overlap control did not produce its intended defect')
        (args.out/f'{name}.mp4').write_bytes(Path(diagnostics['rendered_video']).read_bytes())
    import cv2
    import numpy as np
    capture=cv2.VideoCapture(str(args.out/'good.mp4'));frames=[]
    while True:
        ok,frame=capture.read()
        if not ok:break
        frames.append(frame)
    capture.release()
    if len(frames)!=75:raise RuntimeError('control is not exactly 75 frames')
    encode(args.out/'frozen.mp4',[frames[-1]]*75)
    encode(args.out/'reverse.mp4',list(reversed(frames)))
    decorated=[]
    for index in range(75):
        frame=frames[-1].copy();center=(int(100+50*np.cos(index*.25)),int(100+50*np.sin(index*.25)))
        cv2.circle(frame,center,12,(255,80,20),-1);decorated.append(frame)
    encode(args.out/'decoration.mp4',decorated)
    tiny=[]
    for index in range(75):
        frame=frames[-1].copy()
        if index>30:cv2.putText(frame,'ok',(810,450),cv2.FONT_HERSHEY_SIMPLEX,.5,(80,240,80),1)
        tiny.append(frame)
    encode(args.out/'tiny_reveal.mp4',tiny)
    rows=[{'id':name,'case':{**case,'id':name},'video_path':str((args.out/f'{name}.mp4').resolve()),
           'expected_presentation_pass':name=='good'} for name in ('good','overlap','frozen','reverse','decoration','tiny_reveal')]
    (args.out/'manifest.json').write_text(json.dumps(rows,indent=2)+'\n')
    print(json.dumps({'controls':len(rows),'directory':str(args.out)},indent=2))


if __name__=='__main__':main()
