import ast
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
APP_PATH = ROOT / "app.py"
LATE_PUBLIC_NAMES = (
    "stripe_production_checklist_answer",
    "revenue_dashboard_answer",
    "referral_answer",
    "referral_start_code",
)


def _is_main_guard(node):
    return (
        isinstance(node, ast.If)
        and isinstance(node.test, ast.Compare)
        and ast.unparse(node.test) == "__name__ == '__main__'"
    )


class TelegramEntrypointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = APP_PATH.read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.source)

    def _environment(self, db_file):
        env = dict(os.environ)
        env.update({
            "OPENAI_API_KEY": "test-key",
            "TELEGRAM_TOKEN": "123456:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi",
            "NINA_RUNTIME_ENV": "test",
            "NINA_DB_FILE": str(db_file),
            "PYTHONPATH": os.pathsep.join(
                filter(None, [str(ROOT), env.get("PYTHONPATH", "")])
            ),
        })
        for name in (
            "DATABASE_URL", "POSTGRES_URL", "POSTGRES_PRIVATE_URL",
            "POSTGRES_PUBLIC_URL", "DATABASE_PRIVATE_URL", "DATABASE_PUBLIC_URL",
            "PGURL", "PG_URL", "RAILWAY_DATABASE_URL", "RAILWAY_POSTGRES_URL",
            "POSTGRES_CONNECTION_URL", "DATABASE_CONNECTION_URL",
        ):
            env.pop(name, None)
        return env

    def test_one_final_main_guard_calls_explicit_startup(self):
        guards = [
            (index, node)
            for index, node in enumerate(self.tree.body)
            if _is_main_guard(node)
        ]
        self.assertEqual(len(guards), 1)
        index, guard = guards[0]
        self.assertEqual(index, len(self.tree.body) - 1)
        self.assertEqual(len(guard.body), 1)
        self.assertEqual(ast.unparse(guard.body[0]), "run_telegram_core()")

    def test_no_definition_remains_after_main_guard(self):
        guard_index = next(
            index for index, node in enumerate(self.tree.body) if _is_main_guard(node)
        )
        after_guard = self.tree.body[guard_index + 1:]
        self.assertFalse(
            any(isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                for node in after_guard)
        )

    def test_blocking_polling_occurs_only_inside_explicit_startup(self):
        startup = next(
            node for node in self.tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "run_telegram_core"
        )
        polling_calls = [
            node for node in ast.walk(startup)
            if isinstance(node, ast.Call)
            and ast.unparse(node.func) == "telegram_app.run_polling"
        ]
        self.assertEqual(len(polling_calls), 1)
        for node in self.tree.body:
            if node is startup or _is_main_guard(node):
                continue
            self.assertFalse(
                any(
                    isinstance(child, ast.Call)
                    and ast.unparse(child.func) == "telegram_app.run_polling"
                    for child in ast.walk(node)
                )
            )

    def test_import_exposes_all_late_public_definitions_and_handlers(self):
        with tempfile.TemporaryDirectory() as tmp:
            names = repr(LATE_PUBLIC_NAMES)
            code = (
                f"import app; names={names}; "
                "assert all(callable(getattr(app, name, None)) for name in names); "
                "assert callable(app.run_telegram_core); "
                "registered=[handler for group in app.telegram_app.handlers.values() "
                "for handler in group]; "
                "assert len(registered) == 6, len(registered); "
                "print('telegram-entrypoint-ok')"
            )
            result = subprocess.run(
                [sys.executable, "-c", code],
                cwd=ROOT,
                env=self._environment(Path(tmp) / "entrypoint.sqlite"),
                text=True,
                capture_output=True,
                timeout=60,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("telegram-entrypoint-ok", result.stdout)


if __name__ == "__main__":
    unittest.main()
