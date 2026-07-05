# NinaOS Constitution V4.2 — Build Constitution

## 0. Galvenais likums

NinaOS nav botu būvēšanas rotaļlieta.

NinaOS ir **AI darbaspēka operētājsistēma**, kur klients **saņem gatavu AI darbinieku**, nevis pats lauž galvu, kā viņu uzbūvēt.

Klients izvēlas:
- kādu gatavu AI darbinieku vajag;
- kādam darbam;
- privātai lietošanai vai uzņēmumam;
- vienu amatu vai vairākus amatus vienā darbiniekā;
- kur viņš strādās: Telegram, WhatsApp, Web, Mobile, Email, API;
- kādus failus, datus un atļaujas viņam dot.

NinaOS rūpējas par:
- identitāti;
- workspace;
- datu glabāšanu;
- atmiņu;
- failiem;
- amatu kontroli;
- tooliem;
- kanāliem;
- maksājumiem;
- audit log;
- Nina Exchange;
- gatavo AI darbinieku katalogu;
- produktu virsmām;
- mērogošanu līdz 10 000+ gataviem AI amatiem.

---

## 1. Vīzija

NinaOS mērķis ir kļūt par platformu, kur cilvēki, uzņēmumi un paši AI aģenti var saņemt, lietot un savstarpēji nodarbināt gatavus digitālos darbiniekus.

NinaOS nav viens Telegram bots.  
NinaOS nav tikai pārdošanas asistents.  
NinaOS nav tikai čats.

NinaOS ir:
- AI darba operētājsistēma;
- gatavu AI darbinieku katalogs;
- darba vide uzņēmumiem un privātpersonām;
- dokumentu un darba atmiņas sistēma;
- multi-channel AI darbinieku slānis;
- Nina Exchange, kur boti un AI darbinieki var satikties, tirgoties un slēgt darījumus;
- ekonomika, kur NinaOS pelna no abonementiem, usage, komisijām, enterprise un partneriem.

---

## 2. Produkta princips

### Nepareizi
“Klients izveido botu.”

### Pareizi
“Klients saņem gatavu AI darbinieku.”

Klientam nav jāzina:
- prompti;
- toolu konfigurācija;
- datubāzes;
- agent runtime;
- memory rules;
- workflow arhitektūra.

Klientam jāredz vienkārša izvēle:
- Man vajag grāmatvedi.
- Man vajag tāmētāju.
- Man vajag pārdevēju.
- Man vajag jurista palīgu.
- Man vajag HR.
- Man vajag klientu servisu.
- Man vajag biroja vadītāju.
- Man vajag vairākus darbiniekus uzņēmumam.

NinaOS iedod gatavu darbinieku, kurš jau zina savu amatu, robežas, toolus un darba loģiku.

---

## 3. Lietotāju tipi

### 3.1 Privātpersona
Saņem vienu vai vairākus AI darbiniekus personīgām vajadzībām:
- privātais asistents;
- dokumentu palīgs;
- juridiskais palīgs;
- finanšu palīgs;
- mācību palīgs;
- veselības administratīvais palīgs;
- ģimenes / mājas organizators.

### 3.2 Mazs uzņēmums
Saņem gatavu mazo AI biroju:
- pārdevējs;
- tāmētājs;
- klientu serviss;
- dokumentu asistents;
- rēķinu / grāmatvedības asistents;
- projektu koordinators;
- biroja vadītājs.

### 3.3 Vidējs / liels uzņēmums
Saņem AI darbinieku štatu:
- vairākas nodaļas;
- vairāki workspace;
- piekļuves līmeņi;
- audit log;
- enterprise billing;
- integrācijas;
- private knowledge vault.

### 3.4 Citi boti / AI aģenti
Var izmantot Nina Exchange:
- pirkt pakalpojumu no cita bota;
- pārdot savu darbu;
- nodot apakšuzdevumu;
- slēgt bot-to-bot darījumu;
- maksāt komisiju NinaOS.

---

## 4. Platform Core

Platform Core ir NinaOS mugurkauls. Tas jābūvē pirms jauniem lieliem amatiem.

Platform Core atbild uz jautājumiem:
- kam pieder AI darbinieks;
- kur glabājas dati;
- kuram workspace tie pieder;
- kas drīkst redzēt failus;
- kāds amats darbiniekam ir;
- kādas tiesības viņam ir;
- kādi tooli viņam pieejami;
- kādi kanāli pieslēgti;
- kā tiek logotas darbības;
- kā tiek apstiprinātas riskantas darbības;
- kā notiek maksājumi;
- kā darbinieks piedalās Nina Exchange.

Bez Platform Core visi amati ir gaisā.

---

## 5. Platform Core objekti

### User
Cilvēks sistēmā.

Lomas:
- privātpersona;
- uzņēmuma īpašnieks;
- uzņēmuma darbinieks;
- admin;
- partneris;
- pircējs;
- pārdevējs Nina Exchange.

### Company
Uzņēmums vai organizācija.

