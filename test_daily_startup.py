import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PUBLIC_DAILY_FUNCTIONS = (
    "build_daily_answer",
    "build_morning_answer",
    "build_evening_answer",
    "build_goal_prompt_answer",
)


class DailyStartupTests(unittest.TestCase):
    def _import_in_subprocess(self, statement):
        with tempfile.TemporaryDirectory() as tmp:
            env = dict(os.environ)
            env.update({
                "OPENAI_API_KEY": "test-key",
                "TELEGRAM_TOKEN": "123456:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi",
                "NINA_RUNTIME_ENV": "test",
                "NINA_DB_FILE": str(Path(tmp) / "daily-startup.sqlite"),
                "PYTHONPATH": os.pathsep.join(
                    filter(None, [str(ROOT), env.get("PYTHONPATH", "")])
                ),
            })
            return subprocess.run(
                [sys.executable, "-c", statement],
                cwd=ROOT,
                env=env,
                text=True,
                capture_output=True,
                timeout=60,
            )

    def test_daily_import_exposes_real_public_builders_without_fallback(self):
        names = repr(PUBLIC_DAILY_FUNCTIONS)
        result = self._import_in_subprocess(
            f"import daily; names={names}; "
            "assert all(callable(getattr(daily, name, None)) for name in names); "
            "assert daily.build_daily_answer(name='Nina').startswith('👋 Sveiks, Nina!'); "
            "print('daily-startup-ok')"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        output = result.stdout + result.stderr
        self.assertIn("daily-startup-ok", output)
        self.assertNotIn("partially initialized module 'daily'", output)
        self.assertNotIn("daily.py imports nav pieejams, izmantoju fallback", output)

    def test_app_resolves_the_public_functions_from_daily(self):
        names = repr(PUBLIC_DAILY_FUNCTIONS)
        result = self._import_in_subprocess(
            f"import app, daily; names={names}; "
            "assert all(getattr(app, name, None) is getattr(daily, name, None) for name in names); "
            "print('app-daily-interface-ok')"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        output = result.stdout + result.stderr
        self.assertIn("app-daily-interface-ok", output)
        self.assertNotIn("partially initialized module 'daily'", output)
        self.assertNotIn("daily.py imports nav pieejams, izmantoju fallback", output)

    def test_daily_source_contains_no_self_import(self):
        source = (ROOT / "daily.py").read_text(encoding="utf-8")
        self.assertNotIn("from daily import", source)
        self.assertNotIn("import daily", source)
        for name in PUBLIC_DAILY_FUNCTIONS:
            self.assertIn(f"def {name}(", source)


if __name__ == "__main__":
    unittest.main()
