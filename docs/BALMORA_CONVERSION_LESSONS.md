# Balmora conversion: problems, causes, implications and resolutions

## Geometry import validation update: 2026-10-06T20:06:10+03:00

The RC1 Temple investigation confirmed that nearly collinear leading vertices
can produce incorrect exported BSP planes despite retained source triangles.
Use [the geometry import checks](MESH_TIPS_AND_TRICKS.md) and retain
[the Temple regression](bugs/BALMORA-TEMPLE-GEOMETRY-29.md) for future imports.
The repair candidate is Temple-only; the wider interior audit is read-only.

Working reference for v0.0.24-rc1, 30 September 2026. This consolidates the
dev1–dev5 findings and current RC1 investigation. Historical results apply to
the tested build and route; they do not close a later report automatically.

The complete owner Parts 1–7 coordinate checklist and current acceptance gates
are in [the RC1 investigation](INVESTIGATION-v0.0.24-rc1.md). Keep suspected
causes separate from measured ones, and record native verification separately
from conversion or host-test success.

## 1. Buildings lost their facades while decoration remained

**Problem:** Balmora appeared to contain floating doors, signs and windows.

**Cause:** the generic building triangle target reduced open material components
too aggressively. Original architectural geometry existed in the source and
exported archive, but simplification collapsed parts of the visible shell.

**Implications:** retained reference counts and valid BSPs cannot prove visual
coverage. A perfectly placed reference can still have a damaged mesh. Renderer
overflow was investigated separately and did not explain the isolated failure.

**Resolution:** retain architectural/manufactured geometry and control resident
cost through bounded sub-cells. Match source/candidate views and inspect facade,
roof and boundary coverage. Keep organic-object reduction separately bounded.
The owner subsequently accepted the exteriors in dev2/dev3. See the measured
single-building comparison in [dev2 findings](INVESTIGATION-v0.0.24-dev2.md).

## 2. Hollow passages became solid collision

**Problem:** a visible underpass, stair opening or room could be impassable.

**Cause:** enclosing connected concave/hollow geometry with convex volumes can
fill the space meant for the player. In narrow openings, approximate expansion
by the standing box can also intrude beyond the correct edge bevels.

**Implications:** a blockage under an arch does not establish a player-height
error. Changing the camera or shrinking the player can conceal a conversion
error while changing movement elsewhere. Visual and collision geometry need
independent inspection.

**Resolution:** preserve hollow collision as thin surface prisms; use complete
standing-box convex sums for the selected open architectural shells. Keep
converted collision within region budgets. Validate actual normal walking in
both directions, including adjacent walls and landings. Earlier bridge/temple
and b17 routes passed targeted checks; new RC1 owner coordinates retain their
own gates. See [mesh guidance](MESH_TIPS_AND_TRICKS.md),
[dev4 findings](INVESTIGATION-v0.0.24-dev4.md), and the RC1 checklist.

## 3. A stair ramp fell just below the walkable-floor threshold

**Problem:** intact steps still stopped the walking player after the geometry
repair. The inspected ramp had upward normal `0.6976600289`; the engine required
`0.7`.

**Cause:** surface classification disagreed with the authored collision ramp.
Reference 19034, `ex_hlaalu_b_11`, was the actual blocking surface; the nearest
small stair reference was not enough to identify it.

**Implications:** repeated meshes repeat the failure. Movement, idle support,
stepping and arrival placement must use the same rule. This is distinct from
arch clearance and cannot be solved by a facade or texture change.

**Resolution:** centralize `AW_WALKABLE_Z = 0.69f` and match the offline audit.
Player dimensions, race/sex eyes, FOV, step height and bob remain unchanged.
The reported stairs1 route passes native ascent/descent; host tests include
idle support and rejection of a steeper surface. Do not keep lowering the
threshold for arbitrary blockers. A steep trace may be a stair's side rail,
not its walking surface. See the full reusable procedure and numerical evidence
in [Stair ramp walkability](STAIR_RAMP_WALKABILITY.md).

## 4. Far-origin interiors became nearly empty rooms

**Problem:** several guard towers compiled successfully with almost no room
geometry, despite valid original CELL records.

**Cause:** interior assembly inherited a starting-area exterior distance filter
with extent 736. Interior local coordinates need not be near zero; choosing
centre `(0,0)` did not disable that filter.

**Implications:** doors and actors may survive while their floors/walls vanish.
Successful export/compiler exits and file existence cannot establish a usable
room. Other interior families can encounter the same bug.

