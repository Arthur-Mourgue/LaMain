"""CLI `lamain` for La Main.

Subcommands:
  lamain bus scan | set-id OLD NEW | dump ID
  lamain assemble [--release]
  lamain calibrate [--verify] [--repeat N] [--tag NAME] [--simulate]
  lamain studio [--calibration FILE] [--step DEG]
  lamain demo play NAME [--loops N] [--speed X]
  lamain gesture list | show NAME | rename OLD NEW | delete NAME
  lamain episode list | show NAME | rename OLD NEW | delete NAME
  lamain inspect [JOINT] [--plot]
  lamain collect-collisions

Real commands always end with torque off (including on Ctrl+C). Use
`--simulate` to run the logic on a FakeBus.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from datetime import datetime
from pathlib import Path

from lamain_core import units
from lamain_core.bus import FakeBus, RustypotBus, _scalar
from lamain_core.calibration import CalibrationAbort, calibrate_hand
from lamain_core.controller import HandController, load_calibration
from lamain_core.demos import (
    EpisodeStore,
    GestureStore,
    PlayOptions,
    Player,
    PlayerStopped,
    Step,
)
from lamain_core.diagnostics import plot as diag_plot
from lamain_core.diagnostics import sweep_joint
from lamain_core.diagnostics import write_csv as diag_write_csv
from lamain_core.model import default_model_path, load_hand_model
from lamain_core import paths
from lamain_cli.keys import KeyReader
from lamain_cli.studio import Studio

REPO_ROOT = paths.repo_root()
DEFAULT_LOGS_DIR = paths.logs_dir()
DEFAULT_GESTURE_DIR = paths.gesture_dir()
DEFAULT_EPISODE_DIR = paths.episode_dir()
DEFAULT_SERIAL = paths.DEFAULT_SERIAL


def _bus(args, model):
    if getattr(args, "simulate", False):
        return FakeBus.standard_hand(model)
    port = getattr(args, "port", None) or model.bus.port
    return RustypotBus(port, model.bus.baudrate)


def _model(args):
    return load_hand_model(getattr(args, "model", None) or default_model_path())


def _confirm(message: str, assume_yes: bool) -> bool:
    if assume_yes:
        return True
    try:
        answer = input(f"{message} [o/N] ").strip().lower()
    except EOFError:
        return False
    return answer in ("o", "oui", "y", "yes")


def _new_run_dir(kind: str, label: str | None = None, base=None) -> Path:
    """Create logs/<kind>/<timestamp>[_<label>][_N]/ for one run, so outputs stay
    segregated. A number is appended if the same name already exists."""
    root = Path(base or DEFAULT_LOGS_DIR)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    stem = f"{timestamp}_{label}" if label else timestamp
    directory = root / kind / stem
    n = 2
    while directory.exists():
        directory = root / kind / f"{stem}_{n}"
        n += 1
    directory.mkdir(parents=True, exist_ok=True)
    return directory


# --------------------------------------------------------------------------- #
# F1 - bus
# --------------------------------------------------------------------------- #
def cmd_bus(args) -> int:
    from rustypot import Scs0009PyController

    port = args.port or _model(args).bus.port
    c = Scs0009PyController(serial_port=port, baudrate=1_000_000, timeout=0.5)
    try:
        if args.action == "scan":
            found = c.scan()
            if not found:
                print("Aucun servo. Verifie alim, cable et cavalier.")
                return 1
            for sid in sorted(found):
                volt = _scalar(c.read_register(sid, "present_voltage")) / 10.0
                temp = _scalar(c.read_register(sid, "present_temperature"))
                print(f"  ID {sid:>3}  modele {found[sid]:>5}  {volt:.1f} V  {temp} C")
            return 0

        if args.action == "set-id":
            old, new = args.old, args.new
            found = c.scan()
            if len(found) > 1:
                print(
                    "Refus : plusieurs servos sur le bus. "
                    "Branche UN SEUL servo pour changer un ID."
                )
                return 1
            if old not in found:
                print(f"Servo {old} absent du bus.")
                return 1
            c.write_register(old, "lock", 0)
            c.write_id(old, new)
            c.write_register(new, "lock", 1)
            print(f"ID {old} -> {new} OK.")
            for sid in sorted(c.scan()):
                print(f"  present : {sid}")
            return 0

        if args.action == "dump":
            for reg in Scs0009PyController.registers():
                try:
                    value = _scalar(c.read_register(args.servo_id, reg.name))
                except Exception:
                    continue
                print(f"  {reg.name:28} = {value}")
            return 0
    finally:
        c.close()
    return 0


# --------------------------------------------------------------------------- #
# F2 - assemble
# --------------------------------------------------------------------------- #
def cmd_assemble(args) -> int:
    model = _model(args)
    bus = _bus(args, model)
    try:
        found = set(bus.scan())
        expected = {j.servo_id for j in model.joints.values()}
        missing = sorted(expected - found)
        if missing:
            print(f"IDs manquants : {missing}. Verifie le montage/alim.")
            return 1
        print(f"Servos detectes : {sorted(found)}")

        print("Positions AVANT :")
        for name in model.calibration_order:
            j = model.joint(name)
            print(f"  ID {j.servo_id} ({name}) : {bus.read_position(j.servo_id)} ticks")

        print("\nDeplacement vers la pose de montage :")
        for name in model.calibration_order:
            j = model.joint(name)
            bus.set_torque_limit_pct(j.servo_id, model.safety.default_torque_pct)
            bus.set_torque_enable(j.servo_id, True)
            bus.set_goal_speed(j.servo_id, model.safety.move_speed)
            bus.write_goal(j.servo_id, j.assembly_position)
            hint = (
                "palonnier vers le haut (extension complete / point mort)"
                if j.reference.startswith("dead_center")
                else "doigt dans une position neutre, non bloquee"
            )
            print(f"  ID {j.servo_id} ({name}) -> {j.assembly_position} ticks : {hint}")

        # attendre que les servos atteignent (ou non) la consigne
        elapsed = 0.0
        reached = {}
        while elapsed < 3.0:
            reached = {
                j.servo_id: bus.read_position(j.servo_id) for j in model.joints.values()
            }
            if all(
                abs(reached[j.servo_id] - j.assembly_position) <= 2
                for j in model.joints.values()
            ):
                break
            if not bus.simulated:
                time.sleep(0.1)
            elapsed += 0.1

        print("\nPositions APRES :")
        for name in model.calibration_order:
            j = model.joint(name)
            pos = reached.get(j.servo_id, bus.read_position(j.servo_id))
            delta = pos - j.assembly_position
            flag = "OK" if abs(delta) <= 2 else f"ECART {delta:+d} ticks (bloque ?)"
            print(f"  ID {j.servo_id} ({name}) : {pos} ticks  [{flag}]")

        if not _confirm(
            "Emboite les palonniers dans cette pose, puis Entree.", args.yes
        ):
            print("Abandon.")
            return 1

        if args.release:
            for j in model.joints.values():
                bus.set_torque_enable(j.servo_id, False)
            print("Couple coupe.")
        else:
            print("Couple maintenu (les palonniers restent en pose). Ctrl-C pour liberer.")
            while True:
                time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nArret, couple coupe.")
    except Exception as exc:
        print(f"\nBUS/MATERIEL error: {exc}")
    finally:
        for j in model.joints.values():
            try:
                bus.set_torque_enable(j.servo_id, False)
            except Exception:
                pass
        bus.close()
    return 0


# --------------------------------------------------------------------------- #
# F3/F4 - calibrate
# --------------------------------------------------------------------------- #
def _print_hand(hand) -> None:
    print(f"\nMain {hand.hand_serial} ({hand.model_version}) :")
    for name, c in hand.joints.items():
        print(
            f"  {name:16} {c.status:9} mount={c.mount_ticks:4} ref={c.reference_ticks:4} "
            f"stops=[{c.stop_low_ticks},{c.stop_high_ticks}] "
            f"course={c.measured_travel_deg:5.1f} deg (nom {c.nominal_travel_deg:.0f}) "
            f"rep={c.repeatability_ticks}"
        )
        if c.cause:
            print(f"      -> {c.cause}")


def _run_calibration(
    args, model, bus, serial, mount: bool = False, logs_dir=None
) -> "object":
    if not _confirm(
        "La main doit etre LIBRE (rien entre les doigts). Continuer ?", args.yes
    ):
        raise CalibrationAbort("annule par l'utilisateur")

    def progress(name, servo_id, index, total):
        print(f"\n[{index}/{total}] calibration de {name} (ID {servo_id}) ...")

    def on_reset(label, positions):
        detail = "  ".join(f"{name}={ticks}" for name, ticks in positions.items())
        print(f"  mise a 0 ({label}) : {detail}")

    def mount_confirm():
        print(
            "\nServos a 0 deg. Monte les palonniers pour une main ETENDUE "
            "(palonniers vers le haut), puis valide."
        )
        if not args.yes:
            try:
                input("Appuie sur Entree pour lancer la calibration... ")
            except EOFError:
                pass

    run_dir = logs_dir or (Path(args.logs_dir) if args.logs_dir else DEFAULT_LOGS_DIR)
    return calibrate_hand(
        bus,
        model,
        hand_serial=serial,
        logs_dir=run_dir,
        verify=args.verify,
        step_by_step=not args.batch,
        progress=progress,
        on_reset=on_reset,
        mount_confirm=mount_confirm if mount else None,
        trace=print,
    )


def _next_calibration_path(calib_dir, serial: str, tag: str | None = None) -> Path:
    """N'ecrase jamais une calibration existante : incremente le suffixe."""
    d = Path(calib_dir)
    d.mkdir(parents=True, exist_ok=True)
    if tag:
        return d / f"{serial}_{tag}.json"
    base = d / f"{serial}.json"
    if not base.exists():
        return base
    n = 2
    while True:
        candidate = d / f"{serial}_{n}.json"
        if not candidate.exists():
            return candidate
        n += 1