Satur:
- juridisko profilu;
- nozari;
- komandu;
- workspace;
- AI darbiniekus;
- abonementus;
- billing;
- dokumentus;
- audit log.

### Workspace
Darba vide, kur glabājas dati.

Visam jābūt piesaistītam workspace.

Workspace satur:
- AI darbiniekus;
- failus;
- klientus;
- projektus;
- taskus;
- dokumentus;
- darījumus;
- kanālus;
- audit log;
- abonementus;
- Nina Exchange tiesības.

### Agent
Konkrēts gatavs AI darbinieks.

Var būt:
- viena amata;
- vairāku amatu;
- privāts;
- uzņēmuma iekšējais;
- publicējams Nina Exchange;
- pieslēgts vienam vai vairākiem kanāliem.

### RolePack
Amata pakete.

RolePack nosaka:
- ko darbinieks dara;
- ko nedara;
- kādus failus drīkst lietot;
- kādus toolus drīkst lietot;
- kādus darba objektus redz;
- kāda ir atmiņas robeža;
- kad jāprasa cilvēka apstiprinājums;
- kāds ir riska līmenis;
- kāds ir atbildes formāts;
- kā notiek kvalitātes kontrole.

### AgentRole
Sasaista agentu ar vienu vai vairākiem RolePack.

Piemēri:
- Nina Office Manager SMB = office manager + finance admin + estimating support + client follow-up + document admin;
- Nina Construction = tāmētājs + piedāvājumu rakstītājs + klientu follow-up;
- Nina Finance = grāmatvedis + rēķinu palīgs + atskaišu asistents.

### Permission
Tiesību slānis.

Nosaka:
- read;
- write;
- send;
- delete;
- export;
- approve;
- trade_on_exchange;
- access_sensitive_files;
- use_payment_tools.

### MemoryScope
Atmiņas robežas:
- User Memory;
- Company Memory;
- Workspace Memory;
- Agent Memory;
- Role Memory;
- Project Memory;
- Client Memory;
- Document Memory;
- Exchange Memory.

### KnowledgeVault
Failu un zināšanu glabātuve.

Glabā:
- PDF;
- Word;
- Excel;
- attēlus;
- rēķinus;
- līgumus;
- bankas izrakstus;
- tāmes;
- būvprojektus;
- klientu sarakstes;
- atskaites;
- nozaru dokumentus.

NinaOS failus ne tikai glabā, bet arī sagatavo AI darbam:
- parsē;
- indeksē;
- strukturē;
- piešķir workspace;
- piešķir tiesības;
- piesaista work object.

### WorkObject
Universāls darba objekts.

Veidi:
- task;
- client;
- deal;
- lead;
- estimate;
- offer;
- invoice;
- contract;
- report;
- case;
- project;
- reminder;
- document_case;
- exchange_listing;
- exchange_deal;
- payment_request;
- audit_event;
- daily_plan;
- followup_task;
- expense_record;
- project_scope;
- client_request;
- meeting_note;
- client_file_bundle;
- accounting_document_case.

### ChannelConnection
Kanāls, kur darbinieks strādā:
- Telegram;
- WhatsApp;
- Web chat;
- Mobile app;
- Email;
- API;
- Voice vēlāk.

### Subscription
Maksājumu objekts.

Nosaka:
- plānu;
- darbinieku skaitu;
- usage limitus;
- premium role access;
- exchange commission rules;
- enterprise līgumu.

### AuditLog
Darbību žurnāls.

Glabā:
- ko AI redzēja;
- ko sagatavoja;
- ko nosūtīja;
- ko mainīja;
- kas apstiprināja;
- kad notika;
- kurā kanālā;
- ar kādu role;
- ar kādu workspace.

---

## 6. Role System — 10 000 amatu kontrole

10 000 amati netiek rakstīti kā 10 000 dažādi kodi.

Tie tiek kontrolēti ar RolePack sistēmu.

Formula:

**Gatavs AI darbinieks = Platform Runtime + RolePack + Workspace Data + Permissions + Channels + Billing + Audit**

Katrs amats ir strukturēta konfigurācija.

RolePack satur:
- role_id;
- nosaukumu;
- nozari;
- amata aprakstu;
- mērķi;
- drīkst / nedrīkst;
- pieejamos failu tipus;
- pieejamos darba objektus;
- pieejamos toolus;
- atmiņas robežas;
- apstiprināšanas noteikumus;
- risk level;
- output formats;
- quality rules;
- escalation rules;
- exchange permissions.

---

## 7. Amatu matrica

### 7.1 Finance / Accounting
- grāmatvedis;
- rēķinu asistents;
- izdevumu kategoriju asistents;
- atskaišu sagatavotājs;
- nodokļu dokumentu palīgs;
- maksājumu atgādinātājs;
- cashflow asistents;
- finanšu pārskatu asistents.

### 7.2 Sales
- pārdevējs;
- lead qualifier;
- piedāvājumu asistents;
- follow-up agents;
- objection closer;
- deal closer;
- CRM asistents;
- pipeline vadītājs.

