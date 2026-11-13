"""Optional symbolic spatial primitive for the ordinary lesson-generation path."""
import copy

from .common import digest
from .spatial_solver import VERSION, construct_graph

SYSTEM = '''
Optional spatial construction for an explicitly requested tetrahedral relationship:
you may use exactly one primitive in a scene:
{type:"symbolic_spatial_graph",spec:{nodes:[{id:"center",label:"C"},...],
links:[{source:"center",target:"neighbor",kind:"bond"|"arrow",color:"#14283e"}],
constraints:[{kind:"tetrahedral",nodes:[centerID,neighbor1,neighbor2,neighbor3,neighbor4],
prompt_quote:"exact public-task span"},...]}}.
Node IDs are short ASCII identifiers; labels at most12characters; optional color.
Supply NO coordinates or camera. Code constructs one regular tetrahedron, then
can add nodes using opposite_sides [center,knownNeighbor,newNode]; directed_link
[source,target] checks an actual arrow. Every constraint needs an exact public
task quote. All nodes must be determined by these relations. No other constraints,
multiple centers or molecule simulations are supported by this constructor.
The whole scene panel is occupied; no accompanying primitives or motion fields.
Code chooses a readable camera and uses wedge/hashed-wedge depth marks with a
legend. Labels are dark, outlines retain color. This checks your declared geometry,
not whether your semantic interpretation is true. Do not use this primitive when
the public task does not request tetrahedral geometry, when it would replace a
required source image, or for transition/product states not justified by the task.
Other scenes may use the usual primitives. Keep the complete teaching narrative.
'''


def compile_plan(plan, public_task):
    """Compile on a copy, retaining the exact symbolic input in a side receipt."""
    candidate = copy.deepcopy(plan)
    records = []
    for index, scene in enumerate(candidate.get('scenes', [])):
        primitives = scene.get('primitives', [])
        chosen = [p for p in primitives if isinstance(p, dict) and p.get('type') == 'symbolic_spatial_graph']
        if not chosen:
            continue
        if scene.get('state_visual') or scene.get('source_visual'):
            raise ValueError('symbolic spatial construction cannot replace protected state/source visuals')
        if len(primitives) != 1 or set(chosen[0]) != {'type', 'spec'}:
            raise ValueError('symbolic spatial graph owns its panel and accepts only type/spec')
        spec = chosen[0]['spec']
        compiled = construct_graph(spec, public_task['prompt_text'])
        scene['primitives'] = [{'type': 'spatial_graph', 'graph': compiled['graph']}]
        records.append({'scene': index, 'symbolic_input': spec, 'compiled': compiled})
    return candidate, {'version': VERSION, 'status': 'compiled' if records else 'not_selected',
                       'input_plan_hash': digest(plan), 'output_plan_hash': digest(candidate),
                       'constructions': records, 'semantic_binding_status': 'model_proposed_unverified'}
