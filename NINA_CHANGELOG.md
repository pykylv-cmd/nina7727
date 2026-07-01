# NINA_CHANGELOG.md

# NinaOS Changelog

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
