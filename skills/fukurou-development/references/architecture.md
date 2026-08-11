# Fukurou architecture decisions

Load this reference for backend changes, refactors, shared infrastructure, API changes, model or migration work, workers, storage, deployment, or changes crossing more than one component.

## Stable architecture

Fukurou intentionally remains a modular Django monolith.

Preserve these boundaries unless the task explicitly changes the architecture program:

- Django application with domain modules rather than microservices by default;
- public frontend sources separate from server-rendered Studio/ProgrammerStudio surfaces;
- PostgreSQL, Redis, storage, and worker boundaries as existing operational contracts;
- historical migrations as immutable history;
- synchronized dependency locks;
- generated or fingerprinted frontend delivery artifacts derived from source;
- stable root launch, update, release, and rollback behavior.

Do not propose a framework rewrite, microservice split, Kubernetes migration, SPA rewrite, or broad infrastructure replacement as a convenient way to solve a local task.

## Ownership before abstraction

Use Developer Intelligence to identify the owning component before editing shared code.

Prefer this order:

1. Fix or implement inside the owning domain.
2. Reuse an existing shared primitive when it already models the need.
3. Extract a shared primitive only when at least two real callers share the same concept and lifecycle.
4. Change a cross-domain contract only when local ownership cannot solve the problem cleanly.

Do not move code into `core`, `common`, or a generic helper merely because more than one file needs it. Shared code creates shared coupling.

## Data and API contracts

For public or cross-component API changes:

- identify current producers and consumers;
- preserve response shape unless change is deliberate;
- update serialization, frontend consumers, authorization coverage, and compatibility behavior together;
- distinguish absent, empty, unauthorized, deleted, and invalid states where the product cares about the difference;
- avoid leaking internal model structure into public response shapes without a reason.

Backward compatibility is a product and operations decision, not an automatic requirement. But do not silently break an existing consumer.

## Models and migrations

Model changes require:

- migration consistency;
- safe defaults or backfill strategy for existing rows where needed;
- awareness of uniqueness, index, and locking effects;
- tests at the behavior boundary, not only model construction;
- no renumbering or rewriting historical migrations that may already be applied.

Prefer database-enforced invariants for facts the database can reliably own.

## Transactions and concurrency

For stateful operations, identify the durable transition explicitly.

Ask:

- what state proves this work is claimed?
- can two processes observe the same work?
- what happens after a crash between state change and side effect?
- which failures are retryable?
- can the operation run twice safely, or does it need idempotency or uniqueness?

Do not use process-local state as the source of truth for work coordinated across processes.

## Workers and external side effects

Worker code must claim durable state before browser, network, filesystem, provider, or other external side effects where the existing contract requires it.

Keep retryable and permanent failures explicit. Do not convert all exceptions into retries.

For provider integrations, separate:

- provider configuration and credentials;
- request or browser execution;
- parsing and normalization;
- durable state transition;
- retry classification;
- user or operator-visible failure information.

## Security boundaries

Do not weaken or route around:

- authentication and authorization;
- CSRF and session boundaries;
- rate limits and abuse controls;
- privacy and user scoping;
- signed or private media access;
- audit and moderation checks;
- queue ownership;
- secret and environment isolation.

When changing a privileged path, include a negative authorization case where relevant.

## Refactoring

Refactor because a concrete change is unsafe or expensive under the current structure, not because a different structure is aesthetically cleaner.

Good refactor triggers include:

- responsibilities are mixed and the current task must touch several unrelated concerns;
- a file has become a bottleneck evidenced by budgets, change frequency, or repeated bugs;
- duplicate behavior is already diverging;
- lifecycle or ownership is impossible to reason about locally;
- a compatibility layer has completed migration and usage evidence says it can be removed.

For behavior-preserving moves, separate the move from behavior change when doing both together would make failures ambiguous.

## Cross-component changes

If implementation legitimately expands beyond generated task context:

1. stop before editing the new component;
2. restart `task-start` with the complete component set;
3. re-evaluate affected risks and checks;
4. continue with expanded context.

Do not silently broaden scope because a convenient shared file is nearby.

## Architecture finish gate

Before completing a cross-component or refactor task, verify:

- ownership is clearer or unchanged, not more ambiguous;
- public behavior is intentionally preserved or intentionally changed;
- call sites and consumers moved together;
- generated artifacts remain derived;
- migration and authorization contracts are intact;
- targeted regression coverage exists;
- the final diff contains no speculative architecture work unrelated to the request.