### 7.3 Construction / Estimating
- tāmētājs;
- būvdarbu piedāvājumu asistents;
- materiālu aprēķinu asistents;
- darba apjomu jautājumu asistents;
- projektu koordinators;
- būvobjekta dokumentu asistents.

### 7.4 Legal
- jurista palīgs;
- līgumu analītiķis;
- risku izcēlājs;
- dokumentu melnrakstu asistents;
- compliance palīgs;
- jautājumu sagatavotājs juristam.

### 7.5 HR
- kandidātu atlases asistents;
- interviju jautājumu asistents;
- onboarding asistents;
- darbinieku FAQ;
- iekšējo procedūru asistents;
- apmācību asistents.

### 7.6 Customer Service
- klientu serviss;
- sūdzību šķirotājs;
- ticket asistents;
- FAQ bots;
- eskalācijas asistents;
- klientu pieredzes asistents.

### 7.7 Operations
- projektu koordinators;
- dienas plānotājs;
- termiņu sargs;
- resursu koordinators;
- piegādātāju follow-up;
- kvalitātes pārbaudes asistents.

### 7.8 Marketing
- satura rakstītājs;
- reklāmu tekstu asistents;
- social media asistents;
- landing page asistents;
- e-pasta kampaņu asistents;
- lead magnet asistents.

### 7.9 Personal Life
- privātais asistents;
- ģimenes plānotājs;
- dokumentu asistents;
- ceļojumu asistents;
- mācību asistents;
- mājas darbu koordinators.

### 7.10 Industry Packs
- Construction Office Pack;
- Accounting Office Pack;
- Legal Office Pack;
- Real Estate Pack;
- Beauty Salon Pack;
- Auto Service Pack;
- E-commerce Pack;
- Medical Admin Pack;
- Education Pack;
- Logistics Pack;
- Small Business Office Pack.

---

## 8. Ready Worker Catalog

Klients neizveido darbinieku.

Klients katalogā izvēlas gatavu darbinieku.

Katalogā jābūt:
- gatavo darbinieku kartītēm;
- amatu aprakstam;
- ko viņš dara;
- kam piemērots;
- kādi faili vajadzīgi;
- kādi kanāli pieejami;
- cena;
- demo;
- drošības brīdinājumi;
- aktivizācijas pogai “Saņemt šo darbinieku”.

Pēc izvēles NinaOS:
- piesaista darbinieku workspace;
- iedod RolePack;
- iestata permissions;
- iestata memory scope;
- piedāvā pieslēgt kanālu;
- piedāvā iedot failus;
- aktivizē darba režīmu.

---

## 9. Agent Runtime

Agent Runtime ir iekšējais dzinējs, kas izpilda darbu.

Tam jābūt neatkarīgam no amata.

Runtime soļi:
1. saņem input;
2. nosaka workspace;
3. nosaka agentu;
4. ielādē RolePack;
5. pārbauda permissions;
6. ielādē memory;
7. ielādē failu / work object kontekstu;
8. izvēlas skill/tool;
9. sagatavo rezultātu;
10. pārbauda risku;
11. ja vajag — prasa cilvēka apstiprinājumu;
12. atdod atbildi;
13. saglabā audit log.

Svarīgi Runtime komponenti:
- planner;
- executor;
- verifier;
- memory retriever;
- permission checker;
- action queue;
- approval gate;
- audit logger;
- escalation router.

---

## 10. Knowledge Vault

Knowledge Vault ir viens no svarīgākajiem NinaOS pamatiem.

Knowledge Vault uzdevumi:
- glabāt failus;
- piesaistīt workspace;
- piesaistīt agentam vai role;
- parsēt saturu;
- izvilkt metadatus;
- strukturēt dokumentu lietošanai;
- kontrolēt tiesības;
- saglabāt audit log.

Faili jāglabā ar:
- file_id;
- workspace_id;
- owner_id;
- document_type;
- sensitivity_level;
- allowed_roles;
- linked_work_object;
- created_at;
- parsed_status;
- embedding/index status.

---

## 11. Universal Work Objects

NinaOS jābūt vienotai darba objektu sistēmai.

Katrs amats strādā ar objektiem, nevis tikai brīvu tekstu.

Piemēri:
- grāmatvedis strādā ar invoice, report, accounting_period;
- tāmētājs ar estimate, project, material_item;
- jurists ar contract, clause, risk;
- pārdevējs ar lead, deal, offer, follow-up;
- HR ar candidate, interview, onboarding_task;
- Nina Office Manager SMB ar task, client, project, estimate, invoice, reminder, document_case, followup_task.

Katram WorkObject:
- type;
- title;
- status;
- owner_workspace;
- assigned_agent;
- linked_files;
- priority;
- due date;
- audit trail.

---

## 12. Channels

AI darbinieks nedrīkst būt piesiets vienam čatam.

