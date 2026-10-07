# BALMORA-TEMPLE-GEOMETRY-29: missing interior walls and floors

## Status: 7 October 2026

Fixed in v0.0.30-dev3 (Temple rebuilt with the converter correction); carried
through v0.0.30-rc1. Owner playtest of the lower rooms pending. The sections
below are kept as recorded.

## Cause found, candidate repair: 7 October 2026

Status: **cause identified; repair is a v0.0.30-dev candidate, not shipped and
not yet owner-accepted.** First shipped fixed version: none yet.

**What was wrong.** Some Morrowind meshes carry a transform on the NIF *root*
node. When Morrowind places an object, it ignores that root node's authored
**rotation** but keeps its **translation and scale**. The scenery converter
(`tools/prepare_scenery.py`, `model_geometry`) applied the full root transform,
so any mesh with a rotated root came out turned around its own origin. The
Velothi interior kit pieces used in the Temple carry exactly a 90-degree yaw on
the root node, so whole wall, room and corner pieces were a quarter turn off.

**How it looked in game.** Walls missing where they belong and standing where
they do not; walls seen edge-on as thin slits; black see-through holes (the
black area is the converter's sealed outer box behind the room); floors and
ceilings that could be walked around or through; objects appearing to float
because the surfaces they rested on had moved.

**Why earlier audits missed it.** Triangle counts, surface areas, bounds and
plane checks compared the BSP with source geometry flattened by the same
converter, so both sides carried the same rotation. The 13 off-plane faces fixed
earlier were real but unrelated to the visible holes.

**Evidence.**
- Independent reference: OpenMW at the reported entrance pose (local
  997 1062 3701) shows a closed room with a wall and bench ahead, the entrance
  door, an archway and a banner; v0.0.29 shows an open corridor with black holes.
- Ray-cast of the original scene from the ESM placements and BSA meshes:
  see-through pixels at the reported views drop from 393 / 96 / 39 / 218 to
  **0 / 0 / 0 / 0** when the root rotation is ignored. Applying the root
  rotation in the opposite direction instead closed some holes but left pieces
  90 degrees off (an archway replaced by a solid wall), so that is not the fix.
- Translation check: crates (`contain_crate_01`, root offset z -32) rest exactly
  on the Temple floor only when the root translation is applied, so translation
  must be kept.
- Rebuilt Temple map with the fix: 71 of 76 converted models and all textures
  are byte-identical to the release; exactly the 5 models with a root rotation
  changed (`in_v_s_int_wall_01`, `in_v_s_int_entrance_01`,
  `in_velothismall_room_05`, `in_velothilarge_corner_01`,
  `in_velothilarge_cap_01`). In FS-UAE, four headings at the reported entrance
  pose match OpenMW (wall and bench; bench corner and door; door and archway;
  archway and banner), with no black holes. Only the Temple map was replaced on
  fresh copies of the v0.0.29 disks; the engine was unchanged.

**Repair.** `model_geometry` keeps the root node's translation and scale and
replaces its rotation with identity. Child-node transforms are unchanged.
Regression test: `tests/test_scenery_root_transform.py` (fictional meshes; three
of its four checks fail on the v0.0.29 converter).

**Other maps.** In the base game, 112 placed meshes have a root rotation or
offset. Among maps converted so far, the root *rotation* affects Balmora Temple,
Tharys Ancestral Tomb (same Velothi kit), seven Seyda Neen interiors with
`in_nord_fireplace_01` (180-degree root yaw) and one `furn_pathspear_03` in
Balmora. Those maps need rebuilding with the repaired converter. Root offsets
such as the crate's were already handled correctly.

**Still to verify.** Normal walking and collision across the whole lower level,
the remaining door-frame seam, the other affected maps, and owner acceptance.

## RC2 entrance-level traversal report: 6 October 2026

Status: **major, open geometry and collision defect**. The player reports that
they cannot cross the broken entrance area and also reports floating objects.
The latest original screenshot visibly shows missing entrance-level coverage at
local XYZ **997 1062 3701**, direction **S197**, pitch **4**, time **06:21** in
v0.0.29-rc2. Earlier views from the same report are local **924 1076 3701**,
SE114, pitch 5, time 05:04, and **995 1033 3701**, NW330, pitch 5, time 05:24.

The affected lower area is specifically the **entrance level**. The upper level
and stairs work and already worked in the previous version; retain them as
intact controls. The player accepts carrying this known issue on the roadmap
for v0.0.29. This is a release-scope decision, not repair acceptance. Missing
wall dimensions is a reported hypothesis; the cause remains unproven.

Do not describe this as cosmetic: blocked traversal and collision holes remain
part of the open report. Normal collision/route replay and exact face/reference
bindings are still required for repair verification.

## Packaged interior plane audit: 2026-10-06T20:11:15+03:00

Read-only check of the sealed v0.0.29-rc1 package completed: all 58 gameplay
interiors, 880,244 faces. Every scanned map matched its packaged SHA-256.
There were 44 faces with vertex-to-stored-plane distance above 0.05 BSP units:

| Map | Flagged faces | Maximum distance |
| --- | ---: | ---: |
| Balmora Temple | 13 | 31.4870 |
| Prison ship interior | 23 | 0.72159 |
| Census Office | 3 | 0.93969 |
| Tradehouse | 4 | 0.93969 |
| Warehouse | 1 | 0.93969 |

The remaining 53 interiors had no failures of this specific threshold check.
The auxiliary character plane was checked separately: 464 faces, no failures.
All 2,723 packaged map names were accounted for: 58 interiors, 2,664 exterior
maps outside this audit scope and one separately scanned auxiliary map. Two
optional section names were absent from the package and were recorded as such.

These additional 31 flagged faces are import-risk findings, not proof of the
same root cause, visible holes or broken collision. Passing this plane check
does not certify an entire interior. No map was modified. The repair remains
limited to Balmora Temple. Future imports should retain this check alongside
source coverage, native rendering and ordinary collision-route validation.

## Temple plane defect and import risk: 2026-10-06T20:06:10+03:00

Affected evidence: v0.0.29-rc1. This is a confirmed exported-face-plane defect,
with a Temple-only repair candidate; the complete Temple geometry/collision
failure remains open. First shipped fixed version: none.

Merged polygons can begin with three nearly collinear vertices. The old
placement exporter normalizes their cross product to construct the BSP plane,
even though the merge stage carries a stable source normal. Tiny coordinate
errors then produce a plane that does not contain the polygon's other vertices.
The incorrect plane is already in the BSP before the engine loads it. Preserved
mesh counts, bounds and triangle totals do not establish correct face planes.

The sealed Temple has 13 faces with vertex-to-plane error above 0.05 BSP units.
Examples: model 38 / face 7961 reaches 31.487 units, model 39 / face 8189 reaches
27.110, and model 95 / face 23838 reaches 7.587. Replaying the exact cached source
triangles through the production merge/split and old placement reproduces the
bad planes in those models. This confirms a correctness failure; no speed or
memory optimization has been demonstrated. Those 13 faces represent less than
0.6% of total face area, so they cannot yet be claimed to explain every gap.

The candidate uses a whole-polygon area normal and validates every vertex
against its plane, without projecting or discarding source geometry. It rejects
nonfinite, degenerate or nonplanar output. The production room builder opts in
only for explicit map identity `bmtemple`. Focused validation passed 23 checks;
all 13 measured errors disappeared in exact polygon replay, with worst float32
error 0.000503 units across 35,190 inline faces. Non-Temple output controls remain
byte-identical. A rebuilt-map native comparison and ordinary collision route
are still required; this is not a full Temple repair acceptance.

For future imports, audit original placements/triangles, merged polygons,
serialized face planes and native visibility/collision separately. Validate
finite normalized planes, whole-polygon area and maximum vertex-plane distance
after serialization; retain face/model/reference identities and input hashes.
Include near-collinear leading edges, large offsets, transforms, UV splits and
intact control rooms in regression coverage. A read-only packaged-interior
audit is in progress. Do not apply the Temple repair to other areas on the
strength of this finding alone. See the [Temple issue](BALMORA-TEMPLE-GEOMETRY-29.md).

## Native and loader discriminators: 2026-10-06T18:49:45+03:00

The original RC1 engine and unchanged Temple BSP reproduced missing lower-room
regions near local 931,1052,3701 and 1063,1048,3700 in FS-UAE. Noclip placement,
rounded positions and quantized view angles make this a rendering diagnostic;
ordinary walking collision acceptance was not established. The intact upper
route was not revisited in this bounded run. Some areas remain intact as the
owner reported. No Temple repair has been implemented or delivered.

All 185 inline entity origins fit the transport range and touch the same empty
world leaf at the checked poses. The actual loader passed address/undefined
behavior sanitizer checks. All 35,242 render faces reference planes 0 through
14,622; signed plane overflow is not this artifact's cause. Higher plane totals
include collision planes. Structural export preservation alone does not prove
correct runtime display or collision.

Changing surface ordering/culling did not restore the missing structures.
Logged use was 6,719 of 12,289 surfaces and 13,503 of 24,576 edges, without
observed exhaustion. At the rounded primary pose, noclip-off was refused as
inside solid; later movement remained noclip and is excluded from walking
evidence. Next useful check is placement-specific brush submission and face
rejection compared with the intact upper control. Cause remains unknown.

## Original mesh completeness: 2026-10-06T15:03:42+00:00

All 31 audited structural NIF model sources used by 62 architectural placements
contain 12,913 visible triangles; exported packets retain exactly 12,913.
Current exporter output matches every cached packet byte-for-byte, with bounds
and material face ranges intact. The audit found no hidden-shape or strip
triangles; 1,548 collision-ancestry triangles are excluded from visual export
under the current policy. That exclusion is not proof that runtime collision is
correct. Combined with the earlier packet/BSP area and bounds check, no broad
structural import loss or placement offset is demonstrated for this subset.

Investigate face winding, BSP leaf/visibility membership, runtime culling and
collision at the damaged lower locations versus the intact upper control.
No cause or fix is proven. Latest additional pose: local931,1052,3701,
SE131/pitch8 at game10:21. Geometry edits remain limited to Balmora Temple.

## Structural packet/BSP comparison: 2026-10-06T14:46:55+00:00

A read-only comparison of all 62 architectural instances in the exact packaged
Temple found no missing architectural entity, surface-area differences below
0.1%, and transformed bounds agreeing within 0.000031 runtime units. This checks
the exported MWG geometry against sealed BSP polygons after applying the actual
entity `angles` field. An initial diagnostic read only `angle`; that comparison
was corrected before attributing any placement error to the game.

This narrows the loss search: there is no evidence of large architectural offsets
or widespread surface collapse in the packet-to-BSP stages. Original NIF export
completeness, normals/winding, runtime visibility/culling and collision still need
independent checks. Preserve the damaged lower areas and intact upper/stair route
as separate controls. An omitted rope placement does not identify a visible strip.
Cause remains unproven; no Temple repair or fixed version is claimed. Geometry
changes, once justified, remain explicitly limited to Balmora Temple.

## Lower-section follow-ups and pipeline regression requirement: 2026-10-06T14:01:20+00:00

Additional owner RC1 captures show thin horizontal remnants and open lower
structures at local1016,1033,3701 (SW204/pitch13,08:56), 1061,1056,3700
(E072/pitch31,09:24), and1062,888,3697 (SW207/pitch46,09:50).
The last view shows a largely open damaged section. The earlier correction
still applies: other sections, including the tested upper route/stairs, are intact.

Curved/hollow structural conversion and offset handling are owner-suggested
diagnostic leads, not confirmed causes. Identify each apparent strip's source
piece before labeling it a collapsed wall; a retained trim/rope can coexist
with an omitted wall. Match source placement IDs, surfaces and collision.

The eventual repair must add a reusable interior-pipeline regression: retain
selected structural references, transformed surface coverage and matching
collision at broken and intact control locations. Shift a synthetic interior
with its door arrivals and collision, retaining equivalent geometry across
large positive/negative local offsets. Exercise curved/hollow pieces and
post-assembly processing. Stage-specific counts and unexplained losses must
fail validation rather than accepting a successful compiler exit alone.
These regression requirements are recorded; no repair is claimed yet.

## Scope correction and pipeline audit: 2026-10-06T13:57:39+00:00

The owner clarified that the damage is **partial**, not a wholly absent interior:
some Temple areas retain walls and ceilings. The upper area and the stairs
leading to it looked usable in the latest RC1 playtest. Preserve this intact
route as a regression control while repairing the broken sections.

Additional evidence: thin horizontal strips where walls should be, local
1033,885,3701, NE050/pitch7 at06:50; missing ceiling sections near
1035,882,3701, NE046/pitch-49 at07:13. The owner-approved upper-area control is
near1170,1036,3700, S183/pitch-5 at08:29. HUD readings are approximate integer
poses. Seven screenshots now support the issue; captures remain private.

Classification: **major interior geometry/collision failure** with conversion/
BSP loss suspected. Do not reduce this to a missing-texture issue. Conversely,
thin remnants do not prove that the renderer is faithfully drawing complete
input: conversion, assembly and runtime visibility still need comparison.

The historical distance-filter defect is documented in
[Interior coordinate culling](../INTERIOR_COORDINATE_CULLING.md). Current
`prepare_area.build_room` passes explicit exported reference IDs and retains
dressing for Balmora, so the old default736-unit selector is not sufficient
evidence of this RC1 cause. Verify the actual packaged lineage and later stages.
Llarara Omayn259838 appears in the earlier [ground-contact findings](../NPC_GROUND_CONTACT.md);
that is a separate corroborating investigation lead, not proof of a shared cause.

Required first diagnostic: original Temple reference IDs and source triangles,
selected/exported intermediate geometry, base `.map`/BSP, assembled mesh BSP,
post-processing and sealed RC1 BSP. This pipeline compiles the `.map` enclosure
first and then appends original meshes, so architectural triangles must not be
counted as lost merely because the intermediate `.map` contains only enclosure
brushes. Compare actual geometry and collision coverage at both damaged and
intact positions. No fix or native repair acceptance is established yet.

Updated 2026-10-06T13:53:32+00:00. **Open, major geometry/collision defect; final-release blocker.**

| Field | Evidence |
| --- | --- |
| Reported build / environment | v0.0.29-rc1 private playtest / WinUAE |
| First report date | 6 October 2026 |
| Location | Balmora, Temple interior; configured map `bmtemple` |
| Primary owner-reported local XYZ | 1063, 1048, 3700 |
| Direction / pitch / game time | E 076 / 65 / approximately 05:28 |
| Additional screenshot positions | 1072,1063,3701 at 05:22; 975,1026,3701 at 05:50; 1071,870,3700 at 06:11 |
| Coordinate qualification | Local HUD coordinates; no exterior global coordinate. Preserve the typed primary position as reported; pixel transcription is not a higher-precision pose. |
| Symptoms | Multiple absent/broken wall, floor and connecting structural surfaces; owner can accidentally pass through gaps |
| Cause / introducing version | Unknown; no last-known-good comparison established |
| Fixed / first shipped fixed version | N / none |
| Repair candidate | Not yet established |

## Reproduction

Enter Balmora Temple in RC1. Walk the interior toward the primary position and
the additional locations above, turn through the reported views and look up/down
across the connecting surfaces. Several black/open gaps appear where room walls,
floors or adjoining structures should be. The owner reports ordinary movement
can cross the missing geometry. Four retained private captures document the
progression from one suspected missing wall to multiple wall/floor failures.
An independent FS-UAE-in-Docker reproduction remains pending.

Expected: complete authored room boundaries and usable connected floors, with
correct visible geometry and collision. A visual patch without restored collision
does not satisfy this report; invisible blocking planes alone do not satisfy it.

## Investigation and repair plan

Bind the configured Temple entry to the exact packaged BSP and source placements.
Compare source identity/transform, conversion output, packaged model/face counts,
render visibility and collision hull coverage around each reported position.
Distinguish omitted conversion/packaging from culling, face orientation, BSP
partitioning or runtime geometry failure. These are hypotheses, not established
causes. A historical Temple memory warning is not proof of geometry omission.
Do not simplify or remove required architecture as a budget workaround.

Correct the established stage, rebuild an isolated candidate, then test actual
FS-UAE gameplay inside Docker with normal walking and looking, torch off/on,
both passage directions, entry/exit and save/reload. Retain identical-pose before/
after evidence and collision probes for the reported gaps. Record source/packaged
coverage and RAM costs. Update the exact first fixed version only after the
repair is packaged and verified; keep RC1 and its evidence immutable.

## Related lighting observation

The owner twice reports carried torches work noticeably better indoors than
outdoors, including the Temple. Compare near/far surface and NPC response at
fixed radius/strength/time without assuming this causes missing architecture.
Track the surface-strength work in [torch notes](../TORCH.md) separately from
this geometry/collision defect.

See [issue index](../BUGS.md), [RC1 tracker](../BUGS-v0.0.29-RC1.md),
[coverage](../ASSET_COVERAGE.md) and [roadmap](../ROADMAP.md).