def cmd_calibrate(args) -> int:
    model = _model(args)
    serial = args.serial or DEFAULT_SERIAL
    bus = _bus(args, model)
    run_dir = _new_run_dir("calibration", serial, args.logs_dir)
    try:
        hand = _run_calibration(
            args, model, bus, serial, mount=True, logs_dir=run_dir
        )
        _print_hand(hand)
        if hand.warnings:
            print(
                "\nATTENTION (a verifier) : "
                + ", ".join(hand.warnings)
                + " -> butee douteuse (voir raison ci-dessus)."
            )

        if args.repeat and args.repeat > 1:
            print(f"\nRepetabilite (--repeat {args.repeat}) :")
            for _ in range(args.repeat - 1):
                again = _run_calibration(args, model, bus, serial, logs_dir=run_dir)
                worst = 0
                for name, c in hand.joints.items():
                    d = abs(c.reference_ticks - again.joints[name].reference_ticks)
                    worst = max(worst, d)
                print(f"  ecart max de reference = {worst} ticks (seuil 2)")

        out = _next_calibration_path(
            args.calib_dir or paths.calibration_dir(serial), serial, args.tag
        )
        out.write_text(json.dumps(hand.to_dict(), indent=2), encoding="utf-8")
        print(f"\nCalibration ecrite : {out}")
        print("(les calibrations precedentes sont conservees)")
        print(f"Journal de balayage : {run_dir / 'sweep.csv'}")
        return 0 if hand.valid else 2
    except CalibrationAbort as exc:
        print(f"\nARRET : {exc}")
        return 1
    except KeyboardInterrupt:
        print("\nCtrl-C : coupe du couple.")
        return 130
    except Exception as exc:
        print(f"\nERREUR bus/materiel : {exc}")
        print("Verifie l'alim 6 V et le cable USB, puis relance.")
        return 1
    finally:
        try:
            for j in model.joints.values():
                bus.set_torque_enable(j.servo_id, False)
        except Exception:
            pass
        bus.close()