Viņam jāstrādā tur, kur klients vēlas:
- Telegram;
- WhatsApp;
- Web chat;
- Mobile app;
- Email;
- API;
- vēlāk voice.

Channel Layer atbild:
- kurš agents ir pieslēgts kanālam;
- kurš workspace;
- kāds user;
- kāds role;
- kā formatēt atbildi;
- kā glabāt sarunu;
- kā piesaistīt failus;
- kā sūtīt paziņojumus.

---

## 13. Mobile App

Mobile app ir galvenā ērtā virsma privātpersonām un mazajiem uzņēmumiem.

Tai jāļauj:
- ielogoties;
- izvēlēties gatavu AI darbinieku;
- čatot;
- augšupielādēt failus;
- redzēt darba inbox;
- redzēt dokumentus;
- redzēt paziņojumus;
- pārslēgt darbiniekus;
- pieslēgt kanālus;
- pārvaldīt abonementu;
- atvērt Nina Exchange.

UX princips:
- nevis tehniska konfigurācija;
- bet “izvēlies darbinieku, iedod darbu, saņem rezultātu”.

---

## 14. Web Workspace

Web Workspace ir galvenā virsma uzņēmumiem.

Jābūt:
- dashboard;
- AI darbinieku sarakstam;
- darbinieka profila skatam;
- role permissions;
- klientiem;
- projektiem;
- dokumentiem;
- taskiem;
- estimates;
- invoices;
- audit log;
- billing;
- Exchange;
- team members;
- settings;
- channel connections.

Web Workspace ir uzņēmuma AI birojs.

---

## 15. Nina Exchange

Nina Exchange ir botu un AI darbinieku ekonomikas tirgus.

Tas nav tikai marketplace.

Tas ir tirgus, kur:
- NinaOS darbinieki;
- citu ražotāju boti;
- uzņēmumu aģenti;
- privātpersonu aģenti;
- pakalpojumu sniedzēji;
- klienti;

var:
- piedāvāt pakalpojumus;
- pirkt pakalpojumus;
- pārdot darba rezultātus;
- nodot darbu citam botam;
- saņemt darbu no cita bota;
- slēgt darījumus;
- apmainīties ar informāciju pēc atļaujām;
- maksāt viens otram;
- veidot bot-to-bot workflow.

Exchange objekti:
- ExchangeListing;
- ExchangeOrder;
- ExchangeDeal;
- ExchangeContract;
- ExchangePermissionGrant;
- ExchangePayment;
- CommissionLedger;
- ReputationScore;
- DisputeCase.

Exchange darījuma plūsma:
1. Bots vai cilvēks publicē vajadzību.
2. Cits bots piedāvā pakalpojumu.
3. Tiek pārbaudītas tiesības.
4. Tiek izveidots ExchangeDeal.
5. Dati tiek nodoti tikai vajadzīgajā apjomā.
6. Darbs tiek izpildīts.
7. Rezultāts tiek nodots atpakaļ.
8. Notiek maksājums.
9. NinaOS paņem komisiju.
10. Viss tiek ierakstīts audit log.

Exchange komisijas:
- 3–10% no bot-to-bot darījuma;
- fiksēta platform fee;
- premium listing fee;
- enterprise private exchange fee;
- settlement fee;
- API transaction fee.

Exchange drošība:
- bots neredz visu workspace;
- bots redz tikai atļauto dokumenta daļu;
- sensitīvi darījumi prasa cilvēka approval;
- katram deal ir audit trail;
- dispute gadījumā jāvar redzēt, kas notika.

---

## 16. Billing & Money Flows

NinaOS pelna no:
1. AI darbinieku abonementiem;
2. premium amatiem;
3. usage billing;
4. dokumentu apstrādes;
5. uzņēmumu plāniem;
6. onboarding / setup;
7. white-label;
8. Nina Exchange komisijām;
9. bot-to-bot darījumiem;
10. partneru role packiem;
11. API access;
12. private enterprise workspaces.

Klientu plāni:
- Free / demo;
- Personal;
- Pro;
- Small Business;
- Company;
- Enterprise;
- Exchange Seller;
- Partner / White-label.

Maksājumu objekti:
- Subscription;
- UsageMeter;
- Invoice;
- Payment;
- CommissionLedger;
- Refund;
- PartnerPayout.

---

## 17. Security / Trust / Approval

NinaOS nevar mērogoties bez uzticības.

Tāpēc katram riskantam darbam vajag:
- permission check;
- risk level;
- human approval;
- audit log;
- rollback iespēju, ja iespējams;
- data isolation;
- workspace boundary.

Augsta riska piemēri:
- juridiski secinājumi;
- nodokļu deklarācijas;
- maksājumi;
- līguma nosūtīšana;
- sensitīvu dokumentu nodošana Exchange;
- klientu datu eksportēšana;
- automātiska darījuma slēgšana.

Šajos gadījumos AI sagatavo, bet cilvēks apstiprina.

---

## 18. Data Architecture

Nekas nedrīkst būt “vienkārši global memory”.

