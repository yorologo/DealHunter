#!/usr/bin/env python3
"""Local, network-free release traceability check for branch CI."""
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from dealhunter.metadata import VERSION  # noqa: E402


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def _version_tuple(value: str):
    match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", value)
    if not match:
        raise SystemExit(f"release trace error: unsupported VERSION={value!r}")
    return tuple(map(int, match.groups()))


def main() -> int:
    baseline_tag = git("describe", "--tags", "--abbrev=0")
    if not baseline_tag.startswith("v"):
        raise SystemExit(f"release trace error: invalid baseline tag {baseline_tag}")
    baseline_version = baseline_tag[1:]
    tagged_metadata = git("show", f"{baseline_tag}:src/dealhunter/metadata.py")
    match = re.search(r'^VERSION\s*=\s*[\"\']([^\"\']+)[\"\']', tagged_metadata, re.M)
    if not match or match.group(1) != baseline_version:
        raise SystemExit(f"release trace error: {baseline_tag} metadata mismatch")

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    docs_index = (ROOT / "docs" / "README.md").read_text(encoding="utf-8")
    for name, text in (("README.md", readme), ("CHANGELOG.md", changelog), ("docs/README.md", docs_index)):
        if baseline_tag not in text:
            raise SystemExit(f"release trace error: {name} does not reference public baseline {baseline_tag}")

    if _version_tuple(VERSION) < _version_tuple(baseline_version):
        raise SystemExit(f"release trace error: runtime {VERSION} precedes public baseline {baseline_version}")
    if VERSION != baseline_version:
        candidate = f"v{VERSION}"
        if candidate not in readme or candidate not in changelog:
            raise SystemExit(f"release trace error: development candidate {candidate} is not documented")

    print(
        "release_trace=OK "
        f"runtime={VERSION} baseline={baseline_tag} "
        f"baseline_commit={git('rev-parse', baseline_tag + '^{}')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
