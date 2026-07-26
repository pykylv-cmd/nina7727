"""Version contract used to gate NinaOS rolling deployments."""

from __future__ import annotations

import os
import re

import persistence_backend


DATABASE_COMPATIBILITY_VERSION = 1
DATABASE_COMPATIBILITY_MIN = 1
DATABASE_COMPATIBILITY_MAX = 1
INTERNAL_API_COMPATIBILITY_VERSION = 1
INTERNAL_API_COMPATIBILITY_MIN = 1
INTERNAL_API_COMPATIBILITY_MAX = 1


class DeploymentCompatibilityError(RuntimeError):
    pass


def _integer(name, default):
    raw = str(os.environ.get(name) or "").strip()
    if not raw:
        return int(default)
    try:
        value = int(raw)
    except ValueError as exc:
        raise DeploymentCompatibilityError(
            f"nina_compatibility_invalid_integer:{name}"
        ) from exc
    if value < 1:
        raise DeploymentCompatibilityError(
            f"nina_compatibility_invalid_integer:{name}"
        )
    return value


def commit_identifier():
    for name in ("RAILWAY_GIT_COMMIT_SHA", "NINA_COMMIT_SHA", "GIT_COMMIT"):
        value = str(os.environ.get(name) or "").strip()
        if value and re.fullmatch(r"[A-Za-z0-9._-]{7,64}", value):
            return value[:64]
    return "unknown"


class DeploymentCompatibilityContract:
    def __init__(
        self,
        application_version,
        service_role,
        database_min=DATABASE_COMPATIBILITY_MIN,
        database_max=DATABASE_COMPATIBILITY_MAX,
        internal_api_version=INTERNAL_API_COMPATIBILITY_VERSION,
    ):
        self.application_version = str(application_version)
        self.service_role = str(service_role)
        self.database_min = int(database_min)
        self.database_max = int(database_max)
        self.internal_api_version = int(internal_api_version)

    def detected_database_version(self):
        return _integer(
            "NINA_DATABASE_COMPATIBILITY_VERSION",
            DATABASE_COMPATIBILITY_VERSION,
        )

    def assert_compatible(self):
        database_version = self.detected_database_version()
        if not self.database_min <= database_version <= self.database_max:
            raise DeploymentCompatibilityError(
                "nina_database_compatibility_unsupported:"
                f"runtime={self.database_min}-{self.database_max}:"
                f"database={database_version}"
            )
        from managed_migrations import assert_required_migrations_complete
        if persistence_backend.HOSTED:
            assert_required_migrations_complete()
        return True

    def identity(self):
        database_version = self.detected_database_version()
        return {
            "application_version": self.application_version,
            "database_compatibility_version": database_version,
            "database_compatibility_supported": {
                "min": self.database_min,
                "max": self.database_max,
            },
            "internal_api_compatibility_version": self.internal_api_version,
            "internal_api_compatibility_supported": {
                "min": INTERNAL_API_COMPATIBILITY_MIN,
                "max": INTERNAL_API_COMPATIBILITY_MAX,
            },
            "service_role": self.service_role,
            "commit_identifier": commit_identifier(),
            "rolling_deploy_policy": "expand-deploy-contract",
        }
