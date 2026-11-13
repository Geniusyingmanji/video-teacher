"""Pronounce supported inline math explicitly before TTS, without changing the script."""
from __future__ import annotations

import re

VERSION='localbench-math-speech-v1'


def verbalize_math(text):
    # Only single-letter function notation, not arbitrary parenthesized prose.
    text=re.sub(r'\b([A-Za-z])\(\s*([A-Za-z])\s*\)',r'\1 of \2',text)
    text=re.sub(r'(?<![\w.])(\d+(?:\.\d+)?)\s*([xyz])\b',r'\1 times \2',text)
    comparisons={'<=':'less than or equal to','>=':'greater than or equal to',
                 '!=':'not equal to','≤':'less than or equal to','≥':'greater than or equal to',
                 '≠':'not equal to','<':'less than','>':'greater than','=':'equals'}
    text=re.sub(r'<=|>=|!=|[≤≥≠<>=]',lambda m:' '+comparisons[m.group()]+' ',text)
    digits='zero one two three four five six seven eight nine'.split()
    def decimal(match):
        sign,integer,fraction=match.groups()
        spoken=digits[int(integer)] if len(integer)==1 else integer
        prefix={'-':'minus ','+':'plus ','':''}[sign]
        return prefix+spoken+' point '+' '.join(digits[int(x)] for x in fraction)
    text=re.sub(r'(?<![\w.])([+-]?)(\d+)\.(\d+)(?![\w.])',decimal,text)
    return re.sub(r'[ \t]+',' ',text).strip()
