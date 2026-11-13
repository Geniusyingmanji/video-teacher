"""Small executable-state adapters derived from public tasks, never judge references.

Initial coverage is deliberately explicit: binary search, angle-sum demonstrations,
and Na/Cl electron transfer. Other tasks retain the general scene backend.
"""
from __future__ import annotations

import math
import re
from fractions import Fraction

from PIL import ImageDraw


def binary_search(values,target):
    if not values or any(a>b for a,b in zip(values,values[1:])):
        raise ValueError('binary search requires a nonempty sorted array')
    low,high=0,len(values)-1
    trace=[]
    while low<=high:
        mid=(low+high)//2
        value=values[mid]
        decision='found' if value==target else 'right' if value<target else 'left'
        trace.append({'low':low,'high':high,'mid':mid,'value':value,'decision':decision})
        if decision=='found':return trace
        if decision=='right':low=mid+1
        else:high=mid-1
    return trace


def derive_state(public):
    text=public['prompt_text']
    lowered=text.lower()
    if 'convex lens' in lowered and 'parallel' in lowered and ('focal point' in lowered or 'focus' in lowered):
        count=re.search(r'(\d+)\s+parallel rays',lowered)
        # Current schematic supports the task's explicit three-ray construction.
        if count and int(count[1])==3:
            return {'kind':'converging_lens','ray_count':3,
                    'facts':['Use an ideal thin converging lens in air and parallel rays close to the principal axis.',
                             'Show exactly three incoming rays, all horizontal and mutually parallel until they reach the lens plane.',
                             'At the lens plane, the upper ray bends down and the lower ray bends up. The axial ray stays straight.',
                             'The outgoing segments meet at one common point F on the principal axis to the right of the lens.',
                             'Light continues through F and the rays separate beyond it; F is not a stopping point.',
                             'The diagram uses the ideal thin-lens approximation: bending is drawn at the lens plane, not as detailed trajectories inside glass.',
                             'Distances and angles are schematic, not measured values. Explain which rays are parallel and how their intersection identifies F.'],
                    'phases':['setup','parallel','refraction','focus','beyond_focus','check']}
    equation=re.search(r'(?<![a-z0-9])(-?\d+)\s*x\s*([+-])\s*(\d+)\s*=\s*(-?\d+)',lowered)
    if equation and any(word in lowered for word in ('solve','find x')):
        a=int(equation[1]);b=int(equation[3])*(1 if equation[2]=='+' else -1);c=int(equation[4])
        if a:
            solution=Fraction(c-b,a)
            return {'kind':'linear_equation','a':a,'b':b,'c':c,'solution':str(solution),
                    'facts':[f'Original equation: {a}x + ({b}) = {c}.',
                             f'Subtract {b} from BOTH sides: {a}x = {c-b}.',
                             f'Divide BOTH sides by nonzero {a}: x = {solution}.',
                             f'Check by substitution into the ORIGINAL equation: {a}*({solution})+({b})={c}.',
                             'Explain that applying the same reversible operation to both sides preserves equality.'],
                    'phases':['setup','balance','subtract','divide','check','recap']}
    cross=re.search(r'cross\s+([A-Za-z]{2})\s*[x×]\s*([A-Za-z]{2})',text,re.I)
    if cross and len({x.upper() for x in cross[1]+cross[2]})==1:
        parents=[cross[1],cross[2]]
        outcomes=[''.join(sorted([a,b],key=lambda x:(x.islower(),x))) for a in parents[0] for b in parents[1]]
        recessive=parents[0][0].lower()*2
        fraction=Fraction(outcomes.count(recessive),4)
        return {'kind':'punnett','parents':parents,'outcomes':outcomes,'recessive':recessive,'fraction':str(fraction),
                'facts':[f'Cross {parents[0]} x {parents[1]} at one locus.',
                         f'Each parent contributes one allele under standard Mendelian segregation. Four equally likely allele-pair combinations: {outcomes}.',
                         f'Homozygous recessive genotype is {recessive}; it occurs in {outcomes.count(recessive)} of the four cells, fraction {fraction}.',
                         'Distinguish heterozygous from homozygous genotypes. Do not equate all recessive-allele carriers with homozygous recessive offspring.'],
                'phases':['parents','gametes','grid','offspring','count','answer']}
    if 'binary search' in lowered:
        numbers=re.search(r'\[\s*(-?\d+(?:\s*,\s*-?\d+)+)\s*\]',text)
        target=re.search(r'(?:value|target)\s+(-?\d+)',text,re.I)
        if not numbers or not target:return None
        values=[int(x.strip()) for x in numbers.group(1).split(',')]
        if len(values)>12:return None
        value=int(target.group(1));trace=binary_search(values,value)
        return {'kind':'binary_search','values':values,'target':value,'trace':trace,
                'facts':[f'Zero-based indexing. Sorted array {values}. Target {value}.',
                         f'Use mid=floor((low+high)/2). Exact trace: {trace}',
                         'Do not invent extra comparisons after finding the target.',
                         'A one-comparison example still allows explanation of sortedness, bounds, midpoint, comparison and verification.'],
                'phases':['setup','bounds','midpoint','compare','result','recap']}
    if 'triangle' in lowered and '180' in lowered and ('interior angle' in lowered or 'angle sum' in lowered):
        return {'kind':'triangle_sum','facts':['For Euclidean plane triangles, interior angles sum to 180 degrees.',
                    'Start with three different triangles. Label interior angles alpha, beta, gamma.',
                    'Highlight the three interior sectors; move and rotate the sectors to a common vertex.',
                    'Placed side by side, these sectors form a straight angle. Sizes/shape do not change the sum.',
                    'This is a visual angle rearrangement demonstration; do not invent measured angle values.'],
                'phases':['examples','identify','highlight','rearrange','straight_angle','recap']}
    if re.search(r'\bNa\b',text) and re.search(r'\bCl\b',text) and 'electron' in lowered and 'neutral' in lowered:
        return {'kind':'electron_transfer','facts':['Na has 11 protons and initially 11 electrons: shells 2,8,1.',
                    'Cl has 17 protons and initially 17 electrons: shells 2,8,7.',
                    'Transfer exactly one electron from Na to Cl. Protons do not move.',
                    'Na then has 10 electrons and charge +1; Cl has 18 electrons and charge -1.',
                    'Total electron count 28 and net charge 0 are conserved. Opposite ions attract.',
                    'A schematic shell diagram is used; do not claim realistic orbital trajectories.'],
                'phases':['neutral','valence','transfer','ions','check','recap']}
    return None


