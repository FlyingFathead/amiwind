# CHIM-TRACKER-APRON-40: Town apron dependencies counted as complete original cells

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | test |
| First noticed | 15 October 2026, in v0.0.40-dev2 |
| Where | CHIM cell-progress digest and aggregate statistics |
| Reproduction | always |
| Duplicate of | no |
| Persists in | fixed in v0.0.40 |
| Severity | medium: Coverage and per-cell resource claims can be overstated despite correct converted geometry. |
| Family | Content silently missing from a build (`build-content-missing`) |
| CHIM | Builder ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | none: found in source (development branch, tests or gates), not in a playtest build |
| From commit | source aa49f1d, engine unknown, CHIM world 01bdf9f |
| CHIM engine version | CHIM 0.2.0, engine unknown, world format 0.7 |
| Unknown because | Offline tracker audit; no native image is accepted by this finding. |
| Platform or emulator | not in game (Read-only conversion-receipt and tracker audit.) |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.42-dev1 (17 October 2026)._

<!-- contents start -->
## Contents

- [Symptom and reproduction](#symptom-and-reproduction)
- [Cause and why it was not caught](#cause-and-why-it-was-not-caught)
- [Repair](#repair)
- [Verification](#verification)
- [Prevention](#prevention)
- [Direct Seyda source receipt gap, 15 October 2026](#direct-seyda-source-receipt-gap-15-october-2026)
- [Direct Seyda source accounting, 15 October 2026](#direct-seyda-source-accounting-15-october-2026)
- [Seyda full conversion follow-up - 15 October 2026](#seyda-full-conversion-follow-up---15-october-2026)
- [Bugs in the same category](#bugs-in-the-same-category)

<!-- contents end -->

## Symptom and reproduction

Digest the expanded Vivec conversion with its source ownership receipts. The
old reader counts 45 converted cells, although the declared core covers 36
original Morrowind cells. Nine cells outside that core are terrain-apron or
object dependencies. Whole-frame memory and time figures also appear on each
cell, where they can be mistaken for independent cell measurements.

## Cause and why it was not caught

The tracker inferred logical ownership from rendered placement ownership in
chunks. Objects needed across a boundary can appear outside their owning core.
Earlier fixtures did not distinguish an empty owned cell from a populated
apron cell, or exercise neighboring cores sharing reference dependencies.
Geometry validation does not validate this reporting predicate.

## Repair

Validate declared original-cell bounds against the frame origin, scale and
terrain grid. Count the complete declared core, including empty cells, and
retain apron cells separately. Use original master/reference identities for
owned, dependency and deferred types; a shared dependency does not become a
second maintainer. Preserve separate dependency provenance for each frame and
unknown counts when source accounting is absent. Reject conflicting or
incomplete ownership. Historical builds without declarations keep their prior
interpretation. Whole-frame memory, timing, model and placement totals remain
run-level data.

This changes offline reporting only; AmiQuake rendering and collision are
unchanged. Source receipts are evidence, not a runtime acceptance substitute.

## Verification

Nine behavioral cases pass, including adjacent cores with mutual dependencies,
empty owned cells, historical inputs, unknown reference counts, invalid bounds,
duplicate owners and frame-metric scope. The unchanged actual Vivec conversion
now reads as 36 core and 28 apron-only cells, with 6,039 owned references,
33 external dependencies and 297 deferred references. The source fix does not
promote canonical coverage by itself. On 15 October 2026 the canonical tracker
was refreshed from these exact conversion receipts. It retains 36 owned core
cells, 28 apron-only cells, original reference types and deferred actors. Global
converted and package counts are unchanged. The new combined source gate,
native seams, packaging and shipment remain pending.

## Prevention

Require explicit original-cell ownership for new town conversions. Test shared
dependencies across adjacent cores and verify source identities before ingest.
Keep converted, audited, native-checked and packaged states separate.

## Direct Seyda source receipt gap, 15 October 2026

The direct Seyda producer bypasses the common source-receipt writer. Its
conversion output has no declared original-cell ownership receipt, so the
historical occupied-chunk fallback suggests 29 cells instead of the configured
16-cell core. That digest was rejected. Only the confirmed stair failure in
(0, -8) is recorded; no extra whole-cell coverage is added. A common receipt
from the actual source path and measured original-type/deferred accounting
remain required. Geometry has not been re-run to repair reporting.

## Direct Seyda source accounting, 15 October 2026

The direct source path now emits the same original-cell ownership contract.
It hashes the existing audit, original placements and scenery index, checks
every declared-cell reference count, and rejects missing or duplicate identities.
All original core references retain their types and declared CELL, while physical
origin decides ownership. External static dependencies, separate harvest input
and non-static/deferred references have distinct records. These counts do not
assert actor or other gameplay completion.

Fourteen focused tests pass, including truncated non-static references. A separate
readback of existing source data resolves 16 original core cells, 2,982 original
core references and 103 dependencies. It records 1,695 non-static/deferred
references by original type. No geometry or failed receipt was changed and no
new canonical converted/native/package coverage was promoted by this sidecar.


## Seyda full conversion follow-up - 15 October 2026

The fresh conversion records sixteen owned original cells separately from twenty
apron cells. Its catalogue accounts for 2,982 owned references and 103 dependencies;
1,461 deferred references retain original types. Four Seyda and two Vivec cells
formerly counted only as packaged town overlaps now have original-cell conversion
evidence. Native adjacent-cell visual/collision seams and whole-cell package
readback remain pending. No historical shipment count is increased.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Content silently missing from a build (`build-content-missing`). Every omission is receipted; payload and entity counts are compared with the last release; shipped features are on by default. See [families](README.md#families).

- [ACTOR-LIBRARY-LEFT-OUT-48](ACTOR-LIBRARY-LEFT-OUT-48.md): The actor library made no model for corpse creatures and for town NPCs standing outside the towns: 9 outdoor references left out
- ACTOR-MOVING-RUNTIME-GROUND-48 (no report page): Moving actors (levitation, flying creatures, jumping, swimming, knockback, scripted SetPos) need runtime grounding beyond the build-time bake
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
- [CHIM-LAVA-TERRAIN-SPIKES-38](CHIM-LAVA-TERRAIN-SPIKES-38.md): Angular terrain wedges cross a lava pool in the final-image inspection
- [CHIM-NATIVE-IMAGE-NO-SHARED-SKY-36](CHIM-NATIVE-IMAGE-NO-SHARED-SKY-36.md): CHIM-native images with no legacy exterior (MiniWinds of one town) ship without the shared sky their frame maps name
- [CHIM-REGION-DOORS-NO-ROOMS-48](CHIM-REGION-DOORS-NO-ROOMS-48.md): The load doors of CHIM region frames never lead into a room
- [CHIM-ROOM-FAST-MB-AFTER-OPTIMIZER-48](CHIM-ROOM-FAST-MB-AFTER-OPTIMIZER-48.md): Marking rooms as needing 32 MB rewrote 16 room maps after the optimizer receipt, and the image step stopped
- [CHIM-ROOM-LAVA-UNDER-WATER-48](CHIM-ROOM-LAVA-UNDER-WATER-48.md): CHIM rooms could not hold a lava pool whose bed reaches under the water level: 3 base-game rooms set aside
- [CHIM-ROOM-SHELL-NO-HULL-48](CHIM-ROOM-SHELL-NO-HULL-48.md): Batch CHIM rooms declared no standing hull, so the actor ground check refused all 1,910 of their residents
- [GUARD-TORCH-REBAKE-MISMATCH-48](GUARD-TORCH-REBAKE-MISMATCH-48.md): Eight guards first staged in v0.0.48 get no torch: their base models do not rebake exactly
- [GUARD-TORCH-TYPES-LIMIT-48](GUARD-TORCH-TYPES-LIMIT-48.md): The image step stops on Too many distinct staged guard models: the batch rooms bring more than 32 guard types
- [INTERIOR-PLACED-ITEMS-47](INTERIOR-PLACED-ITEMS-47.md): Takeable and movable items and containers in converted interiors are not live objects (placed items are left out)
- [LAVA-NOT-IMPLEMENTED-33](LAVA-NOT-IMPLEMENTED-33.md): Lava is drawn as plain static meshes: no liquid surface, no damage, no view tint, never tracked
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
