from lamain_core import units


def test_roundtrip_ticks_deg():
    assert abs(units.ticks_to_deg(units.deg_to_ticks(90.0)) - 90.0) < 0.5


def test_deg_per_tick_matches_spec():
    # 300 deg / 1024 steps = 0.293 deg
    assert abs(units.DEG_PER_TICK - 0.29296875) < 1e-9


def test_rad_matches_ticks():
    rad = units.ticks_to_rad(units.rad_to_ticks(0.5))
    assert abs(rad - 0.5) < 0.01
