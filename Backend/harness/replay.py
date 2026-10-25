from __future__ import annotations
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Optional, Callable

class ReplayClock:
    """
    Simulated clock managing episode time travel, playback, pause, and speed warp.
    Episode = 10 days (240 h), first 48 h warm-up.
    """
    def __init__(self, start_time: Optional[datetime] = None, total_hours: int = 240):
        self.start_time = start_time or datetime(2026, 7, 26, 0, 0, 0, tzinfo=timezone.utc)
        self.total_hours = total_hours
        self.current_step_h = 48  # start at end of warm-up
        self.speed = 1.0          # 1.0 = 1 sec per sim-hour
        self.is_paused = True
        self._lock = threading.RLock()
        self._on_tick_callbacks = []

    @property
    def as_of(self) -> datetime:
        with self._lock:
            return self.start_time + timedelta(hours=self.current_step_h)

    def register_callback(self, cb: Callable[[datetime, int], None]):
        self._on_tick_callbacks.append(cb)

    def seek(self, hour: int):
        with self._lock:
            self.current_step_h = max(0, min(self.total_hours, hour))
            current_as_of = self.as_of
        for cb in self._on_tick_callbacks:
            cb(current_as_of, self.current_step_h)

    def set_speed(self, speed_mult: float):
        with self._lock:
            self.speed = max(0.1, min(10.0, speed_mult))

    def play(self):
        with self._lock:
            self.is_paused = False

    def pause(self):
        with self._lock:
            self.is_paused = True

    def step(self, delta_h: int = 1):
        with self._lock:
            self.current_step_h = min(self.total_hours, self.current_step_h + delta_h)
            current_as_of = self.as_of
        for cb in self._on_tick_callbacks:
            cb(current_as_of, self.current_step_h)
