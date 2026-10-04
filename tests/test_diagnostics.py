from lamain_core.bus import FakeBus
from lamain_core.diagnostics import plot, sweep_joint, write_csv
from lamain_core.model import default_model_path, load_hand_model


def _model_bus():
    m = load_hand_model(default_model_path())
    return m, FakeBus.standard_hand(m)


def test_sweep_reports_full_travel():
    m, bus = _model_bus()
    d = sweep_joint(bus, m, m.joint("index_flex"), step_ticks=8)
    assert d.stop_low <= 25
    assert d.stop_high >= 995
    assert d.travel_deg > 250
    assert d.temp_max >= 0
    assert d.voltage_min > 0


def test_thumb_rot_flags_a_servo_end():
    m, bus = _model_bus()
    d = sweep_joint(bus, m, m.joint("thumb_rot"), step_ticks=8)
    # fake thumb_rot stops are 682..1006: low inside, high at the servo end
    assert d.low_is_servo_end is False
    assert d.high_is_servo_end is True
    assert "internal end" in d.verdict


def test_outputs(tmp_path):
    m, bus = _model_bus()
    d = sweep_joint(bus, m, m.joint("index_flex"), step_ticks=8)
    csv_path = tmp_path / "d.csv"
    write_csv(d, csv_path)
    assert csv_path.exists()
    png_path = tmp_path / "d.png"
    plot(d, png_path)
    assert png_path.exists()
