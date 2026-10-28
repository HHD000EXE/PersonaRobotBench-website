#!/usr/bin/env python3
"""Offline release-data and local-asset checks for the benchmark website."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from collections import defaultdict
from fractions import Fraction
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


def verify_previews(root: Path, tasks: list[dict]) -> int:
    receipt = json.loads((root / "data/task-preview-provenance.json").read_text())
    assert receipt["schema"] == "personarobotbench.website-task-previews/1"
    assert re.fullmatch(r"[0-9a-f]{40}", receipt["sourceRevision"])
    records = {item["taskId"]: item for item in receipt["previews"]}
    assert len(records) == len(receipt["previews"]) == 100, "Expected one preview receipt per task"
    for task in tasks:
        preview, record = task["preview"], records[task["id"]]
        expected = f"assets/task-scenes/task-{task['id']:03}.webp"
        assert preview["image"] == record["asset"] == expected, task["id"]
        assert preview["kind"] == "static_initial_scene" and preview["alt"], task["id"]
        assert preview["provenance"] == "data/task-preview-provenance.json", task["id"]
        assert record["folder"] == task["folder"] and record["sourceCurrent"], task["id"]
        assert record["sourceLayers"] and record["captureScene"], task["id"]
        assert all(re.fullmatch(r"[0-9a-f]{64}", value) for value in record["sourceLayers"].values())
        image = (root / expected).read_bytes()
        assert image[:4] == b"RIFF" and image[8:12] == b"WEBP", expected
        assert int.from_bytes(image[4:8], "little") + 8 == len(image), expected
        assert hashlib.sha256(image).hexdigest() == record["sha256"], expected
        assert len(image) == record["bytes"], expected
        assert [preview["width"], preview["height"]] == record["dimensions"], expected
    return len(records)


def verify_leaderboard(root: Path, tasks: list[dict]) -> int:
    data = json.loads((root / "data/leaderboard.json").read_text())
    evidence = json.loads((root / "data/leaderboard-results.json").read_text())
    assert data["schema"] == "personarobotbench.website-leaderboard/1"
    assert evidence["schema"] == "personarobotbench.website-leaderboard-results/1"
    assert evidence["tasks"] == 100 and evidence["personaCases"] == 217
    assert data["provenance"]["paperCommit"] == evidence["source"]["paperCommit"]
    assert data["provenance"]["resultsUrl"] == "data/leaderboard-results.json"
    rows = [row for board in data["boards"] for row in board["rows"]]
    ids = [row["id"] for row in rows]
    assert len(ids) == len(set(ids)) and rows, "Duplicate or missing policy configuration"
    for board in data["boards"]:
        assert board["title"] and board["metric"] and board["description"]
        for row in board["rows"]:
            score = row["scorePercent"]
            assert score is None or (type(score) in (int, float) and 0 <= score <= 100), row["id"]
            assert row["policy"] and row["protocol"] and row["coverage"], row["id"]
    expected_cases = {(task["id"], persona) for task in tasks for persona in task["personaIds"]}
    configs = evidence["configurations"]
    assert {row["id"] for row in configs} == set(ids), "Evidence and display policy IDs differ"
    for config in configs:
        if config["status"] == "pending":
            assert config["taskBalancedSuccessPercent"] is None
            assert next(row for row in rows if row["id"] == config["id"])["scorePercent"] is None
            continue
        if config["status"] == "paper_snapshot":
            # This figure-only point has no matching trial-count bundle. Bind
            # it to the inspected paper asset rather than inventing counts.
            assert config["id"] == "gemini4"
            display = next(row for row in rows if row["id"] == config["id"])
            assert config["taskBalancedSuccessPercent"] == display["scorePercent"] == 30.4
            assert config["sourceCommit"] == data["provenance"]["paperCommit"] == "e2293166876ea2410f0d3a82fe5513e5df71feaf"
            assert config["sourceFigure"] == data["provenance"]["paperFigure"] == "CoRL Late Breaking Results/figures/policy_leaderboard.pdf"
            assert config["sourceSha256"] == data["provenance"]["paperFigureSha256"] == evidence["source"]["paperFigureSha256"] == "faed740590b96505c721989c1bdba6c2fe48e18a3727551c066a96123250a63e"
            assert all(config[key] is None for key in ("taskBalancedRateExact", "strictSuccesses", "scored", "observedPersonas", "ci95Percent"))
            assert config["personaCounts"] == [] and config["currentTrialCountsVerified"] is False
            assert config["planned"] == 2170 and config["trialsPerPersona"] == 10
            assert config["reasoningEffort"] == "medium"
            continue
        assert config["status"] in {"verified_strict", "archived_strict"}, "Unknown leaderboard evidence status"
        counts = config["personaCounts"]
        assert len(counts) == len(expected_cases) == 217
        assert {(item["task"], item["persona"]) for item in counts} == expected_cases
        by_task: dict[int, list[Fraction]] = defaultdict(list)
        totals = dict.fromkeys(("strictSuccesses", "scored", "planned"), 0)
        for item in counts:
            assert all(type(item[key]) is int for key in totals)
            assert 0 <= item["strictSuccesses"] <= item["scored"] <= item["planned"]
            for key in totals:
                totals[key] += item[key]
            if item["scored"]:
                by_task[item["task"]].append(Fraction(item["strictSuccesses"], item["scored"]))
        assert len(by_task) == 100, "Archived configuration does not cover all tasks"
        rate = sum(sum(values, Fraction()) / len(values) for values in by_task.values()) / 100
        assert rate == Fraction(config["taskBalancedRateExact"]), config["id"]
        assert abs(float(rate) * 100 - config["taskBalancedSuccessPercent"]) < 1e-10
        assert totals["strictSuccesses"] == config["strictSuccesses"]
        assert totals["scored"] == config["scored"] and totals["planned"] == config["planned"]
    # Displayed points follow the paper; archived trial evidence has its own
    # exact rates. Do not silently substitute one for the other.
    return len(rows)


def verify_recorded_pose_receipt(item: dict, source: dict, recording: dict) -> None:
    """Check model-demo evidence and the measured-pose playback contract."""
    assert source["kind"] == "model_rollout" and recording["kind"] == "model"
    for key in ("model", "reasoningEffort"):
        assert item[key] == source[key] == recording[key] and item[key], key
    scores = item["nativeScores"]
    assert all(scores[key] is True for key in
               ("physics", "personalized_success", "process_valid", "faithful", "strict_success"))
    assert scores["evaluation_fixture"] is False and scores["timeout"] is False
    assert scores["controller_error"] is None and scores["process_preference_success"] is not False
    assert item["nativeRescorePassed"] and item["sourceOriginalsUnchanged"]
    assert item["completeRecordedEpisode"] and item["sourceReportedSuccess"]
    assert item["sourceArtifactsGitTracked"] is False, "Locally retained source artifacts must not be presented as Git-tracked"
    assert item["physicsStepsDuringRender"] == item["newModelCallsDuringRender"] == 0
    assert item["modelObservationVideo"] is False
    assert type(item["inferenceCalls"]) is int and item["inferenceCalls"] > 0
    limit = item["simulationTimeLimitSeconds"]
    assert limit == source["simulationTimeLimitSeconds"] and 0 < item["simulatedSeconds"] <= limit
    fps, sample_hz, record_hz = item["fps"], item["renderSampleHz"], item["recordedStateHz"]
    assert all(type(value) in (int, float) and math.isfinite(value) and value > 0
               for value in (fps, sample_hz, record_hz, limit))
    assert fps == source["outputFrameRateHz"] and sample_hz == source["renderSampleHz"]
    assert record_hz == source["recordedStateHz"]
    stride = round(record_hz / sample_hz)
    assert stride > 0 and abs(stride * sample_hz - record_hz) < 1e-9
    last_row = round(item["simulatedSeconds"] * record_hz)
    expected_samples = last_row // stride + 1 + int(bool(last_row % stride))
    assert item["renderedSamples"] == expected_samples, "Measured-pose sample count differs"
    assert abs(item["frames"] / fps - item["durationSeconds"]) < 1e-6, "Video clock differs from frame count"
    assert abs(item["durationSeconds"] - item["simulatedSeconds"] - 1 / fps) < 1e-6, "Final-frame hold differs"
    for key in ("sourceEpisodeSha256", "sourceReportSha256", "sourceStatusSha256",
                "sourceFrameManifestSha256", "timeLimitVariantSha256"):
        assert re.fullmatch(r"[0-9a-f]{64}", item[key]), key
    assert item["sourceModelReceiptHashes"] and all(
        re.fullmatch(r"[0-9a-f]{64}", value) for value in item["sourceModelReceiptHashes"].values())
    def public_values(value):
        if isinstance(value, dict):
            for key, child in value.items():
                public_values(key)
                public_values(child)
        elif isinstance(value, list):
            for child in value:
                public_values(child)
        elif isinstance(value, str):
            assert not value.startswith(("/home/", "/Users/", "file:", "http://127.0.0.1", "http://localhost")), "Local path leaked into public evidence"
            assert not re.match(r"^[A-Za-z]:[\\/]", value), "Local path leaked into public evidence"
    public_values(item)
    public_values(source)


def verify_display_gait_receipt(item: dict, source: dict, recording: dict,
                                originals: dict, sources: dict) -> None:
    """Verify a display-only leg render against its unchanged native recording."""
    assert item["schema"] == "personarobotbench.display-gait-render/1"
    assert item["captureMode"] == "display_gait_replay"
    assert item["source"] == recording["source"] == "astra-high-display-gait"
    assert source["kind"] == "model_rollout" and recording["kind"] == "model"
    assert recording["playback"] == "Recorded task trajectory with display-only walking animation; physics not rerun."
    key = (item["taskId"], item["persona"])
    original = originals[key]
    parent = item["originalRecording"]
    canonical = json.dumps(original, sort_keys=True, separators=(",", ":"),
                           ensure_ascii=False, allow_nan=False).encode()
    assert parent["recordSha256"] == hashlib.sha256(canonical).hexdigest(), "Original recording binding differs"
    assert parent["video"] == original["video"] and parent["source"] == original["source"]
    assert original["source"] in source["parentSources"]
    assert original["captureMode"] == "recorded_pose_replay"
    verify_recorded_pose_receipt(original, sources[original["source"]], {
        "kind": "model", "model": original["model"], "reasoningEffort": original["reasoningEffort"]})
    for field in ("sourceEpisodeSha256", "sourceReportSha256", "sourceStatusSha256"):
        assert parent[field] == original[field], field
    assert parent["nativeEvaluationReusedUnchanged"] is True
    assert parent["animatedTrajectoryScored"] is False
    assert "nativeScores" not in item and "nativeRescorePassed" not in item, "Animation must not impersonate a native trial"
    for field in ("model", "reasoningEffort"):
        assert item[field] == source[field] == recording[field] == original[field]
    assert item["recordedTaskId"] == original["recordedTaskId"] == recording["recordedTaskId"]
    assert item["video"] != original["video"] and item["poster"] != original["poster"]
    assert item["completeRecordedEpisode"] is True and item["modelObservationVideo"] is False
    assert item["newModelCallsDuringRender"] == item["physicsStepsDuringRender"] == 0
    assert item["frames"] == original["frames"] and item["fps"] == original["fps"]
    assert abs(item["durationSeconds"] - original["durationSeconds"]) < 1e-6
    assert abs(item["durationSeconds"] - item["frames"] / item["fps"]) < 1e-6
    assert item["renderedSamples"] == original["renderedSamples"]
    assert item["renderSampleHz"] == original["renderSampleHz"]
    preserved = item["measuredStatePreserved"]
    assert set(preserved) == {"basePoses", "nonLegJointAngles", "objectPoses", "passiveFixtures"}
    assert all(value is True for value in preserved.values())
    gait = item["displayGait"]
    legs = {f"{side}_{joint}_joint" for side in ("left", "right")
            for joint in ("hip_pitch", "hip_roll", "hip_yaw", "knee", "ankle_pitch", "ankle_roll")}
    assert len(gait["animatedJointNames"]) == 12 and set(gait["animatedJointNames"]) == legs
    assert gait["displayOnly"] is True and gait["dynamicallySimulatedWalking"] is False
    assert gait["balanceControllerEvaluated"] is False
    assert gait["chunkIndependentPhase"] is True
    camera = item["cameraPresentation"]
    assert camera["schema"] == "prb.static_walking_camera_presentation/1"
    assert camera["task_id"] == item["taskId"] and camera["per_frame_tracking"] is False
    assert 1 <= camera["fov_widen_factor"] <= 3
    assert all(camera[key] is True for key in ("session_layer_only", "camera_position_and_orientation_unchanged",
                                              "same_for_all_task_personas", "source_usd_unchanged"))
    assert camera["settings_sha256"] == item["rendererSourceHashes"]["camera_presentation.json"]
    for field in ("gaitCacheSha256", "gaitImplementationSha256", "renderFreezeManifestSha256",
                  "sourceExportReceiptSha256", "sourceFrameManifestSha256"):
        assert re.fullmatch(r"[0-9a-f]{64}", item[field]), field
    assert item["rendererSourceHashes"] and all(
        re.fullmatch(r"[0-9a-f]{64}", value) for value in item["rendererSourceHashes"].values())
    def public_values(value):
        if isinstance(value, dict):
            for key, child in value.items():
                public_values(key)
                public_values(child)
        elif isinstance(value, list):
            for child in value:
                public_values(child)
        elif isinstance(value, str):
            assert not value.startswith(("/home/", "/Users/", "file:", "http://127.0.0.1", "http://localhost")), "Private path in display evidence"
            assert not re.match(r"^[A-Za-z]:[\\/]", value), "Private path in display evidence"
    public_values(item)
    public_values(source)


def verify_background_repair_receipt(item: dict, source: dict, recording: dict,
                                     originals: dict, sources: dict, variants: dict) -> None:
    """Verify the reviewed scenery repair without inventing a new policy trial."""
    source_id = "astra-high-background-repair"
    upstream_id = "astra-high-display-gait"
    playback = "Recorded task trajectory with display-only walking animation and repaired decorative background; physics not rerun."
    assert item["source"] == recording["source"] == source_id
    assert source["upstreamSource"] == upstream_id
    assert source["playback"] == recording["playback"] == playback
    assert item["taskId"] in {25, 30, 33, 40} and item["persona"] in {"A", "B"}
    assert all(item[key] is True for key in ("backgroundOnlyRepair", "upstreamA2GaitReusedUnchanged",
                                            "nativeEvaluationAppliesToOriginalRecording"))
    # The original native/gait validator remains unchanged. Normalize only the
    # two presentation identifiers after checking the new source above.
    normalized_item = dict(item, source=upstream_id)
    normalized_recording = dict(recording, source=upstream_id,
        playback="Recorded task trajectory with display-only walking animation; physics not rerun.")
    verify_display_gait_receipt(normalized_item, source, normalized_recording, originals, sources)

    parent = item["priorWalkingRender"]
    assert set(parent) == {"video", "sha256", "recordSha256"}
    prior = variants[(item["taskId"], item["persona"], parent["video"])]
    assert prior["source"] == upstream_id and prior["sha256"] == parent["sha256"]
    canonical = json.dumps(prior, sort_keys=True, separators=(",", ":"),
                           ensure_ascii=False, allow_nan=False).encode()
    assert hashlib.sha256(canonical).hexdigest() == parent["recordSha256"], "Prior walking-render binding differs"
    assert item["video"] != prior["video"] and item["poster"] != prior["poster"]
    for key in ("originalRecording", "model", "reasoningEffort", "recordedTaskId", "frames", "fps",
                "durationSeconds", "renderedSamples", "renderSampleHz", "measuredStatePreserved",
                "displayGait", "gaitCacheSha256", "gaitImplementationSha256", "gaitQualityReviewSha256",
                "cameraPresentation", "sceneRevision", "sceneSha256", "sceneLayerHashes", "sceneTextureHashes"):
        assert item[key] == prior[key], "Background repair changed recorded motion, gait, camera or source: " + key
    approved_capture_dependencies = {'checkpoint_pose_frames.py': '6c60db6b430dea7c408f5d825060ca56c896e87e9aca8ab47524324f66286a09', 'demo_render_common.py': '6735362968196fe7069d7b997fd0d034652f3c81c0eef0b0d52f298cc36f219c', 'storm_capture.py': 'dae6a17d532316f8cfddefdae33a0b315547a7215591bfeaf3fbe2d13f1a19b3', 'recorded_visual_state.py': '386d1294fb7d95137785214b7efcf15004f55f6a4072a313cce163fd67fd4deb', 'origin_evidence.py': '803d6f033f89fa5aa168a2432ad36e62ebd1b067cb057780dbb2b7d787fbd08b', 'replay_render_minimal.kit': 'a5dc7cc865cacb8ebf3cc1b1125bf18195a3ae895a22f8a92086a1dcd38aa9f5', 'prepare_gait.py': '1a2af392d5cf655a3deb64f887bef303ffb9d51241f5c437a9281d9206a1ab43', 'display_gait.py': '610e80985acd01a14ed8a42178e878ff6859ff02c79d33ea6f2069dc955e077b', 'camera_presentation.py': '3dbc562ad890bda509facc30e8229d63a14397aa523fe028f9533d9aef522a45', 'camera_presentation.json': 'db2d354c2a9678e736f3a9287ae7e9a9a6cb0b74d2344087ceb0f21d703e314f', 'background_presentation.py': '247162f382b46ec49df70955e027240027c0089413c775a12aa2451413e10e38', 'background_presentation.json': 'ce817d1a1acabf4f8ee9bc5958a9adc418a6a4b9958e77e08f675aa0d5288ad7', 'upstream_identity.json': 'c5a023a15662fd3c4b22a74993b23b058295c4e43f281e83c12328bf2112470c'}
    approved_freeze = '1a0f542048a3144e10e43ffa05ebaa9a7876f87e6eaa4b5de15e7d3fa2564c41'
    approved_policy = 'ce817d1a1acabf4f8ee9bc5958a9adc418a6a4b9958e77e08f675aa0d5288ad7'
    assert item["rendererSourceHashes"] == source["captureDependencies"] == approved_capture_dependencies
    assert item["renderFreezeManifestSha256"] == source["renderFreezeManifestSha256"] == approved_freeze
    background = item["backgroundPresentation"]
    assert background["schema"] == "prb.background_presentation/1"
    assert background["task_id"] == item["taskId"]
    assert background["policy_sha256"] == source["backgroundPolicySha256"] == approved_policy
    assert background["policy_sha256"] == item["rendererSourceHashes"]["background_presentation.json"]
    assert all(background[key] is True for key in ("session_layer_only", "display_only", "source_layers_unchanged",
                                                  "recorded_task_motion_unchanged", "approved_A2_gait_unchanged"))
    assert background["physics_steps"] == background["new_model_calls"] == 0
    presentation = item["renderPresentation"]
    assert presentation["render_revision"] == "background-repair-R1"
    assert presentation["physics_steps"] == presentation["new_model_calls"] == 0

    def vector(value, count):
        assert isinstance(value, list) and len(value) == count
        assert all(type(number) in (int, float) and math.isfinite(number) for number in value)
        return value

    def matrix(value):
        assert isinstance(value, list) and len(value) == 4
        for row in value:
            vector(row, 4)
        assert value[3] == [0, 0, 0, 1]
        return value

    def bounds(value):
        assert isinstance(value, list) and len(value) == 2
        low, high = (vector(row, 3) for row in value)
        assert all(a <= b for a, b in zip(low, high))
        return low, high

    actions = background["actions"]
    assert isinstance(actions, list) and actions
    if item["taskId"] in {25, 30, 33}:
        assert len(actions) == 1
        action = actions[0]
        assert action["prim"] == "/World/TaskContext" and action["kind"] == "hide"
        assert action["source_visibility"] == "inherited" and action["render_visibility"] == "invisible"
        matrix(action["source_world_transform"])
        bounds(action["source_world_bounds"])
    else:
        groups = [
            (["KitchenBaseBody", "KitchenBaseTop", "KitchenBaseDrawer0", "KitchenBasePull0", "KitchenBaseDrawer1",
              "KitchenBasePull1", "KitchenBaseFoot0", "KitchenBaseFoot1"], [-0.69, -0.92, 0], [-1.56, 1.17, 0], 90),
            (["KitchenUpperBody", "KitchenUpperDoor0", "KitchenUpperPull0", "KitchenUpperDoor2", "KitchenUpperPull2"],
             [-0.79, -1.02, 0], [-1.56, 1.27, 0], 90),
            (["KitchenPlantPot"] + ["KitchenPlantLeaf" + str(i) for i in range(7)],
             [-0.69, -0.92, -0.0705], [-1.56, 1.17, 0], 90),
            (["DiningSideboardBody", "DiningSideboardTop", "DiningSideboardDrawer0", "DiningSideboardPull0",
              "DiningSideboardDrawer1", "DiningSideboardPull1", "DiningSideboardFoot0", "DiningSideboardFoot1"]
             + ["StorageCanister" + suffix + str(i) for i in range(3) for suffix in ("", "Lid")]
             + ["DiningPrintFrame", "DiningPrintMat", "DiningPrintArt", "DiningPrintArtStripe"],
             [0.5, 0, 0], [0, 0, 0], 0),
        ]
        expected = {"/World/HomeSet/" + name: (delta, pivot, angle)
                    for names, delta, pivot, angle in groups for name in names}
        assert len(actions) == len(expected) == 39
        assert len({action["prim"] for action in actions}) == 39
        assert {action["prim"] for action in actions} == set(expected), "Repair edits nondecorative or unexpected geometry"
        for action in actions:
            assert action["kind"] == "rigid_transform"
            delta, pivot, angle = expected[action["prim"]]
            assert action["translation_world_m"] == delta
            assert action["pivot_world_m"] == pivot
            assert action["rotation_world_z_degrees"] == angle
            before, after = matrix(action["source_world_transform"]), matrix(action["render_world_transform"])
            rotation = ((0, -1, 0), (1, 0, 0), (0, 0, 1)) if angle == 90 else ((1, 0, 0), (0, 1, 0), (0, 0, 1))
            for row in range(3):
                for column in range(3):
                    calculated = sum(rotation[row][k] * before[k][column] for k in range(3))
                    assert math.isclose(after[row][column], calculated, abs_tol=3e-7, rel_tol=0)
                calculated = sum(rotation[row][k] * (before[k][3] - pivot[k]) for k in range(3)) + pivot[row] + delta[row]
                assert math.isclose(after[row][3], calculated, abs_tol=3e-7, rel_tol=0)
            bounds(action["source_world_bounds"])
            low, high = bounds(action["render_world_bounds"])
            assert low[0] >= -2.55 - 1e-6 and high[0] <= 2.55 + 1e-6, "Decor leaves the room"


def verify_render_variant(item: dict, source: dict, recording: dict,
                          originals: dict, sources: dict, variants: dict) -> None:
    if item["source"] == "astra-high-display-gait":
        verify_display_gait_receipt(item, source, recording, originals, sources)
    elif item["source"] == "astra-high-background-repair":
        verify_background_repair_receipt(item, source, recording, originals, sources, variants)
    else:
        raise AssertionError("Unknown display-render source: " + item["source"])



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
    variants = []
    if provenance_path.exists():
        provenance = json.loads(provenance_path.read_text())
        assert provenance["schema"] == "personarobotbench.website-rollouts/1", "Unknown rollout provenance schema"
        recordings = provenance["recordings"]
        records = {(item["taskId"], item["persona"]): item for item in recordings}
        assert len(records) == len(recordings), "Duplicate rollout receipt"
        variants = provenance.get("renderVariants", [])
        variant_keys = set()
        media_records = {(item["taskId"], item["persona"], item["video"]): item for item in recordings}
        for item in variants:
            key = (item["taskId"], item["persona"], item["video"])
            assert key not in media_records and (item["taskId"], item["persona"]) in records, "Duplicate or unbound display variant"
            assert item.get("captureMode") == "display_gait_replay", "Unknown display variant capture mode"
            media_records[key] = item
            variant_keys.add(key)
        featured_variants = set()
        expected = {(task_id, persona) for task_id in (18, 51, 68, 87) for persona in ("A", "B")}
        assert expected <= records.keys(), "Missing featured A/B recording receipt"
        # Every receipt names the source that recorded it (a model rollout or a
        # scripted demonstration); the page labels each pair from that source.
        sources = provenance.get("sources", {})
        for item in recordings:
            assert item.get("source") in sources, f"Unknown recording source: {item.get('source')}"
            assert sources[item["source"]].get("label") and sources[item["source"]].get("kind"), item["source"]

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

        def verify_media_assets(receipt: dict) -> None:
            """Check published and archived media against their immutable receipts."""
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

        for example in examples:
            if not example.get("recording"):
                continue
            for persona in example["personas"]:
                if not persona.get("video"):
                    continue
                media_key = (example["id"], persona["id"], persona["video"])
                receipt = media_records[media_key]
                if media_key in variant_keys:
                    verify_render_variant(receipt, sources[receipt["source"]], example["recording"], records, sources, media_records)
                    featured_variants.add(media_key)
                elif receipt.get("captureMode") == "recorded_pose_replay":
                    verify_recorded_pose_receipt(receipt, sources[receipt["source"]], example["recording"])
                assert receipt["video"] == persona["video"], "Video URL differs from receipt"
                assert receipt["poster"] == persona["videoPoster"], "Poster URL differs from receipt"
                assert receipt["recordedTaskId"] == example["recording"]["recordedTaskId"], "Historical task ID differs"
                assert receipt["source"] == example["recording"].get("source"), "Recording source differs from receipt"
                assert example["recording"].get("label") == sources[receipt["source"]]["label"], "Recording label differs from its source"
                assert abs(receipt["durationSeconds"] - persona["videoDurationSeconds"]) < 0.001, "Duration differs"
                verify_media_assets(receipt)
        # Gallery curation does not discard the archived render evidence. Every
        # display variant still passes its native binding and exact media checks.
        for media_key in variant_keys - featured_variants:
            receipt = media_records[media_key]
            source = sources[receipt["source"]]
            original = records[(receipt["taskId"], receipt["persona"])]
            recording = {
                "source": receipt["source"], "kind": "model",
                "model": source["model"], "reasoningEffort": source["reasoningEffort"],
                "recordedTaskId": original["recordedTaskId"],
                "playback": source["playback"],
            }
            verify_render_variant(receipt, source, recording, records, sources, media_records)
            verify_media_assets(receipt)
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
    preview_count = verify_previews(root, tasks)
    policy_count = verify_leaderboard(root, tasks)
    return {"status": "passed", "tasks": len(tasks), "persona_cases": 217,
            "task_previews": preview_count, "policy_configurations": policy_count,
            "examples": len(examples), "recordings": len(recordings), "render_variants": len(variants),
            "local_assets_checked": len(checked_assets), "unique_html_ids": len(page.ids)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    print(json.dumps(verify(args.root), indent=2))
