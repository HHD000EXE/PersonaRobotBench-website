# Contributing to the website

Website improvements are welcome: copy corrections, accessibility, responsive
layout, task browsing, accurate catalog updates, and real simulation recordings.
Open issues and PRs in **HHD000EXE/PersonaRobotBench-website**. Benchmark task,
controller, or evaluator changes belong in the benchmark repository.

## Make a change

1. Fork the public website repository.
2. Create a working branch from `website`:

   ~~~bash
   git clone --branch website https://github.com/YOUR-USERNAME/PersonaRobotBench-website.git
   cd PersonaRobotBench-website
   git switch -c improve-website
   ~~~

3. Preview with `python3 -m http.server 8080` and edit the source files.
4. Run the checks below, commit, and push your working branch.
5. Open a PR with **base repository `HHD000EXE/PersonaRobotBench-website`** and
   **base branch `website`**. Describe the change and include screenshots for
   visible layout changes when available.

## Verify your work

~~~bash
python3 verify.py
python3 build.py
python3 verify.py --root dist
npm ci
npm test
~~~

Python 3.10+ and Node.js 24 are sufficient. Node and jsdom are development-only;
the published site has no JavaScript dependencies. CI runs these checks on PRs.
Do not commit `dist/`, `node_modules/`, generated simulation outputs or credentials.
After a maintainer merges a PR to `website`, GitHub Actions publishes the site.

## Content and recordings

- Preserve authored task instructions, persona descriptions and the 100-task /
  217-case scope. Explain the upstream source for any catalog correction.
- Keep evaluation figures tied to a documented model, controller, protocol and
  evidence. A demonstration alone is not a benchmark success rate.
- Add rollout URLs in `data/examples.json` under `personas[].video`; see the
  [README](README.md#add-or-replace-rollout-videos) for a complete example.
- Keep A/B recordings from the same task clearly identified. State whether a
  recording is complete or partial; static scene renders remain illustrations.
- Retain font license files and asset provenance when changing bundled assets.
- The public website can be edited without access to the private benchmark;
  links into that repository still require access.

The benchmark repository's private `website` branch is an initial snapshot.
Submit public contributions here; there is no automatic cross-repository sync.
