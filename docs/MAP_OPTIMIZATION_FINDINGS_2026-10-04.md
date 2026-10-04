# Map optimization findings: 4 October 2026

Companion to [AmiWind Map Optimization Toolkit](AMIWIND_MAP_OPTIMIZATION_TOOLKIT.md).
This integrates the owner's supplied documentation draft with measured local
artifacts and host tests. Public summaries contain no game geometry or private
host paths. The supplied draft and independent reviews remain unchanged in the
private archive. Diagnostic numbers are experiment identifiers, not game releases.

## Trial ledger at a glance

Each gain below is relative to the immediate input unless the entry explicitly
says “vs original.” Counts distinguish placed-face classifications from stored
BSP records. Later byte or face totals are not automatically attributable to one
pass; the raw tables and scoped receipts remain below.

| Change / how | Immediate input; immutable-original comparator | Gain | Loss / remaining failure | Verification | Verdict | Evidence identifier |
|---|---|---|---|---|---|---|
| Immutable source baseline | — (original 26,190 stored faces / 4,550,392 B) | Reference only | Existing same-ABI combined-peak estimate is 6,471,168 B, 179,712 B over 6 MiB; not a physical-memory measurement | Source copy and SHA bound in local receipt | Baseline; fails current modeled budget | Original sn045 |
| **001 terrain clip:** clip against upward world-model LAND | Original: 26,190 / 4,550,392 B | 1,441 fully buried faces removed; −1,441 stored faces / −110,208 B; 805 crossing clips | Used compiled BSP LAND with a −512 bound, not canonical global topomap; water/sky/stone excluded; 298 fragment-growth cases retained; target load/heap pending | 240 placements, 4,241 receiver triangles, 960 collision checks; 3,777 world faces and world polygons/UVs exact | **Not accepted for canonical-terrain requirement** | Terrain receipt 001 |
| **017 canonical-terrain diagnostic:** direct topomap clipping | Immediate source: 30,987 / 5,180,472 B | 2,581 placed faces classified fully buried among 39,454 processed placed faces | Output grew to 33,654 / 5,335,220 B (+2,667 stored faces / +154,748 B); receiver/renderer range and full serialized acceptance unresolved | Independent/local 017 audit; 4,686 placed crossings/subdivisions | **Incomplete; no net storage win** | Canonical receipt 017 |
| **022 hidden-surface pass:** bounded closed opaque convex-shell proof | 021: 32,209 / 5,013,620 B | None; 0 whole house faces removed | Same geometry and bytes; 1,769 open/nonmanifold, 138 nonconvex, 15 duplicate and 1 budget-retained; general flood fill absent | 240 placements, 212 assembly proofs; output byte-identical to 021 | **Partial classifier only; house-removal goal unmet** | Hidden receipt 022 |
| **023 exact plane dedup:** merge identical full 20-byte plane rows | 021: 32,209 / 5,013,620 B | −50,940 BSP bytes; face count unchanged | Still +6,019 stored faces / +412,288 B vs immutable original; no geometry reduction | 2,547 exact duplicates removed; 484 collision checks and exact remap checks | **Verified storage-only partial win, not overall acceptance** | Plane receipt 023 |
| **Original → 023 total comparison:** compare immutable source to plane-only candidate | Original: 26,190 / 4,550,392 B | No net benefit demonstrated | 023 is 32,209 / 4,962,680 B: +6,019 faces / +412,288 B (+22.98% / +9.06%); lump attribution follows below | Hash-bound whole-file and per-lump audit | **Overall candidate remains larger** | Original-to-023 storage receipt |
| **Safe control 002:** exact-plane pass, remove reserved local sky faces, compact unused records | Immediate input: control 001 stage 02, 4,545,500 BSP B + 32,768-B shared asset = 4,578,268 B; immutable original: 4,550,392 BSP B | Output: 4,495,396 BSP B + same 32,768-B asset = 4,528,164 B; −50,104 B vs immediate input, −22,228 B vs original combined total. Modeled combined peak: 6,406,912 B, 64,256 B below original estimate. | Still 115,456 B over 6 MiB; no canonical terrain clipping; only 169 sky faces removed; no HDF/native or target-performance evidence | Same-ABI model; 476 collision checks, exact PVS, surviving polygons/material/UV/light and placement bindings | **Limited storage control passes; still fails modeled map budget and has no playable acceptance** | Safe-pass controls 001/002; control-memory 001 |
| **Shared sky conversion batch 001:** remove local exterior sky faces and stage one shared background resource | Reported original aggregate: 2,664 exteriors / 4,114,227,244 B; no pre-run map hashes were captured. The 58 interior maps and one unclassified map (27 sky faces retained) are out of scope. | Output: 3,976,523,908 B including one 32,768-B resource; all 301,751 exterior sky faces removed, zero remain. Reported aggregate difference: −137,703,336 B (−131.324 MiB). Measured accounting: 8,555,996 B face/marksurface/metadata savings + 129,180,108 B cleanup − 32,768 B shared asset = 137,703,336 B net reduction. | Inputs were not changed; missing pre-run hashes prevent a hash-bound before/after claim. No HDF, same-ABI peak estimate, Amiga native rendering or target-cost result. | 8-worker conversion (262.281 s), then 20-worker final readback (1.891 s), zero per-map failures; 741,044 model/hull checks; output readback/hash and model metadata, PVS and lighting checks | **Host conversion completed; package, source-bound comparison, memory and target acceptance remain pending** | Shared sky unused-cleanup batch 001 |
| **House terrain A/B:** clip one mesh to measured terrain | 616 vertices / 578 polygons / 864 fan triangles | Removed 12,360.891177 square compiled units of buried area, about 5.217% of original total mesh area | Output rose to 675 / 590 / 919 (+59 vertices / +12 polygons / +55 triangles); no BSP emitted; no disk or runtime saving measured | Same-clipper area consistency and UV checks; not independent Boolean proof | **Reject as an optimization result** | Terrain-object A/B 001 |
| **Corrected one-house repeat:** repeat the same clip after float32 and BSP write/reload | One bounded house fixture; first cut output 675 / 590 / 919 | Reported stable through 10 raw float32 repeats and 10 actual BSP write/reload recuts at `2e-5`; first cut removed 12,360.891177 compiled square units | Fixture-only evidence. The reviewed 023-002 ZIP contains the unchanged 023 BSP; it omits the matching corrected clipper, tests and full-scene runner. This result was not independently reproduced from that ZIP and was not applied to its BSP. | Local receipt; independent package audit confirms the BSP bytes are still the uncorrected 023 candidate | **Scoped repeat evidence only; no corrected BSP or world-wide certificate** | Terrain idempotence 001; 023 independent audit |
| **Full 023-002 stress repeat:** repeat float32 array clipping across placements | 224 placements / 37,948 polygons in the local diagnostic run | Reported 10 repetitions with zero geometry changes, unknowns or degeneracies; no observed boundary error over `2e-5` | 18 conservative bounds exceed `2e-5` (not observed failures; maximum about `5.692e-5`); no BSP emitted; corrected source/tests/runner absent from the reviewed ZIP, whose BSP is unchanged | Private run receipt; external reviewer could not rerun this result from the supplied package | **Bounded array stability only; universal certification and reproducible package remain pending** | Full 023-002 receipt; 023 independent audit |
| **Objects-only canonical clip estimate:** clip placements against canonical land without inserting LAND | Control 002 BSP: 26,021 stored faces; canonical surface used only as a clipping reference | 2,581 buried placed faces classified removed; placed faces 39,454 → 37,948 | Estimated stored faces 26,021 → 28,688 (+2,667), vertices 23,265 → 29,220; geometry-array plus registry estimate +438,928 B. No BSP written; no full-loader estimate. Coarse visual terrain and original collision disagree with canonical receiver; lightmap/UV writer not run. | Read-only 240-placement estimate; 5,755 new fragment faces; no errors in the bounded run, but tolerance is not globally certified | **Not accepted; demonstrates that buried placed-face cuts can still grow stored arrays** | Objects-only control estimate 001 |
| **023 winding audit and bounded source fix:** preserve directed winding through clipping/coalescing | Actual 023 plus source fixture now verified against original ordered points; diagnostic BSP remains unchanged | Fixed fixture: 590 polygons / 919 fan triangles, zero reversed loops; exact ordered loop/plane bytes+side; 27 focused tests; ten float32 recuts stable | The 023 BSP/023-002 package is not rebuilt; full-scene repeat, production serialization and Amiga visual consequence remain unknown | Hash-bound `canonical-winding-fix-001` receipt and actual-BSP numeric fixture | **Bounded source fix validated; production BSP/release acceptance remains open** | Canonical winding fix 001; prior 023 independent audit |
| **Serializer winding follow-up:** correct source-loop orientation in canonical writers | Original-based full diagnostic build is currently being prepared | Three regressions reproduced against old source; current focused suite passes 30 tests across world writer, placement writer and visible-water preservation | The helper-level proof did not cover actual serialized output. The original-based canonical-terrain + clipped-object + shared-sky BSP is not complete, reviewed or accepted. Current policy preserves visible upward water and clips buried closure sides/bottoms. | Current source fixes in both canonical writers; 30 focused tests; actual final BSP output still required | **Source fix and focused tests pass; integrated candidate pending** | Canonical writer follow-up, 4 Oct 2026 |
| **Bounded stump canonical audit:** classify one bounded static-scene sample | One read-only sample against canonical terrain; no production BSP emitted | 67 removed, 24 crossing, 27 unchanged; 3,421 above-ground samples survive | Local rendered LAND differs from canonical by up to 9.29443 compiled units in the sample. No whole-world coverage or net-storage result. | Bounded source audit and current writer regressions; sample-specific only | **Evidence for the bounded sample, not culling acceptance** | Stump canonical audit, 4 Oct 2026 |
| **PVS exact-data deduplication probe** | Eleven-map bounded probe | None; zero bytes saved | All 11 outputs byte-identical; no geometry or memory improvement to pursue from this probe | Byte comparison across the bounded sample | **No-op; no optimization claim** | PVS dedup probe, 4 Oct 2026 |
| **Host visibility / simplification:** RTX/offline cameras, IDs/depth and optional simplifier | Proposed assembled building plus canonical terrain | None measured or implemented | Sampled unseen faces are not deletion proof; target replay and acceptance not run | Research plan only | **Proposal, not an optimization trial result** | [Host visibility analysis](HOST_VISIBILITY_ANALYSIS.md) |

