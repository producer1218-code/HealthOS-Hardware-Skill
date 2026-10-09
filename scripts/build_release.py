"""Build a source ZIP from an explicit public-file allowlist."""
from __future__ import annotations

import argparse
from hashlib import sha256
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo


ROOT = Path(__file__).resolve().parents[1]
ROOT_FILES = ["README.md", "README.zh-CN.md", "AI_CONTEXT.md", "AGENTS.md", "llms.txt",
              "CITATION.cff", "LICENSE", "pyproject.toml", ".gitignore",
              "CONTRIBUTING.md", "SECURITY.md", "AUTHORS.md", "healthos-skill.json"]
DIRS = ["src", "docs", "examples", "tests", "scripts", ".github", "site", "skills", "schemas"]
EXCLUDE_PARTS = {"__pycache__", "_work", ".git", ".venv", "demo-output"}
EXCLUDE_SUFFIXES = {".pyc", ".pyo", ".token"}


def public_files():
    paths = [ROOT / name for name in ROOT_FILES]
    for directory in DIRS:
        paths.extend(path for path in (ROOT / directory).rglob("*") if path.is_file())
    for path in sorted(set(paths)):
        relative = path.relative_to(ROOT)
        if any(part in EXCLUDE_PARTS or part.endswith(".egg-info") for part in relative.parts) or path.suffix in EXCLUDE_SUFFIXES:
            continue
        if path.is_symlink() or path.stat().st_size > 2_000_000:
            raise ValueError(f"unexpected public file: {relative}")
        if not path.exists():
            raise ValueError(f"missing public file: {relative}")
        yield path, relative


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT.parent / "healthos-open-v0.6.0-dev.zip")
    args = parser.parse_args()
    files = list(public_files())
    if not files:
        raise ValueError("empty release")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(args.output, "w", ZIP_DEFLATED, compresslevel=9) as archive:
        for path, relative in files:
            entry = ZipInfo(f"healthos-open/{relative.as_posix()}", (2026, 10, 8, 0, 0, 0))
            entry.compress_type = ZIP_DEFLATED
            entry.external_attr = 0o644 << 16
            archive.writestr(entry, path.read_bytes(), compress_type=ZIP_DEFLATED, compresslevel=9)
    with ZipFile(args.output) as archive:
        bad = archive.testzip()
        if bad:
            raise ValueError(f"corrupt ZIP member: {bad}")
    digest = sha256(args.output.read_bytes()).hexdigest()
    checksum = args.output.with_suffix(args.output.suffix + ".sha256")
    checksum.write_text(f"{digest}  {args.output.name}\n", encoding="ascii")
    print(f"{args.output} ({len(files)} files, sha256 {digest})")


if __name__ == "__main__":
    main()
