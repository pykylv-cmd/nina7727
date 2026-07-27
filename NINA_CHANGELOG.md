# NINA_CHANGELOG.md

# NinaOS Changelog

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
