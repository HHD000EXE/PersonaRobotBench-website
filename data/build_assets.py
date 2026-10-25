"""Rebuild website metadata and optimized static renders; no simulator required."""
from pathlib import Path
import argparse
import hashlib
import json
import sys

from PIL import Image

OUT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--benchmark-root", type=Path, default=OUT.parent,
                    help="Path to a full PersonaRobotBench checkout (requires repository access)")
ROOT = parser.parse_args().benchmark_root.resolve()
if not (ROOT / "scripts/task_registry.py").is_file():
    parser.error("Pass --benchmark-root /path/to/PersonaRobotBench; the website-only checkout has no task registry")
sys.path.insert(0, str(ROOT / "scripts"))
from task_registry import ALL_TASKS

REPO = "https://github.com/HHD000EXE/PersonaRobotBench/blob/main/"
CATEGORIES = {
    "Food & dining": {5,9,17,18,26,40,46,60,63,70,75,76,77,78,79,91,93,94,97,99},
    "Workspace": {1,3,14,16,20,25,30,33,34,37,38,39,42,45,49,50,51,52,53,54,55,56,59,61,65,74,82,83,84,85,86,87,89,100},
    "Assistance": {11,21,23,28,29,31,35,36,90,92,95,96,98},
    "Manipulation": {15,27,66,67,68,69},
    "Social & creative": {19,22,24,32},
}
assigned = set()
for values in CATEGORIES.values():
    assert not assigned & values
    assigned |= values
CATEGORIES["Household"] = set(range(1, 101)) - assigned


def description(persona):
    for field in ("preference_text", "description"):
        if persona.get(field):
            return persona[field]
    priority = persona.get("preferences", {}).get("priority")
    if priority:
        return priority[0].upper() + priority[1:] + "."
    return persona.get("name", "Persona configuration")


