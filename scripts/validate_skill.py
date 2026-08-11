from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

SKILL_NAME = "fukurou-development"
REFERENCE_RE = re.compile(r"references/[A-Za-z0-9_.-]+\.md")
MAX_SKILL_BYTES = 12_000
MAX_REFERENCE_BYTES = 12_000


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def normalize_newlines(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def parse_frontmatter(text: str, errors: list[str]) -> dict[str, str]:
    text = normalize_newlines(text)
    if not text.startswith("---\n"):
        fail(errors, "SKILL.md must start with YAML frontmatter")
        return {}
    end = text.find("\n---\n", 4)
    if end == -1:
        fail(errors, "SKILL.md frontmatter is not closed")
        return {}

    data: dict[str, str] = {}
    for raw_line in text[4:end].splitlines():
        if not raw_line.strip():
            continue
        if ":" not in raw_line:
            fail(errors, f"unsupported frontmatter line: {raw_line!r}")
            continue
        key, value = raw_line.split(":", 1)
        data[key.strip()] = value.strip().strip('"')
    return data


def validate(repo_root: Path) -> list[str]:
    errors: list[str] = []
    skill_root = repo_root / "skills" / SKILL_NAME
    skill_file = skill_root / "SKILL.md"

    if not skill_file.is_file():
        return [f"missing {skill_file.relative_to(repo_root)}"]

    skill_bytes = skill_file.read_bytes()
    if len(skill_bytes) > MAX_SKILL_BYTES:
        fail(errors, f"SKILL.md is {len(skill_bytes)} bytes; limit is {MAX_SKILL_BYTES}")

    text = skill_bytes.decode("utf-8")
    frontmatter = parse_frontmatter(text, errors)
    if frontmatter.get("name") != SKILL_NAME:
        fail(errors, f"frontmatter name must be {SKILL_NAME!r}")
    description = frontmatter.get("description", "")
    if not description:
        fail(errors, "frontmatter description is required")
    elif len(description) > 1024:
        fail(errors, "frontmatter description exceeds 1024 characters")

    references = sorted(set(REFERENCE_RE.findall(text)))
    if not references:
        fail(errors, "SKILL.md does not reference any supporting files")
    for relative in references:
        target = skill_root / relative
        if not target.is_file():
            fail(errors, f"missing referenced file: {relative}")
            continue
        size = target.stat().st_size
        if size > MAX_REFERENCE_BYTES:
            fail(errors, f"{relative} is {size} bytes; limit is {MAX_REFERENCE_BYTES}")

    expected_references = {
        "references/architecture.md",
        "references/debugging.md",
        "references/frontend.md",
        "references/product-design.md",
        "references/review.md",
    }
    if set(references) != expected_references:
        fail(
            errors,
            "SKILL.md reference set differs from canonical set: "
            f"found={references}",
        )

    metadata = skill_root / "agents" / "openai.yaml"
    if not metadata.is_file():
        fail(errors, "missing agents/openai.yaml")
    else:
        metadata_text = metadata.read_text(encoding="utf-8")
        for required in ("interface:", "display_name:", "short_description:", "default_prompt:"):
            if required not in metadata_text:
                fail(errors, f"agents/openai.yaml missing {required}")
        if "$fukurou-development" not in metadata_text:
            fail(errors, "agents/openai.yaml default prompt must invoke $fukurou-development")

    installer = skill_root / "scripts" / "install.py"
    if not installer.is_file():
        fail(errors, "missing scripts/install.py")
    else:
        try:
            compile(installer.read_text(encoding="utf-8"), str(installer), "exec")
        except SyntaxError as exc:
            fail(errors, f"installer syntax error: {exc}")

    forbidden = list(skill_root.rglob("__pycache__")) + list(skill_root.rglob("*.pyc"))
    for path in forbidden:
        fail(errors, f"generated Python artifact must not be committed: {path.relative_to(repo_root)}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the Fukurou Agent Skill package.")
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()

    repo_root = args.repo.resolve()
    errors = validate(repo_root)
    if errors:
        print("Fukurou skill validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print("Fukurou skill validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