## Prioritized recovery checklist

1. **Keep the immutable original as the release comparison.** The 023 diagnostic
   is not a release base. Under the same recorded ABI policy, the original is
   modeled at 6,471,168 bytes and safe control 002 at 6,406,912 bytes. The
   64,256-byte reduction still leaves control 115,456 bytes over the 6 MiB map
   allowance (derived from the 11 MiB engine Hunk, less 3 MiB engine reserve and
   2 MiB safety margin). This modeled shortfall is not observed heap exhaustion
   and does not block previews/development; it does block a claim of passing the
   map budget. It is not physical-Amiga RAM; 023 has no fresh same-ABI full
   estimate. Never infer RAM savings from BSP disk bytes.
2. **Unblock terrain correctness before map acceptance.** Diagnostic canonical
   terrain still lacks production spawning and verified agreement with coarse
   collision terrain. Do not reduce terrain quality or substitute a lower-detail
   surface to pass the budget. Keep the canonical analysis reference distinct
   from the final stored render representation and validate their relationship.
3. **Measure each accepted stage with the same ABI policy.** Report each staged
   map's resident/combined peak and remaining headroom separately from disk
   bytes. Every required stage must remain below the 6 MiB cap; repeat the budget
   audit over all staged maps before HDF assembly. Native target measurement is a
   separate gate.
