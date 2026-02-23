# Review of Phase 1.5 Kickoff: Persistence Layer (Revised)

**Date:** 2026-02-23
**Reviewer:** Gemini CLI
**Subject:** docs/plans/2025-02-23-pwa-phase1-5-kickoff.md

## Verdict: Strategic Approval (SQLite Pivot)

The plan has been revised to target **SQLite (WAL Mode)** instead of PostgreSQL. This is a radically candid engineering decision that simplifies operations for local clinic deployments without sacrificing necessary performance.

### ✅ Why This Is The Right Call
1.  **Operational Simplicity:** Removing the Docker/Postgres requirement eliminates the #1 source of failure for local, on-premise deployments (container networking/volume issues).
2.  **Concurrency Reality:** For a single clinic (<50 concurrent users), SQLite in WAL mode handles write throughput easily.
3.  **Backup Reliability:** The inclusion of `backup_db.py` using the SQLite Online Backup API addresses the data safety risk of file-based databases.

### 💡 Implementation Guidance
1.  **WAL Mode is Non-Negotiable:** Ensure the `PRAGMA journal_mode=WAL` command is executed on every connection checkout. Without this, the UI *will* freeze during uploads.
2.  **Batch Migrations:** SQLite has limited support for `ALTER TABLE`. Ensure Alembic is configured with `render_as_batch=True` or migrations will fail.
3.  **Path Management:** Hardcoding `data/clinical.db` is risky. Use `platformdirs` or an environment variable `CLINICAL_DATA_DIR` to ensure the DB lives in a persistent, backed-up location on the host OS.

### ⚠️ Replaces Previous Review
This review supersedes the previous "Strong Approval" for the Postgres plan. The shift to SQLite aligns better with the "Local First / Single Server" constraints of the project.

## Conclusion
**Proceed with the SQLite implementation.**
