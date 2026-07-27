# NINA_CONTROL_CENTER.md

## Platform Foundation V1 — current checkpoint

Implementation commit:
`fe5dba4839e59daa4b0ad0b7d3f3fb812b2f3e70`

Completed: Platform Core V1 → RolePack System V1 → Ready Worker Catalog V1.

Next: **Agent Assignment V1**. It will persist a stable customer worker
instance linked to one workspace and one exact Ready Worker version. It will not
yet execute autonomous work or provision external channels.

Staging: project `confident-expression`, environment `staging`, Web/Core service
`secure-rebirth`, pre-deploy `python manage_migrations.py expand`, start
`python web_app.py`, `/live` alive and `/ready` ready.

Baseline: Python 213/213 and Node 38/38 passed.

Do not rebuild completed foundation layers. Preserve PostgreSQL fail-closed
persistence, managed migrations, readiness, rolling compatibility, restart
persistence and separate Telegram/Web runtimes.

---

## NinaOS patiesība

Nina nav Telegram bots.
NinaOS ir AI darbinieku operētājsistēma / platforma.
Telegram ir tikai testa kanāls jeb adapters.

Mērķis: izveidot pasaulē labāko AI darbinieku platformu, kur AI darbinieki sniedz pakalpojumus, pārdod idejas, palīdz cilvēkiem un uzņēmumiem, un vēlāk darbojas Nina Exchange platformā.

## Produkta virziens

- Nina AI — pirmais AI darbinieks
- Nina Core — domāšanas kodols
- Nina Memory — kopīgā atmiņa
- Nina Identity — pastāvīga identitāte
- Nina Vision — attēlu/dokumentu saprašana
- Nina Voice — balss slānis
- Nina Business — biznesa AI darbinieki
- Nina Exchange — AI darbinieku, ideju un pakalpojumu tirgus
- Nina Pay — maksājumi un komisijas
- Nina API — ārējās integrācijas

## Pareizā arhitektūra

NinaOS → Nina Core → Employee Brain → Think Engine → Learning Engine → Quality Engine → Reply Builder → Channel Adapter → Telegram

Telegram nav arhitektūras sākums. Telegram ir tikai viens no kanāliem.

## Failu lomas

### app.py
Routeris / adapteris. Saņem Telegram ziņu un nodod tālāk. Nedrīkst kļūt par biznesa loģikas miskasti.

### employee_brain.py
AI darbinieka darba vadības slānis. Šeit Core statusi un darba ceļi tiek pārvērsti atbildēs.

### think_engine.py
Klasificē nodomu. Neveido gala tekstu.

### learning_engine.py
Mācīšanās un kļūdu atziņu slānis.

### quality_engine.py
Kvalitātes pārbaude.

### reply_builder.py
Centrālais gala atbildes veidošanas princips.

### initiative_engine.py
Core 2.6 iniciatīvas loģika. Nedrīkst apiet Reply Builder.

### memory.py / memory_service.py
Atmiņas saglabāšana un lasīšana.

### user_profile_engine.py
Lietotāja profila fakti: vārds, profesija, intereses, projekti.

### conversation_engine.py
Dzīvās sarunas slānis. Nedrīkst apēst Core komandas.

## Core Evolution

- Core 2.0 — Employee Brain: DONE
- Core 2.1 — Identity + Employee State: DONE
- Core 2.2 — Responsibility Brain: DONE
- Core 2.3 — Think Engine: DONE
- Core 2.4 — Learning Engine: DONE
- Core 2.5 — Quality Engine: DONE
- Core 2.5.1 — Reply Builder: ACTIVE
- Core 2.6 — Initiative Engine: IN PROGRESS
- Core 2.6.1 — Initiative Detector: CURRENT
- Core 2.6.2 — Initiative Generator: NEXT

## Atrastā kļūda

Simptoms:
`core 2.6.1` Telegramā aizgāja uz parastu OpenAI sarunu.

Cēlonis:
`app.py` Employee Brain vārti laida tikai līdz `core 2.5`.
Tāpēc `core 2.6.1` netika nodots uz `employee_brain.py`.

Pareizais labojums:
`app.py` Employee Brain vārtos jābūt:
- core 2.5.1
- core 2.6
- core 2.6.1
- reply builder status
- initiative engine
- initiative detector status

## Darba noteikumi

Lietotājs nekad nelabo atsevišķas rindas.
ChatGPT vienmēr sagatavo pilnus failus.

Pirms koda:
1. Nosaki moduli.
2. Nosaki izsaukumu ķēdi.
3. Nelabo uz minējumiem.
4. Nelabo Telegram slāni, ja problēma ir NinaOS Core.

Pēc katra Core:
1. Atjaunina kodu.
2. Atjaunina šo failu.
3. Tikai tad iet tālāk.

## Jaunā čata starts

NINA RESET.
Strādājam ar NinaOS, nevis Telegram botu.
Izlasi NINA_CONTROL_CENTER.md.
Telegram ir tikai testa adapters.
Pašreizējais Core: 2.6.1 Initiative Detector.
Pirms koda rakstīšanas nosaki moduli un izsaukumu ķēdi.
