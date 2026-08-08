# Lending Nelson V2 — Development and Git Workflow

## 1. Workspace

Use only this project directory:

```text
Windows: D:\Development\lending_nelson_v2
WSL:    /mnt/d/Development/lending_nelson_v2
```

Run project commands from WSL unless a later platform-specific instruction says otherwise. Before
changing files, confirm the working directory and read `AGENTS.md` plus the relevant documents.

## 2. Learning-History Branch Model

The Git graph is part of the course material. `main` contains only reviewed, verified learning
milestones. Feature work follows this simple workflow:

```text
main
→ feature/mXX-description
→ implement
→ inspect diff
→ test
→ commit
→ review
→ merge --no-ff into main
```

Milestone branches remain available after merging so their commits and decisions can be revisited.
Do not automatically merge an implementation task. The project owner reviews it first and
explicitly requests the merge. The GitHub remote mirrors reviewed learning-history branches;
push only the branch explicitly authorized for the current task, without force or history rewrites.

## 3. Core Git Commands

### `git status`

Shows the current branch and staged, unstaged, or untracked files. Run it before work, before a
commit, and after a commit.

```bash
git status
```

### `git branch`

Lists local branches and marks the current branch. It helps verify that feature work is not being
performed directly on `main`.

```bash
git branch
```

### `git switch`

Moves between existing branches or creates the milestone branch from the reviewed `main` tip.

```bash
git switch main
git switch -c feature/mXX-description
```

### `git diff`

Reviews unstaged changes. Use `--stat` for a summary and the plain command for exact content.

```bash
git diff --stat
git diff
```

### `git diff --staged`

Reviews exactly what the next commit will contain. This is the final scope and secret check before
committing.

```bash
git diff --staged --stat
git diff --staged
```

### `git add`

Stages intentionally selected files. Prefer explicit paths so unrelated changes are not bundled.

```bash
git add path/to/file another/file
```

### `git commit`

Creates a meaningful learning checkpoint. Use a concise Conventional Commit subject such as
`docs:`, `chore:`, `feat:`, `fix:`, `refactor:`, or `test:`.

```bash
git commit -m "docs: describe the learning checkpoint"
```

### `git log`

Shows history. The graph form makes milestone branches and non-fast-forward merges visible.

```bash
git log --graph --oneline --decorate --all -10
```

### `git show`

Explains one commit by showing its metadata and patch. It is useful during milestone review.

```bash
git show --stat HEAD
git show HEAD
```

### `git merge --no-ff`

After explicit review approval, merge from `main` with a merge commit that preserves the milestone
branch in the learning graph:

```bash
git switch main
git merge --no-ff feature/mXX-description
```

Do not delete the local milestone branch afterward. Do not introduce advanced Git commands only
for appearance; `restore`, `revert`, `stash`, `rebase`, `cherry-pick`, and tags belong in later
lessons when a real need makes their tradeoffs teachable.

## 4. Incremental Development Cycle

For each coherent milestone:

1. Inspect current code, documentation, migrations, tests, and Git state.
2. Plan the smallest coherent increment within the milestone scope.
3. Implement related changes together.
4. Run focused tests for the behavior changed.
5. Run the relevant broader quality gates.
6. Inspect `git status`, `git diff --stat`, `git diff`, and the staged diff.
7. Commit a meaningful learning checkpoint.
8. Update `ROADMAP.md` with status, commits, checks, and lessons.
9. Stop for review; merge only when explicitly requested.

When explicit step-by-step mode is requested, complete one step and wait for confirmation instead
of continuing through the whole milestone.

## 5. Quality Gates

Each command becomes active when its milestone introduces the relevant toolchain.

### Backend

From `backend/`, M02 introduces:

```bash
python -m pytest
python -m ruff check .
python -m ruff format --check .
python -m mypy app
python -m alembic heads
python -m alembic current
python -m alembic check
```

The first six gates are collected in `./verify.sh`. `alembic current` and `alembic check` require
a configured PostgreSQL connection and become database-backed gates in M03. M02 has no migration
revision, so a successful `alembic heads` command intentionally prints no head.

M02 distinguishes `/health/live`, which only proves the API process can answer, from
`/health/ready`, which executes `SELECT 1` and safely returns HTTP 503 when PostgreSQL is
unavailable. Mocked readiness tests are unit tests; they are not labeled database integration
tests.

Database milestones additionally test migration from zero, downgrade/re-upgrade, constraints, and
model behavior against a dedicated local PostgreSQL test database.

M04 Owner authentication adds focused security tests plus real PostgreSQL lifecycle tests:

```bash
.venv/bin/python -m pytest tests/test_security.py
.venv/bin/python -m pytest tests/integration/test_owner_auth.py -v
.venv/bin/python scripts/bootstrap_owner.py --username nelson
```

The bootstrap command prompts for the password without echo. Never pass passwords or bearer tokens
on a command line, store them in test output, or commit them. Integration tests override only the
database dependency and continue to use the guarded `lending_nelson_v2_test` database. Login rate
limiting remains a production-hardening decision rather than introducing Redis or a misleading
single-process limiter in M04.

### Local PostgreSQL workflow

M03 uses PostgreSQL only on `127.0.0.1:5432`, with `lending_nelson_v2` for development and the
separate `lending_nelson_v2_test` database for rollback-only integration tests. Before destructive
work, inspect existing databases and confirm both the loopback host and exact database name.

Schema changes follow this sequence:

```text
change SQLAlchemy metadata
→ generate and inspect an Alembic revision
→ upgrade a clean development database
→ inspect tables and constraints
→ downgrade to base
→ re-upgrade to head
→ run alembic check
→ run integration tests against the dedicated test database
```

Integration tests require `TEST_DATABASE_URL`, carry the `integration` marker, and reject remote
hosts or any database name other than `lending_nelson_v2_test`. A mocked database test is never
reported as an integration test. The test database is not interchangeable with development data.

Use PostgreSQL catalog queries (`pg_tables`, `pg_constraint`, and `pg_indexes`) plus
`alembic current`, `alembic heads`, and `alembic check` to verify that code metadata, migration
history, and the real schema agree.

### Flutter

From each future Flutter application:

```bash
flutter analyze
flutter test
```

Client tests must verify presentation/session behavior without duplicating authoritative backend
financial calculations.

## 6. Database and Secret Safety

- All persistent PostgreSQL schema changes use Alembic.
- Destructive integration tests use a separate, explicitly local test database and refuse unsafe
  targets.
- Existing databases are inspected before reuse or recreation; old schema/data is not silently
  accepted for a new learning milestone.
- Real `.env` files, credentials, keys, tokens, dumps, and database storage are never committed.
- Commit safe `.env.example` values only when configuration is introduced.
- Before every commit, check both the staged patch and ignored/untracked files for accidental
  secrets or generated artifacts.

## 7. Failure and Completion Reporting

Report the exact command, failure summary, and useful error details for any failed check. Never
claim an unrun or failing gate passed. A milestone is ready for review only when its deliverables
exist, relevant checks pass, its commits are coherent, and the working tree is clean.
