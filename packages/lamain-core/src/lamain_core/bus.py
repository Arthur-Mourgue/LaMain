# SPDX-License-Identifier: Apache-2.0
"""Servo access: common interface, real rustypot driver and FakeBus.

The rest of the library only talks to `ServoBus`, never directly to rustypot.
Register addresses are avoided: access goes through rustypot's register table
(`Scs0009PyController.registers()`), by name.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Protocol

TORQUE_ON = 1
TORQUE_OFF = 2
TORQUE_FREE = 3

TORQUE_REG_FULL_SCALE = 1000  # register 16: 1000 = 100 %
SERVO_MIN_TICK = 0
SERVO_MAX_TICK = 1023
STALL_LOAD = 1000.0           # load (present_load) when stalled at 100 % torque


class BusError(RuntimeError):
    pass


class ServoNotFound(BusError):
    pass


def _scalar(value):
    """rustypot returns a sequence (one element) even for a single servo."""
    if isinstance(value, (int, float, bool)):
        return value
    try:
        return value[0]
    except (TypeError, IndexError, KeyError):
        return value


class ServoBus(Protocol):
    """Minimal interface used by calibration, safety and controller."""

    simulated: bool

    def scan(self) -> dict[int, int]: ...
    def read_position(self, servo_id: int) -> int: ...
    def read_load(self, servo_id: int) -> int: ...
    def read_temperature(self, servo_id: int) -> int: ...
    def read_voltage(self, servo_id: int) -> float: ...
    def read_moving(self, servo_id: int) -> int: ...
    def write_goal(self, servo_id: int, ticks: int) -> None: ...
    def set_goal_speed(self, servo_id: int, speed: float) -> None: ...
    def set_torque_enable(self, servo_id: int, on: bool) -> None: ...
    def read_torque_enable(self, servo_id: int) -> int: ...
    def set_torque_limit_pct(self, servo_id: int, pct: float) -> None: ...
    def read_register(self, servo_id: int, name: str) -> int: ...
    def write_register(self, servo_id: int, name: str, value: int) -> None: ...
    def step(self) -> None: ...
    def close(self) -> None: ...


# --------------------------------------------------------------------------- #
# Real driver
# --------------------------------------------------------------------------- #
class RustypotBus:
    simulated = False

    def __init__(self, port: str, baudrate: int = 1_000_000, timeout: float = 0.2):
        from rustypot import Scs0009PyController

        self._port = port
        self._c = Scs0009PyController(
            serial_port=port, baudrate=baudrate, timeout=timeout
        )

    def scan(self) -> dict[int, int]:
        return dict(self._c.scan())

    def _require(self, servo_id: int) -> None:
        if not self._c.ping(servo_id):
            raise ServoNotFound(f"servo {servo_id} not on the bus")

    def _read_reg(self, servo_id: int, name: str) -> int:
        try:
            return int(_scalar(self._c.read_register(servo_id, name, retries=2)))
        except Exception as exc:
            raise BusError(f"read {name} servo {servo_id}: {exc}") from exc

    def _write_reg(self, servo_id: int, name: str, value: int) -> None:
        try:
            self._c.write_register(servo_id, name, int(value), retries=2)
        except Exception as exc:
            raise BusError(f"write {name} servo {servo_id}: {exc}") from exc

    def read_position(self, servo_id: int) -> int:
        # Raw 0-1023 register (rustypot's "raw" API uses a different multi-turn
        # representation, unrelated to ticks).
        return self._read_reg(servo_id, "present_position")

    def read_load(self, servo_id: int) -> int:
        return self._read_reg(servo_id, "present_load")

    def read_temperature(self, servo_id: int) -> int:
        return self._read_reg(servo_id, "present_temperature")

    def read_voltage(self, servo_id: int) -> float:
        # present_voltage register: raw value in 0.1 V.
        return self._read_reg(servo_id, "present_voltage") / 10.0

    def read_moving(self, servo_id: int) -> int:
        return self._read_reg(servo_id, "moving")

    def write_goal(self, servo_id: int, ticks: int) -> None:
        self._write_reg(servo_id, "goal_position", int(ticks))

    def set_goal_speed(self, servo_id: int, speed: float) -> None:
        # rustypot: 0 = max speed, 1..6 = speed step.
        try:
            self._c.write_goal_speed(servo_id, float(speed))
        except Exception as exc:
            raise BusError(f"write goal_speed servo {servo_id}: {exc}") from exc

    def set_torque_enable(self, servo_id: int, on: bool) -> None:
        try:
            self._c.write_torque_enable(servo_id, TORQUE_ON if on else TORQUE_OFF)
        except Exception as exc:
            raise BusError(f"torque servo {servo_id}: {exc}") from exc

    def read_torque_enable(self, servo_id: int) -> int:
        return self._read_reg(servo_id, "torque_enable")

    def set_torque_limit_pct(self, servo_id: int, pct: float) -> None:
        value = int(round(max(0.0, min(100.0, pct)) * TORQUE_REG_FULL_SCALE / 100.0))
        self._write_reg(servo_id, "max_torque_limit", value)

    def read_register(self, servo_id: int, name: str) -> int:
        return self._read_reg(servo_id, name)

    def write_register(self, servo_id: int, name: str, value: int) -> None:
        self._write_reg(servo_id, name, int(value))

    def step(self) -> None:  # hardware does not need to be advanced
        return None

    def close(self) -> None:
        self._c.close()


# --------------------------------------------------------------------------- #
# FakeBus (tests, CI)
# --------------------------------------------------------------------------- #
@dataclass
class FakeServo:
    servo_id: int
    stop_min: int
    stop_max: int
    assembly_position: int = 511
    position: int = 511
    goal: int = 511
    speed_ticks: int = 24          # ticks travelled per step()
    torque_enabled: bool = True
    torque_limit_pct: float = 100.0
    fault: str | None = None       # "absent" | "overtemp"
    noise: int = 0
    friction_load: int = 20


class FakeBus:
    """Hand simulator: stops, dead center, load at the stop, noise, faults."""

    simulated = True

    def __init__(self, servos: list[FakeServo], seed: int = 0):
        self._servos = {s.servo_id: s for s in servos}
        self._rng = random.Random(seed)

    # construction ---------------------------------------------------------- #
    @classmethod
    def standard_hand(cls, model, seed: int = 0) -> "FakeBus":
        from . import units

        servos = []
        for name in model.calibration_order:
            j = model.joint(name)
            half = units.deg_to_ticks(j.nominal_travel_deg / 2.0)
            asm = j.assembly_position
            stop_min = max(SERVO_MIN_TICK, asm - half)
            stop_max = min(SERVO_MAX_TICK, asm + half)
            servos.append(
                FakeServo(
                    servo_id=j.servo_id,
                    stop_min=stop_min,
                    stop_max=stop_max,
                    assembly_position=asm,
                    position=asm,
                    goal=asm,
                )
            )
        return cls(servos, seed=seed)

    # protocol -------------------------------------------------------------- #
    def scan(self) -> dict[int, int]:
        return {
            s.servo_id: 7777
            for s in self._servos.values()
            if s.fault != "absent"
        }

    def _s(self, servo_id: int) -> FakeServo:
        s = self._servos.get(servo_id)
        if s is None or s.fault == "absent":
            raise ServoNotFound(f"servo {servo_id} not on the bus")
        return s

    def read_position(self, servo_id: int) -> int:
        return self._s(servo_id).position

    def read_load(self, servo_id: int) -> int:
        s = self._s(servo_id)
        blocked = s.goal > s.stop_max or s.goal < s.stop_min
        if not blocked or not s.torque_enabled:
            return s.friction_load
        return int(STALL_LOAD * s.torque_limit_pct / 100.0)

    def read_temperature(self, servo_id: int) -> int:
        s = self._s(servo_id)
        return 70 if s.fault == "overtemp" else 30

    def read_voltage(self, servo_id: int) -> float:
        self._s(servo_id)
        return 6.0

    def read_moving(self, servo_id: int) -> int:
        s = self._s(servo_id)
        return 1 if s.goal != s.position else 0

    def write_goal(self, servo_id: int, ticks: int) -> None:
        self._s(servo_id).goal = int(ticks)

    def set_goal_speed(self, servo_id: int, speed: float) -> None:
        self._s(servo_id)  # validate existence

    def set_torque_enable(self, servo_id: int, on: bool) -> None:
        self._s(servo_id).torque_enabled = bool(on)

    def read_torque_enable(self, servo_id: int) -> int:
        return TORQUE_ON if self._s(servo_id).torque_enabled else TORQUE_OFF

    def set_torque_limit_pct(self, servo_id: int, pct: float) -> None:
        self._s(servo_id).torque_limit_pct = max(0.0, min(100.0, pct))

    def read_register(self, servo_id: int, name: str) -> int:
        self._s(servo_id)
        if name == "present_temperature":
            return self.read_temperature(servo_id)
        if name == "present_voltage":
            return int(self.read_voltage(servo_id) * 10)
        if name == "max_torque_limit":
            return int(self._s(servo_id).torque_limit_pct * TORQUE_REG_FULL_SCALE / 100)
        raise BusError(f"register {name!r} not simulated")

    def write_register(self, servo_id: int, name: str, value: int) -> None:
        self._s(servo_id)
        if name == "max_torque_limit":
            self._s(servo_id).torque_limit_pct = value * 100.0 / TORQUE_REG_FULL_SCALE
        else:
            raise BusError(f"register {name!r} not simulated")

    def step(self) -> None:
        for s in self._servos.values():
            if s.fault == "absent" or not s.torque_enabled:
                continue
            if s.goal > s.position:
                s.position = min(s.goal, s.position + s.speed_ticks)
            elif s.goal < s.position:
                s.position = max(s.goal, s.position - s.speed_ticks)
            if s.noise:
                s.position += self._rng.randint(-s.noise, s.noise)
            s.position = max(s.stop_min, min(s.stop_max, s.position))

    def close(self) -> None:
        return None
