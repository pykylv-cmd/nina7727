# NINA_REGISTRY.md

# NinaOS Module Registry

| Modulis | Loma | Statuss | Versija / Core | Piezīmes |
|---|---|---:|---|---|
| `app.py` | Router / channel adapter | ⚠️ jālabo | V115.2 | Jāielaiž `core 2.6.1` uz Employee Brain |
| `employee_brain.py` | AI darbinieka darba vadība | ✅ | Core 2.6.1 | Izvēlas atbildes ceļu pēc Think Engine |
| `think_engine.py` | Nodoma klasifikācija | ✅ | Think Engine 2.6.1 | Neveido gala tekstu |
| `learning_engine.py` | Mācīšanās slānis | ✅ | Core 2.4 | Mācīšanās un kļūdu atziņas |
| `quality_engine.py` | Atbildes kvalitātes pārbaude | ✅ | Core 2.5 | Pārbauda pirms nosūtīšanas |
| `reply_builder.py` | Gala atbildes veidošana | ✅ | Core 2.5.1 | Vienīgais ilgtermiņa final reply slānis |
| `initiative_engine.py` | Iniciatīvas loģika | 🚧 | Core 2.6 | Strukturē iniciatīvas, neveido gala tekstu |
| `memory.py` | Atmiņas pamata loģika | ✅/jāpārbauda | V114/V115 | Jāpārbauda, vai nepārraksta profilu |
| `memory_service.py` | Pastāvīgā atmiņa | ✅/jāpārbauda | V115 | Jāsavieno ar kopīgo Memory |
| `user_profile_engine.py` | Lietotāja profils | ⚠️ jāsaskaņo | V22.0 | `interests` pret veco `hobbies/facts` |
| `conversation_engine.py` | Dzīvā saruna | ⚠️ jāpārbauda | V114/V115 | Nedrīkst apēst Core komandas |
| `assistant.py` | Vecāks/paralēls asistenta slānis | ⚠️ jāpārbauda | Legacy | Jāsaprot, vai vēl tiek izmantots |
| `brain.py` | Vecāks Brain modulis | ⚠️ jāpārbauda | Legacy | Jāsaprot attiecība ar Employee Brain |
| `vision_engine.py` | Vision / bildes | ✅ | V114+ | Attēlu un dokumentu saprašana |
| `premium.py` | Premium/abonements | ⚠️ jāpārbauda | V115 | Telegram vēsturē reizēm klusēja |

## Galvenā kontroles doma

Ja kaut kas salūzt, vispirms jāatrod atbildīgais modulis, nevis jālabo `app.py` uz minējumiem.
