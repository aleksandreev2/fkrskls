# Research decisions

This file records why `fukurou-development` adopts or rejects patterns from other agent-skill systems. It is maintenance documentation, not a runtime reference, so agents do not load it during normal Fukurou tasks.

## Anthropic skill-creator

Source: `anthropics/skills` and the official Claude skill-creator plugin.

Adopted:

- keep triggering information in the frontmatter description;
- make the description explicit enough to avoid under-triggering;
- use realistic quality evals in `evals/evals.json`;
- keep a separate should-trigger / should-not-trigger corpus;
- compare skill versions using real task outcomes, not only structural linting;
- preserve progressive disclosure: compact `SKILL.md`, detailed references only when needed.

Fukurou adaptation:

- quality evals add structured `expected_references` and `forbidden_references` so context waste can be measured;
- CI validates the eval corpus offline but does **not** pretend that static validation proves model behavior;
- live with-skill / without-skill runs remain a separate evaluation step.

## Superpowers

Source: `obra/superpowers`.

Adopted:

- root-cause investigation before behavior fixes;
- repeated failed fixes are evidence that the mental model should be rebuilt;
- fresh verification evidence before claiming completion.

Fukurou adaptation:

- literal visible corrections keep a zero-reference fast path;
- the process is not forced onto every typo or obvious local edit;
- Fukurou Developer Intelligence remains the source of truth for repository context and checks.

## gstack

Source: `garrytan/gstack`.

Adopted:

- distinguish pre-implementation product/design judgment from post-implementation review;
- treat design as hierarchy, states, mobile behavior, and actual interaction rather than decorative polish;
- stop blind patch loops after repeated failed fixes.

Rejected as a default:

- a mandatory multi-review ceremony for every change;
- large design audits for narrow fixes;
- one-commit-per-design-finding workflows as a universal rule.

Fukurou uses adaptive gates instead: ambiguity/risk increases process depth; explicit local work stays lightweight.

## Vercel agent skills and web guidelines

Sources: `vercel-labs/agent-skills` and `vercel-labs/skills`.

Adopted:

- Agent Skills directory structure and progressive disclosure conventions;
- accessibility, responsive, state, navigation, theming, and performance concerns as frontend correctness;
- keep `SKILL.md` small and push detailed material into one-level references/scripts.

Not adopted as a runtime dependency:

- fetching a mutable remote guideline/prompt file before every review.

Fukurou freezes the high-value principles locally. External research may inform a specific decision, but mutable remote instructions are treated as untrusted research material rather than executable agent instructions.

## Distribution

The repository keeps a self-contained Python installer for Codex and Claude Code because it is cross-platform, covered by Windows/Linux CI, and does not require Node/npm or a third-party installer at runtime.

General Agent Skills CLIs can remain optional convenience tooling, but they are not part of the correctness or CI path of this repository.

## Evaluation rule

A borrowed pattern is retained only if it improves one or more of:

- correctness;
- product/design decision quality;
- root-cause accuracy;
- verification quality;
- trigger accuracy;
- context/tool efficiency.

If a pattern mostly adds ceremony, duplicated repository discovery, or unconditional context loading, it should not be added.
