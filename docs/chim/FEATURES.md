# CHIM feature tracker

<!-- Generated whole by tools/chim_features.py render from docs/chim/features.json; do not edit by hand. -->

What the [CHIM engine](README.md) has done for AmiWind, feature by feature: what each feature does, where it stands, the gain that was measured (what was compared, how and when) and how Quake's visibility culling still works with it. Generated from [`features.json`](features.json); a test fails when this page is stale. Bugs are on the [CHIM bug tracker](../bugs/CHIM_TRACKER.md); ideas and held-back work are collected in [CHIM ideas](IDEAS.md). How far the open world has been converted, cell by cell, is on the [CHIM cell tracker](CELL_TRACKER.md).

CHIM version: 0.1.0. 35 features: 21 in this release, 8 in progress, 3 planned, 3 ideas. Updated 9 October 2026.

## What CHIM has done so far

The headline measured gains. Each links to its feature, which says what was compared. Emulator figures are relative until a frame has been measured on a real accelerated Amiga.

- **Every asset stored once:** Balmora exterior: 162.1 MB of legacy region maps to 21.3 MB of CHIM world (7.62 times smaller). *builder output, 9 October 2026.* [Details](#every-asset-stored-once)
- **Every asset stored once:** Seyda Neen with the intro docks and the courtyard: 190.4 MB to 7.83 MB (24.3 times smaller). *builder output, 9 October 2026.* [Details](#every-asset-stored-once)
- **Streaming with no region stop:** Bytes read on the Balmora door walk: 73.5 MB to 40.7 MB. *builder output, 8 October 2026.* [Details](#streaming-with-no-region-stop)
- **Incremental frame world:** At most 16 KB copied per update instead of 405 KB; 85 chunk copies instead of 4,504. *emulator, relative, busy host, 9 October 2026.* [Details](#incremental-frame-world)
- **Chunk pinning: no holes in the town:** Steps with a chunk missing its ground inside the collision margin on the owner's Balmora route: 860 to 0. *host simulation, 9 October 2026.* [Details](#chunk-pinning-no-holes-in-the-town)
- **No disk writes during play:** Time spent "not validated" during play: 3.7 % to 0 %; write bursts during play: 6 in 410 s to 0 in 1,355 s. *emulator, relative, busy host, 9 October 2026.* [Details](#no-disk-writes-during-play)
- **Quake's visibility culling kept effective:** Brush models sent to the renderer: 512-654 to 46-114; BSP nodes walked per clipped face: 27-52 to 8.6-9.9. *exact counts, 8 October 2026.* [Details](#quakes-visibility-culling-kept-effective)
- **Faster frames in town:** Slow preset (cycle-exact 68040 at about 50 MHz): median frame 2.0-4.1 s to 1.1-1.6 s, 1.6-2.6 times faster. *emulator, relative, busy host, 9 October 2026.* [Details](#faster-frames-in-town)
- **Far terrain: the distant view:** Far layer in the low Hunk: 13.2 KB for Balmora; drawing it costs 30.6-43.7 ms per frame on the slow preset at the bridge and east-bank poses. *emulator, relative, busy host, 9 October 2026.* [Details](#far-terrain-the-distant-view)
- **Build cache and prerendered store:** Image step on MiniWind maps, warm: BSP optimizer 388 s to 5.7 s, hidden-surface cull 48 s to 6.6 s, byte-identical outputs. *builder output, busy host, 9 October 2026.* [Details](#build-cache-and-prerendered-store)
- **Statics and flora sprites streamed with their chunks:** Seyda Neen: largest free Hunk gap after the first load 1,099,200 B to more than 2,097,200 B. *emulator, relative, busy host, 9 October 2026.* [Details](#statics-and-flora-sprites-streamed-with-their-chunks)

Several features also have a cost, listed under their caveats: CHIM leaves less of the Hunk free at the load peak, spends more time outside the 3D view and draws slightly more spans. CHIM 0.1.0 is not published yet; the features marked "in this release" are in the development line for AmiWind v0.0.33.

## Features by status

| Status | Meaning | Features |
| --- | --- | --- |
| Shipped in CHIM 0.1.0 | in a published release | 0 |
| In this release (CHIM 0.1.0) | in the line that becomes the next release; not yet published | 21 |
| In progress | being built or measured; not finished | 8 |
| Planned | decided; no finished design or code | 3 |
| Idea | written down, not decided | 3 |

### In this release (CHIM 0.1.0)

| Feature | Area | What it does | Measured gain |
| --- | --- | --- | --- |
| [Every asset stored once](#every-asset-stored-once) | World format and disk | Every mesh, collision hull and texture of an exterior is stored once and placed by reference, instead of being copied into every region map that can see it. | 7.62 times smaller for Balmora, 24.3 times for Seyda Neen |
| [Pure CHIM towns: no legacy maps shipped](#pure-chim-towns-no-legacy-maps-shipped) | World format and disk | Balmora and Seyda Neen (with the intro docks and the courtyard) are drawn only by CHIM; the legacy region maps of a CHIM town are neither built nor shipped. Seyda Neen is regenerated from your data, so the temporary heap bypass for three recorded maps ends. | not measured |
| [Streaming with no region stop](#streaming-with-no-region-stop) | Streaming and memory | The land is cut into chunks of 256 units. A ring of chunks around the player is resident and chunks join and leave a little at a time, within a per-frame budget, so crossing a region border no longer loads a whole map. | 40.7 MB read instead of 73.5 MB on the door walk |
| [Incremental frame world](#incremental-frame-world) | Streaming and memory | When a chunk joins or leaves the ring, only the leaves it touches are relinked, instead of rebuilding the whole frame world on every crossing. The full rebuild is kept as a selectable method (chim_graft_mode 0). | 16 KB copied per update instead of 405 KB |
| [Chunk pinning: no holes in the town](#chunk-pinning-no-holes-in-the-town) | Streaming and memory | Chunks are pinned only while they load, farther chunks give way first, small blocks come from the high end of the memory zone and the ground never waits for a building. A chunk shows as soon as its ground is in. | holes on the owner's route 860 to 0 |
| [Zone walk gate](#zone-walk-gate) | Builder and tools | The builder runs the engine's own zone code over a walk through every frame and fails the build when a step leaves the player without ground. | not measured |
| [Strict heap gate and a fixed chunk zone](#strict-heap-gate-and-a-fixed-chunk-zone) | Streaming and memory | CHIM reserves one chunk zone of fixed size in the Hunk when a town loads. The builder checks every CHIM area against the engine's own numbers (active ring, load ring, largest block) before the game ever runs. | Seyda Neen passes the strict heap gate with room to spare |
| [No disk writes during play](#no-disk-writes-during-play) | Engine | Diagnostic logs stay in memory during play and are written on request or when the game is left, so a closed emulator or a power cut no longer lands in the middle of a write and leaves the volume "not validated". | time "not validated" in play 3.7 % to 0 % |
| [Quake's visibility culling kept effective](#quakes-visibility-culling-kept-effective) | Rendering and visibility | Placements are linked to the leaves they touch, terrain is world geometry with shallow per-chunk trees, and each chunk carries a row of the placements a view from it may see. Nothing is a func_wall that vis ignores. | 46-114 brush models sent instead of 512-654 |
| [Terrain as world geometry](#terrain-as-world-geometry) | Rendering and visibility | Each chunk's ground is a small BSP subtree grafted under the frame's world, so Quake's visibility, collision and water work on it as on any map, and the terrain occludes what lies behind it. | not measured |
| [Faster frames in town](#faster-frames-in-town) | Rendering and visibility | The shallow per-chunk trees and the far smaller number of models sent to the renderer cut the time a frame takes at the Balmora cameras. | 1.6-2.6 times faster on the slow preset |
| [Far terrain: the distant view](#far-terrain-the-distant-view) | Rendering and visibility | A resident low-detail layer of the land for the frame and beyond its edge (maps/<frame map>.far, written once per frame by the builder), drawn past the fog plane in the fog colour like the v0.0.32 horizon, so valleys and far land are not empty fog. | 13.2 KB, 31-44 ms per frame on the slow preset |
| [Texture effects (.chimfx)](#texture-effects-chimfx) | World format and disk | An optional effect file can add specks of chosen colours to chosen textures, identical in every build and off unless selected. It began as a bug: the first CHIM worlds showed bright specks because their textures skipped the palette guard. | not measured |
| [Island-wide audits as build gates](#island-wide-audits-as-build-gates) | Builder and tools | Each geometry or collision finding names its mechanism, sweeps every mesh that goes through the same converter path, is fixed once in the shared converter and stays as a gate: seam tears, the stair walk of every flight, terrain hull bevels, sky-bank texels and the memory fit. | not measured |
| [The CHIM builder](#the-chim-builder) | Builder and tools | tools/build.py --builder chim builds the CHIM world from your own Morrowind data with the same stages, --jobs, profiler and receipts as before; receipts record builder, chim_version and world_format. The legacy builder stays in the code and selectable. | Balmora exterior stage 5.2 minutes against 8.5 (different hosts) |
| [Build cache and prerendered store](#build-cache-and-prerendered-store) | Builder and tools | Stage fingerprints let a development build reuse the finished stages of an earlier run, a per-file asset pool reuses converted sounds and movies, a per-map pass cache reuses the image step's optimizer, cull and stair-walk passes, and the prerendered store (--prerendered DIR) keeps finished stage outputs (CHIM worlds, interiors, region maps) across runs and workspaces. Releases write the store but never read it. | image passes 388 s to 6 s when warm |
| [MiniWind quick test build](#miniwind-quick-test-build) | Builder and tools | A builder type for quick playtests: Balmora on CHIM with its interiors and what the engine needs, booting straight into Balmora. Development versions only; marked as a partial-area test. | not measured |
| [dbg tp, doors and saves on CHIM towns](#dbg-tp-doors-and-saves-on-chim-towns) | Engine | Every check that a scene exists (dbg tp arrivals, quick start, doors, saves and loads, the scene picker) goes through one function that finds the scene's map or the town's CHIM frame map, so a pure CHIM image works with the same commands as a legacy one. A save made in CHIM Balmora loads in either kind of image. | not measured |
| [Legacy and CHIM side by side](#legacy-and-chim-side-by-side) | Engine | chim_towns 0 brings back the legacy region maps for an A/B in one session; the console states which mode every town runs in, and start-up prints how many towns are on CHIM. No working method is deleted. | not measured |
| [Statics and flora sprites streamed with their chunks](#statics-and-flora-sprites-streamed-with-their-chunks) | Streaming and memory | The frame map tags its static models and flora sprites with their chunk; the engine loads and links them when the chunk joins the ring and frees them when it leaves, instead of holding all of them in the map's fixed cost in the Hunk. | Seyda Neen Hunk gap 1.1 MB to 2.1 MB |
| [--heap-mb builder option](#--heap-mb-builder-option) | Builder and tools | A builder option like --jobs: the map heap in MiB, exact, default 11; beyond the safe profile it prints one loud warning and runs anyway, and every gate uses the build's own value. | not measured |

### In progress

| Feature | Area | What it does | Measured gain |
| --- | --- | --- | --- |
| [Modular NPCs](#modular-npcs) | Characters | Humanoid NPCs are assembled from shared body parts converted once, with one small recipe per actor, instead of one complete baked model per actor. Equipment changes and looting can then change how an actor looks. The baked whole-actor method stays selectable. | about 0.4 million triangles in parts against 12.3 million baked |
| [NPC pathfinding and companions](#npc-pathfinding-and-companions) | Characters | A ladder that starts with plain Quake chase movement and stair climbing, and escalates only when stuck: a local ping, then A* on a small walkable graph stored with the chunks. dbg companion is a prototype follower that tests the first steps. | not measured |
| [Routed standing hulls for many-piece models](#routed-standing-hulls-for-many-piece-models) | Builder and tools | Models with more than 16 collision pieces get one routed standing hull (same solid set, nested routing) instead of a long chain of pieces, in CHIM and in the legacy converter alike; tools/hull_chain_audit.py sweeps every map for deep hull chains. --model-hull (auto, chain, routed or balanced) keeps every method selectable. | not measured |
| [CHIMport: the whole island, cell by cell](#chimport-the-whole-island-cell-by-cell) | Builder and tools | An autobuilder that converts every exterior cell with everything placed in it to CHIM, from the sea at the edge of the map inwards ring by ring, runs every builder audit on each cell, records its figures and feeds the CHIM Progress Tracker. | not measured |
| [Memory estimator](#memory-estimator) | Builder and tools | A predictor of how many bytes the chunk zone must hold at any position on the island, before anything is built, from the distinct models in the ring, terrain, catalogue entries and textures. | about 20 % to 40 % accuracy |
| [Vivec on CHIM (milestone M3)](#vivec-on-chim-milestone-m3) | Roadmap | Stage A moves the Vivec Arena canton onto CHIM with the v0.0.32 parity gates; stage B puts all of Vivec in one frame (world format 0.6, sectors in one folder per sector row). | not measured |
| [Lighting audit in the cell tracker](#lighting-audit-in-the-cell-tracker) | Builder and tools | Every exterior cell is checked for light like the original: its original lights by class, with and without a mesh, how each reaches the frame (baked, night lamps only, not at all) and the share of lit surfaces. Lit is required for both completion levels; cells that wait only for light are shown as awaiting lighting. | not measured |
| [Lit like the original](#lit-like-the-original) | Rendering and visibility | The hybrid lighting type (builder default, --chim-lighting-type): Morrowind lights as Quake light entities baked into CHIM terrain lightmaps with lightstyles for flicker and pulse, one light level per placed model, the nearest sources of every class as dynamic lights, and per-plant glow generated at build time. | not measured |

### Planned

| Feature | Area | What it does | Measured gain |
| --- | --- | --- | --- |
| [Mold shells for distant landmarks](#mold-shells-for-distant-landmarks) | Rendering and visibility | Closed low-poly shells for landmarks such as Vivec's cantons, so they stand on the horizon without paying for their full detail. | not measured |
| [The open world on CHIM (milestone M4)](#the-open-world-on-chim-milestone-m4) | Roadmap | A fixed grid of frames of 3 x 3 cells covers the whole island; the engine keeps up to four frames resident and shifts the origin when you cross a frame edge, with no map load. | not measured |
| [The whole game on one legacy-safe hard file](#the-whole-game-on-one-legacy-safe-hard-file) | Roadmap | With every asset stored once, the world itself should come to about 1 GB, so the whole game fits one hard file that a classic Amiga can use, where today's pipeline would need about 24 GB. | about 1 GB against about 24 GB |

### Idea

| Feature | Area | What it does | Measured gain |
| --- | --- | --- | --- |
| [Run-time scale and tilt of shared models](#run-time-scale-and-tilt-of-shared-models) | World format and disk | One model per mesh instead of one variant per scale and tilt: the largest model-byte saving left island-wide, though hulls stay per variant. | not measured |
| [Terrain generated from a heightfield at load](#terrain-generated-from-a-heightfield-at-load) | World format and disk | Generate the ground from height samples when a chunk loads instead of storing its faces, once the 68040 cost of doing so is measured. | not measured |
| [Shared interior props with per-placement lighting](#shared-interior-props-with-per-placement-lighting) | World format and disk | Store interior props once and light each placement separately, which would remove the per-map model limit indoors. | not measured |

## Features

### World format and disk

#### Every asset stored once

**Status:** In this release (CHIM 0.1.0). **ID:** `stored-once`.

Every mesh, collision hull and texture of an exterior is stored once and placed by reference, instead of being copied into every region map that can see it.

**Measured gain:**

- Balmora exterior: 162.1 MB of legacy region maps to 21.3 MB of CHIM world (7.62 times smaller). Compared: the 64 legacy region maps of a v0.0.32 development image against the CHIM world (index, frame and chunk sections) plus its frame map, world format 0.5; interiors are the same in both and left out. *builder output, 9 October 2026.*
- Seyda Neen with the intro docks and the courtyard: 190.4 MB to 7.83 MB (24.3 times smaller). Compared: the 66 recorded legacy maps v0.0.32 ships against the CHIM world (51 files and 3 frame maps), world format 0.5. *builder output, 9 October 2026.*
- Legacy layout: each exterior object is stored about 9.8 times (about 1.4 million copies of 143,147 placements over the island, about 20 GB of maps); CHIM stores each placement once. Compared: the whole-world estimate behind WORLD-REGION-DUPLICATION-31; the CHIM figure for the whole island comes with the open world on CHIM (milestone M4). *estimate, 8 October 2026.*

**Visibility:** Each placement is linked to the visibility leaves its box touches (Quake's efrags) and is drawn once, from its owner chunk, so the PVS still culls it. Sharing a model never turns it into a brush entity; placements over 16 leaves are counted by the validator.

**Caveats:**

- The island-wide CHIM size is not measured yet; only Balmora and Seyda Neen are built as CHIM worlds.

**Read more:** [World streamer design](../WORLD_STREAMER.md); [CHIM world format](WORLD_FORMAT.md); [Draft v0.0.33 release notes, disk](../RELEASE-v0.0.33.md#disk-each-asset-once); [Measurements behind the release charts](../performance/CHIM-v0.0.33-MEASUREMENTS.json).

**Bugs:** [WORLD-REGION-DUPLICATION-31](../bugs/WORLD-REGION-DUPLICATION-31.md).

#### Pure CHIM towns: no legacy maps shipped

**Status:** In this release (CHIM 0.1.0). **ID:** `pure-chim-towns`.

Balmora and Seyda Neen (with the intro docks and the courtyard) are drawn only by CHIM; the legacy region maps of a CHIM town are neither built nor shipped. Seyda Neen is regenerated from your data, so the temporary heap bypass for three recorded maps ends.

**Measured gain:** Not measured. The gain is the disk figure of the entry above; the effect on build time of the legacy exterior chain is not measured yet.

**Visibility:** A town runs as one frame map: terrain is world geometry, so Quake's visibility and collision work on it as on any map.

**Caveats:**

- CHIM builds still run part of the legacy exterior chain (the open world, the Vivec Arena and Balmora's region maps) and record which stages and who reads them; moving the frame maps and town flora off that chain is still to do (CHIM-LEGACY-CHAIN-33).
- The countryside between the towns still ships as legacy region maps, marked "not yet CHIM", until milestone M4.

**Read more:** [CHIM engine: towns](ENGINE.md#towns); [Builder types](build_guide/BUILDER_TYPES.md); [Draft v0.0.33 release notes](../RELEASE-v0.0.33.md).

**Bugs:** [CHIM-LEGACY-CHAIN-33](../bugs/CHIM-LEGACY-CHAIN-33.md), [BUILD-SEYDA-REGEN-30](../bugs/BUILD-SEYDA-REGEN-30.md), [HEAP-SEYDA-OVERLAP-32](../bugs/HEAP-SEYDA-OVERLAP-32.md).

#### Texture effects (.chimfx)

**Status:** In this release (CHIM 0.1.0). **ID:** `texture-effects`.

An optional effect file can add specks of chosen colours to chosen textures, identical in every build and off unless selected. It began as a bug: the first CHIM worlds showed bright specks because their textures skipped the palette guard.

**Measured gain:** Not measured. A feature, not a speed or size gain. The bug itself is repaired: the CHIM world now goes through the same palette guard as the legacy maps, and the validator refuses sky-bank texels.

**Visibility:** Not applicable: effects change texels, not geometry.

**Read more:** [CHIM texture effects](TEXTURE_EFFECTS.md).

**Bugs:** [CHIM-TEXTURE-SPECKS-33](../bugs/CHIM-TEXTURE-SPECKS-33.md).

**Commits:** `8caf66e`.

#### Run-time scale and tilt of shared models

**Status:** Idea. **ID:** `runtime-scale-tilt`.

One model per mesh instead of one variant per scale and tilt: the largest model-byte saving left island-wide, though hulls stay per variant.

**Measured gain:** Not measured; to be measured with the engine first.

**Visibility:** Not designed in detail yet; any implementation is checked with the renderer counters like every CHIM change.

**Read more:** [CHIM ideas: also held back](IDEAS.md#also-held-back).

#### Terrain generated from a heightfield at load

**Status:** Idea. **ID:** `heightfield-terrain`.

Generate the ground from height samples when a chunk loads instead of storing its faces, once the 68040 cost of doing so is measured.

**Measured gain:** Not measured.

**Visibility:** Terrain must stay world geometry, so that it occludes and is culled like stored terrain.

**Read more:** [CHIM ideas: also held back](IDEAS.md#also-held-back).

#### Shared interior props with per-placement lighting

**Status:** Idea. **ID:** `shared-interior-props`.

Store interior props once and light each placement separately, which would remove the per-map model limit indoors.

**Measured gain:** Not measured.

**Visibility:** Interiors keep Quake's vis today; shared props would have to keep it, checked with the renderer counters.

**Caveats:**

- Interiors stay ordinary Quake maps in CHIM 0.1.0, where Quake's vis works well.

**Read more:** [World streamer](../WORLD_STREAMER.md); [CHIM ideas: also held back](IDEAS.md#also-held-back).

### Streaming and memory

#### Streaming with no region stop

**Status:** In this release (CHIM 0.1.0). **ID:** `chunk-streaming`.

The land is cut into chunks of 256 units. A ring of chunks around the player is resident and chunks join and leave a little at a time, within a per-frame budget, so crossing a region border no longer loads a whole map.

**Measured gain:**

- Bytes read on the Balmora door walk: 73.5 MB to 40.7 MB. Compared: the same walk through all 70 load doors (16,007 units): 18 legacy region map loads against 83 chunk crossings, from the builder's walk report, world format 0.2. *builder output, 8 October 2026.*
- Median read time per area change: 94 ms to 21 ms; longest read stall 112 ms to 71 ms. Compared: file reads of that walk replayed in FS-UAE (cycle-approximate 68040), busy host, one session with a drift-control rerun. *emulator, relative, busy host, 8 October 2026.*

**Visibility:** Chunks are linked into the frame world's leaves; the visibility rows of the chunk the camera is in decide which leaves are visited. Streaming never changes how the PVS culls what is already resident.

**Caveats:**

- The total read time over the walk is the same, 1.64 s legacy against 1.65 s CHIM: CHIM spreads it thinner, it does not remove it.
- To be repeated with the release world (format 0.5) on a quiet host.

**Read more:** [CHIM engine: loading](ENGINE.md#loading); [Draft v0.0.33 release notes, loading](../RELEASE-v0.0.33.md#loading-smaller-steps-no-region-stop); [Measurements behind the release charts](../performance/CHIM-v0.0.33-MEASUREMENTS.json).

**Bugs:** [CHIM-READ-RUNS-33](../bugs/CHIM-READ-RUNS-33.md), [CHIM-READ-BUDGET-33](../bugs/CHIM-READ-BUDGET-33.md), [BENCH-JIT-PROFILE-32](../bugs/BENCH-JIT-PROFILE-32.md).

#### Incremental frame world

**Status:** In this release (CHIM 0.1.0). **ID:** `incremental-frame-world`.

When a chunk joins or leaves the ring, only the leaves it touches are relinked, instead of rebuilding the whole frame world on every crossing. The full rebuild is kept as a selectable method (chim_graft_mode 0).

**Measured gain:**

- At most 16 KB copied per update instead of 405 KB; 85 chunk copies instead of 4,504. Compared: the same walk (1,536 units east and back) on Balmora's frame map, full rebuild against the incremental method with its defaults. *emulator, relative, busy host, 9 October 2026.*
- Median update time 0.42 ms against 0.9 ms (1.7 ms in the drift-control rerun). Compared: the same session, FS-UAE with the JIT. *emulator, relative, busy host, 9 October 2026.*

**Visibility:** On the five benchmark cameras both methods give identical renderer counters (entities sent, BSP nodes per clipped face), so visibility culling is unchanged.

**Caveats:**

- Relative emulator numbers; the cycle-exact run is pending.

**Read more:** [CHIM engine: the frame world](ENGINE.md#the-frame-world); [Renderer counters](../performance/RENDERER-COUNTERS.md).

**Bugs:** [CHIM-REBUILD-COST-33](../bugs/CHIM-REBUILD-COST-33.md), [CHIM-TERRAIN-GRAFT-33](../bugs/CHIM-TERRAIN-GRAFT-33.md).

**Commits:** `839b36e`.

#### Chunk pinning: no holes in the town

**Status:** In this release (CHIM 0.1.0). **ID:** `chunk-pinning`.

Chunks are pinned only while they load, farther chunks give way first, small blocks come from the high end of the memory zone and the ground never waits for a building. A chunk shows as soon as its ground is in.

**Measured gain:**

- Steps with a chunk missing its ground inside the collision margin on the owner's Balmora route: 860 to 0. Compared: the engine's own zone allocator run over the route twice (1,192 steps), first methods against all methods with defaults; Seyda Neen sweep of the frame with rows 128 units apart: 107 to 0. *host simulation, 9 October 2026.*
- In the emulator on the same route: nearest chunk without ground 69 units to 438 units away, failed chunk loads 180 to 95, bytes read 24.8 MB to 16.7 MB. Compared: CHIM preview engine against the repaired engine with its defaults, JIT preset, seven poses with a short walk at each, twice. *exact counts, 9 October 2026.*

**Visibility:** Pinning decides which chunks are resident, not how they are culled; placements stay linked to the leaves they touch.

**Caveats:**

- Some loads still fail for lack of room (far buildings); a larger zone budget would halve the remaining gaps and waits for the memory measurements (CHIM-ZONE-BUDGET-33).
- The repaired engine awaits the owner's playtest.

**Read more:** [Draft v0.0.33 release notes, Balmora's holes](../RELEASE-v0.0.33.md#lets-fix-those-bugs); [CHIM engine: memory](ENGINE.md#memory).

**Bugs:** [CHIM-CHUNK-LOAD-FAIL-33](../bugs/CHIM-CHUNK-LOAD-FAIL-33.md), [CHIM-ZONE-BUDGET-33](../bugs/CHIM-ZONE-BUDGET-33.md), [CHIM-ZONE-RING-THRASH-33](../bugs/CHIM-ZONE-RING-THRASH-33.md).

#### Strict heap gate and a fixed chunk zone

**Status:** In this release (CHIM 0.1.0). **ID:** `heap-gate-and-zone`.

CHIM reserves one chunk zone of fixed size in the Hunk when a town loads. The builder checks every CHIM area against the engine's own numbers (active ring, load ring, largest block) before the game ever runs.

**Measured gain:**

- Seyda Neen passes the strict heap gate with 558 KB to spare inside the zone, where the legacy map sn019 was 238 KB over its budget and shipped through a temporary bypass. Compared: builder heap gate, legacy v0.0.32 recorded maps against the CHIM world. *builder output, 9 October 2026.*

**Visibility:** Not applicable: memory accounting only.

**Caveats:**

- The zone is taken from the Hunk, so less Hunk is left at the load peak: Balmora 2.32 MB (legacy 3.53 MB), Seyda Neen 1.10 MB (legacy 4.42 MB), which is under the 2 MiB rule (CHIM-SEYDA-HUNK-GAP-33, open).
- The zone size is an interim 7,680 KiB in the builder; the owner decision is pending (CHIM-ZONE-BUDGET-33).

**Read more:** [CHIM engine: memory](ENGINE.md#memory); [Draft v0.0.33 release notes, memory](../RELEASE-v0.0.33.md#memory); [CHIM ideas: memory](IDEAS.md#memory).

**Bugs:** [CHIM-SEYDA-HUNK-GAP-33](../bugs/CHIM-SEYDA-HUNK-GAP-33.md), [CHIM-ZONE-BUDGET-33](../bugs/CHIM-ZONE-BUDGET-33.md), [CHIM-HEAP-CHECK-33](../bugs/CHIM-HEAP-CHECK-33.md), [HEAP-SEYDA-OVERLAP-32](../bugs/HEAP-SEYDA-OVERLAP-32.md).

#### Statics and flora sprites streamed with their chunks

**Status:** In this release (CHIM 0.1.0). **ID:** `sprite-statics-streamed`.

The frame map tags its static models and flora sprites with their chunk; the engine loads and links them when the chunk joins the ring and frees them when it leaves, instead of holding all of them in the map's fixed cost in the Hunk.

**Measured gain:**

- Seyda Neen: largest free Hunk gap after the first load 1,099,200 B to more than 2,097,200 B. Compared: the same Seyda Neen position with the frame map's statics resident against streamed with their chunks (FS-UAE A/B). *emulator, relative, busy host, 9 October 2026.*

**Visibility:** Not a drawing change: the sprites stay ordinary static entities, only their loading moves with the chunks.

**Caveats:**

- The frame map and the engine must match: a frame map with tagged statics needs this engine (both ship together).

**Read more:** [CHIM ideas: memory](IDEAS.md#memory).

**Bugs:** [CHIM-SEYDA-HUNK-GAP-33](../bugs/CHIM-SEYDA-HUNK-GAP-33.md).

### Rendering and visibility

#### Quake's visibility culling kept effective

**Status:** In this release (CHIM 0.1.0). **ID:** `vis-kept`.

Placements are linked to the leaves they touch, terrain is world geometry with shallow per-chunk trees, and each chunk carries a row of the placements a view from it may see. Nothing is a func_wall that vis ignores.

**Measured gain:**

- Brush models sent to the renderer: 512-654 to 46-114; BSP nodes walked per clipped face: 27-52 to 8.6-9.9. Compared: the five fixed Balmora benchmark cameras, legacy region maps against CHIM (dbg rcount; the legacy figure is its brush-model passes). *exact counts, 8 October 2026.*
- Faces clipped 5-25 % fewer; spans drawn 1-6 % more. Compared: the same cameras; surface cache builds are 0 on both. *exact counts, 8 October 2026.*

**Visibility:** This is the vis story itself: every CHIM change is checked with the renderer counters (entities sent, faces clipped, BSP nodes per face) on fixed cameras, and they may not get worse.

**Caveats:**

- CHIM draws slightly more spans than the legacy maps at every camera.
- Per-placement lists block 11.5 % of the visibility tests in Balmora (CHIM-PVS-HOLLOW-33): hollow house shells let rows see through buildings.
- A few models dominate every view; distance detail is the owner (CHIM-VIEW-FACES-33).

**Read more:** [CHIM engine: vis and culling](ENGINE.md#vis-and-culling); [World streamer: visibility requirement](../WORLD_STREAMER.md#visibility-and-culling-requirement); [Town visibility](../performance/TOWN-VISIBILITY.md); [Renderer counters](../performance/RENDERER-COUNTERS.md).

**Bugs:** [CHIM-PVS-HOLLOW-33](../bugs/CHIM-PVS-HOLLOW-33.md), [CHIM-VIEW-FACES-33](../bugs/CHIM-VIEW-FACES-33.md), [TOWN-VIS-OCCLUSION-31](../bugs/TOWN-VIS-OCCLUSION-31.md).

#### Terrain as world geometry

**Status:** In this release (CHIM 0.1.0). **ID:** `terrain-world-geometry`.

Each chunk's ground is a small BSP subtree grafted under the frame's world, so Quake's visibility, collision and water work on it as on any map, and the terrain occludes what lies behind it.

**Measured gain:** Not measured on its own; its effect is part of the renderer counters under "Quake's visibility culling kept effective".

**Visibility:** The grafted terrain is part of the world tree, so it occludes and is culled by the PVS; a brush-entity terrain would not.

**Read more:** [CHIM overview](README.md#what-chim-is); [CHIM engine: the frame world](ENGINE.md#the-frame-world).

**Bugs:** [CHIM-TERRAIN-GRAFT-33](../bugs/CHIM-TERRAIN-GRAFT-33.md).

#### Faster frames in town

**Status:** In this release (CHIM 0.1.0). **ID:** `frame-time`.

The shallow per-chunk trees and the far smaller number of models sent to the renderer cut the time a frame takes at the Balmora cameras.

**Measured gain:**

- Slow preset (cycle-exact 68040 at about 50 MHz): median frame 2.0-4.1 s to 1.1-1.6 s, 1.6-2.6 times faster. Compared: the five Balmora cameras, legacy v0.0.32 disks against CHIM with the preview engine (0d8bf4f, world format 0.4); a legacy rerun in the same session agrees within 0.3-5 %. *emulator, relative, busy host, 9 October 2026.*
- Standard (JIT) preset: median frame 40-87 ms to 15-20 ms, 2.6-4.4 times faster. Compared: the same cameras, one session, world format 0.4. *emulator, relative, busy host, 8 October 2026.*

**Visibility:** The gain comes from the counters of the previous entry: fewer brush models sent and shallower trees, with the same potentially visible set.

**Caveats:**

- Emulator numbers are relative until a frame has been measured on a real accelerated Amiga.
- CHIM spends 17-28 % more time outside the 3D view (streaming and the frame world), measured at two of the cameras.
- The JIT figures have no drift-control rerun and vary about 2 times between busy-host sessions; a quiet-host session is still to be measured.

**Read more:** [Draft v0.0.33 release notes, frame time](../RELEASE-v0.0.33.md#frame-time-and-renderer-counters); [Measurements behind the release charts](../performance/CHIM-v0.0.33-MEASUREMENTS.json); [CHIM ideas: the slow-accelerator reality](IDEAS.md#the-slow-accelerator-reality).

**Bugs:** [BENCH-JIT-PROFILE-32](../bugs/BENCH-JIT-PROFILE-32.md), [CHIM-VIEW-FACES-33](../bugs/CHIM-VIEW-FACES-33.md).

#### Far terrain: the distant view

**Status:** In this release (CHIM 0.1.0). **ID:** `far-terrain`.

A resident low-detail layer of the land for the frame and beyond its edge (maps/<frame map>.far, written once per frame by the builder), drawn past the fog plane in the fog colour like the v0.0.32 horizon, so valleys and far land are not empty fog.

**Measured gain:**

- Far layer in the low Hunk: 13.2 KB for Balmora; drawing it costs 30.6-43.7 ms per frame on the slow preset at the bridge and east-bank poses. Compared: the far layer on and off at the owner's bridge pose and the east-bank pose (docs/chim/FAR_TERRAIN.md, Cost). *emulator, relative, busy host, 9 October 2026.*

**Visibility:** The far layer is drawn beyond the ring the way the approved horizon draws land at the fog plane, from the same height samples as the chunk terrain; it is checked with the renderer counters against the v0.0.32 horizon before it counts.

**Caveats:**

- Distant buildings are not drawn yet: the far layer carries the land only (chim_far_objects 0). The v0.0.32 house silhouettes on the horizon are a known issue of v0.0.33 (CHIM-FAR-OBJECTS-33).
- Emulator numbers are relative until a frame has been measured on a real accelerated Amiga.

**Read more:** [Far terrain: design and measurements](FAR_TERRAIN.md); [CHIM ideas: the distant view](IDEAS.md#the-distant-view-far-terrain-and-mold-shells); [Distant terrain](../DISTANT_TERRAIN.md).

**Bugs:** [CHIM-FAR-TERRAIN-33](../bugs/CHIM-FAR-TERRAIN-33.md), [CHIM-FAR-OBJECTS-33](../bugs/CHIM-FAR-OBJECTS-33.md).

#### Mold shells for distant landmarks

**Status:** Planned. **ID:** `mold-shells`.

Closed low-poly shells for landmarks such as Vivec's cantons, so they stand on the horizon without paying for their full detail.

**Measured gain:** Not measured. The shell tool exists and was measured on a Balmora map; the engine switch is designed but not built, so there is no in-game gain yet.

**Visibility:** Shells are closed low-poly bodies drawn in place of the full distant model; the renderer counters decide whether they are kept.

**Read more:** [Distant shells](../DISTANT_SHELLS.md); [CHIM ideas: the distant view](IDEAS.md#the-distant-view-far-terrain-and-mold-shells).

#### Lit like the original

**Status:** In progress. **ID:** `lit-like-the-original`.

The hybrid lighting type (builder default, --chim-lighting-type): Morrowind lights as Quake light entities baked into CHIM terrain lightmaps with lightstyles for flicker and pulse, one light level per placed model, the nearest sources of every class as dynamic lights, and per-plant glow generated at build time.

**Measured gain:** Not measured. In source: light sources in styles 32-36 with generated flicker and pulse strings, and the night lamp table widened from 694 to 2,962 exterior sources. Measured in memory and bake time (docs/chim/LIGHTING.md): terrain lightmaps add 17 KB to the Balmora ring and 27 KB to Seyda Neen. The look is not measured yet.

**Visibility:** Adds no entity or brush: light entities exist only at bake time and the per-placement level rides in the placement record; renderer counters are compared before and after.

**Caveats:**

- Balmora has 2,528 bytes of active-ring headroom: any stored light needs room made there first.

**Read more:** [CHIM lighting](LIGHTING.md); [CHIM lights roadmap](LIGHTING_ROADMAP.md).

**Bugs:** [CHIM-BALMORA-LIGHT-ROOM-33](../bugs/CHIM-BALMORA-LIGHT-ROOM-33.md), [CHIM-LIGHT-CONTENTS-33](../bugs/CHIM-LIGHT-CONTENTS-33.md), [LIGHT-ENTITIES-UNWIRED-33](../bugs/LIGHT-ENTITIES-UNWIRED-33.md), [LIGHT-STYLES-UNDEFINED-33](../bugs/LIGHT-STYLES-UNDEFINED-33.md).

### Characters

#### Modular NPCs

**Status:** In progress. **ID:** `modular-npcs`.

Humanoid NPCs are assembled from shared body parts converted once, with one small recipe per actor, instead of one complete baked model per actor. Equipment changes and looting can then change how an actor looks. The baked whole-actor method stays selectable.

**Measured gain:**

- The 2,675 humanoid NPC records resolve to about 3,500 appearances made of only 1,726 distinct body parts (942 mesh files), each used about 39 times; baking whole models processes 12.3 million source triangles, the distinct parts hold about 0.4 million. Compared: a census of the game's own data. *census of the game data, 9 October 2026.*

A census, not a CHIM run. The expected drop of the NPC gallery stage from about half an hour to a few minutes is an expectation, not a measurement.

**Visibility:** The engine composes one ordinary Quake alias model per appearance when it loads, so the renderer and its culling are unchanged.

**Caveats:**

- The host prototype and its tests exist; the engine side (load-time composition) is not built yet.
- Measured and dropped: attaching parts as follower entities costs about 19 entity setups per actor per frame, too much for the slow 68040 target.

**Read more:** [Modular NPCs](../MODULAR_NPCS.md); [NPC model cache](../NPC_MODEL_CACHE.md); [Character equipment roadmap](../CHARACTER_EQUIPMENT_ROADMAP.md).

**Bugs:** [NPC-BAKED-WHOLE-DUPLICATION-33](../bugs/NPC-BAKED-WHOLE-DUPLICATION-33.md).

#### NPC pathfinding and companions

**Status:** In progress. **ID:** `npc-pathfinding`.

A ladder that starts with plain Quake chase movement and stair climbing, and escalates only when stuck: a local ping, then A* on a small walkable graph stored with the chunks. dbg companion is a prototype follower that tests the first steps.

**Measured gain:** Not measured yet. Budgets are fixed up front: at most two traces per think and 48 bytes of state per follower.

**Visibility:** Pathfinding reads the walkable graph and collision, not the render tree; it does not change what is drawn.

**Caveats:**

- dbg companion is a test bed (not saved). Followers through doors and the A* patch are designed, not built.
- A scripted actor step could move the chunk ring to the actor; fixed in source (CHIM-ACTOR-RING-33).

**Read more:** [CHIM NPC pathfinding](CHIM_NPC_PATHFINDING.md); [NPC pathfinding](../NPC_PATHFINDING.md); [Console commands: dbg companion](../AMIWIND_CONSOLE_COMMANDS.md).

**Bugs:** [CHIM-ACTOR-RING-33](../bugs/CHIM-ACTOR-RING-33.md).

### Engine

#### No disk writes during play

**Status:** In this release (CHIM 0.1.0). **ID:** `logs-in-memory`.

Diagnostic logs stay in memory during play and are written on request or when the game is left, so a closed emulator or a power cut no longer lands in the middle of a write and leaves the volume "not validated".

**Measured gain:**

- Time spent "not validated" during play: 3.7 % to 0 %; write bursts during play: 6 in 410 s to 0 in 1,355 s. Compared: previous engine against logs in memory, slow setting (cycle-exact 68040, CPU multiplier 14), three sessions of 510, 311 and 534 s. *emulator, relative, busy host, 9 October 2026.*

**Visibility:** Not applicable.

**Caveats:**

- Autosaves are not covered by these runs.

**Read more:** [Draft v0.0.33 release notes](../RELEASE-v0.0.33.md).

**Bugs:** [BOOT-VOLUME-NOT-VALIDATED-33](../bugs/BOOT-VOLUME-NOT-VALIDATED-33.md).

**Commits:** `12a3931`.

#### dbg tp, doors and saves on CHIM towns

**Status:** In this release (CHIM 0.1.0). **ID:** `tp-and-scene-lookup`.

Every check that a scene exists (dbg tp arrivals, quick start, doors, saves and loads, the scene picker) goes through one function that finds the scene's map or the town's CHIM frame map, so a pure CHIM image works with the same commands as a legacy one. A save made in CHIM Balmora loads in either kind of image.

**Measured gain:** Not measured. Not a performance feature.

**Visibility:** Not applicable.

**Read more:** [CHIM engine: towns](ENGINE.md#towns); [Console commands](../AMIWIND_CONSOLE_COMMANDS.md).

#### Legacy and CHIM side by side

**Status:** In this release (CHIM 0.1.0). **ID:** `legacy-side-by-side`.

chim_towns 0 brings back the legacy region maps for an A/B in one session; the console states which mode every town runs in, and start-up prints how many towns are on CHIM. No working method is deleted.

**Measured gain:** Not measured. A tool for measuring; every CHIM against legacy figure on this page was made this way.

**Visibility:** Not applicable.

**Read more:** [CHIM engine: towns](ENGINE.md#towns); [CHIM overview: design rules](README.md#design-rules).

### Builder and tools

#### Zone walk gate

**Status:** In this release (CHIM 0.1.0). **ID:** `zone-walk-gate`.

The builder runs the engine's own zone code over a walk through every frame and fails the build when a step leaves the player without ground.

**Measured gain:** Not measured. A build gate, not a speed or size gain. It is how the chunk-loading fix above is kept from regressing.

**Visibility:** Not applicable: the gate checks memory behaviour, not drawing.

**Read more:** [Island-wide audits](IDEAS.md#island-wide-audits-mechanism-classes); [CHIM world format: the heap gate](WORLD_FORMAT.md).

**Bugs:** [CHIM-CHUNK-LOAD-FAIL-33](../bugs/CHIM-CHUNK-LOAD-FAIL-33.md), [CHIM-ZONE-TMP-NOEXEC-33](../bugs/CHIM-ZONE-TMP-NOEXEC-33.md).

#### Island-wide audits as build gates

**Status:** In this release (CHIM 0.1.0). **ID:** `island-wide-audits`.

Each geometry or collision finding names its mechanism, sweeps every mesh that goes through the same converter path, is fixed once in the shared converter and stays as a gate: seam tears, the stair walk of every flight, terrain hull bevels, sky-bank texels and the memory fit.

**Measured gain:** Not measured. Quality gates. For example, the silt strider's open hull (sky showing through its shell) was fixed once, and every caravan town places the same repaired model.

**Visibility:** Not applicable: the audits are about geometry and collision correctness.

**Caveats:**

- Hidden faces (placed-model faces buried under the terrain) are an open audit (CHIM-HIDDEN-FACES-33).

**Read more:** [CHIM ideas: island-wide audits](IDEAS.md#island-wide-audits-mechanism-classes); [Stair rules](../STAIR_RULES.md).

**Bugs:** [CHIM-TERRAIN-HULL-BEVELS-33](../bugs/CHIM-TERRAIN-HULL-BEVELS-33.md), [CHIM-HIDDEN-FACES-33](../bugs/CHIM-HIDDEN-FACES-33.md), [COLLISION-STAIR-SLOPE-32](../bugs/COLLISION-STAIR-SLOPE-32.md).

#### Routed standing hulls for many-piece models

**Status:** In progress. **ID:** `routed-hulls`.

Models with more than 16 collision pieces get one routed standing hull (same solid set, nested routing) instead of a long chain of pieces, in CHIM and in the legacy converter alike; tools/hull_chain_audit.py sweeps every map for deep hull chains. --model-hull (auto, chain, routed or balanced) keeps every method selectable.

**Measured gain:** Not measured as a frame-time gain yet. The audit found 183 models of 63 meshes with hull chains 512 or more deep on the v0.0.33-dev1 full build (COLLISION-HULL-CHAINS-33).

**Visibility:** Not a drawing change: collision only.

**Caveats:**

- v0.0.33 shipped --model-hull chain: routed hulls pushed an open-world map past its flora collision reserve (BUILD-ROUTED-FLORA-RESERVE-33). After v0.0.33 auto is the default again: that map falls back to chains, CHIM routes every chain deeper than 256 clipnodes (routed_hull.CHAIN_DEPTH_LIMIT, the same rule the hull audits read), and a ring over the zone keeps its smallest routed meshes as chains (chim_build hull fallback). Measured on the emulator (relative numbers): a trace near a Balmora house costs 12-33 ms as a chain and 2.8-3.6 ms routed on the slow preset (COLLISION-TRACE-COST-33). chain, routed and balanced stay selectable.

**Read more:** [Collision hull chains](../bugs/COLLISION-HULL-CHAINS-33.md); [CHIMport: hull policy pending](CHIMPORT.md#hull-policy-pending).

**Bugs:** [BUILD-ROUTED-FLORA-RESERVE-33](../bugs/BUILD-ROUTED-FLORA-RESERVE-33.md), [CHIM-HULL-CHAIN-COST-33](../bugs/CHIM-HULL-CHAIN-COST-33.md), [COLLISION-HULL-CHAINS-33](../bugs/COLLISION-HULL-CHAINS-33.md), [ROUTED-HULL-NODE-ORDER-33](../bugs/ROUTED-HULL-NODE-ORDER-33.md).

#### The CHIM builder

**Status:** In this release (CHIM 0.1.0). **ID:** `chim-builder`.

tools/build.py --builder chim builds the CHIM world from your own Morrowind data with the same stages, --jobs, profiler and receipts as before; receipts record builder, chim_version and world_format. The legacy builder stays in the code and selectable.

**Measured gain:**

- Balmora exterior stage: 5.2 minutes wall and 5.1 CPU minutes on CHIM against 8.5 minutes wall and 24.1 CPU minutes for the 64 legacy region maps. Compared: two different builds: CHIM on a 6-thread build with the host about 98 % busy, legacy on a 24-thread build on a quiet host. *builder output, mixed host, 9 October 2026.*

**Visibility:** The builder links every placement to its leaves and writes the visibility rows; a build that makes the counters worse fails its gate.

**Caveats:**

- Different builds and host loads, so wall times are not a matched pair; a matched from-scratch pair on a quiet host is still to be run.

**Read more:** [Builder types](build_guide/BUILDER_TYPES.md); [CHIM build statistics](STATS.md); [Draft v0.0.33 release notes, build time](../RELEASE-v0.0.33.md#build-time).

**Bugs:** [CHIM-LEGACY-CHAIN-33](../bugs/CHIM-LEGACY-CHAIN-33.md), [CHIM-RECEIPT-COMMIT-33](../bugs/CHIM-RECEIPT-COMMIT-33.md).

#### CHIMport: the whole island, cell by cell

**Status:** In progress. **ID:** `chimport`.

An autobuilder that converts every exterior cell with everything placed in it to CHIM, from the sea at the edge of the map inwards ring by ring, runs every builder audit on each cell, records its figures and feeds the CHIM Progress Tracker.

**Measured gain:** Not measured. First island-wide run (9 October 2026): 1,292 cells, 716 done (613 passed, 103 empty sea), 546 hull policy pending, 26 failed, 4 not converted; 1,436 distinct meshes converted about once each with content-keyed units.

**Visibility:** Each cell frame keeps its own visibility rows, checked by the validator in every cell; the vis figures are recorded per cell.

**Caveats:**

- Cells are one-cell frames for now; the open world joins them into 3 x 3 cell frames.
- Actors and creatures are deferred to the actor pipeline and counted per cell.

**Read more:** [CHIMport](CHIMPORT.md); [Hull policy pending](CHIMPORT.md#hull-policy-pending).

**Bugs:** [CHIM-UNIT-FP-SOURCE-LAYOUT-33](../bugs/CHIM-UNIT-FP-SOURCE-LAYOUT-33.md), [CHIM-WORLD-AUDIT-SCALING-33](../bugs/CHIM-WORLD-AUDIT-SCALING-33.md), [CHIM-MEASURE-EMPTY-FRAME-33](../bugs/CHIM-MEASURE-EMPTY-FRAME-33.md), [CHIM-WINDOW-MOUNT-CROSS-CELL-33](../bugs/CHIM-WINDOW-MOUNT-CROSS-CELL-33.md).

#### Build cache and prerendered store

**Status:** In this release (CHIM 0.1.0). **ID:** `build-cache`.

Stage fingerprints let a development build reuse the finished stages of an earlier run, a per-file asset pool reuses converted sounds and movies, a per-map pass cache reuses the image step's optimizer, cull and stair-walk passes, and the prerendered store (--prerendered DIR) keeps finished stage outputs (CHIM worlds, interiors, region maps) across runs and workspaces. Releases write the store but never read it.

**Measured gain:**

- Image step on MiniWind maps, warm: BSP optimizer 388 s to 5.7 s, hidden-surface cull 48 s to 6.6 s, byte-identical outputs. Compared: the same MiniWind maps with and without the per-map pass cache (BUILD-IMAGE-NOT-INCREMENTAL-33). *builder output, busy host, 9 October 2026.*

**Visibility:** Not applicable.

**Caveats:**

- Release candidates and finals are always built from scratch and refuse every shortcut.

**Read more:** [CHIM ideas: build speed](IDEAS.md#build-speed); [Build profile](../BUILD_PROFILE.md).

**Bugs:** [BUILD-CACHE-CHIM-UNITS-33](../bugs/BUILD-CACHE-CHIM-UNITS-33.md), [BUILD-CACHE-CLOSURE-WIDE-33](../bugs/BUILD-CACHE-CLOSURE-WIDE-33.md), [BUILD-CACHE-OVERBROAD-33](../bugs/BUILD-CACHE-OVERBROAD-33.md), [BUILD-IMAGE-NOT-INCREMENTAL-33](../bugs/BUILD-IMAGE-NOT-INCREMENTAL-33.md), [BUILD-PRERENDERED-PRUNE-ORDER-33](../bugs/BUILD-PRERENDERED-PRUNE-ORDER-33.md).

#### MiniWind quick test build

**Status:** In this release (CHIM 0.1.0). **ID:** `miniwind`.

A builder type for quick playtests: Balmora on CHIM with its interiors and what the engine needs, booting straight into Balmora. Development versions only; marked as a partial-area test.

**Measured gain:** Not measured in the public record yet; it is described as building in a fraction of the time of a full build.

**Visibility:** Not applicable: the same engine and world as a full build.

**Caveats:**

- Never a release: areas the build does not hold say "Area unavailable".

**Read more:** [MiniWind playtester build](../MINIWIND_PLAYTESTER.md).

**Bugs:** [CHIM-HARVEST-REMOVED-MAPS-33](../bugs/CHIM-HARVEST-REMOVED-MAPS-33.md).

#### Memory estimator

**Status:** In progress. **ID:** `memory-estimator`.

A predictor of how many bytes the chunk zone must hold at any position on the island, before anything is built, from the distinct models in the ring, terrain, catalogue entries and textures.

**Measured gain:**

- Accuracy about plus or minus 20 % at the load radius on towns like the ones it was fitted on, about 40 % on a town type it has not seen. Compared: coefficients fitted on built worlds, checked by leaving one town out. *host simulation, 9 October 2026.*

**Visibility:** Not applicable.

**Caveats:**

- A draft. It flags a handful of dense town cells over budget at the load radius; the heap gate on a built world always has the final word.

**Read more:** [CHIM ideas: the memory estimator](IDEAS.md#the-memory-estimator); [World estimate](../WORLD_ESTIMATE.md).

#### --heap-mb builder option

**Status:** In this release (CHIM 0.1.0). **ID:** `heap-mb-option`.

A builder option like --jobs: the map heap in MiB, exact, default 11; beyond the safe profile it prints one loud warning and runs anyway, and every gate uses the build's own value.

**Measured gain:** Not measured. Not a speed feature: it makes the map heap size an explicit, recorded build choice.

**Visibility:** Not applicable.

**Read more:** [CHIM ideas: memory](IDEAS.md#memory).

#### Lighting audit in the cell tracker

**Status:** In progress. **ID:** `light-tracker`.

Every exterior cell is checked for light like the original: its original lights by class, with and without a mesh, how each reaches the frame (baked, night lamps only, not at all) and the share of lit surfaces. Lit is required for both completion levels; cells that wait only for light are shown as awaiting lighting.

**Measured gain:** Not measured. A measurement, not a speed or size gain: island-wide 0 lit, 133 partial and 1,052 unlit converted cells, 2,284 lights without a mesh and 690 with one (9 October 2026).

**Visibility:** No effect on drawing: the audit reads the census and the build figures only.

**Read more:** [CHIM cell tracker](CELL_TRACKER.md); [CHIM lighting](LIGHTING.md).

**Bugs:** [LIGHT-ENTITIES-UNWIRED-33](../bugs/LIGHT-ENTITIES-UNWIRED-33.md).

### Roadmap

#### Vivec on CHIM (milestone M3)

**Status:** In progress. **ID:** `vivec-m3`.

Stage A moves the Vivec Arena canton onto CHIM with the v0.0.32 parity gates; stage B puts all of Vivec in one frame (world format 0.6, sectors in one folder per sector row).

**Measured gain:** Not measured yet.

**Visibility:** Canton bodies and the Temple are the first big closed masses CHIM meets: real occluders. Visibility rows and placements per view are measured and may not get worse than the legacy preview.

**Caveats:**

- In this release the Vivec Arena exterior is left out and says "Area unavailable" until M3 is done.

**Read more:** [CHIM ideas: M3](IDEAS.md#m3-vivec-on-chim); [CHIM overview: milestones](README.md#milestones).

**Bugs:** [VIVEC-ARENA-FRAME-EDGE-32](../bugs/VIVEC-ARENA-FRAME-EDGE-32.md), [VIVEC-ARENA-ACTORS-32](../bugs/VIVEC-ARENA-ACTORS-32.md).

#### The open world on CHIM (milestone M4)

**Status:** Planned. **ID:** `open-world-m4`.

A fixed grid of frames of 3 x 3 cells covers the whole island; the engine keeps up to four frames resident and shifts the origin when you cross a frame edge, with no map load.

**Measured gain:** Not measured. The first slice is Balmora with the grid frames east and west of it.

**Visibility:** The ring is centred on the player, so the memory peak does not depend on where frame edges are; dense places fit only by simpler distant models, a stated view budget or a larger zone.

**Caveats:**

- Until then the countryside between the towns ships as legacy region maps, marked "not yet CHIM".

**Read more:** [CHIM ideas: M4](IDEAS.md#m4-the-open-world); [CHIM engine: frame re-centring plan](ENGINE.md#frame-re-centring-plan-not-implemented); [CHIMport: the whole island converted cell by cell](CHIMPORT.md).

#### The whole game on one legacy-safe hard file

**Status:** Planned. **ID:** `one-disk-image`.

With every asset stored once, the world itself should come to about 1 GB, so the whole game fits one hard file that a classic Amiga can use, where today's pipeline would need about 24 GB.

**Measured gain:**

- About 1 GB for the world against about 24 GB with the legacy pipeline. Compared: estimated from the game's own data; CHIM 1.0 is the release in which the whole island runs on CHIM. *estimate, 8 October 2026.*

**Visibility:** Not applicable.

**Caveats:**

- An estimate, not a measurement. Every partition must stay under 2 GiB and start below 2 GiB on its drive.

**Read more:** [World streamer: disk budget](../WORLD_STREAMER.md#disk-budget); [Asset census](../ASSET_CENSUS.md).

**Bugs:** [WORLD-REGION-DUPLICATION-31](../bugs/WORLD-REGION-DUPLICATION-31.md).
