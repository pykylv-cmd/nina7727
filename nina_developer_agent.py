"""Outbound-only read-only Windows agent for Nina Developer."""

from __future__ import annotations

import json
import hashlib
import os
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

REPOSITORY_ROOT = Path(r"C:\Users\User\Documents\nina7727")
BLOCKED_NAMES = {".env", ".env.local", ".env.production", ".git", "nina_memory.db"}
BLOCKED_SUFFIXES = {".pem", ".key", ".p12", ".pfx", ".keystore", ".db", ".sqlite", ".sqlite3"}
SAFE_WRITE_SUFFIXES = {".py", ".js", ".mjs", ".cjs", ".json", ".md", ".html", ".css"}
SKIP_SEARCH_DIRECTORIES = {".git", ".pnpm-store", "__pycache__", "node_modules"}
MAX_FILE_BYTES = 512 * 1024
MAX_SEARCH_FILES = 2500
MAX_RESULTS = 100


class DeveloperAgentError(RuntimeError):
    pass


class ReadOnlyDeveloperAgent:
    def __init__(self, repository_root=REPOSITORY_ROOT):
        self.root = Path(repository_root).resolve(strict=True)

    def _path(self, relative=""):
        candidate = (self.root / str(relative or "")).resolve(strict=False)
        try:
            candidate.relative_to(self.root)
        except ValueError as exc:
            raise DeveloperAgentError("path_outside_repository") from exc
        for part in candidate.relative_to(self.root).parts:
            lowered = part.lower()
            if lowered in BLOCKED_NAMES or "credential" in lowered or "secret" in lowered:
                raise DeveloperAgentError("blocked_sensitive_path")
        if candidate.suffix.lower() in BLOCKED_SUFFIXES:
            raise DeveloperAgentError("blocked_sensitive_path")
        return candidate

    def _read(self, relative):
        path = self._path(relative)
        if not path.is_file() or path.stat().st_size > MAX_FILE_BYTES:
            raise DeveloperAgentError("file_not_readable")
        raw = path.read_bytes()
        if b"\x00" in raw:
            raise DeveloperAgentError("binary_file_blocked")
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise DeveloperAgentError("non_utf8_file_blocked") from exc

    def execute(self, operation, arguments=None):
        args = arguments if isinstance(arguments, dict) else {}
        if operation == "list_root":
            return self._list("")
        if operation == "list_directory":
            return self._list(args.get("path", ""))
        if operation == "read_text_file":
            return {"path": str(args.get("path", "")), "text": self._read(args.get("path", ""))}
        if operation == "search_text":
            return self._search(args.get("query", ""), args.get("path", ""))
        if operation == "git_status":
            completed = subprocess.run(
                ["git", "-C", str(self.root), "status", "--short", "--branch"],
                stdin=subprocess.DEVNULL, capture_output=True, text=True,
                timeout=10, check=False, shell=False,
            )
            if completed.returncode:
                raise DeveloperAgentError("git_status_failed")
            return {"status": completed.stdout[:128 * 1024]}
        if operation == "apply_approved_patch":
            return self._apply_approved_patch(args)
        raise DeveloperAgentError("operation_not_allowed")

    def _list(self, relative):
        directory = self._path(relative)
        if not directory.is_dir():
            raise DeveloperAgentError("directory_not_found")
        entries = []
        for item in sorted(directory.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
            try:
                self._path(str(item.relative_to(self.root)))
            except DeveloperAgentError:
                continue
            entries.append({"name": item.name, "type": "directory" if item.is_dir() else "file"})
        return {"path": str(relative or "."), "entries": entries[:500]}

    def _search(self, query, relative):
        needle = str(query or "").strip()
        if not needle or len(needle) > 200:
            raise DeveloperAgentError("invalid_search_query")
        base = self._path(relative)
        if base.is_file():
            files = [base]
        else:
            discovered = []
            for root, directories, filenames in os.walk(base, followlinks=False):
                directories[:] = [name for name in directories if name not in SKIP_SEARCH_DIRECTORIES]
                discovered.extend(Path(root) / name for name in filenames)
                if len(discovered) >= MAX_SEARCH_FILES:
                    break
            files = discovered
        matches, scanned, file_hashes = [], 0, {}
        for path in files:
            if scanned >= MAX_SEARCH_FILES or len(matches) >= MAX_RESULTS or not path.is_file():
                continue
            scanned += 1
            try:
                text = self._read(str(path.relative_to(self.root)))
            except (DeveloperAgentError, OSError):
                continue
            relative_path = str(path.relative_to(self.root))
            file_hashes[relative_path] = hashlib.sha256(text.encode("utf-8")).hexdigest()
            for line_number, line in enumerate(text.splitlines(), 1):
                if needle.casefold() in line.casefold():
                    matches.append({"path": relative_path, "line": line_number,
                                    "text": line.strip()[:300], "raw_text": line[:1000]})
                    if len(matches) >= MAX_RESULTS:
                        break
        matched_hashes = {match["path"]: file_hashes[match["path"]] for match in matches}
        return {"query": needle, "matches": matches, "scanned_files": scanned,
                "file_hashes": matched_hashes}

    @staticmethod
    def _sha256_text(value):
        return hashlib.sha256(str(value).encode("utf-8")).hexdigest()

    def _safe_write_path(self, relative, allow_new=False):
        path = self._path(relative)
        if path.suffix.lower() not in SAFE_WRITE_SUFFIXES:
            raise DeveloperAgentError("write_file_type_blocked")
        if path.is_symlink() or any(parent.is_symlink() for parent in path.parents if parent != self.root):
            raise DeveloperAgentError("symlink_escape_blocked")
        if not path.exists() and not allow_new:
            raise DeveloperAgentError("approved_source_missing")
        if path.exists() and not path.is_file():
            raise DeveloperAgentError("write_target_not_file")
        return path

    @staticmethod
    def _parse_unified_diff(patch_text):
        lines = str(patch_text or "").splitlines()
        files, index = [], 0
        while index < len(lines):
            if not lines[index].startswith("--- a/"):
                index += 1
                continue
            old_path = lines[index][6:]
            index += 1
            if index >= len(lines) or not lines[index].startswith("+++ b/"):
                raise DeveloperAgentError("invalid_patch")
            new_path = lines[index][6:]
            if old_path != new_path:
                raise DeveloperAgentError("rename_not_allowed")
            index += 1
            hunks = []
            while index < len(lines) and not lines[index].startswith("--- a/"):
                if not lines[index].startswith("@@"):
                    index += 1
                    continue
                index += 1
                hunk = []
                while index < len(lines) and not lines[index].startswith("@@") and not lines[index].startswith("--- a/"):
                    line = lines[index]
                    if not line or line[0] not in {" ", "+", "-"}:
                        raise DeveloperAgentError("invalid_patch")
                    hunk.append((line[0], line[1:]))
                    index += 1
                if not hunk:
                    raise DeveloperAgentError("invalid_patch")
                hunks.append(hunk)
            files.append({"path": new_path, "hunks": hunks})
        if not files:
            raise DeveloperAgentError("invalid_patch")
        return files

    @staticmethod
    def _apply_hunks(source_text, hunks):
        newline = "\r\n" if "\r\n" in source_text else "\n"
        trailing = source_text.endswith(("\n", "\r"))
        lines = source_text.splitlines()
        cursor = 0
        for hunk in hunks:
            old = [text for prefix, text in hunk if prefix in {" ", "-"}]
            new = [text for prefix, text in hunk if prefix in {" ", "+"}]
            found = -1
            for candidate in range(cursor, len(lines) - len(old) + 1):
                if lines[candidate:candidate + len(old)] == old:
                    found = candidate
                    break
            if found < 0:
                raise DeveloperAgentError("patch_context_mismatch")
            lines[found:found + len(old)] = new
            cursor = found + len(new)
        result = newline.join(lines)
        return result + newline if trailing else result

    @staticmethod
    def _run_fixed(command, cwd):
        return subprocess.run(command, cwd=str(cwd), stdin=subprocess.DEVNULL,
                              capture_output=True, text=True, timeout=60,
                              check=False, shell=False)

    def _validate_approved_change(self, validation, affected_paths):
        py_files = [str(value) for value in (validation.get("py_compile") or [])]
        pytest_files = [str(value) for value in (validation.get("pytest") or [])]
        affected = set(affected_paths)
        if any(path not in affected or not path.endswith(".py") for path in py_files):
            raise DeveloperAgentError("py_compile_not_allowlisted")
        if any(path not in affected or not Path(path).name.startswith("test_") or not path.endswith(".py")
               for path in pytest_files):
            raise DeveloperAgentError("pytest_not_allowlisted")
        commands = []
        if py_files:
            commands.append([sys.executable, "-m", "py_compile", *py_files])
        if pytest_files:
            commands.append([sys.executable, "-m", "pytest", "--", *pytest_files])
        commands.append(["git", "diff", "--check", "--", *affected_paths])
        results = []
        for command in commands:
            completed = self._run_fixed(command, self.root)
            results.append({"command": command[1:3] if command[0] == sys.executable else command[:3],
                            "returncode": completed.returncode,
                            "output": (completed.stdout + completed.stderr)[:4000]})
            if completed.returncode:
                raise DeveloperAgentError("focused_validation_failed")
        diff = self._run_fixed(["git", "diff", "--", *affected_paths], self.root)
        status = self._run_fixed(["git", "status", "--short"], self.root)
        if diff.returncode or status.returncode:
            raise DeveloperAgentError("git_readback_failed")
        return {"checks": results, "git_diff": diff.stdout[:128 * 1024],
                "git_status": status.stdout[:32 * 1024]}

    def _atomic_write(self, path, text):
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="", delete=False,
                                         dir=str(path.parent), prefix=".nina-approved-", suffix=".tmp") as handle:
            handle.write(text)
            temporary = Path(handle.name)
        os.replace(temporary, path)

    def _apply_approved_patch(self, args):
        approval_id = str(args.get("approval_id") or "")
        patch_text = str(args.get("patch") or "")
        if not approval_id.startswith("devapproval_"):
            raise DeveloperAgentError("invalid_approval")
        try:
            expires_at = datetime.fromisoformat(str(args.get("expires_at") or "").replace("Z", "+00:00"))
        except ValueError as exc:
            raise DeveloperAgentError("invalid_approval") from exc
        if expires_at <= datetime.now(timezone.utc):
            raise DeveloperAgentError("approval_expired")
        if not patch_text or self._sha256_text(patch_text) != str(args.get("diff_hash") or ""):
            raise DeveloperAgentError("approved_diff_changed")
        parsed = self._parse_unified_diff(patch_text)
        parsed_paths = [item["path"] for item in parsed]
        approved_paths = [str(value) for value in (args.get("affected_files") or [])]
        if parsed_paths != approved_paths or len(set(parsed_paths)) != len(parsed_paths):
            raise DeveloperAgentError("approved_paths_changed")
        expected_hashes = args.get("expected_source_hashes") or {}
        backups, outputs = {}, {}
        for item in parsed:
            relative = item["path"]
            path = self._safe_write_path(relative, allow_new=True)
            before = self._read(relative) if path.exists() else None
            actual_hash = self._sha256_text(before or "")
            if actual_hash != str(expected_hashes.get(relative) or ""):
                raise DeveloperAgentError("stale_source_hash")
            backups[relative] = before
            outputs[relative] = self._apply_hunks(before or "", item["hunks"])
        written = []
        try:
            for relative in parsed_paths:
                self._atomic_write(self._safe_write_path(relative, allow_new=True), outputs[relative])
                written.append(relative)
            validation = self._validate_approved_change(args.get("validation") or {}, parsed_paths)
        except Exception:
            for relative in reversed(written):
                path = self._safe_write_path(relative, allow_new=True)
                before = backups[relative]
                if before is None:
                    if path.exists():
                        path.unlink()
                else:
                    self._atomic_write(path, before)
            raise
        return {"approval_id": approval_id, "applied_files": parsed_paths,
                "validation": validation, "write_access": "disabled",
                "deploy_access": "disabled", "write_executed": True}


