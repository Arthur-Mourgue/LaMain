import pytest

from lamain_core.bus import FakeBus
from lamain_core.calibration import calibrate_hand
from lamain_core.controller import HandController
from lamain_core.demos import (
    Episode,
    EpisodeStore,
    Gesture,
    GestureStore,
    PlayOptions,
    Player,
    Pose,
    Step,
    lerp,
    smoothstep,
)
from lamain_core.model import default_model_path, load_hand_model


def _controller():
    m = load_hand_model(default_model_path())
    bus = FakeBus.standard_hand(m)
    hand = calibrate_hand(bus, m, "TEST")
    ctrl = HandController(bus, m, hand)
    ctrl.enable_torque("default")
    return m, ctrl


def _settle(ctrl, n: int = 300) -> None:
    for _ in range(n):
        ctrl.bus.step()


def _pose(ctrl, **joint_q):
    q = {name: 0.0 for name in ctrl.joint_names}
    q.update(joint_q)
    ctrl.set_normalized(q)
    _settle(ctrl)
    applied = ctrl.get_normalized()
    rad = ctrl.get_joint_positions()
    return Pose(q=applied, rad=rad)


def test_smoothstep_and_lerp():
    assert smoothstep(0.0) == 0.0
    assert smoothstep(1.0) == 1.0
    assert lerp({"a": 0.0, "b": 2.0}, {"a": 2.0, "b": 4.0}, 0.5) == {"a": 1.0, "b": 3.0}


def test_gesture_store_overwrites(tmp_path):
    store = GestureStore(tmp_path / "gestures")
    p1 = Pose(q={"index_flex": 0.1}, rad={"index_flex": 0.2})
    store.save(Gesture("grip", p1))
    p2 = Pose(q={"index_flex": 0.9}, rad={"index_flex": 1.8})
    store.save(Gesture("grip", p2))
    assert store.list() == ["grip"]
    assert store.load("grip").pose.q["index_flex"] == 0.9


def test_gesture_rename(tmp_path):
    store = GestureStore(tmp_path / "gestures")
    store.save(Gesture("old", Pose(q={"index_flex": 0.3})))
    assert store.rename("old", "new")
    assert store.list() == ["new"]
    assert not store.exists("old")


def test_episode_write_overwrites_and_rename(tmp_path):
    store = EpisodeStore(tmp_path / "episodes")
    store.write(Episode("demo", steps=[Step("keypoint", Pose({"index_flex": 0.0}))]))
    store.write(Episode("demo", steps=[Step("keypoint", Pose({"index_flex": 0.2}))]))
    assert store.list() == ["demo"]                     # no _2 suffix
    assert store.load("demo").steps[0].pose.q["index_flex"] == 0.2
    assert store.rename("demo", "demo2")
    assert store.list() == ["demo2"]


def test_episode_store_numbering(tmp_path):
    store = EpisodeStore(tmp_path / "episodes")
    ep = Episode("demo", steps=[Step("keypoint", Pose({"index_flex": 0.0}))])
    first = store.save(ep)
    ep2 = Episode("demo", steps=[Step("keypoint", Pose({"index_flex": 0.1}))])
    second = store.save(ep2)
    assert first.name != second.name
    assert second.stem == "demo_2"


def test_player_reaches_last_pose():
    m, ctrl = _controller()
    a = _pose(ctrl, index_flex=0.0)
    b = _pose(ctrl, index_flex=0.5, middle_flex=0.5)
    steps = [Step("keypoint", a, hold=0.05), Step("keypoint", b, hold=0.05)]
    player = Player(ctrl, PlayOptions(loops=1, speed=2.0, default_step_s=0.05))
    player.play(steps)
    _settle(ctrl)
    end = ctrl.get_normalized()
    assert abs(end["index_flex"] - b.q["index_flex"]) < 0.05
    assert abs(end["middle_flex"] - b.q["middle_flex"]) < 0.05


def test_play_single_gesture_starts_from_zero():
    m, ctrl = _controller()
    target = _pose(ctrl, index_flex=-0.5)
    ctrl.set_normalized({"index_flex": 0.9})   # start far from zero
    _settle(ctrl)
    player = Player(ctrl, PlayOptions(loops=1, speed=2.0, default_step_s=0.05))
    player.play([Step("gesture", target)])
    _settle(ctrl)
    end = ctrl.get_normalized()
    assert abs(end["index_flex"] - target.q["index_flex"]) < 0.05


def test_episode_gesture_reference_resolves_by_name(tmp_path):
    m, ctrl = _controller()
    store = GestureStore(tmp_path / "gestures")
    store.save(Gesture("g", _pose(ctrl, index_flex=0.2)))
    step = Step("gesture", None, name="g")          # reference only, no snapshot
    store.save(Gesture("g", _pose(ctrl, index_flex=0.7)))  # replace same name
    player = Player(
        ctrl,
        PlayOptions(loops=1, speed=2.0, start_at_zero=False, approach=True),
    )
    player.play([step], gestures=store)
    _settle(ctrl)
    assert abs(ctrl.get_normalized()["index_flex"] - store.load("g").pose.q["index_flex"]) < 0.05
    assert "q" not in step.to_dict()                # gesture step stores no pose
