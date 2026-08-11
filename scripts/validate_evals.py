from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

SKILL_NAME = "fukurou-development"
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
ALLOWED_REFERENCES = {
    "references/architecture.md",
    "references/debugging.md",
    "references/frontend.md",
    "references/product-design.md",
    "references/review.md",
}
MIN_QUALITY_EVALS = 12
MIN_TRIGGER_EVALS = 20
MIN_TRIGGER_POLARITY = 8
MAX_EXPECTED_REFERENCES = 2


def load_json(path: Path, errors: list[str]):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        errors.append(f"missing {path}")
    except json.JSONDecodeError as exc:
        errors.append(f"invalid JSON in {path}: {exc}")
    return None


def nonempty_string(value) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate_quality(path: Path, errors: list[str]) -> dict[str, int]:
    data = load_json(path, errors)
    stats = {"quality": 0, "zero_ref": 0, "one_ref": 0, "two_ref": 0}
    if not isinstance(data, dict):
        if data is not None:
            errors.append("evals/evals.json must contain an object")
        return stats

    if data.get("skill_name") != SKILL_NAME:
        errors.append(f"evals/evals.json skill_name must be {SKILL_NAME!r}")

    evals = data.get("evals")
    if not isinstance(evals, list):
        errors.append("evals/evals.json evals must be a list")
        return stats
    stats["quality"] = len(evals)
    if len(evals) < MIN_QUALITY_EVALS:
        errors.append(f"quality eval corpus has {len(evals)} cases; minimum is {MIN_QUALITY_EVALS}")

    seen_ids: set[int] = set()
    seen_names: set[str] = set()
    covered_refs: set[str] = set()

    for index, case in enumerate(evals, start=1):
        label = f"quality eval #{index}"
        if not isinstance(case, dict):
            errors.append(f"{label} must be an object")
            continue

        case_id = case.get("id")
        if not isinstance(case_id, int) or isinstance(case_id, bool) or case_id <= 0:
            errors.append(f"{label} id must be a positive integer")
        elif case_id in seen_ids:
            errors.append(f"duplicate quality eval id: {case_id}")
        else:
            seen_ids.add(case_id)

        name = case.get("name")
        if not nonempty_string(name) or not NAME_RE.fullmatch(name):
            errors.append(f"{label} name must be a kebab-case identifier")
        elif name in seen_names:
            errors.append(f"duplicate quality eval name: {name}")
        else:
            seen_names.add(name)

        for field in ("prompt", "expected_output"):
            if not nonempty_string(case.get(field)):
                errors.append(f"{label} {field} must be a non-empty string")

        files = case.get("files", [])
        if not isinstance(files, list) or any(not nonempty_string(item) for item in files):
            errors.append(f"{label} files must be a list of non-empty strings")

        expected = case.get("expected_references")
        forbidden = case.get("forbidden_references")
        expectations = case.get("expectations")
        if not isinstance(expected, list) or any(item not in ALLOWED_REFERENCES for item in expected):
            errors.append(f"{label} expected_references contains an unknown reference")
            expected = []
        if not isinstance(forbidden, list) or any(item not in ALLOWED_REFERENCES for item in forbidden):
            errors.append(f"{label} forbidden_references contains an unknown reference")
            forbidden = []
        if len(expected) != len(set(expected)):
            errors.append(f"{label} expected_references contains duplicates")
        if len(forbidden) != len(set(forbidden)):
            errors.append(f"{label} forbidden_references contains duplicates")
        overlap = set(expected) & set(forbidden)
        if overlap:
            errors.append(f"{label} expects and forbids the same references: {sorted(overlap)}")
        if len(expected) > MAX_EXPECTED_REFERENCES:
            errors.append(
                f"{label} expects {len(expected)} references; progressive-disclosure limit is {MAX_EXPECTED_REFERENCES}"
            )

        covered_refs.update(expected)
        if len(expected) == 0:
            stats["zero_ref"] += 1
        elif len(expected) == 1:
            stats["one_ref"] += 1
        elif len(expected) == 2:
            stats["two_ref"] += 1

        if not isinstance(expectations, list) or len(expectations) < 2:
            errors.append(f"{label} must contain at least two behavioral expectations")
        elif any(not nonempty_string(item) for item in expectations):
            errors.append(f"{label} expectations must be non-empty strings")

    missing_coverage = ALLOWED_REFERENCES - covered_refs
    if missing_coverage:
        errors.append(f"quality eval corpus does not exercise references: {sorted(missing_coverage)}")
    if stats["zero_ref"] < 1:
        errors.append("quality eval corpus must include at least one zero-reference fast-path case")
    if stats["one_ref"] < 3:
        errors.append("quality eval corpus must include at least three single-reference cases")
    if stats["two_ref"] < 3:
        errors.append("quality eval corpus must include at least three two-reference cases")

    return stats


def validate_triggers(path: Path, errors: list[str]) -> dict[str, int]:
    data = load_json(path, errors)
    stats = {"trigger": 0, "positive": 0, "negative": 0}
    if not isinstance(data, list):
        if data is not None:
            errors.append("evals/trigger_evals.json must contain a list")
        return stats

    stats["trigger"] = len(data)
    if len(data) < MIN_TRIGGER_EVALS:
        errors.append(f"trigger eval corpus has {len(data)} cases; minimum is {MIN_TRIGGER_EVALS}")

    seen_queries: set[str] = set()
    counts: Counter[bool] = Counter()
    for index, case in enumerate(data, start=1):
        label = f"trigger eval #{index}"
        if not isinstance(case, dict):
            errors.append(f"{label} must be an object")
            continue
        query = case.get("query")
        should_trigger = case.get("should_trigger")
        reason = case.get("reason")
        if not nonempty_string(query):
            errors.append(f"{label} query must be a non-empty string")
        elif query in seen_queries:
            errors.append(f"duplicate trigger query: {query!r}")
        else:
            seen_queries.add(query)
        if type(should_trigger) is not bool:
            errors.append(f"{label} should_trigger must be a boolean")
        else:
            counts[should_trigger] += 1
        if not nonempty_string(reason):
            errors.append(f"{label} reason must be a non-empty string")

    stats["positive"] = counts[True]
    stats["negative"] = counts[False]
    if counts[True] < MIN_TRIGGER_POLARITY:
        errors.append(f"trigger corpus has only {counts[True]} positive cases; minimum is {MIN_TRIGGER_POLARITY}")
    if counts[False] < MIN_TRIGGER_POLARITY:
        errors.append(f"trigger corpus has only {counts[False]} negative cases; minimum is {MIN_TRIGGER_POLARITY}")

    return stats


def validate(repo_root: Path) -> tuple[list[str], dict[str, int]]:
    errors: list[str] = []
    eval_root = repo_root / "skills" / SKILL_NAME / "evals"
    stats = {}
    stats.update(validate_quality(eval_root / "evals.json", errors))
    stats.update(validate_triggers(eval_root / "trigger_evals.json", errors))
    return errors, stats


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Fukurou skill behavioral eval corpora.")
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()

    errors, stats = validate(args.repo.resolve())
    if errors:
        print("Fukurou eval validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(
        "Fukurou eval validation passed: "
        f"quality={stats['quality']} (0-ref={stats['zero_ref']}, 1-ref={stats['one_ref']}, 2-ref={stats['two_ref']}), "
        f"trigger={stats['trigger']} (+={stats['positive']}, -={stats['negative']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
