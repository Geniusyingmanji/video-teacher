"""Bounded analytic shading on an unchanged source plot, evaluated at raster resolution."""
from __future__ import annotations

import ast
import copy
import math
from functools import lru_cache

import numpy as np
from PIL import Image,ImageColor

VERSION='localbench-source-region-dev3'
EXTRACT_SYSTEM='''Read only the PUBLIC question and original plot. Extract the two functions
in lower(x) < y < upper(x), and calibrate the ORIGINAL whole image coordinates.
Do not solve for or restrict the x intervals. The code examines the full image width.
Return JSON {lower_expression,upper_expression,origin:[x,y],unit_x,unit_y,
lower_color,upper_color}. origin is the image position of mathematical (0,0), normalized
to image width/height. unit_x is normalized width per positive x unit; unit_y is normalized
height per positive y unit (positive y points UP). Read ticks across the whole graph.
Colors are hexadecimal #RRGGBB matching the actual curve ink. Expressions use x, pi,
numeric constants, + - * / **, sin(), cos(). No other names/functions or code.
No private answers are supplied. Do not crop the source or guess unobserved axes.'''

PLAN_SYSTEM='''Create a complete English-narrated lesson from the PUBLIC task, original
source image and supplied CODE-COMPUTED region facts. No private answer is supplied.
Return JSON {case_id,scenes:[...]} with EXACTLY SIX scenes: source/givens, interpretation
of the inequality, checking where upper exceeds lower, revealing the shaded solution,
verification including disconnected regions, recap. Each scene has title (<=65 chars),
duration_s,narration,caption (<=120 chars),slide_text (<=140 chars),teaching_lines
(one or two lines <=65 chars each),primitives:[{type:"text",x:0.5,y:0.5,text:"plot"}].
Durations sum to target. Each narration has 15-24 words; maximum 135 words TOTAL for
all six scenes of this 60-second lesson. Do not repeat all givens or every decimal.
The complete original plot remains visible. It is unedited for scenes 0-2; in scene 3,
code reveals ALL computed shaded intervals, and retains them in scenes 4-5.
Do not claim shading appears before scene 3. No source_edits or coordinates are needed.
Explain lower/upper bounds, check positive and negative x when present, and explicitly
account for every computed interval. Do not invent values or omit disconnected regions.
Preserve strict inequality: original curves are boundaries, not included solutions.
Use spoken words for numbers in narration. Captions/teaching_lines may use numbers.
Use estimated_open_intervals for boundaries; a clipped_left/right flag means the
solution continues to the viewport edge, not that the viewport defines a mathematical root.
The code facts use numerical computation from model-extracted public functions and axes,
not an expert answer key; do not claim exact roots when they are approximate.'''


def expression_values(expression,x):
    if not isinstance(expression,str) or len(expression)>200:raise ValueError('bounded expression required')
    tree=ast.parse(expression,mode='eval')
    if len(list(ast.walk(tree)))>40:raise ValueError('expression too complex')
    def visit(node):
        if isinstance(node,ast.Constant) and type(node.value) in (int,float):return node.value
        if isinstance(node,ast.Name) and node.id in ('x','pi'):return x if node.id=='x' else math.pi
        if isinstance(node,ast.UnaryOp) and isinstance(node.op,(ast.UAdd,ast.USub)):
            value=visit(node.operand);return -value if isinstance(node.op,ast.USub) else value
        if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id in ('sin','cos') and len(node.args)==1 and not node.keywords:
            return (np.sin if node.func.id=='sin' else np.cos)(visit(node.args[0]))
        if isinstance(node,ast.BinOp):
            left,right=visit(node.left),visit(node.right)
            if isinstance(node.op,ast.Add):return left+right
            if isinstance(node.op,ast.Sub):return left-right
            if isinstance(node.op,ast.Mult):return left*right
            if isinstance(node.op,ast.Div):return left/right
            if isinstance(node.op,ast.Pow) and isinstance(node.right,ast.Constant) and type(right) in (int,float) and abs(right)<=8:return left**right
        raise ValueError('unsupported region expression')
    with np.errstate(all='raise'):
        try:values=np.broadcast_to(np.asarray(visit(tree.body),dtype=float),np.shape(x))
        except (ArithmeticError,ValueError) as exc:raise ValueError('nonfinite or unsupported region values') from exc
    if not np.all(np.isfinite(values)) or np.any(np.abs(values)>1e8):raise ValueError('region outside numeric bounds')
    return values


