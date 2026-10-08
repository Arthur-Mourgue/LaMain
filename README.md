# LaMain

The smallest three-finger end-effector with tactile feedback that replaces the SO-101 gripper, and succeeds at a task the gripper fails, with the dataset and policy to prove it.

<p align="center">
  <img src="docs/lamainv0.gif" alt="LaMain prototype" width="400">
</p>

## Status

Early prototype. The long-term goal is a low-cost, low-weight hand for the
SO-101 arm, integrable with LeRobot.

What already works today (from the code):

- **Joints** (five Feetech SCS0009 servos, from the `hand_model.yaml` bundled in
  `lamain-core`):
  `index_flex`, `middle_flex`, `index_middle_abd` (index + middle abduction),
  `thumb_rot`, `thumb_flex`.
- **Automatic calibration** of every joint at reduced torque, with a stop
  confirmation push and repeatability reporting.
- **Safety filter**: joint-range clamping, per-cycle step limit, per-mode torque.
- **Controller** (`HandController`): radians and normalized `[-1, 1]` commands,
  never raw servo IDs.
- **Studio**: keyboard jog, gestures, episodes, fast playback.
- **Diagnostics**: per-joint sweep with position/load plots.
- **Tests** on a simulated bus (FakeBus), no hardware required.

## Quickstart

```bash
uv sync                 # install the workspace and dependencies
uv run lamain --help    # CLI overview
uv run pytest           # tests on FakeBus, no hardware
```

## Repository layout

```
lamain/
├── packages/lamain-core/   # reusable library (bus, calibration, safety, controller, demos)
├── packages/lamain-cli/    # the `lamain` CLI (bus, assemble, calibrate, studio, inspect)
├── hands/LM-0001/          # per-hand data: build manifest + calibration files
├── demos/                  # gestures and episodes
├── docs/                   # roadmap and decision records
└── tests/                  # FakeBus tests, run in CI
```

## Roadmap

Next milestones and the planned benchmark are in [docs/ROADMAP.md](docs/ROADMAP.md).

## Hardware

Bill of materials:
[LaMain BOM](https://docs.google.com/spreadsheets/d/1QRkrFNEr4OLIYoRjOxhvR7IqRy3qPOLTq45OjTfyoFY/edit?usp=sharing).
CAD rev A not published yet.

## Design principle

Standardize what the sensor sees; diversify everything else.

## License

- Software: Apache-2.0 (see [LICENSE](LICENSE)).
- Hardware: license pending (see [D-003](docs/decisions/D-003-licences.md)).
- Datasets: CC-BY-4.0, hosted on the Hugging Face Hub, not in git.

## Credits

- Arthur Mourgue
- Julien Navet (CAD)

Inspired by Pollen Robotics' AmazingHand (reference kept in `vendor/`).