4. **Carry the bounded winding fix into a full-scene candidate and recheck it.**
   The source-linked one-house fixture now has zero reversed loops and passes its
   directed-loop/plane-side and ten-recut checks. The actual 023 BSP is unchanged;
   full-scene repeat and native rendering remain pending.
5. **Treat unfinished visibility work as a blocker or research item.** There is
   still no general assembled-scene solver for sealed/interior-only house faces,
   and camera/GPU analysis remains a proposal. Keep its results out of the memory
   case until stable, reviewed exclusions are serialized and remeasured.

## Evidence and compiled storage

Independent reviews cover preview 017 and diagnostics 021/022. Subsequent local
checks cover the written 023 plane-only BSP, inspector builds 018/019 and one
canonical-terrain house experiment. These checks are not native/GPU acceptance.

| Stage | Stored faces | BSP file bytes | Δ vs original (faces; bytes) | Evidence |
|---|---:|---:|---:|---|
| **Original production sn045** | **26,190** | **4,550,392** | **baseline** | Immutable original verified locally; absent from the independent review packages. |
| Canonical diagnostic 017 | 33,654 | 5,335,220 | +7,464; +784,828 | Independent audit and matching local artifact. |
| Diagnostic 021 / hidden-cull 022 | 32,209 | 5,013,620 | +6,019; +463,228 | Both local and independent checks: byte-identical. |
| **Plane-only diagnostic 023** | **32,209** | **4,962,680** | **+6,019; +412,288** | Written file measured locally and bound to its remapping receipt. |

