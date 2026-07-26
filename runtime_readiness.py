"""Central liveness/readiness state for NinaOS Python runtimes."""

from __future__ import annotations

import threading
from collections import OrderedDict


class RuntimeReadiness:
    def __init__(self, runtime_name):
        self.runtime_name = str(runtime_name or "unknown")
        self._lock = threading.RLock()
        self._checks = OrderedDict()
        self.reset()

    def reset(self):
        with self._lock:
            self._ready = False
            self._startup_started = False
            self._startup_completed = False
            self._failure_class = ""
            self._check_results = OrderedDict()

    def register(self, name, check):
        if not callable(check):
            raise TypeError("readiness_check_must_be_callable")
        with self._lock:
            self._checks[str(name)] = check

    def begin_startup(self):
        with self._lock:
            self._ready = False
            self._startup_started = True
            self._startup_completed = False
            self._failure_class = ""
            self._check_results = OrderedDict()

    @staticmethod
    def _check_succeeded(result):
        if isinstance(result, dict):
            return bool(result.get("ok"))
        return result is not False

    def run_checks(self):
        for name, check in tuple(self._checks.items()):
            try:
                result = check()
                if not self._check_succeeded(result):
                    raise RuntimeError(f"readiness_check_failed:{name}")
                with self._lock:
                    self._check_results[name] = True
            except Exception as exc:
                with self._lock:
                    self._check_results[name] = False
                    self._failure_class = type(exc).__name__
                    self._ready = False
                    self._startup_completed = False
                raise
        return True

    def complete_startup(self):
        with self._lock:
            if not self._startup_started:
                raise RuntimeError("readiness_startup_not_started")
            if any(value is not True for value in self._check_results.values()):
                raise RuntimeError("readiness_checks_incomplete")
            if len(self._check_results) != len(self._checks):
                raise RuntimeError("readiness_checks_incomplete")
            self._startup_completed = True
            self._ready = True
            self._failure_class = ""

    def fail_startup(self, exc):
        with self._lock:
            self._ready = False
            self._startup_completed = False
            self._failure_class = type(exc).__name__ if exc is not None else "RuntimeError"

    @property
    def ready(self):
        with self._lock:
            return bool(self._ready and self._startup_completed)

    def liveness(self):
        return {
            "alive": True,
            "runtime": self.runtime_name,
        }

    def snapshot(self):
        with self._lock:
            return {
                "ready": bool(self._ready and self._startup_completed),
                "runtime": self.runtime_name,
                "startup_started": bool(self._startup_started),
                "startup_completed": bool(self._startup_completed),
                "checks": dict(self._check_results),
                "failure_class": self._failure_class,
            }


_RUNTIMES = {}
_RUNTIMES_LOCK = threading.Lock()


def get_runtime_readiness(runtime_name):
    name = str(runtime_name or "unknown")
    with _RUNTIMES_LOCK:
        state = _RUNTIMES.get(name)
        if state is None:
            state = RuntimeReadiness(name)
            _RUNTIMES[name] = state
        return state
