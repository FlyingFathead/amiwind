# AmiWind v0.0.23-dev1 - parallel build checkpoint

29 September 2026. First development checkpoint after v0.0.22, based on the
owner's `amiwind-2026-09-29_124939.zip`, SHA-256
`d01d1bf130e4072dc794417f4127a3d7e62469861a85b3b3d146ff5d1baad568`.

## Public package revision 2

The first delivery contained trailing spaces on blank lines in
`prepare_mesh_bsp.py` and `prepare_music.py`. The owner's final Git whitespace
check stopped publication. Revision 2 removes those spaces and makes whitespace
validation mandatory in source inspection, candidate creation and validation.
The workflow now explicitly requires the check before delivery. Two release-gate
tests raise the host suite to 243 tests. The corrected publishing helper accepts
the exact initially applied dev1 files as well as the original v0.0.22 base.

Runtime VERSION stays 0.0.23-dev1. Existing archives remain immutable; corrected
public archives use `-r2` filenames. Both compiled playtests remain unchanged:
this packaging correction does not require another native build or font bake.

## Build changes

- Enable dependency-aware stage scheduling by default. Native compilation, music
  and dialogue lookup can overlap the ordered world-conversion chain.
- Parallelize NIF decoding, preview bakes, BSP model preparation and placed-model
  lightmaps/collision, intro actors, character heads and music tracks.
- Share one CPU budget across stages, respecting detected affinity and cgroup
  quota. Bound queued work and numerical-library threads; preserve output order
  and a single writer for shared archives/BSP data.
- Propagate the job limit into interior and Census tools; group native compiler
  output per target. Keep individual stage logs, timings and failure receipts.
- Retain `--jobs N`, `-j N`, `--j N` and `--single-thread`. Add
  `--serial-stages` for diagnosis with stage overlap disabled.

See [parallel builds](PARALLEL_BUILD.md) for limits and remaining serial work.
Native gameplay code and conversion recipes are unchanged in this checkpoint.

## Font builds

Both complete builds passed with the supplied owned data:

| Input variant | Verified conversion | Full pipeline time |
| --- | --- | --- |
| Loose BookArt TTFs present | Magic Cards and both Gothic families use TTF; Daedric safely falls back because its TTF exceeds native glyph limits | 262.321 seconds |
| Separate input copy with all three loose TTFs absent | All four UI families use their original FNT/TEX pairs; paper uses filled bitmap ink | 265.865 seconds |

Each run used the automatically detected eight-worker budget and completed all
17 stages. Times are observed stage-pipeline wall times, excluding prerequisite
checks, source hashing and tool installation. They are not a controlled speedup
ratio against v0.0.22. The final TTF image was assembled again after the native
diagnostic-output grouping change, using a fresh native build.

This verifies the TTF-present and Steam-style bitmap-only input conditions. It
does not claim a second independent Steam installation or a storefront detector.
The owner's earlier successful Steam build remains separate evidence.

`--bitmap-paper-ink filled` is the shipped default. `original` restores the older
bitmap paper coverage. Usable TTFs are selected automatically; the ink option
does not force bitmap fonts or change TTF output, dialogue or menu glyphs.
See [font options](PAPER_FONT_OPTIONS.md).

## Validation

- All 243 host tests pass, including the revision-2 whitespace gate and real
  process ordering, worker/thread limits,
  concurrent stage dependencies and cancellation after a failed stage.
- Native cross-compilation succeeds. Its 87 warnings match the unmodified
  v0.0.22 baseline diagnostics exactly; no new warning is introduced.
- All 275 character head/hair previews and ten intro actor models are
  byte-identical between the serial and parallel conversions checked here.
- Exterior and prison BSPs match all 15 sections of the serial output. Census
  geometry, collision, textures and lightmaps match all 14 non-entity sections;
  its baseline entity section includes later NPC/door additions.
- Both private HDFs boot in FS-UAE 3.1.66 under the reference A1200/AGA,
  68040/FPU, JIT, 2 MiB Chip + 16 MiB Z3 profile. Versioned menus and the prison
  name prompt render with their respective font variants; movie skip works.
- Public source allowlist, archive hashes and clean incremental application are
  checked before delivery. Private image receipts, logs and captures accompany
  the playable packages.

These are bounded emulator smoke tests, not full opening-route or physical-Amiga
acceptance. Town was reached through the debug command; the subsequent scripted
Census command was not confirmed, so it is not recorded as a pass. Existing
transition/freezing reports remain open. Windows/WSL was not exercised here.

## Following checkpoints

Restore and verify the reported missing intro sea splashes, check music through
gameplay and transitions, then implement and connect the remaining Seyda Neen
interiors. [The interior inventory](SEYDA_NEEN_INTERIORS.md) lists all 13 original
named cells; only the Census Office is currently converted. This build does not
claim those gameplay changes. Continue with dev2, dev3 and so on.

Publish this checkpoint as a GitHub prerelease with only the full and incremental
public source ZIPs and their checksum sidecars. Playable HDFs, original/converted
game assets, ROMs and private evidence are excluded from the public release.
