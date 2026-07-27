"""Railway pre-deploy entry point for NinaOS managed migrations."""

import argparse

from managed_migrations import (
    PHASE_CONTRACT,
    PHASE_EXPAND,
    preflight_release,
    run_migrations,
)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("preflight", "expand", "contract"))
    parser.add_argument(
        "--allow-contract",
        action="store_true",
        help="Required explicit approval for future CONTRACT migrations.",
    )
    args = parser.parse_args(argv)
    if args.phase == "preflight":
        result = preflight_release(require_postgres=True)
        print(
            "NinaOS migration preflight PASS",
            f"backend={result['backend']}",
            f"ledger_entries={result['ledger_entries']}",
            f"work_object_rows={result['work_object_rows']}",
            f"duplicate_source_keys={result['duplicate_source_keys']}",
            f"events_table={result['events_table']}",
            "pending=" + ",".join(result["pending_migrations"]),
        )
        return 0
    phase = PHASE_EXPAND if args.phase == "expand" else PHASE_CONTRACT
    result = run_migrations(phase=phase, allow_contract=args.allow_contract)
    print(
        "NinaOS migrations complete",
        f"phase={result['phase']}",
        f"applied={len(result['applied'])}",
        f"skipped={len(result['skipped'])}",
        f"adoption={result['adoption']}",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
