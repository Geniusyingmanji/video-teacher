"""Bounded offline mathematical checks; never an expert truth certificate."""
from __future__ import annotations

import ast
import re

import sympy as sp

VERSION = 'scientific-consistency-v1'


def expression(text, symbols, denominators=None):
    """Construct SymPy trees from a tiny AST, without eval/sympify on model text."""
    if not isinstance(text, str) or len(text) > 240:
        raise ValueError('bounded mathematical expression required')
    tree = ast.parse(text, mode='eval')
    if len(list(ast.walk(tree))) > 100:
        raise ValueError('expression too complex')
    def visit(node):
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            if abs(node.value) > 1000000:
                raise ValueError('numeric literal too large')
            return sp.Rational(str(node.value))
        if isinstance(node, ast.Name) and re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,23}', node.id):
            return symbols.setdefault(node.id, sp.Symbol(node.id, real=True))
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
            return -visit(node.operand) if isinstance(node.op, ast.USub) else visit(node.operand)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in {'sin', 'cos'} and len(node.args) == 1 and not node.keywords:
            return {'sin': sp.sin, 'cos': sp.cos}[node.func.id](visit(node.args[0]))
        if isinstance(node, ast.BinOp):
            a, b = visit(node.left), visit(node.right)
            if isinstance(node.op, ast.Add): return a + b
            if isinstance(node.op, ast.Sub): return a - b
            if isinstance(node.op, ast.Mult): return a * b
            if isinstance(node.op, ast.Div):
                if b == 0: raise ValueError('division by zero')
                if denominators is not None:denominators.append(b)
                return a / b
            if isinstance(node.op, ast.Pow) and b.is_Integer and abs(b) <= 4:
                if b<0 and denominators is not None:denominators.append(a)
                value=a**b
                if any(p.exp.is_Integer and abs(p.exp)>16 for p in value.atoms(sp.Pow)):
                    raise ValueError('nested power too large')
                return value
        raise ValueError('unsupported mathematical syntax')
    result = visit(tree.body)
    if result.has(sp.zoo, sp.nan, sp.oo, -sp.oo):
        raise ValueError('nonfinite mathematical expression')
    return result


