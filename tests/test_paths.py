import os

from lamain_core import paths


def test_latest_calibration_picks_most_recent(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "hands_dir", lambda: tmp_path / "hands")
    directory = paths.calibration_dir("LM-0001")
    directory.mkdir(parents=True)
    files = {}
    for name in ("a.json", "b.json", "c.json"):
        (directory / name).write_text("{}")
        files[name] = directory / name
    # mtime order deliberately differs from name order: it must be mtime that wins
    os.utime(files["c.json"], (1, 1))
    os.utime(files["b.json"], (2, 2))
    os.utime(files["a.json"], (3, 3))
    assert paths.latest_calibration("LM-0001").name == "a.json"


def test_latest_calibration_none_when_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "hands_dir", lambda: tmp_path / "hands")
    assert paths.latest_calibration("LM-0001") is None


def test_paths_layout(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "repo_root", lambda: tmp_path)
    assert paths.calibration_dir("LM-0001") == tmp_path / "hands" / "LM-0001" / "calibration"
    assert paths.gesture_dir() == tmp_path / "demos" / "gestures"
    assert paths.episode_dir() == tmp_path / "demos" / "episodes"
