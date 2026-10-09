# rc1 Balmora checklist and investigation

30 September 2026. Dev5 source is pushed as `1e1823d`; owner publication is a prerelease.
Keep v0.0.23 as the stable release. Delivered dev5 archives are immutable.

<!-- contents start -->
## Contents

- [Owner acceptance checklist](#owner-acceptance-checklist)
- [Initial findings](#initial-findings)
- [Verification still required](#verification-still-required)
- [Additional owner direction](#additional-owner-direction)
- [Stable release presentation gate](#stable-release-presentation-gate)
- [Part 3: NPC targeting](#part-3-npc-targeting)
- [Confirmed: interior coordinate culling](#confirmed-interior-coordinate-culling)
- [Confirmed: recurring stair-ramp classification mismatch](#confirmed-recurring-stair-ramp-classification-mismatch)
- [Owner pavement reference](#owner-pavement-reference)
- [Native acceptance record](#native-acceptance-record)
- [Legacy disk filename correction](#legacy-disk-filename-correction)
- [Latest doorway and wedged-player follow-up](#latest-doorway-and-wedged-player-follow-up)

<!-- contents end -->

The [Balmora conversion lessons](BALMORA_CONVERSION_LESSONS.md) consolidate
problem, cause, implications and resolution for future regions. This file keeps
the complete coordinate checklist and remaining release acceptance gates.

## Owner acceptance checklist

Every report starts open. Conversion alone is not native traversal acceptance.
Keep the accepted Strider, 90-degree FOV, player hull/race eye heights, Shift+V
and frozen-frame Loading... presentation.

| Report | Runtime XYZ | Yaw / pitch | Status |
| --- | --- | --- | --- |
| stairs1 | -410, -586, 137 | 4 / -6 | Targeted native ascent/descent passed after geometry and slope-cutoff corrections |
| stairs2 | -561, -1135, 142 | 7 / 5 | Native ordinary ascent/descent passed; see route evidence below |
| stairs3 | -687, -620, 141 | 133 / -26 | Native ordinary ascent/descent passed; see route evidence below |
| stairs4 | -398, -578, 137 | 103 / -11 | Native ordinary ascent/descent passed; see route evidence below |
| stairs4b | -410, -212, 142 | 278 / -11 | Native ordinary ascent/descent passed; see route evidence below |
| bridge5 | 699, -1889, 59 | 183 / 0 | Native ordinary ascent/descent passed; see route evidence below |
| stairs6 | 635, -913, 58 | 6 / -9 | Native turned route ascends 58→107→139 and returns to 58; stay between authored side rails |
| stairs7 | 940, -147, 63 | 94 / -17 | Native ordinary ascent/descent passed; see route evidence below |
| stairs8 | 566, -466, 69 | 0 / -27 | Native ordinary ascent/descent passed; see route evidence below |
| archdoor1 | -445, -443, 142 | 4 / 0 | Native ordinary approach reaches the doorway; linked entrance round trip passed |
| archdoor2 | -448, -346, 142 | 1 / -1 | Native ordinary approach reaches the doorway; linked entrance round trip passed |
| jagged | 72, 185, 63 | 268 / -8 | Native ordinary ascent/descent passed; see route evidence below |
| door1 | -1296, -79, 270 | 170 / 7 | Source label present; included in all-70 native entrance/return audit |
| door2 | -1296, -129, 270 | 180 / 1 | Source label present; included in all-70 native entrance/return audit |
| door3 | -591, -446, 153 | 98 / 8 | Source label present; included in all-70 native entrance/return audit |
| door4 | -536, 41, 151 | 194 / 5 | Source label present; included in all-70 native entrance/return audit |
| door5 | -308, 55, 213 | 0 / 0 | Source label present; included in all-70 native entrance/return audit |
| ground1 | -119, 162, 92 | 76 / 59 | Source-default tile replaced by checked adjoining road34; native repaired view checked |
| ground2 | -15, 243, 79 | 200 / 47 | Source-default tile replaced by checked adjoining road34; native repaired view checked |
| stairs9 (Part 2) | 1269, -633, 133 | 3 / -5 | Native ordinary ascent/descent passed; see route evidence below |
| jagged2 (Part 2) | 1322, -331, 128 | 285 / -2 | Native ordinary ascent/descent passed; see route evidence below |
| door6 (Part 2) | 1269, -799, 133 | 358 / -3 | Source label present; included in all-70 native entrance/return audit |
| ground3 (Part 2) | 562, -1176, 49 | 320 / 44 | Source-default tile replaced by checked adjoining road34; native repaired view checked |
| archdoor3 | 888, 3, 56 | 13 / 18 | Native ordinary approach reaches the doorway; linked entrance round trip passed |
| stairs7b | 935, -146, 63 | 92 / -11 | Native ordinary ascent/descent passed; see route evidence below |
| ground4 (Part 5) | -1, 271, 76 | 219 / 24 | Same repaired tile as ground1/2; native repaired view checked |
| stairs10 (Part 6) | -685, 619, 141 | 130 / -29 | Unresolved coordinate: positive Y=619 places the reported origin inside terrain; do not claim this view passed or silently change its sign |
| ground5 (Part 6) | -1036, -901, 150 | 225 / 36 | source default tile repaired with material 14 to match three adjacent rock/scrub tiles; native repaired view checked |
| stairs11 (Part 7) | -15, -583, 71 | 196 / -3 | Native ordinary ascent/descent passed; see route evidence below |
| ground6 (Part 8) | 121, -49, 56 | 54 / 47 | Source tile (-3,-2)/(9,7): default 0 replaced by adjoining WG_road 34; native repaired view checked |
| ground7 (Part 9) | 198, 34, 62 | 230 / 34 | Same source tile (9,7) as ground6, viewed from the opposite side; native repaired view checked |
| ground8 (Part 9) | 252, 169, 60 | 68 / 27 | Source tile (-3,-2)/(10,9), checked 0-to-34 paving repair; native repaired view checked |
| ground9 (Part 10) | 547, -1182, 59 | 336 / 44 | Same source tile (-3,-3)/(12,14) as ground3; owner reference at 556,-1108 confirms road34; native repaired view checked |
| archdoor4 (Part 11) | 112, 37, 56 | 177 / 0 | Native ordinary approach reaches the doorway; linked entrance round trip passed |
| ground10 (Part 12a) | -42, 233, 83 | 23 / 67 | Same source tile (-3,-2)/(7,9) as ground1/2/4; road34 repair rebuilt; latest native view checked |
| door7 (Part 12b) | -539, 46, 218 | 180 / 13 | The Razor Hole, source reference 32816; native aimed door 49 and label confirmed; included in the 70 round trips |
| wedge1 (follow-up) | -225, 348, 131 | 13 / 78 | Open exact-location reproduction: reported origin overlaps collision; adjacent -241,348,134 retreats normally to -338,328,138; this does not prove escape from the reported wedge |

- Gold font: separate lowercase e from c; make uppercase H unmistakably uppercase.
- Audit every exterior entrance, not just the five missing-prompt reports.
- Add all 43 interior destinations in the converted region, including their placed NPCs and authored greeting voices.
- Verify exterior/interior transitions both ways and normal approaches beneath arches.
- Check the reported stairs by normal walking, plus existing dev5 accepted routes.
- Confirm all reported ground-material gaps in native views before selecting a checked repair.

## Initial findings

All 70 source exterior doors are present in the dev5 door catalogue. Missing
prompts need runtime targeting/occlusion inspection, not invented replacement doors.
New collision reports include b01/b03/b11/b16/b20/b21/b24/b26/b27/b28, balcony01/02,
bridge04 and dsteps01, beyond the individually inspected dev5 profiles.

The 43 destination interiors comprise 42 Balmora interiors and Tharys Ancestral
Tomb. Source door links find no additional interior-to-interior destinations in
this set. Keep stable map IDs by appending entries after existing ID16 (Balmora).

The original `CharGenDoorEnterCaptain` script checks ring_keley, blocks activation
until it is held, and explicitly tells the player to check the barrel to the left.
Retain this source-authored tutorial gate.

The dev5 release helper assumed `gh api --slurp`. The owner CLI rejected it before
tag/release creation. Standalone release kit r2 uses explicit JSON-array pagination;
source/game packages remain identical. Local Git fixtures and simulated legacy API
responses verify retry, pagination, conflict handling and asset integrity.

## Verification still required

Owner playtesting of the full natural introduction and city roaming remains.
The positive-Y stairs10 coordinate and exact wedge1 trap are unresolved; retain
them as RC limitations. Local route, door, room, representative NPC and font
checks are recorded below. Packaged-HDF results are in the RC release notes.
Null-audio tests can verify selection/triggering but not subjective sound quality.

## Additional owner direction

The intro dock guard should finish to the left of the Census door, back toward
the wall, facing the docks. Record the inspected route, final transform and
normal intro playtest before calling this fixed.

Each report needs broken behavior, inspected cause, applied fix and verification.
A reusable conversion/troubleshooting guide accompanies the findings.

## Stable release presentation gate

After owner approval, v0.0.24 is titled **Welcome to Balmora**. In README.md,
place release information and verified-build Balmora screenshots directly below
the AmiWind PNG, at the top of **Current state of the project**. Include exterior
and interior views where representative; do not use mockups or stale dev captures.
The release notes should use the same verified images.

## Part 3: NPC targeting

The dev5 report came from divergent direct-ray and facing-cone selectors.
RC1 uses the same 72-unit direct target for name, Talk and manual greeting.
Native Caius and Galbedir checks select the aimed actor and increment manual
greeting counts; aiming aside clears the target. Cooldowns suppress both name
and action together. Selvil remains targetable for the native travel menu.

## Confirmed: interior coordinate culling

The default exterior extent rejected whole guard-tower assemblies located far
from local zero. The Balmora builder now passes the complete selected reference
list explicitly. East / West North / West South towers now retain 85 / 79 / 78
references and pass native loading/rendering checks; route acceptance remains
separate.

The follow-up reference-ID audit also found a separate legacy dressing filter:
initially 19 of 43 rooms omitted 99 references. These were not distance
rejections, and the empty `selection.omitted` list did not expose them. Balmora
now retains the dressing already selected by its interior content policy.
The rebuilt final maps contain all 3,408 selected geometry references exactly
once, with 90 living NPC placements and three authored corpses. All indexed
source payload lengths and hashes pass after re-exporting four truncated
intermediate caches. All 43 rooms load and render in a clean 899-frame native
smoke run, with no surface or edge overflow frames. All 70 exterior entrances now complete native round trips, covering all 43
rooms. Both additional same-room Fighters Guild links also pass. Caius and
Galbedir manual greetings and Selvil travel pass native checks.

See [the complete bug/cause/implications/future-fix guide](INTERIOR_COORDINATE_CULLING.md).

## Confirmed: recurring stair-ramp classification mismatch

The authored `ex_hlaalu_b_11` ramp at source reference 19034 has upward normal
`0.6976600289`; the old `0.7` floor cutoff rejected it. RC1 uses the shared
`AW_WALKABLE_Z = 0.69f` threshold across movement, ground support and spawn
placement. The reported stairs1 route now passes targeted native ascent and
descent with the player dimensions unchanged. Similar architectural meshes
require this check in future conversions; do not treat it as an isolated
Balmora coordinate patch.

See [Stair ramp walkability](STAIR_RAMP_WALKABILITY.md) for cause, implications,
measured limits, test evidence and the repeatable diagnosis procedure. Other
checklist routes remain open until separately validated.

## Owner pavement reference

XYZ `(193,346,61)`, yaw146/pitch80: source cell `(-3,-2)`, tile `(9,10)`,
material34 `WG_road`, texture `Tx_WG_road_01.tga`. This is the owner-approved
reference for the Part8/Part9 canal-side paving repairs.

## Native acceptance record

Reference: FS-UAE, 68040/FPU/JIT, 2 MiB Chip + 16 MiB Z3, 11 MiB runtime heap;
offscreen video and null audio. Source voice selection/triggering is checked;
subjective sound quality and physical Amiga performance are not certified.

- Ordinary stair/bridge runs keep movement mode 3. Tests that used diagnostic
  noclip to stage an initial camera do not count that movement as traversal.
- The first long scripts overshot several landings and fell off the far side.
  Shorter ascent/return paths passed for stairs4/4b/7/7b and both jagged reports.
  This was test-path error, not evidence that the landing itself was blocked.
- The twisting route begins between the short stair's rails, then turns south:
  `(635,-913,58)` → `(745,-930,107)` → `(745,-1012,139)`;
  the reverse reaches `(605,-928,58)` by ordinary movement.
- The late Itan arch report reaches `(29,45,68)` from `(112,37,56)` without
  a player-size change. The nearby door carries the original Itan label.
- All 70 exterior source references activate their original destination and
  return through their paired interior entrance. The Fighters Guild also has
  two same-room links, both exercised. Roof trapdoors require aiming downward
  after walking onto the hatch. Two long test batches reached their host time
  limit after completed cases; later batches resumed the remaining cases.
- Caius and Galbedir each receive an ordinary manual greeting; the count rises
  from 0 to 1. Aiming aside clears Caius's target; after cooldown it returns.
  Selvil's native menu offers the Seyda Neen return journey.
- Original/readable gold variants were compared at 12, 14 and 16 pixels. The
  readable e/H changes retain metrics; the original remains selectable.
- Guard post check reaches `(302,-199,31)` and holds actor yaw225 toward the
  docks. This is a targeted post-race route check; the entire natural intro
  remains an owner acceptance gate.
- A normal Hors→Balmora→Caius sequence saves and restores with health55 intact.
  Earlier diagnostic bare `map` commands reset the engine player to health100,
  exceeding Hors's maximum55 and correctly failing save validation. Keep this
  fixture limitation separate from normal door/teleport behavior.

## Legacy disk filename correction

A native directory-mount run accepted `scene-doors-bmhlaalucouncil.txt`, but it
is 31 bytes and legacy Amiga FFS accepts at most 30. HDF construction rejected
it. Generated banks now use `doors-<map>.txt`; the runtime tries this first and
retains old-name fallback. Packing preflight checks every component and rejects
case-insensitive collisions. Test the actual disk image, not only host mounts.

The source alias for teleport now selects the destination area's door bank;
new Balmora interior IDs previously searched only Seyda Neen's bank.

## Latest doorway and wedged-player follow-up

The Razor Hole label at -539,46,218 is present in the RC native view (door
index 49, placed source reference 32816). The actual floor settles the player
origin to Z213. Its entrance is included in the full round-trip audit.

The reported wedge at -225,348,131 remains an exact-location reproduction
item. Native placement needs a lateral recovery to -241,348,134; from there
ordinary backward movement reaches -338,328,138, then -417,312,137. That
nearby escape is useful evidence but is not a pass for the user's original
trapped state. Do not shrink the player or remove a rock without reproducing
the approach. Keep the report in RC1's known issues.

The shortened Council bank loads natively with three links and supports a
quicksave. See [Amiga limitations](RELEASE_WORKFLOW.md#amiga-limitations) for
the filename rule and original-to-target mapping requirements.

The packed-image scripted check exposed command ordering in quickload: a later
queued teleport could overtake the deferred saved-map load and cancel restoration.
`AW_SaveRead` now inserts the map command before subsequent console commands,
matching immediate scene transitions. This does not change save bytes or relax
validation. The final packed-image check covers restore before further travel.