def check_chain(spec):
    """Only proven equivalences pass; domain-changing steps remain unverified."""
    if not isinstance(spec, dict) or set(spec) - {'equations', 'nonzero', 'substitutions'}:
        raise ValueError('invalid derivation declaration')
    equations = spec.get('equations')
    if not isinstance(equations, list) or not 2 <= len(equations) <= 12:
        raise ValueError('derivation needs 2..12 equations')
    names = spec.get('nonzero', [])
    if not isinstance(names, list) or len(names) > 24 or any(not isinstance(n,str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,23}', n) for n in names):
        raise ValueError('invalid nonzero assumptions')
    symbols = {n: sp.Symbol(n, real=True, nonzero=True) for n in names}
    substitutions = spec.get('substitutions', {})
    if not isinstance(substitutions, dict) or len(substitutions) > 12:
        raise ValueError('bounded substitutions required')
    replacements = {}
    denominators = []
    for key, value in substitutions.items():
        if not isinstance(key,str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,23}',key):
            raise ValueError('invalid substitution symbol')
        symbol=expression(key,symbols)
        replacement=expression(value,symbols,denominators)
        if symbol.is_nonzero is True and replacement.is_zero is True:raise ValueError('substitution contradicts nonzero assumption')
        replacements[symbol] = replacement
    residuals = []
    for equation in equations:
        if not isinstance(equation,str) or equation.count('=') != 1:
            raise ValueError('each equation needs one equality')
        left, right = [expression(t.strip(),symbols,denominators) for t in equation.split('=')]
        denominators.extend([sp.denom(left),sp.denom(right)])
        residual=sp.factor((left-right).subs(replacements, simultaneous=True))
        if residual.has(sp.zoo,sp.nan,sp.oo,-sp.oo):raise ValueError('nonfinite substituted equation')
        residuals.append(residual)
    checks = []
    for index, (a, b) in enumerate(zip(residuals,residuals[1:])):
        ratio = sp.cancel(a/b) if b != 0 else None
        equivalent = (a == b == 0) or (ratio is not None and ratio.is_nonzero is True)
        checks.append({'from':index,'to':index+1,'status':'proven_equivalent' if equivalent else 'unverified',
                       'reason':'Nonzero residual multiplier proved under declared assumptions.' if equivalent else 'Equivalence not proved; do not infer truth from the final formula.'})
    # Denominator assumptions must be explicit; cancellation must not hide poles.
    domains = [str(d) for d in denominators if d.subs(replacements,simultaneous=True).is_nonzero is not True]
    return {'status':'proven_equivalent' if all(c['status']=='proven_equivalent' for c in checks) and not domains else 'unverified',
            'steps':checks,'unresolved_denominators':domains,'assumptions':names,
            'scope':'Algebraic equivalence only; physical premises and declared assumptions require independent review.'}


def audit_text(text):
    """Recognize the demonstrated Snell-law regression, including Unicode/LaTeX."""
    normalized = text.lower().replace('₁','1').replace('₂','2').replace('θ','theta').replace('\\theta','theta')
    normalized = normalized.replace('Δ'.lower(), 'delta').replace('\\sin','sin').replace('\\cdot','*').replace('\\delta','delta')
    for token in ('\\left','\\right','{','}'):
        normalized=normalized.replace(token,'')
    problems = []
    if not re.search(r'snell|refraction|refracti|huygens', normalized):
        return problems
    time_factor = r'(?:\s*(?:\*|·)?\s*(?:delta\s*t|dt|t))?'
    factor = r'v[_ ]?1' + time_factor + r'\s*(?:\*|·)?\s*sin\s*\(?\s*theta[_ ]?1\s*\)?\s*=\s*v[_ ]?2' + time_factor + r'\s*(?:\*|·)?\s*sin\s*\(?\s*theta[_ ]?2\s*\)?'
    for match in re.finditer(factor, normalized):
        # Explicitly labelled counterexamples are not affirmative physics claims.
        context = normalized[max(0,match.start()-90):match.start()]
        suffix = normalized[match.end():match.end()+70]
        if re.match(r'\s*(?:is (?:wrong|incorrect|false)|does not hold)',suffix):continue
        if re.search(r'\b(?:incorrect|wrong|false|not|avoid|misconception)\b[^.;\n]*$',context):
            continue
        problems.append({'kind':'snell_velocity_relation','normalized_quote':match.group(),
            'reason':'This velocity product does not imply Snell law under v=c/n; the invariant is sin(theta1)/v1 = sin(theta2)/v2.',
            'affected':['conceptual_correctness.reasoning','conceptual_correctness.relationships']})
    return problems


def audit_case(case, *, public_only=False, contract=None):
    fields = ['prompt_text'] if public_only else ['prompt_text','expected_concepts','expected_visual_elements','expected_narrative_order','discipline_specific_rubric']
    issues = []
    for field in fields:
        values = ([(item['quote']) for item in contract.get('reference_items',[]) if item.get('field')==field and item.get('role') in {'factual_reference','public_requirement'}]
                  if contract is not None and field!='prompt_text' else case.get(field, []))
        for index, value in enumerate(values if isinstance(values,list) else [values]):
            if isinstance(value,str):
                issues.extend({'field':field,'index':index,**x} for x in audit_text(value))
    return {'version':VERSION,'status':'conflict' if issues else 'no_known_conflict', 'issues':issues,
            'scope':'Bounded known-error screening, not an exhaustive scientific or expert review.'}


def validate_public(case):
    result = audit_case(case,public_only=True)
    if result['issues']:
        raise ValueError('public task scientific conflict; correct and refreeze the task before generation: '+result['issues'][0]['reason'])
    return result


def validate_plan_math(plan, case=None):
    receipts = []
    if not isinstance(plan,dict) or not isinstance(plan.get('scenes'),list):raise ValueError('plan needs scenes')
    for i,scene in enumerate(plan.get('scenes',[])):
        if not isinstance(scene,dict):raise ValueError('scene must be an object')
        strings = [scene.get(k,'') for k in ('title','caption','narration','slide_text')]
        strings += [p.get('text','') for p in scene.get('primitives',[]) if p.get('type')=='text']
        # Lesson context is included so isolated formula labels are checked too.
        context = (case or {}).get('prompt_text','').split('\n')[0]+' '+ ' '.join(strings)
        if audit_text(context): raise ValueError(f'scene {i}: inconsistent Snell velocity relation')
        if 'derivation' in scene:
            receipt = check_chain(scene['derivation']);receipts.append({'scene':i,**receipt})
            if receipt['status']!='proven_equivalent':raise ValueError(f'scene {i}: mathematical derivation unverified')
    return {'version':VERSION,'derivations':receipts}
