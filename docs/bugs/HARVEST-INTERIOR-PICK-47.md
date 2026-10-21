# HARVEST-INTERIOR-PICK-47: mushrooms inside interiors cannot be picked

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 21 October 2026, in v0.0.46 |
| Where | Converted interiors with original small mushrooms (Addamasartus, Vivec plazas) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.46 (last seen) |
| Severity | medium: A whole class of original harvest placements is drawn but cannot be picked; no crash or data loss |
| Family | Harvestable plants (`harvest`) |
| Playtest version | v0.0.46 |
| From commit | source unknown, engine unknown, CHIM world unknown |
| CHIM engine version | CHIM 0.2.1, engine unknown, world format 0.7 |
| Unknown because | the build receipt does not record source commit, engine commit, world commit |
| Platform or emulator | FS-UAE 3.1.66, JIT, A1200 68040 preset, 128 MB |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.47 (21 October 2026)._

<!-- contents start -->
## Contents

- [Status: 21 October 2026](#status-21-october-2026)
- [Symptom](#symptom)
- [Where](#where)
- [How it happened](#how-it-happened)
- [Why it was not caught](#why-it-was-not-caught)
- [Reproduction](#reproduction)
- [Repair](#repair)
- [Verification](#verification)
- [Prevention](#prevention)
- [Bugs in the same category](#bugs-in-the-same-category)

<!-- contents end -->

## Status: 21 October 2026

Open. Present in v0.0.46 (and every earlier build with converted interiors). Fixed in source on the branch
v0.0.47-interior-picks, not shipped at the time of writing: it waits for the next build of the development line.
Part of HARVEST-WORLD-29 (picking and persistent state worldwide), which listed interiors as unverified.

## Symptom

The maintainer, 21 October 2026: "we should do the same as with the pickable mushrooms, so that they disappear once
picked", for the plants inside interiors, and: "we've never done any indoor picking".

In the v0.0.46 release image (headless FS-UAE, 128 MB, fresh play copy), standing on the floor of the Addamasartus
cave 34 units from a Violet Coprinus (original reference 365589) and looking at it: no "E: Pick" prompt, the use key
pressed twice does nothing, `aw_shroomtracker` does not change. Outdoors on the Seyda Neen shore a Luminous Russula
(reference 266995) is picked (`aw_shroomtracker` 0 to 1) and stays picked after the cave visit, after walking back to
it, and after a quicksave and quickload.

## Where

Every converted interior that contains original small mushrooms (Luminous Russula and Violet Coprinus,
`flora_bc_mushroom_01` to `_08`). In the v0.0.46 image these are 345 placements in shipped interiors, 305 of which
the harvest catalogue can represent (the other 40 belong to an owner: taking them would be theft, which the runtime
does not model yet), in 8 maps: Addamasartus, the Hlaalu, St. Delyn, St. Olms and Foreign Quarter plazas, the Hlaalu
and St. Delyn underworks and the Library of Vivec. Island-wide the master places 1,149 such mushrooms in interiors.

Outdoor mushrooms are not affected. Other organic plants (Heather, Comberry, Corkbulb, Trama Root and the rest) are
not pickable indoors or outdoors: HARVEST-ORGANIC-PLANTS-47. Placed ingredient items (an `ingred_russula_01` on a
shelf) are not in the converted rooms at all: INTERIOR-PLACED-ITEMS-47.

## How it happened

Outdoors, the builder's harvest step converts every original small mushroom into a shared model and the image step
writes one catalogue per map (`harvest-<map>.txt`); the engine loads the catalogue of the running map, spawns the
plants from it, hides a picked one and stores the pick in the saved state (`aw_state.harvest`, one fact per placement
slot of a global index). The global index already reserved slots for the interior mushrooms
(`tools/prepare_harvest.py` `placement_index`: exterior and interior identities, one digest), and the engine loads
an interior map's catalogue the same way. But the harvest step read only the exterior placements
(`tools/harvest_build.py` `exterior_references`) and planned catalogues only for exterior maps, so no interior map
got a catalogue. The interior converters keep each mushroom as part of the room's scenery (a brush entity bound to
its reference), which is drawn and has no pick.

## Why it was not caught

Interiors were never part of the harvest work (the one-room prototype `tools/prepare_harvest_room.py` was not wired
into the builder), and no check compared the interior mushrooms of the shipped rooms with the catalogues.

## Reproduction

In the v0.0.46 image: go to Addamasartus and stand by the mushrooms on the cave floor (a camera mark on the map at
local -615.64 93.51 -84.5, view 315 32.8, then `noclip` off), aim at one: no prompt, the use key does nothing,
`aw_shroomtracker` unchanged. In the image payload there is no `harvest-` catalogue for any
interior map (156 catalogues: 64 Seyda Neen, 17 Balmora, 75 region frames).

## Repair

Fixed in source on v0.0.47-interior-picks, with the same mechanism as outdoors (no engine change):

- The harvest step also takes every representable interior mushroom (`interior_references`: the same graph checks as
  a catalogue entry, one placement at a time; an owned or scripted one is left baked and listed with its reason in
  the source receipt).
- The image step finds the shipped interior maps that hold those mushrooms by their exact original reference number
  (`interior_rows`), checks that every plant of a map implies the same map origin, removes the baked plants
  (`tools/remove_harvest_geometry.py`, which now accepts an interior placement key) and writes the map's catalogue,
  with the geometry gate and the heap admission as for every other map.
- The interior catalogues are bound to the same global index (same digest, same slot count) as the world's, so a pick
  indoors and a pick outdoors are facts of one saved table: the save format is unchanged and older saves load as
  before.
- Default on (`--harvest-interiors on`); `--harvest-interiors off` keeps the earlier exterior-only harvest, interior
  mushrooms baked.

## Verification

Builder tests (`tests/test_harvest_build.py` InteriorHarvest): an interior placement joins the source and an owned one
stays baked; the room gets its catalogue with the plant's global slot and loses the baked plant; a recentred room
keeps its origin; plants that imply different origins are refused; with the option off the room is unchanged; the
option reaches the step. Engine test (`tests/aga_interior_harvest_test.c`, real harvest and save code): a room
catalogue and a world catalogue share one pick state through pick, leave, return, save and load, in either order,
and a catalogue bound to another index fails closed without touching the state.

On the real data of the v0.0.46 image (read only, nothing written to the image): 1,056 of 1,149 interior mushrooms are
representable (93 owned), the 8 shipped interior maps bind 305 of them, every map's baked plants are removed exactly,
every map stays within the runtime bounds (at most 68 plants and 8 models a map), and every map passes the heap check
with its catalogue installed and its baked plants removed: six maps gain heap clearance (up to 626,784 bytes, the
St. Delyn and Hlaalu underworks), Addamasartus loses 54,992 bytes and keeps 250,204, the Library of Vivec loses
31,760 and keeps 3,858,860.

The image step's pick audit (`tools/harvest_pick_audit.py`, the engine's pick rule replayed offline) on those 8 maps
with their catalogues: 296 of the 305 plants can be picked from a standing position; for 9 (3 in the St. Delyn
Underworks, 3 in the Hlaalu Plaza, 3 in the St. Olms Plaza) the view line from every position the audit tries meets
room scenery first. They are listed in `config/harvest-pick-known.json` under this bug (the audit fails a build on any
unlisted one); they were not pickable before either. 27 plants have no standing position within reach (reported, not
judged, as outdoors).

Not done yet: a build with the change and an in-game check of picking in a room (no game build on this branch).

## Prevention

The harvest step reports the interior placements it took and the ones it left baked; the image step writes a
catalogue for every shipped interior map that binds an interior mushroom, so a room converter that keeps a mushroom
as scenery is found by the same geometry gate as outdoors. The pick audit (`tools/harvest_pick_audit.py`) runs on the
interior catalogues too.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Harvestable plants (`harvest`). Harvest catalogues are built by the builder for the shipped maps and counted by the entity tracker. See [families](README.md#families).

- [CHIM-HARVEST-SPECIALS-33](CHIM-HARVEST-SPECIALS-33.md): The intro docks on CHIM have no harvestable plants: their catalogue is named after the legacy map, which a pure CHIM image leaves out
- [CHIM-NATIVE-HARVEST-MISSING-36](CHIM-NATIVE-HARVEST-MISSING-36.md): Extra CHIM-native areas get no harvest catalogue: their plants cannot be picked
- [ENGINE-HARVEST-MESSAGE-BOUND-35](ENGINE-HARVEST-MESSAGE-BOUND-35.md): The harvest pickup message joined lines into a fixed buffer without a bound
- [ENTITY-TRACKER-HARVEST-32](ENTITY-TRACKER-HARVEST-32.md): The entity tracker did not count plants placed by harvest catalogues
- [HARVEST-BITTERCOAST-29](HARVEST-BITTERCOAST-29.md): Only one of three nearby Bitter Coast mushrooms reportedly usable
- [HARVEST-CHIM-REGION-LOSS-41](HARVEST-CHIM-REGION-LOSS-41.md): Harvestable plants lost on CHIM region cells: six cells place fewer or different plants than the baseline
- [HARVEST-EXTRA-TOWNS-32](HARVEST-EXTRA-TOWNS-32.md): Opt-in towns get no harvestable mushrooms
- [HARVEST-GEOMETRY-GATE-32](HARVEST-GEOMETRY-GATE-32.md): The harvest geometry gate was never re-run on the shipped Seyda Neen maps
- [HARVEST-ORGANIC-PLANTS-47](HARVEST-ORGANIC-PLANTS-47.md): Only the small mushrooms can be picked; every other harvestable plant is scenery
- [HARVEST-PILOT-SHIPPING-32](HARVEST-PILOT-SHIPPING-32.md): 24 Seyda Neen maps still ship the six-plant pilot harvest catalogue
- [HARVEST-PLANTS-IN-COLLISION-33](HARVEST-PLANTS-IN-COLLISION-33.md): 51 placed harvest plants have their centre inside converted collision (terrain or a tree's convex root piece)
- [HARVEST-SEYDA-STALE-32](HARVEST-SEYDA-STALE-32.md): v0.0.31 ships Seyda Neen harvest catalogues made for older map versions
- [HARVEST-SEYDA-TREE-SPRITE-BLOCKS-PICK-47](HARVEST-SEYDA-TREE-SPRITE-BLOCKS-PICK-47.md): Some mushrooms in the Seyda Neen region cannot be picked: a tree sprite blocks the pick
- HARVEST-WORLD-29 (no report page): Original mushroom placement, picking and persistent state worldwide

Related bugs in other categories:

- [INTERIOR-PLACED-ITEMS-47](INTERIOR-PLACED-ITEMS-47.md): Placed items, ingredients included, are left out of converted interiors

<!-- END GENERATED CATEGORY -->
