"""Railway pre-deploy entry point for NinaOS managed migrations."""

import argparse

from managed_migrations import PHASE_CONTRACT, PHASE_EXPAND, run_migrations


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("expand", "contract"))
    parser.add_argument(
        "--allow-contract",
        action="store_true",
        help="Required explicit approval for future CONTRACT migrations.",
    )
    args = parser.parse_args(argv)
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
