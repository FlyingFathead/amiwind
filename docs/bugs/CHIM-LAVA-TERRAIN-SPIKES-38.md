# CHIM-LAVA-TERRAIN-SPIKES-38: Angular terrain over a lava pool

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | audit |
| First noticed | 13 October 2026, in v0.0.38 |
| Where | Exterior (9,2), vf1703.chim, source XY (81472,21952) |
| Reproduction | once |
| Duplicate of | no |
| Persists in | v0.0.38 (last seen) |
| Severity | high: Visible terrain discrepancy in the release focus area requires diagnosis before visual acceptance. |
| Family | Content silently missing from a build (`build-content-missing`) |
| CHIM | Builder ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | v0.0.38 full image candidate |
| From commit | source c2c2050, engine c2c2050, CHIM world c2c2050 |
| CHIM engine version | CHIM 0.2.0, engine c2c2050, world format 0.7 |
| Platform or emulator | FS-UAE 3.1.66, A1200 68040 preset |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.42-dev1 (17 October 2026)._

<!-- contents start -->
## Contents

- [Symptom](#symptom)
- [Where](#where)
- [How it happened](#how-it-happened)
- [Why it was not caught](#why-it-was-not-caught)
- [Reproduction](#reproduction)
- [Repair](#repair)
- [Verification](#verification)
- [Prevention](#prevention)
- [Candidate investigation, 13 October 2026](#candidate-investigation-13-october-2026)
- [Bugs in the same category](#bugs-in-the-same-category)

<!-- contents end -->

## Symptom

The final-image inspection in exterior cell (9,2), vf1703.chim, shows thin
angular terrain wedges crossing the lava view at source XY (81472,21952).
The original-game comparison shows a continuous rock/terrain slope in this
view. This establishes a visual discrepancy, not yet its exact mesh or cause.

## Where

v0.0.38 candidate, source c2c2050. Native local actor (912,368,190), eye height
14, yaw225, pitch25. Original measured eye (81468.8,21948.8,816.016), yaw225,
pitch25 degrees, vertical FOV40.0516 degrees. Native/source XY residual is
about3.2 units per axis. Original ash weather and lighting remain unmatched.

## How it happened

CHIM retained coarse LAND beneath lava pools and emitted flat lava faces over
the whole underlying polygon, including ground above the liquid level. The
candidate investigation below separates the sampling and face-clipping defects.

## Why it was not caught

Format, memory and file-readback gates establish valid packaged data but do
not certify original visual fidelity at every location. Earlier lava contact
checks verified damage at this pool, not the raised-camera terrain silhouette.

## Reproduction

Load the full candidate, reach cell (9,2), use diagnostic noclip to position
the camera as above, then inspect southwest/downward over the pool. This
camera inspection does not establish ordinary walking or traversal behavior.

## Repair

The candidate reuses the legacy LAND triangulator for lava-footprint detail
and the existing terrain polygon clipper for the ground/liquid intersection.
AmiQuake liquid contents and damage machinery remain unchanged. Scoped native
visual and contact checks pass; combined-world validation and final image
integration remain pending.

## Verification

Original native and reference screenshots, camera logs and hashes are retained
as private evidence. Native lava contact independently reports contents-5 and
health loss with noclip and god mode disabled. That result does not close this
visual issue. No fixed or shipped claim.

## Prevention

Retain this repeatable pose in lava visual regression checks alongside contact,
source-reference coverage, memory and packaged-file gates.


## Candidate investigation, 13 October 2026

The affected frame records a 128-unit terrain grid and no refined tiles.
The CHIM ground preparation calls only shoreline refinement; it does not pass
lava footprints to the existing legacy detail triangulator. An offline check
in the inspected footprint finds coarse heights differing from original LAND
samples by up to 84 compiled units. This is a concrete sampling defect;
identification of every visible wedge remains pending.

The candidate reuses `prepare_world_regions.terrain_triangles` with full detail
inside lava-footprint tiles and required intermediate samples on adjoining
coarse edges. Eleven stitching tests pass, including depression preservation,
matching boundary vertices, shoreline-off lava detail and unchanged no-pool
triangles. The affected frame grows from 1,800 to 5,454 ground triangles;
194 tiles are refined. This cost must pass chunk and active-ring budgets before
integration. Whole-footprint maximum error remains 62.5 units outside the refined
area; do not interpret local lava refinement as universal original-detail terrain.
The scoped cell (9,2) rebuild passes format validation, the active-ring gate
(6,068,880 of 6,242,304 bytes), and 493 walked stair/ramp checks. Its load-ring
peak is 7,461,408 bytes; 206 positions exceed the full-load budget. The streaming
walk completes with six loads without room and five partial activations. These
limits require native inspection and must not be reported as full-load clearance.
All 1,987 original 32-unit LAND samples in the lava-detail tiles, including
boundaries, match exactly. A diagnostic FS-UAE run of the repaired cell removes
the large spikes at the inspected pose, but smaller angular shoreline artifacts
remain. The frame-world allocator reports only the nearest 15 of 33 chunks
resident, with a 768 KiB block and a request for 1,841 KiB. Thus this is a partial
candidate improvement, not an accepted repair or release integration. Resolve
the remaining visible discrepancy and residency cost before replacing the
release image. The matched original reference still has different weather and
lighting; it does not establish lighting parity.

Further inspection found a second defect in `chim.terrain.lava_over`: unlike
sea-water faces, lava faces were flattened across a ground polygon's entire
footprint, including the part above the lava level. The parent BSP plane clips
contents but does not clip those face edges. The candidate clips each lava
face to the ground-plane intersection before emitting its two sides, retaining
the existing liquid contents tree. A sloping-ground regression requires every
emitted lava vertex to lie above or on the ground and the edge to reach the
analytic intersection. All 38 lava tests pass. At the same native comparison
pose, this additional repair removes the remaining triangular teeth and leaves
a continuous shoreline. This is one inspected diagnostic cell, not full-world
acceptance. Combined-world budget validation, contact revalidation and final
image integration are still pending. Subsequent scoped contact verification with
god mode and noclip off records water level 1, lava contents -5, and health
falling from 100 to 76.8, 64.7 and 52.6. This confirms damage still occurs after
the geometry change; it does not establish exact damage-rate or route parity.

Final full-image verification, 13 October 2026: all 349 original lava references across 27 cells survive conversion and final HDF readback matches the rebuilt CHIM world. Scoped native views show a continuous shoreline with HUD and crosshair off. Contact with god mode and noclip off records health 100 -> 76.9 -> 64.8 -> 52.8, water level 1 and lava contents -5. This supersedes pending integration notes; sound, wider traversal and maintainer acceptance remain open.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Content silently missing from a build (`build-content-missing`). Every omission is receipted; payload and entity counts are compared with the last release; shipped features are on by default. See [families](README.md#families).

- [ARENA-PIT-NO-INTERIOR-33](ARENA-PIT-NO-INTERIOR-33.md): The Vivec Arena minigame fights on the test floor: the Arena Pit interior is not in v0.0.33 builds
- [AUDIO-MISSING-SOURCES-32](AUDIO-MISSING-SOURCES-32.md): The image step reports missing sources for 7 voices and 2 effects
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
- [CHIM-NATIVE-IMAGE-NO-SHARED-SKY-36](CHIM-NATIVE-IMAGE-NO-SHARED-SKY-36.md): CHIM-native images with no legacy exterior (MiniWinds of one town) ship without the shared sky their frame maps name
- [CHIM-TRACKER-APRON-40](CHIM-TRACKER-APRON-40.md): Tracker counts town apron dependencies as complete original cells
- [INTERIOR-PLACED-ITEMS-47](INTERIOR-PLACED-ITEMS-47.md): Takeable and movable items and containers in converted interiors are not live objects (placed items are left out)
- [LAVA-NOT-IMPLEMENTED-33](LAVA-NOT-IMPLEMENTED-33.md): Lava is drawn as plain static meshes: no liquid surface, no damage, no view tint, never tracked
- [MINIWIND-PAYLOAD-NOT-SLIM-33](MINIWIND-PAYLOAD-NOT-SLIM-33.md): MiniWind #2 was built with the full movie and voice payload
- [NIGHT-WINDOWS-LOST-CHIM-36](NIGHT-WINDOWS-LOST-CHIM-36.md): Windows no longer glow at night: the night-windows table has been empty since the towns moved to CHIM
- [PLAYTEST-PAYLOAD-COVERAGE-32](PLAYTEST-PAYLOAD-COVERAGE-32.md): The v0.0.32-dev1 playtest has no first-person hands and no harvest
- [SEYDA-LANTERNS-MISSING-31](SEYDA-LANTERNS-MISSING-31.md): Seyda Neen lanterns light the night but are not in its maps
- [SKY-FLAT-PALETTE-DRIFT-41](SKY-FLAT-PALETTE-DRIFT-41.md): Exterior sky flat with no clouds: the sampled palette drifted and the shared cloud sky silently fell back to a one-colour placeholder
- TREE-SCALE-001 (no report page): Non-unit-scale tree sprites omitted; bounds too conservative

<!-- END GENERATED CATEGORY -->
