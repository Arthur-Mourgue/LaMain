"""Conversions d'unites pour les servos Feetech SCS0009.

D'apres la fiche SCS0009 (spec La Main) : la plage mecanique utile est de 300
deg sur les registres 0-1023, soit 1024 pas pour 300 deg -> 0,293 deg/pas.
On travaille en ticks bruts dans toute la logique bas niveau ; les radians
n'apparaissent qu'a la frontiere de l'API `HandController`.
"""
from __future__ import annotations

import math

MECH_RANGE_DEG = 300.0
TICKS_PER_TURN = 1024
TICKS_PER_DEG = TICKS_PER_TURN / MECH_RANGE_DEG
DEG_PER_TICK = MECH_RANGE_DEG / TICKS_PER_TURN
TICKS_PER_RAD = TICKS_PER_TURN / math.radians(MECH_RANGE_DEG)
RAD_PER_TICK = math.radians(MECH_RANGE_DEG) / TICKS_PER_TURN


def rad_to_ticks(rad: float) -> int:
    return int(round(rad * TICKS_PER_RAD))


def ticks_to_rad(ticks: float) -> float:
    return ticks * RAD_PER_TICK


def deg_to_ticks(deg: float) -> int:
    return int(round(deg * TICKS_PER_DEG))


def ticks_to_deg(ticks: float) -> float:
    return ticks * DEG_PER_TICK
