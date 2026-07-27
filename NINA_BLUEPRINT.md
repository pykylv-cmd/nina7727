# NinaOS Platform Blueprint V6

Status labels describe repository evidence at Constitution V6 adoption.
Existing partial functionality does not make a future platform-wide layer
complete.

| Block | Status | Governing purpose |
|---|---|---|
| Platform Core V1 | implemented | Capability graph, initialization, readiness |
| RolePack System V1 | implemented | Versioned jobs, boundaries, permissions |
| Ready Worker Layer | implemented | Reviewed versioned worker definitions |
| Agent Assignment Layer | next | Customer-owned worker instances |
| Knowledge Vault | planned | Governed customer/worker knowledge |
| Universal Work Objects | planned; existing implementation partial | Platform-wide ownership and execution model |
| Channel Layer | planned; existing channels partial | Neutral channel contracts and coherent identity/work |
| Billing | planned | Entitlements, usage, budgets, charging |
| Nina Exchange | planned | Governed worker and service ecosystem |
| Nina Experience Layer | strategic future; current surfaces partial | One Nina-centered customer experience |
| Voice Layer | strategic future; current input experimental | Provider-neutral speech experience and controls |
| AI Provider Hub | strategic future; OpenAI integration partial | Governed provider adapters and policy |
| Model Router | strategic future | Quality/risk/privacy/cost-aware selection |
| Model Evaluation | strategic future | Evidence-based model and route performance |
| Nina Trust Layer | strategic future as explicit layer; principles mandatory now | Identity, permission, transparency, approvals, safety |
| Connector Layer | strategic future; channel adapters partial | Stable external-system contracts |
| Human Approval | strategic future; isolated concepts partial | Policy and risk gates |
| Audit | strategic future; existing logs/records partial | Customer- and operator-useful action history |
| Device and Robot Layer | strategic future | Device identity, authorization, telemetry |
| Fleet Orchestration | strategic future | Hierarchical assignment and fleet policy |
| Global Control Plane | strategic future | Regional, resilient, tenant-safe coordination |

## Customer flow

`Customer objective -> Nina Experience -> Trust policy -> Agent Assignment -> worker/model/tool selection -> governed work -> validation -> outcome and audit`

The customer remains Nina-centered. Providers, channels, and devices attach as
replaceable resources through stable contracts.

## Current implementation order

1. Platform Core V1 — implemented
2. RolePack System V1 — implemented
3. Ready Worker Catalog V1 — implemented
4. Agent Assignment V1 — next
5. Knowledge Vault V1 — planned
6. Universal Work Objects V1 — planned platform layer
7. Channel Layer V1 — planned platform layer
8. Billing V1 — planned
9. Nina Exchange V1 — planned
10. Mobile and extended interfaces — planned

Strategic layers do not displace Agent Assignment V1. The architecture ledger
must record any future sequence change.