The earlier 001 terrain-clipping candidate is part of this history, but it used
a different receiver definition and must not be conflated with later canonical-
topomap experiments:

| Stage | Stored faces | BSP file bytes | Recorded result |
|---|---:|---:|---|
| Original baseline used by 001 | 26,190 | 4,550,392 | Immutable source; same starting totals as the table above. |
| 001 compiled-LAND clip candidate | 24,749 | 4,440,184 | 1,441 fully buried faces removed; 110,208 bytes saved; candidate only. |

Receipt 001 processed 240 placed model records against 4,241 upward world-model
LAND triangles, with a bounded bottom at -512 compiled units; water, sky and stone
were excluded as receivers. It recorded 805 crossing faces clipped, 298 cases
where crossing-fragment growth was retained, 960 collision semantic checks, and
3,777 world render faces unchanged with world polygons and UVs exact. The source
was not overwritten, and target loader/heap acceptance remained pending. This
older receiver was compiled BSP LAND, not the later globally aligned canonical
topomap surface; its removals are historical evidence for that limited trial,
not acceptance of the owner-required canonical-terrain pass.

Unlike the supplied draft's derived total, 023's size above is now measured.
It remains 6,019 faces and 412,288 disk bytes larger than the original production
baseline: +22.98% in stored faces and +9.06% in file bytes. Reducing one
representation cost does not establish overall success.

These rows are serialized BSP totals, not counts of distinct placed meshes or
surfaces actually drawn by a camera. The sequence is not a monotonic before/after
series for one unchanged conversion: canonical terrain scope, assembled delta
content and later representation-only operations differ. Do not attribute the
overall growth or reduction to one culling pass without a hash-bound A/B of the
same inputs and stages.

## What differs between the original and diagnostic 023

A separate lump-by-lump audit compared the immutable original and the written
023 candidate directly. The total difference is exactly **+412,288 serialized
bytes**; the table below locates that growth. Record counts are stored BSP
records, not unique placed surfaces or proof of what the camera draws.

