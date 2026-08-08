# Lending Nelson V2

> **Status: M02 — Backend Foundation**

Lending Nelson V2 is a production-quality lending platform in incremental development and a
structured full-stack learning journey. M02 establishes the backend infrastructure and quality
tooling only; business features are not implemented yet.

The target system has four core components:

- an Owner Flutter App for the single business Owner;
- a separate Borrower Flutter App with no path to Owner privileges;
- a FastAPI Backend that owns authorization and authoritative financial calculations; and
- PostgreSQL as authoritative persistent storage.

New V2 loans will use only Flexible Reducing-Balance repayment with Monthly or calendar-based
Twice-a-Month schedules. The repository uses local milestone feature branches and explicit
non-fast-forward merges so the Git graph remains a readable learning history.

See [ROADMAP.md](ROADMAP.md) for the sequence, [architecture](docs/architecture/ARCHITECTURE.md)
for system boundaries, [loan rules](docs/domain/LOAN_RULES.md) for the canonical financial model,
and [development workflow](docs/development/DEVELOPMENT_WORKFLOW.md) for the Git learning process.
