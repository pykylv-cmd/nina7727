import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from cryptography.fernet import Fernet


ROOT = Path(__file__).resolve().parent
WORKSPACE = "ninaos_company"
CONVERSATION_ID = "company:test-restart-sender"


class RestartPersistenceTests(unittest.TestCase):
    def _environment(self, db_file, credential_key):
        env = dict(os.environ)
        env.update({
            "NINA_RUNTIME_ENV": "test",
            "NINA_DB_FILE": str(db_file),
            "NINA_CONTACT_IDENTITY_KEY": "restart-contact-identity-key-at-least-32-bytes",
            "NINA_CHANNEL_CREDENTIAL_KEY": credential_key,
            "NINA_COMPANY_WHATSAPP_WORKSPACE": WORKSPACE,
            "NINA_WEB_WORKSPACE_ID": WORKSPACE,
            "OPENAI_API_KEY": "test-key",
            "TELEGRAM_TOKEN": "123456:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi",
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

    def _run(self, code, env):
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            timeout=90,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        marker_lines = [
            line for line in result.stdout.splitlines()
            if line.startswith("RESTART_RESULT=")
        ]
        self.assertEqual(len(marker_lines), 1, result.stdout)
        return json.loads(marker_lines[0].split("=", 1)[1])

    def test_customer_critical_domains_survive_process_replacement(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_file = Path(tmp) / "restart-persistence.sqlite"
            env = self._environment(db_file, Fernet.generate_key().decode())

            runtime_a = self._run(
                f"""
import json
import channel_connections, client_identity, company_whatsapp
import contact_identity, nina_message_service, work_objects

contact = contact_identity.resolve_contact_identity(
    {WORKSPACE!r}, "company_whatsapp", "opaque-restart-provider-id",
    {{"display_name": "Restart Client", "relationship_type": "client"}},
)
mapping = client_identity.get_or_create_client_mapping(
    {WORKSPACE!r}, contact["contact_id"]
)
nina_message_service.save_channel_turn(
    {WORKSPACE!r}, "Persistent user message", "Persistent Nina reply",
    conversation_id={CONVERSATION_ID!r}, channel="company_whatsapp",
)
work = work_objects.create_work_object(
    object_type="task",
    title="Restart-safe customer task",
    workspace_id={WORKSPACE!r},
    assigned_agent_id="nina_office_manager_smb",
    client_id=mapping["canonical_client_id"],
    status="open",
    metadata={{"content": "Customer-critical content"}},
    origin_channel="company_whatsapp",
    origin_user_id=contact["contact_id"],
    source_key="restart-persistence:v1",
)
company_whatsapp.store_auth_record(
    {WORKSPACE!r}, "creds", {{"registered": True, "account": "opaque"}}
)
channel_connections.set_connection_for_test(
    {WORKSPACE!r}, "whatsapp_company", "connected",
    {{"mode": "company_external", "runtime_state": "connected"}},
)
print("RESTART_RESULT=" + json.dumps({{
    "contact_id": contact["contact_id"],
    "client_id": mapping["canonical_client_id"],
    "work_object_id": work.object_id,
}}, sort_keys=True))
""",
                env,
            )

            # Runtime B is a separate interpreter process. It cannot reuse Runtime A
            # modules, object caches, connection objects, readiness, or Web globals.
            runtime_b = self._run(
                f"""
import json
import channel_connections, client_identity, company_whatsapp
import contact_identity, nina_message_service, work_objects

expected = {runtime_a!r}
assert expected["work_object_id"] not in work_objects.WORK_OBJECT_STORE
contact = contact_identity.resolve_contact_identity(
    {WORKSPACE!r}, "company_whatsapp", "opaque-restart-provider-id",
    {{"display_name": "Restart Client", "relationship_type": "client"}},
)
mapping = client_identity.get_or_create_client_mapping(
    {WORKSPACE!r}, contact["contact_id"]
)
conversation = nina_message_service.load_channel_conversation(
    {CONVERSATION_ID!r}, limit=20
)
work = work_objects.get_work_object(expected["work_object_id"])
auth = company_whatsapp.load_auth_records({WORKSPACE!r})
connection = channel_connections.get_connection(
    {WORKSPACE!r}, "whatsapp_company"
)

assert contact["contact_id"] == expected["contact_id"]
assert mapping["canonical_client_id"] == expected["client_id"]
assert [item["text"] for item in conversation] == [
    "Persistent user message", "Persistent Nina reply"
]
assert work.object_id == expected["work_object_id"]
assert work.status == "open"
assert work.workspace_id == {WORKSPACE!r}
assert work.assigned_agent_id == "nina_office_manager_smb"
assert work.client_id == expected["client_id"]
assert work.title == "Restart-safe customer task"
assert work.metadata["content"] == "Customer-critical content"
assert auth["creds"] == {{"registered": True, "account": "opaque"}}
assert connection["status"] == "connected"
assert connection["metadata"]["mode"] == "company_external"

print("RESTART_RESULT=" + json.dumps({{
    "contact_id": contact["contact_id"],
    "client_id": mapping["canonical_client_id"],
    "work_object_id": work.object_id,
    "conversation_messages": len(conversation),
    "auth_loaded": bool(auth),
    "connection_status": connection["status"],
}}, sort_keys=True))
""",
                env,
            )

            self.assertEqual(runtime_b["contact_id"], runtime_a["contact_id"])
            self.assertEqual(runtime_b["client_id"], runtime_a["client_id"])
            self.assertEqual(runtime_b["work_object_id"], runtime_a["work_object_id"])
            self.assertEqual(runtime_b["conversation_messages"], 2)
            self.assertTrue(runtime_b["auth_loaded"])
            self.assertEqual(runtime_b["connection_status"], "connected")

    def test_process_local_web_state_resets_while_csrf_stays_worker_safe(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = self._environment(
                Path(tmp) / "transient-boundaries.sqlite",
                Fernet.generate_key().decode(),
            )
            code = """
import hashlib, json, web_app
snapshot = {
    "ready": web_app.WEB_RUNTIME_READINESS.ready,
    "csrf_fingerprint": hashlib.sha256(web_app._CHANNEL_CSRF_SECRET).hexdigest(),
    "previews": len(web_app.WORKSPACE_ACTION_PREVIEWS),
    "workflow_states": len(web_app.THREAD_WORKFLOW_STATES),
    "object_cache": len(web_app.WORKSPACE_OBJECT_CACHE),
}
print("RESTART_RESULT=" + json.dumps(snapshot, sort_keys=True))
"""
            runtime_a = self._run(code, env)
            runtime_b = self._run(code, env)
            self.assertFalse(runtime_a["ready"])
            self.assertFalse(runtime_b["ready"])
            self.assertEqual(runtime_a["previews"], 0)
            self.assertEqual(runtime_b["previews"], 0)
            self.assertEqual(runtime_a["workflow_states"], 0)
            self.assertEqual(runtime_b["workflow_states"], 0)
            self.assertEqual(runtime_a["object_cache"], 0)
            self.assertEqual(runtime_b["object_cache"], 0)
            self.assertEqual(
                runtime_a["csrf_fingerprint"], runtime_b["csrf_fingerprint"]
            )

    def test_node_socket_maps_are_explicitly_process_local(self):
        personal_source = (
            ROOT / "personal_whatsapp_bridge" / "src" / "session_manager.js"
        ).read_text(encoding="utf-8")
        company_source = (
            ROOT / "personal_whatsapp_bridge" / "src" / "company_session_manager.js"
        ).read_text(encoding="utf-8")
        self.assertIn("sessions = new Map()", personal_source)
        self.assertIn("companySessions=new Map()", company_source)
        self.assertIn("loadCompanyAuth", company_source)


if __name__ == "__main__":
    unittest.main()
