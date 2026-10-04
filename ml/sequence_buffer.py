"""Bounded telemetry history for real-time temporal inference.

The buffer stores telemetry independently for each aircraft/component pair.
It does not perform model inference or feature scaling; callers should apply
the same preprocessing used by the selected model before converting a window
to a model input array.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from math import isfinite
from typing import Iterable, Mapping

import numpy as np


@dataclass(frozen=True)
class TelemetryPoint:
    aircraft_id: str
    component: str
    cycle: int
    values: dict[str, float]


class TelemetrySequenceBuffer:
    """Keep the latest fixed-size telemetry window per aircraft/component."""

    def __init__(self, window_size: int = 30) -> None:
        if not isinstance(window_size, int) or isinstance(window_size, bool):
            raise TypeError("window_size must be an integer")
        if window_size <= 0:
            raise ValueError("window_size must be greater than zero")

        self.window_size = window_size
        self._buffers: dict[tuple[str, str], deque[TelemetryPoint]] = {}
        self._last_cycle: dict[tuple[str, str], int] = {}

    @staticmethod
    def _entity(value: str, field_name: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field_name} must be a non-empty string")
        return value.strip()

    @staticmethod
    def _values(values: Mapping[str, float]) -> dict[str, float]:
        if not isinstance(values, Mapping) or not values:
            raise ValueError("values must be a non-empty mapping")

        normalized: dict[str, float] = {}
        for name, value in values.items():
            if not isinstance(name, str) or not name.strip():
                raise ValueError("telemetry feature names must be non-empty strings")
            try:
                numeric = float(value)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"telemetry feature {name!r} must be numeric") from exc
            if not isfinite(numeric):
                raise ValueError(f"telemetry feature {name!r} must be finite")
            normalized[name.strip()] = numeric
        return normalized

    def append(
        self,
        aircraft_id: str,
        component: str,
        cycle: int,
        values: Mapping[str, float],
    ) -> None:
        """Append one telemetry sample, enforcing per-entity cycle ordering."""
        aircraft = self._entity(aircraft_id, "aircraft_id")
        part = self._entity(component, "component")

        if not isinstance(cycle, int) or isinstance(cycle, bool):
            raise TypeError("cycle must be an integer")
        if cycle < 0:
            raise ValueError("cycle must be non-negative")

        normalized = self._values(values)
        key = (aircraft, part)

        previous = self._last_cycle.get(key)
        if previous is not None and cycle <= previous:
            raise ValueError(
                f"cycle must increase strictly for {aircraft}/{part}; "
                f"received {cycle} after {previous}"
            )

        buffer = self._buffers.setdefault(
            key,
            deque(maxlen=self.window_size),
        )
        buffer.append(
            TelemetryPoint(
                aircraft_id=aircraft,
                component=part,
                cycle=cycle,
                values=normalized,
            )
        )
        self._last_cycle[key] = cycle

    def has_window(
        self,
        aircraft_id: str,
        component: str,
    ) -> bool:
        """Return True when a complete window is available."""
        return self.size(aircraft_id, component) >= self.window_size

    def size(self, aircraft_id: str, component: str) -> int:
        """Return the number of retained samples for one entity."""
        key = (
            self._entity(aircraft_id, "aircraft_id"),
            self._entity(component, "component"),
        )
        return len(self._buffers.get(key, ()))

    def latest(
        self,
        aircraft_id: str,
        component: str,
        *,
        require_full: bool = True,
    ) -> tuple[TelemetryPoint, ...]:
        """Return the most recent samples in chronological order."""
        key = (
            self._entity(aircraft_id, "aircraft_id"),
            self._entity(component, "component"),
        )
        buffer = self._buffers.get(key)
        if buffer is None:
            raise KeyError(f"No telemetry history for {key[0]}/{key[1]}")

        if require_full and len(buffer) < self.window_size:
            raise ValueError(
                f"Need {self.window_size} cycles for {key[0]}/{key[1]}, "
                f"but only {len(buffer)} are available"
            )
        return tuple(buffer)

    def latest_array(
        self,
        aircraft_id: str,
        component: str,
        feature_names: Iterable[str],
        *,
        require_full: bool = True,
    ) -> np.ndarray:
        """Return the latest window as a float32 [cycles, features] array."""
        names = tuple(feature_names)
        if not names or any(not isinstance(name, str) or not name.strip() for name in names):
            raise ValueError("feature_names must contain non-empty strings")

        points = self.latest(
            aircraft_id,
            component,
            require_full=require_full,
        )
        missing = sorted(
            {
                name.strip()
                for point in points
                for name in names
                if name.strip() not in point.values
            }
        )
        if missing:
            raise ValueError(
                "Telemetry window is missing required features: "
                + ", ".join(missing)
            )

        return np.asarray(
            [[point.values[name.strip()] for name in names] for point in points],
            dtype=np.float32,
        )

    def clear(
        self,
        aircraft_id: str,
        component: str,
    ) -> None:
        """Clear one aircraft/component history."""
        key = (
            self._entity(aircraft_id, "aircraft_id"),
            self._entity(component, "component"),
        )
        self._buffers.pop(key, None)
        self._last_cycle.pop(key, None)

    def clear_all(self) -> None:
        """Clear all retained telemetry history."""
        self._buffers.clear()
        self._last_cycle.clear()
