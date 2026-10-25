#!/usr/bin/env python3
"""Offline release-data and local-asset checks for the benchmark website."""
from __future__ import annotations

import argparse
import hashlib
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
            if persona.get("videoPoster"):
                local_reference(persona["videoPoster"], root)
            if "videoDurationSeconds" in persona:
                assert isinstance(persona["videoDurationSeconds"], (int, float)) and persona["videoDurationSeconds"] > 0, example["id"]
        if example.get("recording"):
            local_reference(example["recording"]["provenance"], root)

    # The public site carries its own receipt manifest; no private repository or
    # simulator is needed to verify that videos and recording posters are intact.
    provenance_path = root / "data/rollout-provenance.json"
    recordings = []
    if provenance_path.exists():
        provenance = json.loads(provenance_path.read_text())
        assert provenance["schema"] == "personarobotbench.website-rollouts/1", "Unknown rollout provenance schema"
        recordings = provenance["recordings"]
        records = {(item["taskId"], item["persona"]): item for item in recordings}
        assert len(records) == len(recordings), "Duplicate rollout receipt"
        expected = {(task_id, persona) for task_id in (18, 51, 68) for persona in ("A", "B")}
        assert expected <= records.keys(), "Missing featured A/B recording receipt"

        def digest(file: Path) -> str:
            checksum = hashlib.sha256()
            with file.open("rb") as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    checksum.update(chunk)
            return checksum.hexdigest()

        def fast_start(file: Path) -> bool:
            """Inspect top-level ISO BMFF boxes, without decoding video frames."""
            with file.open("rb") as stream:
                size = file.stat().st_size
                while stream.tell() + 8 <= size:
                    start = stream.tell()
                    header = stream.read(8)
                    length, kind = int.from_bytes(header[:4], "big"), header[4:]
                    header_size = 8
                    if length == 1:
                        extended = stream.read(8)
                        assert len(extended) == 8, "Truncated MP4 box"
                        length = int.from_bytes(extended, "big")
                        header_size = 16
                    elif length == 0:
                        length = size - start
                    assert header_size <= length <= size - start, "Invalid MP4 box"
                    if kind in (b"moov", b"mdat"):
                        return kind == b"moov"
                    stream.seek(start + length)
            return False

        for example in examples:
            if not example.get("recording"):
                continue
            for persona in example["personas"]:
                if not persona.get("video"):
                    continue
                receipt = records[(example["id"], persona["id"])]
                assert receipt["video"] == persona["video"], "Video URL differs from receipt"
                assert receipt["poster"] == persona["videoPoster"], "Poster URL differs from receipt"
                assert receipt["recordedTaskId"] == example["recording"]["recordedTaskId"], "Historical task ID differs"
                assert abs(receipt["durationSeconds"] - persona["videoDurationSeconds"]) < 0.001, "Duration differs"
                local_reference(receipt["video"], root)
                local_reference(receipt["poster"], root)
                video_parts = urlsplit(receipt["video"])
                video_file = None
                if not video_parts.scheme and not video_parts.netloc:
                    video_file = root / unquote(video_parts.path).lstrip("/")
                    assert video_file.stat().st_size == receipt["bytes"], "Video size differs"
                    assert digest(video_file) == receipt["sha256"], "Video hash differs"
                poster_parts = urlsplit(receipt["poster"])
                if not poster_parts.scheme and not poster_parts.netloc:
                    assert digest(root / unquote(poster_parts.path).lstrip("/")) == receipt["posterSha256"], "Poster hash differs"
                assert receipt["durationSeconds"] > 0 and receipt["frames"] > 0, "Empty recording"
                if receipt.get("fastStart") and video_file and video_file.suffix.lower() == ".mp4":
                    assert fast_start(video_file), "Video does not have fast-start metadata"
    # The opt-in 3D viewer must remain self-contained in the deployment.
    model_dir = root / "assets/models"
    for name in ("assets/models/shared-desk.glb", "assets/models/shared-desk.provenance.json",
                 "assets/models/scene-environment.hdr", "assets/models/scene-environment.provenance.json",
                 "assets/models/texture-sources.json", "assets/vendor/model-viewer.min.js",
                 "assets/vendor/LICENSE.model-viewer", "assets/vendor/LICENSE.unitree"):
        local_reference(name, root)
    for model, receipt in (("shared-desk.glb", "shared-desk.provenance.json"),
                           ("scene-environment.hdr", "scene-environment.provenance.json")):
        record = json.loads((model_dir / receipt).read_text(encoding="utf-8"))
        assert hashlib.sha256((model_dir / model).read_bytes()).hexdigest() == record["outputSha256"], model
    glb = (model_dir / "shared-desk.glb").read_bytes()
    assert glb[:4] == b"glTF" and int.from_bytes(glb[8:12], "little") == len(glb), "Invalid GLB"
    gltf = json.loads(glb[20:20 + int.from_bytes(glb[12:16], "little")])
    assert not gltf.get("animations"), "Initial scene must not contain authored motion"
    assert all("COLOR_0" in primitive["attributes"] for mesh in gltf["meshes"] for primitive in mesh["primitives"]), "Missing baked shading"
    assert any(material.get("pbrMetallicRoughness", {}).get("metallicFactor", 0) > .9 for material in gltf["materials"]), "Missing source metal material"
    return {"status": "passed", "tasks": len(tasks), "persona_cases": 217, "examples": len(examples), "recordings": len(recordings), "local_assets_checked": len(checked_assets), "unique_html_ids": len(page.ids)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    print(json.dumps(verify(args.root), indent=2))
