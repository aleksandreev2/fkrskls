# Review before completion

Load this reference for explicit code review or audit requests and for non-trivial changes before the final changed-scope gate.

The purpose is to catch defects and incompleteness, not to manufacture stylistic feedback.

## Review order

Review in descending impact:

1. **Correctness:** wrong behavior, missing state transitions, race conditions, stale assumptions, broken consumers.
2. **Security and privacy:** authorization, user scoping, CSRF/session, signed access, sensitive data, moderation boundaries.
3. **Regression risk:** shared shell/runtime, lifecycle cleanup, API compatibility, migration behavior, generated delivery.
4. **Product completeness:** missing loading, empty, error, permission, mobile states, or controls with no real outcome.
5. **Performance:** unnecessary requests, global scans, repeated work, large assets, dead code loaded on unrelated pages.
6. **Maintainability:** duplicated responsibility, ambiguous ownership, new abstractions that do not earn their cost.
7. **Visual consistency and accessibility:** hierarchy, tokens, responsive behavior, focus, semantics, contrast, reduced motion.

Do not lead with formatting or naming while a correctness issue exists.

## Evidence standard

A finding should identify:

- exact file, symbol, or changed behavior;
- the condition under which it fails or becomes risky;
- why existing tests or checks do not already prove it safe;
- the smallest reasonable fix or verification step.

Do not report speculative "could maybe" problems without a plausible execution path.

## Severity

Use a small severity scale:

- **P0:** data loss, security boundary break, widespread outage, or unrecoverable corruption.
- **P1:** likely production bug, major user-facing regression, broken critical workflow, or serious performance problem.
- **P2:** meaningful correctness, UX, or maintainability issue that should be fixed before work is considered polished.
- **Note:** optional improvement; never present it as blocking.

If there are no substantive findings, say so. A review is allowed to be clean.

## Diff discipline

Inspect the final diff, not only files currently open in context.

Look for:

- accidental generated or runtime files;
- abandoned debug logging;
- commented-out old implementations;
- unrelated cleanup mixed into the task;
- duplicated code left after a refactor;
- new magic constants or tokens duplicating existing roles;
- tests weakened to match implementation;
- budget or timeout increases without evidence;
- broad exception handling hiding failure classification;
- client behavior assuming only one theme, viewport, or authentication state.

## Tests and checks

Do not equate "tests pass" with "change is correct."

Confirm selected checks actually cover changed behavior. For a reproducible bug, confirm a regression check was added or strengthened unless automation is technically impractical.

For visual work, browser evidence is part of correctness. For model or schema changes, migration consistency is part of correctness. For privileged paths, negative authorization is part of correctness.

## Simplification pass

Before adding more code in response to a review finding, ask whether the correct fix is to:

- delete obsolete code;
- reuse an existing primitive;
- move logic back to its owner;
- reduce state or event paths;
- remove a duplicate source of truth.

Prefer fewer mechanisms with stronger invariants over more defensive layers.

## Completion

After review fixes:

1. inspect the diff again;
2. run the complete changed-scope gate required by Developer Intelligence;
3. run `python tools/dev.py task-finish`;
4. do not claim completion if the report is stale, incomplete, dry-run-only, or from another task or diff.
