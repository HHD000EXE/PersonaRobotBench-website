# PersonaRobotBench website

The public research website for the **100-task / 217-persona** benchmark.

- **Live website:** https://hhd000exe.github.io/PersonaRobotBench-website/
- **Contribute:** fork this repository and open a pull request targeting **`website`**.
- **Contribution guide:** [CONTRIBUTING.md](CONTRIBUTING.md)
The benchmark repositories are currently private. The public site does not link to their code or documentation.

This public repository contains the website, its complete task catalog,
100 task-specific scene previews, and the policy leaderboard. The homepage
features 27 curated task rollout groups (57 persona videos), with Task 1 shown first.
Twenty-five featured Astra high videos use display-only walking animation along
their unchanged recorded base paths; each affected player links the original evidence.
Astra inference rollouts and scripted reference demonstrations retain their source labels.
Unfeatured recordings remain archived; all 100 tasks remain in the task gallery.
Moving-base demonstrations must show leg stepping; stationary fixed-base
manipulation remains eligible.
Controller sources are recorded in the provenance data. At 1×, videos follow
simulation time, with Astra inference waits omitted. These selected
demonstrations are separate from the benchmark success-rate evaluations.
The new high-reasoning demos use a 180-second simulation allowance and native
success checks for the original episodes. Base, object and upper-body states
are sampled at 15 Hz and held at 30 fps; display-only leg animation is identified
below each affected player. Provenance describes the privileged skill interface,
assisted control, renderer, original evidence and timing.
See [recording provenance](data/rollout-provenance.json) for source hashes,
recording context and the historical Task 110 → Task 51 mapping.

The provenance manifest retains all 84 original recording receipts and media,
plus 39 derived walking-render receipts with separate video/poster paths. The
added leg motion is animation, not physically simulated or rescored locomotion.
Native task outcomes and leaderboard results refer to the original trajectories.

## Local preview

~~~bash
git clone --branch website https://github.com/HHD000EXE/PersonaRobotBench-website.git
cd PersonaRobotBench-website
python3 -m http.server 8080
~~~

Open http://localhost:8080. Use HTTP because the task explorer loads local JSON.
No API key, GPU, simulator, or production npm dependencies are needed.

## Check and build

~~~bash
python3 verify.py
python3 build.py
python3 verify.py --root dist
~~~

The static output is `dist/`. Optional interaction checks need Node.js 24:

~~~bash
npm ci
npm test
~~~

Pull requests run source checks, interaction tests, and a verified static build.
Merges to this repository's `website` branch deploy `dist/` to GitHub Pages.
Forks and pull requests run checks without publishing. The workflow uses GitHub's
built-in token; contributors do not configure deployment credentials.

## Add or replace rollout videos

Edit `data/examples.json`. Every example with a `recording` block gets a thumbnail
tile in the rollout section, in file order, labelled by its `tabLabel`. Set each
persona's `video` field, for example:

~~~json
{
  "id": "A",
  "description": "I prefer sugar-free sparkling water.",
  "video": "assets/rollouts/task018-A.mp4",
  "videoPoster": "assets/rollouts/task018-A.webp",
  "videoDurationSeconds": 96.93333333333334
}
~~~

1. Add a browser-compatible MP4/WebM to `assets/rollouts/`, or use an HTTPS video URL.
2. Set each authored persona's `personas[].video`, including C or D when present.
3. Set `videoPoster` to a real frame from that recording, update its duration,
   and include captions for speech. Keep the static scene poster separate.
4. Set the example's `recording`: `source` (a key of `sources` in
   `data/rollout-provenance.json`), `label` (must equal that source's metadata
   label), `kind` (`model` for a policy rollout, `scripted` for a scripted
   controller or expert), `playback` (the note under the videos) and `recordedTaskId`.
5. Add one receipt per persona to `data/rollout-provenance.json` with the same
   `source`, the recording facts and the video and poster hashes. Never label a
   scripted demonstration as a model rollout.
6. Run the checks above and open a PR against `website`.

The rollout section plays all available personas on one simulation clock (play, scrub,
1×/2×/4×/8×); the shorter recording holds its last frame. Use the ±5 s buttons
or the arrow keys while the scrubber has focus to seek all videos. Each video
keeps its own native controls.

Missing videos keep their placeholders. Playback uses `personas[].video`, not
the reserved top-level `video` field. Host large recordings externally to keep
this source repository small.

## Where to edit