| Lump | Original bytes | 023 bytes | Δ bytes | Records, original → 023 where recorded |
|---|---:|---:|---:|---:|
| Edges | 198,972 | 330,140 | **+131,168** | 49,743 → 82,535 |
| Surfedges | 352,696 | 436,472 | **+83,776** | 88,174 → 109,118 |
| Faces | 523,800 | 644,180 | **+120,380** | 26,190 → 32,209 |
| Vertices | 280,380 | 375,432 | **+95,052** | 23,365 → 31,286 |
| Planes | 1,003,440 | 1,057,300 | **+53,860** | 50,172 → 52,865 |
| Texinfo | 765,480 | 710,840 | **−54,640** | 19,137 → 17,771 |
| Textures | 469,700 | 453,248 | **−16,452** | — |
| Marksurfaces | 10,322 | 3,408 | **−6,914** | 5,161 → 1,704 |
| Entities | 50,766 | 56,699 | **+5,933** | — |
| Models | 7,616 | 7,744 | **+128** | 119 → 121 |
| Header padding / other | 129 | 126 | **−3** | — |
| Other unchanged lumps | — | — | **0** | Visibility, nodes, lighting, clipnodes and leaves |
| **Total BSP file** | **4,550,392** | **4,962,680** | **+412,288** | — |

This is an exact storage accounting, not a causal attribution of every change to
terrain clipping or hidden-surface work. The 021→023 plane remap itself removes
50,940 disk bytes without changing geometry; the remainder of the original→023
comparison spans different conversion content and terrain scope. The only
demonstrated net result against the immutable original is a larger serialized
file with more stored faces. No overall optimization benefit, runtime-memory
fit, or Amiga performance gain has been demonstrated; the 50,940-byte plane
reduction is a narrow representation-only improvement, not overall acceptance.

### Required comparison format for future optimization reports

Every future optimization report must show the immutable original and the
immediate input to the pass side by side, each bound to its hash, followed by
the output. Record pass order and canonical-terrain policy, removed/new/net
counts at the placed and stored-record scopes, per-lump disk-byte changes, and
any measured runtime/target cost in separate fields. State what was accepted,
what was rejected and why. Keep disk size separate from modeled or measured
resident memory, loading time and frame cost. A local pass win must not be
presented as a net win against the immutable original unless that full comparison
shows one.

From 017 to 021, the canonical-terrain portion loses 1,597 stored faces while
the world model gains 152. The shared pool remains at 5,218 and other inline
models at 19,862 faces. This is count accounting, not proof that every retained
polygon is identical. The 017 audit also reports 39,454 placed faces processed,
4,686 placed crossings/subdivisions and 2,581 fully buried placed faces removed;
these placement-scope counts are not interchangeable with its 33,654 stored
face records.

## Exact plane-record deduplication: applied

| Input | Plane rows | Distinct complete rows | Duplicate rows | Plane-lump opportunity |
|---|---:|---:|---:|---:|
| 017 | 57,009 | 52,817 | 4,192 | 83,840 bytes |
| 021 / 022 | 55,412 | 52,865 | 2,547 | 50,940 bytes |

These opportunities concern different inputs and are **not cumulative**.
023 applies the second opportunity. Only bitwise-identical full 20-byte records
are combined; float approximations, normal reversal and plane-type changes are
not equivalences. First occurrence order is retained. All plane references in
faces, render nodes and collision nodes are remapped.

Checks resolve the original and remapped records for all 32,209 faces, 16,521
nodes and 25,140 clipnodes. Other fields and the eleven unrelated lumps remain
byte-identical, including geometry, UVs, lighting, textures, entities/shared
ranges, PVS and model roots. There are 484 paired model/hull semantic checks.
Nine focused host tests cover remapping, exactness, malformed input, idempotence
and fresh-output CLI behavior. No source BSP is overwritten. This is a verified
representation saving, not a native frame-rate or whole-map memory-fit result.

The earlier audit's 1,520 exact coplanar terrain quad candidates include five
whose merged UV extent exceeds the 64-pixel surface limit. There are no remaining
pairs under the same criterion in 021/022. Blindly merging all historical pairs
would violate that limit; the old opportunity must not be counted again.

## Hidden-interior detector: zero cuts preserved in the record

