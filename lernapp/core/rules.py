"""Reine Spielregeln: XP, Level, Combo.

Keine GUI, kein I/O, keine Zufallsquelle. Alles hier ist eine reine Funktion
und damit direkt testbar.
"""
from __future__ import annotations

# XP-Schwelle je Level. Index 0 == Level 1.
LEVEL_XP: tuple[int, ...] = (0, 50, 150, 300, 500, 750, 1000, 1500, 2000, 3000)

MAX_LEVEL = len(LEVEL_XP)

# Combo-Stufen: ab dieser Combo gilt dieser Multiplikator (absteigend gelesen).
_COMBO_STUFEN: tuple[tuple[int, float], ...] = ((7, 3.0), (4, 2.0), (2, 1.5))

BASIS_XP = 10
XP_PRO_WIEDERHOLUNG = 5


def get_level(xp: int) -> int:
    """Level fuer einen XP-Stand. Beginnt bei 1, gedeckelt auf MAX_LEVEL."""
    level = 1
    for i, schwelle in enumerate(LEVEL_XP):
        if xp >= schwelle:
            level = i + 1
    return min(level, MAX_LEVEL)


def combo_mul(combo: int) -> float:
    """XP-Multiplikator fuer eine laufende Combo."""
    for ab, mul in _COMBO_STUFEN:
        if combo >= ab:
            return mul
    return 1.0


def xp_gain(streak: int, combo: int) -> int:
    """XP fuer eine richtige Antwort.

    `streak`  - Streak der Karte NACH dieser Antwort (>= 1)
    `combo`   - Combo NACH dieser Antwort (>= 1)
    """
    roh = BASIS_XP + (streak - 1) * XP_PRO_WIEDERHOLUNG
    return round(roh * combo_mul(combo))


def level_fortschritt(xp: int) -> tuple[int, int | None, int | None]:
    """(level, xp_seit_level, xp_bis_naechstes_level).

    Bei MAX_LEVEL sind die beiden letzten Werte None.
    """
    level = get_level(xp)
    if level >= MAX_LEVEL:
        return level, None, None
    vorher, naechste = LEVEL_XP[level - 1], LEVEL_XP[level]
    return level, xp - vorher, naechste - vorher
