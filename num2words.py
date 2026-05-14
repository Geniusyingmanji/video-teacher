"""Tiny local fallback for the external num2words package.

SmolVLM's processor imports ``num2words.num2words`` to verbalize image/frame
indices. The full package is preferable, but this fallback keeps offline smoke
tests working for small non-negative integers.
"""

from __future__ import annotations


ONES = [
    "zero", "one", "two", "three", "four", "five", "six", "seven", "eight",
    "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen",
    "sixteen", "seventeen", "eighteen", "nineteen",
]
TENS = [
    "", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy",
    "eighty", "ninety",
]


def num2words(number: int | str, *args, **kwargs) -> str:
    n = int(number)
    if n < 0:
        return "minus " + num2words(-n)
    if n < 20:
        return ONES[n]
    if n < 100:
        q, r = divmod(n, 10)
        return TENS[q] if r == 0 else f"{TENS[q]}-{ONES[r]}"
    if n < 1000:
        q, r = divmod(n, 100)
        return f"{ONES[q]} hundred" if r == 0 else f"{ONES[q]} hundred {num2words(r)}"
    if n < 10000:
        q, r = divmod(n, 1000)
        return f"{num2words(q)} thousand" if r == 0 else f"{num2words(q)} thousand {num2words(r)}"
    return str(n)
