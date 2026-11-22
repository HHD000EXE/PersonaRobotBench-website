#!/usr/bin/env python3
"""Import recorded model-episode replays into the website gallery as their own group.

Copies each listed web MP4 into assets/<group id>/, extracts a WebP poster from the recording, and
writes data/<group id>-rollouts.json (schema personarobotbench.website-model-replays/1). The page
shows one gallery group per manifest listed in app.js's MODEL_REPLAY_MANIFESTS. Re-running with the
same inputs rewrites nothing.

    python3 tools/import_model_replays.py SPEC.json --videos DIR

SPEC.json describes the group and its episodes:

    {"group": {"id": "deepseek", "title": "DeepSeek V4.1 Flash"},
     "model": "...", "reasoningEffort": "high", "seedRange": [100, 109],
     "description": "...", "note": "...", "selection": "...",
     "episodes": [{"task_id": 23, "task_key": "walking_companion", "persona": "A", "seed": 100,
                   "outcome": "FAILED", "strict_success_seeds": [], "ended": "..."}]}

DIR holds one browser-ready MP4 per episode, named taskNNN-P.mp4 (H.264, yuv420p, fast-start).
Needs `ffmpeg` on PATH.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = "personarobotbench.website-model-replays/1"
POSTER_WIDTH = 960
POSTER_SECONDS = 1.0
RESERVED_GROUPS = {"astra", "gemini4", "example"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def probe(video: Path) -> dict:
    """Stream facts from a full decode-free pass of the file (ffmpeg only; ffprobe is not required)."""
    log = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(video), "-map", "0:v:0", "-c", "copy", "-f", "null", "-"],
                         check=True, capture_output=True, text=True).stderr
    stream = re.search(r"Stream #0:\d+.*Video: (\w+).*?(yuv\w+).*?, (\d+)x(\d+).*?([\d.]+) fps", log)
    frames = re.findall(r"frame=\s*(\d+)", log)
    if not stream or not frames:
        raise ValueError(f"{video.name}: could not read the video stream")
    codec, pixel_format, width, height, fps = stream.groups()
    if codec != "h264" or pixel_format != "yuv420p":
        raise ValueError(f"{video.name}: expected H.264 yuv420p for browsers, found {codec} {pixel_format}")
    return {"width": int(width), "height": int(height), "fps": round(float(fps), 6), "frames": int(frames[-1]),
            "durationSeconds": round(int(frames[-1]) / float(fps), 3)}


def make_poster(video: Path, poster: Path, duration: float) -> None:
    at = min(POSTER_SECONDS, duration / 2)
    with tempfile.TemporaryDirectory() as tmp:
        staged = Path(tmp) / poster.name
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{at:.3f}", "-i", str(video), "-frames:v", "1",
                        "-vf", f"scale={POSTER_WIDTH}:-2", "-c:v", "libwebp", "-quality", "82",
                        "-map_metadata", "-1", str(staged)], check=True)
        data = staged.read_bytes()
        assert data[:4] == b"RIFF" and data[8:12] == b"WEBP", "ffmpeg did not write a WebP poster"
        if not poster.exists() or poster.read_bytes() != data:
            poster.write_bytes(data)


def run(spec_path: Path, videos: Path, root: Path = ROOT) -> dict:
    spec = json.loads(spec_path.read_text())
    group = spec["group"]
    if not re.fullmatch(r"[a-z][a-z0-9-]*", group["id"]) or group["id"] in RESERVED_GROUPS:
        raise ValueError(f"unusable group id: {group['id']!r}")
    first, last = spec["seedRange"]
    tasks = {task["id"]: task for task in json.loads((root / "data/tasks.json").read_text())}
    media_dir = f"assets/{group['id']}"
    (root / media_dir).mkdir(parents=True, exist_ok=True)
    entries = []
    for item in sorted(spec["episodes"], key=lambda e: (int(e["task_id"]), str(e["persona"]))):
        task_id, persona = int(item["task_id"]), str(item["persona"])
        stem = f"task{task_id:03}-{persona}"
        source = videos / f"{stem}.mp4"
        if not source.is_file():
            raise FileNotFoundError(source)
        if item["outcome"] not in ("SUCCESS", "FAILED"):
            raise ValueError(f"{stem}: unknown outcome {item['outcome']!r}")
        seeds = sorted(int(seed) for seed in item["strict_success_seeds"])
        if (int(item["seed"]) in seeds) != (item["outcome"] == "SUCCESS"):
            raise ValueError(f"{stem}: outcome {item['outcome']} disagrees with its strict-success seeds")
        if not all(first <= seed <= last for seed in seeds + [int(item["seed"])]):
            raise ValueError(f"{stem}: seed outside {first}-{last}")
        task = tasks[task_id]
        description = next(p["description"] for p in task["personas"] if p["id"] == persona)
        video = root / media_dir / f"{stem}.mp4"
        poster = video.with_suffix(".webp")
        if not video.exists() or sha256(video) != sha256(source):
            shutil.copyfile(source, video)
        facts = probe(video)
        make_poster(video, poster, facts["durationSeconds"])
        entries.append({
            "taskId": task_id, "taskKey": item["task_key"], "taskFolder": task["folder"],
            "title": task["title"], "instruction": task["instruction"],
            "persona": persona, "personaDescription": description,
            "seed": int(item["seed"]), "outcome": item["outcome"], "strictSuccessSeeds": seeds,
            "ended": item["ended"], "model": spec["model"], "reasoningEffort": spec["reasoningEffort"],
            "video": video.relative_to(root).as_posix(), "poster": poster.relative_to(root).as_posix(),
            "bytes": video.stat().st_size, "sha256": sha256(video), "posterSha256": sha256(poster),
            **facts, "captions": [],
        })
    listed = {f"{Path(e['video']).name}" for e in entries} | {f"{Path(e['poster']).name}" for e in entries}
    for stale in sorted(path for path in (root / media_dir).iterdir() if path.name not in listed):
        stale.unlink()
    manifest = {"schema": SCHEMA, "group": {"id": group["id"], "title": group["title"]},
                "model": spec["model"], "reasoningEffort": spec["reasoningEffort"],
                "description": spec["description"], "note": spec["note"], "selection": spec["selection"],
                "seedRange": [first, last], "mediaDir": media_dir, "entries": entries}
    path = root / f"data/{group['id']}-rollouts.json"
    text = json.dumps(manifest, indent=1, ensure_ascii=False) + "\n"
    if not path.exists() or path.read_text() != text:
        path.write_text(text)
    return {"manifest": path.relative_to(root).as_posix(), "entries": len(entries)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("spec", type=Path)
    parser.add_argument("--videos", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.spec, args.videos), indent=1))
