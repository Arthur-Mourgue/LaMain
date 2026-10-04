# Calibration - custom hand, 5 servos

Reference doc: read before any work on the servos. Summarizes what to keep from
the AmazingHand and what changes for our hand.
The **operational step-by-step** is in [GUIDE.md](GUIDE.md).

## 1. Our hand

Custom hand with **5 servos** (the original AmazingHand has 8: 2 per finger, in
parallel).

| ID | Role |
|----|------|
| 1 | **index** flexion |
| 2 | **middle** flexion |
| 3 | index + middle **abduction** |
| 4 | **thumb base** |
| 5 | **thumb flexion** |

Unlike the AmazingHand, there is **no facing pair of horns** per finger. The two
thumb servos are stacked but drive two distinct motions (base + flexion), so
they are calibrated separately.

## 2. What calibration is for

An SCS0009 measures the angle of **its** shaft, but its zero is **arbitrary**
relative to the mechanism: the horn can fit any spline orientation, and every
servo differs slightly.

Calibration finds, for **each servo**, the raw angle that corresponds to a
**reference pose** of the finger. That value is `MiddlePos` (or `offset`).
Every command is then written as `MiddlePos + angle` - otherwise each finger
would react differently and no pose (fist, pinch...) would be reproducible.

AmazingHand source: `PythonExample/AmazingHand_Demo.py:241-244`
(`np.deg2rad(MiddlePos[0]+Angle_1)`).

## 3. Reference convention (the AmazingHand one)

From `docs/AmazingHand_Assembly.pdf` p. 22-23:

- We **freeze the servo at `MiddlePos` (0 deg by default)** and it is **at that
  moment** that we fit/screw the horn. The assembly creates the reference.
- `AmazingHand_FingerTest.py` sweeps: **closed = `MiddlePos +90`**,
  **open = `MiddlePos -30`** (opposite signs between the 2 servos of a finger).
- Tuning criterion: at closure the mechanism must be clean and the servo
  **must never force against a stop**. Otherwise correct `MiddlePos` by a few
  degrees and repeat.

PDF example: *"right servo horn (ID1) is a bit not far enough
=> New Middle pos should be increased of +3 deg"*.

For us, the "horns aligned to the median plane" criterion becomes:
- the reference pose is **reproduced identically** at every test;
- both stops (open / closed) stay **within the servo's safe range**.

## 4. Procedure (summary)

Tooling: `calib.py` - replaces the two AmazingHand scripts, handles 1 or 2
servos, configurable port/offsets/signs. Modes: `--hold`, `--cycle`,
`--goto DELTA`, `--interactive` (angles on the fly), `--read`. Details in
[GUIDE.md](GUIDE.md).

For each joint, horns **not screwed yet** at the start:

1. `--hold`: set the servo(s) to `--middle 0`.
2. Fit the horn(s) in the reference pose, screw M2x4.
3. `--cycle`: if the finger does not close or hits a stop, adjust `--middle` in
   3 deg steps and retry.
4. Note `middle_pos`.

Recommended order:
1. **index** flexion (ID 1)
2. **middle** flexion (ID 2)
3. index+middle **abduction** (ID 3, reference = fingers together/aligned)
4. **thumb base** (ID 4) then **thumb flexion** (ID 5)

Safety: reduced speed at first, `Ctrl-C` as soon as a servo forces or heats up.
The SCS0009 handles up to 6 V; a lower voltage is gentler.

## 5. Result to record

`calibration.json`: one `middle_pos` per servo.

## 6. File state

- `legacy/scs_id_tool.py`: scan + ID change.
- `legacy/calib.py`: calibration tool (`--hold` / `--cycle` / `--goto` / `--interactive` / `--read`).
- `legacy/calibration.json`: results (to fill).
- `legacy/GUIDE.md`: operational step-by-step.
- Original scripts: `vendor/AmazingHand/PythonExample/AmazingHand_Hand_FingerMiddlePos.py`
  and `AmazingHand_FingerTest.py`.
- Hardware guide: `vendor/AmazingHand/docs/AmazingHand_Assembly.pdf`, p. 22-24.

### `calibration.json` format

```json
{
  "hand": "custom-5dof",
  "notes": "1 index flex; 2 middle flex; 3 index+middle abduction; 4 thumb base; 5 thumb flex",
  "reference": "servo frozen at middle_pos, horn fitted at that position (AmazingHand convention). Degrees.",
  "servos": {
    "1": { "role": "index_flex", "middle_pos": 0 },
    "2": { "role": "middle_flex", "middle_pos": 0 },
    "3": { "role": "index_middle_abd", "middle_pos": 0 },
    "4": { "role": "thumb_rot", "middle_pos": 0 },
    "5": { "role": "thumb_flex", "middle_pos": 0 }
  }
}
```

## 7. To do / unknowns

- [x] Fill in the **ID <-> role** mapping.
- [x] Create `calib.py`.
- [ ] Run the calibration and fill `calibration.json`.
