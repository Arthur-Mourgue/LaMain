#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Calibration of the Feetech SCS0009 servos of the custom hand (5 dof).

Replaces the AmazingHand_Hand_FingerMiddlePos.py and AmazingHand_FingerTest.py
scripts. Drives one or more servos either to their reference position (--hold)
or in an open/close sweep (--cycle), to set each servo's MiddlePos.

Examples:
  # Set servo 1 to 0 deg (reference position to fit the horn)
  uv run python calib.py --ids 1 --middle 0 --hold

  # Open/close sweep of servo 1, reference 0
  uv run python calib.py --ids 1 --middle 0 --cycle

  # Adjust servo 1 reference to +3 deg
  uv run python calib.py --ids 1 --middle 3 --cycle

  # Go straight to an angle (MiddlePos + 180) with custom limits
  uv run python calib.py --ids 2 --middle 30 --goto 180

  # Wide sweep: open at -60, closed at +180
  uv run python calib.py --ids 2 --middle 30 --open -60 --close 180 --cycle

  # Interactive mode: type any angle on the fly
  uv run python calib.py --ids 2 --middle 30 --interactive

  # Thumb: 2 servos (base + flexion), adjusted together
  uv run python calib.py --ids 4,5 --middle 0,0 --cycle

  # Read current positions in degrees
  uv run python calib.py --ids 1,2,3,4,5 --read
