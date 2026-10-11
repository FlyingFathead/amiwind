# Experimental flags

Work that is in the source but not finished, or not yet the default, ships behind a switch that is
off by default. A default build is unchanged by everything on this page; each switch has a test that
checks it is off by default.

| Switch | Where | Default | What it does | State |
| --- | --- | --- | --- | --- |
| `--skip-census` / `aw_skip_census 1` | builder / engine cvar | off | Quick test builds: New Game skips the Census and Excise Office and opens a quick character screen instead | experimental, unfinished (the screen, its console command and its docs are in progress) |
| `--chim-lighting-type hybrid` | builder | hybrid | CHIM lighting: light styles and the night lamp table widened to every class | partial: terrain lightmaps, model light levels and plant glow not yet |

| `--npc-lod on` (config `npc_lod`) | builder | off | Near and far NPC models chosen by distance (engine `dbg npclod`) | experimental: to be compared in game before it becomes the default |
| `--anim-kit off` / `aw_animkit 0` | builder / engine cvar | on | The previous idle-only residents (the kit is the default) | the old method, kept selectable |

| `--npc-head-detail original` (config `npc_head_detail`) | builder | off (auto = budget) | NPC heads keep every original triangle | experimental: unfinished head/body balance, not yet compared in game |

| `--npc-models parts` | builder | whole | NPC gallery models composed from a shared parts library (each body part converted once) | experimental: joint seams and head spikes still open (NPC-JOINT-GAPS-33, NPC-GALLERY-SPIKE-33) |
| `--chim-regions SET` (+ `--chim-regions-status FILE`) | builder | off | Finished CHIMport cells on CHIM inside the legacy open world: each cell's open-world map replaced in place by its CHIM frame map ([CHIM regions](chim/CHIM_REGIONS.md)) | experimental: harvest catalogues of replaced cells not carried over; a terrain margin per cell costs storage (CHIM-REGION-MARGIN-STORAGE-36) |
| `--night-lamp-lightmaps on` | builder | off | baked night-lamp light (lightstyle 32) on the terrain and buildings of the rebuilt legacy Balmora cores, from `tools/lamp_lightmaps.py` | prototype from v0.0.31 development: untested in a full build; the shipped night lamps stay the engine lights |
| `--chim-terrain-hull auto` / `--chim-terrain-refs off` | builder | compiled / on | CHIM chunk terrain the earlier way: routed hull chains for the regular grid and a terrain copy in every chunk (world format 0.5); the defaults since v0.0.36 are the compiled hull (checked and patched against its pieces) and terrain references (format 0.7) | the old method, kept selectable: a default build with it overruns Balmora's CHIM ring (CHIM-BALMORA-RING-GROWTH-36) |
| `--chim-model-hull-patch off` | builder | on | Compiled model hulls stay exactly as compiled (the check is still recorded); the default adds back the pieces the compiler lost under a walkable surface | the old method, kept selectable (CHIM-COMPILED-HULL-SHORT-36) |
| `--chim-model-hull-patch on` | builder | off | Compiled model hulls get the pieces the compiler lost under a walkable surface added back exactly | experimental: makes 11 Balmora and test-area models exact, but Balmora's ring has no zone room for it yet (CHIM-COMPILED-HULL-SHORT-36) |
| `--coord-range narrow` (`AW_COORD_NARROW`, `make EXTRA_DEFINES=-DAW_COORD_NARROW`) | builder / engine compile switch | wide | Positions travel as Quake's 16-bit eighths (about +/-4,096 units, protocol 15) instead of the default 24 bits of 1/256 units (+/-32,768, protocol 1015, one byte more per coordinate); the frame, arrival and spawn bounds follow (`AW_COORD_BOUND`, engine/aga/src/aw_coord.h; builder tools/coord_range.py; audit list config/coord-range-audit.json); an area wider than +/-4,000 (all of Vivec in one frame, `vivec_city`) is refused | the old method, kept selectable (CHIM-FRAME-COORD-RANGE-33); `--engine-experiment widecoord`, the switch of the v0.0.36 spike, still selects wide |
| `--engine-profile upstream` (`--engine-asm`, `--engine-opt`) | builder (`build.py`, `build_aga.py engine`) | c | The engine compiled with the optimisations of TerribleFire's AmiQuake GCC port (Stephen Leary), including NovaCoder's original routines: upstream's 68k assembly for the turbulent span loop and the chunky-to-planar conversion, at `-O1` as upstream builds; `--engine-opt o2` is the selective `-O2` experiment ([engine profiles](ENGINE_PROFILES.md)) | experimental: measured on the slow preset before the owner picks the default; `c` stays the regression reference build |
| `--stair-walk-cache full` | builder | cached | Walks every map and CHIM frame again instead of reusing the stored walk of unchanged ones | regression and beta-test runs only (from-scratch reference build, nightly check) |

