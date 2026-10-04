import json

from lamain_cli.keys import ScriptedKeySource
from lamain_cli.studio import Studio
from lamain_core.bus import FakeBus
from lamain_core.calibration import calibrate_hand
from lamain_core.demos import EpisodeStore, Gesture, GestureStore
from lamain_core.model import default_model_path, load_hand_model


def _setup(tmp_path):
    m = load_hand_model(default_model_path())
    bus = FakeBus.standard_hand(m)
    hand = calibrate_hand(bus, m, "TEST")
    calib = tmp_path / "cal.json"
    calib.write_text(json.dumps(hand.to_dict()), encoding="utf-8")
    return m, bus, calib


def _studio(tmp_path, m, bus, calib, keys, lines):
    return Studio(
        model=m,
        bus=bus,
        calibration_path=calib,
        gestures=GestureStore(tmp_path / "gestures"),
        episodes=EpisodeStore(tmp_path / "episodes"),
        keys=ScriptedKeySource(keys=keys, lines=lines),
        out=lambda *a: None,
    )


def test_create_gesture(tmp_path):
    m, bus, calib = _setup(tmp_path)
    st = _studio(tmp_path, m, bus, calib, keys=["1", "1", "s"], lines=["grip"])
    st._create_gesture()
    assert st.gestures.exists("grip")
    loaded = st.gestures.load("grip")
    assert set(loaded.pose.q) == set(m.joints)


def test_create_episode_with_gesture_moves_hand(tmp_path):
    m, bus, calib = _setup(tmp_path)
    st = _studio(tmp_path, m, bus, calib, keys=["2", "g", " ", "s"], lines=["1", "ep"])
    # pre-create one gesture
    st.jog.handle_key("1")
    st.gestures.save(Gesture("grip", st.jog.capture()))
    st._create_episode()
    names = st.episodes.list()
    assert names
    episode = st.episodes.load(names[0])
    kinds = [s.type for s in episode.steps]
    assert "gesture" in kinds
    gesture_step = next(s for s in episode.steps if s.type == "gesture")
    assert gesture_step.name == "grip"
