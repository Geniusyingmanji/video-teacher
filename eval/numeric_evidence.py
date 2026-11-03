"""Exact arithmetic anchors from current task text; never infer unseen values."""
from decimal import Decimal, InvalidOperation, localcontext
import re

NUMBER = r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)'
EQUATION = re.compile(rf'(?<![\w.])({NUMBER})\s*([+*/×÷−-])\s*({NUMBER})\s*=\s*({NUMBER})(?![\w.])')


def arithmetic_anchors(required):
    out = []
    seen = set()
    for item in required:
        for match in EQUATION.finditer(item['text']):
            left, operator, right, stated = match.groups()
            identity = match.group(0)
            if identity in seen:
                continue
            seen.add(identity)
            a, b = Decimal(left), Decimal(right)
            try:
                with localcontext() as context:
                    context.prec = 40
                    actual = {'+':lambda:a+b, '-':lambda:a-b, '−':lambda:a-b,
                              '*':lambda:a*b, '×':lambda:a*b,
                              '/':lambda:a/b, '÷':lambda:a/b}[operator]()
            except (InvalidOperation, ZeroDivisionError):
                continue
            out.append({'task_identity':identity, 'computed_result':str(actual),
                        'stated_result_correct':actual == Decimal(stated)})
    return out
