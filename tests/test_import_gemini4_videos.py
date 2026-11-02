"""Import-script checks: python3 -m unittest discover -s tests -p 'test_*.py' (needs ffmpeg)."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT))
import import_gemini4_videos as importer  # noqa: E402
import verify  # noqa: E402


def selection_item(task_id: int, persona: str, outcome: str, seed: int = 100) -> dict:
    return {"task_id": task_id, "task_key": f"key{task_id}", "task_folder": "ignored", "persona": persona,
            "seed": seed, "episode_dir": "/private/run", "outcome": outcome,
            "strict_successes_s0100_s0109": [seed, 105] if outcome == "SUCCESS" else [105],
            "duration_s": 1.0, "model": "gemini-4-test", "reasoning_effort": "medium", "model_api_calls": 1}


def make_video(path: Path, color: str) -> None:
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c={color}:s=320x180:r=30:d=2",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(path)], check=True)


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "ffmpeg is required")
class ImportGemini4Videos(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.root, self.videos, self.captions = self.tmp / "site", self.tmp / "web", self.tmp / "captions"
        for directory in (self.root / "data", self.videos, self.captions):
            directory.mkdir(parents=True)
        shutil.copy(ROOT / "data/tasks.json", self.root / "data/tasks.json")
        self.tasks = json.loads((ROOT / "data/tasks.json").read_text())
        for name, color in (("task021-gemini4-A", "red"), ("task021-gemini4-B", "blue"), ("task023-gemini4-C", "green")):
            make_video(self.videos / f"{name}.mp4", color)
        (self.captions / "task021-gemini4-A-master.captions.json").write_text(json.dumps({"episode": "x", "calls": [
            {"skill_call": 2, "model_call": 1, "start_s": 4.5, "full_call": "place(object=keys)"},
            {"skill_call": 3, "model_call": 1, "start_s": 9.0, "full_rationale": "Because A prefers it."},
            {"skill_call": 4, "model_call": 1, "start_s": 9.5}]}))
        self.addCleanup(shutil.rmtree, self.tmp)

    def write_selection(self, name: str, items: list[dict]) -> Path:
        path = self.tmp / name
        path.write_text(json.dumps({"merge": "/private", "predicate": "p", "selection": items}))
        return path

    def run_import(self, selection: Path) -> dict:
        return importer.run(selection, self.videos, self.captions, self.root)

    def test_manifest_from_selection_is_idempotent_and_extendable(self) -> None:
        pilot = self.write_selection("pilot.json", [selection_item(21, "A", "SUCCESS"), selection_item(21, "B", "FAILED", 101)])
        first = self.run_import(pilot)
        self.assertEqual((first["entries"], first["added"], first["updated"], first["missing"]), (2, 2, 0, []))
        manifest_path = self.root / importer.MANIFEST
        manifest = json.loads(manifest_path.read_text())
        self.assertEqual(manifest["schema"], importer.SCHEMA)
        a, b = manifest["entries"]
        self.assertEqual((a["taskId"], a["persona"], a["outcome"], b["outcome"], b["seed"]), (21, "A", "SUCCESS", "FAILED", 101))
        self.assertEqual(a["video"], "assets/gemini4/task021-A.mp4")
        self.assertEqual((a["width"], a["height"], a["fps"], a["frames"]), (320, 180, 30.0, 60))
        self.assertEqual(a["personaDescription"], self.tasks[20]["personas"][0]["description"])
        self.assertEqual(a["captions"], [{"skillCall": 2, "startSeconds": 4.5, "full_call": "place(object=keys)"},
                                         {"skillCall": 3, "startSeconds": 9.0, "full_rationale": "Because A prefers it."}])
        self.assertEqual(b["captions"], [])
        self.assertEqual((self.root / a["poster"]).read_bytes()[8:12], b"WEBP")
        self.assertNotIn("/private", manifest_path.read_text(), "Local paths must not reach the public manifest")
        self.assertEqual(verify.verify_gemini4(self.root, self.tasks), 2)

        before = {path: path.stat().st_mtime_ns for path in self.root.rglob("*") if path.is_file()}
        text = manifest_path.read_text()
        again = self.run_import(pilot)
        self.assertEqual((again["entries"], again["added"], again["updated"]), (2, 0, 0))
        self.assertEqual(manifest_path.read_text(), text)
        self.assertEqual({path: path.stat().st_mtime_ns for path in self.root.rglob("*") if path.is_file()}, before)

        scale = self.write_selection("scale.json", [selection_item(23, "C", "SUCCESS"), selection_item(99, "A", "FAILED")])
        grown = self.run_import(scale)
        self.assertEqual((grown["entries"], grown["added"], grown["missing"]), (3, 1, ["task099-A"]))
        keys = [(e["taskId"], e["persona"]) for e in json.loads(manifest_path.read_text())["entries"]]
        self.assertEqual(keys, [(21, "A"), (21, "B"), (23, "C")])
        self.assertEqual(verify.verify_gemini4(self.root, self.tasks), 3)

    def test_changed_video_updates_entry_and_verify_detects_tampering(self) -> None:
        pilot = self.write_selection("pilot.json", [selection_item(21, "A", "SUCCESS")])
        self.run_import(pilot)
        make_video(self.videos / "task021-gemini4-A.mp4", "yellow")
        self.assertEqual(self.run_import(pilot)["updated"], 1)
        self.assertEqual(verify.verify_gemini4(self.root, self.tasks), 1)
        with (self.root / "assets/gemini4/task021-A.mp4").open("ab") as stream:
            stream.write(b"x")
        with self.assertRaises(AssertionError):
            verify.verify_gemini4(self.root, self.tasks)

    def test_rejects_unknown_outcome_and_non_gemini_model(self) -> None:
        bad = selection_item(21, "A", "PARTIAL")
        with self.assertRaises(ValueError):
            self.run_import(self.write_selection("bad.json", [bad]))
        other = dict(selection_item(21, "A", "SUCCESS"), model="astra")
        with self.assertRaises(ValueError):
            self.run_import(self.write_selection("other.json", [other]))


if __name__ == "__main__":
    unittest.main()
