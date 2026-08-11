# Live benchmark

This benchmark compares the same Fukurou engineering cases with and without `fukurou-development` using real Codex CLI and Claude Code runs.

It is intentionally **local-first**. The benchmark operates on isolated Git worktrees of an existing `fukurouserver` checkout and does not require model credentials to be stored in this repository or GitHub Actions.

Use `scripts/run_live_benchmark.py` as the public entrypoint. It performs CLI capability checks and installs the purity guards before delegating to the benchmark core in `scripts/live_benchmark.py`.

## What it measures

For each selected case the runner can execute:

- Codex baseline
- Codex with the project skill
- Claude Code baseline
- Claude Code with the project skill

Each run records:

- structured engineering decision/output;
- self-reported supporting references actually consulted;
- whether Developer Intelligence was used;
- observable skill/reference signals from the host event stream;
- tool-call counts where exposed by the host;
- input/cached/output token usage where exposed;
- Claude API cost when reported by Claude Code;
- wall-clock time;
- process exit code;
- whether the planning-only run modified tracked or unexpected untracked source files.

The runner does **not** treat self-reported reference usage as perfect ground truth. It is combined with host telemetry and the static routing eval corpus. The goal is comparable evidence, not a fake single-number benchmark.

## Isolation

The important comparison rule is that the skill must be the only intentional difference between a pair.

For every run the runner creates a fresh detached Git worktree at the requested committed ref.

### Codex

- baseline removes project `fukurou-development` copies;
- with-skill copies only `SKILL.md`, `references/`, and `agents/` to `.agents/skills/fukurou-development`;
- `evals/` and installer scripts are never copied into the benchmark worktree;
- a temporary `HOME` hides personal `$HOME/.agents/skills` from discovery;
- `CODEX_HOME` remains pointed at the user's real Codex home so existing authentication can still work;
- `--ignore-user-config` removes user configuration as a benchmark variable;
- sessions are ephemeral.

### Claude Code

- baseline removes project `fukurou-development` copies;
- with-skill copies the runtime skill to `.claude/skills/fukurou-development`;
- Claude runs with `--setting-sources project`, preventing personal skills/settings from contaminating the pair;
- Edit/Write/NotebookEdit are explicitly disallowed for benchmark runs;
- session persistence is disabled;
- each run has a default dollar cap.

### Purity guard

The injected `.agents/skills/fukurou-development/` or `.claude/skills/fukurou-development/` tree is the only untracked benchmark content ignored by the purity check. Any other tracked **or untracked** file created or modified by the agent is reported as a planning-only violation. Ignored Fukurou Developer Intelligence runtime state remains ignored by Git normally.

## CLI preflight

Before the first model run, the public entrypoint resolves each requested CLI, records its version, reads its help output, and verifies that every flag required by the benchmark is supported.

If a CLI is missing a required capability, the benchmark stops before any paid run and tells you which flags are unavailable.

## Requirements

- Python 3.11+
- Git
- a local committed checkout of `fukurouserver`
- Codex CLI and/or Claude Code installed and already authenticated

## Smoke benchmark

The default `smoke` suite contains five deliberately different cases: frontend lifecycle bug, ambiguous mobile product redesign, literal typo fast path, architecture pressure, and PR review.

Run both hosts and both variants:

```bash
python scripts/run_live_benchmark.py --repo ../fukurouserver
```

Run only Codex:

```bash
python scripts/run_live_benchmark.py --repo ../fukurouserver --agent codex
```

Run only Claude Code:

```bash
python scripts/run_live_benchmark.py --repo ../fukurouserver --agent claude
```

Compare only one case:

```bash
python scripts/run_live_benchmark.py --repo ../fukurouserver --case 1
```

Run a named suite:

```bash
python scripts/run_live_benchmark.py --repo ../fukurouserver --suite frontend
```

Run all 15 quality cases explicitly:

```bash
python scripts/run_live_benchmark.py --repo ../fukurouserver --all
```

This can consume significant model usage. It is intentionally not the default.

## Model and cost controls

Pin models when comparing runs across time:

```bash
python scripts/run_live_benchmark.py \
  --repo ../fukurouserver \
  --codex-model <model> \
  --claude-model <model>
```

Claude Code is capped to `$0.50` per run by default. Override deliberately:

```bash
python scripts/run_live_benchmark.py \
  --repo ../fukurouserver \
  --agent claude \
  --claude-max-budget-usd 1.00
```

The runner cannot impose an equivalent dollar cap on Codex CLI, so selecting a small suite is the primary cost control.

## Dry run

Verify worktree isolation, CLI capabilities, and generated commands without calling either model:

```bash
python scripts/run_live_benchmark.py --repo ../fukurouserver --dry-run
```

## Results

Results are written under `benchmark-results/<UTC timestamp>/` and ignored by Git.

Important files:

```text
metadata.json
results.json
summary.md
case-XX-<agent>-<variant>/
  command.json
  events.jsonl
  stderr.log
  structured.json       # Codex; Claude structured output is extracted from its stream
  result.json
```

`summary.md` shows one row per run and paired token/time deltas when both baseline and skill variants exist.

## Interpreting results

A useful skill should generally improve the engineering decision while keeping its context overhead bounded.

Look for:

- expected references used without forbidden/extra references;
- fewer blind-fix patterns in debugging cases;
- fewer unnecessary product/architecture escalations for local fixes;
- Developer Intelligence used where appropriate;
- no tracked or unexpected untracked source changes in planning-only mode;
- acceptable token/time overhead relative to baseline;
- more concrete verification and risk handling in the structured result.

Do not optimize the skill solely to minimize tokens. A smaller run that makes a worse engineering decision is not a win.

## CI boundary

Normal GitHub Actions validates the benchmark core, guarded entrypoint, schemas, parsers, Git-worktree integration, CLI preflight logic, and isolation rules with fixtures/unit tests. It does **not** call Codex or Claude and does not require model secrets.

Live model runs stay explicit until there is a separate reviewed credential strategy for this public repository.
