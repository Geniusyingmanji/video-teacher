"""An unfolded nephron/collecting-duct schematic from one connected filtrate route."""
from __future__ import annotations

import copy
import math

from .common import public_case

VERSION='nephron-route-v1'
COLORS={'proximal':'#946000','loop':'#176e91','distal':'#7848a0','collecting':'#975533'}


def topology():
    return {'capsule_outlet':[207,245],
        'proximal':[[207,245],[245,245],[245,211],[281,211],[281,245],[315,245],[315,211],[351,211],[351,245],[370,245]],
        'loop':[[370,245],[370,352],[389,378],[431,378],[450,352],[450,245]],
        'distal':[[450,245],[476,245],[476,216],[510,216],[510,247],[546,247],[546,216],[581,216],[581,247],[620,247],[620,235],[700,235]],
        'collecting':[[700,175],[700,235],[700,403]],
        'collecting_join_index':1}


def validate_topology(state):
    if set(state)!={'capsule_outlet','proximal','loop','distal','collecting','collecting_join_index'}:
        raise ValueError('invalid nephron route fields')
    for name in ('proximal','loop','distal','collecting'):
        path=state[name]
        if not isinstance(path,list) or len(path)!={'proximal':10,'loop':6,'distal':12,'collecting':3}[name]:
            raise ValueError('invalid bounded tubule route')
        for p in path:
            if (not isinstance(p,list) or len(p)!=2 or
                any(type(x) not in (int,float) or not math.isfinite(x) for x in p) or
                not 70<=p[0]<=950 or not 120<=p[1]<=414):
                raise ValueError('tubule point outside the schematic panel')
        if any(a==b for a,b in zip(path,path[1:])):raise ValueError('zero-length tubule segment')
    if state['capsule_outlet']!=state['proximal'][0]:raise ValueError('proximal tubule must begin at the capsule outlet')
    if state['proximal'][-1]!=state['loop'][0] or state['loop'][-1]!=state['distal'][0]:
        raise ValueError('filtrate route is disconnected or out of order')
    j=state['collecting_join_index']
    if type(j) is not int or not 0<j<len(state['collecting'])-1 or state['distal'][-1]!=state['collecting'][j]:
        raise ValueError('distal tubule must join the collecting duct')
    p=state['loop'];ys=[q[1] for q in p]
    if p[0][1]!=p[-1][1] or max(ys)<=p[0][1]+80 or p[0][0]>=p[-1][0]:
        raise ValueError('loop must descend and return on a distinct ascending limb')
    if not (p[0][0]==p[1][0]<p[2][0]<p[3][0]<p[4][0]==p[5][0]
            and ys[0]<ys[1]<ys[2]==ys[3]>ys[4]>ys[5]):
        raise ValueError('loop must have a single U-shaped descending/ascending route')
    duct=state['collecting']
    if not (duct[0][0]==duct[1][0]==duct[2][0] and duct[0][1]<duct[1][1]<duct[2][1]):
        raise ValueError('collecting duct must continue downward past its junction')
    return state


def rounded(points,radius=9):
    """Round corners without moving route endpoints or joining separate segments."""
    result=[list(points[0])]
    for a,b,c in zip(points,points[1:],points[2:]):
        da,dc=math.dist(a,b),math.dist(b,c);r=min(radius,da/3,dc/3)
        before=[b[i]+(a[i]-b[i])*r/da for i in range(2)]
        after=[b[i]+(c[i]-b[i])*r/dc for i in range(2)]
        result.append(before)
        for k in range(1,7):
            t=k/6;result.append([(1-t)**2*before[i]+2*(1-t)*t*b[i]+t*t*after[i] for i in range(2)])
    result.append(list(points[-1]));return result


