# Fukurou Skills

Canonical Agent Skills for development of [Fukurou](https://github.com/aleksandreev2/fukurouserver).

This repository is intentionally separate from the application repository so agent behavior can be versioned, tested, reviewed, benchmarked, and installed for multiple coding agents without coupling its lifecycle to production code.

## Available skill

### `fukurou-development`

A project-specific engineering skill for Codex and Claude Code. It layers product judgment, root-cause debugging, frontend/design discipline, architecture decisions, and completion review on top of Fukurou's existing Developer Intelligence system.

The main `SKILL.md` is intentionally compact. Specialized guidance is loaded on demand from `references/` so unrelated UI, debugging, or architecture instructions do not consume context on every task.

## Install

Clone this repository, then run:

```bash
python skills/fukurou-development/scripts/install.py
```

Managed destinations:

- Codex: `~/.agents/skills/fukurou-development`
- Claude Code: `~/.claude/skills/fukurou-development`

Install only one target when needed:

```bash
python skills/fukurou-development/scripts/install.py --codex-only
python skills/fukurou-development/scripts/install.py --claude-only
```

The installer refuses to overwrite an existing unmanaged skill unless `--force` is supplied explicitly.

## Update / verify

After pulling a newer version of this repository, refresh installed copies with the same install command:

```bash
python skills/fukurou-development/scripts/install.py
```

Check whether installed copies match the canonical repository version without modifying them:

```bash
python skills/fukurou-development/scripts/install.py --check
```

A missing, stale, or unmanaged copy returns a non-zero exit code.

## Repository validation

Run the same deterministic checks used by CI:

```bash
python scripts/validate_skill.py
python scripts/validate_evals.py
python scripts/validate_benchmarks.py
python -m unittest discover -s tests -p "test_*.py" -v
```

GitHub Actions runs these checks on Ubuntu and Windows with Python 3.11 and 3.13. Normal CI never calls a paid model.

## Behavioral evals

The repository keeps two eval corpora inside the skill:

- `evals/evals.json` — realistic Fukurou engineering tasks with expected routing and behavioral outcomes;
- `evals/trigger_evals.json` — prompts that should and should not activate the skill.

The quality corpus deliberately includes:

- a zero-reference fast path for literal corrections;
- single-reference frontend/debug/architecture/review cases;
- two-reference cases for problems that genuinely cross concerns;
- repeated-fix, CI, security, worker/idempotency, mobile, theme, performance, product-design, and architecture edge cases.

CI enforces a progressive-disclosure contract: a normal eval may expect no more than two specialized references. This prevents future changes from quietly turning the skill into an "always read everything" prompt.

Static CI validates the corpus and routing contract; it does **not** claim to measure model quality.

## Live Codex / Claude benchmark

`scripts/run_live_benchmark.py` is the guarded public entrypoint for paired real-agent runs against one committed Fukurou repository state. It performs CLI capability checks and purity guards before delegating to the benchmark core.

The default smoke benchmark compares baseline vs skill on five different engineering cases for both Codex and Claude Code:

```bash
python scripts/run_live_benchmark.py --repo ../fukurouserver
```

Useful narrower runs:

```bash
python scripts/run_live_benchmark.py --repo ../fukurouserver --agent codex
python scripts/run_live_benchmark.py --repo ../fukurouserver --agent claude
python scripts/run_live_benchmark.py --repo ../fukurouserver --case 1
python scripts/run_live_benchmark.py --repo ../fukurouserver --suite frontend
```

Running all 15 quality cases is explicit because it can consume significant model usage:

```bash
python scripts/run_live_benchmark.py --repo ../fukurouserver --all
```

The runner creates a fresh detached Git worktree for every run, injects the skill only for the `skill` variant, hides personal Codex skills with a shadow home, limits Claude discovery to project settings, and never copies the eval answer corpus into the runtime skill. Claude edit tools are explicitly disabled. Planning runs may create ignored Developer Intelligence state, but any tracked or unexpected untracked source change is reported as a purity violation.

Before the first model request, the entrypoint verifies that each requested CLI exposes every benchmark-required flag. This avoids spending a run only to discover an incompatible CLI version.

Results are written to ignored `benchmark-results/` directories with raw event streams, structured outputs, usage telemetry, routing results, and a Markdown pair summary.

See [`benchmarks/README.md`](benchmarks/README.md) for isolation details, cost controls, model pinning, result interpretation, and dry-run usage.

## Structure

```text
benchmarks/
├─ README.md
├─ response_schema.json
└─ suites.json

skills/
└─ fukurou-development/
   ├─ SKILL.md
   ├─ agents/
   │  └─ openai.yaml
   ├─ evals/
   │  ├─ README.md
   │  ├─ evals.json
   │  └─ trigger_evals.json
   ├─ references/
   │  ├─ architecture.md
   │  ├─ debugging.md
   │  ├─ frontend.md
   │  ├─ product-design.md
   │  └─ review.md
   └─ scripts/
      └─ install.py

scripts/
├─ live_benchmark.py
├─ run_live_benchmark.py
├─ validate_benchmarks.py
├─ validate_evals.py
└─ validate_skill.py

tests/
├─ test_benchmark_entrypoint.py
├─ test_evals.py
├─ test_installer.py
└─ test_live_benchmark.py

docs/
└─ research-decisions.md
```

## Design principles

- Spend tokens on decisions and evidence, not repository rediscovery.
- Let Fukurou Developer Intelligence own file ranking, scope, risks, and canonical checks.
- Load specialized skill references only when the task type needs them.
- Keep a zero-reference fast path for literal local corrections.
- Fix root causes before symptoms.
- Prefer existing Fukurou product/design patterns over generic AI-generated UI.
- Keep routine fixes lightweight; escalate only genuinely ambiguous product, design, or architecture decisions.
- Do not automatically load a final-review reference after every non-trivial edit.
- Require fresh evidence before claiming work is fixed, passing, or complete.
- Benchmark baseline and skill on the same committed repository state before optimizing prompts from intuition.

## Research provenance

`docs/research-decisions.md` records which ideas were adopted, adapted, or rejected from Anthropic skill-creator, Superpowers, gstack, and Vercel agent-skill tooling. It is intentionally outside the runtime skill so normal engineering tasks do not pay context for research history.