| File | Purpose |
| --- | --- |
| `index.html` | Page copy, public sections and navigation |
| `styles.css` | Responsive layout and typography |
| `assets/persona-concept.svg`, `assets/persona-concept-mobile.svg` | User profile → preference inference → robot action concept figure, with a separate phone layout |
| `tools/build_concept_figure.py` | Rebuild both concept figures from a symmetric grid and the shared Task 1 initial layout |
| `app.js` | Search, category filters, task details, tabs and video playback |
| `data/tasks.json` | All 100 task descriptions and 217 task-local persona cases |
| `assets/task-scenes/` | One current initial-scene preview for every task |
| `data/task-preview-provenance.json` | Per-task source revision, scene layers, textures, renderer and image hashes |
| `data/leaderboard.json` | Paper leaderboard points, policy settings, metric and coverage |
| `data/leaderboard-results.json` | Downloadable result provenance and archived per-persona counts |
| `data/examples.json` | Curated examples, posters and rollout video URLs |
| `data/rollout-provenance.json` | Recording sources, hashes, timing and historical task numbering |
| `data/asset-provenance.json` | Original image sources, hashes and font sources |
| `assets/fonts/` | Self-hosted fonts with their OFL license notices |

Task instructions and persona descriptions follow the benchmark configurations;
category grouping and short example headings are editorial. Images are static
scene illustrations, not evidence of policy success. Do not publish an inferred
success rate or label a partial attempt as a completed rollout.

The catalog and optimized images are checked in. For a scene update, render the
current benchmark's composed initial USD scene with its own background and
authored camera. Update `assets/task-scenes/task-NNN.webp`, the matching task's
`preview` fields, and its receipt in `data/task-preview-provenance.json` together.
Record all composed scene layers and texture hashes; do not reuse a historical
capture after those sources change. Keep rollout frame posters separate from
initial-scene illustrations. The original `data/build_assets.py` bootstrap
exporter refuses to overwrite this complete preview catalog.

Normal website edits and deployments do not need the private benchmark checkout.

To edit the overview concept, update `tools/build_concept_figure.py` and run
`python3 tools/build_concept_figure.py`. Both SVG layouts share one grid-based
source; all Before views reuse the same initial-desk symbol. No simulator or
additional Python packages are needed.

The overview appears immediately after the title and release statistics, before
the leaderboard. Its Task 1 environment and optional 3D viewer share one panel
with the concept figure. The illustrated profile contains only dominant hand;
identical instructions enter one policy that infers a computer-work preference,
plans and executes. Object labels are embedded in the desk views.
Small robot nodes sit on the Before-to-After transitions. A shared planner
connection reaches a central junction and branches to the two examples. Both
robot icons represent executions of the same G1. Instructions are single-line;
the phone layout shares one instruction row inside the user-input block.
The broader preference dimensions are described in the figure caption.

## Policy leaderboard

The leaderboard follows the latest paper snapshot and displays each evaluated
policy configuration separately. Its metric is task-balanced strict success:
average scored trials within each observed persona, then personas within each
task, then all 100 tasks equally. Infrastructure outcomes remain unscored.
Coverage and trial budgets are recorded in the result data because the
configurations use different protocols. Gemini 4 uses the current CoRL paper
figure (30.4%); its current per-trial counts are not included in this archive.

Update `data/leaderboard.json` and `data/leaderboard-results.json` together when
new results arrive. Preserve the paper revision, metric, settings, scored and
planned coverage, and raw source hashes. The downloadable archive includes
per-persona counts and exact rational rates for reproducing the archived
assessments; paper points and archived assessments retain their own provenance.
`verify.py` checks every archived count and recomputes its task-balanced mean.

## Branch ownership

`HHD000EXE/PersonaRobotBench-website:website` is the public contribution and
deployment source. The benchmark repository `HHD000EXE/PersonaRobotBench` also
has a `website` branch. It is synchronized explicitly with the public website
source; there is no automatic cross-repository mirror. Do not merge the website
branch into benchmark `main`.

This website has no backend, analytics, model calls or simulator processes.
Keep API keys, credentials, local outputs and runtime files outside this repository.


## Interactive initial scene

Scene 001 includes an opt-in 3D view: select **Explore in 3D**, drag to orbit,
scroll or pinch to zoom, and select **Reset view** to restore the camera.
**Show image** restores the original render. The original image remains available
without WebGL or if loading fails. The model and lighting load only on request.

The initial USD scene is converted to glTF with original object transforms,
source-derived PBR materials, compressed diffuse textures, baked ambient
occlusion and the source HDR environment. It is a static visualization, not an
Isaac Sim execution or a task score. See `assets/models/README.md` and the
provenance receipts for export limitations, source hashes and licenses.
Google model-viewer 4.4.0 is bundled locally; the viewer requires no CDN.
