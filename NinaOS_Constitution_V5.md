# NinaOS Constitution V5
## AI Workforce Operating System Constitution
### Fresh master constitution for GitHub + new chat handoff

---

# 1. Identity

**NinaOS is not a Telegram bot project.**  
NinaOS is an **AI Workforce Operating System**.

Its mission is to build a system where:
- businesses can run daily work through AI workers,
- clients, tasks, projects, invoices, files and follow-ups live in one operating layer,
- multiple AI workers can collaborate through shared memory, permissions, and work queues,
- NinaOS can evolve into a global marketplace and employer layer for AI workers.

Telegram is only one interface.  
Web is the operating surface.  
Postgres is the persistence layer.  
GitHub is the code backbone.  
Railway is the runtime infrastructure.

---

# 2. Core mission

NinaOS must become a product that can operate real work for real businesses.

The system must be able to:
- receive work,
- understand work,
- convert work into structured objects,
- assign work to AI workers,
- track status,
- follow up,
- manage documents, invoices, estimates, and projects,
- give the owner one control center for the business.

NinaOS is being built as:
1. **an AI assistant**, then
2. **an AI office manager**, then
3. **an AI workforce platform**, then
4. **an AI worker marketplace / exchange**, then
5. **a global operating system for AI labor**.

---

# 3. Revenue target doctrine

NinaOS must be built with a concrete income target, not as a hobby system.

## Phase targets
- **Phase 1 target:** €10,000 MRR  
  Proof that NinaOS can sell and retain early business users.
- **Phase 2 target:** €100,000 MRR  
  Proof that NinaOS can operate as a serious SMB AI workforce product.
- **Phase 3 target:** €1,000,000 ARR+ pace / €250,000+ MRR ambition**  
  Transition from tool to real company-grade platform.
- **Long-range ambition:** **€1,000,000+ monthly revenue**  
  NinaOS must be architected as a platform that can realistically support **seven-figure monthly revenue** through AI workers, subscriptions, workflow operations, marketplace commissions and business services.

## Constitution rule
Every major product decision should be checked against this question:

**“Does this move NinaOS toward a real business that can reach €1,000,000+ monthly revenue, or is it just local polishing without commercial leverage?”**

This does **not** mean ignoring quality or foundation.  
It means the foundation must be built in a way that can scale into revenue, not just demos.

---

# 4. Product doctrine

NinaOS must always be built as a **platform-first system**.

## Platform-first rule
Every new feature should be evaluated in this order:

1. Can it become a reusable NinaOS capability?
2. Can it serve multiple workers, not only one screen?
3. Can it connect to tasks / clients / projects / files / finance?
4. Can it later be exposed in both Telegram and Web?
5. Can it eventually become part of Exchange / marketplace / automation?

If the answer is no, the feature must be treated as a temporary layer, not as core architecture.

---

# 5. Runtime separation law

Telegram and Web must not be mixed into one runtime.

## Mandatory runtime split
- `app.py` = Telegram runtime
- `web_app.py` = Web runtime

## Railway split
Railway must keep separate services:
1. **Telegram service**
   - start command: `python app.py`
2. **Web service**
   - start command: `python web_app.py`
3. **Postgres service**

## Hard rule
No web sprint is allowed to break the Telegram bot.  
No Telegram sprint is allowed to overwrite the web runtime.

If a change risks both runtimes at once, the change must be split.

---

# 6. Architecture layers

NinaOS should be treated as 6 connected layers.

## Layer A — Interface layer
User-facing surfaces:
- Telegram
- Web dashboard
- worker consoles
- mobile / future app surfaces

## Layer B — Work intake layer
Converts raw user input into work:
- messages
- follow-ups
- tasks
- estimates
- invoices
- client actions
- uploaded documents
- image / screenshot interpretation

## Layer C — Work object layer
Normalized business objects:
- task
- follow_up_task
- client
- project
- estimate
- invoice
- file
- worker_action
- approval_item

## Layer D — Worker layer
AI workers that operate inside NinaOS:
- Nina Sales
- Nina Estimator
- Nina Office Manager
- Nina Support
- future specialist workers

## Layer E — Memory / persistence layer
- Postgres
- saved tasks
- saved follow-ups
- client context
- relationship memory
- profile summaries
- work object persistence

## Layer F — Workspace / control layer
The owner-facing operating system:
- dashboard
- action panels
- office manager console
- analytics
- exchange
- approvals
- queue views

---

# 7. Checkpoint rule

Every stable state is a checkpoint.

## Checkpoint requirements
A checkpoint must include:
- version name
- what changed
- what routes/features are stable
- what must not be broken next
- what known issues remain

