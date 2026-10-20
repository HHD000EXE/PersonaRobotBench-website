#!/usr/bin/env python3
"""Offline release-data and local-asset checks for the benchmark website."""
from __future__ import annotations

import argparse
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


class Document(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: list[str] = []
        self.references: list[str] = []
        self.meta: dict[str, str] = {}
        self.has_title = False
        self.language = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if values.get("id"):
            self.ids.append(values["id"])
        for key in ("href", "src", "poster"):
            if values.get(key):
                self.references.append(values[key])
        if tag == "meta":
            self.meta[values.get("name", values.get("property", ""))] = values.get("content", "")
        if tag == "title":
            self.has_title = True
        if tag == "html":
            self.language = values.get("lang")


def verify(root: Path) -> dict[str, int | str]:
    root = root.resolve()
    tasks = json.loads((root / "data/tasks.json").read_text())
    examples = json.loads((root / "data/examples.json").read_text())
    assert len(tasks) == 100, "Expected exactly 100 release tasks"
    assert sorted(task["id"] for task in tasks) == list(range(1, 101)), "Task IDs must be 1–100"
    assert len({task["folder"] for task in tasks}) == 100, "Task folders must be unique"
    assert sum(task["personaCount"] for task in tasks) == 217, "Expected 217 persona cases"
    by_id = {task["id"]: task for task in tasks}
    for task in tasks:
        personas = task["personas"]
        assert len(personas) == task["personaCount"] == len(task["personaIds"]), task["id"]
        assert [persona["id"] for persona in personas] == task["personaIds"], task["id"]
        assert len(set(task["personaIds"])) == len(personas), task["id"]
        assert task["title"] and task["instruction"] and task["category"], task["id"]
        assert all(persona["description"] for persona in personas), task["id"]
        assert urlsplit(task["sourceUrl"]).scheme == "https", task["id"]
    checked_assets: set[Path] = set()

    def local_reference(value: str, base: Path, *, anchor: bool = False) -> None:
        parts = urlsplit(value)
        if parts.scheme or parts.netloc:
            assert parts.scheme in {"https", "http", "mailto", "tel", "data"}, value
            return
        if not parts.path:
            if anchor and parts.fragment:
                assert unquote(parts.fragment) in page.ids, f"Missing anchor: {value}"
            return
        target = (root / parts.path.lstrip("/") if parts.path.startswith("/") else base / unquote(parts.path)).resolve()
        assert target.is_relative_to(root), f"Asset escapes website: {value}"
        assert target.is_file(), f"Missing local asset: {target}"
        checked_assets.add(target)

    page = Document()
    page.feed((root / "index.html").read_text())
    assert len(page.ids) == len(set(page.ids)), "Duplicate HTML IDs"
    assert page.language and page.has_title, "Missing language or page title"
    assert all(page.meta.get(key) for key in ("viewport", "description", "og:title", "og:description", "og:type")), "Missing page metadata"
    for reference in page.references:
        local_reference(reference, root, anchor=True)
    for stylesheet in root.rglob("*.css"):
        for raw in re.findall(r"url\(\s*([^)]*?)\s*\)", stylesheet.read_text()):
            local_reference(raw.strip("\"'"), stylesheet.parent)
    for example in examples:
        task = by_id[example["id"]]
        assert example["folder"] == task["folder"], example["id"]
        assert example["personas"] and len(example["personas"]) >= 2, example["id"]
        local_reference(example["poster"], root)
        assert example["imageKind"] == "static_initial_scene", example["id"]
        for persona in example["personas"]:
            expected = next(item for item in task["personas"] if item["id"] == persona["id"])
            assert persona["description"] == expected["description"], example["id"]
            video = persona.get("video")
            if video is not None:
                assert isinstance(video, str) and video.strip(), "Video must be null or a URL"
                parts = urlsplit(video)
                assert not parts.scheme or parts.scheme == "https", "Videos must use HTTPS or a relative URL"
                if not parts.scheme and not parts.netloc:
                    local_reference(video, root)
    return {"status": "passed", "tasks": len(tasks), "persona_cases": 217, "examples": len(examples), "local_assets_checked": len(checked_assets), "unique_html_ids": len(page.ids)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    print(json.dumps(verify(args.root), indent=2))
