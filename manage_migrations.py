"""Railway pre-deploy entry point for NinaOS managed migrations."""

import argparse
import json

from managed_migrations import (
    PHASE_CONTRACT,
    PHASE_EXPAND,
    preflight_release,
    run_migrations,
)
from production_schema_adoption import (
    adopt_baseline_apply,
    adoption_plan,
    inspect_production_schema,
    write_reports,
)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "phase",
        choices=(
            "preflight", "expand", "contract",
            "inspect-production-schema", "adopt-baseline",
        ),
    )
    parser.add_argument(
        "--allow-contract",
        action="store_true",
        help="Required explicit approval for future CONTRACT migrations.",
    )
    parser.add_argument("--plan", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--fingerprint", default="")
    parser.add_argument(
        "--json-report", default="production_schema_adoption_report.json"
    )
    parser.add_argument(
        "--markdown-report", default="NINA_PRODUCTION_SCHEMA_ADOPTION_REPORT.md"
    )
    args = parser.parse_args(argv)
    if args.phase == "inspect-production-schema":
        inventory = inspect_production_schema(require_postgres=True)
        print(json.dumps(inventory, indent=2, sort_keys=True))
        return 0
    if args.phase == "adopt-baseline":
        if args.plan == args.apply:
            parser.error("adopt-baseline requires exactly one of --plan or --apply")
        if args.plan:
            result = adoption_plan(require_postgres=True)
            write_reports(
                result, args.json_report, args.markdown_report
            )
            print(
                "NinaOS schema adoption plan",
                "PASS" if result["ok"] else "STOP",
                f"fingerprint={result['fingerprint']}",
                "adoptable=" + ",".join(result["adoptable_migrations"]),
                "expand=" + ",".join(result["requires_expand"]),
                f"conflicts={len(result['conflicts'])}",
            )
            return 0 if result["ok"] else 2
        if not args.fingerprint:
            parser.error("adopt-baseline --apply requires --fingerprint")
        result = adopt_baseline_apply(
            args.fingerprint, require_postgres=True
        )
        print(
            "NinaOS schema adoption apply PASS",
            "adopted=" + ",".join(result["adopted_migrations"]),
            f"fingerprint={result['fingerprint']}",
        )
        return 0
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
