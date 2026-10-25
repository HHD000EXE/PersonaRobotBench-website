# Scene 001 web model

`shared-desk.glb` is a derived static viewer export of the initial scene at
`HHD000EXE/PersonaRobotBench`, revision `26cc1ccc3fd97bbcb834b550af11af0d2b1284ff`.
It retains the authored object transforms and default robot pose. It contains no
motion arrays, animation, physics, task execution or evaluation results.

See `shared-desk.provenance.json` for source-layer hashes and conversions.
Robot rendering meshes are simplified; diffuse textures are resized to 1024 px.
MDL diffuse color, metallic and roughness are mapped to glTF PBR. Static
ambient occlusion is ray traced with 24 hemisphere samples and baked into
vertex color (COLOR_0). This affects rendering only. The original residential
garden HDR is resized to 1024 × 512 for image-based lighting. The web renderer
uses ACES tone mapping; appearance differs from Isaac Sim path tracing. This
visualization is not suitable for geometry measurement or simulator equivalence.

Robot: NVIDIA Isaac Sim G1 asset, BSD-3 notice in `../vendor/LICENSE.unitree`.
Room textures: Poly Haven CC0, original source URLs in `texture-sources.json`.
Viewer: Google model-viewer 4.4.0, locally bundled, BSD-3 license in
`../vendor/LICENSE.model-viewer`; embedded dependency notices remain in the bundle.

Re-export from a source checkout containing the entry layer, referenced task
layers, vendor assets and diffuse textures:

    python tools/export_scene.py SOURCE_ROOT assets/models/shared-desk.glb

Requires usd-core, trimesh, numpy, Pillow and fast-simplification, scipy and embreex. No source
layers, archived trajectories or timestamps are modified by the exporter.
