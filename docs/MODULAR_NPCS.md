# Modular NPCs: every body part stored once, assembled per actor

_Last updated with AmiWind v0.0.57-dev1 (30 October 2026)._

<!-- contents start -->
## Contents

- [Where it stands, 24 October 2026](#where-it-stands-24-october-2026)
  - [What OpenMW shares, and what AmiWind takes from it](#what-openmw-shares-and-what-amiwind-takes-from-it)
- [Disk size plan for the actors (v0.0.49)](#disk-size-plan-for-the-actors-v0049)
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
- [Runtime method C: one shared animation table, posed in the alias renderer](#runtime-method-c-one-shared-animation-table-posed-in-the-alias-renderer)
  - [Paged animation frames (v0.0.57)](#paged-animation-frames-v0057)
- [Getting NPC movement right](#getting-npc-movement-right)
- [Runtime method A: load-time composition](#runtime-method-a-load-time-composition)
- [Runtime method B: attached parts as follower entities](#runtime-method-b-attached-parts-as-follower-entities)
- [Comparison](#comparison)
- [Visibility and frame cost](#visibility-and-frame-cost)
- [Recommendation and staged plan](#recommendation-and-staged-plan)
- [Risks](#risks)
- [What the engine needs](#what-the-engine-needs)
- [Reproducing the numbers](#reproducing-the-numbers)

<!-- contents end -->

**Request (maintainer, 9 October 2026):** humanoid NPCs are built from shared body
parts, the way Morrowind builds them, instead of one complete model per actor.
Two reasons: the builder wastes most of its NPC time converting the same parts
again and again, and looting or changing equipment must change an actor's
appearance, which a model baked whole cannot do. The baked whole-actor models
stay in the builder as an option you compile in on purpose
(`--npc-anim-type 1`); skeletons are the default (`--npc-anim-type 2`) from
v0.0.52, since they take a fraction of the space, and release kits carry no
baked actor frames (a kit check refuses one that does).

Tracked as [NPC-BAKED-WHOLE-DUPLICATION-33](bugs/NPC-BAKED-WHOLE-DUPLICATION-33.md).
Builds on the [model cache](NPC_MODEL_CACHE.md) ("Next experiment: component
reuse") and the [equipment roadmap](CHARACTER_EQUIPMENT_ROADMAP.md).

## Where it stands, 24 October 2026

Only the builder half of this plan was built. The parts library (`tools/npc_parts.py`, `--npc-models parts`) converts
each part once and composes the gallery from recipes, but it is not the default, and it still writes one complete
model per actor: it saves build time, not disk. Stage 2 (residents from the library) and stage 3 (the engine composes
actors from the shared parts at load time) were never built, and v0.0.48 placed the residents of every base-game
interior with whole-baked models. The result, measured on the v0.0.48 release candidate image:

| | Size |
| --- | --- |
| The original game's Data Files (Morrowind, Tribunal, Bloodmoon, with music, video and sound) | 1,840 MB |
| `Morrowind.bsa`, the base game's meshes and textures | 297 MB |
| AmiWind's actor models in the image (4,225 complete models, 1,769 resident records) | 1,468 MB |
| of which animation frames (64 per model, about 1,500 vertices each) | 992 MB |
| of which skin textures, one 512 x 256 or 512 x 336 skin inside every model | 587 MB |

Two design faults multiply it, besides the missing composition:

- **Two models per character.** The animation kit gives each resident a standing model (idle, hit, death) and a
  separate "mover" model (walk, run, swim, knockdown, attack) worn while it moves. Every character can move, so every
  body is stored twice, each copy with its own skin.
- **The skin travels with every model.** The same textures are stored again inside each model that uses them,
  standing and mover alike.

Every character keeps all of its animation; the size must come from storing things once:

1. **One model per character, not two**: all animation groups in one set of frames, one skin.
2. **Stage 2 and 3 of this plan**: residents from the parts library, and the engine composing them at load time, so
   the image ships the 1,726 distinct parts instead of 1,769 complete characters. The maintainer chose this first
   (24 October 2026): each part keeps its own vertex frames on one shared animation clock, and its textures are
   shared files, not part of a per-character skin.
3. **Skins stored once**, shared by every model that uses the same texture.
4. **A size budget for the actors** in the build's size ledger, so the payload cannot grow unnoticed again.

Hashing the release candidate's actor models shows where sharing can and cannot help today: only 8 of the 4,225
models are identical, and no skin is shared by more than two models (a character's standing and mover copies; sharing
those saves about 178 MB). Each character's skin is its own atlas of all its body-part textures, so two characters in
the same robe still carry two different skins. Texture sharing becomes possible only at the part level, which is why
stage 2 and 3 come first.

### What OpenMW shares, and what AmiWind takes from it

Read from the OpenMW 0.51.0 source:

- **Morrowind's own data**: an NPC record names its race, sex, head, hair and inventory, never a mesh of its own.
  Body-part records point at shared meshes, textures are referenced by name, and one animation file per skeleton family
  (`xbase_anim.kf` and its kin) serves every humanoid.
- **One copy of every resource**: the scene, image and keyframe managers load each file once. An actor instance copies
  only its node tree and controllers; geometry, textures and animation keys are shared. Textures are never stored
  inside meshes.
- **Assembly**: `NpcAnimation` puts each equipped body part on the actor's own skeleton: skinned parts follow the
  skeleton, rigid parts hang on a named bone (the same idea as the engine's tag frames, which carry the guard torches).
- **No separate mover**: animation sources stack on one skeleton, and blend masks let walking and attacking play at
  once.
- **Skinning on the CPU**: vertices with the same bone weights are grouped, one blended matrix per group, then about
  nine multiplies and nine adds per vertex; actors off screen or far away are skipped.

For the Amiga, the per-frame skinning is the part to avoid in a crowded street. The step after the parts library is to
skin once when a character is first loaded, not every frame: ship the shared bone animation and each part once, and
expand them into vertex frames in RAM (estimated at 0.2 to 0.5 seconds per appearance on a 25 MHz 68040, to be
measured), with no per-frame cost after that. That could bring the actor payload down to tens of megabytes.

The [roadmap](ROADMAP.md#the-actors-get-the-chim-rule-store-once-place-many-times) puts this first in the next
version; the register entry is
[ROOM-RESIDENT-MODELS-SIZE-48](bugs/ROOM-RESIDENT-MODELS-SIZE-48.md).

## Disk size plan for the actors (v0.0.49)

The goal: the actors take a size that belongs on an Amiga, with every character keeping all of its animation. The
starting point is the v0.0.48 release candidate: **1,468 MB** of actor models in 4,225 complete models. Measured again
on the v0.0.51 release image (25 October 2026, from its readback record): 1,478 MB in the same 4,225 models (2,174
characters and creatures: 2,077 movers at about 501 KB, 2,148 standing models at about 215 KB), 39% of the 3.70 GB
image; the store-once layout leaves only 0.01 GB stored twice in the whole image. Each stage is
built, measured on the same rooms against the stage before it, and kept by a test. A stage that does not pay is
reverted, not shipped.

| Stage | What changes | Saving (estimate until measured) |
| --- | --- | --- |
| 0. Budget | The build's size ledger records the actor payload (frames, skins, files) and fails a build whose actors grew by more than a set margin over the previous release without a stated reason. **Done in source on v0.0.52-dev** (25 October 2026): `tools/size_ledger.py` counts `id1/progs/a_*` and `id1/progs/skins` as the actors group (1.55 GiB of the v0.0.51 image, the release baseline); the size guard's 0.05 GiB margin applies to it | none: it stops silent growth |
| 1. One model per character | The standing and the mover model become one model holding all animation groups and one skin | about 178 MB of duplicate skins (measured) and half the files |
| 2. Residents from the parts library | Every resident is a recipe over the parts library (stage 2 of the [staged plan](#recommendation-and-staged-plan)); the builder still writes composed models, so the engine is unchanged | build time; no disk yet |
| 3. The engine composes at load time | The image ships the parts, each with its own frames on one shared animation clock and its textures as shared files, plus one recipe per character; the engine composes a character into the model cache when it is first needed ([runtime method A](#runtime-method-a-load-time-composition)) | frames from about 990 MB to under 100 MB; textures stored once per part instead of once per character |
| 4. Skin once at load time | The image ships the shared bone animation and each part once; the engine expands a character's frames in RAM when it first loads, the way OpenMW skins on the CPU, but once instead of every frame | the actors toward tens of MB |

How each stage is measured:

- **Disk**: the actor bytes in the size ledger (frames, skins, files), and the image and partition count.
- **Looks**: an A/B sheet of every appearance against the previous stage, same poses and frames.
- **Load time**: entering a room full of residents (a Vivec canton, a Balmora tradehouse) in FS-UAE, 16 MB and 32 MB
  of Fast RAM.
- **Frame time**: a crowded Balmora street and the busiest rooms, slow CPU settings included; stage 3 may draw a few
  more polygons per character, stage 4 adds load time, neither may cost frame time.
- **RAM**: composed and expanded characters live in the model cache, so the cache budget at 16 MB and 32 MB is part
  of each stage's result.

Order and decision: stage 0 and 1 first (small, safe), then stages 2 and 3 as the main work (the maintainer's choice,
24 October 2026), then stage 4 once stage 3 is measured. The joint seams of the parts
([NPC-JOINT-GAPS-33](bugs/NPC-JOINT-GAPS-33.md)) are fixed in the parts library before stage 3 ships.

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

Inputs: the maintainer's GOG Game of the Year data (Morrowind.esm, Morrowind.bsa),
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

Maintainer question (9 October 2026): do the bodies close at the joints? They do
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

## Runtime method C: one shared animation table, posed in the alias renderer

**Decision (the maintainer, 25 October 2026):** every NPC uses a shared animation table, the way Morrowind and OpenMW
do ("every single NPC should use a shared animation table"), built on the engine's own alias renderer and cheap to
compute. It replaces the baked frames of methods A and B, whose parts still carried their own vertex frames.

Why it is cheap: the alias renderer already transforms every vertex of a model by one 3 x 4 matrix every frame
(`r_alias.c`, `R_AliasSetUpTransform` and `R_AliasTransformVerts`). With a skeleton, each vertex names the bone it
hangs on, and the renderer uses that bone's matrix (bone pose times the model's view matrix) instead of the one model
matrix. The work per vertex stays what it is today; the new work is one matrix per bone per drawn actor (34 bones,
a few dozen small multiplies) and, at joints, a blend of two bone positions for the few vertices that need it.

Measured on the base game's data (25 October 2026):

| | |
| --- | --- |
| Body-part meshes (`meshes/b`) | 519, of them 479 rigid (the whole part hangs on one bone) and 40 skinned |
| Skinned vertices | 25,216: 90.3 % on one bone, 7.7 % on two, 2.0 % on three or more (weights of at least 0.05) |
| The humanoid animation (`xbase_anim.kf`) | 34 bones, 891 animation groups, about 139,000 keys over 356 seconds |
| Stored once at 16 bits per value | about 1.3 MB for every humanoid in the game |
| Baked frames today (v0.0.51) | 992 MB of the 1.5 GB of actor models |

What ships and what the engine does:

- **On disk:** each body part once, in its rest pose, with one bone index per vertex (two and a weight for joint
  vertices); one animation table per skeleton family (the humanoid table and the creatures' own); each actor's recipe
  (its parts and their skins). The baked frames go.
- **In RAM:** the animation table of the skeletons in use, each drawn actor's composed parts, and per drawn actor the
  bone matrices of its current pose. No frames per character, so a crowd costs far less memory than today's 200 to
  500 KB per character.
- **Per frame, per drawn actor:** sample the table at the actor's animation time (the group the game logic asks for:
  idle, walk, run, attack, hit, death), build the bone matrices, transform each vertex by its bone. Actors off screen
  or past the draw distance are skipped, as today.
- **Unchanged:** the rasteriser, the skins, the entity, visibility and collision paths, and the frame numbers the game
  logic uses (they name a group and a time instead of a baked frame).

Every NPC then has every action: the region NPCs that today have only a standing model (ANIMKIT-COVERAGE-35) walk,
run and fight like the town NPCs. First step: a prototype on one town, measuring the frame time with and without the
bone transform on the slow-CPU preset and the RAM of the town's actors, against today's baked models.

### Paged animation frames (v0.0.57)

A table is read in two parts (WALK-CYCLES-57, `aw_skel_load.c`). Its index (header, bones, group names and frame
ranges, text keys, the bones' base keys) is loaded with the table and kept; its frames stay in the file, which stays
open with the table, and are read 16 at a time the first time a pose needs one of them, then kept with the table. A
town whose people stand, play their idles, turn, walk and run holds those groups' frames, not the deaths, attacks,
spellcasts and swims nobody plays there. Measured on the tables of v0.0.57-dev1:

| Table | File | Index | Frame rows | Idles, turns, walk, run |
| --- | --- | --- | --- | --- |
| Common humanoid (29 bones, 2,932 frames) | 602,008 bytes | 39,064 | 562,944 (192 a frame) | 117,696 |
| Beast humanoid (33 bones, 2,570 frames) | 654,324 bytes | 37,524 | 616,800 (240 a frame) | 107,760 |

A walk cycle is 11 table frames at 8 a second (2,112 bytes of the common table); a chunk read is about 3 KB, made the
first time an actor poses a frame of it (the pose cache in `r_alias.c` keeps the posed vertices as before). Frame 0's
row is read with the index and stands in for a chunk that cannot be read. The tables are given back with the posed
frames before a room sizes its block (`aw_skel_release.c`), as before. `dbg animkit tables` prints the bytes held
against the bytes on disk; `dbg animkit tables whole` is the previous method (the whole file in one block) for the
next table loaded, `dbg animkit tables paged` the default.

## Getting NPC movement right

The rules the skeletons follow (decided with the maintainer, 25 October 2026: whatever a humanoid can do must be in
the look-up table, and it is not pre-baked):

**Every action, from one table.** The table holds every animation group of the humanoid skeleton (139 of 139 in the
base game: idles, walking, running, sneaking, swimming and turning in every direction and weapon stance, jumping,
every attack set with its phases, spellcasting, blocking, hits, knockdowns, knockouts, deaths, the torch, lockpicking,
the storm idle, the inventory poses). A build check refuses a table that misses a group of its sources. Walking,
running, sneaking, swimming and jumping are held in place: the game moves the actor, the animation only moves its body.

**Chosen as the original chooses them.** The game logic picks the group and its speed the way OpenMW's character
controller does (`mwmechanics/character.cpp`): the movement direction and speed pick walk, run, sneak or swim and the
playback rate, so the feet do not slide; combat picks the attack set of the weapon in hand and its phases; hits,
knockdowns and deaths interrupt; the torch and the inventory poses play over the rest. The animation kit's game logic
(docs/ANIMKIT.md: frame ranges per group, `dbg animkit play`) stays; only where the motion comes from changes.
That includes AmiWind's own combat presentation ([COMBAT](COMBAT.md)), kept as it is: a swing whose roll missed
shows why, the target raising its shield (the base game's shield group) or dodging (a quick step aside: the
walk-left or walk-right loop in place, named `dodgel` and `dodger` in the table over those same frames, while the
combat code moves the actor 10 units through the collision), one roll per swing, for the player and the NPCs alike.

**As cheap as a baked frame.** Quake's monsters cost little because the renderer transforms each vertex of a stored
frame once. A skeletal actor must cost the same:

- each vertex is transformed once, by its bone's matrix (the view, model and bone matrices combined once per bone),
  and the light direction is turned into each bone's space once, so the per-vertex work is today's;
- an actor is posed only when its frame changes (about 10 times a second), never every drawn frame;
- actors on the same table frame share the pose; far actors pose less often and skip the joint blend;
- no division and no float-to-integer conversion per vertex (the 68040 has no instruction for the truncation).

The first working version poses every vertex twice a drawn frame and does both; it is the version to replace
([SKEL-RUNTIME-COST-52](BUGS.md)).

How it fits the alias renderer (`r_alias.c`, as in AmiQuake): today it picks a stored frame, builds one combined
matrix (view x model) and runs every vertex through it, then projects and draws. The skeletal path keeps that shape:

- the actor stays one entity: one bounding box test (a box that holds every pose), one world light sample, one
  dynamic light pass, the existing triangle drawing and clipping;
- per bone one combined matrix (view x model x bone) and the light direction turned into the bone's space, once per
  drawn frame; the builder sorts each model's vertices by bone, so the inner loop keeps one matrix for a run of
  vertices and does the same work per vertex as a baked frame (no blend for a rigid part);
- the pose (the table's quaternions turned into the 29 bone matrices, parent first) only when the actor's table
  frame changes, about 8 times a second: a few thousand floating-point operations per actor a second. Matrices
  ready-made per table frame would save that, but cost 1.9 to 3.8 MB for the common table alone; measured
  against the vertex loop it is not worth it. Blending between table frames can be switched off (the nearest frame
  only) where the CPU is short;
- the vertices are still transformed, projected and drawn every displayed frame: a lower animation rate does not
  remove that, which is why the vertex loop must stay today's.

A part that looks wrong rigid and too costly blended (a skirt, a robe hem) may keep a small shared baked deformation
of its own: trading memory for CPU on one piece is fine when measured; baking every actor whole is not.

**Parts carry no motion.** The modular bodies ride the one skeleton; a body part stores no movement of its own.
479 of the 519 body parts are rigid, each on one bone (a forearm, a helmet, a boot): the renderer draws each with
that bone's matrix, Quake-style, so a rigid part costs no more than a static model. Only about 40 skin parts bend at
the joints, and only their vertices take the bone blend. Movement sets kept per part would be baking again, per part
instead of per character: smaller than 992 MB, but the same mistake. A baked actor cannot change clothes either:
every outfit would need its own bake. With parts on bones, a part is swapped and the skeleton keeps moving.

**Fewer frames are fine.** The bar is that every NPC moves with a real cycle (walk, run, idle, fight), not that it
looks perfect: 8 to 10 table frames a second with fewer keys is part of the squeeze when it saves RAM, disk or CPU.
Like an animator's keyframes, a stretch where little moves (an idle, a held pose) can keep 4 frames a second or
fewer while a swing keeps 8: a frame is stored only where the motion needs it, and the engine poses an actor only
when its stored frame changes.

**A stick figure.** The table keeps 29 of the skeleton's 61 nodes: the root, pelvis, chest, neck and head; per side
the clavicle, upper arm, forearm and hand, the thigh, calf and foot; the weapon and shield bones; and per hand a thumb
and one unit for the fingers, each with both its joints, so a hand still closes around a weapon. The two lower spine
links, the attachment nodes and the second finger are left out: their motion is kept in the kept bones' transforms
(the kept bones move within 0.6 units of the full skeleton's), and a part on a left-out node rides its nearest kept
bone at the same place. The beast races (Argonians and Khajiit, `base_animkna.nif`: their own walk on the toes, a
tail) keep their toes and two of the four tail bones (33 bones); the female groups (`base_anim_female.nif`, three
groups over the common ones) are a table of their own, chosen per actor as OpenMW chooses them. The fidelity bar is
every animation working, not OpenMW's or the original's smoothness.

**Small enough to ship.** The base game's table was 4.3 MB as first built (version 1: 61 nodes, every one with a
four-part rotation and a position, 15 frames a second). Version 2 stores a bone that never changes once, a bone that
only turns (or moves under one unit) without its position, three-part rotations (w >= 0, rebuilt from x, y and z) and
8 frames a second, blended between. The table also carries the text keys as frames (a group's phases such as
`self release` or `chop min hit`, and the sound events), which the game logic, and MWScript's PlayGroup later, play
between (`AW_SkelKeyFrame`). Measured: the common table 549 KB (139 groups, 835 keys), the female 14 KB, the beast
639 KB (138 groups, 813 keys). Keys only where the motion changes (within an error too small to see) come next
([SKEL-TABLE-SIZE-52](BUGS.md)). The
characters themselves come from the parts library (each body part once, about 67 MB for every resident) assembled at
load, not one baked model each: together the actors go from 1.5 GB to well under 100 MB, held by a budget in the size
ledger.

**Skeletons by default.** The builder makes skeletal actors (`--npc-anim-type 2`, the default); baked actor frames
are made only by a build compiled with `--npc-anim-type 1` on purpose, and the project's release kits carry none.
A debug console switch (planned with the engine posing) turns the skeletal posing on and off in the game (off draws
the rest pose), never to baked data.

What type 2 builds (v0.0.52): every humanoid resident (towns, Seyda Neen, the rooms) and every actor-library
model is one rest frame and its skeletal block on the table of its skeleton, made by the resident bake's own
reduction and atlas (`tools/skeletal_actor.py` `skeletal_resident`, called by `tools/prepare_area.py` and
`tools/npc_library.py`). Two tables are written once into the image: `progs/humanoid.awsk`, which also holds
the female groups under an `f:` prefix (`f:walkforward` and her two idles: OpenMW's `NpcAnimation` adds
`xbase_anim_female` after `xbase_anim` for a female human, and the later source wins for each group it has), and
`progs/humanoid_kna.awsk` (the beast races alone, as the baked kit has always made them). A female human's model
names the view `progs/humanoid.awsk|f`: the engine loads the common file once for both, and the view's group
lookup tries `f:` and the name first; her layout points at her own frames directly. A table of her own repeated
the common one whole, 561 KB of Fast RAM for three groups. An NPC whose record names an animation file of its
own (the Suran dancers' `anim_dancingGirl.nif`) gets that file's groups the same way, under `d:`, and the view
`progs/humanoid.awsk|d|f` ([ANIMKIT](ANIMKIT.md#an-npcs-own-animation-file)). The animation kit's
layout beside each model names the table's frames ([ANIMKIT](ANIMKIT.md#skeletal-actors-the-layout-from-the-table)),
with every group of the profile and no mover. The carried weapon and shield hang on the table's weapon and
shield bones (the `AWTS1` item tag). The type is part of the resident stages' keys (`AMIWIND_NPC_ANIM_TYPE`) and
of the actor library's appearance keys, so the two types never share a cached model. For now the head is
reduced to the budget detail, so every actor fits the 2,000 vertices of the alias stream reader
([SKEL-VERTEX-LIMIT-52](BUGS.md)); an actor that starts dead keeps its one death pose as a one-frame model. A
guard who carries the original torch has it on the shield bone beside its own shield (the `light` and `emitter`
lines of its tag: the torch model and the flame's point), shown by the day and night cycle: no baked torch
companions for a skeletal guard.

Size ledger (26 October 2026, measured on the base game's data: every NPC record placed in a cell of
`Morrowind.esm`, 2,612 records, baked as the resident stage bakes them with the `react+full` profile; the files
each writes into the image, before the resident stage shares identical files and without the greeting voices,
which are the same in both):

| | Type 1 (baked) | Type 2 (skeletal) |
| --- | --- | --- |
| Actors baked | 2,515 (97 over the alias budget) | 2,612 |
| Actor files of the 2,515 both bake | 3,222 MB (models 1,256 MB, movers 1,957 MB, layouts and tags 9 MB) | 512 MB (models 511 MB, layouts and tags 1.5 MB) |
| Mover models | 2,515 | none |
| Shared animation tables | | 1.8 MB (`humanoid` 563 KB for 1,424 actors, `humanoid_f` 561 KB for 954, `humanoid_kna` 654 KB for 234); since then the female groups live in `humanoid` (about 1.2 MB in all) |
| Per actor | about 1,281 KB | about 204 KB |

Type 2 stores the same characters in about a sixth of the bytes (514 MB with the tables against 3,222 MB), with
every group of the profile on every actor. What is left in a skeletal actor is mostly its own skin and mesh,
stored once per character: the parts library (each body part once, assembled at load) is the next step down.

**Open to the scripts.** The table keeps Morrowind's own group names, and an actor's animation goes through one
entry point that the game's NPC logic calls now and MWScript will call later, as OpenMW does
(`mwscript/animationextensions.cpp`): play a group, loop it a number of times, skip a frame, return to idle. The
first version may be rough; the interface is what later work plugs into. The same holds for everything else a
script touches on an actor: its base level, attributes, skills, health, magicka and fatigue, abilities and spells,
equipped weapon and armour, and inventory live in one record per actor, read from its NPC record at load and changed
by play; MWScript's actor functions (GetLevel, ModHealth, Get/Set/Mod of a skill or attribute, AddItem, Equip,
AddSpell, PlayGroup ...) read and write that record only, and an equipment change re-picks the actor's body parts on
the skeleton. The record comes first; the scripts can come later.

**Seen before the game.** `tools/skeleton_preview.py` draws the shipped tables from your own copy of the game: the
common and beast skeletons as bones, group after group (`--data-files DIR --out DIR`), or one character dressed as
the game dresses it, posed exactly as the engine poses it (`--npc "balyn omavel" --palette gfx/palette.lmp`). The
project ships no game data; the pictures it makes from yours stay with you.

**Proved in the game.** A MiniWind animation stage plays every group on Seyda Neen and Balmora characters, with the
frame time and memory read on the slow-CPU preset next to today's baked actors
([SKEL-ANIM-STAGE-52](BUGS.md)).

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

All in Docker, with the maintainer's own data mounted read-only:

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
