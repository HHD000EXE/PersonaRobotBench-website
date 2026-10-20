# PersonaRobotBench website

The public research website for the **100-task / 217-persona** benchmark.

- **Live website:** https://hhd000exe.github.io/PersonaRobotBench-website/
- **Contribute:** fork this repository and open a pull request targeting **`website`**.
- **Contribution guide:** [CONTRIBUTING.md](CONTRIBUTING.md)
- **Benchmark:** [HHD000EXE/PersonaRobotBench](https://github.com/HHD000EXE/PersonaRobotBench), currently private. Its code and linked technical guides require repository access.

This public repository contains only the website, its task catalog, and selected
static scene illustrations. Model results remain labelled pending. The homepage
includes six complete recorded Astra episodes: A/B pairs for Tasks 18, 51 and 68.
Videos play at their original simulation rate with inference waits omitted;
they are selected demonstrations rather than a benchmark success-rate estimate.
See [recording provenance](data/rollout-provenance.json) for source hashes,
recording context and the historical Task 110 → Task 51 mapping.

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

Edit `data/examples.json`. The homepage has matched A/B videos for Tasks 18, 51
and 68. Set each persona's `video` field, for example:

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
2. Set the corresponding `personas[].video`; supply both A and B for a paired comparison.
3. Set `videoPoster` to a real frame from that recording, update its duration,
   and include captions for speech. Keep the static scene poster separate.
4. Update `data/rollout-provenance.json` with the recording source and hashes.
5. Run the checks above and open a PR against `website`.

Missing videos keep their placeholders. Playback uses `personas[].video`, not
the reserved top-level `video` field. Host large recordings externally to keep
this source repository small.

## Where to edit

| File | Purpose |
| --- | --- |
| `index.html` | Page copy, sections, links and evaluation context |
| `styles.css` | Responsive layout and typography |
| `app.js` | Search, category filters, task details, tabs and video playback |
| `data/tasks.json` | All 100 task descriptions and 217 task-local persona cases |
| `data/examples.json` | Curated examples, posters and rollout video URLs |
| `data/rollout-provenance.json` | Recording sources, hashes, timing and historical task numbering |
| `data/asset-provenance.json` | Original image sources, hashes and font sources |
| `assets/fonts/` | Self-hosted fonts with their OFL license notices |

Task instructions and persona descriptions follow the benchmark configurations;
category grouping and short example headings are editorial. Images are static
scene illustrations, not evidence of policy success. Do not publish an inferred
success rate or label a partial attempt as a completed rollout.

The catalog and optimized images are already checked in. Maintainers with a full
benchmark checkout and Pillow can regenerate them with:

~~~bash
python3 data/build_assets.py --benchmark-root /path/to/PersonaRobotBench
~~~

Regeneration replaces `data/examples.json`, so preserve any added rollout URLs
and reapply them afterwards. Normal website edits and deployments do not need
the private benchmark checkout.

## Branch ownership

`HHD000EXE/PersonaRobotBench-website:website` is the public contribution and
deployment source. The original benchmark repository also has a `website`
branch containing the initial website snapshot. That private snapshot is not an
automatic mirror: maintainers should bring future public website changes into
it explicitly when needed. Do not merge the website branch into benchmark `main`.

This website has no backend, analytics, model calls or simulator processes.
Keep API keys, credentials, local outputs and runtime files outside this repository.