"""
import argparse
import math
import sys
import time

from rustypot import Scs0009PyController

BAUDRATE = 1_000_000
TORQUE_ON = 1
TORQUE_OFF = 2


def _expand(values, n, name):
    if len(values) == 1:
        return values * n
    if len(values) != n:
        sys.exit(
            f"--{name}: {len(values)} value(s) for {n} servo(s). "
            f"Give 1 value or {n}."
        )
    return values


def _parse_ints(text):
    return [int(x) for x in text.replace(" ", "").split(",") if x != ""]


def _parse_floats(text):
    return [float(x) for x in str(text).replace(" ", "").split(",") if x != ""]


def parse_args():
    ap = argparse.ArgumentParser(
        description="Calibration of the SCS0009 servos of the custom hand.")
    ap.add_argument("--port", default="/dev/ttyACM0")
    ap.add_argument("--baudrate", type=int, default=BAUDRATE)
    ap.add_argument("--timeout", type=float, default=0.5)
    ap.add_argument("--ids", required=True,
                    help="comma-separated IDs, e.g. 1 or 4,5")
    ap.add_argument("--middle", default="0",
                    help="MiddlePos in degrees (1 value or one per ID)")
    ap.add_argument("--open", type=float, default=-30.0,
                    help="open delta in degrees (default -30)")
    ap.add_argument("--close", type=float, default=90.0,
                    help="close delta in degrees (default 90)")
    ap.add_argument("--signs", default="1",
                    help="sign per servo (1 by default), e.g. 1 or 1,-1")
    ap.add_argument("--speed", type=float, default=3.0,
                    help="speed 1..6 (6 = max)")
    ap.add_argument("--period", type=float, default=3.0,
                    help="duration of one phase in seconds (--cycle)")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--hold", action="store_true",
                      help="hold the servos at MiddlePos (default)")
    mode.add_argument("--cycle", action="store_true",
                      help="loop the open/close sweep")
    mode.add_argument("--goto", metavar="DELTA",
                      help="go to MiddlePos+DELTA (1 value or one per ID) then quit")
    mode.add_argument("-i", "--interactive", action="store_true",
                      help="drive the angles on the fly (keyboard dialog)")
    mode.add_argument("--read", action="store_true",
                      help="print the current positions then quit")
    return ap.parse_args()


def _scalar(value):
    return value[0] if isinstance(value, (list, tuple)) else value


def _report(c, ids, middle):
    for sid, mid in zip(ids, middle):
        pos = _scalar(c.read_present_position(sid))
        load = _scalar(c.read_present_load(sid))
        temp = _scalar(c.read_present_temperature(sid))
        print(
            f"  servo {sid}: {math.degrees(pos):+.1f} deg "
            f"(rel MiddlePos {math.degrees(pos) - mid:+.1f}) "
            f"| load {load} | {temp} C"
        )


def _interactive(c, ids, middle, signs, args, go):
    print("Interactive mode. Commands:")
    print("  <deg>        go to MiddlePos+deg (e.g. 180, or 180,-180 for 2 servos)")
    print("  f / o        close / open (MiddlePos+close / +open)")
    print("  r            return to MiddlePos")
    print("  s <speed>    change the speed (1..6)")
    print("  l            re-read position / load / temperature")
    print("  q            quit")
    go(0.0, "reference (MiddlePos)")
    time.sleep(min(1.5, max(0.2, args.period / 2)))
    _report(c, ids, middle)
    while True:
        try:
            line = input("angle> ").strip()
        except EOFError:
            break
        if not line:
            continue
        if line in ("q", "quit", "exit"):
            break
        if line in ("f", "close"):
            go(args.close, "close ")
        elif line in ("o", "open"):
            go(args.open, "open")
        elif line in ("r", "ref", "0"):
            go(0.0, "reference")
        elif line in ("l", "ls"):
            _report(c, ids, middle)
            continue
        elif line.startswith("s"):
            parts = line.split()
            if len(parts) == 2:
                try:
                    speed = float(parts[1])
                except ValueError:
                    print("  usage: s <speed 1..6>")
                    continue
                for sid in ids:
                    c.write_goal_speed(sid, speed)
                print(f"  speed = {speed}")
            else:
                print("  usage: s <speed 1..6>")
            continue
        else:
            try:
                deltas = _parse_floats(line)
            except ValueError:
                print("  enter a number, f, o, r, s <v>, l or q")
                continue
            go(deltas, "goto  ")
        time.sleep(min(1.5, max(0.2, args.period / 2)))
        _report(c, ids, middle)


def main():
    args = parse_args()
    ids = _parse_ints(args.ids)
    n = len(ids)
    middle = _expand(_parse_floats(args.middle), n, "middle")
    signs = _expand(_parse_floats(args.signs), n, "signs")

    c = Scs0009PyController(
        serial_port=args.port,
        baudrate=args.baudrate,
        timeout=args.timeout,
    )

    if args.read:
        _report(c, ids, middle)
        return

    for sid in ids:
        c.write_torque_enable(sid, TORQUE_ON)
        c.write_goal_speed(sid, float(args.speed))

    def go(deltas, label):
        if not isinstance(deltas, (list, tuple)):
            deltas = _expand([float(deltas)], n, "delta")
        for sid, mid, sign, d in zip(ids, middle, signs, deltas):
            c.write_goal_position(sid, math.radians(mid + sign * d))
        detail = ", ".join(
            f"{sid}={mid + sign * d:+.0f}deg"
            for sid, mid, sign, d in zip(ids, middle, signs, deltas)
        )
        print(f"  {label}: {detail}")

    print(f"Servos {ids} | MiddlePos={middle} | signs={signs}")
    try:
        if args.goto is not None:
            deltas = _expand(_parse_floats(args.goto), n, "goto")
            go(deltas, "goto  ")
            time.sleep(min(2.0, max(0.3, args.period)))
            _report(c, ids, middle)
        elif args.interactive:
            _interactive(c, ids, middle, signs, args, go)
        elif args.cycle:
            print("Open/close sweep. Ctrl-C to stop.")
            while True:
                go(args.close, "close ")
                time.sleep(args.period)
                go(args.open, "open")
                time.sleep(args.period)
        else:
            go(0.0, "reference (MiddlePos)")
            print("Holding. Ctrl-C to stop.")
            while True:
                time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        for sid in ids:
            c.write_torque_enable(sid, TORQUE_OFF)
        print("Torque off.")


if __name__ == "__main__":
    main()
