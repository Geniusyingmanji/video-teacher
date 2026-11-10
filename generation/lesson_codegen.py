"""Generation settings and fast rejection of known invalid lesson scene code."""
import ast


def is_code_request(prompt):
    text = str(prompt).lstrip()
    return text.startswith('Write complete runnable Manim') or (
        'Manim' in text[:800] and '**Current Code:**' in text)


def validate_code(source):
    """Report actionable failures before expensive rendering; never rewrite content."""
    tree = ast.parse(source)
    findings = []
    runtime_methods = {'begin_teaching_step', 'teaching_caption', 'source_text', 'source_curve', 'source_highlight'}
    invalid_calls = {'Check': 'draw a check with two Line objects',
                     'Checkmark': 'draw a check with two Line objects',
                     'angle_between': 'use angle_between_vectors, or Angle with real Line objects'}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name in runtime_methods:
                findings.append(f'line {node.lineno}: do not redefine runtime method {node.name}')
            if node.name == 'construct' and any(isinstance(child, ast.Pass) or
                    isinstance(child, ast.Constant) and child.value is Ellipsis for child in ast.walk(node)):
                findings.append(f'line {node.lineno}: construct contains an unfinished pass or ellipsis placeholder')
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            name = node.func.id
            if name in ('Text', 'MarkupText') and any(keyword.arg == 'font_weight' for keyword in node.keywords):
                findings.append(f'line {node.lineno}: {name} uses unsupported font_weight; use weight=BOLD instead')
            if name in invalid_calls:
                findings.append(f'line {node.lineno}: {name} is not a supported Manim primitive; {invalid_calls[name]}')
            points = node.args if name == 'Polygon' else node.args[:2] if name in ('Line', 'Arrow') else node.args[:1] if name == 'Dot' else []
            for point in points:
                if isinstance(point, (ast.List, ast.Tuple)) and len(point.elts) == 2:
                    findings.append(f'line {node.lineno}: {name} point needs [x, y, 0], not a two-coordinate vector')
    if findings:
        raise ValueError('Lesson code preflight failed; correct ALL findings while preserving teaching content and timing:\n'
                         + '\n'.join(dict.fromkeys(findings)))



def validate_source_ownership(source):
    """Source scenes obtain their one fixed reference from the runtime."""
    tree=ast.parse(source)
    duplicates=[node.lineno for node in ast.walk(tree) if isinstance(node,ast.Call)
                and ((isinstance(node.func,ast.Name) and node.func.id=='ImageMobject')
                     or (isinstance(node.func,ast.Attribute) and node.func.attr=='ImageMobject'))]
    aliases=set()
    def owned(node):
        if isinstance(node,ast.Attribute) and node.attr=='animate':return owned(node.value)
        return (isinstance(node,ast.Attribute) and node.attr=='source_image'
                and isinstance(node.value,ast.Name) and node.value.id=='self') or (isinstance(node,ast.Name) and node.id in aliases)
    assignments=[node for node in ast.walk(tree) if isinstance(node,ast.Assign)]
    for _ in assignments:
        for node in assignments:
            if owned(node.value):aliases.update(target.id for target in node.targets if isinstance(target,ast.Name))
    mutations={'scale','stretch','shift','move_to','to_edge','to_corner','rotate','set_width','set_height','scale_to_fit_width','scale_to_fit_height','copy','deepcopy','set_opacity','set_color','fade'}
    animations={'Indicate','FadeIn','FadeOut','Transform','ReplacementTransform','Create','Write','Uncreate'}
    for node in ast.walk(tree):
        if not isinstance(node,ast.Call):continue
        if isinstance(node.func,ast.Attribute) and node.func.attr in mutations and owned(node.func.value):
            duplicates.append(node.lineno)
        if isinstance(node.func,ast.Name) and node.func.id in animations and any(owned(arg) for arg in node.args):
            duplicates.append(node.lineno)
    if duplicates:
        raise ValueError('Runtime owns the source image: remove source image construction or mutation at lines '
                         + ', '.join(map(str,duplicates))
                         + '. Use self.source_image without moving or resizing it; use source_text/curve/highlight for edits.')
