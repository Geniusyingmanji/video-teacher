#!/usr/bin/env python3
import argparse,copy,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from localbench.scene import render_frame,inspect_layout
from localbench.common import write_json
from localbench.layout_audit import audit_layout
from localbench.client import MatrixClient
parser=argparse.ArgumentParser(description='One historical failure plus synthetic layout controls; development validation, not held-out accuracy.')
parser.add_argument('--out',type=Path,required=True)
parser.add_argument('--model',default='qwen3.8-flash')
parser.add_argument('--real-frame',type=Path,default=ROOT/'tests/fixtures/layout_language_overflow.jpg')
parser.add_argument('--call-model',action='store_true',help='Run bounded final-pixel VLM audit; otherwise render controls offline')
args=parser.parse_args();out=args.out.resolve()
if out.exists():parser.error('use a fresh output directory')
out.mkdir(parents=True)
from localbench.provenance import freeze_run,file_hash
freeze_run(out,{'entrypoint':'layout_control_validation','model':args.model,'call_model':args.call_model,'real_frame_sha256':file_hash(args.real_frame),'max_calls':8,'max_tokens':400000})
# Actual video pixel from the previously reviewed failure. No generator data sent to judge.
frames=[{'id':'F00','time_s':0,'path':str(args.real_frame.resolve())}]
base={'title':'An observed layout control','caption':'Read each label.','primitives':[
 {'type':'rect','x':.25,'y':.3,'w':.45,'h':.3,'color':'#1868ae','fill':'#eef8ff'},
 {'type':'text','x':.475,'y':.45,'align':'center','text':'VERB (was chased)','font_size':26,'color':'#14283e'}]}
controls=[('clean',base)]
a=copy.deepcopy(base);a['primitives'][0].update(x=.42,w=.1);controls.append(('overflow',a))
a=copy.deepcopy(base);a['primitives'].append({'type':'text','x':.475,'y':.47,'align':'center','text':'SECOND LABEL','font_size':26,'color':'#14283e'});controls.append(('overlap',a))
a=copy.deepcopy(base);a['primitives'][1]['color']='#eaf3fa';controls.append(('contrast',a))
a=copy.deepcopy(base);a['primitives'].append({'type':'rect','x':.40,'y':.30,'w':.12,'h':.3,'color':'#1868ae','fill':'#1868ae'});controls.append(('occlusion',a))
expect={'F00':'real historical container overflow'};local=[]
for i,(name,scene) in enumerate(controls,1):
 image,found=render_frame(scene,0);path=out/f'{name}.jpg';image.save(path,quality=95)
 frames.append({'id':f'F{i:02d}','time_s':0,'path':str(path)})
 expect[f'F{i:02d}']=name;local.append({'name':name,'issues':found})
write_json(out/'controls.json',{'expected':expect,'local_checks':local,'scope':'one real failure plus synthetic controls, not population recall'})
if args.call_model:
 client=MatrixClient(out,model=args.model,max_calls=8,max_tokens_total=400000,concurrency=4)
 try:
  audit=audit_layout(client,{'frames':frames,'sampling':'one historical real frame + five synthetic controls'},'controls',out/'audit')
  print(json.dumps(audit,ensure_ascii=False,indent=2),flush=True)
 finally:client.http.close()
else:print('Rendered five synthetic controls without API calls:',out)
