# NinaOS new chat start pack — Platform Foundation V1

Paste this package into a new ChatGPT conversation before continuing NinaOS.

## Governing direction

Follow `NinaOS_Constitution_V5.md` (V5.1).

NinaOS is not a bot builder. Customers receive reviewed ready AI workers.
Telegram, Web and WhatsApp are channels into shared NinaOS capabilities, not
separate brains.

## Repository checkpoint

- Repository: `pykylv-cmd/nina7727`
- Branch: `feature/web-chat-v1`
- Platform implementation checkpoint:
  `fe5dba4839e59daa4b0ad0b7d3f3fb812b2f3e70`
- Architecture checkpoint: this document's commit; verify with
  `git log -1 --oneline`

Completed layers:

1. Platform Core V1
2. RolePack System V1
3. Ready Worker Catalog V1

Do not rebuild or replace these layers.

## Current architecture

`RolePack → Ready Worker Definition → Agent Assignment (next) → Knowledge Vault → Universal Work ownership/execution`

- RolePacks define versioned jobs, permissions and operating boundaries.
- Ready Workers bind exact RolePack versions and immutable provisioning defaults.
- Neither object is a customer-owned worker instance.

## Next exact task

Implement **Agent Assignment V1**.

It must connect:

- one customer workspace;
- one exact Ready Worker version;
- one stable worker instance ID;
- lifecycle and provisioning state;
- customer-specific language, timezone and permissions;
- PostgreSQL persistence.

Agent Assignment V1 must not yet execute autonomous work or provision external
channels.

## Railway staging

- Project: `confident-expression`
- Environment: `staging`
- Web/Core service: `secure-rebirth`
- Deployed commit: `fe5dba4839e59daa4b0ad0b7d3f3fb812b2f3e70`
- Public Web URL: `https://secure-rebirth-staging.up.railway.app`
- Pre-deploy: `python manage_migrations.py expand`
- Start: `python web_app.py`
- `/live`: `{"alive":true,"runtime":"web"}`
- `/ready`: `ready=true`

The Node Company WhatsApp bridge remains `happy-education`; it does not serve the
Web UI.

Never expose database URLs, tokens, encryption keys or credentials.

## Verified test baseline

- Python: 213/213 passed
- Node: 38/38 passed
- Focused catalog/RolePack/Platform/readiness: 60/60 passed
- Deployment-safety regression group: 38/38 passed
- Syntax, required imports, legacy Ready Worker compatibility and
  `git diff --check`: passed

## Inspect these files first

1. `NinaOS_Constitution_V5.md`
2. `NINA_ARCHITECTURE_LEDGER.md`
3. `NINA_PROJECT_STATE.json`
4. `platform_core.py`
5. `rolepack_system.py`
6. `ready_worker_registry.py`
7. `ready_worker_catalog.py`
8. `runtime_readiness.py`
9. `persistence_backend.py`
10. `managed_migrations.py`
11. `web_app.py`
12. `app.py`
13. `test_platform_core.py`
14. `test_rolepack_system.py`
15. `test_ready_worker_catalog.py`

## Safety constraints

- Preserve PostgreSQL fail-closed behavior in hosted runtimes.
- Preserve managed EXPAND migrations and migration ledger validation.
- Preserve liveness/readiness separation and request gating.
- Preserve rolling-deploy compatibility and restart-persistence guarantees.
- Preserve separate `app.py` Telegram/Core and `web_app.py` Web runtimes.
- Do not import `app.py` into `web_app.py`.
- Do not create duplicate memory, routing, work, identity or channel systems.
- Do not change Railway or deploy without explicit approval.

## Known limitations and deferred work

- No Agent Assignment or customer worker instances yet.
- No worker provisioning or runtime multi-role routing.
- No RolePack or Ready Worker database persistence in V1.
- No catalog UI, billing or entitlement system.
- Knowledge Vault, platform-wide Universal Work ownership, Channel Layer,
  Billing, Nina Exchange and later Mobile layers remain deferred.
- Existing legacy Ready Worker command APIs are intentionally preserved.
