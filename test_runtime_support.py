"""Shared explicit runtime setup for local NinaOS integration tests."""

from __future__ import annotations

import os
import sys
import types


TEST_SECRET_ENV = {
    "NINA_RUNTIME_ENV": "test",
    "NINA_CONTACT_IDENTITY_KEY": "test-contact-identity-key-with-stable-entropy",
    "NINA_WEB_WORKSPACE_COOKIE_SECRET": "test-workspace-cookie-secret-with-stable-entropy",
    "NINA_CHANNEL_CREDENTIAL_KEY": (
        "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA="
    ),
    "NINA_PERSONAL_WHATSAPP_BRIDGE_TOKEN": "test-bridge-token",
}


def install_test_environment():
    """Install non-production test defaults before application imports."""
    for name, value in TEST_SECRET_ENV.items():
        os.environ.setdefault(name, value)


def bind_sqlite_database(db_file, *modules):
    """Bind already-imported persistence owners to one isolated SQLite file."""
    import persistence_backend

    shared_owner_names = (
        "channel_connections",
        "client_identity",
        "company_whatsapp",
        "contact_identity",
        "nina_message_service",
        "personal_whatsapp",
        "web_app",
        "work_objects",
    )
    owners = [persistence_backend, *modules]
    owners.extend(
        sys.modules[name]
        for name in shared_owner_names
        if name in sys.modules
    )
    owners = tuple(dict.fromkeys(owners))
    snapshots = []
    global_snapshots = []
    for module in owners:
        snapshots.append(
            (
                module,
                {
                    name: getattr(module, name)
                    for name in (
                        "HOSTED",
                        "DATABASE_URL",
                        "DB_FILE",
                        "USE_POSTGRES",
                        "_SCHEMA_READY",
                    )
                    if hasattr(module, name)
                },
            )
        )
        for value in vars(module).values():
            if not isinstance(value, types.FunctionType):
                continue
            globals_dict = value.__globals__
            if not globals_dict or "DB_FILE" not in globals_dict:
                continue
            if any(existing is globals_dict for existing, _values in global_snapshots):
                continue
            global_snapshots.append(
                (
                    globals_dict,
                    {
                        name: globals_dict[name]
                        for name in (
                            "DATABASE_URL",
                            "DB_FILE",
                            "USE_POSTGRES",
                            "_SCHEMA_READY",
                        )
                        if name in globals_dict
                    },
                )
            )
    persistence_backend.HOSTED = False
    persistence_backend.USE_POSTGRES = False
    persistence_backend.DATABASE_URL = ""
    persistence_backend.DB_FILE = str(db_file)
    for module in modules:
        if hasattr(module, "DATABASE_URL"):
            module.DATABASE_URL = ""
        if hasattr(module, "DB_FILE"):
            module.DB_FILE = str(db_file)
        if hasattr(module, "USE_POSTGRES"):
            module.USE_POSTGRES = False
        if hasattr(module, "_SCHEMA_READY"):
            module._SCHEMA_READY = False
    for globals_dict, _values in global_snapshots:
        globals_dict["DATABASE_URL"] = ""
        globals_dict["DB_FILE"] = str(db_file)
        globals_dict["USE_POSTGRES"] = False
        if "_SCHEMA_READY" in globals_dict:
            globals_dict["_SCHEMA_READY"] = False

    def restore():
        for globals_dict, values in reversed(global_snapshots):
            globals_dict.update(values)
        for module, values in reversed(snapshots):
            for name, value in values.items():
                setattr(module, name, value)

    return restore


def initialize_ready_web(web_module):
    """Run the real explicit Web startup contract for customer-route tests."""
    web_module._WEB_RUNTIME_INITIALIZED = False
    web_module.initialize_web_runtime()
    if not web_module.WEB_RUNTIME_READINESS.ready:
        raise AssertionError(web_module.WEB_RUNTIME_READINESS.snapshot())
