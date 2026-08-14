# NinaOS Managed Database Migrations V1

## Railway deployment sequence

1. **EXPAND pre-deploy**

   Run in `secure-rebirth` with the same database variables as Web:

   ```text
   python manage_migrations.py expand
   ```

   The command acquires a database-level lock, validates or adopts the current
   schema, applies pending EXPAND migrations transactionally, and records their
   checksums in `nina_schema_migrations`.

2. **Application deployment**

   Deploy compatible application versions only after EXPAND succeeds. Web
   readiness remains false while required EXPAND ledger entries are missing or
   mismatched.

3. **Confirm old runtime removal**

   Verify Railway has no old `secure-rebirth` replica and confirm customer-visible
   behavior before considering contraction.

4. **Explicit CONTRACT approval**

   CONTRACT never runs during ordinary startup. A future reviewed contraction
   requires:

   ```text
   python manage_migrations.py contract --allow-contract
   ```

   V1 contains no CONTRACT or destructive migration.

5. **Rollback**

   Roll application code back only to a version compatible with the expanded
   schema. Do not delete ledger rows or reverse additive structures manually.

6. **Failure recovery**

   A failed migration transaction is rolled back and is not recorded as
   successful. Correct the migration or environment, retain the same identifier
   and checksum policy, and rerun EXPAND. A checksum mismatch requires review;
   never edit the production ledger to bypass it.

## Remaining transition boundary

Legacy modules still contain `CREATE TABLE IF NOT EXISTS` compatibility paths.
V1 moves only shared `conversation_state` creation into a managed EXPAND
migration for hosted runtimes. Remaining DDL must move incrementally in later
reviewed migrations; broad schema rewriting is intentionally out of scope.