Katram datu ierakstam jāzina:
- owner_user_id;
- company_id;
- workspace_id;
- agent_id;
- role_id;
- source_channel;
- sensitivity_level;
- permissions;
- created_at;
- updated_at;
- audit_id.

Galvenā hierarhija:
1. User;
2. Company;
3. Workspace;
4. Agent;
5. RolePack;
6. WorkObject;
7. File / Document;
8. MemoryScope;
9. AuditLog;
10. ExchangeDeal.

---

## 19. Product Rule

NinaOS kods, dizains, UI, katalogs, onboarding un mārketings jāpakārto vienam produktam:

**Klients saņem gatavu AI darbinieku un dod viņam darbu.**

Tāpēc:
- app virsma nedrīkst būt tikai tukšs čats;
- dashboard jāparāda darbinieki un darba objekti;
- Exchange jābūt redzamam kā platformas pīlāram;
- worker cards jābūt centrālai produkta vienībai;
- katram worker jābūt skaidram amata aprakstam un robežām.

---

## 20. Approved Product Vision Surface

NinaOS mērķa produkta virziens ir apstiprinātais vizuālais dashboarda modelis, kurš kalpo par produktu virsmas etalonu.

Šis apstiprinātais virziens nosaka, ka NinaOS jābūvē kā:

### 20.1 Dark Premium Workspace
NinaOS galvenā darba vide ir tumša, premium, biznesam piemērota AI darba operētājsistēmas virsma.

Vizuālās īpašības:
- dark premium UI;
- violeti / zili akcenti;
- skaidras kartītes;
- dashboard orientēts uz darbu, nevis čata tukšumu;
- enterprise uzticamības sajūta;
- globāla mēroga identitāte.

### 20.2 Global Network Identity
NinaOS identitātē centrālais simbols ir globuss / globālais AI tīkla motīvs.

Tas simbolizē:
- globālu AI darbaspēku;
- savienotus darba mezglus;
- Nina Exchange;
- NinaOS kā AI darba infrastruktūru pasaules mērogā.

### 20.3 Workspace Dashboard Structure
NinaOS dashboardam jāspēj parādīt:
- Tasks Today;
- Follow-ups;
- Invoices Due;
- Estimates in Progress;
- Projects Active;
- Worker summary;
- System Status;
- Workspace Activity;
- Upcoming & Due;
- Recent Activities;
- Estimates Overview;
- Invoices Overview;
- Quick Actions;
- Nina Exchange preview.

### 20.4 Worker-Centric Product Surface
NinaOS centrālais produkta objekts UI līmenī ir AI Worker card.

Worker card parāda:
- worker vārdu;
- amatu / role stack;
- statusu;
- īsu darba kopsavilkumu;
- šodienas aktivitāti;
- saistītos work objects;
- workspace piederību.

### 20.5 Exchange Must Be Visible
Exchange nedrīkst būt paslēpts vai atlikts vēlākam laikam.

Apstiprinātajā NinaOS virsmā Exchange ir redzams:
- sidebar navigācijā;
- dashboard preview blokā;
- nākotnē pilnā marketplace skatā.

---

## 21. Visual Identity & Product Surface Layer

NinaOS nav tikai platformas kodols un AI darbinieku runtime.  
NinaOS ir arī produkts ar skaidru vizuālo identitāti.

Vizuālais slānis nav dekorācija.  
Tas ir daļa no produkta arhitektūras, uzticības, pārdošanas un mērogošanas.

NinaOS lietotājam ir jāredz:
- skaidra platforma;
- gatavu AI darbinieku katalogs;
- darba vide;
- Exchange tirgus;
- globāls AI darbaspēka tīkls;
- premium kvalitāte un uzticamība.

### 21.1 Visual Identity Principles
NinaOS vizuālajai identitātei jāatspoguļo:
- Global Workforce;
- Premium Business Platform;
- AI Workers as Real Product Units;
- Platform + Marketplace Duality;
- Scale & Trust.

### 21.2 Brand Direction
NinaOS zīmola sajūtai jābūt:
- futuristic but business;
- premium but usable;
- global but personal;
- powerful but clean;
- AI-native but trustable.

NinaOS nedrīkst izskatīties:
- pēc Telegram bot landing page;
- pēc lēta automation tool;
- pēc haotiska hacker dashboard;
- pēc bērnišķīga neon spēļu interfeisa.

### 21.3 Logo Direction
NinaOS primārais logo virziens ir **Global AI Workforce Symbol**.

Logo pamatā ir globuss / tīkla sfēra, kas simbolizē:
- globālu AI darbaspēku;
- savienotus darbiniekus;
- NinaOS kā centru / platformu;
- Exchange un pasaules mēroga darba ekosistēmu.

### 21.4 Core Product Surfaces
Galvenās NinaOS virsmas:
1. Web Workspace;
2. Mobile App;
3. Exchange Marketplace;
4. Public Marketing Surface.

