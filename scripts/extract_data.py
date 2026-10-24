"""
scripts/extract_data.py
=======================
Reproducible extraction of the supplied challenge archives into the
git-ignored data/extracted/ directory.

- Keeps every shapefile's companion files (.shp/.shx/.dbf/.prj/.cpg/...) together
  by extracting each archive into its own subdirectory.
- Idempotent: re-running does not overwrite existing files (like `unzip -n`).

Owner: Samai (scripts/)

Usage:
    python -m scripts.extract_data
"""

from __future__ import annotations
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = REPO_ROOT / "data" / "raw"
EXTRACT_DIR = REPO_ROOT / "data" / "extracted"

# archive file -> subdirectory name under data/extracted/
ARCHIVES = {
    "Data1.zip": "Data1",
    "Data2.zip": "Data2",
    "matched_upstream.zip": "matched_upstream",
}


def extract_archive(zip_path: Path, dest_dir: Path) -> list[str]:
    """Extract one zip into dest_dir without overwriting existing files.

    Returns the list of member names that were newly written.
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    written: list[str] = []
    with zipfile.ZipFile(zip_path) as zf:
        for member in zf.namelist():
            # Skip directory entries
            if member.endswith("/"):
                continue
            target = dest_dir / member
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                continue  # -n behaviour: do not overwrite
            with zf.open(member) as src, open(target, "wb") as out:
                out.write(src.read())
            written.append(member)
    return written


def extract_all(verbose: bool = True) -> dict[str, Path]:
    """Extract all known archives. Returns {archive_name: extracted_dir}."""
    results: dict[str, Path] = {}
    for archive_name, subdir in ARCHIVES.items():
        zip_path = RAW_DIR / archive_name
        dest = EXTRACT_DIR / subdir
        if not zip_path.exists():
            if verbose:
                print(f"[skip] {archive_name} not found at {zip_path}")
            continue
        written = extract_archive(zip_path, dest)
        results[archive_name] = dest
        if verbose:
            print(f"[ok] {archive_name} -> {dest.relative_to(REPO_ROOT)} "
                  f"({len(written)} new file(s))")
    return results


if __name__ == "__main__":
    extract_all()
