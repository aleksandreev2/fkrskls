# Root-cause debugging

Load this reference for bugs, regressions, flaky tests, unexpected browser behavior, performance regressions, build failures, worker failures, or any situation where the cause is not already proven.

## Iron rule

Do not patch a symptom before establishing a plausible causal chain supported by evidence.

A small obvious typo can be fixed directly when the cause is literally visible. Everything else gets an investigation pass first.

## Phase 1: establish the failure

1. Restate the observed behavior in concrete terms.
2. Identify expected behavior and where that expectation comes from: product contract, test, existing behavior, API shape, or user report.
3. Reproduce when practical, or gather the strongest available evidence when reproduction is unavailable.
4. Record the smallest conditions that trigger the failure: route, state, account or permission, viewport or theme, worker state, input, timing, or deployment context.

Do not infer the cause from the symptom name.

## Phase 2: trace the causal chain

Follow data and control flow from the visible failure backward through the owning component.

At boundaries, inspect what actually crosses them:

- request -> route -> API/service;
- serializer -> response shape -> frontend consumer;
- DOM state -> event handler -> page lifecycle;
- queue row -> claim -> external side effect -> state transition;
- source asset -> build -> manifest -> browser delivery;
- theme token -> page token -> selector -> computed state.

Prefer direct evidence such as values, call sites, test fixtures, browser state, logs, or measured sizes over verbal guesses.

## Phase 3: hypotheses

Form one specific hypothesis at a time:

> X happens because Y under condition Z; if true, evidence E should be observable.

Test the cheapest discriminating evidence first. Do not change several unrelated things and then infer which one worked.

If the first hypothesis fails, update the model of the system before trying the next one.

## Three-fix stop rule

After three failed implementation attempts for the same symptom, stop editing.

Re-check:

- whether the owning component is correct;
- whether reproduction is stable;
- whether shared state or lifecycle is involved;
- whether the assumed API/data shape is wrong;
- whether the real bug sits one boundary earlier;
- whether a compatibility layer or generated artifact is masking the source.

Three failed patches are evidence that the mental model is wrong, not a signal to add a fourth patch.

## Fix design

Once the cause is supported:

1. Fix the earliest appropriate point in the causal chain.
2. Prefer restoring an existing invariant over adding a special case.
3. Keep the change within the owning component unless evidence requires crossing a boundary.
4. Remove obsolete workaround code made unnecessary by the fix when safe.
5. Add or strengthen a regression check for reproducible bugs unless automation is technically impractical.

Do not weaken assertions, authorization checks, Quality Truth, budgets, or timeouts just to make the symptom disappear.

## Frontend-specific traps

Before using another CSS override or timing delay, rule out:

- specificity/cascade ownership;
- hidden, aria, disabled, and visual state disagreement;
- async shell or cached state arriving after first paint;
- soft-navigation teardown leaks;
- scroll container vs document/root confusion;
- containing blocks created by transforms, filters, or backdrop filters;
- stale generated delivery output;
- event propagation and DOM replacement changing listener assumptions;
- mobile viewport or keyboard behavior;
- theme-specific token mismatch.

## Backend/worker-specific traps

Before retrying or adding guards, rule out:

- authorization or user-scope mismatch;
- transaction boundary mistakes;
- duplicate or missing durable queue claims;
- retryable vs permanent failure classification;
- side effects occurring before durable state is claimed;
- stale cache or serialization shape mismatch;
- migration/schema drift;
- provider/network failure being mistaken for application logic.

## Verification

A debugging task is not complete because the symptom disappeared once.

Verify:

- the original reproduction now passes;
- a regression check fails on broken behavior and passes with the fix where practical;
- adjacent states still work;
- the final diff contains no abandoned diagnostics or speculative workarounds;
- changed-scope checks and `task-finish` pass.

In the final report, state root cause separately from the fix.
