"""Evidence-bound ONE NINA code proposal generation for Developer Self-Coding V1."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple

MAX_FILES = 3
FORBIDDEN_PATHS = {".env", "nina_memory.db"}


def _extract_json(raw: str) -> Dict[str, Any]:
    text = str(raw or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.I)
        text = re.sub(r"\s*```$", "", text)
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.S)
        if not match:
            raise ValueError("developer_self_coding_json_required")
        payload = json.loads(match.group(0))
    if not isinstance(payload, dict):
        raise ValueError("developer_self_coding_object_required")
    return payload


def _safe_paths(values) -> List[str]:
    files = [str(value or "").replace("\\", "/").strip() for value in (values or [])]
    if not files or len(files) > MAX_FILES or len(files) != len(set(files)):
        raise ValueError("developer_self_coding_file_scope_invalid")
    if any(
        (not path)
        or path.startswith("/")
        or path.startswith("../")
        or "/../" in path
        or path in FORBIDDEN_PATHS
        for path in files
    ):
        raise ValueError("developer_self_coding_file_forbidden")
    return files


def build_self_coding_proposal(
    *,
    question: str,
    cited: List[Dict[str, Any]],
    source_hashes: Dict[str, str],
    generator: Callable[[str], Any],
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    evidence = [
        {
            "role": item.get("role"),
            "path": item.get("path"),
            "line": item.get("line"),
            "symbol": item.get("symbol"),
            "source_hash": item.get("source_hash"),
        }
        for item in cited
    ]
    if not evidence or not all(
        item.get("path") and item.get("line") and item.get("source_hash")
        for item in evidence
    ):
        raise ValueError("developer_self_coding_evidence_required")

    prompt = (
        "You are ONE NINA operating the owner-only NinaOS Developer capability.\n"
        "Return ONLY one JSON object.\n"
        "You are generating a PROPOSAL only. Never claim you wrote, committed, pushed, or deployed.\n"
        "Current repository evidence is authoritative.\n"
        "Never create a second Nina, second brain, second conversation store, channel-specific brain, "
        "parallel task truth, or a parallel customer/work truth.\n"
        "Use the existing controlled-write approval and local Developer Agent.\n"
        "Propose the smallest safe implementation. Maximum 3 changed files.\n"
        "The unified diff may touch only the listed files.\n"
        "Do not include secrets, credentials, tokens, .env files, databases, or generated artifacts.\n\n"
        "Required JSON fields: problem, root_cause, architecture_boundary, files, functions, reason, risk, "
        "diff, focused_tests, validation.\n"
        "risk must be LOW, MEDIUM, or HIGH.\n"
        "validation must contain py_compile (list) and pytest (list).\n\n"
        "OWNER REQUEST:\n" + str(question or "") +
        "\n\nCURRENT REPOSITORY EVIDENCE:\n" +
        json.dumps(evidence, ensure_ascii=False)
    )

    raw = generator(prompt)
    if isinstance(raw, dict):
        raw = raw.get("text") or raw.get("reply") or raw.get("response") or json.dumps(raw)
    payload = _extract_json(str(raw or ""))

    files = _safe_paths(payload.get("files"))
    diff = str(payload.get("diff") or "")
    if not diff:
        raise ValueError("developer_self_coding_diff_required")

    mentioned = set(re.findall(r"^(?:--- a/|\+\+\+ b/)(.+)$", diff, flags=re.M))
    if not mentioned or mentioned - set(files):
        raise ValueError("developer_self_coding_diff_extra_file")
    if set(files) - mentioned:
        raise ValueError("developer_self_coding_diff_scope_invalid")

    risk = str(payload.get("risk") or "MEDIUM").upper()
    if risk not in {"LOW", "MEDIUM", "HIGH"}:
        raise ValueError("developer_self_coding_risk_invalid")

    focused = [str(value).strip() for value in (payload.get("focused_tests") or []) if str(value).strip()]
    validation = payload.get("validation") if isinstance(payload.get("validation"), dict) else {}
    py_compile_files = [str(value).strip() for value in (validation.get("py_compile") or []) if str(value).strip()]
    pytest_files = [str(value).strip() for value in (validation.get("pytest") or []) if str(value).strip()]
    if len(focused) < 2 or not py_compile_files:
        raise ValueError("developer_self_coding_validation_incomplete")
    if any(path not in files for path in py_compile_files):
        raise ValueError("developer_self_coding_compile_scope_invalid")
    if any(
        path not in files
        or not Path(path).name.startswith("test_")
        or not path.endswith(".py")
        for path in pytest_files
    ):
        raise ValueError("developer_self_coding_pytest_scope_invalid")

    expected = {path: str(source_hashes.get(path) or "") for path in files}
    if any(
        len(value) != 64
        or any(ch not in "0123456789abcdef" for ch in value.casefold())
        for value in expected.values()
    ):
        raise ValueError("developer_self_coding_source_hash_missing")

    analysis = {
        "problem": str(payload.get("problem") or question),
        "repository_evidence": evidence,
        "architecture_boundary": str(
            payload.get("architecture_boundary")
            or "ONE NINA Developer capability using the existing controlled-write approval and local agent."
        ),
        "affected_modules": files,
        "call_chain_dependencies": [str(item.get("symbol") or "") for item in evidence],
        "risks": {
            "classification": risk,
            "items": [
                "Model output is proposal-only until exact owner approval.",
                "Source hashes bind approval to the repository state that was inspected.",
                "The local Developer Agent validates and rolls back on failure.",
            ],
        },
        "alternatives": ["Keep the current read-only behavior."],
        "chosen_solution": str(payload.get("reason") or "Smallest evidence-bound implementation proposal."),
        "why": str(
            payload.get("root_cause")
            or "Owner requested implementation through the existing controlled-write path."
        ),
        "focused_validation_plan": focused,
        "resolved_targets": ["Developer Self-Coding"],
    }

    proposal = {
        "files": files,
        "functions": [str(value) for value in (payload.get("functions") or [])],
        "reason": str(
            payload.get("reason")
            or "Implement the owner request through the existing controlled-write flow."
        ),
        "risk": risk,
        "diff": diff,
        "focused_tests": focused,
        "expected_source_hashes": expected,
        "validation": {"py_compile": py_compile_files, "pytest": pytest_files},
    }
    return analysis, proposal
