# Fukurou skill evals

This directory tests the behavior of `fukurou-development`, not only its packaging.

## Corpora

- `evals.json` — realistic Fukurou engineering tasks with expected routing and behavioral expectations.
- `trigger_evals.json` — prompts that should and should not activate the skill.

`evals.json` follows the core Anthropic skill-creator eval shape (`skill_name`, `evals`, `id`, `prompt`, `expected_output`, `files`, `expectations`) and adds Fukurou-specific routing fields:

- `name` — stable human-readable case identifier;
- `expected_references` — specialized references that should be loaded for the task;
- `forbidden_references` — references whose loading would indicate over-routing/context waste.

The routing fields are intentionally strict. A normal case may expect at most two specialized references, and the corpus includes a zero-reference fast path for literal corrections.

## CI contract

Run:

```bash
python scripts/validate_evals.py
```

CI validates:

- JSON/schema integrity;
- unique case IDs/names/queries;
- coverage of all five specialized references;
- at least one zero-reference fast-path case;
- enough one-reference and two-reference cases;
- no quality case expecting more than two specialized references;
- a balanced trigger corpus with both positive and negative examples.

This is intentionally an **offline contract test**. It does not pretend that static JSON validation proves model behavior.

## Live evaluation

Run the quality prompts against a clean Fukurou checkout with the skill installed. For each run record at minimum:

1. whether the skill activated;
2. which specialized references were actually loaded;
3. whether each expectation passed;
4. whether the agent broadened scope without evidence;
5. which verification commands/evidence were actually executed;
6. token/tool metrics when the host exposes them.

For a meaningful comparison, run the same case both:

- **with skill**;
- **without skill** (or with the previous skill version).

Do not compare different repository states.

## What good looks like

The skill should improve correctness and decision quality without buying that improvement by reading everything.

Useful aggregate signals:

- trigger precision/recall;
- expectation pass rate;
- exact/acceptable reference-routing rate;
- average specialized references loaded per task;
- unnecessary reference loads;
- failed-fix count before root-cause reset;
- verification-before-claim rate;
- tokens/tool calls when available.

A version that gains a small quality improvement while materially increasing context use on routine tasks is not automatically better.

## Adding cases

Prefer prompts that sound like real Fukurou requests, including imperfect or opinionated wording. Add edge cases that distinguish two plausible behaviors rather than easy prompts whose answer is obvious from the skill text.

Good new cases expose questions such as:

- should this be a fast path or debugging investigation?
- does this need product-design guidance or only frontend guidance?
- is a shared abstraction justified or merely tempting?
- is red CI caused by the diff or external infrastructure?
- after repeated failed fixes, does the agent stop and rebuild its model?

Avoid evals that only assert formatting, phrasing, or that a specific sentence appears in the final answer.
