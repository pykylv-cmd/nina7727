import ast
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
ENTRYPOINTS = {
    "app.py": "initialize_app_runtime",
    "web_app.py": "initialize_web_runtime",
    "daily.py": "initialize_daily_runtime",
    "sales_engine.py": "initialize_sales_runtime",
}


class StartupDeterminismTests(unittest.TestCase):
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

    def test_imports_do_not_initialize_database(self):
        with tempfile.TemporaryDirectory() as tmp:
            for module_name in ("app", "web_app", "daily", "sales_engine"):
                with self.subTest(module=module_name):
                    db_file = Path(tmp) / f"{module_name}.sqlite"
                    result = subprocess.run(
                        [
                            sys.executable,
                            "-c",
                            f"import {module_name}; "
                            f"assert callable({module_name}.{ENTRYPOINTS[module_name + '.py']}); "
                            "print('import-ok')",
                        ],
                        cwd=ROOT,
                        env=self._environment(db_file),
                        text=True,
                        capture_output=True,
                        timeout=60,
                    )
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertIn("import-ok", result.stdout)
                    self.assertFalse(db_file.exists(), module_name)

    def test_startup_initializers_are_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            for module_name in ("app", "daily", "sales_engine"):
                with self.subTest(module=module_name):
                    db_file = Path(tmp) / f"{module_name}-startup.sqlite"
                    initializer = ENTRYPOINTS[module_name + ".py"]
                    result = subprocess.run(
                        [
                            sys.executable,
                            "-c",
                            f"import {module_name}; "
                            f"assert {module_name}.{initializer}() is True; "
                            f"assert {module_name}.{initializer}() is False; "
                            "print('startup-ok')",
                        ],
                        cwd=ROOT,
                        env=self._environment(db_file),
                        text=True,
                        capture_output=True,
                        timeout=60,
                    )
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertIn("startup-ok", result.stdout)
                    self.assertTrue(db_file.exists(), module_name)

    def test_no_top_level_schema_initialization_call_remains(self):
        for filename, initializer in ENTRYPOINTS.items():
            tree = ast.parse((ROOT / filename).read_text(encoding="utf-8"))
            top_level_calls = [
                node.value.func.id
                for node in tree.body
                if isinstance(node, ast.Expr)
                and isinstance(node.value, ast.Call)
                and isinstance(node.value.func, ast.Name)
            ]
            self.assertNotIn("init_db", top_level_calls, filename)
            source = (ROOT / filename).read_text(encoding="utf-8")
            self.assertIn(f"def {initializer}(", source)

    def test_mandatory_app_contract_fails_clearly(self):
        with tempfile.TemporaryDirectory() as tmp:
            code = (
                "import app; "
                "app.ONE_NINA_WORK_OBJECTS_READY=False; "
                "app.ONE_NINA_DOCUMENT_INTAKE_READY=False; "
                "app.validate_mandatory_startup_components()"
            )
            result = subprocess.run(
                [sys.executable, "-c", code],
                cwd=ROOT,
                env=self._environment(Path(tmp) / "unused.sqlite"),
                text=True,
                capture_output=True,
                timeout=60,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(
                "nina_mandatory_startup_components_unavailable:"
                "work_objects,document_intake",
                result.stderr,
            )


if __name__ == "__main__":
    unittest.main()
