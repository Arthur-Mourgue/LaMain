from lamain_core.bus import FakeBus, FakeServo


def test_servo_moves_and_clamps_at_stop():
    s = FakeServo(1, stop_min=100, stop_max=500, position=300, goal=300, speed_ticks=50)
    bus = FakeBus([s])
    bus.write_goal(1, 1000)  # au-dela de la butee haute
    for _ in range(20):
        bus.step()
    assert bus.read_position(1) == 500
    assert bus.read_load(1) > 0


def test_load_is_low_when_free():
    s = FakeServo(1, stop_min=0, stop_max=1023, position=511, goal=511, speed_ticks=300)
    bus = FakeBus([s])
    bus.write_goal(1, 700)
    bus.step()
    assert bus.read_position(1) == 700
    assert bus.read_load(1) < 150


def test_absent_servo_raises():
    bus = FakeBus([FakeServo(1, 0, 1023, fault="absent")])
    assert bus.scan() == {}
    try:
        bus.read_position(1)
    except Exception as exc:
        assert "absent" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("attendu une erreur")
