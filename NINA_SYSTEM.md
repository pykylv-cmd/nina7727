# NINA_SYSTEM.md

# NinaOS System Constitution

## 1. Projekta būtība

Nina nav Telegram bots.

NinaOS ir AI darbinieku operētājsistēma / platforma.

Telegram ir tikai testa kanāls jeb adapters.

Nina AI ir pirmais AI darbinieks, kas darbojas uz NinaOS kodola.

Ilgtermiņa mērķis: izveidot pasaulē labāko AI darbinieku platformu, kur AI darbinieki sniedz pakalpojumus, pārdod idejas, palīdz cilvēkiem un uzņēmumiem, un vēlāk darbojas Nina Exchange platformā.

## 2. Galvenie produkti

- NinaOS — platforma
- Nina AI — pirmais AI darbinieks
- Nina Core — domāšanas kodols
- Nina Memory — kopīgā atmiņa
- Nina Identity — pastāvīga identitāte
- Nina Vision — attēlu un dokumentu saprašana
- Nina Business — biznesa AI darbinieki
- Nina Exchange — AI darbinieku, ideju un pakalpojumu tirgus
- Nina Pay — maksājumi un komisijas
- Nina API — ārējās integrācijas

## 3. Pareizā arhitektūras domāšana

Nepareizi:

Telegram → app.py → kaut kāda atbilde

Pareizi:

NinaOS → Nina Core → Employee Brain → Think Engine → Learning Engine → Quality Engine → Reply Builder → Channel Adapter → Telegram

Telegram nekad nav arhitektūras sākums. Telegram ir tikai viens no kanāliem.

## 4. Stingrie noteikumi

- `app.py` ir routeris, nevis biznesa loģikas vieta.
- Jauna biznesa loģika dzīvo atsevišķos moduļos.
- Think Engine nekad neveido gala atbildi.
- Initiative Engine neveido gala tekstu, tikai strukturētu iniciatīvas objektu.
- Reply Builder ir vienīgais ilgtermiņa gala atbildes ģenerators.
- Telegram ir adapters, nevis produkta centrs.
- Lietotājs nekad nelabo atsevišķas rindas.
- ChatGPT vienmēr sagatavo pilnus failus.
- Pirms koda rakstīšanas jānosaka atbildīgais modulis un izsaukumu ķēde.

## 5. Jaunā čata starts

NINA RESET.

Strādājam ar NinaOS, nevis Telegram botu.
Izlasi:
1. `NINA_SYSTEM.md`
2. `NINA_MANIFEST.json`
3. `NINA_REGISTRY.md`
4. `NINA_CHANGELOG.md`
5. `TEST_PROTOCOL.md`

Pašreizējais Core: Core 2.6.1 — Initiative Detector.
