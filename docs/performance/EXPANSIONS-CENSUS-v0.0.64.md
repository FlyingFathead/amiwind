# Expansions census: Tribunal and Bloodmoon, measured

_Last updated with AmiWind v0.0.64-dev4 (11 November 2026)._

<!-- contents start -->
## Contents

- [What was measured and how](#what-was-measured-and-how)
- [The census](#the-census)
- [What the census says about the plan](#what-the-census-says-about-the-plan)
- [The legacy map estimate per expansion](#the-legacy-map-estimate-per-expansion)
- [Build stage times of the v0.0.63 line](#build-stage-times-of-the-v0063-line)
- [Scaling to the expansions](#scaling-to-the-expansions)

<!-- contents end -->

The two expansions are planned as optional layers of the world (Mournhold from Tribunal, Solstheim from
Bloodmoon). This page replaces the estimated column of the plan with counts read from the game's own files, so the
budget of each layer starts from measured numbers. Nothing here changes a build's output.

## What was measured and how

| Item | Value |
| --- | --- |
| Source | the maintainer's Morrowind data (GOTY installation): Morrowind.esm, Tribunal.esm, Bloodmoon.esm and their archives |
| Morrowind.esm SHA-256 | 5c3c8c2cbd20e25901b59b3ece33d36b7ef0e3d60ad8d11828bcc61a5ead1647 |
| Tribunal.esm SHA-256 | 2ace511f23cc2a9ddd5f3aa59c7919789b9378cf4b17c8ae3375dd6b782f3f2b |
| Bloodmoon.esm SHA-256 | bd27090d0e6ad4c1bf1abc83f1a2dac56fcc82cae7bfe8263c413fb301801357 |
| Builder source | v0.0.63 as published (commit e6e56524) plus `tools/expansions_census.py` and its test, both read-only on the data |
| Census command | `python3 tools/expansions_census.py --data-files <Data Files> --out <dir>` in the builder container |
| Estimate command | `python3 tools/build_aga.py estimate --data-files <Data Files> --out <dir> --jobs 8` in the builder container (460 s: 448 s of it the scan of 4,768 meshes) |
| Stage times | the Toolkit monitor history of the v0.0.63 runs named below (commit and run name given per row) |
| Date | 10 November 2026 |

Definitions used below. A cell's placements are its references that are not marked deleted. "Median" and
"maximum" run over the cells that hold at least one placement. A land cell is an exterior cell with a LAND record
in the expansion or in Morrowind.esm at the same grid position; a sea cell has none. A "new" exterior cell is one
whose grid position Morrowind.esm does not have. The master index is the top byte of a reference number: 0 is
a placement new in this file, k greater than 0 edits a placement of the file's k-th master (the decoding of
`tools/mwscript/gamedata.py`).

## The census

| | Mournhold (Tribunal.esm) | Solstheim (Bloodmoon.esm) |
| --- | --- | --- |
| Cells (not deleted) | 121 | 276 |
| Exterior cells | 18 | 173 |
| Exterior land cells (a LAND record) | 4 | 148 |
| Exterior sea cells (no LAND record) | 14 | 25 |
| LAND records in the master itself | 0 | 144 |
| Exterior cells not in Morrowind.esm (new ground): land / sea | 0 / 0 | 144 / 11 |
| Exterior cell box (x min, x max, y min, y max) | -16, 4, -14, 8 | -29, -2, -8, 28 |
| Placements per new exterior cell, maximum | 0 | 579 |
| Placements per new exterior cell, median | 0 | 120 |
| Placements in new exterior cells, total | 0 | 13,628 |
| Placements per exterior cell (all 18 / 173), maximum | 1 | 579 |
| Placements per exterior cell (all 18 / 173), median | 1 | 119 |
| Placements in exterior cells, total | 1 | 13,630 |
| Interior cells | 103 | 103 |
| Interior cells with at least one placement | 98 | 98 |
| Placements per interior cell, maximum | 393 | 434 |
| Placements per interior cell, median | 159 | 126 |
| Placements in interior cells, total | 15,102 | 12,843 |
| Interior cells that behave like an exterior (cell flag 0x80) | 5 | 0 |
| Models the placements use (distinct) | 1,308 | 1,200 |
| Files in the expansion's own archive | 1,174 | 1,545 |
| Models used that the expansion's archive holds and Morrowind.bsa does not | 555 | 823 |
| ... of those, also not a loose mesh in the data folder | 0 | 0 |
| Models used that no archive and no loose file holds | 2 | 3 |
| Cells that also exist in Morrowind.esm (exterior / interior) | 18 / 7 | 18 / 5 |
| ... of those, cells that receive placements of the expansion | 4 | 4 |
| References with a master index above 0 (edits of a base placement) | 0 | 0 |
| Moved references (MVRF) | 0 | 0 |

The data folder carries loose copies of every expansion mesh the placements use, so the count of models found only
in an archive is 0 here; a data folder without those loose files needs the 555 and 823 models from the expansion
archives (the row above it).

### Mournhold: the districts that act like an exterior

Mournhold has no real exterior: its 18 exterior cells are cells of the base game that Tribunal.esm touches, and
they hold one new placement in all (in Ebonheart). The city is interior cells. Five of them carry the
exterior-behaviour flag:

| Cell | Placements |
| --- | --- |
| Mournhold, Great Bazaar | 315 |
| Mournhold, Temple Courtyard | 302 |
| Mournhold, Godsreach | 282 |
| Mournhold, Plaza Brindisi Dorom | 187 |
| Mournhold, Royal Palace: Courtyard | 126 |

### The base-game cells each master touches

Neither master edits an existing base-game placement: no reference in either file has a master index above 0, and
neither file moves a reference. What they do to the base game is add placements, in four cells each:

| Cell | Kind | New placements |
| --- | --- | --- |
| Tribunal: Ebonheart (1,-13) | exterior | 1 |
| Tribunal: Ebonheart, Grand Council Chambers | interior | 1 |
| Tribunal: Bthuand | interior | 1 |
| Tribunal: Dagoth Ur, Facility Cavern | interior | 1 |
| Bloodmoon: Khuul (-9,17) | exterior | 1 |
| Bloodmoon: Ald-ruhn (-2,6) | exterior | 1 |
| Bloodmoon: ToddTest | interior | 3 |
| Bloodmoon: Dagoth Ur, Facility Cavern | interior | 1 |

The other base cells in the table above (17 exterior and 4 interior for Tribunal, 16 exterior and 3 interior for
Bloodmoon) carry the expansion's version of the cell record and no placements of their own.
Bloodmoon.esm lists one master, Morrowind.esm, in this installation.

### Solstheim: tree references by model

Exterior cells only; model file names that contain "tree", "spruce" or "pine". The model names do not say which
are the spruces.

| Model | Placements | Cells |
| --- | --- | --- |
| flora_tree_bm_snow_01 | 403 | 54 |
| flora_tree_bm_01 | 307 | 38 |
| flora_tree_bm_07 | 295 | 38 |
| flora_tree_bm_snow_07 | 287 | 57 |
| flora_tree_bm_03 | 280 | 37 |
| flora_tree_bm_snow_05 | 260 | 50 |
| flora_tree_bm_02 | 254 | 38 |
| flora_tree_bm_snow_03 | 245 | 52 |
| flora_tree_bm_snow_06 | 243 | 53 |
| flora_tree_bm_snow_04 | 235 | 53 |
| flora_tree_bm_06 | 203 | 38 |
| flora_tree_bm_05 | 200 | 40 |
| flora_tree_bm_snow_02 | 194 | 54 |
| flora_tree_bm_04 | 185 | 37 |
| Stumps, branches and five single tree actors (14 models) | 84 | 1 to 9 each |

Total: 3,675 tree placements in 74 exterior cells (per cell: maximum 96, median 57.5). The seven plain and the
seven snow-covered tree models carry 1,724 and 1,867 of them. The most placed models of Solstheim overall are the
ice layer (948), a rock (529) and then the snow tree (403).

### The sea around and between the islands

Counted on the same data (11 November 2026), cell by cell:

| | Cells |
| --- | --- |
| Bloodmoon.esm exterior cells | 173: 18 that Morrowind.esm also has, 155 new |
| New cells with land (heights) | 144 (the tracker's land count) |
| New cells with a land record without heights (seabed) | 6 |
| New cells without a land record (open water) | 5 |
| Solstheim's extent | cells x -29 to -16, y 14 to 28 |
| Cells next to Solstheim's land that are land in neither file | 59: 4 water cells of Bloodmoon.esm, 55 without a cell record |
| Between the islands (the rectangle x -29 to -8, y 6 to 28, 506 cells) | 137 cells of Morrowind.esm, 160 of Bloodmoon.esm, 214 in neither file |

A cell no file defines is still open sea in the original game: OpenMW creates such a cell when it is first needed,
as an empty exterior cell with water and no land (apps/openmw/mwworld/worldmodel.cpp, `createExteriorCell`). So
the sea around Solstheim and between the two islands has no edge where the data ends. Vvardenfell on CHIM is its
1,404 recorded cells plus 5 open-sea cells; following that model, Solstheim's recorded sea is its 6 seabed and 5
water cells, and the open sea the player can swim or sail across (up to the 214 recordless cells of the strait and
the 55 around the island) has to be generated (CHIM-SEA-BETWEEN-ISLANDS-64).

## What the census says about the plan

| Plan figure (ESTIMATE) | Measured |
| --- | --- |
| Mournhold: no real exterior, 7 to 9 districts that act like an exterior | 18 exterior cells that all belong to the base game and hold 1 new placement; 5 interior cells with the exterior flag (126 to 315 placements each) |
| Mournhold: about 95 rooms | 103 interior cells, 98 of them with placements (the legacy estimate maps 92 of them, below) |
| Solstheim: about 160 to 190 land cells | 148 land cells and 25 sea cells in a box of 173 exterior cells; 144 of the land cells and 11 of the sea cells are new ground (the other 18 cells of the box are base-game cells) |
| Solstheim: about 120 to 150 rooms | 103 interior cells, 98 with placements |
| Solstheim: about 20 to 25 frames of 3x3 cells | 20 frames on the estimator's grid, sea-only frames skipped |
| Base cells each expansion edits: "a few" | 4 cells each, one placement each (three in ToddTest); no edit of a base placement, no moved reference |

Placements per cell: the median Solstheim exterior cell holds 120 placements and the densest 579; the five Mournhold
districts hold 126 to 315 each, and the median Mournhold interior cell 159.

## The legacy map estimate per expansion

`build_aga.py estimate` models the old per-map conversion (one BSP map per interior, exterior regions on a 3x3-cell
frame grid), not the CHIM records that the world now uses. Its numbers are kept here because they are the only
measured per-place sizes of the two expansions, and they name the places that are heavy; they are not CHIM limits.
Scenario "cur" = what the converters take today; "evr" = every placed reference with a mesh as geometry and actors
as edicts. Limits in the estimate: 600 edicts, 32,767 texinfo, 65,535 faces, a map heap of 11,534,336 bytes.

| | Tribunal | Bloodmoon |
| --- | --- | --- |
| Maps estimated | 92 (92 interiors) | 1,004 (93 interiors, 911 exterior regions on 20 frames) |
| Maps passing every limit, "cur" / "evr" | 63 / 59 | 855 / 851 |
| Maps failing at least one limit, "cur" / "evr" | 29 / 33 | 149 / 153 |
| Maps within 10 % of a limit, "cur" | 13 | 82 |
| Failing interior maps / failing exterior maps, "cur" | 29 / 0 | 36 / 113 |
| Heap failures (interior / exterior), "cur" | 26 / 0, worst 1.83 of the budget | 29 / 95, worst 1.73 |
| Texinfo failures (interior / exterior), "cur" | 9 / 0, worst 1.61 | 11 / 71, worst 2.09 |
| Edict failures (interior / exterior), "cur" | 0 / 0 | 0 / 9, worst 1.62 of 600 |
| Estimated final BSP bytes, all maps, "cur" | 306,181,875 | 3,008,120,544 |

Interiors the estimate leaves out are those that no door chain or script reaches (for Mournhold, "mournhold
temple" and "mournhold, royal palace" are among them), which is why its interior counts are below the census.
The heaviest places are Mournhold, Temple Courtyard (heap 21,116,886 bytes, 137,882 faces, 52,953 texinfo in "evr")
and the densest Solstheim forest region at exterior cell (-27,25), regions 53 and 54 (heap about 19.5 and 19.9 million
bytes, texinfo 66,577 and 68,508).

## Build stage times of the v0.0.63 line

Seconds of wall time per stage, from the Toolkit monitor history. The release build and the fifth development build
reused the world stages; their rows show what the reuse check of each stage costs. The next rows are the most recent
builds that computed the stage.

| Run (commit) | chim | chim-room-batches | chim-interiors | Build total |
| --- | --- | --- | --- | --- |
| v0.0.63 release build, `2026_11_09_v0.0.63_full-v0.0.63-release_84bc6f5` (84bc6f5): all three reused | 76.5 | 26.5 | 1.5 | 728 |
| v0.0.63-dev5, `2026_11_09_v0.0.63-dev5_full-v0.0.63-dev5_5a4c472` (5a4c472): all three reused | 78.2 | 28.9 | 1.7 | 790 |
| v0.0.63-dev4 try 2, `2026_11_09_v0.0.63-dev4_full-v0.0.63-dev4-try2_82548f7` (82548f7): computed | 1,302.0 | 118.4 | 73.7 | 2,483 |
| v0.0.63-dev3 try 2, `2026_11_09_v0.0.63-dev3_full-v0.0.63-dev3-try2_6e68096` (6e68096): chim and interiors computed, room batches reused | 1,293.6 | 29.2 | 53.7 | 1,985 |
| v0.0.63-dev1, `2026_11_09_v0.0.63-dev1_full-v0.0.63-dev1_dc356e3` (dc356e3): computed | 1,713.6 | 91.4 | 176.5 | 7,545 |
| v0.0.62, `2026_11_08_v0.0.62_full-v0.0.62_fe90f8e` (fe90f8e): all three computed; the room batches with no history (every room again) | 1,050.1 | 9,925.0 | 132.2 | 21,436 |

The image step of the release build took 588 s and of the dev5 build 638 s.

## Scaling to the expansions

Scaled by the count of what a stage loops over. These are projections from the measured rows above, not
measurements; the first from-scratch build of each layer replaces them.

| Stage | Measured per unit | Mournhold (103 rooms, no exterior) | Solstheim (173 exterior cells, 103 rooms) |
| --- | --- | --- | --- |
| chim (1,404 land and 5 sea cells = 1,409 cells; 1,302 s in dev4, 1,050 to 1,714 s over the runs above) | 0.74 to 1.22 s per cell, with the stage's jobs | none | 128 to 210 s (173 cells), more if the dense forests cost more per cell than Vvardenfell |
| chim-room-batches (1,134 rooms; 9,925 s when every room is built again) | 8.75 s per room | 900 s (103 rooms), the five districts and Clockwork City above the mean | 900 s |
| chim-interiors (1,134 rooms; 53.7 to 176.5 s) | 0.05 to 0.16 s per room | 5 to 16 s | 5 to 16 s |

The plan's earlier build-time estimates (0.5 to 1 hour for Mournhold, 1.5 to 2.5 hours for Solstheim) are about
two to eight times above what these scalings give. The scalings leave out new meshes (555 and 823 models that the
base build does not have), the actors, and the dense-forest frames, which the first measured build of each layer
decides.
