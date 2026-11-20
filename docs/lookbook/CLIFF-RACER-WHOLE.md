# Look book page CLIFF-RACER-WHOLE

_Generated from tests/lookbook/pages.json with AmiWind v0.0.67._

The cliff racer is drawn whole: wings joined to the body, no holes.

## What the maintainer confirmed

The cliff racer (and its blighted and diseased kinds, one mesh) is baked whole from its source: every source triangle on shared vertices, no open edge, the whole surface kept.

- 2026-11-18, on v0.0.67-dev2: the maintainer's report of the regression: the racer had been whole since the v0.0.58 fix (CREATURE-RACER-MESH-SPIKE-58)

## How it is checked

The creature surface check of the image's creature library (tools/creature_surface.py, from the cliff racer repair): the cliff racer's model has its source's 965 triangles on 667 shared vertices, no open edge, and 100 % of the whole model's surface within 0.5 units; then a close-up still in first and third person.

- 965 of 965 triangles, 667 vertices, 0 open edges, the whole surface within 0.5 units of its source

Status: drafted, not run yet.

## The code it lives in

- `tools/creature_library.py` (the creature library's bake)
- `tools/creature_tables.py` (the creature tables and their profiles)

## The code it guards

No code is marked yet: the marker goes on the code once the page passes.

## Feature pages

- [ACTOR_RECORDS.md](../ACTOR_RECORDS.md)

## Register entries

<!-- the register history below is rendered from docs/bugs/bugs.json when the page is rendered -->

### [CREATURE-RACER-MESH-SPIKE-58](../bugs/CREATURE-RACER-MESH-SPIKE-58.md)

The cliff racer's model is drawn broken: the wings do not join the body, the parts sit apart, and a long spike runs far below. State: open; found in v0.0.57-dev4.

- 2026-11-18 Cause of the regression found by number: from v0.0.66-dev3 the creature library bakes every creature with the skeletal method (its own animation table), whose model is the resident bake; the gallery profile that keeps the cliff racer whole was not read there. The racer was baked to 474 of its 965 triangles, every triangle on three vertices of its own with its own baked texture tile (474 tiles against the 21 texture islands of the whole model), 62 open edges, two pieces; 66 per cent of the whole model's surface within half a unit of it. And its root bone is named root bone, not Bip01, so its ow
- 2026-11-18 Guarded by the look book page CLIFF-RACER-WHOLE (docs/lookbook/CLIFF-RACER-WHOLE.md): The cliff racer is drawn whole: wings joined to the body, no holes; a change to the code it lives in must pass that page before it is merged (docs/LOOKBOOK.md).
- 2026-11-18 fixed in source: a commit on the dev line, v0.0.67-dev3 line (cfcc4d9a) (tests/test_creature_whole.py and the whole route baked on the game data, measured against the v0.0.65 whole model)
- 2026-11-18 regressed on v0.0.67-dev2 (was fixed in v0.0.58): A regression on the v0.0.67-dev2 image (the maintainer's picture, 2026-11-18): a cliff racer in the Ashlands (`cliff racer`, reference 393760, model progs/c_64031b3f740e_k.mdl) is drawn as flat wing plates apart from a thin body, full of holes, as before the v0.0.58 fix. Whether the blighted cliff racer is whole too is to be checked; if it is, its model is the reference for the plain one.
- 2026-11-19 shipped: a development build, v0.0.67-dev3 (a375b13f) (the fix commit cfcc4d9a is an ancestor of the delivered dev3 head a375b13f (git merge-base --is-ancestor) and not of the dev2 head 0d6f7ab7)