More rows are added as the remaining side branches are gathered into this release.

`--chim-native-towns on` left this table in v0.0.36: it is the default (CHIM-native areas: every CHIM area
prepared through the CHIM pipeline from the game data, with no legacy town chain; Seyda Neen too since
v0.0.36-dev5, whose frame maps are made from the scene stage's town with no region maps cut). The
open world outside the CHIM areas is still made of legacy region maps.

## Retired flags

A retired flag selects an older method that is kept in the source only for historical regression tests
(`tools/retired_flags.py`). Its help starts with "RETIRED - DO NOT USE except for antiquated regression
testing". In developer mode (`--developer-mode`, used by every development, release candidate and final
build) it stops the build before any stage:

```
ERROR: --legacy-area has been disabled since CHIM v0.1.0 in development mode. Override only if sure / for historical regression tests: --override legacy-area
```

`--override NAME` (repeatable) lets that one flag through. Outside developer mode the build continues with
`WARNING: DO NOT USE <flag> EXCEPT FOR ANTIQUATED REGRESSION PURPOSES (retired since CHIM v0.1.0)`. Every use,
overridden or not, is printed in a `RETIRED FLAGS USED: ...` banner at the start and in the end-of-build
summary, and recorded as `retired_flags_used` in `build-state.json`, `build-summary.json` and the image
receipt `image/build.json`.

| Flag | Override name | Retired since | What it selects | Use instead |
| --- | --- | --- | --- | --- |
| `--legacy-area TOWN` | `legacy-area` | CHIM v0.1.0 | TOWN's CHIM frame prepared through the legacy region-map chain (its region maps built, the frame map copying its actors from them) | the default CHIM-native town |
| `--chim-native-towns off` | `chim-native-towns-off` | CHIM v0.1.0 | every CHIM town prepared through its legacy chain (the v0.0.35 default; Seyda Neen: its region maps cut in the image step) | `--chim-native-towns on` (the default) |
| `--chim-area`, `--miniwind-town` or `--extra-town` naming a Vivec district (`vivec_arena`, `vivec_foreign`, `vivec_hlaalu`, `vivec_redoran`, `vivec_telvanni`, `vivec_temple`, `vivec_delyn`, `vivec_olms`) | `vivec-districts` | CHIM v0.1.0 (retired 11 October 2026) | one CHIM frame per canton (the Arena-only frame of Vivec stage A, or another district) instead of the whole city | `vivec_city`, all of Vivec in one CHIM frame with its rooms (the default) |
| `--seyda-recorded DIR` | `seyda-recorded` | CHIM v0.1.0 (retired 10 October 2026) | the recorded v0.0.31 Seyda Neen region maps shipped instead of Seyda Neen converted from the game data (NOT RECOMMENDED since v0.0.31) | Seyda Neen converted from the game data (the default) |

Not retired, but not recommended: `--seyda-recorded DIR` (the recorded v0.0.31 Seyda Neen maps, NOT
RECOMMENDED since v0.0.31) stays selectable with a loud warning in every mode.
