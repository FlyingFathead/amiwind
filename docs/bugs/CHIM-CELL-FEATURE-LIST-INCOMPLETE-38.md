# CHIM-CELL-FEATURE-LIST-INCOMPLETE-38: Cell feature list incomplete

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 12 October 2026, in v0.0.38-dev2 |
| Where | Exterior CHIM cell coverage and release feature lists |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.38-dev2, v0.0.40-dev1 (last seen) |
| Severity | medium: Coverage reporting can hide deferred authored features despite passed geometry audits. |
| Family | Content silently missing from a build (`build-content-missing`) |
| CHIM | Builder ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | source-only |
| From commit | source c2eaa5a, engine unknown, CHIM world unknown |
| CHIM engine version | CHIM unknown, engine unknown, world format unknown |
| Unknown because | Source ocean checklist integration has98targeted passes. Actual successor conversion/final routing/native/package remain pending; original LAND and routing-only cells stay distinct. |
| Platform or emulator | not in game (Original master and source audit.) |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.42-dev1 (17 October 2026)._

<!-- contents start -->
## Contents

- [Explicit ocean checklist integration, 15 October 2026](#explicit-ocean-checklist-integration-15-october-2026)
- [Symptom](#symptom)
- [Where](#where)
- [How it happened](#how-it-happened)
- [Why it was not caught](#why-it-was-not-caught)
- [Reproduction](#reproduction)
- [Repair](#repair)
- [Verification](#verification)
- [Prevention](#prevention)
- [Maintainer evidence reconciliation, 13 October 2026](#maintainer-evidence-reconciliation-13-october-2026)
- [Entrance metadata audit, 14 October 2026](#entrance-metadata-audit-14-october-2026)
- [Ring-0 runtime ownership, 14 October 2026](#ring-0-runtime-ownership-14-october-2026)
- [Planned original map-reference views, 14 October 2026](#planned-original-map-reference-views-14-october-2026)
- [Dev2 ocean source integration and town scope, 15 October 2026](#dev2-ocean-source-integration-and-town-scope-15-october-2026)
- [Original-cell town source implementation, 15 October 2026](#original-cell-town-source-implementation-15-october-2026)
- [Ocean validation and town corrections - 15 October 2026, v0.0.40-dev2](#ocean-validation-and-town-corrections---15-october-2026-v0040-dev2)
- [Expanded conversion checkpoint, 15 October 2026](#expanded-conversion-checkpoint-15-october-2026)
- [Bugs in the same category](#bugs-in-the-same-category)

<!-- contents end -->

## Explicit ocean checklist integration, 15 October 2026

15 October 2026, v0.0.41-dev1: full-build preparation rejected five explicitly selected ocean routing cells absent from the original CELL/LAND inventory, before legacy compilation. The source checklist now records additional ocean routing cells separately and allows their absence only before routing rows are appended. Final classification/stage verification still requires every row and CHIM routing flags; undeclared or unselected missing cells are rejected. All 98 targeted checks across five modules pass, including three new ocean checklist regressions. Exact production conversion, native ocean behavior, image/package and delivery checks remain pending; coverage states are unchanged.

The failed dependency preparation is preserved. The full build selected all
365 regional cells, including five explicit ocean cells without original
CELL/LAND inventory rows. exterior_plan.make required every selected cell to
exist in that source inventory, while terrain preparation classified rows
before its existing verified ocean-routing append step. No legacy compilation
or native ocean check completed in this failed preparation.

The checklist now accepts an explicit ocean_cells selection and records only
additional routing cells absent from the original source inventory separately.
They are never relabelled as original LAND. The full builder forwards ocean
kinds; terrain preparation uses before_ocean_routing=True only before
append_routing_rows. Undeclared or unselected missing cells remain rejected.
Default/final classify_regions and verify_stage remain strict: every final
row must exist with required CHIM routing flags. Original ocean admission,
engine behavior and rendering are unchanged; no new runtime mechanism is added.

Three semantic regressions cover the pre-routing/final-row boundary and
refusal of invalid selections or missing final rows. Actual five-module run
(test_chim_seyda, test_chim_ownership, test_world_payload, test_world_manifest
and test_chim_ocean_runtime) passes 98 checks. Current source SHA-256:

- tools/exterior_plan.py: `4ed46d1a56628b94bd7feae9221a814171cd685d5b1f9715fb819d7dd75ebda8`.
- tools/build.py: `dc22c5251ffd65a746a8344ba2b75ab8b4192331eded6507a2e377daa833d6e4`.
- tools/prepare_world_regions.py: `761c0648a87c98234ba2c3aff21bc577f43e196e558c46048dd1be9c32b9cc68`.
- tests/test_world_payload.py: `f04d27fe7ae09b8aa5e66a79023401b9a590e636244717049108d2bf710a7efe`.

This targeted pass also covers the separately recorded opening-barrel missing
CELL correction under [CHIM-FRAME-STATIC-SEAM-40](CHIM-FRAME-STATIC-SEAM-40.md).
The preceding full-suite result remains bound to its earlier snapshot. New
exact world/dependency conversion, final routing readback, native ocean and
boundary checks, image finalization, packaging and delivery remain pending.
The prepared Linux source kit remains held for successor source and undelivered.
Original source cells, routing-only ocean cells, planned coverage and included
payload remain distinct; no tracker state is promoted by this source repair.

## Symptom

Passed measured audits do not establish that every authored exterior-cell feature is present and functional in the playable release. Existing deferred category counts need a per-reference chain from original data through conversion, packaging and gameplay acceptance.

## Where

Exterior CHIM cells and release feature lists. The immediate target is every exterior cell in rings 0, 1 and 2. Interiors may remain BSP29, CHIM or a mixture; converting all interiors to CHIM is not required.

## How it happened

import_town.split_references defers NPC_, CREA, LEVC and LEVI references. NPC residents have a separate path; creature simulation is deferred in the inspected cell. The world validator compares packed references against selected conversion inputs, not an independent inventory of every original reference. Planned coverage is also distinct from final packaged inclusion.

## Why it was not caught

Geometry and format checks answer narrower questions than feature completeness. The tracker exposes deferred categories, but a passed overview can be mistaken for playable feature coverage. This does not establish that every dedicated placement is missing.

## Reproduction

The original CREA record mudcrab_unique has authored reference 404350 in exterior cell (9,-10), with merchant-related dialogue entries. It is a direct placement rather than a leveled random spawn. The inspected tracker places that cell in ring 6 with audits_passed status and all seven creatures deferred. This example is outside the immediate rings 0-2 target. Native presence, dialogue and trading are not accepted.

The flora category is a documented subset of statics with a placed-only count; its zero converted counter does not establish missing vegetation. Some inspected light rows contain both legacy marker and meshless-light deferral counts, so their summed outcomes exceed their original placements. Reconcile unique reference IDs before reporting missing totals; the tracker recursively merged complete accounting snapshots and retained obsolete reasons from older receipts.

An independent base-master census of all 333 target exterior cells found 12,060 original references. Against the dev2 CHIM source manifest, 520 non-light references required explanation: 62 have explicit harvest-removal receipts (an alternate representation), while 458 remain unresolved across cells (-3,-11), (-2,-11), (-1,-11), (0,-11) and (6,-14). These five cells were excluded from regional CHIM ownership by the town-overlap rule. This is a manifest-level finding; legacy-map coverage and final packaged/native presence still need checking. The 383 meshless lights and 430 actor or leveled references are tracked separately.

Exact-package follow-up: 51 map and harvest files covering the five cells were extracted from the sealed dev2 disks and matched their readback hashes. They account for 235 of the 458 unresolved references. The remaining 223 are absent from those maps/catalogues as well as the CHIM source manifest: 183 STAT, 26 CONT, four DOOR and ten ACTI references. Original native/OpenMW scene comparison remains pending. This is a known dev2 content limitation, not a repaired or accepted cell set.

## Repair

Maintainer feedback on 12 October identifies Vivec gondola travel as not implemented.
The dev2 image shows Dalse Adren with a talk prompt at global 33524,-89237,643
in cell (4,-11), heading 281, pitch 11, time 06:50. Visible NPC presence is not
travel-service acceptance. Track inter-canton destinations, fares and successful
transitions separately from the blocked dock approach in
[WORLD-SLOPE-STUCK-38](WORLD-SLOPE-STUCK-38.md). The service remains planned;
this report does not establish that every gondolier or route was tested.

An independent original-master census finds five Gondolier-class NPCs with
16 authored travel destinations in total. Dalse Adren has four destinations
and exterior placement 259456 in cell (4,-11). This establishes source service
data, not fare calculations, interaction implementation or playable travel.

The mutable follow-up now replaces a supplied reference-accounting snapshot instead of recursively merging its obsolete reasons. The tracker suite ran 92 tests with no failures or errors and three skips. Reading preserved results through the repaired loader gives 588 accounting rows for rings 0-2 with no outcome-total discrepancies; 385 lights comprise two converted and 383 deferred. The live tracker was regenerated with the repaired loader and full dev2 build inputs; all 333 target cells retain their ring membership. This repairs reporting only and adds no missing game content.

Remaining: reconcile original IDs and record types: statics, doors, containers, items, flora, lights, NPCs, creatures, leveled lists and markers. Record converted, intentionally nonvisual, deferred, failed, packaged and native-verified outcomes with reasons. Separate visible presence from collision, interaction, dialogue, trading and spawning. Verify town overlaps and ocean coverage against the final package.

## Verification

Source inspection confirms actor/leveled-reference deferral and selected-input placement validation. Original data confirms the merchant reference and dialogue links. No repair, complete original-reference census or native merchant functionality is claimed. The active dev2 build remains pinned independently of this documentation follow-up.

## Prevention

The dev2 world-directory follow-up separates terrain frame bounds from runtime handoff cores. All 223 unresolved references lie outside every configured town handoff core and resolve to eight open-world directory rows. This includes all 53 references inside a larger town frame box. The CHIM preflight currently drops a whole cell on any town-frame intersection, while runtime destination selection prioritizes the smaller town core. Neither intersection nor the town's terrain apron establishes object coverage. The legacy world-scenery census includes rocks and giant mushrooms only; it is not a fallback census for all original reference types. These are source and directory findings, not a native repair acceptance.

The dev2 omission audit must distinguish whole-cell selection from town source coverage. Of the 223 references absent from the checked package paths, 170 have origins outside all selected town frame boxes and 53 have origins inside a town frame box. All 53 inside-box entries are absent from the Seyda source audit and exported scenery index. They are also outside its scenery origin margin; 52 are beyond its export radius, and 15 are outside the ordinary STAT/DOOR type filter. These are overlapping predicates, not additive missing counts. A town-frame overlap therefore does not establish reference coverage. Repair must reconcile per-reference ownership before suppressing a whole coast cell and must preserve alternate asset and gameplay paths.

Generate feature manifests independently from original references and account for every reference before claiming playable completeness. Preserve converted, audited, native-checked and packaged states separately. See [CHIM-COAST-OBJECTS-MISSING-36](CHIM-COAST-OBJECTS-MISSING-36.md) for separate coastline observations whose causes remain unverified.

12 October script and topology investigation: original Stronghold scripts control 139 references in this cell. Their predicates enable respectively 0, 3, 9, 18, 53, 65 and 106 of these references at stages 0 through 6; the event-dependent foreman script is excluded from those counts. These are reference counts, not measured memory savings. Several heavy root and sprout models belong to mutually exclusive construction stages. The unchanged baseline still counts the resident models together. Its two largest root variants each contain 872 compiled faces and 2,600 BSP nodes, plus 13,654 and 13,655 clipnodes. This identifies both conditional-content and compiled-topology contributors; it does not establish a native fix. Effective initial runtime state, phase transitions, render/collision parity and matched OpenMW evidence remain pending. All original assets remain retained.

12 October stage-residency diagnostic: matched original-game views at requested Stronghold stages 0 and 6 show the structure absent and present respectively; logged camera position, yaw, base pitch and field of view agree. A hypothetical residency calculation retaining catalogue allocation and unchanged on-disk assets estimates active-ring peaks for stages 0-6 of 825,344; 1,376,976; 1,489,216; 5,307,184; 5,929,168; 7,141,088; and 7,638,112 bytes. The budget remains 6,242,304 bytes. Stages 5 and 6 still exceed it by 898,784 and 1,395,808 bytes. These are diagnostic estimates, not passing production audits: activation metadata, transition overlap, adjacent-frame demand and deferred actors remain unaccounted. Proposed repair needs both correct stage-aware drawing/collision/residency and further model-memory reduction for the later stages. Existing CHIM Hidden handles opening-story drawing/collision, while Need requests the chunk model list without that filter; hiding alone cannot establish the proposed saving. No engine change, native fix or packaged acceptance is claimed.

12 October source visibility audit: the conservative audit now recognizes complete global-conditioned enable/disable templates and leaves event-driven or unsupported scripts unresolved. A private audit of Molag Mar exterior (10,1) records 139 conditional references, one unresolved event-driven script and 18 references with no attached script. At an explicitly requested Stronghold value of 6, 106 of those conditional references evaluate enabled. This does not infer the initial game state or prove that references without attached scripts are unconditional. Six focused regression tests passed in Docker, covering comparison operators, inverted branches, unknown logic, reference types, ambiguous input and nonfinite CLI state rejection. This is audit metadata only: runtime activation, model residency, gameplay, native and package acceptance remain pending.

12 October whole-region script census: all 123 Molag Mar exterior cells now have per-reference source-script audit receipts covering 15,162 placements. Counts are 139 recognized conditional references, 652 unresolved by the narrow visibility classifier and 14,371 with no attached script. Unresolved includes 310 lava, 262 steam-sound and 33 rotating-sign references; it does not establish that the corresponding engine feature is absent. Cross-reference each script with its implemented geometry, effects, audio or gameplay path and test that path independently. Actor/script support, conversion, residency, native and packaged states remain separate. No original initial global state was inferred.

12 October feature-path reconciliation: all 310 lava-script references in 24 Molag Mar exterior cells are deferred from static geometry with reason lava liquid. Their per-cell counts match the separate CHIM liquid records and generated terrain-liquid prisms, with zero count mismatches across all 123 cells. This establishes count coverage, not an independent reference-to-prism geometry match or native damage/audio acceptance. The same reference-ID join finds converted geometry for 262 steam-sound objects, 33 rotating signs and nine outside banners; sound looping and script-driven animation must be verified separately. The original steam script requests a positional loop, the sign script swings around its starting angle, and the banner script selects animations using weather and randomness. Static geometry alone does not implement these behaviors.


## Maintainer evidence reconciliation, 13 October 2026

The following maintainer screenshot evidence was visually reviewed. Original images
remain in the private evidence archive; identifiers bind this report to those
originals. This records reported symptoms and comparison controls, not a repair
or runtime acceptance. Missing build or pose information remains unknown.

- `OWNER-20261012-184648`: SHA-256 `432c07a628db9bdc39ea69f33b68a21c4a55c225d37f60a8ae51ea48eca88ed9`. Gondolier and talk prompt visible; still frame does not prove absence of travel interaction.


## Entrance metadata audit, 14 October 2026

The maintainer requests recorded exterior entrance locations and original interior destinations even when the interior remains deferred to the next pass. The existing source census and compact entrance tree are useful, but the tree deduplicates destination interiors and does not retain every doorway location as a separate visible entrance. Nonvisual marker DOOR records must stay separate.

A bounded original-master audit finds 19 visible directed teleport-door references in rings 0–2, with 19 destination labels; none has a configured destination map. Pelagiad (0,-7) has 22 visible directed doors to 11 interior cells plus one PrisonMarker. Its 22 door meshes convert in the new offline cell result, but no Pelagiad activation bank or interior payload is produced by that converter-only run.

In the inspected RC2 image stage, one of these 42 original DOOR references has an activation row: Ansi reference 300699 in cell (6,-14), with target `-`; the remaining 18 ring-door references and 22 Pelagiad doors have no row in the scanned banks. Stage metadata is not exact-package/native verification. Ansi's cell remains a partial town overlap excluded from whole-cell packaged counts. The maintainer's unnamed Dwemer example still needs its exact cell/reference binding.

The existing handler already shows `Interior not found.` on normal activation when a registered door's target is invalid or unavailable, and the normal invalid-target prompt is `Interior unavailable`. Quick-build exclusions and MiniWind use their own area-unavailable wording. This requires an aimed door-bank row; missing metadata never reaches the handler. Reuse the original-reference/bounds/label row generation with unavailable target `-` while interiors are deferred. No interior implementation is claimed here.

Preserve per-reference statuses for geometry, activation metadata, destination configuration, actual payload, native entry/return and maintainer verification. The current `door_links` result measures converted door placements after marker exclusion; it does not establish playable interior links. Deferred interiors must not be described as implemented because a door mesh or label exists.

## Ring-0 runtime ownership, 14 October 2026

All five ring-0 cells lack LAND records and runtime core owners. Historical shared-ocean-template checks are retained, but converted/runtime-placed counts remain zero. Two cells contain four original Bloodmoon LEVC references to horkers; the other three have no original CELL or references in the audited three masters. Shared terrain references and ordinary region ownership are the proposed implementation path; no runtime placement, native cost or gameplay acceptance is established.

The Pelagiad selection preserves seven outside-frame static references rather than silently treating them as complete. Windows3348/3350 belong to sourceCELL(0,-7) but their origins lie in(0,-8); they are also absent from the retained neighbouring frame. Preserve this per-reference coverage limitation for the later ownership audit. Source checks alone do not establish a visible missing-window reproduction.

## Planned original map-reference views, 14 October 2026

The maintainer requests original World/Local views at least in the progress tracker.
Reuse existing local-input/background navigation and calibrate detailed local
reference layers independently from the terrain/placement schematic. Original
imagery and exploration never increase converted/audited/native/package counts;
failed, held and excluded overlays remain distinct. This is planned reference
work, not new imagery, cell coverage or native acceptance.

## Dev2 ocean source integration and town scope, 15 October 2026

The current converter candidate admits explicit no-LAND ocean cells and appends
ordinary sequential AWR2 ownership rows without changing existing map or save
identities. It uses the existing CHK1/TERR terrain-reference loader alongside
inline terrain, with the normal AmiQuake world graft, standing hulls and traces.
Original-master hashes bind admission, nearby LAND heights and master-local
material indices. Unsupported or ambiguous source content is refused. Four
original leveled creature references remain explicitly deferred; geometry does
not implement their spawning. New ocean rows are excluded before legacy BSP
compilation. CHIM remains 0.2.0.

The original isolated implementation passed 64 focused synthetic checks.
The integrated source passes 100 focused terrain, routing, far-terrain and
tracker checks with no failures, errors or skips. Actual five-cell conversion,
matched original/native water and seam checks, measured memory and final payload
readback remain pending. These source changes do not increase converted,
native-checked or packaged counts.

The agreed dev2 town repair aligns owned boundaries with the original cell grid:
Vivec x=1..6, y=-14..-9; Seyda Neen x=-3..0, y=-11..-8. It must fill the newly
included reference bands, preserve origins and save IDs, keep terrain aprons
separate from ownership, and verify adjacent terrain/water/collision in both
directions. The older next-batch deferral for six partial overlaps is superseded
by this dev2 requirement. Implementation and coverage acceptance remain open.

## Original-cell town source implementation, 15 October 2026

The dev2 source now owns Seyda Neen cells x=-3..0,y=-11..-8 and Vivec
x=1..6,y=-14..-9, with a separate terrain apron and unchanged frame origins.
Source terrain auditing and scenery selection expand together; old narrow
source catalogues cannot satisfy the new cache fingerprint. Seyda extends
outer edges while preserving all 64 region names, order and ownership of old
points. Vivec uses 64 catalogue selectors; existing scene and interior IDs
remain, but old-save and harvest behavior still needs runtime checks.

Ten source tests and 18 bounded fixtures pass. The source-band audit accounts
for 1,607 Seyda and 1,497 Vivec original references, including moved source-cell
references. Emitted source catalogues classify owned origins separately from
whole-object footprint dependencies and reject duplicate identities within
one frame. Actual adjacent catalogues, resident budgets and original/native
terrain, water and collision seams are still pending. These source fixtures do
not establish converted, packaged or maintainer-accepted coverage.

Five ocean frames were converted, but the reporting step failed on an empty
scenery-model list. See [the reporting repair](CHIM-EMPTY-MODEL-REPORT-40.md).
Original four leveled creature references remain deferred; no spawning or
other unimplemented gameplay is implied by the converted ocean geometry.


## Ocean validation and town corrections - 15 October 2026, v0.0.40-dev2

The five ring-0 ocean cells (-19,14), (-19,15), (-18,15), (-6,26) and
(12,23) contain no original static scenery placements. Their five frames
contain 1,125 terrain chunks. Four original Bloodmoon leveled-creature
references remain deferred because their spawning is not implemented.
No scenery was removed to construct a test case.

An empty-model reporting exception stopped the first validation. The corrected
reporter passes structural/statistics, active-ring memory and zone-allocator
checks against the same geometry. The original failure is retained. The
canonical cell tracker records these scoped offline results and clears stale
measurements from the older shared ocean chunk. Runtime routing, adjacent-cell
visual/collision seams, final payload and native checks remain pending; these
cells still do not count as complete or packaged coverage.

The approved town source now distinguishes owned core from the actual terrain
apron in handoff metadata. The generated engine town table matches the expanded
configuration. The directory check enumerates the existing sector sharding and
retains the 72-entry filesystem and 32-byte engine path limits. Eighty combined
town/reporting tests pass. Actual source conversion, reference ownership,
resource budgets and native save/load/seam checks are still required.

15 October 2026 source follow-up: the fresh Seyda gameplay carrier uses shared
original intro placement and validated hand timing. The full intro retains its
default ten-actor path; the carrier selects exterior roles with original IDs,
headings and grounding. It checks conversion/UI/runtime palette compatibility
before cloning, then uses the existing exterior population and opening scripts.
It rebuilds no unrelated interiors or movie. Seventeen focused checks pass;
actual carrier conversion, original-reference parity, native seams and packaging
remain pending. No converted or playable cell count is increased.

15 October 2026: the expanded original-cell Vivec conversion completed with
structural, active-heap, allocator and stair gates passing. The stair gate walked
12,828 steps/ramps with zero failures and 1,464 advisory findings. Independent
original-reference ownership and per-cell accounting are still under review;
these full-frame results do not establish native seams or playable inclusion.
The fresh Seyda carrier is blocked by the separately tracked
[fixed ocean seal](BUILD-SEYDA-OCEAN-FLOOR-40.md).

## Expanded conversion checkpoint, 15 October 2026

Vivec conversion and canonical ingestion retain 36 original core cells and
28 apron cells separately: 6,039 owned original references, 33 external
dependencies and 297 deferred references. Seyda conversion has 594 models,
1,390 placements and 1,638 chunks. Structure, active heap and allocator gates
pass; 15 stair probes fail at references 3322 and 3324. See
[CHIM-SEYDA-EXPANDED-STAIRS-40](CHIM-SEYDA-EXPANDED-STAIRS-40.md). The source-only carrier avoids the complete-town legacy
terrain compiler; its original-data execution remains pending. Whole playable
coverage, native seams and package inclusion are not promoted.

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
- [CHIM-COAST-OBJECTS-MISSING-36](CHIM-COAST-OBJECTS-MISSING-36.md): Objects including Dwemer ruins are reported missing from the CHIM coast
- [CHIM-LAVA-TERRAIN-SPIKES-38](CHIM-LAVA-TERRAIN-SPIKES-38.md): Angular terrain wedges cross a lava pool in the final-image inspection
- [CHIM-NATIVE-IMAGE-NO-SHARED-SKY-36](CHIM-NATIVE-IMAGE-NO-SHARED-SKY-36.md): CHIM-native images with no legacy exterior (MiniWinds of one town) ship without the shared sky their frame maps name
- [CHIM-REGION-DOORS-NO-ROOMS-48](CHIM-REGION-DOORS-NO-ROOMS-48.md): The load doors of CHIM region frames never lead into a room
- [CHIM-ROOM-FAST-MB-AFTER-OPTIMIZER-48](CHIM-ROOM-FAST-MB-AFTER-OPTIMIZER-48.md): Marking rooms as needing 32 MB rewrote 16 room maps after the optimizer receipt, and the image step stopped
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

Related bugs in other categories:

- [BUILD-SEYDA-OCEAN-FLOOR-40](BUILD-SEYDA-OCEAN-FLOOR-40.md): Expanded Seyda ocean terrain collapses onto the fixed BSP seal
- [CHIM-MOLAG-MEMORY-38](CHIM-MOLAG-MEMORY-38.md): Tel Uvirith exterior cell (10,1) exceeds the CHIM active-ring memory budget

<!-- END GENERATED CATEGORY -->
