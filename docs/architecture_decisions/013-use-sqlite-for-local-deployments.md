# 013. Use SQLite for Local Clinic Deployments

**Date:** 2026-02-23
**Status:** Accepted
**Context:** Phase 1.5 - Persistence Layer

## Context

We are building a clinical PWA designed to run on-premise in small clinics (typically a single Mac Studio server).
The initial plan (Phase 1.5) proposed replacing the in-memory Python dictionaries with **PostgreSQL** running in a Docker container.

However, the operational constraints of a small clinic environment differ from a cloud-native SaaS:
- **Single Server:** Most deployments are single-node.
- **Limited IT Support:** Doctors are not DevOps engineers. Docker networking/volume issues are a major support burden.
- **Concurrency:** A typical clinic has <50 concurrent users, well within the limits of modern SQLite.
- **Data Integrity:** Persistence is critical, but "High Availability" via failover clusters is often over-engineering for a scenario where "replacing the Mac" is the disaster recovery plan.

## Decision

We will use **SQLite (with WAL Mode)** as the primary persistence layer for local clinic deployments, instead of PostgreSQL.

### Configuration
1.  **Driver:** `aiosqlite` for async support with SQLAlchemy.
2.  **Concurrency:** `PRAGMA journal_mode=WAL` (Write-Ahead Logging) must be enabled to allow non-blocking reads during writes.
3.  **Safety:** `PRAGMA synchronous=NORMAL` and `PRAGMA busy_timeout=5000` to prevent database locking errors.
4.  **Backups:** Use the [SQLite Online Backup API](https://www.sqlite.org/backup.html) for hot backups without downtime.

## Consequences

### Positive
- **Operational Simplicity:** No Docker containers, no volume mounts, no port mapping issues.
- **Performance:** Zero network latency (in-process). Faster for simple reads/writes than Postgres over TCP.
- **Deployment:** The database is a single file (`data/clinical.db`), making backups and migrations trivial (file copy).
- **Development:** Developers do not need to spin up a Docker compose stack to run tests or the app.

### Negative
- **JSON Queries:** SQLite stores JSON as TEXT. Querying inside the JSON blob (e.g., `verification_results->'risk'`) requires full table scans, which is slower than Postgres `JSONB` indexing.
    - *Mitigation:* For datasets <100k rows (years of data for a clinic), this performance difference is negligible.
- **Scaling Limit:** We cannot easily scale to multiple API servers (horizontal scaling) because they cannot share the SQLite file reliably over a network.
    - *Mitigation:* If a clinic outgrows a single Mac Studio, we can migrate to PostgreSQL by changing the SQLAlchemy connection string.

## Compliance
- **Encryption:** The `clinical.db` file must be on an encrypted volume (FileVault on macOS, LUKS on Linux).
- **Backups:** Automated scripts must move backups to a separate secure location.

## References
- [SQLite WAL Mode](https://sqlite.org/wal.html)
- [Appropriate Uses For SQLite](https://www.sqlite.org/whentouse.html)
