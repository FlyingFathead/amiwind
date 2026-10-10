# Modular NPCs: every body part stored once, assembled per actor

**Request (owner, 9 October 2026):** humanoid NPCs are built from shared body
parts, the way Morrowind builds them, instead of one complete model per actor.
Two reasons: the builder wastes most of its NPC time converting the same parts
again and again, and looting or changing equipment must change an actor's
appearance, which a model baked whole cannot do. The baked whole-actor models
stay in the builder as a selectable method (comparison and fallback).

<!-- contents start -->
## Contents

- [Summary](#summary)
- [How an actor is built today](#how-an-actor-is-built-today)
- [The part model](#the-part-model)
- [Measurements](#measurements)
  - [Today's cost](#todays-cost)
  - [The parts census](#the-parts-census)
  - [Library quota policies](#library-quota-policies)
  - [Build time and disk (estimate from the measured cost per face)](#build-time-and-disk-estimate-from-the-measured-cost-per-face)
  - [Composition prototype](#composition-prototype)
- [Build side: a parts library and recipes](#build-side-a-parts-library-and-recipes)
- [Stage 1 in the builder: the gallery from parts](#stage-1-in-the-builder-the-gallery-from-parts)
- [Joint seams](#joint-seams)
- [Runtime method A: load-time composition](#runtime-method-a-load-time-composition)
- [Runtime method B: attached parts as follower entities](#runtime-method-b-attached-parts-as-follower-entities)
- [Comparison](#comparison)
- [Visibility and frame cost](#visibility-and-frame-cost)
- [Recommendation and staged plan](#recommendation-and-staged-plan)
- [Risks](#risks)
- [What the engine needs](#what-the-engine-needs)
- [Reproducing the numbers](#reproducing-the-numbers)

<!-- contents end -->

Tracked as [NPC-BAKED-WHOLE-DUPLICATION-33](bugs/NPC-BAKED-WHOLE-DUPLICATION-33.md).
Builds on the [model cache](NPC_MODEL_CACHE.md) ("Next experiment: component
reuse") and the [equipment roadmap](CHARACTER_EQUIPMENT_ROADMAP.md).

## Summary

- The 2,675 humanoid NPC records resolve to 3,500 distinct appearances made of
  68,001 part uses, but only **1,726 distinct parts** (942 mesh files). Each
  part is used about 39 times.
- Baking every appearance whole processes **12.3 million** source triangles and
  writes 1.63 million output faces; the distinct parts hold **0.40 million**
  source triangles. The output faces needed by a parts library are 0.05 to 0.43
  million, depending on how many quota levels each part keeps.
- The current baker already simplifies and textures **each shape on its own**.
  The only coupling between parts is the triangle quota (split over the whole
  outfit) and the actor height used for shell preservation. A part baked alone
  with the quota it gets in an outfit, then concatenated with the others, gives
  exactly the whole model (byte-identical at unit scale, tested).
- Recommended: build a **parts library** (each part converted once, a few quota
  levels) plus a **recipe** per appearance; build the gallery from the library;
  in the engine, **compose one alias model per appearance at load time**
  (method A) and recompose it when equipment changes. Follower entities
  (method B) cost about 19 entity setups per actor per frame and are not
  recommended on the slow-CPU target.

## How an actor is built today

Host side, all in `tools/npc_geometry.py` (PyFFI reads the NIF files):

1. **Resolve** (`src/mwad/npc.py`, `outfit`): from the NPC, RACE, BODY, CLOT,
   ARMO and inventory records, one deterministic appearance: for each of the 27
   Morrowind body-part slots (head, hair, neck, chest, groin, hands, wrists,
   forearms, upper arms, feet, ankles, knees, upper legs, clavicles, tail,
   weapon and shield bones) the BODY record drawn there. The race's skin parts
   come first; worn clothing and armour replace slots by priority (robe 24,
   skirt 8, other clothing 2, armour 3), and a robe or skirt also clears the
   slots it covers. Shields and weapons are not drawn in the idle study.
2. **Assemble** (`assemble`): every part's mesh is posed on the race's skeleton
   (`base_anim.nif`, or `base_animkna.nif` for beast races) at each sampled
   time. Skinned meshes (clothing, armour, most body parts) are skinned on the
   host with the NIF's bone weights; rigid meshes (head, hair, some hands) are
   attached to their bone, mirrored for a Left bone. Positions are scaled by
   the race's weight (x, y) and height (z), and by 0.25 into Quake units.
3. **Bake** (`bake`): the outfit's 480-face budget is split over its shapes in
   proportion to their triangle counts (a head counts 1.7 times); each shape is
   simplified on its own to its quota (`fast_simplification`; large chest
   panels keep their area and extent if the panel spans at least a fifth of the
   actor's height); each output face gets its own 16 x 16 texel tile sampled
   from the original texture. Faces share no vertices (three per face).
   Since NPC-HEAD-DECIMATION-33 the head and hair or helmet (slots 0 and 1)
   are exempt: they keep every original triangle, the split covers only body
   and clothing, and the face limit rises to 777 or 1,024 where needed
   (`--npc-head-detail original`, default; `budget` is the split above for the
   whole outfit). A modular head part is therefore the original head mesh.
4. **Encode** (`animated_mdl`): one Quake alias model (MDL): a 512-wide skin of
   face tiles, three texture coordinates per face and one vertex frame per
   sampled pose. Residents get 8 idle frames ('idle: start' to 'idle: stop'),
   corpses 1 death frame; QuakeC (`aw_npc_idle`) steps the frame every
   `aw_idle_step` seconds. If the outfit overflows the 666-face alias limit at
   480 (shell preservation can grow a quota), the stage retries at 384, 320,
   256 and 192.

The gallery (`tools/prepare_gallery.py`) does steps 1 to 4 for every NPC
record twice (equipped and base body) with one frame and 8 x 8 tiles; residents
(`tools/prepare_area.py`, `build_resident`) do it per placed actor. Quake
mechanism: an alias model with vertex frames is exactly what Quake draws for a
monster; animation is QuakeC changing `self.frame`. Nothing here is new engine
machinery, and modular actors keep it that way (method A).

## The part model

A **part** is one mesh, its shape filter, its attachment bone and its slot, on
one skeleton:

    part key = skeleton | mesh path | shape filter | attach bone | slot

The mesh path alone is not a key: one shirt NIF holds the chest and both arm
shapes (selected by the shape-name filter), and a rigid mesh on a Left bone is
mirrored. Beast parts are posed on their own skeleton. A **recipe** is an
appearance: skeleton, height, weight and the ordered list of parts (each with
its quota level). Equipment state (what is worn now) belongs to the placed
actor, not to the recipe: removing one guard's shirt makes a new recipe for that
guard only.

**Frames are shared by construction.** Every part is posed on the same skeleton
at the same sampled times, so frame *i* of every part belongs to the same pose;
the actor's frame *i* is the concatenation of its parts' frames *i*. Adding an
animation (walk, death, attack) adds frames to every part once, not to every
actor.

**Skins are per part.** Each face owns its tile, so a part's tiles travel with
the part; an assembled skin is the parts' tiles packed one after another.

**Scale.** Race height and weight are a per-axis scale of the posed vertices.
A library part is baked at unit scale and scaled when composed. This changes
the simplifier's input slightly for non-unit races (the prototype measured
bounding-box differences of at most 0.14 Quake units on 32-unit actors); a
library baked per race scale removes the difference at 1.6 times the bakes.

**Quotas.** Today a part's quota depends on the whole outfit (the same pair of
boots gets more faces under a plain shirt than under full armour), and shell
preservation depends on the actor's height. A filename-only cache is therefore
wrong ([model cache](NPC_MODEL_CACHE.md)). The library keeps each part at a
few **quota levels** and the recipe picks, per part, the level nearest to the
quota today's bake would give it in that outfit; shell preservation uses the
skeleton's reference height. The number of levels trades library size against
faithfulness (measured below).

## Measurements

Inputs: the owner's GOG Game of the Year data (Morrowind.esm, Morrowind.bsa),
the v0.0.32 release build made from scratch on 8 October 2026 (24 threads), and
`tools/modular_npc_study.py` (host, Docker, 4 CPUs) on 9 October 2026.

### Today's cost

| Item | Value |
| --- | --- |
| Gallery stage, cold (3,551 models: 3,500 humanoid, 51 creature) | 2,034 s wall, 23,388 CPU s (6.5 CPU hours), 11.5 cores on average |
| Gallery worker time per model | 7.7 s (27,187 worker s in total) |
| Gallery models on disk | 228.7 MB (3,551 models plus 3,551 footprint markers) |
| Gallery output faces | 1.74 million (489 per model); skins 115 MB |
| Resident actor models in the v0.0.32 image | 128 models, 27.6 MB, median 201 KB |
| Share of a resident model | skin 66 %, vertex frames 22 %, texture coordinates and faces 12 % |
| Bake cost per output face (1 core, prototype and gallery) | 16 to 20 ms |

### The parts census

| Item | Value |
| --- | --- |
| Humanoid NPC records | 2,675 (resolver errors: 0) |
| Distinct appearances (equipped and base body, race scale included) | 3,500 |
| Part uses in those appearances | 68,001 |
| Distinct parts (key above) | 1,726, from 942 mesh files and 1,110 textures |
| Uses per part | 39.4 |
| Source triangles processed by whole-appearance baking | 12,343,696 |
| Source triangles in the distinct parts | 402,807 (30.6 times fewer) |
| Whole-appearance output faces (quota estimate) | 1,626,230 (465 per appearance) |
| Posing all 1,726 parts at 8 frames | 383 s of CPU, once |

### Library quota policies

Faces of the library, and faces per assembled appearance, when each part keeps
*n* quota levels (quantiles of the quotas it gets today) and a recipe takes the
nearest level. "Exact" keeps every distinct quota (assembly then equals today's
bake at unit scale).

| Policy | Part bakes | Library faces | Faces per appearance (mean / max) | Over 480 | Over 666 |
| --- | --- | --- | --- | --- | --- |
| Today (whole appearances) | 3,500 | 1,626,230 | 465 / 475 | 0 | 0 |
| Exact, per race scale | 16,591 | 573,491 | 465 / 475 | 0 | 0 |
| Exact, unit scale | 10,146 | 428,920 | 465 / 475 | 0 | 0 |
| 6 levels | 6,077 | 216,339 | 464 / 499 | 74 | 0 |
| 4 levels | 5,048 | 165,850 | 463 / 514 | 243 | 0 |
| 3 levels | 4,297 | 133,876 | 463 / 531 | 529 | 0 |
| 1 level (median) | 1,726 | 53,117 | 476 / 650 | 1,157 | 0 |

No policy exceeds the 666-face alias limit; levels that land above 480 cost
proportionally more to draw for that actor.

### Build time and disk (estimate from the measured cost per face)

At 15.6 ms per output face (the gallery's own measured rate) plus the one-time
posing of every part:

| Gallery built from | CPU time | Wall at 11.5 cores | Library on disk (8 x 8 tiles, 1 frame) |
| --- | --- | --- | --- |
| Whole appearances (today) | 23,388 s measured | 2,034 s measured | 228.7 MB of complete models |
| Exact library, per race scale | about 9,300 s | about 810 s | about 73 MB |
| Exact library, unit scale | about 7,100 s | about 620 s | about 55 MB |
| 4-level library | about 3,000 s | about 260 s | about 21 MB |
| 1-level library | about 1,200 s | about 100 s | about 7 MB |

Composing the 3,500 gallery appearances from the library takes milliseconds
each on the host (prototype: 4 to 15 ms per actor). The 51 creature models keep
today's path. If the game composes gallery models itself (method A), the
gallery's disk use falls from 228.7 MB to the library size.

For residents (8 idle frames, 16 x 16 tiles, 404 bytes per face): every humanoid
record baked whole, as today, would need about 2,675 x 200 KB = 535 MB for the
whole game; a 4-level library needs about 67 MB and an exact library about
173 MB.

### Composition prototype

All 13 NPCs placed in Balmora's exterior cells (the cells named Balmora),
8 idle frames, 16 x 16 tiles, one core. "Outfit" bakes each part with the quota
today's bake gives it in that outfit (including the lower-budget retry);
"3 levels" uses the library policy of the table above.

| | Whole bake (today) | Parts, outfit quotas | Parts, 3 levels |
| --- | --- | --- | --- |
| Faces (13 actors) | 6,394 | 6,382 | 6,526 |
| Actors with exactly today's faces | - | 6 of 13 (byte-identical models) | 0 of 13 |
| Faces per actor versus today | - | -8 to +3 | -29 to +111 |
| Model bytes (13 actors) | 2.82 MB | 2.73 MB | 2.78 MB |
| Largest bounding-box difference | - | 0.14 units | 0.21 units |
| Bake time | 110 s | 103 s (262 part bakes) | 87 s (225 part bakes) |
| Composition (host, per actor) | - | 4 to 12 ms | 4 to 15 ms |

The six byte-identical actors are races with unit height and weight; the
others differ only by the race scale applied after the part bake (see
[the part model](#the-part-model)). Byte differences with equal faces are the
skin height: a composed skin is packed to its faces, the whole bake pads it.
Side-by-side flat previews of all 13 (private evidence) show no visible
difference for the outfit quotas and small silhouette changes for 3 levels.
One actor (Dranas Dradas, heavy armour) reaches 717 faces with 3 levels: over
the 666-face limit, so the recipe planner must cap levels per actor.

Thirteen actors give no reuse yet (199 distinct parts for 253 uses; the bake
time is the same): the saving comes from the whole catalogue, where each part
is used about 39 times.

## Build side: a parts library and recipes

1. **Catalogue** (host, seconds): resolve every appearance (gallery and placed
   actors) to recipes; collect the distinct parts and the quota each gets.
2. **Pose** every distinct part once per skeleton and animation set (8 idle
   frames, 1 death frame, later walk and others): 383 s of CPU for all parts
   at 8 frames, in the shared worker pool.
3. **Bake** each (part, quota level) once: `bake(..., quotas=..., shell_height=...)`
   (added for this study; the default whole-appearance path is unchanged and
   tested byte for byte). Parallel per part, completion-ordered, cached by the
   full input identity (mesh bytes, textures, skeleton, quota, palette,
   converter identity), exactly like the gallery cache.
4. **Store** the library once: per part its tiles, texture coordinates, faces
   and frames, quantised on one grid per skeleton (see method A), in a parts
   PAK written last and whole, sorted by first use. Recipes are a small table
   (part index and level per slot, height, weight).
5. **Gallery** from recipes: composed on the host into today's gallery files
   (stage 1 of the plan), later composed by the game.
6. **Residents** from recipes: the map entity names a recipe instead of a
   model file (stage 2).

The whole-appearance bake stays selectable (a builder option, proposed as
`--npc-models whole|parts`; whole stays the default until the library passes
its checks) and is the reference for every comparison.

## Stage 1 in the builder: the gallery from parts

`build.py --npc-models parts` (and `build_gallery.py --npc-models parts`)
builds the NPC gallery's humanoid models from the parts library; `whole` stays
the default until the library passes its checks, and both methods stay in the
builder. Options: `--parts-cache DIR` (default `WORKSPACE/cache/npc-parts-v1`),
`--npc-parts-policy exact|levelsN` (default `exact`) and
`--npc-parts-face-cap FACES` (default 666; for `levelsN`). Implementation:
`tools/npc_parts.py`.

1. **Census** (shared worker pool, grouped per mesh so each NIF is parsed once
   per worker): every distinct part at every race scale it is used at is posed
   once; the store keeps its posed frame-0 shapes, face counts, extents and
   materials. 3,500 appearances use 5,335 such parts (1,726 parts, several race
   scales each).
2. **Plan and bake** in passes: each appearance gets the quotas and shell flags
   the whole bake would give its shapes (`bake_quotas` and the whole bake's
   shell test on the gallery's translated frame); every distinct (part, scale,
   quotas, shell flags) is baked once, longest first. An appearance whose
   composed faces exceed the alias limit moves to the next cascade step
   (666 faces at 480, 384, 320, 256, 192, then the 1,024-face profile), exactly
   like the whole bake. Parts are baked under the 1,024-face ceiling; the
   planner applies the step's limit to the composed model. The 51 creature
   models keep the whole path and run inside the first bake pass.
3. **Compose** (shared pool): part bakes are concatenated in shape order,
   translated like the gallery, and written as the same model files with the
   same receipt fields (`method: parts`, the policy and the cascade step added).
   `npc-parts-recipes.json` records which bakes make each appearance.
4. **Joint-seam gate**: see [joint seams](#joint-seams).

The store is keyed by the full input identity of each part (mesh, texture and
skeleton bytes, race scale, quotas, shell flags, palette, converter sources and
package versions), never by a file name. A warm rebuild re-bakes only parts
whose inputs changed.

**Equivalence.** Composed parts are byte-identical to the whole bake done
without the gallery's translation (40 of 40 appearances checked). The whole
gallery translates each actor before baking, so floating-point rounding in
the simplifier differs slightly; the gallery comparison measures what that
changes (`tools/npc_parts_compare.py`):

STAGE1_TABLE

**Faster bake for both methods.** Half of the bake's time went into one
pseudo-inverse per output face, vertex and texel sample, always of an original
triangle's edge matrix. They are now computed once per shape; batched results
are bitwise equal to the per-call ones (19,754 matrices checked; 60 of 60
release gallery models reproduced byte for byte), and the bake runs about 1.7
times faster.

## Joint seams

Owner question (9 October 2026): do the bodies close at the joints? They do
not always, in the whole bake and in the parts bake alike: each shape is
reduced alone, and the reducer also collapses rim edges, so a part pulls back
from the part it meets ([NPC-JOINT-GAPS-33](bugs/NPC-JOINT-GAPS-33.md)).

**Audit** (`tools/npc_seam_audit.py`): from the posed, unreduced source parts
of each appearance, every rim edge lying within 0.05 units of another part is a
joint edge (neck/head, wrists, elbows, knees, ankles, chest/groin, clothing and
armour rims over skin). A point 0.5 units in from the rim on the part's own
source surface must stay within 0.25 units (two alias grid steps) of the
reduced model; otherwise the part pulled back and nothing covers the strip.
A view check renders source and reduced models from 16 directions and counts
background pixels inside the source silhouette.

SEAM_TABLE

**Repair options measured** (20 appearances, same budgets): locking every rim
(the boundary-locked quadric reducer used for static meshes) closes the joints
but needs 686 faces per actor on average instead of 491, and half the outfits
then need the 1,024-face profile; locking only joint rims is no better (702);
snapping reduced rim vertices back onto the source rim keeps the faces but
does not close the joints (open share 0.206 to 0.197). The planned repair is
coordinated rim reduction: both parts reduce a shared rim to the same subset of
its source vertices, chosen from the rim's own geometry, and lock that subset.

**Gate.** The parts gallery runs the audit over every appearance and fails when
the island-wide open joint length, the number of appearances with open joints
or the largest gap exceeds `config/npc-seam-limits.json`. The limits are the
measured values of today's reduction; each repair lowers them.

## Runtime method A: load-time composition

When an actor's model is needed (precached by the map, or entering range in a
CHIM zone), the engine builds one ordinary alias model from the recipe and
keeps it in the model cache (Quake's `Cache_Alloc` LRU), keyed by recipe. The
renderer, QuakeC, collision, frames and visibility see exactly what they see
today: one alias model per actor.

- **Quake mechanism:** `Mod_ForName` and the alias stream loader
  (`model_alias_stream.inc`), which already reads an MDL straight into its final
  relocatable cache block. A composed model is a model name such as
  `*npc/<recipe>` whose loader reads the recipe and its parts instead of one
  file, writing into the same cache block layout.
- **Merge cost:** with every part quantised on one grid per skeleton, merging
  is copying: skin tiles, texture coordinates (offset by the tile position),
  triangles (offset by the vertex count) and frame vertices, plus a header
  whose scale and origin carry the race's height and weight. No per-vertex
  arithmetic. A resident model is about 200 KB, so a merge copies about 200 KB
  (a few milliseconds on a 50 MHz 68040, plus the disk reads of about 19
  parts).
- **Memory per resident actor:** one model, about 200 KB (the same as today;
  66 % of it skin). Identical recipes share one model (guards). Temporary
  memory: none beyond the cache block if the loader streams part by part.
- **Equipment change:** the actor's recipe changes (a slot is cleared or
  replaced, exposed skin parts come back), the old model is released and the
  new recipe composed. Looting is rare and happens in a menu, so a few
  milliseconds is acceptable; the corpse keeps its frame (pose).
- **Limits:** a composed model obeys today's alias limits (666 faces, 1,999
  vertices, or the opt-in extended profile); the recipe planner picks quota
  levels that fit.

A later variant (A+) keeps the composed geometry per actor but points its
faces at shared per-part skin pages instead of copying tiles. That saves the
66 % skin share where actors share parts, but needs a renderer change (one skin
pointer per part group instead of per model; the polygon rasteriser rebuilds a
480-row skin table on every skin change, so groups must be drawn together).
Only worth it if memory, not CPU, becomes the limit.

## Runtime method B: attached parts as follower entities

Each part is its own alias model, shared by every actor using it; an actor is
drawn as up to 19 or more part entities that copy the parent's origin, angles
and frame.

- **Quake mechanism:** client-side render proxies, as the guard torches
  already do (`aw_guard_torch.c` adds a body and a held model to the visible
  list next to the original actor). Parts must not be server edicts: 19 per
  actor would exhaust `MAX_EDICTS` (600) at about 30 actors and add 19 links
  per actor to the world's areanodes.
- **Memory:** no per-actor model; only distinct parts. In a whole town reuse is
  low: the 13 actors of Balmora's exterior cells use 199 distinct parts for
  253 part uses, so the memory saving is modest in practice (the global 39x
  reuse comes from the many records across the whole game).
- **Per frame:** every part entity runs the alias setup Quake runs per model:
  bounding-box test, transform setup (angle vectors and a 3 x 4 matrix),
  `R_LightPoint` (a walk down the world BSP), skin setup (a skin-table rebuild
  in the rasteriser), frame setup. That is about 19 times the per-actor setup
  of today, for the same number of faces and vertices. A dedicated draw loop
  could share the transform and light of the parent and still pay the skin and
  frame setup per part.
- **Limits:** `MAX_VISEDICTS` (1,112) holds about 58 actors of 19 parts;
  `MAX_MOD_KNOWN` (256) must hold every distinct part on screen, where today it
  holds one model per actor.
- **Equipment change:** instant (drop or swap a part entity).

## Comparison

| | Today (whole) | A: compose at load | B: follower parts |
| --- | --- | --- | --- |
| Build time (gallery) | 2,034 s | about 260 s (4 levels) | same as A |
| Disk (whole game, residents) | about 535 MB | about 67 MB library | about 67 MB library |
| Memory per resident actor | about 200 KB | about 200 KB (shared by identical recipes) | 0 per actor; distinct parts only |
| Per-frame entity setups per actor | 1 | 1 | about 19 |
| Equipment change | impossible | recompose (milliseconds) | instant |
| Engine change | none | composed-model loader, recipe table | proxy list, part table, draw loop |
| Visibility | one entity | one entity | parts follow a visible parent |

## Visibility and frame cost

Method A keeps one entity per actor: the server links it to the leaves it
touches and the PVS and frustum cull it whole, as today; no new entity is sent.
The vertex and face work equals today's for the same faces, because the faces
are the same faces. Method B adds part proxies only after the parent passed
the PVS and frustum tests (never as separate server edicts), so it does not
change visibility, but it multiplies per-entity setup. The renderer counters
(`dbg rcount`: alias models drawn, entities sent) are checked before and after
on the benchmark cameras for every stage below, together with a CHIM Balmora
frame-time pair on the slow-CPU preset (CHIM-SLOWCPU-FRAMETIME-33).

## Recommendation and staged plan

1. **Parts library and recipes on the host; gallery from parts** (implemented:
   [stage 1](#stage-1-in-the-builder-the-gallery-from-parts)). Builder only,
   no engine change. The gallery composes its files from the library;
   acceptance: every appearance present, face counts within the chosen policy,
   an A/B sheet of all 3,500 appearances against the whole bake, a byte-exact
   check of the exact policy at unit scale, gallery stage time measured cold.
   Expected: gallery 2,034 s to roughly 260 s (4 levels), 6.5 CPU hours to
   under one.
2. **Residents from the same library.** The resident stages write composed
   models from recipes (still one MDL file per actor, so the engine is
   unchanged); actor-contact and the image use them as today.
3. **Composed-model loader in the engine (method A).** Map entities name
   recipes; the loader composes into the model cache; residents and the gallery
   stop shipping complete models (disk falls to the library). Counters and
   slow-CPU frame time must not get worse.
4. **Equipment state.** Per-actor worn items, persisted through streaming and
   save/load; recomposition on change; the acceptance cases of the
   [equipment roadmap](CHARACTER_EQUIPMENT_ROADMAP.md) (boots only, shirt,
   armour over clothing, robe, helmet and hair, corpse looting, two actors
   sharing a recipe).
5. **More animation sets** (walk, death, combat) as frames per part: the
   [animation kit](ANIMATION.md) (one sampler, shared sample times for every part).

## Risks

- **Look changes with quota levels.** Fewer levels mean a part's face count
  differs from today's bake for some outfits. Mitigation: the exact policy for
  stage 1 if build time allows, otherwise 4 or 6 levels, judged on the A/B sheet.
- **Non-unit race scale** gives slightly different simplification than baking
  the scaled actor (measured at most 0.14 units). A per-race-scale library
  removes it at 1.6 times the bakes.
- **Over-budget recipes**: levels that land above 480 faces cost more to draw;
  the planner caps the sum per actor.
- **Intro actors with facial animation** (`npc_faces.py`) and guard torch
  layers keep their current paths until they are converted separately.
- **Equipment rules**: the resolver's slot and priority rules are a bounded
  reading of the records ([equipment roadmap](CHARACTER_EQUIPMENT_ROADMAP.md));
  modular parts make their mistakes visible per slot, not hidden in a bake.
- **Cache pressure in the engine**: a recompose allocates a new model; the old
  one must be released at once, not left to the LRU.

## What the engine needs

For method A (stage 3): a recipe table and parts PAK reader; a composed-model
loader behind `Mod_ForName` for `*npc/` names, writing the existing alias cache
layout; recipe names in map entities (`model` key) for legacy maps and CHIM
frame maps; release of a replaced model on recomposition; save data for worn
items (stage 4). No renderer change. For A+: a per-part skin pointer in the
alias draw path. For B: client-side part proxies, a part model table outside
the map's model precache, and a draw loop sharing the parent's transform and
light.

## Reproducing the numbers

All in Docker, with the owner's own data mounted read-only:

    python3 tools/modular_npc_study.py census --data-files DATA --out OUT --jobs 4
    python3 tools/modular_npc_study.py policies --data-files DATA --out OUT --census OUT/census.json
    python3 tools/modular_npc_study.py compose --data-files DATA --out OUT \
        --palette PALETTE --policy outfit --census OUT/census.json --previews

`census` writes every part with its source faces and the quotas it receives;
`policies` the library sizes per quota policy; `compose` the whole-versus-parts
comparison for up to 20 (`--count`) NPCs placed in the exterior cells whose name
starts with `Balmora`
(flat preview sheets are private evidence and never enter the repository).
Tests: `tests/test_modular_npc.py`.
