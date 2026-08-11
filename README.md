# Fukurou Skills

Canonical Agent Skills for development of [Fukurou](https://github.com/aleksandreev2/fukurouserver).

This repository is intentionally separate from the application repository so agent behavior can be versioned, tested, reviewed, and installed for multiple coding agents without coupling its lifecycle to production code.

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

Run the same checks used by CI:

```bash
python scripts/validate_skill.py
python -m unittest discover -s tests -p "test_*.py" -v
```

GitHub Actions runs these checks on Ubuntu and Windows with Python 3.11 and 3.13.

## Structure

```text
skills/
└─ fukurou-development/
   ├─ SKILL.md
   ├─ agents/
   │  └─ openai.yaml
   ├─ references/
   │  ├─ architecture.md
   │  ├─ debugging.md
   │  ├─ frontend.md
   │  ├─ product-design.md
   │  └─ review.md
   └─ scripts/
      └─ install.py

scripts/
└─ validate_skill.py

tests/
└─ test_installer.py
```

## Design principles

- Spend tokens on decisions and evidence, not repository rediscovery.
- Let Fukurou Developer Intelligence own file ranking, scope, risks, and canonical checks.
- Load specialized skill references only when the task type needs them.
- Fix root causes before symptoms.
- Prefer existing Fukurou product/design patterns over generic AI-generated UI.
- Keep routine fixes lightweight; escalate only genuinely ambiguous product, design, or architecture decisions.
- Verify real behavior before completion.