def assign_state(plan,state):
    if state is None:return plan
    if len(plan['scenes'])!=6:raise ValueError('state-backed pilot requires exactly six scenes')
    if state['kind']=='triangle_sum':
        from .triangle import compile_sequence
        compiled,receipt=compile_sequence(plan)
        if receipt['status']=='compiled':
            from .triangle_examples import compile_examples
            return compile_examples(compiled)[0]
    for scene,phase in zip(plan['scenes'],state['phases']):
        scene['state_visual']={'state':state,'phase':phase}
        # This backend renders its own primitives. Model placeholders are unused.
        scene['primitives']=[{'type':'text','x':.1,'y':.1,'text':phase}]
        scene['arithmetic_checks']=[]
    from .teaching_cues import bind
    return bind(plan)


def electron_position(t, radius):
    """Executed electron trajectory shared by drawing and label placement."""
    sx,sy=280+radius,254
    tx,ty=737+radius*math.cos(7*math.pi/4),254+radius*math.sin(7*math.pi/4)
    return sx*(1-t)+tx*t,sy*(1-t)+ty*t-48*math.sin(math.pi*t)


def draw_state(image,spec,progress,motion_paths=None):
    from .scene import font
    draw=ImageDraw.Draw(image)
    state,phase=spec['state'],spec['phase']
    dark,blue,orange,green='#183550','#1769aa','#df8428','#18826b'
    boxes=[]
    def label(x,y,text,color=dark,size=25):
        face=font(size)
        boxes.append({'text':text,'bbox':list(draw.textbbox((x,y),text,font=face,anchor='mm'))})
        draw.text((x,y),text,font=face,fill=color,anchor='mm')
    if state['kind']=='triangle_cut':
        from .triangle import draw_triangle
        return draw_triangle(image,spec,progress)
    if state['kind']=='converging_lens':
        from .geometry import parallel_rays_to_focus
        lens_x,focus_x,axis_y=450,720,270
        ray_end=900 if phase in {'beyond_focus','check'} else focus_x
        draw.line((85,axis_y,945,axis_y),fill='#8a969f',width=2)
        polygon=[]
        for sign,ys in ((-1,range(155,386,2)),(1,range(385,154,-2))):
            for y in ys:
                normalized=(y-axis_y)/115
                polygon.append((lens_x+sign*24*math.sqrt(max(0,1-normalized**2)),y))
        draw.polygon(polygon,fill='#e5f3fc',outline=blue,width=3)
        label(lens_x,130,'Thin convex lens',size=23)
        label(845,380,'Principal axis',size=21)
        rays=parallel_rays_to_focus([190,270,350],start_x=105,lens_x=lens_x,focus_x=focus_x,end_x=ray_end,axis_y=axis_y)
        for ray,color in zip(rays,(blue,orange,green)):
            a,b=ray['incoming'];draw.line((tuple(a),tuple(b)),fill=color,width=4)
            x,y=280,a[1];draw.polygon([(x,y),(x-11,y-5),(x-11,y+5)],fill=color)
            if phase not in {'setup','parallel'}:
                a,b=ray['outgoing'];fraction=max(.05,min(1,progress*1.7)) if phase=='refraction' else 1
                tip=(a[0]+(b[0]-a[0])*fraction,a[1]+(b[1]-a[1])*fraction)
                draw.line((tuple(a),tip),fill=color,width=4)
        if phase in {'focus','beyond_focus','check'}:
            draw.ellipse((focus_x-5,axis_y-5,focus_x+5,axis_y+5),fill='#9e3654')
            label(focus_x,235,'F',size=27)
        phrases={'setup':'Ideal thin-lens model; not drawn to scale.',
                 'parallel':'All three incident rays remain horizontal.',
                 'refraction':'Bending is represented at the lens plane.',
                 'focus':'All three outgoing rays meet at the same F.',
                 'beyond_focus':'The rays continue beyond F and separate.',
                 'check':'Parallel before the lens; one common focus after it.'}
        label(512,419,phrases[phase],size=23)
    elif state['kind']=='linear_equation':
        a,b,c=state['a'],state['b'],state['c'];solution=state['solution']
        sign='+' if b>=0 else '−'
        original=f'{a}x {sign} {abs(b)} = {c}'
        label(512,148,'Keep both sides equal',size=28)
        if phase in {'setup','balance'}:
            draw.rounded_rectangle((225,205,475,290),radius=12,outline=blue,width=3,fill='#eaf2fb')
            draw.rounded_rectangle((552,205,802,290),radius=12,outline=blue,width=3,fill='#eaf2fb')
            label(350,247,f'{a}x {sign} {abs(b)}',size=36);label(677,247,str(c),size=36);label(512,247,'=',size=36)
            label(512,370,'Use the same operation on each side.',size=26)
        elif phase=='subtract':
            if spec.get('teaching_cues'):
                label(512,202,original,size=32)
                label(512,268,f'{a}x {sign} {abs(b)} − ({b})  =  {c} − ({b})',orange,size=32)
                label(512,330,f'{a}x = {c-b}',green,size=36)
                label(512,405,'The same subtraction preserves equality.',size=23)
            else:
                label(512,215,original,size=34)
                label(512,276,f'Subtract ({b}) from each side',orange,size=26)
                label(512,354,f'{a}x = {c-b}',green,size=37)
        elif phase=='divide':
            if spec.get('teaching_cues'):
                label(512,202,f'{a}x = {c-b}',size=32)
                label(512,268,f'({a}x) / ({a})  =  ({c-b}) / ({a})',orange,size=32)
                label(512,330,f'x = {solution}',green,size=36)
                label(512,405,'Each side is divided by the same nonzero number.',size=23)
            else:
                label(512,208,f'{a}x = {c-b}',size=34)
                label(512,278,f'Divide each side by {a}',orange,size=26)
                label(512,354,f'x = ({c-b}) / ({a}) = {solution}',green,size=34)
        else:
            label(512,207,f'x = {solution}',green,size=38)
            label(512,290,f'{a} × ({solution}) {sign} {abs(b)} = {c}',size=32)
            label(512,372,'Substitution checks the original equation.',size=25)
    elif state['kind']=='punnett':
        parents=state['parents'];outcomes=state['outcomes']
        label(512,139,f'{parents[0]} × {parents[1]}',size=32)
        x0,y0,w,h=414,204,135,72
        for j,allele in enumerate(parents[1]):label(x0+j*w+w/2,182,allele,blue,size=27)
        for i,allele in enumerate(parents[0]):label(x0-30,y0+i*h+h/2,allele,orange,size=27)
        reveal=phase in {'grid','offspring','count','answer'}
        for i,genotype in enumerate(outcomes):
            col,row=i%2,i//2;x,y=x0+col*w,y0+row*h
            selected=phase in {'count','answer'} and genotype==state['recessive']
            draw.rectangle((x,y,x+w,y+h),fill='#d6efe3' if selected else '#f0f5fb',outline=green if selected else blue,width=3)
            if reveal:label(x+w/2,y+h/2,genotype,green if selected else dark,size=30)
        if phase in {'count','answer'}:
            label(512,398,f"{state['recessive']}: {outcomes.count(state['recessive'])} of 4 = {state['fraction']}",green,size=29)
        else:label(512,400,'One allele from each parent.',size=26)
    elif state['kind']=='binary_search':
        values=state['values'];trace=state['trace']
        trace_index=min(len(trace)-1,int(progress*len(trace))) if phase=='compare' else len(trace)-1 if phase in {'result','recap'} else 0
        row=trace[trace_index]
        n=len(values);w=min(87,830/n);left=(1024-w*n)/2
        show_mid=phase in {'midpoint','compare','result','recap'}
        for i,value in enumerate(values):
            x=left+i*w
            fill='#d7f0e5' if show_mid and i==row['mid'] else '#eaf1f8'
            draw.rounded_rectangle((x+3,201,x+w-3,262),radius=8,fill=fill,outline=green if show_mid and i==row['mid'] else blue,width=3)
            label(x+w/2,232,str(value),size=29)
            label(x+w/2,287,str(i),size=18)
        label(512,139,f"Find {state['target']} in a sorted array",size=28)
        if phase in {'bounds','midpoint','compare','result','recap'}:
            label(290,176,f"low = {row['low']}",blue,size=21)
            label(735,176,f"high = {row['high']}",blue,size=21)
        if show_mid:
            label(512,331,f"mid = floor(({row['low']} + {row['high']}) / 2) = {row['mid']}",size=26)
        if phase in {'compare','result','recap'}:
            operator='=' if row['value']==state['target'] else '<' if row['value']<state['target'] else '>'
            result='NOT FOUND' if phase in {'result','recap'} and all(t['decision']!='found' for t in trace) else row['decision'].upper()
            label(512,380,f"array[{row['mid']}] = {row['value']} {operator} {state['target']}  |  {result}",green,size=25)
    elif state['kind']=='triangle_sum':
        colors=[blue,orange,green]
        if phase=='examples':
            triangles=[[(116,343),(290,343),(186,170)],[(427,343),(597,343),(427,170)],[(692,343),(928,343),(741,273)]]
            for points in triangles:draw.polygon(points,fill='#edf4fb',outline=blue,width=4)
            label(512,398,'Different shapes. The same angle sum.',size=27)
            return boxes
        points=[(260,365),(730,365),(434,140)]
        sectors=[]
        for i,p in enumerate(points):
            q,r=points[(i+1)%3],points[(i+2)%3]
            a=math.degrees(math.atan2(q[1]-p[1],q[0]-p[0]))%360
            b=math.degrees(math.atan2(r[1]-p[1],r[0]-p[0]))%360
            diff=(b-a)%360
            start,sweep=(a,diff) if diff<=180 else (b,360-diff)
            sectors.append((p,start,sweep))
        moving=phase=='rearrange'
        joined=phase in {'straight_angle','recap'}
        if not joined:draw.polygon(points,fill='#f8fafc',outline=dark,width=3)
        cumulative=180
        for i,((x,y),start,sweep) in enumerate(sectors):
            amount=progress if moving else 1 if joined else 0
            tx,ty=512,313
            cx,cy=x*(1-amount)+tx*amount,y*(1-amount)+ty*amount
            target_start=cumulative;cumulative+=sweep
            angle_delta=(target_start-start+180)%360-180
            angle=start+angle_delta*amount
            radius=48*(1-amount)+110*amount
            draw.pieslice((cx-radius,cy-radius,cx+radius,cy+radius),angle,angle+sweep,fill=colors[i],outline=colors[i])
            if not moving and not joined:
                offset=[(-35,28),(38,27),(0,-24)][i]
                label(x+offset[0],y+offset[1],['α','β','γ'][i],colors[i],25)
        if joined:
            draw.line((334,313,690,313),fill=dark,width=3)
            label(512,378,'α + β + γ = 180°',size=31)
        elif moving:label(512,406,'Move and rotate each angle without changing it.',size=23)
    elif state['kind']=='electron_transfer':
        transfer=phase=='transfer';after=phase in {'ions','check','recap'}
        t=progress if transfer else 1 if after else 0
        layout=spec.get('teaching_cues',{}).get('particle_layout')
        countable=layout in {'countable-v1','countable-v2'}
        radii=[32,62,96] if countable else [23,47,76]
        dot_radius=6 if countable else 5
        for center,element,protons,shells in [(280,'Na',11,[2,8,1]),(737,'Cl',17,[2,8,7])]:
            ionized=(t>0 if element=='Na' else t>=1)
            electron_count=protons+(-1 if element=='Na' else 1)*(1 if ionized else 0)
            visible_counts=[]
            for shell_i,count in enumerate(shells):
                radius=radii[shell_i]
                draw.ellipse((center-radius,254-radius,center+radius,254+radius),outline='#b9cbdc',width=2)
                slots=8 if shell_i==2 and element=='Cl' else count
                if shell_i==2 and element=='Na' and t>0:count=0
                if shell_i==2 and element=='Cl' and t>=1:count=8
                visible_counts.append(count)
                for k in range(count):
                    angle=2*math.pi*k/slots
                    x,y=center+radius*math.cos(angle),254+radius*math.sin(angle)
                    draw.ellipse((x-dot_radius,y-dot_radius,x+dot_radius,y+dot_radius),fill=blue)
            draw.ellipse((center-15,239,center+15,269),fill=orange)
            # Plain charge signs are scientifically equivalent and supported by
            # the cross-platform font; Arial lacked superscript +/- on macOS.
            label(center,134 if countable else 147,element+('+' if element=='Na' else '-') if ionized else element,size=32)
            label(center,378 if countable else 361,f'{protons} protons | {electron_count} electrons',size=22)
            if countable:
                label(center,414,'Shells: '+' + '.join(map(str,visible_counts))+f' = {electron_count}',size=21)
        if 0<t<1:
            x,y=electron_position(t,radii[2])
            draw.ellipse((x-7,y-7,x+7,y+7),fill=green)
            cue_y=185
            if layout=='countable-v2':
                from .flow import path_intersects_box
                points=[electron_position(i/300,radii[2]) for i in range(301)]
                for candidate_y in (185,134):
                    a,b,c,d=draw.textbbox((510,candidate_y),'one electron →',font=font(24),anchor='mm')
                    if not path_intersects_box(points,(a-9,b-9,c+9,d+9)):
                        cue_y=candidate_y;break
                else:raise ValueError('no trajectory-clear electron label position')
            label(510,cue_y,'one electron →',green,size=24)
        if transfer and motion_paths is not None:
            motion_paths.append({'object':'transferred_electron','radius':7,
                                 'points':[electron_position(i/300,radii[2]) for i in range(301)]})
        if countable and after:
            for start,end in [(407,474),(610,543)]:
                draw.line((start,272,end,272),fill=green,width=4)
                direction=1 if end>start else -1
                draw.polygon([(end,272),(end-direction*12,265),(end-direction*12,279)],fill=green)
            label(510,216,'Electrostatic',green,size=21)
            label(510,242,'attraction',green,size=21)
        if not countable:
            if phase=='check':label(512,407,'Electrons: 10 + 18 = 28     Net charge: +1 − 1 = 0',size=24)
            elif after:label(512,407,'Opposite charges attract.',size=26)
    return boxes
