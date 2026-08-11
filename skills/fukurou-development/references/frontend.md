# Fukurou frontend engineering

Load this reference for public frontend, theme, responsive, accessibility, browser-runtime, reader, catalog, profile, forum, library, or other visual/client-side changes.

## Existing architecture first

Fukurou is a brownfield public frontend with deliberate boundaries. Before creating anything new, inspect task context and the nearest existing pattern.

Important sources include, when relevant:

- `frontend/shell/` for shared server-rendered header/footer structure;
- `frontend/assets/css/core/shell.css` for shell and global stability behavior;
- `backend/core/static/theme/theme-system.css` for theme tokens and cross-page appearance contracts;
- `frontend/assets/css/components/` for shared component styles;
- `frontend/assets/css/pages/` for page-scoped styles;
- `frontend/assets/js/core/` for shared runtime helpers;
- `frontend/assets/js/pages/` for page-scoped behavior;
- `frontend/assets/js/legacy/` only where the current page still legitimately depends on legacy behavior;
- `frontend/budgets.json` for measured delivery budgets and recorded tradeoffs.

Do not load all of these by default. Let Developer Intelligence choose relevant files, then expand only when evidence requires it.

## Design-system priority

When styling a changed surface, prefer in this order:

1. Existing component behavior and tokens.
2. Global semantic `--theme-*` tokens.
3. Shared radius scale (`--radius-*`) and established sizing/layout tokens.
4. Existing page-semantic tokens when the concept is truly page-specific.
5. A new semantic token only when the value represents a reusable role existing tokens cannot express.
6. A raw color or size only for a genuinely local value that should not become a system concept.

Do not create a new token merely to rename one hard-coded value. Do not create a parallel palette inside a page when the global theme already models the role.

If a raw value repeats because the same semantic role repeats, consolidate it rather than copying it again.

## CSS and layout discipline

- Fix cascade or ownership problems before adding specificity.
- `!important` needs a concrete invariant, not frustration with an existing selector.
- Avoid page-wide overrides for a local defect.
- Reuse the established radius scale instead of introducing arbitrary radii.
- Do not add wrappers/cards solely to create spacing; use layout primitives where possible.
- Prefer stable dimensions/placeholders when async content would otherwise cause visible layout shift.
- Long real content must wrap, truncate, scroll, or reflow intentionally; do not validate only with short fixtures.
- Preserve supported narrow layouts and touch usability.

## Runtime and soft-navigation discipline

The shared shell and soft navigation make lifecycle mistakes expensive.

- Keep page-ready work independent from optional badges, telemetry, footer hydration, and background refreshes.
- Page listeners, intervals, observers, and other resources must be scoped to the active page and cleaned up on teardown.
- Do not introduce document-wide `MutationObserver`, polling, repeated full-DOM scans, or permanent listeners for a local feature.
- Prefer event delegation only when ownership and lifecycle remain bounded and clear.
- Avoid work on every navigation when it is required only on one page type.
- Preserve scroll position and interaction state intentionally when changing navigation overlays or soft-navigation behavior.
- Cache only where data semantics justify it; do not hide stale or authorization-sensitive state behind convenience caching.

## Theme behavior

A visual change is incomplete if it only works in the theme used while coding.

- Use semantic theme roles rather than assuming dark colors.
- Preserve readable contrast, focus visibility, and selected, hover, and disabled states in light and dark themes.
- Keep reader-specific theme contracts separate where the reader intentionally has its own behavior.
- Theme preview and CSP behavior are part of the contract; do not bypass them with ad-hoc inline execution.

## Mobile is a first-class surface

Do not define mobile as "desktop stacked vertically" or as desktop made smaller.

For dense paired or sequential structures such as progression paths, timelines, comparison rows, or related reward tracks, preserve the relationship between items by changing the interaction model when needed: use a one-item snap/step view, a readable vertical milestone, or another existing Fukurou pattern supported by the real scan task. Do not solve density by shrinking type, actions, and columns until the desktop layout merely fits. Choose the narrow layout from real item count, comparison needs, and the user's next action.

For changed flows, check:

- the primary action remains obvious;
- touch targets are usable;
- menus and overlays fit the viewport and have a correct scroll-lock lifecycle;
- sticky/fixed elements do not create gaps or trap content;
- long labels and localized text do not collide;
- content density remains useful rather than being hidden to make screenshots clean;
- back and close behavior is predictable;
- keyboard and viewport resizing do not make important form controls unreachable.

## Accessibility baseline

For changed interactive UI:

- use native elements when they fit the behavior;
- give controls accessible names;
- keep focus visible;
- ensure keyboard activation and escape/close behavior for dialogs and menus;
- maintain meaningful landmarks and headings;
- keep `hidden`, `aria-*`, disabled, and visual state in agreement;
- respect `prefers-reduced-motion` when adding or changing motion;
- avoid color as the only signal for state.

Accessibility is part of interaction correctness, not a separate polish pass.

## Performance and delivery

Do not guess at performance limits. Use Fukurou's measured contracts:

- `frontend/budgets.json` for source, production, and page budgets;
- canonical frontend checks for loaded assets and request budgets;
- production build/delivery tools for generated manifests and fingerprints.

Never edit generated frontend manifests, fingerprints, minified output, or build artifacts manually. Change sources and run the canonical build.

Do not raise a budget merely because a change exceeded it. First determine whether growth is required functionality, duplicated code, dead code loaded on unrelated pages, a mixed-responsibility module, or a measurement artifact.

Record a budget increase only when the tradeoff is intentional and evidenced.

## Visual workflow

For visual tasks:

1. Capture route, viewport/device class, theme, relevant interaction state, and component.
2. Inspect existing browser behavior before changing it when possible.
3. Implement against existing Fukurou patterns and tokens.
4. Iterate with `python tools/dev.py check --mode visual` or `tools\dev_visual.bat` on Windows.
5. At the final checkpoint validate required evidence states declared by task context.
6. Record evidence through `python tools/dev.py evidence add --kind <state>`.

Do not repeatedly run heavy backend suites between pixel-level iterations.

## Visual quality gate

Before finishing a meaningful UI change, check:

- hierarchy: the eye reaches important content or action first;
- consistency: spacing, typography, radii, surfaces, controls, and icon language belong to Fukurou;
- completeness: relevant loading, empty, error, disabled, and permission states work;
- responsiveness: not just one desktop and one ideal phone width;
- accessibility: semantics, focus, contrast, touch;
- stability: no avoidable flash, jump, scroll reset, or late shell movement;
- economy: no decorative layer exists without helping hierarchy or interaction.

An attractive screenshot is not proof that frontend behavior is correct.
