#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Calibration des servos Feetech SCS0009 de la main custom (5 dof).

Remplace les scripts AmazingHand_Hand_FingerMiddlePos.py et
AmazingHand_FingerTest.py. Pilote un ou plusieurs servos soit a leur position
de reference (--hold), soit en balayage ouvert/ferme (--cycle), afin de regler
le MiddlePos de chaque servo.

Exemples :
  # Met le servo 1 a 0 deg (position de reference pour emboiter le palonnier)
  uv run python calib.py --ids 1 --middle 0 --hold

  # Balayage ouvert/ferme du servo 1, reference 0
  uv run python calib.py --ids 1 --middle 0 --cycle

  # Ajuste la reference du servo 1 a +3 deg
  uv run python calib.py --ids 1 --middle 3 --cycle

  # Va directement a un angle (MiddlePos + 180) avec les limites personnalisees
  uv run python calib.py --ids 2 --middle 30 --goto 180

  # Balayage large : ouvert a -60, ferme a +180
  uv run python calib.py --ids 2 --middle 30 --open -60 --close 180 --cycle

  # Mode interactif : tape l'angle voulu a la volee
  uv run python calib.py --ids 2 --middle 30 --interactive

  # Pouce : 2 servos (base + flexion), ajustes ensemble
  uv run python calib.py --ids 4,5 --middle 0,0 --cycle

  # Lecture des positions courantes en degres
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
            f"--{name} : {len(values)} valeur(s) pour {n} servo(s). "
            f"Donne 1 valeur ou {n}."
        )
    return values


def _parse_ints(text):
    return [int(x) for x in text.replace(" ", "").split(",") if x != ""]


def _parse_floats(text):
    return [float(x) for x in str(text).replace(" ", "").split(",") if x != ""]


def parse_args():
    ap = argparse.ArgumentParser(
        description="Calibration des SCS0009 de la main custom.")
    ap.add_argument("--port", default="/dev/ttyACM0")
    ap.add_argument("--baudrate", type=int, default=BAUDRATE)
    ap.add_argument("--timeout", type=float, default=0.5)
    ap.add_argument("--ids", required=True,
                    help="IDs separes par des virgules, ex: 1 ou 4,5")
    ap.add_argument("--middle", default="0",
                    help="MiddlePos en degres (1 valeur ou une par ID)")
    ap.add_argument("--open", type=float, default=-30.0,
                    help="Delta ouvert en degres (defaut -30)")
    ap.add_argument("--close", type=float, default=90.0,
                    help="Delta ferme en degres (defaut 90)")
    ap.add_argument("--signs", default="1",
                    help="Signe par servo (1 par defaut), ex: 1 ou 1,-1")
    ap.add_argument("--speed", type=float, default=3.0,
                    help="Vitesse 1..6 (6 = max)")
    ap.add_argument("--period", type=float, default=3.0,
                    help="Duree d'une phase en secondes (--cycle)")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--hold", action="store_true",
                      help="Maintient les servos a MiddlePos (defaut)")
    mode.add_argument("--cycle", action="store_true",
                      help="Balayage ouvert/ferme en boucle")
    mode.add_argument("--goto", metavar="DELTA",
                      help="Va a MiddlePos+DELTA (1 valeur ou une par ID) puis quitte")
    mode.add_argument("-i", "--interactive", action="store_true",
                      help="Pilote les angles a la volee (dialogue au clavier)")
    mode.add_argument("--read", action="store_true",
                      help="Affiche les positions courantes puis quitte")
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
            f"| couple {load} | {temp} C"
        )


def _interactive(c, ids, middle, signs, args, go):
    print("Mode interactif. Commandes :")
    print("  <deg>        va a MiddlePos+deg (ex: 180, ou 180,-180 pour 2 servos)")
    print("  f / o        ferme / ouvert (MiddlePos+close / +open)")
    print("  r            revient a MiddlePos")
    print("  s <vitesse>  change la vitesse (1..6)")
    print("  l            relit position / couple / temperature")
    print("  q            quitte")
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
        if line in ("f", "ferme"):
            go(args.close, "ferme ")
        elif line in ("o", "ouvert"):
            go(args.open, "ouvert")
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
                    print("  usage: s <vitesse 1..6>")
                    continue
                for sid in ids:
                    c.write_goal_speed(sid, speed)
                print(f"  vitesse = {speed}")
            else:
                print("  usage: s <vitesse 1..6>")
            continue
        else:
            try:
                deltas = _parse_floats(line)
            except ValueError:
                print("  entre un nombre, f, o, r, s <v>, l ou q")
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

    print(f"Servos {ids} | MiddlePos={middle} | signes={signs}")
    try:
        if args.goto is not None:
            deltas = _expand(_parse_floats(args.goto), n, "goto")
            go(deltas, "goto  ")
            time.sleep(min(2.0, max(0.3, args.period)))
            _report(c, ids, middle)
        elif args.interactive:
            _interactive(c, ids, middle, signs, args, go)
        elif args.cycle:
            print("Balayage ouvert/ferme. Ctrl-C pour arreter.")
            while True:
                go(args.close, "ferme ")
                time.sleep(args.period)
                go(args.open, "ouvert")
                time.sleep(args.period)
        else:
            go(0.0, "reference (MiddlePos)")
            print("Maintenu. Ctrl-C pour arreter.")
            while True:
                time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nArret.")
    finally:
        for sid in ids:
            c.write_torque_enable(sid, TORQUE_OFF)
        print("Couple coupe.")


if __name__ == "__main__":
    main()