022 uses exact-topology opaque convex-shell strict containment. It attempts 240
static placements with 212 distinct geometry proofs. Its output is byte-identical
to 021; no house-interior polygons are removed.

| Component classification | Count |
|---|---:|
| Open or nonmanifold exact-coordinate topology: retained | 1,769 |
| Not convex: retained | 138 |
| Duplicate triangles: retained | 15 |
| Proof budget exhausted: retained | 1 |
| Certified opaque convex shells | 70 |
| Total | 1,993 |

Failure to prove strict containment is not proof that a surface is visible or
necessary. Conversely, a two-sided noclip view does not prove an extra inner wall
exists. General assembled-world exterior flood fill is not implemented. The
default-on bounded pass and its failure on these houses remain separately
documented in [exterior hidden surfaces](EXTERIOR_HIDDEN_SURFACES.md).

Host-side visibility capture and surface simplification are separate research
proposals, not current optimizer results. Camera-sampled unseen faces remain
candidates until independently justified; RTX timing would describe offline
analysis only, not Amiga performance. See the proposed
[host visibility-analysis and optimizer-profiler workflow](HOST_VISIBILITY_ANALYSIS.md).

## Inspector receiver and selection corrections

The archived inspector 016 searched model zero for terrain, whereas the tagged
canonical receiver was another model. Build 018 uses entity roles for receiver
discovery, target exclusion and terrain visibility. Empty receivers report
"Terrain unavailable; check not performed". Sixteen host groups passed. This
fixes discovery, not the preview's finite-depth/fragment-retention limitations.

Build 019 manually integrates the reviewed placement-group selection approach
into the newer inspector, preserving terrain, painting and camera fixes. Counts,
highlighting, selected-only isolation and Fit use the same entity group. Active
batch counts remain distinct; face indices and clicked-side paint IDs are stable.
Eighteen host groups passed. Actual 023 contains 609 nonempty render batches,
226 nonempty entity/world groups and 145 multi-batch placements. One checked
placement has 1,136 polygons and 1,276 fan triangles across two batches; its
clicked pool batch alone has 162 polygons. Batch counts are not placement counts.

The Python scene exporter also preserves explicit terrain role, entity index,
class and shared-range binding. Seventeen focused exporter/pool tests pass.
GPU appearance is not verified. Painted/volume plans remain proposed cuts;
compiler consumption is not connected by these inspector changes.

## Embedded-house A/B: less buried area, more geometry

One original house is clipped against the exact globally transformed canonical
terrain packet with 0.5 compiled units of contact overlap. Water is not a receiver;
the terrain is unchanged. This is surface clipping, not a welded Boolean union.

| Metric | Untouched house | First clipped result | Change |
|---|---:|---:|---:|
| Polygons | 578 | 590 | +12 |
| Inspector fan triangles | 864 | 919 | +55 |
| Exact float32 local vertex positions | 616 | 675 | +59 |

The cut creates 83 new positions and leaves 24 old positions unreferenced. No
whole face is dropped; 48 crossing or numerically changed source faces produce
60 fragments. Total surface area falls 5.218%, but geometry counts increase.
There are no final degenerate polygons/fan triangles or unknown terrain coverage
in this bounded case. Original texinfo is reused; maximum recorded UV float32
error is approximately 0.00000246 texels. Area consistency was checked with the
same clipper, not an independent Boolean proof. No BSP was emitted for this
experiment, so no file, heap, collision, PVS or lightmap saving is claimed.

### Repeat-clip acceptance: separate geometry from representation

The recorded A/B starts at 616 float32 local vertices / 578 polygons / 864 fan
triangles; the first clipped result has 675 / 590 / 919. Re-clipping the 675 / 590 /
919 result at the same boundary produces 704 / 594 / 948. These additional fragments
prove representation instability in this example. They do not yet prove that the
resolved clipping boundary moved, that surface coverage was duplicated, or that the
complete BSP grows after shared geometry and compaction.

