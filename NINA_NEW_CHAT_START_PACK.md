# NinaOS New Chat Start Pack — Constitution V6

## Governing law

Read `NinaOS_Constitution_V6.md` first. It is authoritative; V5.1 is historical.

NinaOS is a universal AI workforce operating system. The customer tells Nina
the desired result. Nina coordinates the best permitted people, ready workers,
AI providers, systems, channels, devices, and future robots. Nina is not one
model, and the experience remains Nina-centered.

## Repository checkpoint

- Repository: `pykylv-cmd/nina7727`
- Branch: `feature/web-chat-v1`
- Architecture checkpoint before V6: `a9c639df62c65098fcbb6fb69fdb334398848593`
- Latest documented deployed functional commit:
  `fe5dba4839e59daa4b0ad0b7d3f3fb812b2f3e70`
- Always verify current Git and deployment state; do not assume either hash is
  still current.

Implemented: Platform Core V1, RolePack System V1, Ready Worker Catalog V1.

Next exact task: **Agent Assignment V1**. Do not rebuild completed layers.

## Present truth versus direction

- WhatsApp: partial. Meta Cloud API plus Personal and Company/Baileys paths,
  persistence, endpoints, and tests exist. The universal Channel Layer is not
  complete.
- AI providers: OpenAI runtime integration is evidenced. A provider-neutral AI
  Provider Hub, other providers, model routing, and evaluation are strategic.
- Voice: experimental/partial browser audio input and OpenAI transcription.
  Complete provider-neutral STT/TTS, telephony, interruption, and voice
  continuity are not established.
- Robots/humanoids: strategic future only. No physical control is implemented;
  local safety controllers remain authoritative.
- Nina Trust Layer: mandatory governing rule across every current and future
  layer, even before it becomes one consolidated implementation layer.

## Architecture boundary

`RolePack -> Ready Worker Definition -> Agent Assignment (next) -> Knowledge Vault -> Universal Work ownership/execution`

Definitions are not customer-owned worker instances. Channels and providers are
adapters, not identity or work truth.

## Required safety

- PostgreSQL is authoritative hosted persistence and hosted startup fails
  closed.
- Preserve EXPAND-first managed migrations, rolling compatibility, restart
  persistence, request gating, tenant isolation, and liveness/readiness split.
- Preserve separate Telegram/Core (`app.py`) and Web (`web_app.py`) runtimes.
- Never expose credentials, tokens, keys, provider identities, or database URLs.
- Capabilities and permissions are separate; use least privilege and approval.
- Distinguish planned, implemented, tested, deployed, and production-verified.
- Do not deploy or change Railway without explicit authorization.

## Railway staging record

Project `confident-expression`, environment `staging`, Web/Core
`secure-rebirth`, Company WhatsApp bridge `happy-education`. The recorded
deployed commit is `fe5dba4...`; verify externally before relying on it.

## Files to inspect before Agent Assignment

`NinaOS_Constitution_V6.md`, `NINA_ARCHITECTURE_LEDGER.md`,
`NINA_PROJECT_STATE.json`, `platform_core.py`, `rolepack_system.py`,
`ready_worker_registry.py`, `ready_worker_catalog.py`,
`runtime_readiness.py`, `persistence_backend.py`, `managed_migrations.py`,
`web_app.py`, and the corresponding tests.
