
# NINA_RELEASE_POLICY.md

# NinaOS Release Policy
Version: 1.0

## Galvenais princips

Platforma drīkst augt tikai tad, ja esošās spējas netiek sabojātas.

Katrs NinaOS atjauninājums automātiski uzlabo visus AI darbiniekus,
nezaudējot viņu atmiņu, prasmes un funkcijas.

---

# Golden Rule

Nekad neupdeitot Ninu atsevišķi.

Updeito NinaOS Core.

Visi AI darbinieki izmanto vienu Core.

---

# Pirms katra Release

## 1. Snapshot

Saglabā:
- Memory
- User profile
- Identity
- Premium
- Core status
- Konfigurāciju

## 2. Upgrade

Veic Core izmaiņas.

## 3. Migration

Ja mainās datu struktūras, tās migrē.
Nekas nedrīkst pazust.

## 4. Regression Tests

Obligāti:

✓ core 2.5
✓ core 2.6.1
✓ initiative detector status
✓ ko tu par mani zini
✓ premium
✓ lietotāja vārds
✓ projekti
✓ intereses
✓ atmiņa

Ja kaut viens tests krīt,
release netiek publicēts.

---

# Backward Compatibility

Ja vakar Nina prata:
- atcerēties klienta vārdu;
- atcerēties projektu;
- atbildēt uz premium;
- izmantot Core komandas,

tad pēc jaunās versijas tas joprojām jāprot.

Ja nē, tas ir regress.

---

# Divas paralēlas līnijas

A. Produkts
Mērķis: Nina pelna naudu.

Prioritātes:
- e-pasti
- klientu atbildes
- dokumenti
- tāmes
- CRM
- atmiņa

B. Platforma
Mērķis: NinaOS kļūst spēcīgāks.

Prioritātes:
- Core
- Memory
- Exchange
- API
- Enterprise
- AI Factory

Abi virzieni attīstās vienlaikus.

---

# Release Gate

Neviena jaunā Core versija netiek apstiprināta, kamēr:
1. dokumentācija ir atjaunināta;
2. testi ir zaļi;
3. regress nav atrasts.

Šī politika ir obligāta visiem NinaOS moduļiem.
