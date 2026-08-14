# NinaOS Expand-and-Contract Deployment Rule V1

All database-affecting deployments must preserve rolling compatibility.

## Phase A — Expand

- Add only structures and behavior that remain compatible with the currently deployed runtime.
- Preserve existing reads and writes.
- Do not rename, remove, reinterpret, or make existing fields mandatory.
- Verify old and new runtimes can operate against the expanded database concurrently.

## Phase B — Deploy compatible application versions

- Deploy application versions that support both the old and expanded representations.
- Confirm readiness and user-visible behavior before removing old replicas.
- Verify `secure-rebirth` and `happy-education` internal API compatibility before routing Company WhatsApp traffic.

## Phase C — Contract

- Contract only after production evidence confirms no old runtime remains.
- Destructive changes require a separately reviewed, versioned migration.
- Runtime `CREATE`, `ALTER`, rename, or drop operations are not an acceptable contraction mechanism.