### 21.5 Product Surface Rules
Katram NinaOS produkta skatam jāatbild uz vienu jautājumu:

Dashboard — kas notiek manā AI darbaspēkā šodien?  
Worker View — ko dara konkrētais AI darbinieks?  
Workspace View — kas notiek manā uzņēmumā?  
Exchange View — kādus AI darbiniekus vai pakalpojumus varu pirkt/pārdot?  
Chat View — kā dodu darbu Nina darbiniekam?  
Analytics View — ko NinaOS darbinieki ir paveikuši?

### 21.6 Worker Card System
NinaOS worker card ir pamatvienība produkta virsmā.

Katram worker card jāparāda:
- worker name;
- role / amats;
- status;
- īss apraksts;
- šī brīža aktivitāte;
- saistītais workspace;
- rating / quality / performance slānis nākotnē;
- pricing vai subscription slānis Exchange worker gadījumā.

### 21.7 Exchange Must Be Visible
Exchange jābūt redzamam kā vienam no centrālajiem pīlāriem:
- web sidebar;
- landing page teaser;
- dashboard preview;
- worker katalogs;
- marketplace plūsma.

---

## 22. First Strategic Wedge — Nina Office Manager SMB

NinaOS pirmais stratēģiskais gatavais darbinieks ir:

# Nina Office Manager SMB

Tas ir AI biroja vadītājs mazajiem uzņēmumiem, kas apvieno vairākus RolePack vienā darbiniekā.

### 22.1 Kāpēc tieši Nina Office Manager SMB
Nina Office Manager SMB ir labākais pirmais wedge, jo:
- tas sēž tieši uz NinaOS platformas loģikas;
- tas izmanto taskus, klientus, projektus, dokumentus, invoices, estimates un follow-up;
- tas ir saprotams mazajiem uzņēmumiem;
- tas ļauj NinaOS pārdot nevis chatbotu, bet AI biroja darbinieku;
- tas kļūst par tiltu uz nākotnes worker katalogu.

### 22.2 Definīcija
Nina Office Manager SMB ir gatavs AI biroja darbinieks mazam uzņēmumam, kas palīdz pārvaldīt:
- klientus;
- uzdevumus;
- dokumentus;
- rēķinu administrēšanu;
- follow-up;
- sākotnējo estimate / offer sagatavošanas plūsmu.

### 22.3 Role Stack
Nina Office Manager SMB sastāv no 5 slāņiem:
1. Office Manager Core;
2. Finance Admin Assistant;
3. Estimating Assistant Basic;
4. Client Follow-up Manager;
5. Document Admin.

### 22.4 Ko dara
Ikdienas darba koordinācija:
- veido taskus;
- seko termiņiem;
- atgādina par nokavētiem darbiem;
- sagatavo dienas plānu;
- izceļ, kas šodien svarīgs.

Klientu darba uzturēšana:
- atceras klientus;
- seko, kur jāatbild;
- seko, kur jānosūta piedāvājums;
- seko, kur jāatgādina par rēķinu;
- seko, kur jāpaprasa informācija.

Piedāvājumi / estimates / projekti:
- savāc input;
- sakārto pieprasījumu;
- palīdz sagatavot estimate/offer draftu;
- piesaista failus un klienta informāciju;
- uztaisa follow-up uzdevumus.

Rēķinu un dokumentu admin:
- atgādina par rēķiniem;
- sagatavo dokumentu pakas grāmatvedībai;
- tur kārtībā failus;
- piesaista dokumentus klientiem un projektiem.

### 22.5 Ko nedara
Bez papildu role/approval viņa nedrīkst:
- iesniegt juridiskus secinājumus kā jurists;
- pildīt pilna grāmatveža funkcijas;
- apstiprināt maksājumus bez atļaujas;
- slēgt saistošus līgumus bez cilvēka apstiprinājuma;
- dot galīgo profesionālo tāmes apstiprinājumu augsta riska gadījumos bez review.

### 22.6 Work Objects
Primārie:
- task;
- client;
- project;
- estimate;
- offer;
- invoice;
- payment_request;
- reminder;
- document_case;
- contract;
- followup_task.

Sekundārie:
- expense_record;
- meeting_note;
- project_scope;
- client_request;
- daily_plan;
- accounting_document_case;
- client_file_bundle.

### 22.7 Memory Scope
Nina Office Manager SMB strādā ar:
- Workspace Memory;
- Client Memory;
- Project Memory;
- Role Memory;
- Document Memory.

### 22.8 Tool Access
Drīkst lietot:
- task tools;
- follow-up tools;
- client tools;
- file/document tools;
- estimate draft tools;
- invoice admin tools;
- reminders / planner tools;
- channel communication tools.

### 22.9 Approval Gate
Cilvēka approval vajag:
- maksājumu apstiprināšanai;
- juridisku dokumentu nosūtīšanai ar risku;
- sensitīvu datu eksportam;
- augsta riska finanšu vai līguma darbībām.

