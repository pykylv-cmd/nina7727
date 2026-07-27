# NinaOS Controlled Railway Release

Production release remains pending manual environment and database preflight
verification. Channel Layer V1 remains Planned.

1. Run `git fetch origin`, verify `git status --short`, and require
   `git rev-list --left-right --count HEAD...@{upstream}` to report no remote
   commits on the right before push.
2. Run the focused tests, `python -m unittest discover -v`,
   `node --test test/*.test.js`, both JSON validations, and
   `git diff --check`.
3. In Railway, verify names only: `DATABASE_URL`,
   `NINA_RUNTIME_ENV`, `NINA_WEB_WORKSPACE_COOKIE_SECRET`,
   `NINA_CHANNEL_CREDENTIAL_KEY`, `OPENAI_API_KEY`, `PORT`,
   `NINA_PERSONAL_WHATSAPP_BRIDGE_TOKEN`, `NINA_WEB_INTERNAL_URL`,
   `PERSONAL_WHATSAPP_BRIDGE_URL`, and feature-specific Telegram,
   WhatsApp, admin, and Stripe variables.
4. Run `python manage_migrations.py preflight` in the Web service environment.
   Continue only on `NinaOS migration preflight PASS`.
5. Push `feature/web-chat-v1` only after the previous checks pass.
6. Confirm Railway runs `python manage_migrations.py preflight` followed by
   `python manage_migrations.py expand` as pre-deploy commands.
7. Verify Railpack build and Gunicorn startup complete without secret output.
8. Require HTTP 200 from `/live`, `/ready`, and `/health`.
9. Smoke-test the dashboard and Web Chat with a test workspace.
10. Create, read, transition, and archive one test Agent Assignment.
11. Create, activate, version, and archive one test Knowledge Vault item.
12. Create, transition, query, and archive one test Universal Work Object.
13. Roll back if migration preflight/expand fails, `/ready` remains 503,
    tenant isolation fails, existing data is missing, or core Web Chat breaks.
14. Before a migration, rollback means stop the release. After an additive
    migration, redeploy the last known-good commit; do not reverse 0001–0004
    or delete their columns/tables.
