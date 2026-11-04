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
            if name in invalid_calls:
                findings.append(f'line {node.lineno}: {name} is not a supported Manim primitive; {invalid_calls[name]}')
            points = node.args if name == 'Polygon' else node.args[:2] if name in ('Line', 'Arrow') else node.args[:1] if name == 'Dot' else []
            for point in points:
                if isinstance(point, (ast.List, ast.Tuple)) and len(point.elts) == 2:
                    findings.append(f'line {node.lineno}: {name} point needs [x, y, 0], not a two-coordinate vector')
    if findings:
        raise ValueError('Lesson code preflight failed; correct ALL findings while preserving teaching content and timing:\n'
                         + '\n'.join(dict.fromkeys(findings)))