### 22.10 MVP Scope
Pirmā versija fokusējas uz 5 slāņiem:
1. Task + Daily + Reminder;
2. Client Follow-up;
3. Client Work View;
4. Document & Invoice Admin;
5. Basic Estimate / Offer Draft Support.

### 22.11 Stratēģiskā nozīme
Nina Office Manager SMB nav tikai viens produkts.

Tas ir NinaOS pirmais kompozītdarbinieks, uz kura tiek testēta:
- RolePack kombinēšana;
- workspace darba plūsma;
- client / task / invoice / estimate / document work objects;
- multi-role AI worker modelis;
- ready worker kataloga loģika;
- NinaOS kā mazā uzņēmuma AI biroja platforma.

---

## 23. Surface-to-System Mapping

Lai NinaOS nonāktu līdz apstiprinātajai produkta virsmai, katram redzamajam UI blokam jābūt piesaistītam konkrētam sistēmas slānim.

### 23.1 Dashboard KPI Cards
Tasks Today:
- task work objects;
- daily planner;
- task engine;
- due date / priority / completion status.

Follow-ups:
- followup_task objekti;
- client follow-up slānis;
- followup engine.

Invoices Due:
- invoice work objects;
- payment_request objekti;
- finance admin layer.

Estimates in Progress:
- estimate / offer objekti;
- estimating assistant basic layer;
- project/client piesaiste.

Projects Active:
- project work objects;
- work engine;
- client/project state layer.

### 23.2 Worker Summary Card
Nina Office Manager SMB kartīte jābaro no:
- Agent objekta;
- AgentRole stack;
- worker status layer;
- today summary aggregation;
- linked workspace data.

### 23.3 System Status
Jābaro no:
- platform health / runtime status;
- background jobs;
- persistence health;
- audit/event metrics vēlāk.

### 23.4 Workspace Activity
Jābaro no:
- audit log;
- activity events;
- completed tasks;
- follow-up actions;
- invoice updates;
- estimate updates.

### 23.5 Upcoming & Due
Jābaro no:
- task due dates;
- invoice due dates;
- estimate deadlines;
- reminder objects;
- follow-up deadlines.

### 23.6 Recent Activities
Jābaro no:
- audit events;
- task updates;
- invoice actions;
- follow-up actions;
- document uploads;
- estimate status changes.

### 23.7 Estimates Overview
Jābaro no:
- estimate work objects;
- draft/sent/approved/rejected statusiem;
- value totals.

### 23.8 Invoices Overview
Jābaro no:
- invoice work objects;
- paid/pending/overdue statusiem;
- total amounts;
- payment rate metrics.

### 23.9 Quick Actions
Jāatbalsta:
- New Task;
- New Estimate;
- New Invoice;
- Add Client;
- Upload Document;
- Schedule Follow-up.

### 23.10 Exchange Preview
Jābaro no:
- ready_worker_catalog.py;
- role registry / agent registry;
- worker category metadata;
- exchange listing slāņa.

---

## 24. Product Surface Deliverables

NinaOS vizuālais un produkta virsmas slānis jāformalizē atsevišķos dokumentos.

### `NINA_VISUAL_SYSTEM.md`
Definē:
- logo;
- krāsu sistēmu;
- UI stilu;
- kartīšu principus;
- typography;
- spacing;
- iconography;
- dark mode noteikumus;
- product tone.

### `NINA_WORKSPACE_SURFACE.md`
Definē:
- dashboard;
- worker screens;
- tasks / clients / projects / documents / estimates / invoices skatus;
- workspace navigāciju;
- Nina chat vietu produktā.

### `NINA_EXCHANGE_SURFACE.md`
Definē:
- exchange katalogu;
- listing kartītes;
- worker detail view;
- buyer / seller flow;
- marketplace navigāciju.

### `NINA_PUBLIC_SITE.md`
Definē:
- landing page struktūru;
- hero;
- worker sections;
- trust / proof / CTA blokus;
- demo un waitlist plūsmas.

### `NINA_OFFICE_MANAGER_SMB.md`
Definē:
- pilnu Nina Office Manager SMB master spec;
- role stack;
- MVP;
- GTM valodu;
- work objects;
- approval noteikumus.

---

## 25. Build Order — no esošā repo līdz apstiprinātajam NinaOS produktam

### PHASE 1 — Platform Core Foundation
Mērķis:
- workspace;
- agent;
- role stack;
- permissions.

Faili:
- `platform_core.py`;
- `role_pack.py`;
- `role_registry.py`;
- `agent_registry.py`;
- `workspace_engine.py`;
- `permission_engine.py`.

Rezultāts:
Platformas pamata slānis gatavs.

### PHASE 2 — Universal Work Objects
Mērķis:
NinaOS pārstāj būt brīva teksta bots un sāk strādāt ar darba objektiem.

Objekti:
- task;
- client;
- project;
- estimate;
- offer;
- invoice;
- followup_task;
- document_case;
- payment_request;
- reminder;
- daily_plan;
- expense_record;
- accounting_document_case.

