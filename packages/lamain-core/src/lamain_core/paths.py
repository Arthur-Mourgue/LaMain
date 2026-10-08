# SPDX-License-Identifier: Apache-2.0
"""Single place that resolves every on-disk path used by the project.

The hand model ships inside this package (loaded with `importlib.resources`).
The rest is per-repository data:

    <repo>/hands/<serial>/calibration/*.json
    <repo>/demos/gestures/*.json
    <repo>/demos/episodes/*.json
    <repo>/logs/<kind>/<timestamp>_<label>/
"""
from __future__ import annotations

import os
from importlib.resources import files
from pathlib import Path

DEFAULT_SERIAL = "LM-0001"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def hand_model_path() -> Path:
    env = os.environ.get("LAMAIN_MODEL")
    if env:
        return Path(env)
    return Path(str(files("lamain_core").joinpath("hand_model.yaml")))


def hands_dir() -> Path:
    return repo_root() / "hands"


def hand_dir(serial: str) -> Path:
    return hands_dir() / serial


def calibration_dir(serial: str) -> Path:
    return hand_dir(serial) / "calibration"


def latest_calibration(serial: str) -> Path | None:
    """Most recently modified calibration JSON for this hand, or None."""
    return latest_in_dir(calibration_dir(serial))


def latest_in_dir(directory: str | Path) -> Path | None:
    directory = Path(directory)
    files = sorted(
        directory.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True
    )
    return files[0] if files else None


def demos_dir() -> Path:
    return repo_root() / "demos"


def gesture_dir() -> Path:
    return demos_dir() / "gestures"


def episode_dir() -> Path:
    return demos_dir() / "episodes"


def logs_dir() -> Path:
    return repo_root() / "logs"
