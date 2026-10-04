import pytest

from lamain_core.bus import FakeBus
from lamain_core.calibration import calibrate_hand
from lamain_core.model import default_model_path, load_hand_model
from lamain_core.safety import SafetyError, SafetyFilter


def _fixture():
    m = load_hand_model(default_model_path())
    bus = FakeBus.standard_hand(m)
    hand = calibrate_hand(bus, m, "TEST")
    return m, hand


def test_clamp_mode_bounds_command():
    m, hand = _fixture()
    f = SafetyFilter(hand, m, mode="clamp")
    lim = f.limits["index_flex"]
    assert f.clamp_ticks("index_flex", lim.min_ticks - 500) == lim.min_ticks
    assert f.clamp_ticks("index_flex", lim.max_ticks + 500) == lim.max_ticks


def test_strict_mode_raises():
    m, hand = _fixture()
    f = SafetyFilter(hand, m, mode="strict")
    lim = f.limits["index_flex"]
    with pytest.raises(SafetyError):
        f.clamp_ticks("index_flex", lim.max_ticks + 1)


def test_step_limiting():
    m, hand = _fixture()
    f = SafetyFilter(hand, m)
    step = f.max_step_ticks("index_flex")
    assert f.limit_step("index_flex", 100000, 0) == step


def test_torque_modes():
    m, hand = _fixture()
    f = SafetyFilter(hand, m)
    assert f.torque_pct("grasp") > f.torque_pct("free")
    with pytest.raises(ValueError):
        f.torque_pct("nope")
