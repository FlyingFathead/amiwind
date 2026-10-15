# The CHIM progress map: what CHIMport is and what every colour means

The CHIM progress map shows, cell by cell, how far AmiWind's open world has moved from Quake's old way of storing a
map onto CHIM. It appears in the README, in the release notes and in the Toolkit (the World Map's CHIM Progress
Tracker layer). This page explains the work behind it in plain words, then goes through every colour: what it
means, the problems that usually sit behind it, a few examples, what fixes it and who decides. The tracker itself,
its statuses and its commands are described in [CHIM Progress Tracker](PROGRESS_TRACKER.md); the live figures are on
the generated [CHIM cell tracker](CELL_TRACKER.md).

<!-- contents start -->
## Contents

- [What CHIMport is](#what-chimport-is)
- [Why: what Quake's map format cannot do for an open world](#why-what-quakes-map-format-cannot-do-for-an-open-world)
- [What CHIM does instead](#what-chim-does-instead)
- [Reading the map](#reading-the-map)
- [Green: done](#green-done)
  - [Cell complete and terrain complete](#cell-complete-and-terrain-complete)
  - [Awaiting lighting (green with cyan stripes)](#awaiting-lighting-green-with-cyan-stripes)
  - [Passed, something still deferred (plain green)](#passed-something-still-deferred-plain-green)
- [Violet: hull policy pending](#violet-hull-policy-pending)
- [Red: failing a check](#red-failing-a-check)
- [Magenta: not converted](#magenta-not-converted)
- [Dark grey: not started](#dark-grey-not-started)
- [Blue: empty sea](#blue-empty-sea)
- [Silver: open ocean](#silver-open-ocean)
- [Gold: planned for a release](#gold-planned-for-a-release)
- [Owner marks: approved, playtested, accepted](#owner-marks-approved-playtested-accepted)
- [Problems that are not a colour](#problems-that-are-not-a-colour)
- [Who decides what](#who-decides-what)
- [Package inclusion](#package-inclusion)
- [Reproducing the current image](#reproducing-the-current-image)

<!-- contents end -->

Current source checkpoint, 15 October 2026: boundary ownership repair passes
37 focused checks and the source contract for all 369 frames. Combined-world
readback, split-model/sprite dependencies, seams, native gameplay and full
package gates remain pending. Converted, audited, native-checked and packaged
coverage retain their previous receipts.
[Ownership repair](../bugs/CHIM-FRAME-DEPENDENCY-OWNERSHIP-40.md).


15 October 2026 source geometry follow-up: original height/coordinate and
shared-edge checks pass for the inspected Seyda area. Local detail and diamond
repairs are integrated; compiled-world and native seams remain pending. This
source finding changes no converted, native-checked or packaged cell counts.
The complete source suite passes with explicit skips and expected failures.
Original reference rays use a different diagonal from render/contact triangles;
this finding does not promote collision or native seam acceptance.
[Terrain report](../bugs/CHIM-TERRAIN-DIAGONAL-40.md),
[actor contact](../bugs/CHIM-SEYDA-ACTOR-CONTACT-33.md).


15 October 2026 combined-world update: all 369 frames are generated; six fail
frame ownership validation. All 36 repeated originals have one logical owner
plus boundary dependencies; binary equivalence remains unresolved. The failed
world is excluded from acceptance. All converted, audited, native-checked and
packaged counts retain their previous evidence. Complete rings 0, 1 and 2 and
adjacent-cell checks remain required.
[Boundary ownership](../bugs/CHIM-FRAME-DEPENDENCY-OWNERSHIP-40.md).

## What CHIMport is

Morrowind's world is one big outdoor space made of square cells (Vvardenfell has 1,292 land cells, Solstheim 144).
AmiWind started by cutting that space into many small Quake maps, one per region, and loading them one at a time.
**CHIMport** is the work of moving the whole island from those legacy Quake region maps onto CHIM, the project's
own way of storing and streaming a world ([CHIM](README.md)). It goes cell by cell, **starting at the coast and
spiralling inward**, because the coast is where the land meets the sea and the neighbouring cells can be checked
edge by edge. [CHIMport](CHIMPORT.md) describes the conversion tool and its audits; the progress tracker keeps the
score, and the map is the picture of that score.

## Why: what Quake's map format cannot do for an open world

AmiWind runs on a Quake engine (AmiQuake). Quake maps (the BSP29 format) were made for corridors and rooms, not for an
island. The documented problems for an open world are:

- **A map is one self-contained file with fixed limits.** Its tables use 16-bit indices, an entity can touch at most
  16 leaves of the map before it counts as visible everywhere, and there are fixed limits on surface lists and texture
  info ([the .chim map format](CHIM_MAP_FORMAT.md)). A whole area cannot be one map.
- **Coordinates are small.** The engine's positions were designed for a range of about +-4,096 units, so a large
  area has to be re-centred as the player moves ([engine notes](ENGINE.md)). Version 0.0.36 widens the range so
  that a whole city fits one map ([release notes](../RELEASE-v0.0.36.md)).
- **Every map is a separate file, and objects are copied.** The old exterior regions each carry a core of 768 units
  plus an overlap on every side, so each placed object is stored about ten times, and every
  map holds its own copy of every texture it uses ([world streamer](../WORLD_STREAMER.md)).
- **Quake's visibility does not help outdoors.** Quake hides what cannot be seen through walls; in the open air
  almost everything can be seen, so the visibility data culls little ([town visibility](../performance/TOWN-VISIBILITY.md)).
- **Every region crossing reads a whole map** from a slow disk ([Seyda Neen performance](../SEYDA_NEEN_PERFORMANCE.md)).
- **The Amiga is small.** Memory is tight; disk partitions must stay below 2 GiB and drive images below
  4 GiB ([image size](../IMAGE_SIZE.md)). Storing the island ten times over does not fit, and loading it
  whole into memory is out of the question.

## What CHIM does instead

- **Store once, place by reference.** Every mesh, collision shape and texture is stored a single time; a placement
  is a small record that names its model ([world streamer](../WORLD_STREAMER.md)).
- **Small pieces, streamed.** The land is cut into frames of 3 x 3 cells, chunks of 256 units and small sector
  files that a classic Amiga disk reads whole; the engine streams them around the player ([CHIM](README.md),
  [world format](WORLD_FORMAT.md)).
- **Shared terrain.** Terrain is stored once as compiled pieces, and the open sea around the island is a single
  shared ocean piece.
- **Its own map file.** A CHIM map is a `.chim` file, no longer a Quake `.bsp`, and the plan is to leave BSP29's
  limits behind step by step; interiors stay ordinary Quake `.bsp` maps until they move too
  ([the .chim map format](CHIM_MAP_FORMAT.md)).
- **Wide coordinates**, so one frame can cover a whole city.

## Reading the map

The current README map uses the public reference generated **15 October 2026, 06:48 UTC**. The [cell tracker](CELL_TRACKER.md) records the matching audit
totals and a separate package ledger. These figures describe Vvardenfell only.

| Status | Cells | Included in audit milestone |
| --- | ---: | --- |
| Cell complete, awaiting lighting | 11 | yes |
| Terrain complete, awaiting lighting | 758 | yes |
| Passed, something still deferred | 407 | yes |
| Empty sea | 99 | yes |
| Converted, failing a check | 15 | no |
| Not converted | 2 | no |
| Hull policy pending | 0 | no |
| **TOTALS** (land and empty sea) | **1,292** | **1,275 (98.7%)** |
| Open ocean, outside that denominator | 865 | no |

There are **1,191 converted cells**, including the 15 failing cells. Empty-sea
cells do not require placed-object conversion. A successful geometry audit is
not proof of original actors, gameplay, lighting, native traversal or inclusion
in an image. Keep those checks separate for each original reference type.

The compact README image groups audit milestones in green and failures or
unfinished conversions in red. The Toolkit distinguishes more states, including
lighting stripes, blue empty sea and magenta unconverted cells. The counts above
use the statuses in the data, not the number of colour shades in the PNG.

## Green: done

The tracker's historical internal name is `done`; on the current image the label
is **audit milestone**. Every measured required check passed, or the cell is
empty sea. Unmeasured checks and deferred features remain unresolved.

### Cell complete and terrain complete

These statuses require lighting as well as the geometry checks. Terrain-complete
cells may defer actors. The current Vvardenfell reference has zero cells in
either fully lit status; awaiting-lighting statuses are listed separately.

### Awaiting lighting (green with cyan stripes)

The Toolkit marks **773 cells** here: 11 cell-complete-but-unlit and 762
terrain-complete-but-unlit. The README's compact map groups them in green.
Across the 1,292-cell tracker denominator, lighting is partial in 135 cells,
unlit in 1,056 and not measured in 101. No cell is recorded fully lit.

### Passed, something still deferred (plain green)

There are **403** cells in this state. Inspect the cell's deferred reference
types and unmeasured checks before treating it as a complete scene. Converted
terrain and objects do not establish NPC or creature presence, dialogue,
combat, quests or other gameplay.

## Violet: hull policy pending

The current reference has **zero** cells in this status. This does not establish
that every collision defect is fixed: failing collision checks and cells held
from a particular build remain separate.

A hull-policy hold means the collision chain requires an explicit policy or a
converter repair. The older 11 October snapshot had 218 such cells, mostly
plants; that is historical evidence, not today's count. Retain the established
mesh optimization, collision, memory and native traversal checks when repairing
a cell. Do not raise budgets or add a duplicate BSP to hide a CHIM failure.

## Red: failing a check

There are **15 converted cells** with failed checks. The tracker lists 9
memory-fit failures, 7 hull-bevel/chain failures and 6 stair-walk failures;
these overlap and must not be added into a count of distinct cells.

Trace the failed mechanism, repair it, and rerun the affected cells. Offline
audit results do not replace matched original-game comparisons and actual
walking/collision checks in the target engine.

## Magenta: not converted

There are **2** unconverted Vvardenfell cells: West Gash (-3,1) and Caldera (-2,2).
Window mounting across a cell border remains an open repair class; see
[CHIM-WINDOW-MOUNT-CROSS-CELL-33](../bugs/CHIM-WINDOW-MOUNT-CROSS-CELL-33.md).
The older count of 29 included 25 stale-source lava reruns. It must not be used
as the current count or as evidence that lava is still wholly unconverted.

## Dark grey: not started

The public reference includes **144 Solstheim land cells** as not started.
Vvardenfell has been reached throughout. These are separate island totals;
Solstheim is not in the 1,292-cell Vvardenfell denominator.

## Blue: empty sea

There are **99** land-record cells containing terrain and water without placed
objects. They count toward the audit milestone. The Toolkit uses blue; the
compact README image groups them with the green milestone cells.

## Silver: open ocean

The **865 Vvardenfell open-ocean cells** are counted separately. A shared ocean
piece or ocean-coloured square does not establish runtime placement. Keep them
outside the land and empty-sea denominator until the tracker policy and evidence
support a change.

## Gold: planned for a release

Gold is a planning overlay, never evidence of packaged content. The public
reference used by the current image has no release-plan layer, so the image
shows no gold outlines. The old v0.0.36/v0.0.37 plans are historical and are not
automatically reassigned to v0.0.39.

The current target is all **exterior** cells in rings 0, 1 and 2. Record excluded,
failed and held cells explicitly. The ring table contains 5 open-ocean cells in
ring 0, 171 cells in ring 1 and 160 in ring 2; this membership is not an inclusion
claim. Interiors may independently remain BSP, CHIM or a mixture.

## Owner marks: approved, playtested, accepted

These are explicit review states. A conversion, a green colour or a packaged
file cannot set them. An accepted failure remains labelled as a failure accepted
for a particular development build, with its scope and evidence retained.

## Problems that are not a colour

- **Lava:** the v0.0.38 conversion includes the 27 lava-bearing exterior cells
  and 349 original lava references. Legacy BSP and CHIM paths both matter.
  Scoped lava-contact tests do not establish every pool's traversal, audio or
  safe-save behavior; see [LAVA.md](../LAVA.md) and the open bug reports.
- **Exterior ownership:** each exterior location has one selected terrain and
  scenery format. Superseded BSP maps must not be compiled or packaged alongside
  CHIM. Routing aliases do not require duplicate legacy geometry.
- **Actors and gameplay:** original reference types, converted geometry,
  deferred actors and implemented interactions need independent accounting;
  see [CHIM-CELL-FEATURE-LIST-INCOMPLETE-38](../bugs/CHIM-CELL-FEATURE-LIST-INCOMPLETE-38.md).
- **Unmeasured checks:** an absent result is unknown, not passed.
- **Lighting:** 101 cells in the Vvardenfell denominator lack a measurement.

## Who decides what

Converter and engine defects need code repairs and verification. Policies that
trade collision detail, CPU cost or memory require an explicit documented
decision. Release selection and acceptance are recorded independently of
conversion. The bug register remains the single source of current issue status.

## Package inclusion

Post-pin RC2 evidence, 14 October: 360 regional whole cells are verified by
full disk readback and independent package extraction. Six selected town
overlaps remain partial and are excluded. The exact inspection artifacts were
finalized at 2026-10-13T22:15:44Z. Conversion/audit/native-cell counts are unchanged;
artifact shipment does not certify every actor, gameplay feature or route.
Owner acceptance remains separate.

**Historical RC1 package check, 13 October 2026:** the exact image and
independently extracted package contain 360 verified
whole regional cells, including Tel Uvirith (10,1). Six selected cells
(-3,-11), (-2,-11), (-1,-11), (0,-11), (5,-14) and (6,-14) overlap packaged
town frames only partially and are excluded from that whole-cell count.
All 9,360 frame/chunk files for the 360 cells and all 9,774 CHIM payload files
remain byte-identical to the verified predecessor. The index and four named
town frame maps are present; town coverage and interiors are separate counts.
The 135 town-owned routing-only BSPs are absent under the validated checklist;
required map/dependency readback passed. Native boundary routing remains open.

The exact HDF comparison removes 142,235,493 payload bytes across 212 files:
135 redundant BSP maps and 77 orphan harvest catalogues. No map additions or
unexpected map removals are reported. The independently extracted RC1
playtest ZIP is 2,060,379,345 bytes. Payload savings and compressed archive
size are distinct measurements; these figures do not identify a final039 ZIP.

RC1 package and matching source delivery finalized on 13 October 2026 at
18:06:05 UTC (21:06 in Finland), with source `57a8699` and image `fbf9a6c`
kept distinct. The six partial overlaps remain outside the shipped whole-cell
count. Final v0.0.39 private playtest and matching public source delivery
finalized at 2026-10-14T07:15:35Z. Earlier RC1/RC2 scene checks remain
historical, scoped evidence. Shipment does not establish owner acceptance
or close the renewed [third-person punch](../bugs/PLAYER-PUNCH-THIRDPERSON-39.md),
[readied movement](../bugs/PLAYER-READY-MOVEMENT-39.md),
[blocking](../bugs/COMBAT-BLOCKING-36.md) or
[swimming](../bugs/WATER-GAMEPLAY-PARITY-38.md) reports.
Independent fresh-download verification remains separate.

Conversion/audit data is the 15 October 2026, 06:48 UTC snapshot:
1,191 converted cells including 15 failed audits, 99 empty sea, two not
converted, and 1,275/1,292 audit milestones. The v0.0.40-dev1 Pelagiad (0,-7)
conversion passed measured offline audits; deferred actors, seven spatially
excluded references and unmeasured lighting/native checks remain separate.
The RC2 package layer is unchanged and does not include this new conversion. The 865 ocean cells are
outside the denominator. Converted and packaged per-type actor/gameplay
counts remain unknown; the original reference census is preserved. Planned
cells are not included cells and package presence does not prove gameplay.


## Reproducing the current image

The image uses only the sanitized public cell reference and flat colours, with
no game textures or screenshot material:

```sh
python3 tools/cell_progress_map.py --data docs/chim/cell-progress-reference.json --out docs/images/amiwind-v0.0.40-rings-progress-map.png --date "2026-10-15"
```

Update the image, caption and evidence counts together when the reference or
package ledger changes. Keep historical images and published packages intact.

The 14 October 2026, 22:19 UTC tracker refresh records offline checks for five
ring-0 ocean frames. Their four original leveled-creature spawns remain deferred.
Runtime placement, native seams and package inclusion are pending, so the map
colours and milestone totals are unchanged.

The 14 October 2026, 23:45 UTC refresh records the expanded Vivec conversion
as 36 original core cells and 28 apron-only dependencies. It retains 6,039
owned references, 33 external dependencies and 297 deferred references.
Global converted and packaged counts are unchanged. Native seams and the
combined candidate remain pending.

Expanded Seyda conversion now records 16 original core cells and 20 separate
apron cells, with 2,982 owned references, 103 dependencies and 1,461 deferred
references. Its 3,724 walked stair probes pass; 532 advisory findings and 29
zone chunk loads without room remain explicit. The earlier 15-failure stair
result is preserved. Native traversal, adjacent-cell seams and packaging remain
pending. The final v0.0.40 plan includes all rings 0–2; planned cells do not
increase conversion or package counts.
