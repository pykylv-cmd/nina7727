# NINA_ARCHITECTURE_LEDGER.md

## AL-009 — Platform Foundation V1 checkpoint
Status: ACTIVE
Implementation checkpoint: `fe5dba4839e59daa4b0ad0b7d3f3fb812b2f3e70`

NinaOS is not a bot builder. Customers receive ready AI workers assembled from
reviewed, versioned platform definitions.

`RolePack → Ready Worker Definition → future Agent Assignment → future Knowledge Vault → future Universal Work ownership and execution`

RolePacks and Ready Workers are definitions only. They do not create a
customer-owned worker, execute work, provision channels, or create billing.

### Platform Core V1

`PlatformCapabilityRegistry` is authoritative, thread-safe, validates duplicate
IDs, dependencies, cycles and startup order, tracks enabled/healthy state, and
returns immutable snapshots.

| Order | Capability ID | Dependencies |
|---:|---|---|
| 10 | `persistence_backend` | none |
| 20 | `deployment_compatibility` | `persistence_backend` |
| 30 | `work_objects` | `persistence_backend` |
| 40 | `contact_identity` | `persistence_backend` |
| 50 | `message_service` | `persistence_backend`, `work_objects`, `contact_identity` |
| 60 | `channel_services` | `message_service`, `contact_identity` |
| 70 | `rolepack_system` | `work_objects`, `channel_services` |
| 80 | `ready_worker_catalog` | `rolepack_system` |

Web and Telegram/Core readiness call `initialize_platform_runtime()`. READY
requires initialization, a valid graph, and healthy enabled required
capabilities.

### RolePack System V1

`rolepack_system.py` owns immutable versioned definitions and a thread-safe
registry with exact/latest/latest-compatible lookup, explicit replacement,
validation and immutable snapshots.

Built-ins: `executive_assistant`, `customer_support`, `sales_assistant`.

Validation covers IDs, versions, duplicates, capability overlap, canonical
channels and Work Object types, languages, JSON-safe metadata and required
Platform capabilities. RolePacks define jobs and permissions; they do not
execute customer work.

### Ready Worker Catalog V1

The existing `ready_worker_catalog.py` command API is preserved and re-exports
the additive immutable registry in `ready_worker_registry.py`. Definitions pin
exact ordered RolePack versions and support one-role and future multi-role
composition.

Channels, languages, tools and Work Object types use least-privilege
intersection. Required capabilities are the exact union from bound RolePacks.
The primary RolePack controls category and default operating role.

Built-ins: `nina_executive_assistant`, `nina_customer_support`,
`nina_sales_assistant`.

Provisioning defaults are immutable and JSON-safe. Ready Workers remain catalog
definitions, not customer-owned instances.

### Next: Agent Assignment V1

Agent Assignment will persist one customer workspace, one exact Ready Worker
version, one stable worker instance ID, lifecycle/provisioning state, and
customer language, timezone and permissions in PostgreSQL. It will not yet
execute autonomous work or provision external channels.

### Foundation delivery order

This checkpoint refines but does not replace the Constitution's broader roadmap:

1. Platform Core V1 — completed
2. RolePack System V1 — completed
3. Ready Worker Catalog V1 — completed
4. Agent Assignment V1 — next
5. Knowledge Vault V1
6. Universal Work Objects V1
7. Channel Layer V1
8. Billing V1
9. Nina Exchange V1
10. Mobile and later platform layers

### Verified staging and tests

- Railway: `confident-expression` / `staging` / `secure-rebirth`
- Deployed commit: `fe5dba4839e59daa4b0ad0b7d3f3fb812b2f3e70`
- Pre-deploy: `python manage_migrations.py expand`
- Start: `python web_app.py`
- `/live`: `{"alive":true,"runtime":"web"}`
- `/ready`: `ready=true`
- Checks: `persistence_backend`, `deployment_compatibility`, `work_objects`,
  `contact_identity`, `message_service`, `channel_services`, `platform_core`,
  `rolepack_system`, `ready_worker_catalog`
- `startup_started=true`, `startup_completed=true`, failure class empty
- Python 213/213; Node 38/38; focused foundation 60/60; deployment safety 38/38
- Syntax, imports, legacy compatibility and `git diff --check` passed

No secret or database URL value is recorded.

---

Version: 1.0
Status: ACTIVE

## Mērķis

Šis ir NinaOS arhitektūras lēmumu žurnāls.

Tas glabā atbildes uz jautājumu:
**Kāpēc tika pieņemts šis arhitektūras lēmums?**

---

## AL-001 — NinaOS nav Telegram bots
Statuss: ACTIVE

NinaOS ir AI Economy Operating System.
Telegram ir tikai testa un komunikācijas vide.

---

## AL-002 — Nina ir pirmais AI darbinieks
Statuss: ACTIVE

Nina nav platforma.
Nina ir pirmais AI darbinieks, kas izmanto NinaOS Kernel.

---

## AL-003 — Vienots Kernel
Statuss: ACTIVE

Visi AI darbinieki izmanto kopīgu:
- Identity
- Memory
- Router
- Security
- Context
- Permissions

---

## AL-004 — Master Router
Statuss: IN PROGRESS

Visas ienākošās ziņas vispirms apstrādā Router.

---

## AL-005 — Reply Builder
Statuss: ACTIVE DIRECTION

Gala tekstu veido tikai Reply Builder.

---

## AL-006 — Dokumentācija ir primāra
Statuss: ACTIVE

Vispirms tiek atjaunota dokumentācija.
Pēc tam tiek mainīts kods.

---

## AL-007 — Pilni faili
Statuss: ACTIVE

GitHub vienmēr tiek ielādēti pilni faili.

---

## AL-008 — Platformas princips
Statuss: ACTIVE

Ja funkciju var izmantot visi AI darbinieki,
tā pieder NinaOS.

Ja tā vajadzīga tikai vienam AI,
tā pieder konkrētajam AI darbiniekam.

---

Katrs jaunais arhitektūras lēmums tiek pievienots šim dokumentam.
