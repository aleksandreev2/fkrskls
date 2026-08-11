# Product and UX decisions

Load this reference for user-facing features, workflow changes, navigation, information architecture, or any request where the right product behavior is not already obvious.

## Goal

Do not turn a request directly into UI or code. First identify the smallest product decision that solves the actual user job.

For Fukurou, prefer a strong reading/community product over a generic dashboard, generic SaaS layout, or ornamental redesign.

## Decision pass

Before implementation, answer privately and briefly:

1. **User:** who is affected: reader, translator/editor, moderator, publisher, administrator, or operator?
2. **Job:** what are they trying to finish, understand, discover, or recover from?
3. **Friction:** what concrete step is slow, confusing, error-prone, hidden, or visually unclear today?
4. **Success:** what observable behavior should be better after the change?
5. **Existing pattern:** which current Fukurou surface already solves a similar problem?
6. **Scope:** what is the smallest coherent change that solves the problem without creating a parallel system?

Do not write a long product brief for an obvious local fix. The purpose is better decisions, not ceremony.

## When to explore alternatives

For a non-trivial new feature, navigation change, workflow redesign, or ambiguous UI request, consider 2-3 materially different approaches before choosing one.

Evaluate them by:

- user effort and number of decisions required;
- discoverability and clarity;
- compatibility with current Fukurou patterns and data;
- mobile behavior;
- loading, empty, error, disabled, permission, and success states;
- implementation and maintenance cost;
- risk to existing behavior and soft navigation;
- whether the idea still works with real long titles, chapter lists, comments, covers, and user-generated content.

Do not present cosmetic variants as separate approaches. A different border radius or gradient is not a product alternative.

If one approach clearly dominates and does not require a user preference decision, choose it and continue. Ask the user only when alternatives materially change product behavior or scope.

## Research before invention

When a major interaction or visual pattern is unclear and browsing is available, inspect a small number of strong production references before inventing a pattern from scratch.

Use references to answer specific questions such as:

- how do mature reading platforms expose hundreds of chapters on mobile?
- how do community products handle nested actions without menu overload?
- how do content platforms combine discovery and continue-reading states?

Do not clone another product wholesale. Extract the interaction principle, then adapt it to Fukurou's information, visual language, and technical constraints.

Prefer direct product evidence and live behavior over design-gallery screenshots.

## Fukurou product hierarchy

When priorities conflict, use this order unless the task states otherwise:

1. Core task completion and correctness.
2. Clear hierarchy and discoverability.
3. Fast perceived response and stable layout.
4. Mobile usability and touch behavior.
5. Accessibility and keyboard behavior.
6. Consistency with Fukurou's established patterns.
7. Visual polish and delight.
8. Novelty.

A beautiful control that hides the next action is worse than a plain control that makes the workflow obvious.

## Anti-slop rules

Avoid defaults that make unrelated AI-generated products look identical:

- do not turn every region into a floating card;
- do not add gradients, glass, glow, oversized headings, badges, pills, or motion without a product reason;
- do not create a second visual language inside one page;
- do not use placeholder-style marketing copy where real product nouns exist;
- do not solve information hierarchy by adding more containers;
- do not hide useful desktop functionality on mobile merely to make layout fit;
- do not invent new icons or decorative symbols when existing icon language already covers the action.

Distinctiveness should come from Fukurou's content, hierarchy, interaction model, covers, community features, and consistent brand decisions, not decorative noise.

## Interaction completeness

For changed user-facing behavior, inspect applicable states before declaring the design complete:

- initial/loading;
- loaded/normal;
- empty;
- partial data;
- error/retry;
- disabled/busy;
- unauthenticated;
- authenticated but unauthorized;
- destructive confirmation;
- success/feedback;
- long text and overflow;
- narrow mobile viewport;
- keyboard focus;
- reduced motion;
- light and dark theme where supported.

Only test states relevant to the changed surface. Do not manufacture a giant checklist for every one-line change.

## Finish question

Before implementation is considered done, ask:

> If the user never saw the diff, would the resulting behavior feel like an intentional part of Fukurou rather than a patch attached to it?

If not, find the missing product or interaction decision before adding more decoration.
