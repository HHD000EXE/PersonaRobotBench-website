#!/usr/bin/env python3
"""Import recorded Gemini 4 episode replays into the website gallery.

Copies each selected web MP4 into assets/gemini4/, extracts a WebP poster from
the recording, and merges one entry per (task, persona) into
data/gemini4-rollouts.json. Re-running with the same or a larger selection is
idempotent: unchanged media are not rewritten and existing entries are kept.

    python3 tools/import_gemini4_videos.py SELECTION.json --videos DIR [--captions DIR]
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
MANIFEST = "data/gemini4-rollouts.json"
MEDIA_DIR = "assets/gemini4"
SCHEMA = "personarobotbench.website-gemini4-rollouts/1"
POSTER_WIDTH = 960
POSTER_SECONDS = 1.0
SEED_RANGE = "100–109"
REASONING_EFFORT = "medium"
LABEL = f"Gemini 4 ({REASONING_EFFORT}) + structured skills"
DESCRIPTION = ("Replays of recorded Gemini 4 (medium reasoning) episodes from the final merged "
               "evaluation run, using the structured skill interface. Each video replays one "
               "recorded episode; it is not a new model run, and the outcome is the native "
               "strict-success result of that episode.")
CAPTION_KEYS = ("full_call", "full_rationale")
# Caption text is published verbatim, so paths fail closed: a slash is allowed only as one word/word or a spaced
# " / "; any other slash, slash chain, backslash, ~/ or internal model id is rejected.
PRIVATE_TEXT = re.compile(r"(?<![\w\s])/|/(?![\w\s])|(?<=\w)/(?=\s)|(?<=\s)/(?=\w)|\w/\w+/|\\|~/|gemini-4-", re.IGNORECASE)
# Internal model codenames, stored as sha256 of the lowercase word so the names stay out of public source.
INTERNAL_WORD_SHA256 = frozenset({"0f85e460e0246cfe3a90d4e8cb701afd82d60a7892af9bda1043a49412f2337c"})


def private_match(value: str) -> str | None:
    found = PRIVATE_TEXT.search(value)
    if found:
        return found.group(0)
    words = re.findall(r"[a-z0-9]+", value.lower())
    return next((w for w in words if hashlib.sha256(w.encode()).hexdigest() in INTERNAL_WORD_SHA256), None)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def probe(video: Path) -> dict:
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_packets",
                          "-show_entries", "stream=width,height,avg_frame_rate,nb_read_packets",
                          "-show_entries", "format=duration", "-of", "json", str(video)],
                         check=True, capture_output=True, text=True).stdout
    data = json.loads(out)
    stream = data["streams"][0]
    num, den = (int(x) for x in stream["avg_frame_rate"].split("/"))
    return {"width": int(stream["width"]), "height": int(stream["height"]),
            "fps": round(num / den, 6), "frames": int(stream["nb_read_packets"]),
            "durationSeconds": round(float(data["format"]["duration"]), 3)}


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


def load_captions(captions_dir: Path | None, stem: str) -> list[dict]:
    if captions_dir is None:
        return []
    path = captions_dir / f"{stem}-master.captions.json"
    if not path.is_file():
        return []
    calls = json.loads(path.read_text()).get("calls", [])
    kept = []
    for call in calls:
        text = {key: call[key] for key in CAPTION_KEYS if isinstance(call.get(key), str) and call[key].strip()}
        for key, value in text.items():
            if (found := private_match(value)) is not None:
                raise ValueError(f"{stem}: skill call {call.get('skill_call')} {key} contains private text ({found!r})")
        if text:
            kept.append({"skillCall": call.get("skill_call"), "startSeconds": call.get("start_s"), **text})
    return kept


def entry_for(item: dict, tasks: dict, videos: Path, captions: Path | None, root: Path) -> dict | None:
    task_id, persona = int(item["task_id"]), str(item["persona"])
    stem = f"task{task_id:03}-gemini4-{persona}"
    source = videos / f"{stem}.mp4"
    if not source.is_file():
        return None
    if item["outcome"] not in ("SUCCESS", "FAILED"):
        raise ValueError(f"{stem}: unknown outcome {item['outcome']!r}")
    if not str(item["model"]).startswith("gemini-4"):
        raise ValueError(f"{stem}: not a Gemini 4 episode: {item['model']!r}")
    if item["reasoning_effort"] != REASONING_EFFORT:
        raise ValueError(f"{stem}: reasoning effort {item['reasoning_effort']!r} differs from the gallery label {LABEL!r}")
    task = tasks[task_id]
    description = next(p["description"] for p in task["personas"] if p["id"] == persona)
    media = root / MEDIA_DIR
    media.mkdir(parents=True, exist_ok=True)
    video = media / f"task{task_id:03}-{persona}.mp4"
    poster = video.with_suffix(".webp")
    if not video.exists() or sha256(video) != sha256(source):
        shutil.copyfile(source, video)
    facts = probe(video)
    make_poster(video, poster, facts["durationSeconds"])
    return {
        "taskId": task_id, "taskKey": item["task_key"], "taskFolder": task["folder"],
        "title": task["title"], "instruction": task["instruction"],
        "persona": persona, "personaDescription": description,
        "seed": int(item["seed"]), "outcome": item["outcome"],
        "strictSuccessSeeds": sorted(int(s) for s in item["strict_successes_s0100_s0109"]),
        "model": "Gemini 4", "reasoningEffort": item["reasoning_effort"],
        "video": video.relative_to(root).as_posix(), "poster": poster.relative_to(root).as_posix(),
        "bytes": video.stat().st_size, "sha256": sha256(video), "posterSha256": sha256(poster),
        **facts, "captions": load_captions(captions, stem),
    }


def run(selection: Path, videos: Path, captions: Path | None, root: Path = ROOT) -> dict:
    items = json.loads(selection.read_text())
    items = items["selection"] if isinstance(items, dict) else items
    tasks = {task["id"]: task for task in json.loads((root / "data/tasks.json").read_text())}
    manifest_path = root / MANIFEST
    entries = {}
    if manifest_path.exists():
        entries = {(e["taskId"], e["persona"]): e for e in json.loads(manifest_path.read_text())["entries"]}
    added, updated, missing = 0, 0, []
    for item in items:
        entry = entry_for(item, tasks, videos, captions, root)
        key = (int(item["task_id"]), str(item["persona"]))
        if entry is None:
            missing.append(f"task{key[0]:03}-{key[1]}")
            continue
        if key not in entries:
            added += 1
        elif entries[key] != entry:
            updated += 1
        entries[key] = entry
    manifest = {"schema": SCHEMA, "label": LABEL,
                "description": DESCRIPTION, "seedRange": SEED_RANGE,
                "entries": [entries[key] for key in sorted(entries)]}
    text = json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
    if not manifest_path.exists() or manifest_path.read_text() != text:
        manifest_path.write_text(text)
    return {"entries": len(entries), "added": added, "updated": updated, "missing": missing,
            "videoBytes": sum(e["bytes"] for e in entries.values())}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("selection", type=Path)
    parser.add_argument("--videos", type=Path, required=True, help="directory with taskNNN-gemini4-P.mp4")
    parser.add_argument("--captions", type=Path, help="directory with taskNNN-gemini4-P-master.captions.json")
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    print(json.dumps(run(args.selection, args.videos, args.captions, args.root.resolve())))


if __name__ == "__main__":
    main()
