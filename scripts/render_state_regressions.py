"""Render real regression clips; these fixtures are not full model-generated lessons."""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from manim import *
from generation.scene_state import ArraySlots,FormulaSlot
from generation.layout_guard import check_layout
from generation.layout_policy import tag
from generation.source_primitives import SourcePrimitives
from generation.strict_manim import SourceFrameGuard,check_source

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
 out=args.out.resolve();out.mkdir(parents=True,exist_ok=True);reports=[]
 class ArrayRegression(Scene):
  def construct(self):
   title=tag(Text('Bubble sort: state follows the objects',font_size=30).to_edge(UP),'title');self.add(title)
   array=ArraySlots([3,1,2]);self.play(FadeIn(array.group),run_time=1);self.wait(1)
   array.swap(self,0,1,run_time=1);self.wait(1);array.swap(self,1,2,run_time=1);self.wait(2)
   assert array.values==[1,2,3]
   assert check_layout(self)['valid']
   reports.append({'fixture':'array','states':array.history,'final':array.verify()})
 class FormulaRegression(Scene):
  def construct(self):
   self.add(tag(Text('Solve, then substitute to verify',font_size=30).to_edge(UP),'title'))
   slot=FormulaSlot()
   for tex in ['2x+5=17','2x=12','x=6']:
    slot.replace(self,tex,run_time=.5);self.wait(.5);assert check_layout(self)['valid']
   slot.clear(self,run_time=.5);slot.replace(self,r'2\cdot6+5=17',run_time=.5);self.wait(1)
   assert check_layout(self)['valid'];reports.append({'fixture':'formula','states':slot.history,'layout':check_layout(self)})
 class SourceRegression(Scene):
  def construct(self):
   import numpy as np
   source=ROOT/'data/sources/grade/selected_assets/before/grade_ComputerScience_task_17.png'
   viewport=[.04,.16,.48,.92];boxes=[[426,195,526,242],[418,645,514,689]]
   primitives=SourcePrimitives(source,boxes,viewport)
   image=ImageMobject(str(source));image.scale(min(config.frame_width*.44/image.width,config.frame_height*.76/image.height))
   image.move_to([(-.24)*config.frame_width,(-.04)*config.frame_height,0]);self.source_image=image;self.add(image)
   from generation.source_geometry import canvas_box
   guard=SourceFrameGuard([canvas_box(b,primitives.size,viewport=viewport) for b in boxes],protected_viewport=viewport)
   self.camera.capture_mobjects(self.mobjects);guard.check(self.camera.pixel_array,0);self.wait(1)
   self.add(tag(Text('Fill the original target boxes',font_size=24).move_to([3.5,2.3,0]),'title'))
   for text,box in zip(['0.8','0.4'],boxes):
    obj=self.source_text(text,box) if hasattr(self,'source_text') else primitives.text(text,box)
    self.play(FadeIn(obj),run_time=.6);self.wait(1)
    self.camera.capture_mobjects(self.mobjects);guard.check(self.camera.pixel_array,1)
   assert guard.report()['valid'];reports.append({'fixture':'source','guard':guard.report(),'boxes':boxes,
       'canvas_regions':[canvas_box(b,primitives.size,viewport=viewport) for b in boxes],
       'source':str(source),'viewport':viewport})
 for cls in [ArrayRegression,FormulaRegression,SourceRegression]:
  with tempconfig({'media_dir':str(out/cls.__name__),'pixel_width':854,'pixel_height':480,'frame_rate':15,'disable_caching':True,'verbosity':'WARNING'}):
   cls().render()
   video=next((out/cls.__name__/'videos/480p15').glob(cls.__name__+'.mp4'))
   if cls is SourceRegression:
    row=reports[-1]
    row['encoded_source_preservation']=check_source(video,Path(row['source']),row['canvas_regions'],row['viewport'])
    assert row['encoded_source_preservation']['valid']
   reports[-1]['video']=str(video)
 from PIL import Image,ImageDraw
 from eval.frame_extractor import extract_frames
 sheet=Image.new('RGB',(854*3,510*3),'#202020');draw=ImageDraw.Draw(sheet)
 for i,row in enumerate(reports):
  frames=extract_frames(row['video'],n=3,resize_max=854)
  for j,frame in enumerate(frames):sheet.paste(frame,(854*j,510*i+30))
  draw.text((10,510*i+6),row['fixture'],fill='white')
 sheet.save(out/'review.jpg');(out/'report.json').write_text(json.dumps(reports,indent=2)+'\n')
 print(json.dumps(reports),flush=True)
if __name__=='__main__':main()
