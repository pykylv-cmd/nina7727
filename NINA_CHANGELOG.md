# NINA_CHANGELOG.md

# NinaOS Changelog

## 2026-07-27 — Universal Work Objects V1

Implemented Universal Work Objects V1 by adopting the existing
`nina_work_objects` table as the single tenant-scoped work registry. Added
governed core type/status/priority vocabularies, ownership, optional active
same-tenant Agent Assignment links, hierarchy, scheduling, provenance,
bounded search, lifecycle timestamps, and audit events through managed EXPAND
migration `0004_universal_work_objects_v1`.

Web and Telegram task paths now create or project canonical work objects.
Legacy task-memory writes were disabled without deleting historical data.
Planner, client, task, and follow-up adapters use the same registry. This does
not claim autonomous execution, deployment, production verification, or a
complete Channel Layer. Channel Layer V1 becomes the next planned layer.

## 2026-07-27 — Knowledge Vault V1

Implemented one tenant-owned authorized Knowledge Vault under ONE NINA:

- versioned `KnowledgeItem` records with provenance and SHA-256 checksums;
- managed EXPAND migration `0003_knowledge_vault_v1`;
- controlled `draft`, `active`, terminal `archived` lifecycle;
- immutable history when active authoritative content changes;
- tenant-isolated CRUD, version-history, lifecycle, and keyword search APIs;
- bounded content, metadata, filters, pagination, and sensitive-field checks;
- Platform Core capability registration and regression tests.

V1 stores authorized structured text and document/URL reference records. It
does not upload binaries, parse PDF/DOCX, fetch URLs, create embeddings,
provide semantic search/RAG, create worker/channel memory, or autonomously
execute stored instructions. Universal Work Objects V1 becomes the next
planned layer.

---

## 2026-07-27 — Agent Assignment V1

Implemented tenant-scoped Agent Assignment management under ONE NINA:

- exact Ready Worker definition/version and primary RolePack references;
- managed EXPAND migration `0002_agent_assignment_v1`;
- validated assignment configuration and least-privilege permission narrowing;
- controlled `draft`, `active`, `suspended`, `archived` lifecycle;
- tenant-isolated create/get/list/update/transition service operations;
- tenant-derived Web JSON API endpoints;
- Platform Core capability registration and full regression tests.

This does not implement autonomous worker execution, separate memory/work
truth, provider routing, channel provisioning, Knowledge Vault, billing, or UI
rebuild. Knowledge Vault V1 becomes the next planned layer.

---

## 2026-07-27 — Constitution V6

Adopted `NinaOS_Constitution_V6.md` as the authoritative governing document.
Aligned the architecture ledger, structured project state, control center,
blueprint, roadmap, and new-chat handoff.

V6 defines NinaOS as a universal, provider-neutral AI workforce operating
system; makes the Nina Trust Layer mandatory; establishes AI Provider Hub,
Voice, connectors, and robot/fleet layers as strategic architecture; preserves
Agent Assignment V1 as next; and records current WhatsApp, OpenAI, voice, and
robot truth without presenting future vision as implemented.

Scope: documentation and project-state JSON only. No runtime, migration,
environment, Railway, product behavior, push, or deployment change.

---

## 2026-07-27 — Platform Foundation V1 architecture checkpoint

Recorded Platform Core V1, RolePack System V1, Ready Worker Catalog V1,
verified staging/readiness configuration, and Agent Assignment V1 as the next
layer. Added `NINA_NEW_CHAT_START_PACK.md`.

Scope: documentation only. No runtime, database, migration, Railway or customer
behavior changed.

---

## 2026-07-01 — Documentation Control System

### Added
- `NINA_SYSTEM.md`
- `NINA_MANIFEST.json`
- `NINA_REGISTRY.md`
- `NINA_CHANGELOG.md`
- `TEST_PROTOCOL.md`

### Reason
Projekts izauga no viena faila uz NinaOS modulāru arhitektūru.
Lai jaunā čatā nezaudētu kontekstu, arhitektūra jāglabā GitHub dokumentos, nevis sarunā.

### Current issue
`core 2.6.1` joprojām aiziet uz veco V115.2 sarunas ceļu, jo aktuālajā `app.py` Employee Brain vārtos bija tikai līdz `core 2.5`.

### Next
Salabot `app.py` router gate un tikai tad turpināt Core 2.6.2.

---

## Core 2.6.1 — Initiative Detector

Status: In progress.

Goal: Nina sāk pamanīt situācijas, kur lietotājam vajadzīgs nākamais solis.

Rule: Initiative Engine neveido gala tekstu. Tas veido strukturētu iniciatīvas objektu, ko vēlāk apstrādā Reply Builder.

---

## Core 2.5.1 — Reply Builder

Status: Done / active.

Goal: Visas gala atbildes ilgtermiņā iet caur vienu centrālu Reply Builder.