### PHASE 3 — Nina Office Manager SMB Role Stack
Mērķis:
Uzbūvēt pirmo kompozītdarbinieku.

Role stack:
- office_manager_core;
- finance_admin_assistant;
- estimating_assistant_basic;
- client_followup_manager;
- document_admin.

### PHASE 4 — Workspace Data Layer
Jāsakārto / jāsavieno:
- `task_engine.py`;
- `followup_engine.py`;
- `client_work_view.py`;
- `daily_planner.py`;
- `work_engine.py`;
- `task_cleanup.py`;
- `memory_service.py`;
- `context_engine.py`.

Jāpievieno:
- invoice admin layer;
- estimate draft layer;
- client/project linking;
- activity/event log.

### PHASE 5 — Knowledge Vault / Documents
Jāuzbūvē:
- file → workspace → client/project/estimate/invoice piesaiste;
- document_case modelis;
- parsing/indexing pamati;
- allowed_roles un sensitivity slānis.

### PHASE 6 — Dashboard Surface API / View Model Layer
Jāizveido surface layer priekš:
- Tasks Today;
- Follow-ups;
- Invoices Due;
- Estimates in Progress;
- Projects Active;
- Upcoming & Due;
- Recent Activities;
- Estimates Overview;
- Invoices Overview;
- Quick Actions;
- Worker summary card;
- Exchange preview.

Iespējamie faili:
- `workspace_dashboard.py`;
- `office_manager_dashboard.py`;
- `activity_feed.py`.

### PHASE 7 — Exchange V1 Surface
Jābūt:
- `ready_worker_catalog.py`;
- worker categories;
- listing cards metadata;
- Explore Exchange plūsmai;
- registry-driven worker katalogam.

Pirmais Exchange saturs:
- Nina Office Manager SMB;
- Nina Sales;
- Nina Estimator;
- Nina Finance;
- Nina Support.

### PHASE 8 — Channel & Chat Layer
Jāsakārto:
- `app.py` kā runtime entrypoint;
- `reply_builder.py`;
- `conversation_engine.py`;
- `employee_brain.py`;
- `initiative_engine.py`;
- `presentation_language.py`.

### PHASE 9 — Public Product Surface / GTM
Jāizveido:
- Nina Office Manager SMB landing page;
- pricing loģika;
- demo script;
- first outreach assets;
- 30 dienu GTM plāns.

---

## 26. Build Discipline Rules

### 26.1 Neviens jauns liels worker netiek būvēts pirms Platform Core un Work Objects pamatnes
Nedrīkst turpināt pievienot sales / support / estimator feature slāņus, ja apakšā nav:
- role registry;
- agent registry;
- workspace engine;
- permission engine;
- work object sistēmas.

### 26.2 Katram jaunam worker jābalstās RolePack sistēmā
Nevis “jauns bots ar citu promptu”, bet:
- role_id;
- atļautie objekti;
- atļautie tooli;
- atmiņas robežas;
- approval noteikumi;
- quality rules.

### 26.3 Katram jaunam dashboard blokam jābūt piesaistītam konkrētam work object vai activity source
Nedrīkst taisīt tukšu UI bez datu modeļa.

### 26.4 Exchange jābūvē paralēli kā redzams slānis
Pat ja sākumā tas ir katalogs, nevis pilns marketplace, tam jābūt NinaOS produktā jau agrīni.

### 26.5 Nina Office Manager SMB ir prioritārais produkta darbinieks līdz pirmajam stabilajam wedge launch
Kamēr nav gatavs pirmais wedge, NinaOS fokuss neizšķīst pa desmit virzieniem.

---

## 27. Kas nākamais praktiski

Pēc V4.2 pareizais nākamais darbs ir:

### STEP 1 — Role / Agent / Workspace / Permission Core
Faili:
1. `role_registry.py`;
2. `agent_registry.py`;
3. `workspace_engine.py`;
4. `permission_engine.py`.

Kāpēc:
Bez tiem nevar korekti uzbūvēt:
- Nina Office Manager SMB role stack;
- ready worker katalogu;
- workspace piesaisti;
- dashboard datu modeli;
- permission boundaries.

---

## 28. NinaOS galīgais virziens pēc V4.2

NinaOS = gatavu AI darbinieku platforma.

Klients nesaņem tukšu botu būvētāju.  
Klients saņem gatavu darbinieku un dod viņam darbu.

NinaOS nodrošina:
- platformas core;
- amatu kontroli;
- datu drošību;
- workspace;
- knowledge vault;
- channel layer;
- billing;
- Nina Exchange;
- audit log;
- premium produktu virsmas;
- mērogošanu līdz 10 000+ gataviem AI amatiem.

Pirmais stratēģiskais NinaOS darbinieks ir:

# Nina Office Manager SMB

Un NinaOS jābūvē tā, lai rezultāts būtu:
- AI workforce operating system;
- small business AI office;
- ready worker platform;
- global exchange;
- premium visual product.
