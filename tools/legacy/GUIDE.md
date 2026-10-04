# Calibration guide - step by step

> **Note**: legacy procedure (`calib.py`, manual tuning of one servo).
> The official V1 procedure is `lamain assemble` then `lamain calibrate`
> (see the `README.md` at the repo root). Power supply: **6 V**.

Custom 5 dof hand. Servos: `1` index flex, `2` middle flex,
`3` index+middle abduction, `4` thumb base, `5` thumb flex.

## Prerequisites

- Power on, servos daisy-chained on the Feetech bus.
- USB cable on `/dev/ttyACM0`, your user in the `dialout` group (`groups`).
- Servo horns **not screwed yet**.

## Step 1 - Check the bus

```bash
uv sync
uv run python tools/legacy/scs_id_tool.py --port /dev/ttyACM0 --scan
```

Expected: IDs `1 2 3 4 5`. Otherwise -> power, A/B jumper, cable, permissions.

## Step 2 - Test the calibration script

```bash
uv run python tools/legacy/calib.py --help
uv run python tools/legacy/calib.py --ids 1,2,3,4,5 --read
```

`--read` prints the current angles (in degrees). Note them: that is your
starting point.

## Step 2bis - Explore angles on the fly

To test a specific angle (e.g. 180 deg) without restarting:

```bash
# Go to MiddlePos+180 then quit
uv run python tools/legacy/calib.py --ids 2 --middle 30 --goto 180

# Wide sweep (open -60, closed +180)
uv run python tools/legacy/calib.py --ids 2 --middle 30 --open -60 --close 180 --cycle
```

To drive live (type the angle):

```bash
uv run python tools/legacy/calib.py --ids 2 --middle 30 --interactive
# angle> 180        -> go to MiddlePos+180
# angle> f / o      -> close / open
# angle> r          -> return to MiddlePos
# angle> s 5        -> speed 5
# angle> l          -> re-read position / load / temperature
# angle> q          -> quit
```

The load readout (`l`) rises when the servo pushes: useful to spot a stop
without waiting for it to heat up.

## Step 3 - Set one servo's reference (e.g. index, ID 1)

1. **Freeze the servo at 0 deg**:

   ```bash
   uv run python tools/legacy/calib.py --ids 1 --middle 0 --hold
   ```

2. While it holds, **fit the horn** in the reference pose, then
   **screw M2x4**. Stop with `Ctrl-C`.

3. **Open/close sweep**:

   ```bash
   uv run python tools/legacy/calib.py --ids 1 --middle 0 --cycle
   ```

   The script alternates closed (`middle + 90`) and open (`middle - 30`).
   Watch the finger, then `Ctrl-C`.

4. **Correct**: if the finger does not close fully or hits a stop, change the
   reference by a few degrees and retry:

   ```bash
   uv run python tools/legacy/calib.py --ids 1 --middle 3 --cycle
   ```

   Repeat in **3 deg** steps until the closure is clean, without the servo
   forcing. When in doubt, redo `--hold` with the new value, stop, and review
   the horn assembly.

5. **Note** the final `middle` value for ID 1.

## Step 4 - Repeat for the other servos

Same commands, replacing the ID and, if needed, the signs:

```bash
uv run python tools/legacy/calib.py --ids 2 --middle 0 --hold     # middle flex
uv run python tools/legacy/calib.py --ids 2 --middle 0 --cycle

uv run python tools/legacy/calib.py --ids 3 --middle 0 --hold     # abduction
uv run python tools/legacy/calib.py --ids 3 --middle 0 --cycle
```

For **abduction** (ID 3), the reference pose = fingers together/aligned.
Check that the maximum spread stays in the safe range.

## Step 5 - Thumb (ID 4 base, ID 5 flex)

The two servos are stacked. Calibrate them **base then flex**, or both together:

```bash
uv run python tools/legacy/calib.py --ids 4,5 --middle 0,0 --hold
uv run python tools/legacy/calib.py --ids 4,5 --middle 0,0 --cycle
```

If their mechanics are symmetric, use opposite signs:

```bash
uv run python tools/legacy/calib.py --ids 4,5 --middle 0,0 --signs 1,-1 --cycle
```

Adjust both `middle` values until both thumb stops are reached without blocking.

## Step 6 - Record and save

1. Write the `middle_pos` values you found into `calibration.json`.
2. Check the JSON:

   ```bash
   uv run python -c "import json; print(json.load(open('calibration.json')))"
   ```

3. Commit:

   ```bash
   git add tools/legacy/
   git commit -m "Setup servo: IDs + tooling and calibration guide"
   ```

## Troubleshooting

- **Servo forcing / heating**: `Ctrl-C` immediately, reduce `--close`/`--open`
  or fix `--middle`.
- **Permission denied**: reconnect your session (group `dialout`).
- **No servo**: power, A/B jumper, cable, connector orientation.
- **Reversed direction**: add a negative sign for that servo (`--signs -1`).