def main():
    if (OUT / "data/task-preview-provenance.json").exists():
        raise SystemExit("The complete preview catalog is already published. Follow README.md scene-update instructions; this bootstrap exporter would overwrite current previews and rollout metadata.")
    (OUT / "assets").mkdir(parents=True, exist_ok=True)
    provenance = []
    catalog = {item["task_id"]: item for item in json.loads((ROOT / "docs/task_catalog.json").read_text())["tasks"]}

    def asset(name, source, width=960, crop=None):
        source_path = ROOT / source
        with Image.open(source_path) as image:
            image = image.convert("RGB")
            original = list(image.size)
            box = (0, 0, image.width, image.height)
            if crop:
                box = tuple(round(c * v) for c, v in zip(crop, [image.width, image.height, image.width, image.height]))
                image = image.crop(box)
            if image.width > width:
                image = image.resize((width, round(image.height * width / image.width)), Image.Resampling.LANCZOS)
            destination = OUT / "assets" / name
            image.save(destination, "WEBP", quality=84, method=6)
            dimensions = list(image.size)
        provenance.append({
            "asset": "assets/" + name, "source": source,
            "sourceSha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
            "sourceDimensions": original, "cropPixels": list(box),
            "dimensions": dimensions, "bytes": destination.stat().st_size,
            "role": "Static initial-scene render. Not a rollout or evidence of task completion.",
        })
        return "assets/" + name

    tasks = []
    for number, alias, folder in ALL_TASKS:
        config = json.loads((ROOT / f"tasks/{folder}/config/task.json").read_text())
        personas = json.loads((ROOT / f"tasks/{folder}/config/personas.json").read_text())
        category = next(key for key, values in CATEGORIES.items() if number in values)
        task = {
            "id": number, "folder": folder,
            "title": config.get("title", catalog[number].get("package_title", catalog[number]["title"])),
            "instruction": config["instruction"], "personaCount": len(personas),
            "personaIds": list(personas), "category": category, "tags": [category],
            "personas": [{"id": key, "name": value.get("name", value.get("identity", "User " + key)),
                          "description": description(value), "preferences": value.get("preferences", {})}
                         for key, value in personas.items()],
            "sourceUrl": REPO + f"tasks/{folder}/README.md",
            "personaSourceUrl": REPO + f"tasks/{folder}/config/personas.json",
        }
        if number in (20, 21):
            task["statusNote"] = "Imported package; validation differences and incomplete validation are documented in the repository."
        tasks.append(task)
    assert [item["id"] for item in tasks] == list(range(1, 101))
    assert sum(item["personaCount"] for item in tasks) == 217
    by_id = {item["id"]: item for item in tasks}
    examples = []
    curated = [
        (18, "Beverage selection", "Sparkling water or orange juice?", "Object choice", "home_backgrounds/previews/4k/beverage_selection_initial.jpg", (0.16,0.28,0.88,1)),
        (51, "Stamp press", "A light touch or a sustained press?", "Force & duration", "tasks/stamp_press_operation/previews/usd_initial.png", None),
        (68, "Lifted transfer", "Carry it or slide it?", "Motion strategy", "home_backgrounds/previews/4k/lifted_transfer_initial.jpg", (0.16,0.28,0.88,1)),
        (87, "Speaker volume", "A quiet 30% or a louder 70%?", "Personal settings", "tasks/painter_speaker_volume/previews/isaac_initial.png", None),
        (32, "Greeting", "A wave, a salute, or a hand over the heart?", "Social preference", "home_backgrounds/previews/4k/greeting_initial.jpg", (0.16,0.28,0.88,1)),
        (91, "Cabinet closing", "The same destination. A different motion.", "Process preference", "home_backgrounds/previews/4k/cabinet_closing_initial.jpg", (0.16,0.28,0.88,1)),
    ]
    for number, title, contrast, dimension, path, crop in curated:
        poster = asset(f"task-{number:03}.webp", path, crop=crop)
        example = dict(by_id[number])
        example.update({"shortTitle": title, "contrast": contrast, "dimension": dimension, "poster": poster,
                        "posterAlt": f"Static initial simulation scene for {title.lower()}.",
                        "video": None, "videoLabel": "Simulation rollout · coming soon", "imageKind": "static_initial_scene"})
        example["personas"] = [dict(persona, video=None) for persona in example["personas"]]
        examples.append(example)

    asset("hero-scene.webp", "home_backgrounds/previews/4k/shared_desk_initial.jpg", 1600, (0.12,0.15,0.96,0.99))
    asset("scene-bookshelf.webp", "home_backgrounds/previews/4k/book_organization_initial.jpg", 960, (0.16,0.28,0.88,1))
    asset("scene-workbench.webp", "tasks/masonry_workbench/previews/isaac_initial.png", 960)
    notes = [
        "Category grouping and short example headings are editorial. Native task titles, instructions and preference_text are preserved.",
        "All images are existing static initial-scene renders, optimized to WebP. No rollout videos are included.",
        "Case labels A/B/C/D are local to each task; they do not describe one shared person across the benchmark.",
    ]
    manifest = {"schemaVersion": 1, "sourceRepo": "HHD000EXE/PersonaRobotBench",
                "dataSources": ["scripts/task_registry.py", "tasks/*/config/task.json", "tasks/*/config/personas.json"],
                "scope": {"tasks": 100, "personaCases": 217}, "notes": notes, "assets": provenance}
    previous_manifest = OUT / "data" / "asset-provenance.json"
    if previous_manifest.exists():
        font_records = json.loads(previous_manifest.read_text()).get("fonts")
        if font_records:
            manifest["fonts"] = font_records
    for name, value in (("tasks.json", tasks), ("examples.json", examples), ("asset-provenance.json", manifest)):
        (OUT / "data" / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"tasks": len(tasks), "personas": sum(item["personaCount"] for item in tasks),
                      "assets": [{key: item[key] for key in ("asset", "dimensions", "bytes")} for item in provenance],
                      "totalImageBytes": sum(item["bytes"] for item in provenance)}, indent=2))


if __name__ == "__main__":
    main()
