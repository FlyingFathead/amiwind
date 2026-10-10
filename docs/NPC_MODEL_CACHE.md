# Persistent NPC model conversion cache

Normal builds and image recovery MUST include the complete NPC/creature gallery.
This optimization reuses verified conversion work; it never omits models,
reduces catalogue coverage, changes polygon budgets or bypasses validation.
Any exception to either gallery's mandatory coverage/quality requires a specific
documented case and explicit approval from the project owner, outside the builder.
Build time, disk pressure and convenience are not approval.

<!-- contents start -->
## Contents

- [What rc10 implements](#what-rc10-implements)
- [Completion-driven scheduling in v0.0.25](#completion-driven-scheduling-in-v0025)
- [Reuse a stopped rc9 build](#reuse-a-stopped-rc9-build)
- [Capacity and limits](#capacity-and-limits)
- [Original heads](#original-heads)
- [Near/far NPC models (proposed)](#nearfar-npc-models-proposed)
- [Next experiment: component reuse](#next-experiment-component-reuse)
- [Measured rc10 check](#measured-rc10-check)
- [v0.0.25 validation](#v0025-validation)
- [NPC model levels of detail](#npc-model-levels-of-detail)
  - [Levels](#levels)
  - [Head detail and the levels](#head-detail-and-the-levels)
  - [Which faces get level 0](#which-faces-get-level-0)
  - [Sizes and bake time](#sizes-and-bake-time)
  - [Disk](#disk)
  - [Engine](#engine)

<!-- contents end -->

## What rc10 implements

`npc-gallery: pre-baking in-game character models...` identifies the stage.
Its gallery models are inspection/rest-pose presentations of the game characters;
this stage does not replace the separate gameplay animation conversion.
The next message reports verified cache hits and conversions actually required.
Final `gallery-cache.json` records hits, conversions, dependency/conversion timing,
worker time, capacity estimates and optional rc9 import counts.

The default cache is `WORKSPACE/cache/npc-gallery-v1`, outside individual build
runs. `--gallery-cache PATH` selects a separate private cache. New build outputs
remain independent copies. No cache payload enters public source packages.
Unchanged models are copied from verified entries; misses use the unchanged
converter and existing bounded retry policy. A complete catalogue, footprint
models, inspection map and strict model-budget audit are produced every time.

The key includes the full appearance specification, resolved mesh/texture bytes,
absent preferred DDS candidates, skeleton/animation input, palette, converter
source identity, protected quality settings, Python/platform and relevant package
versions. Changing a head only invalidates appearances depending on that head;
global converter or quality-policy changes may conservatively invalidate more.
A cache hit requires matching identity, model size and SHA-256 and matching
vertex/triangle counts. Invalid or incomplete entries are rebuilt. Model data
and its receipt are atomically replaced; the receipt is the commit marker.
Interrupted writes cannot become accepted partial models. Model pairs completed
before cancellation remain usable in the persistent cache.

No additional runtime work is moved onto the Amiga. Final complete MDL models,
geometry budgets and gallery coverage retain their existing representation.
Dagoth Ur's protected quality profile remains unchanged.

## Completion-driven scheduling in v0.0.25

Independent gallery models use a bounded completion queue with at most twice the
worker budget submitted and unfinished. Freed slots are refilled before results
are reported; a slow early model cannot hold later submissions behind it. Other
conversion stages that require input order continue using their existing helper.

Progress shows disjoint cumulative reused, converted and failed counts; their
sum is the completion count. Converted means successful fresh conversion, not
attempts including failures. Remaining is total minus completed. A failed model
is printed immediately and still blocks the final complete-gallery gate. Results
are restored to original spec order before catalogues, audits and footprints are
written, so worker completion order does not leak into exported content.

`gallery-cache.json` includes `failed`, `completed` and
`scheduler: bounded-completion-v1`, alongside existing hit and conversion counts.
The model converter, cache implementation and cache keys are unchanged from rc10;
existing compatible entries remain reusable without an import or cache migration.
This is a scheduling improvement, not a measured complete cold-build speedup.

## Reuse a stopped rc9 build

Keep the rc9 build running until its output can be retained, or stop it with
Ctrl+C and wait for the shell prompt before applying new source. Never replace
source under a running build. Preserve the entire run directory, including
`build-state.json` and `npc-gallery/`.

Pass `--gallery-seed-run /path/to/stopped-rc9-run` with an rc10 build/recovery.
This imports completed model/receipt pairs only after verifying the old run's
full game input inventory, recorded converter sources, Python/package versions,
palette and per-model protected quality settings and output hashes. It accepts
passed, failed or cancelled rc9 runs; a running run is rejected. Missing or
partial model pairs are converted normally. Incompatible provenance stops with
an explanation instead of silently trusting old files. Omit the seed option for
an ordinary cache lookup/conversion. Loose model files without build provenance
are not migration inputs.

The original failed rc3 run is still the source of retained terrain/music for
`--recover-image-from`; the stopped rc9 run supplies optional character models.
They serve different purposes and neither retained run is modified.

## Capacity and limits

Before model conversion, the gallery checks available storage for its output,
new cache entries, auxiliary map/catalogue files and a margin, combining totals
when output/cache share a filesystem. Hits use verified sizes; misses use a
conservative bound for the existing single-frame gallery format. An rc9 import
also checks its copy footprint. Insufficient capacity stops without omitting
content. This is a gallery-stage storage check, not a guaranteed peak estimate
for a complete HDF build or shared-memory scratch; check those budgets separately.
No automatic cache eviction removes required output or gallery coverage. Retain
completed run outputs; cache lifecycle management can be added independently.

This first optimization helps repeated builds and compatible rc9 recovery.
An empty cache still converts all required appearances. Component-level shared
baking, runtime modular assembly and whole-world terrain caching are separate
work, not claimed implementations in rc10.

## Original heads

Owner decision (9 October 2026): NPC heads keep their original geometry, as
Dagoth Ur's mask does. The previous whole-model bake fitted a humanoid into 480
triangles and decimated the head with everything else, which left faces
unrecognisable (Fargoth; [NPC-HEAD-DECIMATION-33](bugs/NPC-HEAD-DECIMATION-33.md)).

**The rule** (one shared rule for every humanoid, `tools/npc_geometry.py`
`head_plan` and `bake`): every shape of body-part slot 0 (the head) keeps its
exact original triangles, with the same exact-face path as a `minimum_faces`
profile; slot 1 (hair or helmet, attached to the head) too, while it fits. The
body keeps its silhouette: every reduced body shape (torso, skirts, arms, hands,
legs, feet) and a reduced hair or helmet use the shell-preserving reduction
(area and extent kept, `simplify_shape`), and each has a floor: the fewest
triangles that keep its silhouette (`silhouette_floors`), never more than the
budget bake gave it, so the body is never thinner than in the budget model.
Shapes smaller than a tenth of the actor's height are details (floor 4). The
face limit rises only as far as needed: the smallest of 666, 777 and 1,024 that
holds the model. When even 1,024 is tight, triangles come off in this order
(owner, 9 October 2026), each class down to its floors: (1) the hair or helmet,
(2) small details, (3) the torso, (4) the limbs. An overshoot measured in a bake
comes off the same way before any texture work. If the head and every floor do
not fit, the appearance is "LOD only": it gets the budget model, recorded in the
plan (`lod_only`), instead of stick limbs (`bake(..., lod_only='raise')` raises
instead, for a near level that is then not made). The gallery receipt of each
humanoid records the plan that baked it (`head_plan`).

**Skin texels:** a raised-limit model keeps 16-texel face tiles where its 480-row
skin allows and puts the rest on 8-texel tiles, in this order of priority: the
face, then the torso, neck and hands, then the rest of the body, last the hair or
helmet (`mixed_tile_skin`; NPC-NEAR-SKIN-TEXELS-33: halving every tile had left
the body a quarter of the texels of the budget model).

**The switch:** `--npc-head-detail auto|original|budget` (build config
`npc_head_detail`; shipped default `auto`), exported to every converter as
`AMIWIND_NPC_HEAD_DETAIL`. Owner decision (9 October 2026): original heads ship
through the near/far NPC levels only, so `auto` is `budget` while `--npc-lod` is
on (the map model stays the budget bake; the near level bakes the original head)
and `original` when it is off. `original` and `budget` select one bake for every
model; `budget` is the previous bake, byte for byte (checked on Fargoth's world
and gallery models against the code before the rule). The resolved mode is part
of this cache's key (`npc_head_detail` in the identity; `None` for creatures)
and of the stage fingerprint of every builder stage that reaches the bake, so
the two bakes never share a cache entry.

**Allowances:** a model past 2,000 vertices (666 triangles) loads in the engine
only with a byte-matching `model-budgets.txt` line. The gallery already writes
one per model; the image step now adds one for every such model outside the
gallery (world residents, combat and guard models), after the guard torches
(`audit_gallery_budgets.world_allowances`, receipt `world-model-budgets.json`).

**Measured** (owner's base master, 9 October 2026; plan arithmetic over every
appearance with the resident and gallery calls, real bakes for a sample). These
numbers are for the first version of the rule, which kept head and hair whole and
left the body unprotected (Fargoth's legs thinned to sticks); the body figures of
the silhouette rule replace them once measured:

| Over all 3,500 humanoid appearances | Previous (`budget`) | `original` |
| --- | --- | --- |
| Head + hair/helmet source triangles | 288 / 775 / 1,125 (min / median / max) | same |
| Head + hair triangles kept | 30 / 124 / 170 | 288 / 751 / 960 |
| Whole model triangles | 429 / 466 / 475 | 673 / 1,010 / 1,024 |
| Body and clothing triangles | 299 / 343 / 420 | 59 / 261 / 396 (10th percentile 148) |
| Face limit used | 666: 3,500 | 777: 78; 1,024: 3,422 |
| Sum of all models' triangles | 1,626,230 | 3,455,009 |

- Head and hair alone exceed 666 triangles in 2,941 appearances, 777 in 1,722
  and 1,024 in 9. The 161 distinct heads have 12 to 678 triangles (median 502);
  the 163 hair and helmet meshes 6 to 432 (median 66).
- 313 appearances (309 records) cannot hold head, hair and the minimal body in
  1,024 triangles: the head stays exact and the hair or helmet is reduced. Nine
  of them have more than 1,024 head and hair triangles alone: Crazy Batou
  (1,125, Trollbone helm), Davas Aralas, Llarel Llenim, Tidros Indaram and the
  Dreamers (1,059, Dark Elf hair 06), Smokeskin-Killer (1,052, glass helmet),
  Hisin Deep-Raed and Hrargal the Crow (1,047, nordic fur helmet). No head fails.
  Proposed answer for them, and for the thin bodies: the near/far pair below
  (the near model can spend its whole limit on the head end of the actor) or the
  modular parts redesign ([MODULAR_NPCS.md](MODULAR_NPCS.md)), where the head is
  its own original part.
- Real bakes (gallery format) of a sample of 281 appearances weighted to the
  hardest cases (all 313 hair-reduced ones and 150 at random, paused for host
  memory at 281): none failed. Seven (Haki, Missun Akin, Arvs Raram, Zaba,
  Elibael Puntumisun, Patababi, Tis Abalkala) overshot 1,024 even with the
  minimal body, because shell-preserved armour panels cannot shrink; they bake
  with the last fallback (hair or helmet reduced, torso shells given up).
- Fargoth: head 510 and hair 369 triangles kept whole; 1,008 triangles in all
  (previously 448, his head and hair 140 of 879); body and clothing 129 instead
  of 308. Real bake time per model: 2.1 s instead of 6.3 to 8.3 s (exact shapes
  skip the nearest-surface search).
- Model bytes with 8 idle frames (resident format; alias byte formula, matching
  the real bakes): previous median 200,352 B, original median 215,328 B (max
  217,400 B), +15 KB per appearance (about 7 %): the 8-pixel tiles of the larger
  models offset their extra vertices.
- Drawing cost: the alias renderer's work grows with triangles and vertices. A
  humanoid goes from about 466 to about 1,010 triangles (2.2 times; 3,000
  face-local vertices instead of 1,400), on the expanded draw path. A crowd of
  ten residents in view: about 4,700 to about 10,100 model triangles per frame
  (arithmetic from the counts above, not renderer counters).

## Near/far NPC models (proposed)

A level of detail made of the two bakes the switch already produces: up close the
`original` model (whole head), further away the `budget` model (480 triangles,
or lower later for crowds).

- **Builder:** bake both variants from the same recipe (`--npc-head-detail
  original` and `budget`) with identical frame lists (same sampled idle times,
  same order and count), so the engine can swap `ent->model` by distance without
  touching `ent->frame`, its interpolation or QuakeC animation state.
- **Engine (AmiQuake):** the swap belongs where the client relinks entities each
  frame (`CL_RelinkEntities`), or just before drawing in
  `R_DrawEntitiesOnList`: pick the near model when the actor is within a cvar
  distance, with hysteresis (a second, larger distance to switch back) so an
  actor on the threshold does not flicker. Vis is unchanged: both models share
  the entity, its efrags and its bounding box.
- **Memory:** the far model is resident, as today. The near model loads on
  demand for the few closest actors through Quake's `Cache_*` LRU (the alias
  model cache already works this way) and is budgeted inside the CHIM zone and
  heap rules; an evicted near model only costs a reload.
- **Measured bytes** (8 idle frames, all 3,500 appearances): far model median
  200,352 B; near model median 215,328 B, maximum 217,400 B. A near-model cache
  for the nearest N actors holds N near models: N = 2: 430,656 B median, 434,800 B
  worst case; N = 4: 861,312 B / 869,600 B; N = 8: 1,722,624 B / 1,739,200 B. If a
  near model replaced its far model in memory instead of adding to it, the extra
  is only 14,976 B median per actor (N = 8: 119,808 B median, 167,168 B worst).
- **Vis and speed:** fewer far triangles mean faster crowds: the far model costs
  what NPCs cost today, so only the nearest N actors pay for the whole heads,
  and a far model below 480 triangles would make distant crowds cheaper than now.
  Check it with the renderer counters (entities sent, alias triangles drawn) on
  the benchmark cameras before and after.

## Next experiment: component reuse

**Mutable equipment is a requirement.** Looting a corpse or changing equipment
must change the actor's appearance; equipped/base gallery snapshots cannot
represent arbitrary partial removal. Complete-model reuse in rc10 is an interim
host optimization. The [equipment roadmap](CHARACTER_EQUIPMENT_ROADMAP.md)
requires source-derived reusable parts and per-actor equipment state, with
measured load/change-time composition or attached-part rendering. Do not
pre-bake every possible outfit combination.

The supplied base master has 2,675 humanoid records. The current equipped/base
resolver produces 3,500 humanoid appearances using 942 component NIF paths across
68,001 part uses. The additional 260 creature records share 51 model specs.
These are measured catalogue counts, not a promised speedup.

Profile assembly, simplification, per-face texture sampling and encoding before
changing their algorithms. A part's triangle quota depends on its outfit, and
shell preservation depends on actor height: a filename-only component cache is
incorrect. Preserve complete source dependencies, pose/scale, quota, palette and
quality policy. Require byte-identical complete outputs for host-only reuse.
Later load-time composition needs separate loading/RAM/frame-time measurements;
separate per-frame body-part drawing can repeat culling/lighting/skin setup even
at the same polygon count. No runtime assembly change is included here.

## Measured rc10 check

On the retained base-master input and unchanged converter, the full warm-cache
gallery completed in 89.501 seconds with 3,551 hits and zero conversions. The
earlier rc9 cold gallery took 3,622.619 seconds. These are local observations,
not a cross-machine speed guarantee; the warm run used three workers and the
cold run six. First conversion remains expensive. All 3,551 models and all
7,106 non-map payload files were byte-identical. The threaded inspection-map
light compiler changed lightmap packing; all 464 faces, their lighting samples
and other BSP lumps matched. No terrain or target-runtime speedup is claimed.

Keep [recoverable checkpoints](BUILD_RECOVERY_STORAGE.md) outside transient
working storage; the cache does not make an ephemeral workspace persistent.

## v0.0.25 validation

The completion-queue test holds the first model until a later job beyond the
initial submission window runs. This passes without starving that later job.
All 404 source tests pass. A full real-data gallery run reused all 3,551 rc10
cache models with zero conversions or failures; all 7,106 non-map payload files
and catalogue/audit bytes match rc10. All 464 inspection-map faces and their
actual lighting samples match; threaded lightmap packing/padding differs.
These checks establish reuse and output preservation, not a measured speedup
for a complete cold gallery. Both native hand modes compile as asset-free images.

## NPC model levels of detail

Owner decision (9 October 2026): original heads up close and the budget model further
away, as a facial level of detail, generalised to several levels that fit a memory
budget. Implemented in `tools/npc_lod.py` (builder) and `engine/aga/src/aw_npc_lod.c`
(engine). The measurements below are offline (the bakes on the owner's data); the
emulator frame times are still to come.

### Levels

Every resident appearance is baked from the same recipe and the same animation frame
times at up to four levels. Each level has the same frame list (names, order and count),
because the engine swaps one model for another mid-animation by frame index. The builder
checks this for every level (`npc_lod.pair_check`) and refuses a set that differs.

| Level | What | File |
| --- | --- | --- |
| 0 near | the head as authored: the original-head bake of `--npc-head-detail original` when the builder has it, else the head shapes kept whole within 666 faces | `progs/l0/a_<id>.mdl` |
| 1 the map's own model | the budget bake (480-triangle ladder), byte for byte the earlier single model: precached by the map, read by grounding, collision and QuakeC as before | `progs/a_<id>.mdl` |
| 2 mid distance | about 240 triangles; 8-texel body tiles, 16-texel head tiles | `progs/l2/a_<id>.mdl` |
| 3 crowds far away | about 120 triangles; 8-texel tiles | `progs/l3/a_<id>.mdl` |

A level that gives nothing over level 1 is left out for that appearance: level 0 when it
has no more triangles, levels 2 and 3 when they have no fewer (outfits with many parts
cannot go that low). Names stay within the classic FFS rules: 18-character file names, one
folder per level. The level table `progs/npc-lod.txt` (`AWNL2`) lists every appearance:
its map model, the level-0 use flag and the bytes of each level.

Builder options ([LINUX_BUILD.md](LINUX_BUILD.md#npc-model-levels-of-detail)):
`--npc-lod on|off` (off: one model per resident, the earlier method),
`--npc-lod-levels 2|3|4` (2: levels 0-1; 3: levels 0-2; 4: levels 0-3),
`--npc-face-lod all|named|measured|list` and `--npc-lod-disk-mib`. Their defaults are
`config/build-defaults.json`: off, 3 levels, `all`, 96 MiB. The levels stay off by default until
the owner has compared them in game (9 October 2026); turning them on by default is a change of
that file, not of code.

In game, the console's `dbg npclod` switches the levels live
([console commands](AMIWIND_CONSOLE_COMMANDS.md)): `dbg npclod 0`..`3` forces a level on every NPC
and `dbg npclod auto` goes back to the distance bands; `dbg npclod target 0`..`3` forces a level on
the NPC under the crosshair only, for side-by-side looks; `dbg npclod show on` labels each NPC with
its level, triangles, KiB and distance; `dbg npclod bands D0 D1 D2` sets the band edges;
`dbg npclod stats` prints the levels in use, the level-model bytes and the alias triangles of the
last frame. A forced level skips the byte budget and the near cap, not the Cache's free-block
check.

### Head detail and the levels

The NPC heads change (`--npc-head-detail`, NPC-HEAD-DECIMATION-33) and the levels share one
rule set:

- With `--npc-lod on`, level 1 (the map's model) is baked with the budget head detail, so the
  precached model, its grounding and its memory are what they were; level 0 is the
  original-head bake; levels 2 and 3 use the budget detail.
- With `--npc-lod off`, the single model follows `--npc-head-detail` (default original).
- Without the head-detail switch in the builder, level 0 keeps the head shapes whole by its own
  rule (`npc_lod.near_head_faces`); everything else is the same.

### Which faces get level 0

The 480 bake removes 73-95 % of a head's faces (median 83 %: Fargoth 510 to 96). Measured
over all 2,675 NPC records of the base master (equipped appearance, rest pose), the
symmetric surface distance between the original and the reduced head is small: median
0.30 Quake units, 90th percentile 0.53, 99th 1.62, largest 3.01. The large values are almost
all helmets (crests and visors 9-16 units across); a bare face loses detail mostly in its
texture (one 16-texel tile per triangle, so about a fifth of the texels).

| `--npc-face-lod` | Level 0 for | Records selected (of 2,675) |
| --- | --- | ---: |
| `all` (the default in `config/build-defaults.json`) | every appearance | 2,675 |
| `named` | a display name no other NPC record shares | 2,548 |
| `measured` | head surface distance of 0.75 units or more | 175 |
| `list` | the record IDs in `--npc-face-lod-list FILE` | as listed |

Only the selected appearances ship a level-0 file; the asset pool keeps every bake. The
level table flags them; the engine draws level 0 only for flagged appearances
(`aw_npc_lod 1`).

### Sizes and bake time

149 NPC records (every 18th of the master, an island-wide sample), all four levels:

| Level | Baked for | Triangles (median) | Bytes (median / 90th percentile) | Bake time per appearance (median) | Body surface distance to the original (median / 90th) |
| --- | ---: | ---: | ---: | ---: | --- |
| 0 | 123 | 652 | 268,840 / 270,616 | 17 s | the head as authored |
| 1 | 149 | 462 | 199,760 / 260,434 | 14 s | 1.52 / 2.22 |
| 2 | 146 | 252 | 64,158 / 104,172 | 7.7 s | 2.13 / 3.29 |
| 3 | 103 | 146 | 34,208 / 61,610 | 4.7 s | 2.60 / 3.69 |

A model's bytes in the Cache are about its file size. All four levels bake in a median
46 s per appearance against 14 s for the single model; on development builds the asset
pool keeps every level.

### Disk

Disk is the binding limit (every partition under 2 GiB, the whole game on one image).
The level files (all but the map models) may take at most `--npc-lod-disk-mib` (default
96 MiB): levels 3 and 2 go first for every appearance, then level 0 by head surface
distance, largest first. What does not fit is left out and said in the converter output and
its report; those actors keep the map model.

| Resident set | Map models only | 3 levels, `all` | 4 levels, `all` | 3 levels, `measured` |
| --- | ---: | ---: | ---: | ---: |
| The shipped towns (125 resident models) | 25.7 MiB | about 59.8 MiB | about 62.6 MiB | about 34.9 MiB |
| Every NPC record, whole models (estimate) | about 575 MB | about 1.34 GB | about 1.40 GB | about 0.78 GB |

Whole-model levels for every NPC of the island do not fit beside the world in one image;
the disk budget trims them. Shared head parts are the island-wide form (the modular NPC
direction, [MODULAR_NPCS.md](MODULAR_NPCS.md)): the master has 161 head meshes and 162
hair or helmet meshes, about 40 MB as original-detail parts against about 600 MB of
whole-model level 0 (an estimate, not built).

### Engine

The swap is render-only, where Quake's renderer picks an entity's model
(`R_DrawEntitiesOnList`): `currententity->model` is the chosen level for that draw and is
restored after it. Collision, QuakeC, the server's precache list and the entity's frame
are untouched; software Quake has no frame interpolation, so the frame index is the whole
animation state.

Each frame the actors in the visible list are ranked by distance from the view. Each gets
the level of its distance band, then the finest level that fits:

- Bands: `aw_npc_lod_bands` (default `64 256 512`: level 0 within 64 units, level 1 to 256,
  level 2 to 512, level 3 beyond). An edge moves 5 % away from the side an actor is on
  (10 % hysteresis), so a model does not flicker at an edge. At each default edge the
  coarser level's extra surface distance (90th percentile above) is under about one pixel
  of the 320-pixel view.
- Budget: the level models (all but the map's own) share `aw_npc_lod_budget` bytes (default
  1,048,576), nearest actors first, with at most `aw_npc_lod_max` near models (default 4).
  An actor whose level does not fit steps down to a coarser one.
- Memory: level models live in Quake's Cache (`Mod_ForName`, `Mod_TryStreamAlias`, LRU),
  not in the CHIM zone. One is loaded only when the Cache has a free block for it with
  `aw_npc_lod_reserve_kib` (default 512) beside it, so a load never evicts another cache user;
  at most one load a frame, nearest actor first; a refused load is retried after 2 s. A level
  model nobody planned for 2 s is freed (`Mod_ReleaseAlias`). When the Cache evicts one
  anyway, its actors draw a resident level. The fallback is the map's own model, always:
  no refusal is an error.
- `aw_npc_lod 0` draws the map models only, `1` (default) gives level 0 to flagged
  appearances, `2` to every appearance with a level-0 file. `aw_npc_lod_levels` limits the
  levels for an A/B (`1` is the earlier single model; default `0123`).
- `aw_npc_lod_status` prints the table, the resident models and the refusals; `dbg rcount`
  adds `at` (alias triangles drawn) and `ln` (NPCs drawn at level 0 / at level 2 or 3 /
  level models resident) ([renderer counters](performance/RENDERER-COUNTERS.md)).

Tests: `tests/test_npc_lod.py` (frame-list identity, the level table, the policies, the disk
fit, the options, the render-only wiring) and `tests/aga_npc_lod_test.c` (the engine's bands,
budget, near cap, one load a frame and every fallback, under the address and undefined
behaviour sanitizers).
