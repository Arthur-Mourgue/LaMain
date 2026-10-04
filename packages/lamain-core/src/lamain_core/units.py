# SPDX-License-Identifier: Apache-2.0
"""Unit conversions for Feetech SCS0009 servos.

From the SCS0009 datasheet: the usable mechanical range is 300 deg over the
0-1023 registers, i.e. 1024 steps for 300 deg -> 0.293 deg/step. Low-level
logic works in raw ticks; radians only appear at the `HandController` API edge.
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