def _request(base_url, token, path, payload):
    request = Request(base_url.rstrip("/") + path,
        data=json.dumps(payload).encode("utf-8"), method="POST",
        headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"})
    with urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode("utf-8") or "{}")


def run_forever():
    base_url = (os.environ.get("NINA_DEVELOPER_WEB_URL") or "").strip()
    token = (os.environ.get("NINA_DEVELOPER_AGENT_TOKEN") or "").strip()
    local_test_url = base_url.startswith("http://127.0.0.1:") or base_url.startswith("http://localhost:")
    if not (base_url.startswith("https://") or local_test_url) or not token:
        raise DeveloperAgentError("developer_agent_configuration_required")
    agent = ReadOnlyDeveloperAgent()
    while True:
        try:
            _request(base_url, token, "/internal/developer-agent/heartbeat", {"repository": "nina7727"})
            claimed = _request(base_url, token, "/internal/developer-agent/jobs/claim", {})
            job = claimed.get("job")
            if job:
                error_code, result = "", {}
                try:
                    result = agent.execute(job.get("operation"), job.get("arguments"))
                except (DeveloperAgentError, OSError, subprocess.SubprocessError) as exc:
                    error_code = str(exc)[:80]
                _request(base_url, token, "/internal/developer-agent/jobs/result",
                         {"job_id": job.get("job_id"), "result": result, "error_code": error_code})
        except (HTTPError, URLError, TimeoutError, ValueError):
            pass
        time.sleep(2)


if __name__ == "__main__":
    run_forever()
