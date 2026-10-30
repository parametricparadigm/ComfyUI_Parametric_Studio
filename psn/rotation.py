"""Deterministic rotation: pick option i for (unit, index) so that within one unit nothing repeats until the list is used up, neighbouring units start at different places, and the same inputs always give the same choice. No randomness; reproducible outfits/looks/variations."""
from math import gcd
def stride(n):
    s = max(1, n // 2 + 1)
    while gcd(s, n) != 1: s += 1
    return s
def rotate(options, unit, index, offset=0):
    if not options: raise ValueError("no options to rotate")
    n = len(options); return options[(unit * stride(n) + index + offset) % n]
def schedule(options, units, per_unit, offset=0): return [[rotate(options, u, i, offset) for i in range(per_unit)] for u in range(units)]
