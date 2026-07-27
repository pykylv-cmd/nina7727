# NINA_ARCHITECTURE_LEDGER.md

## AL-012 — Agent Assignment V1 implementation

Status: ACTIVE / IMPLEMENTED

Agent Assignment V1 is the tenant-scoped management boundary between an exact
Ready Worker definition and a customer-owned worker instance under ONE NINA.
It stores a stable assignment identity, exact definition version, primary
RolePack reference, display name, validated configuration, least-privilege
permission narrowing, lifecycle state, actor, and timestamps.

Lifecycle:

`draft -> active -> suspended -> active`

`draft | active | suspended -> archived`

Archived is terminal. Tenant and Ready Worker identity are immutable. All reads
and mutations include the server-authenticated tenant context; another tenant
receives the same not-found response as an unknown assignment.

Persistence is the managed EXPAND migration
`0002_agent_assignment_v1`, creating `nina_agent_assignments` with status
CHECK enforcement and tenant, definition, status, tenant/status, and
tenant/definition indexes. Ready Worker and RolePack V1 definitions are
immutable runtime registries rather than database tables, so their exact
references are validated by the service instead of fictional SQL foreign keys.

Agent Assignment is channel- and provider-neutral. It creates no second Nina,
memory, conversation truth, work system, worker execution engine, provider
route, or channel connection.

Verified locally: Python 233/233 and Node 38/38 passed. This is implementation
and test evidence, not deployment or production verification.

Next planned layer: **Knowledge Vault V1**.

---

## AL-011 — ONE NINA and Infinite Workforce

Status: ACTIVE

ONE NINA is the highest architecture principle. It requires one coherent
customer-facing Nina identity and operating relationship across many modular
workers, providers, channels, and future devices. It does not require one
model, process, datastore, region, or failure domain.

Infinite Workforce is compatible with the existing worker chain:

`RolePack -> Ready Worker Definition -> Agent Assignment -> governed worker instance`

The principle permits extensible worker types and large workforce composition;
it does not permit unreviewed bot generation, unlimited authority, autonomous
replication, or bypassing identity, permissions, lifecycle, cost, approval, and
audit. Agent Assignment V1 implements this governed instance boundary; it does
not widen worker authority.

Documentation uses four constitutional statuses: **Implemented**,
**Experimental**, **Planned**, and **Long-Term Vision**. Partial capability must
be described by its evidenced subset and must not promote a complete future
layer to Implemented.

---

## AL-010 — Constitution V6: universal AI workforce operating system

Status: ACTIVE
Governing document: `NinaOS_Constitution_V6.md`

V6 expands V5.1 from an AI workforce/business platform into a durable universal
coordination constitution without weakening V5.1's platform, safety,
persistence, deployment, or workflow rules.

### Decision

- The customer speaks with Nina; Nina is the identity and orchestration layer,
  not an AI provider.
- Provider neutrality is mandatory. The AI Provider Hub, stable provider
  adapters, Model Router, and Model Evaluation are strategic architecture.
- The Nina Trust Layer governs every current and future layer.
- Voice is core experience infrastructure; current input experiments do not
  constitute the complete Voice Layer.
- Physical machines, robots, and humanoids are future worker types. NinaOS may
  coordinate work and policy, but certified local controllers retain low-level
  motion and safety.
- A visible AI brand area may show only genuinely connected and permitted
  providers. It remains secondary to the Nina-centered experience.
- Future vision must never be documented as implemented, tested, deployed, or
  production-verified functionality.

### Architecture horizons

**Current:** Platform Core V1, RolePack System V1, and Ready Worker Catalog V1
are completed. OpenAI integration, existing channels, Work Objects, and
approval/audit concepts are recorded at their evidenced scope rather than
promoted to complete future platform layers.

**Current and next:** Agent Assignment V1 is implemented. Knowledge Vault V1
is the immediate planned implementation layer; the agreed build order remains
intact.

**Strategic future:** AI Provider Hub, routing/evaluation, consolidated Trust
and Voice layers, connectors, human approval, devices/robots, fleet
orchestration, and Global Control Plane.

### Reason

The repository already contains valuable business, worker, channel, voice, and
durability foundations, but earlier documents blurred current implementation
with ambition and centered some flows on individual channels/providers. V6
establishes stable boundaries so new technology attaches to NinaOS instead of
redefining it.

---

## AL-009 — Platform Foundation V1 checkpoint
Status: HISTORICAL CHECKPOINT (before Agent Assignment V1)
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

### Next at this historical checkpoint: Agent Assignment V1

This checkpoint planned Agent Assignment to persist one customer workspace,
one exact Ready Worker version, one stable worker instance ID,
lifecycle/provisioning state, and customer language, timezone and permissions
in PostgreSQL. AL-012 records its later implementation.

### Foundation delivery order

This checkpoint refines but does not replace the Constitution's broader roadmap:

1. Platform Core V1 — completed
2. RolePack System V1 — completed
3. Ready Worker Catalog V1 — completed
4. Agent Assignment V1 — completed in AL-012
5. Knowledge Vault V1 — next
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