def validate_spec(spec):
    fields={'lower_expression','upper_expression','origin','unit_x','unit_y','lower_color','upper_color'}
    if not isinstance(spec,dict) or set(spec)!=fields:raise ValueError('exact source-region fields required')
    if not isinstance(spec['origin'],list) or len(spec['origin'])!=2:raise ValueError('region origin needs two coordinates')
    for v in spec['origin']:
        if type(v) not in (int,float) or not math.isfinite(v) or not 0<=v<=1:raise ValueError('origin must be inside source image')
    for key in ('unit_x','unit_y'):
        v=spec[key]
        if type(v) not in (int,float) or not math.isfinite(v) or not .002<=v<=1:raise ValueError('bounded source-axis unit required')
    for key in ('lower_color','upper_color'):
        if not isinstance(spec[key],str):raise ValueError('curve color required')
        ImageColor.getrgb(spec[key])
    for key in ('lower_expression','upper_expression'):expression_values(spec[key],np.array([-.31,.27]))


def region_arrays(spec,size):
    validate_spec(spec);w,h=size
    xs=(np.arange(w)/w-spec['origin'][0])/spec['unit_x']
    ys=(spec['origin'][1]-np.arange(h)/h)/spec['unit_y']
    lower=expression_values(spec['lower_expression'],xs)
    upper=expression_values(spec['upper_expression'],xs)
    mask=(ys[:,None]>lower[None,:])&(ys[:,None]<upper[None,:])
    return xs,lower,upper,mask


def region_facts(spec,size):
    xs,lower,upper,mask=region_arrays(spec,size)
    eligible=np.any(mask,axis=0)
    starts=np.flatnonzero(eligible&~np.r_[False,eligible[:-1]])
    ends=np.flatnonzero(eligible&~np.r_[eligible[1:],False])
    intervals=[[float(xs[a]),float(xs[b])] for a,b in zip(starts,ends)]
    # Mathematical boundaries are estimated before rasterization. Thin valid wedges
    # may contain no pixel center; their last painted column is not an intersection.
    ymin=(spec['origin'][1]-(size[1]-1)/size[1])/spec['unit_y']
    ymax=spec['origin'][1]/spec['unit_y']
    grid=np.linspace(xs[0],xs[-1],size[0]*4+1)
    def gap(x):
        return np.minimum(expression_values(spec['upper_expression'],x),ymax)-np.maximum(expression_values(spec['lower_expression'],x),ymin)
    positive=gap(grid)>0
    ss=np.flatnonzero(positive&~np.r_[False,positive[:-1]])
    ee=np.flatnonzero(positive&~np.r_[positive[1:],False])
    def boundary(a,b):
        side=float(gap(np.array(a)))>0
        for _ in range(45):
            mid=(a+b)/2
            if (float(gap(np.array(mid)))>0)==side:a=mid
            else:b=mid
        return float((a+b)/2)
    estimated=[{'start':float(grid[a]) if a==0 else boundary(grid[a-1],grid[a]),
                'end':float(grid[b]) if b==len(grid)-1 else boundary(grid[b],grid[b+1]),
                'clipped_left':bool(a==0),'clipped_right':bool(b==len(grid)-1)} for a,b in zip(ss,ee)]
    checks=[]
    for x in (-3,-1,1,3):
        if xs[0]<=x<=xs[-1]:
            lo=float(expression_values(spec['lower_expression'],np.array(x)))
            hi=float(expression_values(spec['upper_expression'],np.array(x)))
            checks.append({'x':x,'lower':lo,'upper':hi,'nonempty_vertical_interval':lo<hi})
    return {'version':VERSION,'lower_expression':spec['lower_expression'],'upper_expression':spec['upper_expression'],
            'visible_x_range':[float(xs[0]),float(xs[-1])],'sampled_solution_intervals':intervals,
            'estimated_open_intervals':estimated,
            'x_resolution':float(xs[1]-xs[0]),'sample_checks':checks,
            'strict_inequality':True,'scope':'Numerically bracketed intervals and separate raster extents, clipped to original viewport; not a symbolic proof or guaranteed discovery of subpixel components.'}


def check_curve_fit(image,spec):
    """Check proposed mapping against actual colored source pixels, including negative x."""
    xs,lower,upper,_=region_arrays(spec,image.size);w,h=image.size
    pixels=np.asarray(image.convert('RGB')).astype(float);records=[]
    for name,values in (('lower',lower),('upper',upper)):
        color=np.array(ImageColor.getrgb(spec[name+'_color']),dtype=float)
        colored=np.linalg.norm(pixels-color,axis=2)<60
        if color.max()-color.min()<35:raise ValueError('source-region fit requires distinguishable colored curves')
        residual=[]
        for ix in np.linspace(4,w-5,min(w-8,160)).astype(int):
            expected=(spec['origin'][1]-values[ix]*spec['unit_y'])*h
            if not 3<=expected<h-3:continue
            candidates=np.flatnonzero(np.any(colored[:,max(0,ix-2):ix+3],axis=1))
            distance=float(np.min(abs(candidates-expected))) if len(candidates) else float(h)
            residual.append(distance)
        accepted=len(residual)>=30 and np.percentile(residual,90)<=max(8,h*.008)
        records.append({'curve':name,'samples':len(residual),'p90_residual_px':float(np.percentile(residual,90)) if residual else None,'passed':bool(accepted)})
    return {'curves':records,'passed':all(r['passed'] for r in records),
            'scope':'Verifies colored curve alignment for supplied expressions, not task interpretation or an exhaustive source-preservation certificate.'}


