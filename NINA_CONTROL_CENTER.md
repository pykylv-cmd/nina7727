# NinaOS Control Center

## Governing direction

`NinaOS_Constitution_V6.md` is authoritative.

Official motto:

> One Nina. Infinite Workforce.
>
> One conversation. Unlimited intelligence. Unlimited workers.
>
> One trusted operating system.

ONE NINA is the highest architecture principle. Nina is the face and one
coherent customer relationship; the workforce behind Nina may expand through
governed Ready Worker definitions and Agent Assignments. “Infinite” means
extensible worker capacity, never unlimited permission, cost, or autonomy.

NinaOS is a universal AI workforce operating system. The customer speaks with
Nina and defines the result; Nina coordinates permitted providers, ready
workers, people, systems, channels, devices, and future robots. Nina is not one
model. Provider neutrality and stable provider adapters are mandatory.

The Nina Trust Layer applies across identity, permissions, providers, tools,
actions, approvals, privacy, cost, audit, and future physical systems. Voice is
strategic product infrastructure. Robot coordination is strategic future
architecture; no current physical-control implementation is claimed and local
controllers retain low-level safety.

## Current, next, and future

- **Implemented:** Platform Core V1, RolePack System V1, Ready Worker
  Catalog V1, Agent Assignment V1, Knowledge Vault V1, and Universal Work
  Objects V1.
- **Planned next:** Channel Layer V1.
- **Implemented in limited scope:** existing WhatsApp paths; these precede but
  do not complete the platform-wide future Channel Layer.
- **Experimental:** current browser/OpenAI voice input capabilities.
- **Long-Term Vision:** AI Provider Hub, Model Router/Evaluation, complete
  Voice and Trust layers, connectors, devices/robots, fleet orchestration, and
  Global Control Plane.

OpenAI is the only evidenced AI runtime provider in the repository. Other
provider brands are strategic until real adapters, configuration, and tests
exist.

## Runtime and persistence guardrails

- PostgreSQL is authoritative in hosted runtimes; hosted startup fails closed.
- Migrations are managed and EXPAND-first; destructive change requires an
  explicit later CONTRACT phase.
- Preserve restart persistence, rolling compatibility, request gating,
  separated liveness/readiness, and tenant isolation.
- `app.py` is Telegram/Core and `web_app.py` is Web; do not couple startup.
- Railway staging is `confident-expression`; Web/Core is `secure-rebirth` and
  the Node Company WhatsApp bridge is `happy-education`.
- Tests do not establish deployment or production success.

## Do not violate

- Do not turn NinaOS into a chatbot, bot builder, provider console, or
  channel-specific product.
- Do not fragment ONE NINA into provider-, worker-, or channel-specific
  customer identities or competing sources of truth.
- Do not interpret Infinite Workforce as unlimited authority, spending,
  autonomous replication, or a bypass around Ready Worker and Agent Assignment.
- Do not equate Nina with OpenAI or any other provider.
- Do not collapse definitions, customer assignments, permissions, credentials,
  channels, work, devices, billing, or audit into one object.
- Do not claim vision, implementation, tests, deployment, or production
  verification interchangeably.
- Do not grant capability as permission; require least privilege and approval.
- Do not bypass local robot safety or claim physical control that does not
  exist.
- Do not rebuild completed foundation layers.

## Agent Assignment V1 boundary

Agent Assignment V1 now binds one authenticated tenant to one exact Ready
Worker version and stable assignment ID. It provides validated configuration,
least-privilege permission narrowing, and `draft`, `active`, `suspended`, and
terminal `archived` lifecycle management through shared persistence and
tenant-scoped APIs.

It does not execute autonomous work, provision channels, route providers,
create separate Nina identities, or own memory/work truth.

## Immediate build task

Implement **Channel Layer V1** next according to the canonical sequence,
preserving ONE NINA, tenant isolation, and the established Agent Assignment,
Knowledge Vault, and Universal Work Object boundaries.

## Universal Work Objects V1 boundary

Universal Work Objects V1 uses the existing `nina_work_objects` table as the
single tenant-scoped work truth. It provides closed core types, lifecycle,
priority, ownership, optional same-tenant active Agent Assignment references,
parent/child work, scheduling, source provenance, bounded search, and audit
events. Web, Telegram task, planner, client, task, and follow-up paths use or
project this registry; no new task-memory writes are made.

It does not provide autonomous execution, channel completion, provider
routing, or a second Nina. Legacy specialized Work Engine values remain
compatible in the same table, while the V1 service governs new core objects.

## Knowledge Vault V1 boundary

Knowledge Vault V1 provides tenant-owned `KnowledgeItem` CRUD, controlled
activation/archive lifecycle, immutable active-content version history,
checksums, provenance, bounded metadata, and tenant-scoped keyword search.

It is not conversation memory, a customer profile, worker/channel memory,
binary file storage, PDF/DOCX ingestion, semantic retrieval, RAG, a prompt
library, or a secrets manager. Stored client instructions remain inert data
until a separately governed future workflow uses them.
