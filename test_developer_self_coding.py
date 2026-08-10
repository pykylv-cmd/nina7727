import json
import unittest

from developer_router import developer_intents, developer_investigation_plan
from developer_self_coding import build_self_coding_proposal


class DeveloperSelfCodingV1Tests(unittest.TestCase):
    def test_owner_implementation_intent_routes_to_self_coding(self):
        command = (
            "NINA DEVELOPER SELF-CODING LOOP V1 "
            "pabeidz un implementē Developer kodu"
        )
        self.assertIn("implementation_request", developer_intents(command))
        kind, plan = developer_investigation_plan(command)
        self.assertEqual(kind, "developer_self_coding_v1")
        self.assertTrue(plan)

    def test_model_output_is_proposal_only_and_hash_bound(self):
        hashes = {"developer_router.py": "a" * 64}
        cited = [{
            "role": "router_contract",
            "path": "developer_router.py",
            "line": 1,
            "symbol": "def developer_intents",
            "source_hash": "a" * 64,
        }]
        payload = {
            "problem": "x",
            "root_cause": "y",
            "architecture_boundary": "ONE NINA",
            "files": ["developer_router.py"],
            "functions": ["developer_intents"],
            "reason": "minimal",
            "risk": "LOW",
            "diff": (
                "--- a/developer_router.py\n"
                "+++ b/developer_router.py\n"
                "@@ -1 +1 @@\n-old\n+new"
            ),
            "focused_tests": ["route", "regression"],
            "validation": {
                "py_compile": ["developer_router.py"],
                "pytest": [],
            },
        }
        analysis, proposal = build_self_coding_proposal(
            question="implement",
            cited=cited,
            source_hashes=hashes,
            generator=lambda _prompt: json.dumps(payload),
        )
        self.assertEqual(
            proposal["expected_source_hashes"]["developer_router.py"],
            "a" * 64,
        )
        self.assertEqual(analysis["risks"]["classification"], "LOW")

    def test_extra_diff_file_is_rejected(self):
        cited = [{
            "role": "router_contract",
            "path": "developer_router.py",
            "line": 1,
            "symbol": "x",
            "source_hash": "a" * 64,
        }]
        payload = {
            "problem": "x",
            "root_cause": "y",
            "architecture_boundary": "ONE NINA",
            "files": ["developer_router.py"],
            "functions": [],
            "reason": "x",
            "risk": "LOW",
            "diff": (
                "--- a/developer_router.py\n"
                "+++ b/developer_router.py\n"
                "--- a/web_app.py\n"
                "+++ b/web_app.py"
            ),
            "focused_tests": ["a", "b"],
            "validation": {
                "py_compile": ["developer_router.py"],
                "pytest": [],
            },
        }
        with self.assertRaisesRegex(ValueError, "extra_file"):
            build_self_coding_proposal(
                question="x",
                cited=cited,
                source_hashes={"developer_router.py": "a" * 64},
                generator=lambda _prompt: json.dumps(payload),
            )


if __name__ == "__main__":
    unittest.main()