# --------------------------------------------------------------------------- #
# F7 - collect-collisions
# --------------------------------------------------------------------------- #
def cmd_collect(args) -> int:
    model = _model(args)
    bus = _bus(args, model)
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
    else:
        out = _new_run_dir("collect", args.serial, args.logs_dir) / "poses.csv"
    try:
        for j in model.joints.values():
            bus.set_torque_enable(j.servo_id, False)
        print("Couple coupe. Place la main pres d'une collision, puis Entree.")
        print("Etiquettes : contact | limite | libre. 'q' pour quitter.")
        with out.open("a", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            if fh.tell() == 0:
                writer.writerow(["joints_rad", "label", "serial"])
            while True:
                try:
                    line = input("Entree pour logger (ou etiquette, ou q) > ").strip()
                except EOFError:
                    break
                if line.lower() == "q":
                    break
                label = line or "limite"
                pos = []
                for j in model.joints.values():
                    ticks = bus.read_position(j.servo_id)
                    pos.append(round(units.ticks_to_rad(ticks), 6))
                writer.writerow([json.dumps(pos), label, args.serial])
                fh.flush()
                print(f"  logged ({label}) : {pos}")
        print(f"Journal : {out}")
        return 0
    finally:
        bus.close()


# --------------------------------------------------------------------------- #
# Studio / demo
# --------------------------------------------------------------------------- #
def _resolve_calibration(args) -> Path | None:
    if getattr(args, "calibration", None):
        return Path(args.calibration)
    if getattr(args, "calib_dir", None):
        return paths.latest_in_dir(args.calib_dir)
    serial = getattr(args, "serial", None) or DEFAULT_SERIAL
    return paths.latest_calibration(serial)


def cmd_studio(args) -> int:
    model = _model(args)
    calib = _resolve_calibration(args)
    if calib is None:
        print("No calibration found. Run `lamain calibrate` first.")
        return 1
    bus = _bus(args, model)
    keys = KeyReader()
    studio = Studio(
        model=model,
        bus=bus,
        calibration_path=calib,
        gestures=GestureStore(args.gesture_dir or DEFAULT_GESTURE_DIR),
        episodes=EpisodeStore(args.episode_dir or DEFAULT_EPISODE_DIR),
        keys=keys,
        step_deg=args.step,
    )
    try:
        studio.run()
        return 0
    except KeyboardInterrupt:
        print("\nInterrupted.")
        return 130
    except Exception as exc:
        print(f"\nBUS/MATERIEL error: {exc}")
        print("Check the 6 V power and the USB cable, then retry.")
        return 1
    finally:
        keys.close()
        bus.close()


def cmd_demo_play(args) -> int:
    model = _model(args)
    calib = _resolve_calibration(args)
    if calib is None:
        print("No calibration found. Run `lamain calibrate` first.")
        return 1
    store = EpisodeStore(args.episode_dir or DEFAULT_EPISODE_DIR)
    gestures = GestureStore(args.gesture_dir or DEFAULT_GESTURE_DIR)
    if args.name in store.list():
        steps = store.load(args.name).steps
        loops = args.loops
    else:
        if not gestures.exists(args.name):
            print(f"Not found (episode or gesture): {args.name}")
            return 1
        steps = [Step("gesture", None, name=args.name)]
        loops = args.loops or 1
    bus = _bus(args, model)
    controller = HandController(bus, model, load_calibration(calib))
    controller.enable_torque(args.torque)
    player = Player(
        controller,
        PlayOptions(loops=loops, speed=args.speed, max_step_deg=90.0),
    )
    print(f"Playing '{args.name}' from zero (Ctrl-C to stop)...")
    try:
        player.play(steps, gestures=gestures)
        return 0
    except PlayerStopped as exc:
        print(f"Stopped: {exc}")
        return 1
    except KeyboardInterrupt:
        print("\nInterrupted.")
        return 130
    except Exception as exc:
        print(f"\nBUS/MATERIEL error: {exc}")
        return 1
    finally:
        controller.disable_torque()
        bus.close()


def cmd_gesture_list(args) -> int:
    store = GestureStore(args.gesture_dir or DEFAULT_GESTURE_DIR)
    names = store.list()
    print("\n".join(names) if names else "(no gestures)")
    return 0


def cmd_episode_list(args) -> int:
    store = EpisodeStore(args.episode_dir or DEFAULT_EPISODE_DIR)
    names = store.list()
    print("\n".join(names) if names else "(no episodes)")
    return 0


def cmd_gesture_delete(args) -> int:
    store = GestureStore(args.gesture_dir or DEFAULT_GESTURE_DIR)
    existed = store.exists(args.name)
    store.delete(args.name)
    print("Deleted." if existed else "Not found.")
    return 0


def cmd_gesture_rename(args) -> int:
    store = GestureStore(args.gesture_dir or DEFAULT_GESTURE_DIR)
    print("Renamed." if store.rename(args.old, args.new) else "Failed.")
    return 0


def cmd_gesture_show(args) -> int:
    store = GestureStore(args.gesture_dir or DEFAULT_GESTURE_DIR)
    if not store.exists(args.name):
        print("Not found.")
        return 1
    print(json.dumps(store.load(args.name).to_dict(), indent=2))
    return 0


def cmd_episode_delete(args) -> int:
    store = EpisodeStore(args.episode_dir or DEFAULT_EPISODE_DIR)
    print("Deleted." if store.delete(args.name) else "Not found.")
    return 0


def cmd_episode_rename(args) -> int:
    store = EpisodeStore(args.episode_dir or DEFAULT_EPISODE_DIR)
    print("Renamed." if store.rename(args.old, args.new) else "Failed.")
    return 0


def cmd_episode_show(args) -> int:
    store = EpisodeStore(args.episode_dir or DEFAULT_EPISODE_DIR)
    try:
        episode = store.load(args.name)
    except FileNotFoundError:
        print("Not found.")
        return 1
    for i, step in enumerate(episode.steps, 1):
        label = f"gesture:{step.name}" if step.type == "gesture" else "keypoint"
        print(f"  {i}) {label}")
    return 0


# --------------------------------------------------------------------------- #
# Diagnostic
# --------------------------------------------------------------------------- #
def _print_diag(diag, serial: str) -> None:
    lo, hi = diag.stop_low, diag.stop_high
    print(
        f"  mount={diag.mount_ticks}  stop_low={lo}  stop_high={hi}  "
        f"travel={diag.travel_deg:.1f} deg"
    )
    print(
        f"    low : {'SERVO END' if diag.low_is_servo_end else 'inside'}"
        f"  eeprom_min={diag.servo_min_limit}"
    )
    print(
        f"    high: {'SERVO END' if diag.high_is_servo_end else 'inside'}"
        f"  eeprom_max={diag.servo_max_limit}"
    )
    print(
        f"    load {diag.load_min}..{diag.load_max}  temp_max {diag.temp_max} C  "
        f"Vmin {diag.voltage_min:.1f}"
    )
    print(f"    verdict: {diag.verdict}")


def _write_inspect_summary(run_dir, diags, serial: str) -> None:
    (run_dir / "summary.json").write_text(
        json.dumps([d.to_dict() for d in diags], indent=2), encoding="utf-8"
    )
    lines = [f"Inspection {serial}", ""]
    for d in diags:
        lines.append(
            f"{d.name:16} servo {d.servo_id}: stops=[{d.stop_low},{d.stop_high}] "
            f"travel={d.travel_deg:.1f} deg  load {d.load_min}..{d.load_max}  "
            f"temp {d.temp_max} C  V {d.voltage_min:.1f}"
        )
        lines.append(
            f"    low={'SERVO END' if d.low_is_servo_end else 'inside'}  "
            f"high={'SERVO END' if d.high_is_servo_end else 'inside'}  {d.verdict}"
        )
    (run_dir / "summary.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def cmd_inspect(args) -> int:
    model = _model(args)
    bus = _bus(args, model)
    names = [args.joint] if args.joint else list(model.joints)
    serial = args.serial or DEFAULT_SERIAL
    run_dir = _new_run_dir("inspect", serial, args.logs_dir)
    try:
        # park every joint at its mount zero first (keeps the others out of the way)
        for j in model.joints.values():
            bus.set_torque_limit_pct(j.servo_id, model.calibration.torque_pct)
            bus.set_torque_enable(j.servo_id, True)
            bus.write_goal(j.servo_id, j.assembly_position)
        for _ in range(50):
            bus.step()

        diags = []
        for name in names:
            joint = model.joint(name)
            print(f"\n=== inspect {name} (servo {joint.servo_id}) === (Ctrl-C to stop)")
            diag = sweep_joint(
                bus,
                model,
                joint,
                step_ticks=args.step,
                torque_pct=args.torque,
                settle_s=args.settle,
                endpoint_margin=args.end_margin,
            )
            _print_diag(diag, serial)
            diag_write_csv(diag, run_dir / f"{name}.csv")
            if args.plot:
                diag_plot(diag, run_dir / f"{name}.png")
            diags.append(diag)

        _write_inspect_summary(run_dir, diags, serial)
        print(f"\nSorties -> {run_dir}/  (csv, plot, summary.txt, summary.json)")
        return 0
    except KeyboardInterrupt:
        print("\nInterrupted.")
        return 130
    except Exception as exc:
        print(f"\nBUS/MATERIEL error: {exc}")
        print("Check the 6 V power and the USB cable, then retry.")
        return 1
    finally:
        for j in model.joints.values():
            try:
                bus.set_torque_enable(j.servo_id, False)
            except Exception:
                pass
        bus.close()


# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="lamain", description="La Main - CLI")
    ap.add_argument("--model", default=None, help="chemin de hand_model.yaml")
    ap.add_argument("--port", default=None, help="port serie (defaut du modele)")
    ap.add_argument("--simulate", action="store_true", help="utiliser le FakeBus")
    sub = ap.add_subparsers(dest="command", required=True)

    b = sub.add_parser("bus", help="outils bus (F1)")
    b.add_argument("action", choices=["scan", "set-id", "dump"])
    b.add_argument("old", nargs="?", type=int)
    b.add_argument("new", nargs="?", type=int)
    b.add_argument("servo_id", nargs="?", type=int, default=1)
    b.set_defaults(func=cmd_bus)

    a = sub.add_parser("assemble", help="pose de montage (F2)")
    a.add_argument("--release", action="store_true")
    a.add_argument("--yes", action="store_true")
    a.set_defaults(func=cmd_assemble)

    c = sub.add_parser("calibrate", help="calibration auto (F3/F4)")
    c.add_argument("--verify", action="store_true", help="valider contre le nominal")
    c.add_argument("--repeat", type=int, default=1, help="repeter N fois (repetabilite)")
    c.add_argument(
        "--batch",
        action="store_true",
        help="calibrer d'affilee sans remettre les autres servos a zero entre chaque",
    )
    c.add_argument("--serial", default=None, help="numero de serie de la main")
    c.add_argument("--tag", default=None, help="suffixe du fichier (ex: apres_pouce)")
    c.add_argument("--calib-dir", default=None)
    c.add_argument("--logs-dir", default=None)
    c.add_argument("--yes", action="store_true", help="ne pas demander confirmation")
    c.set_defaults(func=cmd_calibrate)

    k = sub.add_parser("collect-collisions", help="recueil de poses (F7)")
    k.add_argument("--serial", default=DEFAULT_SERIAL)
    k.add_argument("--out", default=None)
    k.add_argument("--logs-dir", default=None)
    k.set_defaults(func=cmd_collect)

    s = sub.add_parser("studio", help="interactive gesture/episode studio")
    s.add_argument("--calibration", default=None,
                   help="calibration json (defaut : la plus recente)")
    s.add_argument("--calib-dir", default=None)
    s.add_argument("--gesture-dir", default=None)
    s.add_argument("--episode-dir", default=None)
    s.add_argument("--step", type=float, default=3.0, help="jog step en degres")
    s.set_defaults(func=cmd_studio)

    d = sub.add_parser("demo", help="rejouer une demo")
    dsub = d.add_subparsers(dest="demo_action", required=True)
    dp = dsub.add_parser("play", help="rejouer un episode (rapide)")
    dp.add_argument("name")
    dp.add_argument("--loops", type=int, default=0, help="0 = infini")
    dp.add_argument("--speed", type=float, default=2.0)
    dp.add_argument("--torque", default="default",
                    choices=["free", "default", "grasp"])
    dp.add_argument("--calibration", default=None)
    dp.add_argument("--calib-dir", default=None)
    dp.add_argument("--episode-dir", default=None)
    dp.add_argument("--gesture-dir", default=None)
    dp.set_defaults(func=cmd_demo_play)

    g = sub.add_parser("gesture", help="bibliotheque de gestes")
    gsub = g.add_subparsers(dest="gesture_action", required=True)
    gl = gsub.add_parser("list")
    gl.add_argument("--gesture-dir", default=None)
    gl.set_defaults(func=cmd_gesture_list)
    gs = gsub.add_parser("show")
    gs.add_argument("name")
    gs.add_argument("--gesture-dir", default=None)
    gs.set_defaults(func=cmd_gesture_show)
    gd = gsub.add_parser("delete")
    gd.add_argument("name")
    gd.add_argument("--gesture-dir", default=None)
    gd.set_defaults(func=cmd_gesture_delete)
    gr = gsub.add_parser("rename")
    gr.add_argument("old")
    gr.add_argument("new")
    gr.add_argument("--gesture-dir", default=None)
    gr.set_defaults(func=cmd_gesture_rename)

    e = sub.add_parser("episode", help="episodes")
    esub = e.add_subparsers(dest="episode_action", required=True)
    el = esub.add_parser("list")
    el.add_argument("--episode-dir", default=None)
    el.set_defaults(func=cmd_episode_list)
    es = esub.add_parser("show")
    es.add_argument("name")
    es.add_argument("--episode-dir", default=None)
    es.set_defaults(func=cmd_episode_show)
    ed = esub.add_parser("delete")
    ed.add_argument("name")
    ed.add_argument("--episode-dir", default=None)
    ed.set_defaults(func=cmd_episode_delete)
    er = esub.add_parser("rename")
    er.add_argument("old")
    er.add_argument("new")
    er.add_argument("--episode-dir", default=None)
    er.set_defaults(func=cmd_episode_rename)

    i = sub.add_parser("inspect", help="diagnostic sweep of a joint")
    i.add_argument("joint", nargs="?", default=None, help="joint name (default: all)")
    i.add_argument("--step", type=int, default=4, help="sweep step in ticks")
    i.add_argument("--torque", type=float, default=None,
                   help="torque %% (default: joint calibration torque)")
    i.add_argument("--settle", type=float, default=None)
    i.add_argument("--end-margin", type=int, default=20,
                   help="ticks from 0/1023 counted as the servo end")
    i.add_argument("--plot", action=argparse.BooleanOptionalAction, default=True,
                   help="write a PNG plot (default: on; use --no-plot to skip)")
    i.add_argument("--serial", default=None)
    i.add_argument("--logs-dir", default=None)
    i.set_defaults(func=cmd_inspect)

    return ap


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "bus" and args.action == "set-id" and (args.old is None or args.new is None):
        print("usage : lamain bus set-id ANCIEN NOUVEAU")
        return 2
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