For a fixed source surface `S` and occupied boundary `B`, acceptance requires
idempotence of resolved geometry: `C_B(C_B(S)) = C_B(S)`. Keep this separate from
representation stability. The regression should follow one face through original
input → first clip → cleanup → repeat clip with the same `B` → cleanup. Compare
resolved boundary and coverage, orientation, material, UV mapping and placement,
not just counts or hashes. Record tessellation, fragment counts, float32 coordinates
and bytes separately; equivalent surface output may have a different representation,
but its numeric tolerance must be set and checked.

Then serialize using the actual BSP float32 fields, reload that serialized BSP, and
run the same clip and cleanup again. This catches differences hidden by higher-
precision intermediate meshes. The diagnostic repeat must execute the clipper;
do not short-circuit on an `already_clipped` marker. A no-op repeat alone cannot
show the first cut was necessary: compare the untouched input with the first result
and verify the removed region against the same canonical boundary. No material/UV
or placement change may be hidden by cleanup or welding.

The earlier 021 fragment growth remains a historical representation-instability
finding; the corrected one-house fixture below passes its scoped repeat check.
Full-scene acceptance remains pending. The current counts cannot be described as
boundary movement, duplicate surface coverage or whole-BSP growth.

A later bounded 023-002 stress check ran 224 placements / 37,948 polygons through
ten float32-array repetitions: zero geometry changes, unknowns or degeneracies.
Eighteen conservative error bounds exceeded `2e-5`, so the result does not
certify every case. It did not emit a new BSP.

A separate corrected one-house fixture remained at 675 vertices / 590 polygons /
919 fan triangles through ten raw float32 repetitions and ten actual BSP
write/reload recuts under an explicit `2e-5` tolerance; its first clip removed
12,360.891177 square compiled units. This scoped pass does not erase the earlier
021 fixture's 675 / 590 / 919 → 704 / 594 / 948 representation instability and is
not a full-scene certificate. Full-scene numeric certification remains pending.
## Memory, shared sky and production gates

| 021 source-bound estimate | Bytes |
|---|---:|
| BSP-only loader peak | 6,856,336 |
| BSP resident allocation | 6,717,664 |
| Sprite resident allocation | 600,256 |
| Shared-range registry allocation | 11,536 |
| Conservative combined peak | 7,329,456 |
| Combined excess over 6 MiB | 1,038,000 |

The combined figure is not the BSP file size or merely its loader peak. The
original baseline's combined estimate is 6,471,168 bytes, already 179,712 over
the same allowance. None of these figures is a physical-Amiga RAM measurement.

Using the recorded target ABI and allocation alignment, 023 reduces the plane
allocation by 50,928 bytes (different from its 50,940 disk bytes). Subtracting
this component delta gives a provisional combined 7,278,528 bytes, still 987,072
over the allowance. This is arithmetic from existing estimates, not a fresh full
loader execution or native measurement.

A later same-ABI comparison of the immutable original and safe control 002 gives
modeled combined peaks of 6,471,168 and 6,406,912 bytes respectively. The
control's 64,256-byte modeled reduction still leaves it 115,456 bytes above the
6,291,456-byte map limit. This profile does not estimate 023, and neither value
is a physical-RAM measurement. The 7,278,528-byte 023 figure above is only the
older arithmetic projection; do not treat it as a fresh estimate for this
candidate.

The serialized candidate has zero sky-textured render faces, retains a sky
resource, and references the shared exterior sky asset. A universal background
renderer can vary by region and time without restoring cell-sized render boxes.
Regional weather/day-night are separate implementation work; see
[sky and background rendering](DAY_NIGHT_AND_SKY.md).

Canonical terrain remains an inspector-only diagnostic entity without production
QC spawning. Agreement with the older collision terrain, native sky/terrain
appearance and target memory/performance gates remain unresolved. No new HDF is
produced by the plane or inspector work. A smaller diagnostic and a working host
test do not establish a playable production build.
