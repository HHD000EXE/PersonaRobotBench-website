"""Import-script checks: python3 -m unittest discover -s tests -p 'test_*.py' (needs ffmpeg)."""
from __future__ import annotations

import codecs
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# Internal codename, kept out of tracked text: only its rot13 form and sha256 appear here.
CODENAME = codecs.decode("nexrabf", "rot13")
CODENAME_SHA256 = "0f85e460e0246cfe3a90d4e8cb701afd82d60a7892af9bda1043a49412f2337c"
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

    def test_external_media_base_links_videos_without_copying_them(self) -> None:
        pilot = self.write_selection("pilot.json", [selection_item(21, "A", "SUCCESS")])
        importer.run(pilot, self.videos, self.captions, self.root, media_base="https://media.example.org/prb/")
        manifest = json.loads((self.root / "data/gemini4-rollouts.json").read_text())
        entry = manifest["entries"][0]
        self.assertEqual(manifest["mediaBase"], "https://media.example.org/prb")
        self.assertEqual(entry["video"], "https://media.example.org/prb/gemini4/task021-A.mp4")
        self.assertFalse(list((self.root / "assets/gemini4").glob("*.mp4")))
        self.assertTrue((self.root / entry["poster"]).is_file())
        source = (self.videos / "task021-gemini4-A.mp4").read_bytes()
        self.assertEqual((entry["bytes"], entry["sha256"]), (len(source), hashlib.sha256(source).hexdigest()))
        self.assertEqual(verify.verify_gemini4(self.root, self.tasks), 1)

    def test_verify_rejects_external_video_outside_the_https_media_base(self) -> None:
        pilot = self.write_selection("pilot.json", [selection_item(21, "A", "SUCCESS")])
        importer.run(pilot, self.videos, self.captions, self.root, media_base="https://media.example.org/prb")
        path = self.root / "data/gemini4-rollouts.json"
        good = path.read_text()
        for old, new in (("https://media.example.org/prb/gemini4/", "https://evil.example.org/gemini4/"),
                         ("https://media.example.org/prb", "http://media.example.org/prb")):
            path.write_text(good.replace(old, new))
            with self.assertRaises(AssertionError):
                verify.verify_gemini4(self.root, self.tasks)
        with self.assertRaises(ValueError):
            importer.run(pilot, self.videos, self.captions, self.root, media_base="http://media.example.org/prb")

    def test_import_rejects_mixing_media_bases_with_retained_entries(self) -> None:
        manifest = self.root / "data/gemini4-rollouts.json"
        a = self.write_selection("a.json", [selection_item(21, "A", "SUCCESS")])
        b = self.write_selection("b.json", [selection_item(21, "B", "FAILED", 101)])
        for first, second in ((None, "https://media.example.org/prb"), ("https://media.example.org/prb", None),
                              ("https://media.example.org/prb", "https://other.example.org")):
            manifest.unlink(missing_ok=True)
            importer.run(a, self.videos, self.captions, self.root, media_base=first)
            before = manifest.read_text()
            with self.assertRaises(ValueError):
                importer.run(b, self.videos, self.captions, self.root, media_base=second)
            self.assertEqual(manifest.read_text(), before)
            source = self.videos / "task021-gemini4-A.mp4"  # selected again but its source is gone: still retained
            moved = source.rename(source.with_suffix(".bak"))
            try:
                with self.assertRaises(ValueError):
                    importer.run(self.write_selection("ab.json", [selection_item(21, "A", "SUCCESS"),
                                                                  selection_item(21, "B", "FAILED", 101)]),
                                 self.videos, self.captions, self.root, media_base=second)
            finally:
                moved.rename(source)
            self.assertEqual(manifest.read_text(), before)

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


    def imported_manifest(self) -> dict:
        self.run_import(self.write_selection("pilot.json", [selection_item(21, "A", "SUCCESS")]))
        return json.loads((self.root / importer.MANIFEST).read_text())

    def write_manifest(self, manifest: dict) -> None:
        (self.root / importer.MANIFEST).write_text(json.dumps(manifest))

    def test_private_caption_text_is_rejected_by_importer_and_verify(self) -> None:
        manifest = self.imported_manifest()
        for text in ("Read /home/user/run/episode.json", "see /srv/data/x", "from /Volumes/me/a", "in /tmp/x",
                     "C:\\runs\\a", "model gemini-4-argon said", f"the {CODENAME} run", f"the {CODENAME.upper()}-1 run",
                     "Read /root/evals/episode.json", "at /private/run/episode.json", "(/workspace/evals/e.json)",
                     "C:/runs/episode.json", "see ~/runs/e.json", "path=/srv/x/y", "Read /episode.json",
                     "Read /my runs/episode.json", "source:/root/evals/episode.json", "in runs/evals/episode.json",
                     "see https://example.org/a", "dir\\file", "ends with /"):
            for key in ("full_call", "full_rationale"):
                with self.subTest(text=text, key=key):
                    path = self.captions / "task021-gemini4-A-master.captions.json"
                    path.write_text(json.dumps({"episode": "x", "calls": [{"skill_call": 1, "start_s": 0, key: text}]}))
                    with self.assertRaisesRegex(ValueError, "task021-gemini4-A"):
                        self.run_import(self.write_selection("pilot.json", [selection_item(21, "A", "SUCCESS")]))
                    bad = json.loads(json.dumps(manifest))
                    bad["entries"][0]["captions"] = [{"skillCall": 1, "startSeconds": 0, key: text}]
                    self.write_manifest(bad)
                    with self.assertRaisesRegex(AssertionError, "21.*A"):
                        verify.verify_gemini4(self.root, self.tasks)

    def test_verify_rejects_duplicate_or_out_of_range_seeds(self) -> None:
        manifest = self.imported_manifest()
        self.assertEqual(verify.verify_gemini4(self.root, self.tasks), 1)
        for seeds, seed in (([100, 100, 105], 100), ([100, 110], 100), ([99, 100], 100), ([105], 99), ([105], 110)):
            with self.subTest(seeds=seeds, seed=seed):
                bad = json.loads(json.dumps(manifest))
                bad["entries"][0].update(strictSuccessSeeds=seeds, seed=seed,
                                         outcome="SUCCESS" if seed in seeds else "FAILED")
                self.write_manifest(bad)
                with self.assertRaises(AssertionError):
                    verify.verify_gemini4(self.root, self.tasks)

    def test_reasoning_effort_must_match_the_published_label(self) -> None:
        high = dict(selection_item(21, "A", "SUCCESS"), reasoning_effort="high")
        with self.assertRaisesRegex(ValueError, "task021-gemini4-A"):
            self.run_import(self.write_selection("high.json", [high]))
        manifest = self.imported_manifest()
        self.assertIn("(medium)", manifest["label"])
        manifest["entries"][0]["reasoningEffort"] = "high"
        self.write_manifest(manifest)
        with self.assertRaises(AssertionError):
            verify.verify_gemini4(self.root, self.tasks)

    def test_public_caption_text_with_slashes_is_accepted(self) -> None:
        for text in ("pick up/put down the cup", "pick/place", "about 0.5 m/s", "270 degrees / 4.7124 rad",
                     "robot ~0.74 m ahead", "only ~27s left", "ratio 3/4"):
            with self.subTest(text=text):
                path = self.captions / "task021-gemini4-A-master.captions.json"
                path.write_text(json.dumps({"episode": "x", "calls": [{"skill_call": 1, "start_s": 0, "full_call": text}]}))
                self.run_import(self.write_selection("pilot.json", [selection_item(21, "A", "SUCCESS")]))
                verify.verify_gemini4(self.root, self.tasks)

    def test_tracked_files_do_not_contain_the_internal_codename(self) -> None:
        tracked = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, check=True, capture_output=True).stdout
        for name in tracked.decode().split("\0"):
            path = ROOT / name
            if not name or path.suffix in {".mp4", ".webp", ".png", ".jpg", ".gif", ".pdf"} or not path.is_file():
                continue
            words = set(re.findall(r"[a-z0-9]+", path.read_bytes().decode("utf-8", "ignore").lower()))
            with self.subTest(file=name):
                self.assertNotIn(CODENAME_SHA256, {hashlib.sha256(w.encode()).hexdigest() for w in words})

if __name__ == "__main__":
    unittest.main()
