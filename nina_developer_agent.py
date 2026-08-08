"""Outbound-only read-only Windows agent for Nina Developer."""

from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

REPOSITORY_ROOT = Path(r"C:\Users\User\Documents\nina7727")
BLOCKED_NAMES = {".env", ".env.local", ".env.production", ".git", "nina_memory.db"}
BLOCKED_SUFFIXES = {".pem", ".key", ".p12", ".pfx", ".keystore"}
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
        matches, scanned = [], 0
        for path in files:
            if scanned >= MAX_SEARCH_FILES or len(matches) >= MAX_RESULTS or not path.is_file():
                continue
            scanned += 1
            try:
                text = self._read(str(path.relative_to(self.root)))
            except (DeveloperAgentError, OSError):
                continue
            for line_number, line in enumerate(text.splitlines(), 1):
                if needle.casefold() in line.casefold():
                    matches.append({"path": str(path.relative_to(self.root)), "line": line_number,
                                    "text": line.strip()[:300]})
                    if len(matches) >= MAX_RESULTS:
                        break
        return {"query": needle, "matches": matches, "scanned_files": scanned}


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
