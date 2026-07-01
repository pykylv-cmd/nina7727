# TEST_PROTOCOL.md

# NinaOS Test Protocol

## Kad lietot

Pēc katras failu ielādes GitHub un Railway redeploy.

## Pamatkontrole

Testē šādā secībā:

1. `core 2.5`
2. `reply builder status`
3. `core 2.6.1`
4. `initiative detector status`
5. `ko tu par mani zini`
6. `premium`

## Ja krīt `core 2.6.1`

Pirmais pārbaudāmais:
- `app.py` Employee Brain gate.

Tam jāietver:
- `core 2.5.1`
- `core 2.6`
- `core 2.6.1`
- `initiative engine`
- `initiative detector status`

## Ja krīt profils

Pārbaudīt:
- `user_profile_engine.py`
- `memory.py`
- `memory_service.py`
- vecā `hobbies/facts` un jaunā `interests/projects` saskaņošana.

## Ja krīt premium

Pārbaudīt:
- `premium.py`
- `app.py` premium router
- datubāzes premium lauki.

## Noteikums

Ja viens tests krīt, neturpināt nākamo Core.
Vispirms salabot regresiju.
