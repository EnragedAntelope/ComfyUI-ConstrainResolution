# AGENTS.md — ComfyUI-ConstrainResolution

A ComfyUI node that resizes any image to fit your model's resolution rules: a minimum size, a maximum size, and dimensions guaranteed divisible by 2, 8, 16, 32, or 64. Keeps aspect ratio by cropping a few pixels when needed. No dependencies beyond ComfyUI itself (Python ≥3.10). Built on ComfyUI v3 node API (`comfy_api.latest`).

## Current state

_Last verified: 2026-08-24_

- **Status:** released v2.4.1 (`pyproject.toml`). Stable and feature-complete for what it sets out to do. Published to the Comfy Registry — `.github/workflows/publish_action.yml` fires on a `pyproject.toml` version change on `main`, so a functional change needs a version bump or it never ships.
- **Works:** both constraint modes (Prioritize Min Resolution, Prioritize Max Resolution strict); divisibility by 2/8/16/32/64 enforced together with the min/max limits so reported width/height always match the output tensor; minimal smart cropping with a configurable crop position; all five resize methods; the full output set (resized image, original passthrough, width, height, final and original aspect ratios). `.github/workflows/test.yml` runs the pytest suite.
- **In progress:** nothing — v2.4.1 polished the v2.4.0 audit: `validate_inputs` now rejects at queue time (Strict-mode `multiple_of > max_res`, out-of-range resolutions, unknown constraint modes), the min-res memory guard gained an absolute pixel ceiling, large-upscale warnings fire in both modes, CI actions are SHA-pinned with pip caching (`requirements-ci.txt`, CI-only), and a schema-contract test keeps `define_schema()` in sync with `execute()`.
- **Known gaps / next steps:** no batch-specific handling beyond what ComfyUI's own resizer provides; behaviour under extreme aspect ratios is covered by tests but has had little real-world exercise; the README screenshots track v2.3.1 and would need refreshing alongside any visible change.
- **Deep docs:** none — `README.md` is the user-facing reference and `nodes.py` is the whole implementation.

## Architecture in 60 seconds

- **Single node.** `nodes.py` contains the entire feature — one node class, all logic self-contained.
- **Three rules in one step:** min resolution, max resolution, and divisibility. Resize, round, and crop all land on multiples of the chosen number.
- **Two constraint modes:** "Prioritize Min Resolution" (neither dimension goes below `min_res`) and "Prioritize Max Resolution (Strict)" (output always fits in a `max_res × max_res` box — hard VRAM cap).
- **Smart cropping.** When an extreme aspect ratio can't satisfy both limits, crops minimally to hit exact dimensions instead of distorting. Crop position configurable (center/top/bottom/left/right).
- **Uses ComfyUI's own resizer** (`comfy.utils.common_upscale`) — results match core resize nodes. Bicubic/lanczos output clamped to valid range to avoid overshoot artifacts.
- **Rich outputs.** Returns resized_image, original_image passthrough, width/height, and both final and original aspect ratios.

## Layout

| File / Directory | Purpose |
|------------------|---------|
| `__init__.py` | ComfyUI custom-node entry point (registers the node) |
| `nodes.py` | The entire node: resize logic, constraint modes, cropping, validation |
| `tests/` | pytest test suite |
| `conftest.py` | pytest configuration/fixtures |
| `docs/` | Images for README |

## Build / test / run

```bash
# Install via ComfyUI Manager (recommended)
# Search for "Constrain Resolution" in the Manager

# Manual install
cd ComfyUI/custom_nodes
git clone https://github.com/EnragedAntelope/ComfyUI-ConstrainResolution.git
# Restart ComfyUI

# No pip dependencies — Python 3.10+ and ComfyUI itself are the only requirements

# Run tests (conftest.py mocks comfy_api, so no ComfyUI install is needed)
pip install -r requirements-ci.txt
pytest
ruff check .
```

## Conventions & gotchas

- Single-file node — `nodes.py` is the entire feature. Keep it self-contained.
- Zero pip dependencies for the pack itself. `requirements-ci.txt` exists only for CI (pytest/torch/numpy); never add runtime deps.
- `validate_inputs` must NOT take `**kwargs`: ComfyUI then skips its own range and combo-option validation for *every* input on the node (`execution.py`, `validate_has_kwargs`). It also skips those checks for each input the function names explicitly, so anything listed in the signature must have its bounds re-asserted inside the function. `MIN_RESOLUTION`/`MAX_RESOLUTION`/`MIN_MULTIPLE_OF`/`MAX_MULTIPLE_OF` are shared by `define_schema()` and `validate_inputs()` so the widget and the queue-time check cannot drift.
- The GitHub Actions pins are commit SHAs; the comment above each one records the version it corresponds to. Keep them on node24-native majors — GitHub warns on, and will eventually stop running, node20 actions. `Comfy-Org/publish-node-action` is pinned to the commit its `v1` *branch* points at — its `1.0.1` tag is older than that branch and still calls `comfy tracking disable`, which current comfy-cli does not have.
- Divisibility, min/max, and crop dimensions are enforced together — reported width/height always match the actual output tensor.
- Unsatisfiable or memory-exhausting settings raise `ValueError` rather than returning a zero dimension; `calculate_optimal_dimensions` never returns 0 for a non-empty input. The min-res pixel budget is `max(box, min(box * FACTOR, MAX_OUTPUT_PIXELS))` where `box = max_res ** 2` — a size the user's own `max_res` permits is never refused.
- `resize_method` defaults to `lanczos` (sharpest). Options: lanczos, bicubic, bilinear, nearest-exact (pixel art/masks), area (big downscales).
- When `crop_as_required=False` and `multiple_of=1`, no cropping occurs — keeps every pixel.
- The node uses ComfyUI v3 schema (`comfy_api.latest`).

## Security

This file is **public-safe by default**. Never add local paths, credentials, API keys, personal data, infrastructure details, or subscription info.

Before pushing, re-read this file and confirm it contains no local paths, credentials, or personal data.

## Maintenance

**Update rule:** When you change the architecture, build/test commands, or conventions, update this AGENTS.md in the same commit. Keep under 200 lines.

**CLAUDE.md:** One-line shim: `@AGENTS.md`.

**New-repo rule:** Create AGENTS.md in the first session a new repo is worked on.

**No-overlap rule:** Explanatory prose lives in one file. AGENTS.md = agent-facing summary; README.md = human/usage. Identical install commands may be restated verbatim. Explanatory prose must not be duplicated — link instead.
