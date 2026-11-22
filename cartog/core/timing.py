"""Per-stage wall time and peak memory for one analysis run (E4/V1).

The numbers are forensic: they describe this machine and this run. They are
recorded only in ``meta.json`` and never in the deterministic artefacts that
``scripts/golden.py`` hashes.
"""

from __future__ import annotations

import time
import tracemalloc


class StageTimer:
    """Collect one duration per named stage, and optionally peak memory.

    ``track_memory=False`` keeps the timer nearly free and records no
    ``peak_memory_mb`` or stage keys, so a normal run's ``meta.json`` is
    unchanged. ``track_memory=True`` starts ``tracemalloc`` and adds the
    measurements when :meth:`payload` is called.
    """

    def __init__(self, *, track_memory: bool = False) -> None:
        """Create a timer; start tracing allocations only when asked."""
        self.track_memory = track_memory
        self.stage_ms: dict[str, float] = {}
        self.peak_memory_mb = 0.0
        self._stopped = False
        if track_memory:
            tracemalloc.start()

    @staticmethod
    def now() -> float:
        """Return a monotonic start marker for :meth:`record`."""
        return time.perf_counter()

    def record(self, name: str, started: float) -> None:
        """Record the time elapsed since ``started`` under ``<name>_ms``."""
        self.stage_ms[f"{name}_ms"] = round((time.perf_counter() - started) * 1000, 2)

    def payload(self, *, total_ms: float) -> dict[str, float]:
        """Return the ``timings`` mapping for ``meta.json``.

        Stage durations and peak memory are included only when memory tracking
        is on. Calling this more than once returns the same measured values.
        """
        data: dict[str, float] = {"total_ms": round(total_ms, 2)}
        if not self.track_memory:
            return data
        if not self._stopped:
            _, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            self._stopped = True
            self.peak_memory_mb = round(peak / (1024 * 1024), 3)
        data["peak_memory_mb"] = self.peak_memory_mb
        data.update(self.stage_ms)
        return data
