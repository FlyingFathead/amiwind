# BUILD-LAVA-COVERAGE-38: Full dev2 world omits the reported lava cells

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | owner |
| First noticed | 12 October 2026, in v0.0.38-dev2 |
| Where | Full dev2 exterior world |
| Reproduction | unknown |
| Duplicate of | no |
| Persists in | v0.0.38-dev2 (last seen) |
| Severity | high: Full world omits visible lava and its gameplay in reported cells. |
| Family | Content silently missing from a build (`build-content-missing`) |
| Playtest version | v0.0.38-dev2 |
| From commit | source c2eaa5a, engine c2eaa5a, CHIM world c2eaa5a |
| CHIM engine version | CHIM unknown, engine c2eaa5a, world format unknown |
| Unknown because | CHIM version and format not yet transcribed into this report; exact dev2 receipt preserved. |
| Platform or emulator | unknown (Owner screenshot identifies dev2 but not the emulator.) |

<!-- END GENERATED FACTS -->

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
- [Legacy path source diagnosis, 12 October 2026](#legacy-path-source-diagnosis-12-october-2026)
- [Native diagnostic, 12 October 2026](#native-diagnostic-12-october-2026)
- [Height verification requirement, 12 October 2026](#height-verification-requirement-12-october-2026)
- [Partial height audit, 12 October 2026](#partial-height-audit-12-october-2026)
- [Terrain cause isolated, 12 October 2026](#terrain-cause-isolated-12-october-2026)
- [Local terrain-detail candidate, 12 October 2026](#local-terrain-detail-candidate-12-october-2026)
- [Owner evidence reconciliation, 13 October 2026](#owner-evidence-reconciliation-13-october-2026)
- [Bugs in the same category](#bugs-in-the-same-category)

<!-- contents end -->

## Symptom

The owner reports missing lava in v0.0.38-dev2 at cell 9,2 (global
77347,17749,490) and cell 10,2 (global 81952,21390,323). The first screenshot
shows terrain without lava; the second shows the map lava layer. These are
reported positions, not yet independently reproduced camera poses.

## Where

Exterior world coverage and full release builder.

## How it happened

The exact full dev2 CHIM receipt records mode quake but zero lava pools.
Its source frame list contains neither reported cell. The builder default is
already lava=quake; enabling a converter does not include omitted cells.
The release-coast2 selection covers coast rings and named towns. The complete
runtime fallback path at the reported locations still needs inspection.

## Why it was not caught

Diagnostic lava acceptance was not reconciled with full-build spatial
coverage. A passing baseline smoke and default-on option cannot prove that the
delivered world contains the demonstrated feature.

## Reproduction

Repeat the owner scenario above in the delivered development build. Native reproduction remains pending.

## Repair

Extend full-build coverage through the established cell pipeline, with
all original lava references accounted for and explicit held/failed cells.
Add a package gate comparing expected pools/cells against actual world payload.
Verify visible surfaces and normal contact damage at the reported poses against
OpenMW. Do not close this as the older map-outline correction.

## Verification

Open, needs fixing. No repaired full package or native acceptance.

## Prevention

Add a regression that checks the delivered gameplay path and retains original-reference evidence.


## Legacy path source diagnosis, 12 October 2026

The reported cells have offline CHIM conversions but are not CHIM frames in dev2.
The legacy world builder also lacks a lava path: prepare_world_regions.map_text
emits ground, water and sky, and terrain_wad supplies no lava texture. The separate
world_scenery inventory selects static rocks and giant mushrooms, not lava activators.
Lava must work in both legacy and CHIM cells; expanding CHIM selection alone is
not a repair for the legacy omission. The shared lava.exterior_pools and map_parts
helpers provide the existing Quake liquid/bed conversion to reuse. Integration
must account for map coverage clipping, vertical bounds, textures, sound payload,
per-reference receipts and cache invalidation. No implementation is claimed yet.


## Native diagnostic, 12 October 2026

The candidate legacy BSP displays lava on the target engine in a 26-second
noclip capture run. An earlier spawn run reported death from lava contact.
This establishes visible native lava and a reached damage path only: the map
omits scenery, is outside the normal exterior routing, and the original OpenMW
camera height differs. Controlled contact/damage, matched scene comparison,
both world formats, full package coverage and release validation remain pending.


## Height verification requirement, 12 October 2026

The owner explicitly asks whether lava is at the correct height relative to the
topomap. End-to-end verification remains pending. Compare original transformed
mesh surface Z, converted BSP/CHIM surface Z, terrain/topomap coordinate and
elevation data, and runtime contact height at the same references. Shared
converter code and visible lava alone do not prove this. Preserve map origins
and distinguish surface elevation from liquid depth and bed thickness.


## Partial height audit, 12 October 2026

One diagnostic legacy region contains 16 clipped pool references. Re-reading
the original owned source through the pinned converter gives identical recorded
pool heights for all 16. Upward compiled lava surfaces occur at source-world
Z 384, 416, 480, 512 and 768. Two source pools at about Z 352 have no upward
compiled surface at that level; they supplied no exposed-terrain audit samples.
This is not evidence that those two pools should be visible.

At 208 spatial samples inside the clipped pool footprints where original LAND
is at least 8 units below the pool top, 161 show empty contents just above and
lava just below the expected surface. Forty-seven do not: 44 show solid on
both sides, and three show empty above/solid below. These are SUSPECT GEOMETRY
flags, not accepted visual defects. Coarse converted terrain is a hypothesis;
source terrain, compiled geometry and overlap ownership need reconciliation.
The 2D topomap lava layer clips outlines using original LAND and source pool
height; it does not encode a separate vertical surface. Exact packaged topomap
bytes, CHIM heights and native contact elevations remain unverified here.

Reference 396190, sample world XY 76160,18304, illustrates a pending capture:
original bilinear LAND Z 136, pool Z approximately 480, compiled contents solid
at one unit above and below the expected top. All other flagged samples remain
pending individual or shared-view capture coverage. Diagnostic noclip cannot
establish normal collision acceptance.


## Terrain cause isolated, 12 October 2026

Evaluating the exact pinned generated terrain triangles at all 47 flagged XY
positions explains every solid-contents result: the simplified terrain reaches
or exceeds the pool surface. Generated terrain is 16 to 516 source units higher
than original LAND at those samples. At XY 76160,18304, original LAND is Z136,
the source lava top is approximately Z480 and generated terrain is Z544.
Thus preserving the lava tile elevation alone does not preserve visible lava.

The current refinement preserves land/water identity around sea level (Z0),
but does not protect land/lava identity at each local lava elevation. A candidate
should reuse that bounded terrain refinement around affected pool footprints,
with deterministic shared-edge sampling across map aprons. Preserve source lava
height; do not lift pools to hide terrain errors. Check positive and negative
relief, original submerged and exposed areas, shared seams and unchanged remote
terrain. Then measure BSP/clipnode growth, compilation, heap and native cost.
No repair or full-height acceptance is established by this diagnosis.


## Local terrain-detail candidate, 12 October 2026

The unshipped candidate retains original LAND sample detail in terrain tiles
overlapping lava-pool bounds. Adjacent coarse tiles insert matching original
edge samples; distant terrain keeps the existing triangulation. Lava elevations
are unchanged. Forty-nine focused tests pass, including the elevated depression,
shared edges, shifted overlapping maps and unchanged distant terrain.

The same diagnostic region now passes all 208 exposed-pool height/contents
samples and 467 buried-pool solid controls. The target engine completes a
23-second noclip capture on the baseline setup. This is scoped evidence, not
full-world or normal-collision acceptance. Faces increase from 2,008 to 5,686,
clipnodes from 2,395 to 6,732 and BSP bytes from 378,340 to 1,332,928.
First-presented low-hunk usage increases from 2,898,720 to 4,103,776 bytes;
high scratch is 54,288 bytes in both runs. Full scenery, native frame-cost,
controlled contact/damage, matched OpenMW and complete package gates remain.


### Native contact follow-up, 2026-10-12

The corrected diagnostic map survived a 24-second reference-aligned camera run
and a separate 29-second contact run. Lava is visible in both reference and
native views, but scenery and exterior lighting are not represented by this
probe. At one original exposed pool, disabling noclip for approximately one
second reduced health from 78.0 to 58.7; the readback reports lava contents
and water level 1. Noclip was restored after contact. This proves local lava
damage, not exact damage rate, boundary elevation, ordinary approach, full
scene parity or complete package acceptance. The earlier truncated contact
log is preserved; the follow-up retained both complete health readbacks.


### Cache control, 2026-10-12

A pinned single-map cold conversion recorded one cache miss; a second run
with a fresh scene recorded one verified cache hit. Both produced identical
BSP and converted lava WAV hashes. This checks per-map reuse and regeneration
of the sound payload, not whole-stage restore or final image sound presence.


The production stage recorder and restore routine also captured and restored
eight files from an isolated single-map conversion, including the BSP and lava
WAV with exact hashes. This used an explicit diagnostic reuse plan; the complete
pipeline fingerprint selection and final image remain separate gates.

Scenery enrichment retains 113 placements across 59 models and passes a
23-second native capture. Low-hunk use is 4,711,648 bytes with a 6,767,680-byte
peak gap on the baseline diagnostic heap. Lava and nearby scenery are visible.
This remains a standalone map without normal exterior routing; flora, actors,
original steam, audio and frame-cost acceptance are incomplete.


## Owner evidence reconciliation, 13 October 2026

The following owner screenshot evidence was visually reviewed. Original images
remain in the private evidence archive; identifiers bind this report to those
originals. This records reported symptoms and comparison controls, not a repair
or runtime acceptance. Missing build or pose information remains unknown.

- `OWNER-20261012-145808`: SHA-256 `5475b5639b4a1edd47d0be00ecf5282ca80f6c64551d6af751c4fe523590d4fa`. Screenshot association checked; no repair or behavioral acceptance inferred.
- `OWNER-20261012-150043`: SHA-256 `3cd6dfee82435509b6c563fdfe8f354469f3d8011f4dbac457f25d8bd1c9f47b`. Screenshot association checked; no repair or behavioral acceptance inferred.


### Final-image verification, 13 October 2026

Candidate full image includes all27 original lava-bearing CHIM regions and349 references; final HDF regional readback passes. Native vf1703 contact with noclip/god off reports lava contents and health100 to52.6. Original comparison shows lava; steam, terrain-detail and lighting differences remain. Final package delivery, sound and complete parity remain pending.


A subsequent final-image inspection at source XY (81472,21952), looking
southwest and down, flags angular foreground terrain crossing the lava view.
This is suspect geometry, not yet a confirmed regression; an original-game
comparison is pending. The original native capture is retained as private
evidence. It is not selected as release artwork or treated as visual acceptance.

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
- [LAVA-NOT-IMPLEMENTED-33](LAVA-NOT-IMPLEMENTED-33.md): Lava is drawn as plain static meshes: no liquid surface, no damage, no view tint, never tracked
- [MINIWIND-PAYLOAD-NOT-SLIM-33](MINIWIND-PAYLOAD-NOT-SLIM-33.md): MiniWind #2 was built with the full movie and voice payload
- [PLAYTEST-PAYLOAD-COVERAGE-32](PLAYTEST-PAYLOAD-COVERAGE-32.md): The v0.0.32-dev1 playtest has no first-person hands and no harvest
- [SEYDA-LANTERNS-MISSING-31](SEYDA-LANTERNS-MISSING-31.md): Seyda Neen lanterns light the night but are not in its maps
- TREE-SCALE-001 (no report page): Non-unit-scale tree sprites omitted; bounds too conservative

Related bugs in other categories:

- [BUILD-DIAGNOSTIC-PALETTE-38](BUILD-DIAGNOSTIC-PALETTE-38.md): Lava diagnostic mixes conversion and runtime palettes
- [BUILD-LAVA-TERRAIN-BUDGET-38](BUILD-LAVA-TERRAIN-BUDGET-38.md): Detailed lava terrain exceeds region storage budget

<!-- END GENERATED CATEGORY -->
