# BUILD-HANDS-NOT-BUILT-32: Per-race first-person hands are not built by the builder

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | audit |
| First noticed | 8 October 2026, in v0.0.32-dev |
| Where | Builder stage hand-catalog (tools/build.py) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.32-dev (last seen) |
| Severity | high: Every race falls back to Nord hands and torch silently. |
| Family | Content silently missing from a build (`build-content-missing`) |

<!-- END GENERATED FACTS -->

## Status: 8 October 2026

Fixed in source on v0.0.32-dev (not shipped at the time of writing; a finished from-scratch image is still to confirm
it). Found by the builder defaults audit (every option and stage compared with the v0.0.31
payload).

## Symptom

v0.0.31 ships 40 `progs/hands/*.mdl`, `gfx/hand-models.awh` and `gfx/hand-torch.awt`, made only by
the standalone `tools/prepare_hand_catalog.py`, which no builder step calls. A from-scratch build has
none of them, so every race falls back to the Nord hands and torch.

## Where

`tools/prepare_hand_catalog.py` (standalone); `tools/build.py` has no step for it.

## How it happened

The catalog was produced by hand for a release and its output carried forward in patched images.

## Why it was not caught

Release images were patched from earlier images instead of being built from scratch
(BUILD-NOT-FROM-SCRATCH-32), so a missing builder stage never showed.

## Reproduction

A from-scratch build with the repository builder; compare its payload with v0.0.31.

## Repair

- New default builder stage `hand-catalog` (`tools/build.py`, `hand_catalog_status`,
  `hand_catalog_steps`): `prepare_hand_catalog.py --palette <intro scene palette> --runtime-palette
  --topology source --out <run>/hand-catalog`. It depends only on the `intro` stage, so it runs in
  parallel with the rest of the chain (about two minutes on one core). It runs in every real AGA
  build with 3D hands; sprite hands, dry runs, terrain-only builds and the rc3 image recovery make
  none. `build-state.json` records `hand_catalog`, and the build prints its status.
- v0.0.31's hands use the image's final palette: the scene palette with the reserved UI bank and
  the sky colour bank. `--runtime-palette` derives exactly those bytes from the scene palette with
  the image step's own code (`ui_palette.reserved_palette` and `sky_palette_overlay.banked_palette`,
  both factored out of the image path, so there is one implementation). The authored source
  topology is what v0.0.31 shipped (the tool's own default stays `reduced`). The catalogue report
  records the palette it used.
- The image step takes `--hand-catalog DIR` and installs the models, `gfx/hand-models.awh` and
  `gfx/hand-torch.awt` in `finalize_image`, right after the sky palette bank and before the guard
  torches and every final gate (`prepare_hand_catalog.install`). It installs only when every file
  matches the catalogue report and the report's palette is the stage's final palette; otherwise
  nothing is installed and the image stops. It writes `hand-catalog-staging.json`.
- The sky palette overlay read `gfx/hand-models.awh` as a character head preview (same `AWH1`
  magic) and would stop on any stage that already holds the catalogue; it now recognises the hand
  catalogue (model paths only, no pixels).

## Verification

- Owned data, dev1 scene: the builder's exact `hand-catalog` command made all 42 files (40 models,
  catalogue, torch metadata) byte-identical to v0.0.31, and `install` accepted the v0.0.31 final
  palette. The same conversion against the plain scene palette differs in 30 of the 42 files,
  which is why the step derives the runtime palette.
- `tests/test_hand_catalog_step.py`: palette derivation (UI bank only when the scene has no UI
  receipt, sky bank only on the approved sky input), conversion and report use the runtime
  palette, install copies everything or nothing (other palette, changed file, existing target,
  unsafe path), install comes after the sky step and before the guard torches, and the sky
  overlay accepts the hand catalogue while still reading head previews.
- `tests/test_release_coverage.py` and `tests/test_build_defaults.py`: the default build runs
  `hand-catalog` before `image` and passes `--hand-catalog`; the release feature `hands-per-race`
  names that step.
- Pending: a finished from-scratch image compared file by file with v0.0.31.

## Prevention

`config/release-features.json` maps every file class v0.0.31 ships to a feature and its default
builder steps; `tests/test_release_coverage.py` fails when a shipped class has no feature or a
feature's step is not in the default build, and its list of known builder gaps may only shrink.
`tools/payload_coverage.py check` compares a built payload or staged image with the release, by
feature, for the from-scratch gate.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Content silently missing from a build (`build-content-missing`). Every omission is receipted; payload and entity counts are compared with the last release; shipped features are on by default. See [families](README.md#families).

- [ARENA-PIT-NO-INTERIOR-33](ARENA-PIT-NO-INTERIOR-33.md): The Vivec Arena minigame fights on the test floor: the Arena Pit interior is not in v0.0.33 builds
- [AUDIO-MISSING-SOURCES-32](AUDIO-MISSING-SOURCES-32.md): The image step reports missing sources for 7 voices and 2 effects
- [BUILD-DRESSING-EXCLUDED-32](BUILD-DRESSING-EXCLUDED-32.md): The repository builder drops lantern hooks and other dressing in Seyda Neen maps without a receipt
- [BUILD-EXTRA-TOWN-OPTIN-32](BUILD-EXTRA-TOWN-OPTIN-32.md): A default build leaves out the Vivec Arena preview that v0.0.32 ships
- [BUILD-FLORA-OPTIN-32](BUILD-FLORA-OPTIN-32.md): A from-scratch build without --tree-sprites leaves out the trees and grass every release ships
- [BUILD-HARVEST-NOT-BUILT-32](BUILD-HARVEST-NOT-BUILT-32.md): Mushroom harvest data is not built by the builder
- [BUILD-NIGHT-TABLES-31](BUILD-NIGHT-TABLES-31.md): Repository image builds have no night lamp, glowing glass or location fog tables
- [BUILD-STANDALONE-STAGES-32](BUILD-STANDALONE-STAGES-32.md): Door overlay and interior section tools are outside the builder; their use in v0.0.31 is unverified
- [LAVA-NOT-IMPLEMENTED-33](LAVA-NOT-IMPLEMENTED-33.md): Lava is drawn as plain static meshes: no liquid surface, no damage, no view tint, never tracked
- [MINIWIND-PAYLOAD-NOT-SLIM-33](MINIWIND-PAYLOAD-NOT-SLIM-33.md): MiniWind #2 was built with the full movie and voice payload
- [PLAYTEST-PAYLOAD-COVERAGE-32](PLAYTEST-PAYLOAD-COVERAGE-32.md): The v0.0.32-dev1 playtest has no first-person hands and no harvest
- [SEYDA-LANTERNS-MISSING-31](SEYDA-LANTERNS-MISSING-31.md): Seyda Neen lanterns light the night but are not in its maps
- TREE-SCALE-001 (no report page): Non-unit-scale tree sprites omitted; bounds too conservative

Related bugs in other categories:

- [BUILD-NOT-FROM-SCRATCH-32](BUILD-NOT-FROM-SCRATCH-32.md): Five releases shipped without the public builder being able to build them from scratch

<!-- END GENERATED CATEGORY -->