def refine_mapping(image,spec):
    """Fit four bounded axis parameters to observed ink; never alter task expressions."""
    from scipy.optimize import least_squares
    validate_spec(spec);w,h=image.size
    pixels=np.asarray(image.convert('RGB')).astype(float);samples=[]
    for name in ('lower','upper'):
        color=np.array(ImageColor.getrgb(spec[name+'_color']))
        colored=np.linalg.norm(pixels-color,axis=2)<60
        for ix in np.linspace(4,w-5,min(w-8,240)).astype(int):
            candidates=np.flatnonzero(colored[:,ix])
            if 1<=len(candidates)<=16:
                samples.append((name,ix/w,float(np.median(candidates))))
    if len(samples)<100:raise ValueError('not enough colored curve samples for source calibration')
    initial=np.array([*spec['origin'],spec['unit_x'],spec['unit_y']],dtype=float)
    lower=np.r_[np.maximum(0,initial[:2]-.035),np.maximum(.002,initial[2:]*.8)]
    upper=np.r_[np.minimum(1,initial[:2]+.035),np.minimum(1,initial[2:]*1.2)]
    grouped={name:np.array([[x,y] for curve,x,y in samples if curve==name]) for name in ('lower','upper')}
    def residual(values):
        ox,oy,ux,uy=values;parts=[]
        for name,points in grouped.items():
            if not len(points):continue
            xs=(points[:,0]-ox)/ux
            ys=(oy-expression_values(spec[name+'_expression'],xs)*uy)*h
            parts.extend(ys-points[:,1])
        return np.array(parts)
    fit=least_squares(residual,initial,bounds=(lower,upper),loss='soft_l1',f_scale=2,max_nfev=150,x_scale='jac')
    singular=np.linalg.svd(fit.jac,compute_uv=False)
    identifiable=bool(len(singular)==4 and singular[-1]>singular[0]*1e-6)
    refined=copy.deepcopy(spec)
    refined.update(origin=fit.x[:2].tolist(),unit_x=float(fit.x[2]),unit_y=float(fit.x[3]))
    checked=check_curve_fit(image,refined)
    receipt={'version':VERSION,'original_spec':spec,'refined_spec':refined,
             'samples':len(samples),'optimizer_success':bool(fit.success),'identifiable_four_parameters':identifiable,
             'final_curve_fit':checked,'expressions_changed':False,
             'scope':'Local axis calibration around model proposal using original colored curve pixels; does not certify semantic extraction or unlabeled axes.'}
    if not fit.success or not identifiable or not checked['passed']:
        raise ValueError('source calibration is unidentifiable or does not fit observed curves')
    return refined,receipt


@lru_cache(maxsize=16)
def _shaded_bytes(source_bytes,size,spec_json,restriction):
    import json
    spec=json.loads(spec_json);pixels=np.array(Image.frombytes('RGB',size,source_bytes))
    xs,_,_,mask=region_arrays(spec,size)
    if restriction=='positive_only':mask&=xs[None,:]>0
    elif restriction!='all':raise ValueError('unknown region control restriction')
    # Original colored curves, labels, and gray grid lines remain unchanged.
    blank=np.min(pixels,axis=2)>=248
    editable=mask&blank
    tint=np.array([90,184,210],dtype=float)
    pixels[editable]=np.rint(.62*pixels[editable]+.38*tint).astype(np.uint8)
    return pixels.tobytes()


def apply_region(image,spec,progress=1.,restriction='all'):
    import json
    if not math.isfinite(progress) or not 0<=progress<=1:raise ValueError('bounded reveal progress required')
    original=image.convert('RGB')
    shaded=Image.frombytes('RGB',original.size,_shaded_bytes(original.tobytes(),original.size,json.dumps(spec,sort_keys=True),restriction))
    if progress<1:
        cut=round(original.width*progress);shaded.paste(original.crop((cut,0,original.width,original.height)),(cut,0))
    return shaded


def bind_region(plan,attachment,spec):
    from .source_scene import bind_source
    # Reuse source viewport and teaching-line binding; text edits are validated separately.
    out=copy.deepcopy(plan)
    if len(out.get('scenes',[]))!=6:raise ValueError('region lesson requires six phases')
    words=sum(len(s.get('narration','').split()) for s in out['scenes'])
    budget=int(sum(s['duration_s'] for s in out['scenes'])*2.4)
    if words>budget:raise ValueError(f'Region lesson narration is too long: {words} words across six scenes, maximum {budget}. Shorten every scene while retaining all computed solution regions.')
    out['source_edits']=[{'id':'region','kind':'fill_between','spec':spec,'from_scene':3}]
    return bind_source(out,attachment,allow_regions=True)
