#!/usr/bin/env python3
"""
Copy legacy static assets from 'BLAST_web plotly subplot/app/static' to 'frontend/app/static'
and create a '.migrated' sentinel so the app will serve from the new static on next start.
Safe to run multiple times; only copies missing/updated files.
"""
from pathlib import Path
import shutil
import filecmp
import sys

ROOT = Path(__file__).resolve().parents[1]
legacy_static = ROOT / 'BLAST_web plotly subplot' / 'app' / 'static'
new_static = ROOT / 'frontend' / 'app' / 'static'
sentinel = new_static / '.migrated'

def copy_dir(src: Path, dst: Path) -> None:
    if not src.exists():
        return
    dst.mkdir(parents=True, exist_ok=True)
    for p in src.rglob('*'):
        rel = p.relative_to(src)
        target = dst / rel
        if p.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        else:
            # copy if missing or content differs
            if (not target.exists()) or (not filecmp.cmp(p, target, shallow=False)):
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(p, target)

def main() -> int:
    if not legacy_static.exists():
        print(f"Legacy static not found at: {legacy_static}")
        return 1
    print(f"Copying static assets from:\n  {legacy_static}\ninto:\n  {new_static}")
    for sub in ('css','js','fonts'):
        copy_dir(legacy_static / sub, new_static / sub)
    sentinel.touch()
    print(f"Done. Created sentinel: {sentinel}")
    print("Restart the app to serve static from the new path.")
    return 0

if __name__ == '__main__':
    sys.exit(main())

