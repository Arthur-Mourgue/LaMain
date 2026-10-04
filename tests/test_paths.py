import time

from lamain_core import paths


def test_latest_calibration_picks_most_recent(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "hands_dir", lambda: tmp_path / "hands")
    directory = paths.calibration_dir("LM-0001")
    directory.mkdir(parents=True)
    (directory / "a.json").write_text("{}")
    time.sleep(0.01)
    (directory / "b.json").write_text("{}")
    assert paths.latest_calibration("LM-0001").name == "b.json"


def test_latest_calibration_none_when_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "hands_dir", lambda: tmp_path / "hands")
    assert paths.latest_calibration("LM-0001") is None


def test_paths_layout(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "repo_root", lambda: tmp_path)
    assert paths.calibration_dir("LM-0001") == tmp_path / "hands" / "LM-0001" / "calibration"
    assert paths.gesture_dir() == tmp_path / "demos" / "gestures"
    assert paths.episode_dir() == tmp_path / "demos" / "episodes"
