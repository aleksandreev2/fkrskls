from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
from pathlib import Path

SKILL_NAME = "fukurou-development"
MANAGED_MARKER = ".fukurou-managed-skill"


def source_dir() -> Path:
    return Path(__file__).resolve().parents[1]


def destination_map(home: Path) -> dict[str, Path]:
    return {
        "codex": home / ".agents" / "skills" / SKILL_NAME,
        "claude": home / ".claude" / "skills" / SKILL_NAME,
    }


def iter_source_files(root: Path):
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if path.name == MANAGED_MARKER or "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        yield path


def tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in iter_source_files(root):
        relative = path.relative_to(root).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def installed_digest(root: Path) -> str | None:
    if not root.is_dir():
        return None
    return tree_digest(root)


def is_managed(destination: Path) -> bool:
    return (destination / MANAGED_MARKER).is_file()


def remove_path(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.exists():
        shutil.rmtree(path)


def install_one(source: Path, destination: Path, *, force: bool) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)

    if destination.exists() and not is_managed(destination) and not force:
        raise RuntimeError(
            f"Refusing to replace unmanaged skill at {destination}. "
            "Move it away or rerun with --force if replacement is intentional."
        )

    temporary = destination.parent / f".{SKILL_NAME}.installing"
    remove_path(temporary)

    shutil.copytree(
        source,
        temporary,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", MANAGED_MARKER),
    )
    (temporary / MANAGED_MARKER).write_text(
        "Managed copy of github.com/aleksandreev2/fkrskls.\n"
        "Refresh from the canonical repository skill.\n",
        encoding="utf-8",
    )

    remove_path(destination)
    temporary.replace(destination)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Install the canonical Fukurou skill for Codex and/or Claude Code."
    )
    target = parser.add_mutually_exclusive_group()
    target.add_argument("--codex-only", action="store_true")
    target.add_argument("--claude-only", action="store_true")
    parser.add_argument("--check", action="store_true", help="Report whether installed copies match source.")
    parser.add_argument("--force", action="store_true", help="Replace an existing unmanaged skill with the same name.")
    parser.add_argument(
        "--home",
        type=Path,
        help="Override the target home directory. Intended for CI/tests and controlled installations.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source = source_dir()

    if (source / MANAGED_MARKER).is_file():
        print(
            "error: run this installer from the canonical fkrskls checkout, not from an installed managed copy.",
            file=sys.stderr,
        )
        return 2

    home = args.home.expanduser().resolve() if args.home else Path.home()
    targets = destination_map(home)
    if args.codex_only:
        targets = {"codex": targets["codex"]}
    elif args.claude_only:
        targets = {"claude": targets["claude"]}

    expected = tree_digest(source)

    if args.check:
        stale = False
        for host, destination in targets.items():
            actual = installed_digest(destination)
            if actual is None:
                status = "missing"
            elif not is_managed(destination):
                status = "unmanaged"
            elif actual == expected:
                status = "current"
            else:
                status = "stale"
            print(f"{host}: {status} ({destination})")
            stale = stale or status != "current"
        return 1 if stale else 0

    try:
        for host, destination in targets.items():
            install_one(source, destination, force=args.force)
            print(f"{host}: installed {destination}")
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print("Installation complete. Restart an agent only if it does not detect the new skill in the current session.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
