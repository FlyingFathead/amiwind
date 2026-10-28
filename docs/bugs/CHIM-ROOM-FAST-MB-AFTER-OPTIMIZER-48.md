# CHIM-ROOM-FAST-MB-AFTER-OPTIMIZER-48: marking rooms "needs 32 MB" rewrote 16 room maps after the optimizer receipt, and the image step stopped

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | build |
| First noticed | 23 October 2026, in v0.0.48-dev2 |
| Where | image step room heap check (_chim_room_fast_mb) after optimize_world_maps |
| Reproduction | always |
| Duplicate of | no |
| Persists in | fixed in v0.0.48 |
| Severity | critical: stopped the dev2 image step |
| Family | Content silently missing from a build (`build-content-missing`) |
| CHIM | Builder ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | 2026_10_23_v0.0.48-dev2_dev2-try13_0fa0a130 |
| From commit | source 0fa0a13, engine 0fa0a13, CHIM world 0fa0a13 |
| CHIM engine version | CHIM 0.2.1, engine 0fa0a13, world format 0.12 |

<!-- END GENERATED FACTS -->

<!-- contents start -->
## Contents

- [Status: 23 October 2026](#status-23-october-2026)
- [Symptom](#symptom)
- [Cause](#cause)
- [The 16 rooms (dev2 try 13, image/chim-room-heap.json)](#the-16-rooms-dev2-try-13-imagechim-room-heapjson)
- [Fix](#fix)
- [Bugs in the same category](#bugs-in-the-same-category)

<!-- contents end -->

## Status: 23 October 2026

Fixed in v0.0.48 (2026-10-23 21:45 +0300 / 2026-10-23 18:45 UTC): the receipt follows exactly the maps the room heap
gate marks, the receipt is checked right before the marking, and a test keeps every map writer after the optimizer
behind a receipt rebind. dev2 try 14 reruns the image step only.

## Symptom

The dev2 try 13 build stopped in the image step: "Image: optimizer check: FAILED (ValueError)", "Final staged maps no
longer match optimizer receipt". Exactly 16 batch room maps (ri*.chim) differ from the receipt; the same run logged
"[chim] rooms that need 32 MB of Fast RAM (refused at their door on less): 16".

## Cause

The room heap check (tools/chim/heap.py require_room_map_heap, CHIM-ROOM-16MB-REFUSAL-48) marks each room over the
16 MB baseline's zone with `_chim_room_fast_mb "32"` in its map's worldspawn. It ran after the map optimizer had
recorded every staged map's hash, and nothing told the receipt, so the final optimizer check saw 16 changed maps.

The first note said the guard torch fix (GUARD-TORCH-TYPES-LIMIT-48, the engine's guard table from 32 to 128 records)
pushed these rooms over the line. The measurements do not support that:

- dev2 try 13 is the first dev2 run whose image step reached the room heap check at all. Tries 9 to 12 stopped
  earlier (try 9: a room's record placements, tries 10 and 11: the actor placement gate, try 12: "Too many distinct
  staged guard models"); no earlier run on the build volume has a chim-room-heap.json or a "[chim] room heap" line.
- The room heap model does not read the engine's static memory. A room's zone comes from the built heap (11 MiB),
  the measured start-up Hunk (782,416 bytes), the room map's own bytes and its "_chim_hunk_rest"
  (tools/engine_limits.py whole_map_zone); the guard table is static data outside the Hunk.
- The guard table: one record (guard_asset_t, aw_guard_torch.c) is 540 bytes, so 128 records are 69,120 bytes, 51,840
  more than 32 records. The visible table (GUARD_VISIBLE 32) did not change. dev2 try 12 staged 51 records, so 64
  would also hold them; 128 stays, as the change does not move any room.

These 16 rooms were over the 16 MB zone before; the marking was simply never reached in a dev2 image until try 13.

## The 16 rooms (dev2 try 13, image/chim-room-heap.json)

Every room's 16 MB room zone is its zone less the 32 KiB loading buffer; the 32 MB minimum gives every room
15,384,576 bytes (the zone and the automatic 8 MiB cache bank) and one block of 8,388,608 bytes. All 16 are right to
need 32 MB: each is over the 16 MB room zone and well within the 32 MB room, its largest model within one block.

| Room map | Models | Textures | Need (bytes) | 16 MB room zone | Over by | Largest model |
| --- | --- | --- | --- | --- | --- | --- |
| ri0ef0d511bc | 49 | 33 | 7,341,376 | 6,995,968 | 345,408 | 584,080 |
| ri3e199d5c68 | 79 | 83 | 7,785,728 | 6,995,968 | 789,760 | 1,344,240 |
| ri70e838d34b | 68 | 56 | 7,182,224 | 6,995,968 | 186,256 | 529,824 |
| ri8d9058173f | 56 | 51 | 7,349,376 | 6,995,968 | 353,408 | 660,016 |
| rib6b57dacaf | 66 | 47 | 7,025,008 | 6,995,968 | 29,040 | 627,984 |
| ric66b86d071 | 57 | 46 | 7,800,800 | 6,995,968 | 804,832 | 1,344,240 |
| rida15675a31 | 57 | 16 | 8,778,448 | 6,995,968 | 1,782,480 | 678,720 |
| ridcbc2faeeb | 51 | 42 | 7,569,360 | 6,979,584 | 589,776 | 1,344,240 |
| riddfb54bff8 | 58 | 54 | 8,416,656 | 6,995,968 | 1,420,688 | 1,344,240 |
| rie242a8d69e | 19 | 32 | 9,440,448 | 6,995,968 | 2,444,480 | 3,081,200 |
| rieb69889bf7 | 72 | 29 | 8,471,104 | 6,995,968 | 1,475,136 | 748,336 |
| riebb6d4996f | 67 | 41 | 7,019,440 | 6,995,968 | 23,472 | 678,720 |
| ried69dd9c9b | 60 | 64 | 7,067,920 | 6,995,968 | 71,952 | 678,720 |
| rifa4ef181ed | 135 | 44 | 10,450,608 | 6,979,584 | 3,471,024 | 542,032 |
| rifd64641858 | 77 | 64 | 7,733,648 | 6,995,968 | 737,680 | 748,336 |
| riff3395ef71 | 79 | 65 | 7,325,648 | 6,995,968 | 329,680 | 529,824 |

1,132 rooms were checked; the other 1,116 fit the 16 MB zone. Three rooms are close to the line (rib6b57dacaf 29,040
bytes over, riebb6d4996f 23,472, ried69dd9c9b 71,952); the largest is rifa4ef181ed (135 models, 3.3 MiB over). The mark
lies at entity text offsets 417 to 457 in every marked map, inside the first KiB the engine reads at the door.

## Fix

- tools/optimize_world_maps.py rebind_marked_maps: the receipt follows exactly the named maps. Each must be a
  receipt row the optimizer did not optimize and a CHIM room map; its row takes the marked bytes and keeps the hash
  before the mark ('marked_from_sha256', 'marked'), and the receipt records the change under 'post_optimizer_marks'.
  Every other map must still match its row: any other change stops the image as before.
- tools/build_aga.py finalize_image: the room heap check now runs before the final world-map heap audit, with the
  receipt checked right before it (verify_optimized_maps) and rebound right after it, so the final heap audit and the
  last optimizer check bind to the marked maps.
- tools/chim/heap.py require_room_map_heap: the marked rooms are measured again after the mark (the map is a few
  bytes longer and sits before the zone), so the report describes the maps as they ship.
- The early check, tests/test_post_optimizer_map_writers.py: every call in the image step that writes maps after the
  optimizer (the CHIM frame maps, the room heap check, the room and frame marks) is followed by a receipt rebind before
  the next receipt reader, the room mark is written only by the room heap check, and the try 13 stop is reproduced
  without the rebind.

A rebuild reruns the image step (its finalize part) only; every earlier stage, the CHIM rooms and the optimizer pass
cache are reused.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Content silently missing from a build (`build-content-missing`). Every omission is receipted; payload and entity counts are compared with the last release; shipped features are on by default. See [families](README.md#families).

- [ACTOR-LIBRARY-LEFT-OUT-48](ACTOR-LIBRARY-LEFT-OUT-48.md): The actor library made no model for corpse creatures and for town NPCs standing outside the towns: 9 outdoor references left out
- ACTOR-MOVING-RUNTIME-GROUND-48 (no report page): Moving actors (levitation, flying creatures, jumping, swimming, knockback, scripted SetPos) need runtime grounding beyond the build-time bake
- [ARENA-PIT-NO-INTERIOR-33](ARENA-PIT-NO-INTERIOR-33.md): The Vivec Arena minigame fights on the test floor: the Arena Pit interior is not in v0.0.33 builds
- [AUDIO-MISSING-SOURCES-32](AUDIO-MISSING-SOURCES-32.md): The image step reports missing sources for 7 voices and 2 effects
- BUILD-AWF-AWS-EXTENSION-CLASH-54 (no report page): New fog and smoke tables took the extensions .awf and .aws, which already mean font and sprite: the palette overlay parsed the fog table as a font
- [BUILD-CHIM-ROOMS-IMAGE-RACE-36](BUILD-CHIM-ROOMS-IMAGE-RACE-36.md): The image step ran beside a CHIM town's room stage and read its record before it existed
- [BUILD-CHIM-SANDBOX-NO-SHARED-SKY-36](BUILD-CHIM-SANDBOX-NO-SHARED-SKY-36.md): An area build of a CHIM town without exterior BSP maps ships no shared sky although its CHIM frame names it
- [BUILD-DRESSING-EXCLUDED-32](BUILD-DRESSING-EXCLUDED-32.md): The repository builder drops lantern hooks and other dressing in Seyda Neen maps without a receipt
- [BUILD-EXTRA-TOWN-OPTIN-32](BUILD-EXTRA-TOWN-OPTIN-32.md): A default build leaves out the Vivec Arena preview that v0.0.32 ships
- [BUILD-FLORA-OPTIN-32](BUILD-FLORA-OPTIN-32.md): A from-scratch build without --tree-sprites leaves out the trees and grass every release ships
- [BUILD-HANDS-NOT-BUILT-32](BUILD-HANDS-NOT-BUILT-32.md): Per-race first-person hands are not built by the builder
- [BUILD-HARVEST-NATIVE-TOWN-ORDER-36](BUILD-HARVEST-NATIVE-TOWN-ORDER-36.md): The image step's harvest check refused a CHIM-native town's catalogues before its frame map was written
- [BUILD-HARVEST-NOT-BUILT-32](BUILD-HARVEST-NOT-BUILT-32.md): Mushroom harvest data is not built by the builder
- [BUILD-IMAGE-NATIVE-BALMORA-CACHE-36](BUILD-IMAGE-NATIVE-BALMORA-CACHE-36.md): The image step asked for the legacy Balmora cache when Balmora is CHIM-native
- [BUILD-LAVA-COVERAGE-38](BUILD-LAVA-COVERAGE-38.md): Full dev2 world omits the reported lava cells
- [BUILD-LEGACY-TOWN-MAPS-SHIPPED-36](BUILD-LEGACY-TOWN-MAPS-SHIPPED-36.md): CHIM-native Seyda Neen is still built through the legacy chain: 65 sn maps are built and removed before packing (build time, not payload)
- [BUILD-MINIWIND-ARENA-PIT-REFUSED-36](BUILD-MINIWIND-ARENA-PIT-REFUSED-36.md): Regression against v0.0.35: the Vivec Arena Pit is in no CHIM build (no CHIM-native stage made the Arena's rooms), and its start was refused as not converted
- [BUILD-MINIWIND-BALMORA-ASSUMED-36](BUILD-MINIWIND-BALMORA-ASSUMED-36.md): A MiniWind image of another town fails its content fingerprint: the Balmora region table was always required
- [BUILD-MINIWIND-DIRECT-START-TOWN-36](BUILD-MINIWIND-DIRECT-START-TOWN-36.md): A MiniWind build of another town refuses its own direct start: the start check assumed Balmora
- [BUILD-NIGHT-TABLES-31](BUILD-NIGHT-TABLES-31.md): Repository image builds have no night lamp, glowing glass or location fog tables
- [BUILD-RUN-FOLDER-PRECREATED-36](BUILD-RUN-FOLDER-PRECREATED-36.md): Every real CHIM build is refused at its start: the plan writes the world map manifest into the run folder before the run makes it
- [BUILD-STANDALONE-STAGES-32](BUILD-STANDALONE-STAGES-32.md): Door overlay and interior section tools are outside the builder; their use in v0.0.31 is unverified
- [CHIM-CELL-FEATURE-LIST-INCOMPLETE-38](CHIM-CELL-FEATURE-LIST-INCOMPLETE-38.md): Cell feature list incomplete: original placements and gameplay support are not reconciled with packaged coverage
- [CHIM-COAST-OBJECTS-MISSING-36](CHIM-COAST-OBJECTS-MISSING-36.md): Objects including Dwemer ruins are reported missing from the CHIM coast
- [CHIM-LAVA-TERRAIN-SPIKES-38](CHIM-LAVA-TERRAIN-SPIKES-38.md): Angular terrain wedges cross a lava pool in the final-image inspection
- [CHIM-NATIVE-IMAGE-NO-SHARED-SKY-36](CHIM-NATIVE-IMAGE-NO-SHARED-SKY-36.md): CHIM-native images with no legacy exterior (MiniWinds of one town) ship without the shared sky their frame maps name
- [CHIM-REGION-DOORS-NO-ROOMS-48](CHIM-REGION-DOORS-NO-ROOMS-48.md): The load doors of CHIM region frames never lead into a room
- [CHIM-ROOM-LAVA-UNDER-WATER-48](CHIM-ROOM-LAVA-UNDER-WATER-48.md): CHIM rooms could not hold a lava pool whose bed reaches under the water level: 3 base-game rooms set aside
- [CHIM-ROOM-SHELL-NO-HULL-48](CHIM-ROOM-SHELL-NO-HULL-48.md): Batch CHIM rooms declared no standing hull, so the actor ground check refused all 1,910 of their residents
- [CHIM-TRACKER-APRON-40](CHIM-TRACKER-APRON-40.md): Tracker counts town apron dependencies as complete original cells
- [GUARD-TORCH-REBAKE-MISMATCH-48](GUARD-TORCH-REBAKE-MISMATCH-48.md): Eight guards first staged in v0.0.48 get no torch: their base models do not rebake exactly
- [GUARD-TORCH-TYPES-LIMIT-48](GUARD-TORCH-TYPES-LIMIT-48.md): The image step stops on Too many distinct staged guard models: the batch rooms bring more than 32 guard types
- IMAGE-WORLD-BATCH-PAIRS-52 (no report page): The image stopped writing a world partition: the boot units moved off DH0 (source, volume path pairs) were turned into paths before the pairs were read
- INTERIOR-ACTIVATORS-LEFT-OUT-52 (no report page): Interiors leave out every activator but the beds: the heart of Lorkhan is missing from Akulakhan s Chamber, and bar counters, shrines and Dwemer machinery from hundreds of rooms
- [INTERIOR-PLACED-ITEMS-47](INTERIOR-PLACED-ITEMS-47.md): Takeable and movable items and containers in converted interiors are not live objects (placed items are left out)
- [LAVA-NOT-IMPLEMENTED-33](LAVA-NOT-IMPLEMENTED-33.md): Lava is drawn as plain static meshes: no liquid surface, no damage, no view tint, never tracked
- MINIWIND-EXTERIOR-CHIM-INTERIORS-52 (no report page): An exterior MiniWind stops in its image step: the image is told to install the CHIM interior store that the exterior scope does not build
- [MINIWIND-PAYLOAD-NOT-SLIM-33](MINIWIND-PAYLOAD-NOT-SLIM-33.md): MiniWind #2 was built with the full movie and voice payload
- [NIGHT-WINDOWS-LOST-CHIM-36](NIGHT-WINDOWS-LOST-CHIM-36.md): Windows no longer glow at night: the night-windows table has been empty since the towns moved to CHIM
- [PLAYTEST-PAYLOAD-COVERAGE-32](PLAYTEST-PAYLOAD-COVERAGE-32.md): The v0.0.32-dev1 playtest has no first-person hands and no harvest
- [RELEASE-PRIVATE-NAMES-48](RELEASE-PRIVATE-NAMES-48.md): Two public files named the private working folder, and seven public lines used a banned abbreviation for actor behaviour
- [ROOM-ACTORS-FLOATING-48](ROOM-ACTORS-FLOATING-48.md): Regression: 1,662 residents of batch CHIM rooms stood above the floor, never fitted to it
- [ROOM-BATCH-HARVEST-48](ROOM-BATCH-HARVEST-48.md): Harvestable plants in batch rooms may stay baked scenery
- [ROOM-BATCH-NPC-GROUNDING-48](ROOM-BATCH-NPC-GROUNDING-48.md): The residents of rooms no town list holds have no grounding class: --room-batches 5 is refused (62 NPCs in 22 rooms)
- [ROOM-BATCH-WATER-OUTSIDE-48](ROOM-BATCH-WATER-OUTSIDE-48.md): Room batches refused rooms whose cell water lies under or over everything the room places (water outside the room bounds)
- [SEYDA-LANTERNS-MISSING-31](SEYDA-LANTERNS-MISSING-31.md): Seyda Neen lanterns light the night but are not in its maps
- [SKY-FLAT-PALETTE-DRIFT-41](SKY-FLAT-PALETTE-DRIFT-41.md): Exterior sky flat with no clouds: the sampled palette drifted and the shared cloud sky silently fell back to a one-colour placeholder
- TREE-SCALE-001 (no report page): Non-unit-scale tree sprites omitted; bounds too conservative
- VIVEC-HOVER-VERIFY-48 (no report page): Vivec (the god) floats in meditation: verify whether it is his animation over a grounded collision origin or an active effect

<!-- END GENERATED CATEGORY -->
