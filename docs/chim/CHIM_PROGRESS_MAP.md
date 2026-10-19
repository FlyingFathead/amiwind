# The CHIM progress map: what CHIMport is and what every colour means

_Last updated with AmiWind v0.0.45 (19 October 2026)._

<!-- contents start -->
## Contents

- [v0.0.41 candidate - visibility aprons, 15 October 2026](#v0041-candidate---visibility-aprons-15-october-2026)
- [v0.0.41 candidate - window support, 15 October 2026](#v0041-candidate---window-support-15-october-2026)
- [v0.0.41 candidate - lava coverage, 15 October 2026](#v0041-candidate---lava-coverage-15-october-2026)
- [Compiled apron selection, 15 October 2026](#compiled-apron-selection-15-october-2026)
- [Paired boundary validation, 15 October 2026](#paired-boundary-validation-15-october-2026)
- [Owner apron follow-up, 15 October 2026](#owner-apron-follow-up-15-october-2026)
- [Combined-world gate update, 15 October 2026](#combined-world-gate-update-15-october-2026)
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
- [Maintainer marks: approved, playtested, accepted](#maintainer-marks-approved-playtested-accepted)
- [Problems that are not a colour](#problems-that-are-not-a-colour)
- [Who decides what](#who-decides-what)
- [Package inclusion](#package-inclusion)
- [Reproducing the current image](#reproducing-the-current-image)

<!-- contents end -->

[CHIM-CELL-FEATURE-LIST-INCOMPLETE-38](../bugs/CHIM-CELL-FEATURE-LIST-INCOMPLETE-38.md) — 15 October 2026, v0.0.41-dev1: full-build preparation rejected five explicitly selected ocean routing cells absent from the original CELL/LAND inventory, before legacy compilation. The source checklist now records additional ocean routing cells separately and allows their absence only before routing rows are appended. Final classification/stage verification still requires every row and CHIM routing flags; undeclared or unselected missing cells are rejected. All 98 targeted checks across five modules pass, including three new ocean checklist regressions. Exact production conversion, native ocean behavior, image/package and delivery checks remain pending; coverage states are unchanged.

[CHIM-FRAME-STATIC-SEAM-40](../bugs/CHIM-FRAME-STATIC-SEAM-40.md) — 15 October 2026, v0.0.41-dev1: whole-world metadata binding failed because tutorial barrel reference 172851 lacked its original CELL, while the original audit records [-2,-9]. A narrow source correction restores only that missing field before capture, rejecting nonempty wrong cells and every other identity/transform mismatch. Fifty focused Seyda/ownership checks pass, including three new semantic regressions. The preceding 4,247-test full-suite pass remains historical; the repaired world is pending. The prepared Linux source kit is held and undelivered. Native, image/package and playtest acceptance remain pending; coverage states are unchanged.

[CHIM-FRAME-STATIC-SEAM-40](../bugs/CHIM-FRAME-STATIC-SEAM-40.md) — 15 October 2026, v0.0.41-dev1 image integration follow-up: added Seyda dependency numbers and model digests are checked against the world-index-bound source manifest before source-carrier static parity includes them. Frames without supplements retain prior behavior. The focused ownership/apron module now passes 33 checks, including five new semantic regressions and missing/rebound-model rejection. The issue remains OPEN; exact world rebuild, held-boundary/native and image/package checks remain pending.

[CHIM-FRAME-STATIC-SEAM-40](../bugs/CHIM-FRAME-STATIC-SEAM-40.md) — 15 October 2026, v0.0.41-dev1: a source repair supplements only missing Seyda apron dependencies using the included original-cell owner's exact compiled mesh and textures, preserving original identity and unique ownership while translating frame-local origins. It targets rock reference 251397 and shell reference 461804; 32 focused ownership/apron checks pass. The rebuilt world and held boundary/native checks remain pending. Separately, independent normal interior/actor/UI conversion completed 2,451 files with unchanged source and inputs; it is not image, native or package acceptance. CHIM coverage states are unchanged. Earlier full-suite and world results remain bound to their preceding source; changed apron acceptance is pending.

[CHIM-FRAME-STATIC-SEAM-40](../bugs/CHIM-FRAME-STATIC-SEAM-40.md) — 15 October 2026, v0.0.41-dev1: exact source validation completed 4,242 tests (4,236 passed, three Windows-only skips and three Census expected failures), with zero failures/errors; the matching engine compiled. The completed 369-frame world passed structural/source, modeled heap, host zone-walk and scoped stair gates. Of 547 boundary comparisons, 544 measured agreement and three remain held (237, 241, 242). Of 36 sampled models, 22 have matching face counts and unique face correspondence; 14 differ in collision-only versus visual representation and require payload/sprite/native review. These measurements do not establish visual severity or universal equivalence. Native captures, independent interior conversion, image assembly/readback and package acceptance remain pending; coverage states are unchanged. Stair evidence retains 15,348 advisory findings despite zero blocking failures.

15 October 2026: active preparation now targets v0.0.41-dev1. The planned final release title is **v0.0.41: Collisions And Boundaries**. Earlier source snapshots, checks and findings retain their recorded version identities; they do not establish acceptance of this development candidate. Matching source validation, completed image assembly/readback, native checks, packaging and delivery remain separate gates. See the [current development candidate](../RELEASE-v0.0.41-dev1.md).

[BUILD-INVENTORY-PALETTE-41](../bugs/BUILD-INVENTORY-PALETTE-41.md) — 15 October 2026, v0.0.41 source candidate: image assembly prepares inventory before the sky palette pass, which rejected current AWIC icons and AWI2/AWST metadata as unknown images. The source repair validates each inventory format at its exact path, remaps only icon pixels and preserves metadata bytes. Scoped evidence contains 15 passing palette checks and 2 passing inventory-asset checks on matching unchanged source. Actual image assembly, native verification, packaging and shipment remain pending.

[CHIM-FRAME-STATIC-SEAM-40](../bugs/CHIM-FRAME-STATIC-SEAM-40.md) — 15 October 2026, v0.0.41 source candidate: the 941 world stopped at the unchanged ownership guard because ten explicitly deferred Seyda references reappeared through a named-town apron. The candidate applies the existing exact owner dispositions to named and regional neighbours alike. All ten original deferred IDs are verified and 38 focused checks pass. Fresh affected-world conversion and renewed boundary/memory checks remain pending; no coverage, native, package or maintainer acceptance is promoted.

[CHIM-MODEL-ARENA-RESERVE-41](../bugs/CHIM-MODEL-ARENA-RESERVE-41.md) — 15 October 2026: exact allocation and predecessor-world checks remain separately recorded. The later 941 world stopped at its ownership guard because named aprons bypassed ten existing deferred-owner dispositions. The source-only disposition repair passes 38 focused checks; fresh world, boundary/model review and native/package acceptance remain pending.

[CHIM-RECIPE-APRON-SCOPE-41](../bugs/CHIM-RECIPE-APRON-SCOPE-41.md) — 15 October 2026, v0.0.41 candidate: recipe repair converted all four affected frames with structural PASS. Three still failed the unchanged memory gate (peaks 6,957,632; 6,939,952; 6,644,768 bytes for (10,0), (10,1), (9,2)); (11,0) passed at 5,875,568 bytes. The separate placed-model reserve repair passes all four on identical world bytes. A complete successor world and recipe/model/sprite equivalence and native checks remain pending.

15 October 2026: exact-source validation completed 4,231 tests: 4,225 passed, three Windows-only skips and three tracked Census expected failures. The 71 focused tests and original-data readback across nine frame positions passed, consistently hiding 33 of 158 original references at stronghold state 6 while preserving unknown scripts. All 243 player resources are reusable after exact producer, input and file verification. Complete combined-world conversion, native comparison, packaging and shipment remain pending; coverage counts are unchanged.

## v0.0.41 candidate - visibility aprons, 15 October 2026

[CHIM-VISIBILITY-APRON-SCOPE-41](../bugs/CHIM-VISIBILITY-APRON-SCOPE-41.md) - The combined world stopped at Tel Uvirith, original cell (10, 1), because
its approved fixed stronghold snapshot required a source radius of zero.
Regional frames now audit neighbouring cells for separate aprons. The repair
keeps visibility snapshots bound to each original cell across all frames that
audit it. Unknown scripts and unaudited references remain visible. Runtime
quest progression is still deferred; complete conversion and native/package
acceptance remain pending. Coverage counts are unchanged.

## v0.0.41 candidate - window support, 15 October 2026

[CHIM-WINDOW-TOWER-SUPPORT-41](../bugs/CHIM-WINDOW-TOWER-SUPPORT-41.md) - The combined v0.0.41 world build stopped while mounting four Nordic windows
from original cell (7, 22) into the adjacent frame apron. Their supporting
thatched tower was present, but the facade search accepted only model names
containing "house". Exact source triangles support all four windows under the
existing distance and outward-normal checks.

The candidate recognizes the original thatched-tower model in both local and
neighbouring facade searches. It keeps original reference ownership, geometry,
collision, mounting range and clearance. Arbitrary props are still rejected.
The failing build is preserved; complete conversion, native comparison and
fresh package readback remain pending. Coverage counts are not promoted.


15 October 2026, v0.0.41 candidate: 50 focused lava/polygon/terrain checks
and 47 emulator preset/launcher checks pass. Both original failing chunks pass
coverage against the unchanged cached geometry. Full combined-world, exact
source suite, native, package and shipment checks remain pending.

## v0.0.41 candidate - lava coverage, 15 October 2026

[CHIM-LAVA-DUPLICATE-VERTEX-40](../bugs/CHIM-LAVA-DUPLICATE-VERTEX-40.md) - The v0.0.40 combined-world build stopped on two chunks in cell (2, -2).
Readback of the exact cached units found five affected coverage samples:
each has one lava surface and lava contents (-5) at the required depth.
A tiny edge collapses to identical adjacent vertices when the chunk is
translated into float32 frame coordinates. The polygon test mistook this
zero-length edge for a boundary through every sample.

The v0.0.41 candidate skips only exactly identical adjacent XY vertices.
It preserves edge ambiguity, outside rejection and empty/degenerate rejection;
no geometry, collision, pool height, tolerance or engine format is changed.
Full-world validation, native checks, fresh package readback and delivery
remain separate and pending. No coverage count is promoted.

## Compiled apron selection, 15 October 2026

CHIM-FRAME-STATIC-SEAM-40 — The full combined conversion found a conservative
source box overlapping an apron although the compiled rock footprint ends
0.83 game units outside it. The selection now records and excludes only external
references whose compiled pieces all miss that apron. Owned originals, reaching
pieces and missing-piece failures remain protected. The original reference and
compiled boxes remain in the source receipt. All 68 focused checks pass.
The preceding source passed 4,218 tests: 4,212 passed, three Windows checks
skipped and three tracked Census cases were expected failures. The later source
requires its own full suite and combined validation. Native, package and shipment
acceptance remain pending; no converted or accepted coverage count is promoted.

[Canonical report](../bugs/CHIM-FRAME-STATIC-SEAM-40.md).

## Paired boundary validation, 15 October 2026

CHIM-FRAME-STATIC-SEAM-40 — The latest v0.0.40 paired conversion passes structural, heap, zone-walk and
stair validation. The 3,836 tested steps and ramps pass; 610 advisory results
remain recorded. Across 2,816 paired positions, full-static support states agree
and the maximum supported-height difference is 0.000077 game units. Terrain,
water and common standing-hull controls agree. The complete 369-frame successor
is being built from the same converter source; its acceptance remains pending.
The exact source full suite is running. Native gameplay, other boundary segments,
fresh package readback and shipment remain separate unfinished gates.

[Canonical report](../bugs/CHIM-FRAME-STATIC-SEAM-40.md).

The CHIM progress map shows, cell by cell, how far AmiWind's open world has moved from Quake's old way of storing a
map onto CHIM. It appears in the README, in the release notes and in the Toolkit (the World Map's CHIM Progress
Tracker layer). This page explains the work behind it in plain words, then goes through every colour: what it
means, the problems that usually sit behind it, a few examples, what fixes it and who decides. The tracker itself,
its statuses and its commands are described in [CHIM Progress Tracker](PROGRESS_TRACKER.md); the live figures are on
the generated [CHIM cell tracker](CELL_TRACKER.md).

## Owner apron follow-up, 15 October 2026

The source owner check found twelve additional references in the sampled
regional apron: four placements of the fourth kelp mesh, four objects already
deferred by Seyda, and four nonsolid grasses represented by existing sprites.
The successor retains all four original kelp models. Regional aprons now honor
the included town's exact declared deferrals; nonsolid grasses retain the same
hash-verified sprite bytes and original transforms instead of duplicate meshes.
Unrecorded missing owners, changed original identities and corrupt sprite assets
still fail. The existing ownership validator is unchanged. Forty-seven focused
checks pass, including serialized ownership and sprite corruption controls.

The earlier authored-collision source passed 4,213 tests: 4,207 passed, three
Windows-only checks skipped, and three tracked Census expected failures. This
does not certify the later source. Combined conversion, native seams, gameplay,
fresh packaging and delivery remain pending; no coverage acceptance is promoted.

[Canonical report](../bugs/CHIM-FRAME-STATIC-SEAM-40.md).


## Combined-world gate update, 15 October 2026

All 369 frames in the combined candidate passed conversion, structural,
heap, zone-walk and stair validation on 15 October 2026. This establishes a
conversion result for that exact source, not native or packaged acceptance.
The initial comparison measured six of 547 original-cell boundary segments:
five agreed, while southern Seyda between (-2,-12) and (-2,-11) had 477
full-static support disagreements. Later scoped results are recorded below;
the remaining 541 segments are unmeasured.

The regional scenery apron first reduced the southern Seyda comparison from
477 to 69 support-status disagreements. Original reference 463188 had identical
63 rendered faces but 40 collision hit-presence disagreements in 588 rays:
the regional path retained the authored RootCollisionNode while the legacy
Seyda carrier omitted it. A CHIM-only supplement verifies the original NIF and
visual hashes, preserves carrier bytes and appends the original authored hulls.

The corrected Seyda frame now compiles with zero structural failures and passes
heap and zone-walk checks. Compared with the repaired regional frame, the same
boundary has zero full-static support-status disagreements across 2,816 samples
(5,632 queries); terrain and water controls also agree. Its complete stair gate
is unfinished: the parallel run exceeded its memory limit and was stopped by
out-of-memory termination. A passing boundary sample is not a complete stair,
combined-world, native or package pass.

The combined attempt then stopped at ownership validation before packing:
original kelp references, including 463098, were omitted from the Seyda frame.
These references are present in the original source carrier and absent from the
existing flora sprite receipt; a legacy dressing filter removed them. The next
source correction retains only the three known original kelp meshes 01/02/03,
binds additions to the original scenery index and leaves unrelated deferred
dressing unchanged. All 43 focused Seyda, town and ownership checks pass.
Compiled verification of this later correction, native checks and packaging
remain pending. The earlier source's running full suite does not certify it.
[Static seam](../bugs/CHIM-FRAME-STATIC-SEAM-40.md) and
[boundary ownership](../bugs/CHIM-FRAME-DEPENDENCY-OWNERSHIP-40.md).

Earlier failed ownership and source-only checkpoints remain historical evidence;
the successful successor does not transfer acceptance to a later repair.

## What CHIMport is

Morrowind's world is one big outdoor space made of square cells (Vvardenfell has 1,292 land cells, Solstheim 144; with its 98 sea-floor cells and 19 open-sea cells Vvardenfell's
outdoors on CHIM is 1,409 cells, see [what we count](CELL_TRACKER.md#what-we-count)).
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
- **Small pieces, streamed.** Regional frames own one original cell; town frames own their configured cell group. Both use chunks of 256 units and small sector
  files that a classic Amiga disk reads whole; the engine streams them around the player ([CHIM](README.md),
  [world format](WORLD_FORMAT.md)).
- **Shared terrain.** Terrain is stored once as compiled pieces, and the open sea around the island is a single
  shared ocean piece.
- **Its own map file.** A CHIM map is a `.chim` file, no longer a Quake `.bsp`, and the plan is to leave BSP29's
  limits behind step by step; interiors stay ordinary Quake `.bsp` maps until they move too
  ([the .chim map format](CHIM_MAP_FORMAT.md)).
- **Wide coordinates**, so one frame can cover a whole city.

## Reading the map

The current README map uses the public reference generated **15 October 2026, 10:50 UTC**. The [cell tracker](CELL_TRACKER.md) records the matching audit
totals and a separate package ledger. These figures describe Vvardenfell only.

Update, 19 October 2026: the table below is that 15 October snapshot and is kept as it was. Since v0.0.43 every
exterior cell of Vvardenfell is on CHIM; the current counts (1,390 cells with a LAND record, all audit-done, and
1,409 cells on CHIM) are on the [cell tracker](CELL_TRACKER.md) and explained in
[what we count](CELL_TRACKER.md#what-we-count).

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

The Toolkit marks **769 cells** here: 11 cell-complete-but-unlit and 758
terrain-complete-but-unlit. The README's compact map groups them in green.
Across the 1,292-cell tracker denominator, lighting is partial in 135 cells,
unlit in 1,056 and not measured in 101. No cell is recorded fully lit.

### Passed, something still deferred (plain green)

There are **407** cells in this state. Inspect the cell's deferred reference
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

## Maintainer marks: approved, playtested, accepted

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
Maintainer acceptance remains separate.

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
historical, scoped evidence. Shipment does not establish maintainer acceptance
or close the renewed [third-person punch](../bugs/PLAYER-PUNCH-THIRDPERSON-39.md),
[readied movement](../bugs/PLAYER-READY-MOVEMENT-39.md),
[blocking](../bugs/COMBAT-BLOCKING-36.md) or
[swimming](../bugs/WATER-GAMEPLAY-PARITY-38.md) reports.
Independent fresh-download verification remains separate.

Conversion/audit data is the 15 October 2026, 10:50 UTC snapshot:
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
