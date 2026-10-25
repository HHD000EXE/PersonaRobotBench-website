#!/usr/bin/env python3
"""Build the dependency-free benchmark website into dist/."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"


def build():
    required = ("index.html", "styles.css", "app.js")
    for name in required:
        if not (ROOT / name).is_file():
            raise FileNotFoundError(name)
    # Only this script's generated dist directory is replaced.
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir()
    for name in ("index.html", "styles.css", "app.js"):
        shutil.copy2(ROOT / name, DIST / name)
    # GitHub Pages should serve these exact static files without Jekyll processing.
    (DIST / ".nojekyll").touch()
    shutil.copytree(ROOT / "assets", DIST / "assets")
    (DIST / "data").mkdir()
    for name in ("tasks.json", "examples.json", "asset-provenance.json", "rollout-provenance.json",
                 "task-preview-provenance.json", "leaderboard.json", "leaderboard-results.json"):
        shutil.copy2(ROOT / "data" / name, DIST / "data" / name)
    tasks = json.loads((DIST / "data/tasks.json").read_text())
    if len(tasks) != 100 or sum(task["personaCount"] for task in tasks) != 217:
        raise ValueError("The website catalog does not match the release")
    files = sorted(path for path in DIST.rglob("*") if path.is_file())
    manifest = {"schema": "personarobotbench.website/1", "tasks": 100, "personaCases": 217,
                "files": {path.relative_to(DIST).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                          for path in files}}
    (DIST / "asset-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"output": str(DIST), "files": len(files) + 1,
                      "bytes": sum(path.stat().st_size for path in DIST.rglob("*") if path.is_file()),
                      "tasks": 100, "personaCases": 217}))


if __name__ == "__main__":
    build()