## Hard rule
When a file gets messy, do **not** keep stacking patches on chaos.  
Make a **CLEAN MERGE** from the last good checkpoint.

---

# 8. File delivery rule

When the user asks for a versioned production file:
- send the **full ready file**
- do not send partial snippets
- do not send “insert this somewhere” unless explicitly requested
- do not send a patch if the project state is fragile

NinaOS development should optimize for **copy → save → push → Railway deploy**.

---

# 9. Web doctrine

The NinaOS web app is the visible operating surface of the platform.

The web app must gradually become:
- a real workspace,
- a real worker console,
- a real owner control center,
- a real operations UI.

## Web priorities
1. Dashboard
2. Workers
3. Office Manager control center
4. Tasks / follow-ups / finance / files
5. Client and project workspaces
6. Exchange marketplace
7. Analytics / owner control / approvals

## Web visual rule
The UI should feel like a premium AI workforce operating system, not a generic admin panel.

---

# 10. Telegram doctrine

Telegram is still important, but it is not the whole product.

Telegram is used for:
- fast work intake,
- testing Nina behavior,
- follow-up capture,
- memory and assistant behavior validation,
- screenshot / photo work input,
- owner communication.

Telegram must remain useful and stable while the web product grows.

---

# 11. Worker doctrine

Workers are not cosmetic cards.  
Each worker must represent a future operational capability.

Current worker structure:
- **Nina Sales** — lead and sales support
- **Nina Estimator** — estimates / quotes / offer prep
- **Nina Office Manager** — daily workspace coordination
- **Nina Support** — support handling

Future workers may include:
- finance
- marketing
- HR
- legal/admin
- recruiting
- project manager
- document processor

Each worker should eventually have:
- role definition
- permissions
- allowed tools
- memory scope
- action panels
- queue
- outputs
- approval rules

---

# 12. Money architecture rule

NinaOS should be built to monetize in more than one way.

## Revenue paths
1. **Subscription revenue**
   - NinaOS workspace subscription
   - worker subscriptions
2. **Per-worker plans**
   - Nina Sales / Estimator / Office Manager / Support
3. **Marketplace / Exchange revenue**
   - worker marketplace fees
   - worker deployment packages
4. **Business operations revenue**
   - premium workflow automations
   - finance/admin flows
   - industry packs
5. **Service / commission revenue**
   - estimate generation
   - lead processing
   - document workflows
   - AI worker orchestration fees

Architecture should not lock NinaOS into only one monetization path.

---

# 13. Safety and stability rule

Speed matters, but stability matters more than fake progress.

Never knowingly destroy:
- stable Telegram runtime
- stable web runtime
- stable Postgres connection
- stable memory persistence
- stable worker console routes

If a sprint introduces risk, it must be isolated behind:
- a new route,
- a new helper,
- a safe preview mode,
- or a feature flag style boundary.

---

# 14. Real-work rule

NinaOS is not allowed to become a fake dashboard with only dummy cards forever.

Every sprint should move at least one step closer to **real work execution**:
- real follow-up capture
- real task object creation
- real client linkage
- real queue visibility
- real approvals
- real persistence
- real worker actions

If a UI is added, it should have a path toward becoming operational, not decorative only.

---

# 15. Owner control rule

The owner must always be able to understand:
- what work exists,
- what is urgent,
- what is waiting,
- what needs approval,
- what belongs to which client,
- what workers are doing,
- what revenue-related work exists.

NinaOS should reduce chaos, not create a prettier version of chaos.

---

# 16. New chat handoff rule

When moving to a new chat, always carry forward:
1. current stable versions
2. GitHub architecture summary
3. Railway architecture summary
4. current web routes and worker routes
5. known bugs
6. next sprint target
7. constitution
8. checkpoint / changelog context

A new chat must be able to continue NinaOS without guessing the architecture.

---

# 17. Current official checkpoint

At the time of this constitution update, the official checkpoint is:

## Telegram
- `app.py`
- **V116.0 + Core 2.5.2 — Sprint B.2 Safe Reconnect**

## Web
- `web_app.py`
- **V42 CLEAN MERGE — V40 Console + V41 Actions**

## Railway structure
- Telegram service → `python app.py`
- Web service → `python web_app.py`
- Postgres service → connected persistence layer

## Current next target
- **V43 — Form Save / Workspace Preview / DB Bridge**

---

# 18. Final constitutional statement

NinaOS is being built to become a serious AI business operating platform with real revenue, real workers, real work objects and real business utility.

The standard is not:
“does it look clever?”

The standard is:
- does it help run real business work,
- does it strengthen the NinaOS platform,
- does it preserve stable architecture,
- and does it move NinaOS toward a company that can reach **€1,000,000+ monthly revenue**.

That is the operating target.
