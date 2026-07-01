# NINA_BUG_TRACKER.md

# NinaOS Bug Tracker
Version: 1.0
Status: Active

## Darba princips

NinaOS netiek labota uz minējumiem.

Katram defektam jābūt:
- ID;
- simptomam;
- atbildīgajam modulim;
- prioritātei;
- reproducēšanas testam;
- sagaidāmajam rezultātam;
- statusam.

Ja defekts ir kritisks, neturpinām nākamo Core, kamēr tas nav salabots.

## BUG-001 — Core 2.6.1 aiziet uz veco V115.2 sarunas ceļu

**Prioritāte:** 🔴 P0  
**Statuss:** FIX PREPARED  
**Modulis:** `app.py` router

### Simptoms

`core 2.6.1` aiziet uz parastu OpenAI sarunu un rāda `V115.2 + Core 2.5.1`.

### Cēlonis

`app.py` Employee Brain vārti laida tikai līdz `core 2.5`.
Tāpēc `core 2.6.1` netika nodots uz `employee_brain.py`.

### Labojums

`app.py` Employee Brain vārtos pievienot:
- `core 2.5.1`
- `core 2.6`
- `core 2.6.1`
- `reply builder`
- `reply builder status`
- `initiative engine`
- `initiative status`
- `initiative detector`
- `initiative detector status`

### Tests

`core 2.6.1`

### Sagaidāmais rezultāts

Atbilde par Core 2.6.1 / Initiative Detector, nevis OpenAI vispārīga saruna.

## BUG-002 — Memory/Profile regresija

**Prioritāte:** 🔴 P0  
**Statuss:** OPEN  
**Modulis:** `user_profile_engine.py`, `memory.py`, `memory_service.py`, `app.py`

### Simptoms

Nina sākumā atceras lietotāja faktus, bet pēc izmaiņām daļa faktu pazūd.

### Iespējamais cēlonis

Vecā sistēma lieto `hobbies/facts`, bet jaunā `user_profile_engine.py` lieto `interests/projects/clients`.

### Tests

`ko tu par mani zini`

### Sagaidāmais rezultāts

Nina konsekventi parāda saglabātos profila faktus un nepazaudē tos pēc Core izmaiņām.

## BUG-003 — Premium atbilde nav stabila

**Prioritāte:** 🟠 P1  
**Statuss:** OPEN  
**Modulis:** `premium.py`, `app.py`, datubāze

### Tests

`premium`

### Sagaidāmais rezultāts

Nina skaidri parāda Premium statusu.

## BUG-004 — Dokumentācija un faktiskā routing ķēde nav sinhrona

**Prioritāte:** 🟠 P1  
**Statuss:** OPEN  
**Modulis:** docs + `app.py`

### Tests

Salīdzināt:
- `NINA_MANIFEST.json`
- `NINA_REGISTRY.md`
- `app.py` Employee Brain vārtus

## BUG-005 — Vecie V114/V115 slāņi var apēst Core komandas

**Prioritāte:** 🟡 P2  
**Statuss:** OPEN  
**Modulis:** `conversation_engine.py`, `v1151_master_core`, `app.py`

### Risinājums

Core komandām jābūt centralizētai pārbaudei pirms vecā natural conversation slāņa.