def diagram(phase,state=None):
    if type(phase) is not int or not 0<=phase<=5:raise ValueError('invalid nephron teaching phase')
    state=validate_topology(topology() if state is None else state);parts=[]
    def xy(p):return {'x':(p[0]-64)/896,'y':(p[1]-112)/302}
    def line(a,b,color='#496276',width=2,kind='line'):
        return {'type':kind,**xy(a),'x2':(b[0]-64)/896,'y2':(b[1]-112)/302,'color':color,'stroke':width}
    def text(x,y,value,size=22,color='#203b55'):
        return {'type':'text',**xy((x,y)),'text':value,'font_size':size,'align':'center','color':color}
    def path(points,color,width):
        return {'type':'polyline','x':0,'y':0,'closed':False,
                'points':[[(x-64)/896,(y-112)/302] for x,y in points],'color':color,'stroke':width}
    # Capsule is open at its urinary pole. Blood stays in a separate capillary route.
    parts.append({'type':'arc',**xy((160,245)),'r':48/302,'start_angle':15,'end_angle':345,
                  'color':'#4e7180','stroke':4})
    glomerulus=[[128,229],[151,220],[177,231],[141,238],[173,249],[149,261],[130,248],[166,240],[146,225],[136,255]]
    parts.append(path(rounded(glomerulus,4),'#ad3e42',4))
    parts.extend([line((75,210),(128,229),'#ad3e42',4,'arrow'),
                  line((136,255),(75,290),'#ad3e42',4,'arrow')])
    active={0:set(COLORS),1:set(),2:{'proximal'},3:{'loop'},4:{'distal','collecting'},5:set(COLORS)}[phase]
    for name in COLORS:parts.append(path(rounded(state[name]),COLORS[name],9 if name in active else 6))
    # Direction arrows lie on named, connected straight portions of that same route.
    for name,i in [('proximal',2),('loop',0),('loop',4),('distal',10),('collecting',1)]:
        a,b=state[name][i:i+2];distance=math.dist(a,b)
        unit=[(b[k]-a[k])/distance for k in range(2)];mid=[(a[k]+b[k])/2 for k in range(2)]
        aa=[mid[k]-8*unit[k] for k in range(2)];bb=[mid[k]+8*unit[k] for k in range(2)]
        parts.append(line(aa,bb,'#183b51',3,'arrow'))
    parts.extend([line((187,250),(226,245),'#1a6985',3,'arrow'),
                  line((162,160),(152,222)),line((173,333),(177,290)),
                  line((752,192),(700,206)),
                  text(160,145,'Glomerulus',22,'#9d2d34'),
                  text(94,183,'Afferent',18,'#9d2d34'),text(94,309,'Efferent',18,'#9d2d34'),
                  text(171,350,"Bowman's capsule",20),text(255,286,'Filtrate',20,'#1a6985'),
                  text(307,172,'Proximal tubule',22,COLORS['proximal']),
                  text(410,408,'Loop of Henle',22,COLORS['loop']),
                  text(545,178,'Distal tubule',22,COLORS['distal']),
                  text(805,175,'Collecting duct',22,COLORS['collecting']),
                  text(800,404,'To urine outflow',20),text(799,126,'Schematic; not to scale',18)])
    if phase==2:
        parts.extend([line((315,249),(315,294),'#226c42',3,'arrow'),text(305,316,'Reabsorption',20,'#226c42')])
    if phase==3:
        parts.extend([line((365,311),(309,311),'#226c42',3,'arrow'),text(300,337,'H2O out',20,'#226c42'),
                      line((455,311),(523,311),'#226c42',3,'arrow'),text(525,337,'Salt out',20,'#226c42')])
    if phase==4:
        parts.extend([line((706,330),(793,330),'#226c42',3,'arrow'),text(816,299,'ADH: water out',20,'#226c42')])
    return parts


def validate_scene(scene):
    spec=scene['nephron_path']
    if spec.get('version')!=VERSION:raise ValueError('invalid nephron diagram version')
    if scene['primitives']!=diagram(spec['phase'],spec['state']):
        raise ValueError('nephron primitives differ from the connected route')


def bind(plan,case):
    result=copy.deepcopy(plan);unsupported={'status':'unsupported','version':VERSION}
    text=public_case(case).get('prompt_text','').lower();scenes=result.get('scenes',[])
    if not (all(word in text for word in ('human nephron','glomerulus','proximal','henle','distal','collecting duct')) and len(scenes)==6):
        return result,unsupported
    if any(s.get('source_visual') or s.get('state_visual') or s.get('nephron_path') for s in scenes):return result,unsupported
    required=[('nephron','kidney'),('glomerulus',"bowman's"),('proximal','reabsorption'),
              ('descending','ascending'),('distal','collecting duct'),('filtration','flow')]
    if any(not all(w in s.get('narration','').lower() for w in words) for s,words in zip(scenes,required)):
        return result,unsupported
    state=validate_topology(topology())
    for i,s in enumerate(scenes):
        s['primitives']=diagram(i,state)
        s['nephron_path']={'version':VERSION,'phase':i,'state':copy.deepcopy(state)}
    return result,{'status':'compiled','version':VERSION,'scene_indices':list(range(6)),
        'preserves_narration':True,'route':['capsular space','proximal tubule','loop descending','loop ascending','distal tubule','collecting duct'],
        'scope':'Unfolded connected schematic, not anatomical scale, histology, concentration simulation or JGA anatomy. Blood path distinct from filtrate route.'}