**Resolution:** explicitly pass every selected interior reference to assembly,
preserve its local coordinate system and DODT transforms, and compare reference
IDs through selection, export and final BSP entities. All three towers now
retain their selected geometry and load natively. See the complete four-part
finding and recurrence checklist in
[Interior coordinate culling](INTERIOR_COORDINATE_CULLING.md).

## 5. A second selection policy silently removed interior dressing

**Problem:** after correcting distance filtering, 19 rooms still omitted 99
exported references even though `selection.omitted` was empty.

**Cause:** a legacy post-selection name filter removed flora and other dressing.
Its removals were not recorded in that selection report.

**Implications:** one empty omission list is not a complete coverage audit.
Content selection and later assembly must agree on what was intentionally kept.

**Resolution:** Balmora's room builder sets `retain_dressing=True` after the
interior content policy has selected its references. All 43 final maps now
contain all 3,408 selected geometry IDs exactly once. All 43 pass native
loading/rendering smoke checks; full traversal remains a separate gate.

## 6. Truncated intermediate caches interrupted rebuilding

**Problem:** four interior `scenery.mwpak` caches contained short indexed payloads.

**Cause:** truncation is verified; the event that truncated those intermediate
files is not established. Do not attribute it to the original game assets.

**Implications:** cached files must not be trusted solely because an index or
earlier successful build exists. Padding data or bypassing checks can produce
subtle mesh corruption.

**Resolution:** preserve failed evidence, re-export the affected caches from the
owned source, and verify every indexed payload's length and SHA-256. Those checks
now pass for all 43 rooms. Keep integrity failures fatal and rebuild dependent
outputs before packaging.

## 7. NPC names were incompatible with BSP entity quoting

**Problem:** the population pass stopped at Edd "Fast Eddie" Theman's name.

**Cause:** Quake's quoted entity strings cannot safely contain the source name's
embedded double quotes through the existing strict serializer.

**Implications:** globally weakening path/key validation would introduce unrelated
parsing problems. Human display text and identifiers need separate treatment.

**Resolution:** normalize human names/subtitles to a safe display representation
using apostrophes and collapsed whitespace; retain original text in reports.
Strict entity/path checks remain. Population now completes: 93 placements,
83 actor models, 80 living voice sets and three authored-dead actors. Dead
actors do not receive living greetings. Native loading is verified; typical
greetings do not imply full quests, services, schedules or combat behavior.

## 8. Names, Talk prompts and activation selected different targets

**Problem:** Talk could appear off the crosshair, or a visible name lacked the
corresponding action. Strider cooldowns also conflicted with travel availability.

**Cause:** direct-ray and facing-cone rules differed between label, hint and
activation; earlier changes aligned only some of these paths.

**Implications:** making a hint more permissive can create another inconsistency.
Target identity, reach, occlusion, voice eligibility and cooldown must agree.

**Resolution:** the RC1 candidate uses the same direct 72-unit targeting policy
for ordinary NPC names/hints/manual greetings and consistent driver queries.
Host checks pass for crosshair, occlusion, cooldown and Strider cases. Native Caius/Galbedir manual greeting and Selvil travel checks pass. Inspect both aiming on the character and
aiming just beside it; do not accept a screenshot of the name alone.

## 9. Door catalogues existed without playable destination interiors

**Problem:** some doors appeared unnamed or unreachable; dev5 had exterior
destination labels but no Balmora interiors to enter.

**Cause:** all 70 source exterior doors were already catalogued. Individual
missing prompts require targeting, geometry and occlusion inspection; absent
door records must not be assumed from the symptom. The destination maps were
separately unimplemented.

**Implications:** mapping, physical approach, activation, arrival and return are
five distinct gates. A catalogue count cannot certify access.

**Resolution:** RC1 includes 43 source destination interiors and per-map door
banks with original destination names/transforms and authored door sounds.
The two reported guild-door arches are physically approachable in the native
candidate. All 70 exterior entrance round trips and both additional same-room Fighters
Guild links pass native checks. Keep visual reach and target acquisition
separate from catalogue coverage.

## 10. Gold text lost character distinctions

**Problem:** previous gold glyphs lost upper detail in `o`/`s`; the owner then
reported ambiguous `e`/`c` and uppercase `H` resembling lowercase `h`.

**Cause:** the earlier small rasterization/packing problem and the current
glyph-design distinctions are separate issues. Do not assume one filler fixes
every glyph or every font.

