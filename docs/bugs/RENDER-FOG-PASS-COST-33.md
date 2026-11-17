# RENDER-FOG-PASS-COST-33: The per-pixel fog and day-night sky pass costs 150-210 ms per frame on a slow 68040

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 9 October 2026, in v0.0.33-dev |
| Where | engine aw_fog.c AW_FogDraw and r_sky.c R_DayNightSkyPixel, every exterior frame |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.33-dev (last seen) |
| Severity | medium: About 10-15 percent of an exterior frame at 49.7 MHz (cycle-exact emulation, relative); up to 75 percent of a world-only view. |
| Family | Distance drawing (horizon, fog, sky, far edges) (`distance-drawing`) |

<!-- END GENERATED FACTS -->

<!-- BEGIN GENERATED TIMELINE: edit docs/bugs/bugs.json (bug_register.py step, note, report), then run tools/bug_register.py render -->

## Timeline

Dated events, oldest first, from the entry's own data (first noticed, reports, history, closure steps, returns, the fix, a deferral):

- 2026-10-09: reported in v0.0.33-dev
- 2026-10-09: CHIM-SLOWCPU-FRAMETIME-33: Balmora on CHIM at about 1 frame per second on a slow 68040: CHIM-SLOWCPU-FRAMETIME-33: the maintainer play report of the private CHIM preview (engine 0d8bf4f, world format 0.4, v0.0.32 disks) on the slow ...
- 2026-10-30 18:55 +0200: seen again in v0.0.57-dev3: Raspberry Pi 4B, Amiberry JIT, 32 MB Fast, HUD fps, 4 headings per spot: fog off vs fog on at distance 300: Balmora +3 %, Ald-ruhn +4 %, Suran +8 % (the fog pass about 3 to 8 % of the frame), Vivec -8 % (fog on faster there); 300 vs 540 ...

<!-- END GENERATED TIMELINE -->

_Last updated with AmiWind v0.0.45 (19 October 2026)._

## Status: 9 October 2026

Open. Found while splitting the slow-CPU frame time (CHIM-SLOWCPU-FRAMETIME-33). Not repaired.

## Symptom

On the slow accelerator preset (FS-UAE cycle-exact 68040, `uae_cpu_multiplier 14`, relative
numbers), switching off fog and the day-night sky (`aw_fog 0; aw_daynight 0`) makes the 3D view
146 ms faster at Balmora camera 1 (1,368 to 1,222 ms) and 170 ms faster at camera 5 (829 to
659 ms) on CHIM. With brush models off as well, the view drops from 273 to 66 ms: the pass is
three quarters of a world-only view. `aw_fog 0` alone saves 20-30 ms, `aw_daynight 0` alone
90-110 ms.

## Where

`engine/aga/src/aw_fog.c` `AW_FogDraw` (a full-viewport pass after the span renderer: three float
additions per pixel for the view ray, a depth lookup and a colour table per pixel) and
`engine/aga/src/r_sky.c` `R_DayNightSkyPixel` (called for every sky pixel: float tests, sun halo
dot products, night pixel).

## How it happened

The pass was written and judged with the JIT preset, where it costs a few milliseconds.

## Why it was not caught

The renderer counters time the view as a whole; the post pass has no timer of its own.

## Reproduction

Slow preset, Balmora camera 1 or 5, `aw_rcount 2`; compare the view time with
`aw_fog 0; aw_daynight 0`.

## Repair

Pending. Quake has no screen-space post pass: fog belongs in the colormap lookup of the span or
surface-cache stage, or at least in an integer pass (fixed-point ray steps, the sky colour per
column or row band from a table instead of per pixel).

## Verification

Pending: same cameras, view time with the pass on must approach the `aw_fog 0; aw_daynight 0` time.

## Prevention

A timer for the post pass in the renderer counters.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Distance drawing (horizon, fog, sky, far edges) (`distance-drawing`). Far-plane fog, the skyline fill, distant sprites and resident ground. See [families](README.md#families).

- [CHIM-BRIDGE-POP-PIECES-44](CHIM-BRIDGE-POP-PIECES-44.md): Bridges pop into view piece by piece as the player approaches (Balmora)
- CHIM-STAR-TREES-POP-64 (no report page): Star trees (crossed-plane crowns) pop in and out of view while the camera moves
- [CHIM-TERRAIN-TEXTURE-BLOCKY-43](CHIM-TERRAIN-TEXTURE-BLOCKY-43.md): Roads and paths on the ground look blocky: each texture square is drawn with hard edges instead of blending into its neighbours
- [FOG-TOWN-HEAVY-32](FOG-TOWN-HEAVY-32.md): Heavy fog at the Vivec Arena and in Balmora in v0.0.32-dev1
- GEO-02 (no report page): Seyda Neen ground ends before the world terrain handoff
- [HORIZON-FLORA-SPRITES-32](HORIZON-FLORA-SPRITES-32.md): Horizon silhouetting: not yet perfect
- [HORIZON-HOLES-31](HORIZON-HOLES-31.md): Distant buildings break up against the sky
- HORIZON-POP-29 (no report page): Ashlands horizon pops or breaks up while turning
- [LAND-HORIZON-GAPS-29](LAND-HORIZON-GAPS-29.md): Sky visible through gaps in distant resident ground
- [SEYDA-WALL-SHAPE-31](SEYDA-WALL-SHAPE-31.md): Dark shape pokes out of a stone wall by the Seyda Neen shore
- [SHELL-TEXTURE-VOTE-32](SHELL-TEXTURE-VOTE-32.md): Distant shells: door and grille textures win over large sealed areas
- [SKY-FOG-OFF-BACKGROUND-25](SKY-FOG-OFF-BACKGROUND-25.md): With fog off, far pixels outdoors that no surface covered showed a pale solid background instead of the sky
- SKY-NIGHT-COVER-29 (no report page): Dense night clouds rarely reveal moons/stars
- SKY-STARS-28 (no report page): Enlarged stars cover original night artwork
- SKY-VISUAL-01 (no report page): Sky-only day/night remap clashed with gray distance fog
- TREE-PILLAR-28 (no report page): Sprite-tree roots extend into unintended striped pillars
- [TREE-VIEW-FLOAT-38](TREE-VIEW-FLOAT-38.md): Sprite tree appears detached from terrain from particular viewing directions
- [WATER-UNDERWATER-SKY-44](WATER-UNDERWATER-SKY-44.md): Under water the distance shows the sky's clouds instead of blue water

Related bugs in other categories:

- [CHIM-SLOWCPU-FRAMETIME-33](CHIM-SLOWCPU-FRAMETIME-33.md): Balmora on CHIM runs at about 1 frame per second on a slow 68040 (cycle-exact emulation)
- INTERIOR-FOG-UNUSED-51 (no report page): Interiors have no fog: the cell's fog colour and density are never used, so misty caves and tinted rooms show none

<!-- END GENERATED CATEGORY -->
