import numpy as np
import pytest

from ml.sequence_buffer import TelemetrySequenceBuffer


def sample(cycle: int) -> dict[str, float]:
    return {"sensor_a": float(cycle), "sensor_b": float(cycle * 10)}


def test_buffer_keeps_only_latest_window():
    buffer = TelemetrySequenceBuffer(window_size=3)

    for cycle in range(1, 6):
        buffer.append("AF-001", "ENGINE", cycle, sample(cycle))

    assert buffer.size("AF-001", "ENGINE") == 3
    assert [point.cycle for point in buffer.latest("AF-001", "ENGINE")] == [3, 4, 5]


def test_buffer_keeps_aircraft_component_histories_separate():
    buffer = TelemetrySequenceBuffer(window_size=2)
    buffer.append("AF-001", "ENGINE", 1, sample(1))
    buffer.append("AF-002", "ENGINE", 1, sample(1))
    buffer.append("AF-001", "HYDRAULIC", 1, sample(1))

    buffer.append("AF-001", "ENGINE", 2, sample(2))
    buffer.append("AF-002", "ENGINE", 2, sample(2))

    assert buffer.has_window("AF-001", "ENGINE")
    assert buffer.has_window("AF-002", "ENGINE")
    assert not buffer.has_window("AF-001", "HYDRAULIC")

    assert [p.aircraft_id for p in buffer.latest("AF-001", "ENGINE")] == [
        "AF-001",
        "AF-001",
    ]


def test_latest_array_preserves_chronological_feature_order():
    buffer = TelemetrySequenceBuffer(window_size=2)
    buffer.append("AF-001", "ENGINE", 1, sample(1))
    buffer.append("AF-001", "ENGINE", 2, sample(2))

    result = buffer.latest_array(
        "AF-001",
        "ENGINE",
        ["sensor_a", "sensor_b"],
    )

    assert result.dtype == np.float32
    assert result.shape == (2, 2)
    np.testing.assert_array_equal(
        result,
        np.array([[1.0, 10.0], [2.0, 20.0]], dtype=np.float32),
    )


def test_rejects_duplicate_or_out_of_order_cycles():
    buffer = TelemetrySequenceBuffer(window_size=3)
    buffer.append("AF-001", "ENGINE", 5, sample(5))

    with pytest.raises(ValueError, match="must increase strictly"):
        buffer.append("AF-001", "ENGINE", 5, sample(5))

    with pytest.raises(ValueError, match="must increase strictly"):
        buffer.append("AF-001", "ENGINE", 4, sample(4))


def test_rejects_invalid_values_and_incomplete_full_window():
    buffer = TelemetrySequenceBuffer(window_size=2)

    with pytest.raises(ValueError, match="must be finite"):
        buffer.append("AF-001", "ENGINE", 1, {"sensor_a": float("nan")})

    buffer.append("AF-001", "ENGINE", 1, sample(1))

    with pytest.raises(ValueError, match="only 1 are available"):
        buffer.latest("AF-001", "ENGINE")

    assert buffer.latest(
        "AF-001",
        "ENGINE",
        require_full=False,
    )[0].cycle == 1