**Implications:** changing advances or line metrics can break existing layouts.
Book text and console text are separate assets.

**Resolution:** retain packing/advance regression checks. RC1 adds a readable
gold variant limited to `e` and `H`, preserving metrics and the selectable
original ink. Native 12/14/16-pixel comparisons pass; check full words such as
"office" and "Hors", not isolated enlarged pixels alone.

## 11. Ground patches lacked the expected paving

**Problem:** the owner reports ten ground views in Parts 1, 2, 5, 6, 8, 9, 10 and the follow-up.

**Cause:** source default material tiles are identified in the conversion audit;
multiple camera reports can refer to the same tile. Texture absence must still
be distinguished from missing geometry or incorrect UVs.

**Implications:** replacing every default tile would alter unrelated terrain.

**Resolution:** RC1 has narrow, checked tile repairs using the known paving
material 34 where the neighbouring pavement uses it; the western rock/scrub
patch uses matching material 14 instead. The earlier dev5 repair is retained.
Repairs validate the expected
old material before substitution. Native repaired views are captured, including both sides of the canal patches.
Camera coordinates and tile coordinates are recorded separately.

## 12. The dock guard circled or faced the wrong direction at the door

**Problem:** the final route could circle an auxiliary path-grid node; the owner
also wants a post left of the door, back to the wall, facing the docks.

**Cause:** a graph node beyond the requested stop was treated as mandatory.
Later, route completion did not establish the requested final facing.

**Implications:** navigation completion, failure and final idle pose must be
distinct states. Repeatedly steering a completed actor can reintroduce rotation.

**Resolution:** bounded final-leg movement can finish at the actual destination.
The RC1 post candidate targets `(299,-202,31.5)` and holds converted actor yaw
225 (world-facing yaw 315) after successful completion. A native check reaches
`(302,-199,31)` and holds that facing through the next observation, with a clean
404-frame run. Host checks verify no restart or premature facing change. Full
natural opening acceptance is still required.

## Applying these lessons to the next region

1. Record the symptom, build, exact XYZ/yaw/pitch and movement mode. Preserve
   uncertain signs or possible duplicates rather than silently editing reports.
2. Identify the source CELL/reference/model and compare selection, exported
   geometry, visible output and collision separately.
3. Record the confirmed cause or explicitly say it remains unknown. Keep source
   defects, conversion defects, runtime rules and test-harness failures distinct.
4. Apply the smallest reusable correction at the relevant pipeline stage. Keep
   accepted profiles intact, especially the dev3 Balmora Strider.
5. Verify reference coverage, format budgets and payload hashes; then verify
   ordinary movement, both directions of doors, target prompts and native images.
   Stage with diagnostics only; noclip movement cannot prove walkability.
6. Record the fix, measured result and remaining limits. Keep failed attempts
   as evidence. Repeat the relevant accepted routes after shared-policy changes.

Balmora's comparatively good frame rate does not establish polygon count as the
only bottleneck. The ship investigation measured substantial collision work;
rendering, UI queries, actor caches and resident geometry also matter. Preserve
the accepted frozen-frame Loading... box while measuring sub-cell changes.
The whole-map high/low polygon-density study remains a later-version roadmap
item. See [profiling](PROFILING.md), [dev5 investigation](INVESTIGATION-v0.0.24-dev5.md),
[conversion recipes](CONVERSION_RECIPES.md) and [roadmap](ROADMAP.md).

## 13. A directory-mounted build hid an invalid Amiga filename

**Problem:** HDF packing failed on the Hlaalu Council entrance catalogue.

**Cause:** `scene-doors-bmhlaalucouncil.txt` has 31 characters; legacy OFS/FFS
limits a filename component to 30 bytes. Host directory mounts accepted it.

**Implications:** successful emulator tests through host mounts cannot certify
the final disk filesystem or paths. Similar long destination slugs recur.

**Resolution:** emit shorter `doors-<map>.txt` banks, use them in the runtime,
retain legacy-read fallback, and reject oversized components/case collisions
before image construction. Rebuild and independently read back the final HDF.

The packed-image scripted check exposed command ordering in quickload: a later
queued teleport could overtake the deferred saved-map load and cancel restoration.
`AW_SaveRead` now inserts the map command before subsequent console commands,
matching immediate scene transitions. This does not change save bytes or relax
validation. The final packed-image check covers restore before further travel.
