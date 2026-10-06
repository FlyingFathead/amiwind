# Next milestone: dock and Census Office character creation

**Status:** bounded implementation present in v0.0.21-dev1; acceptance remains
in progress. See [checkpoint scope](RELEASE-v0.0.21-dev1.md). The audit below
remains the behavioral target. Numeric journal indices, globals and inventory
counts are distinct from the intro UI stage; no universal linear quest enum.
NPCs retain individual local state and timers. A general script/condition
interpreter and full dialogue-topic state remain future work.
The owner chose maintenance first on 28 September 2026, then this work. Keep
[the intermittent freezes](BUGS.md) open throughout implementation and testing.

## Original source audit

Inspected the owned base Morrowind.esm scripts and object/reference records.
Original dialogue, models and raw script extracts remain private conversion data.

| Stage | Original script / record | Required behavior |
| --- | --- | --- |
| Arrival | CharGen / CharGenWalkNPC | Preserve name entry, escort and authored control restrictions; exit via the real hatch link. |
| Dock guard | CharGenRaceNPC | Walk to the plank, approach threshold 108 source units, disable movement, play CharGenDock1, wait for speech, then open race selection. |
| Accepted appearance | CharGenRaceNPC | After the menu and 1.5-second delay, play CharGenDock2; wait for speech, restore movement and walk toward the office. CharGenDock3 is the later nearby reminder. |
| Census registration | CharGenClassNPC | Socucius Ergalla greets the player, then class selection, birthsign and stat review with the authored voice-completion gates. |
| Papers | CharGen StatsSheet / CharGenDoorGuardTalker | Expose the papers only after review; possession permits the hall guard to unlock passage. |
| Courtyard / captain | CharGenDoorEnterCaptain / CharGenDialogueMessage | Preserve the ring check and Sellus Gravius conversation/release conditions. |
| Completion | CharGenDoorExitCaptain | Check the required package/duties state before setting CharGenState to -1 and completing release. |

The dock guard starts at an authored placement and AITravel targets
(-8914,-73093,126) before the plank, then (-9944,-72481,126) near the office.
These are **source-world coordinates**, not the runtime's quarter-scale coordinates.
The exterior path grids store cell-local points: add cell coordinates times 8192
before subtracting the runtime centre and scaling. The two named Seyda Neen grids
have 95 and 11 nodes; do not mistake them for a single interior coordinate system.

### Authored barriers

The source has 22 exterior placements of ACTI `CharGenCollision - extra`,
using `EditorMarker_box_01.NIF` and `CharGenDisable`. Its collision node has local
bounds (-128,-128,-32)..(128,128,32). References include rotations around multiple
axes; an unrotated box or arbitrary fence would not reproduce their shape.
The script keeps them while CharGenState is nonnegative and disables them after
completion. This confirms authored invisible blockers exist; it does not prove
these boxes alone enclose every route. Audit the visible fence/ship/dock meshes
and every exit as well. Convert blockers as collision only, never editor artwork.

Do not remove the barriers immediately on hatch exit or race confirmation.
The class NPC's script separately disables the ship and its listed attachments
and actors during registration. Preserve those source identities, hide the full
assembly together and release unused interior resources safely. Debug scene
travel remains independent of story progression.

### Persistent rule: opening access is conditional world state

The intended opening route is ship deck -> plank -> pier -> Census Office ->
enclosed courtyard -> captain -> release. Before the relevant conditions are
satisfied, the player must be able to follow that route but must not walk off
its sides into the sea or town, or leave the courtyard to bypass registration.
This is an acceptance condition for the entire sequence, not just the plank.

Model this using the original independent facts and reference identities:

| Source condition | Effect and lifetime |
| --- | --- |
| `CharGenState >= 0` | `CharGenDisable` leaves its collision references enabled. Hatch exit, race confirmation and entering another cell do not remove them. |
| `CharGenState < 0` | `CharGenDisable` disables those references. The completed state must survive save/load and later visits. |
| Dock guard local state and speech completion | Stop the player for race selection, then permit following the guard to the office. This does not complete registration. |
| Class NPC local state | Hide the specifically listed ship assembly and actors during registration; this is separate from releasing the invisible barriers. |
| Papers, ring and duties conditions | Gate the hall/captain/release interactions using their source item counts and journal/global conditions, not merely the current map or proximity to a door. |
| Original input-control scripts | Jumping starts disabled; `CharGenFatigueBarrel` enables it when approached in the courtyard. Keep this distinct from barrier removal. Fighting is enabled by the hall guard accepting papers; drawing and punching use that permission. The current adapter still keeps jumping disabled until release; original courtyard proximity enablement remains to implement. |

The UI stage coordinates implemented menus; it is not a replacement for globals,
journal indices, actor script locals, inventory or reference enable state.
Keep those facts separate when extending quests, transitions, NPC actions and
save/load. A source barrier placement is an oriented collision shape in world
space, not a guessed two-dimensional allowed area. Validate deck/plank/pier
sideways movement, visible railings, courtyard enclosure and later release as
well as forward travel. Preserve both passage and containment.

The dev1 blocker conversion applied compound rotations in the wrong order.
For these placed objects the corrected column-vector transform is
`Rx(-x) @ Ry(-y) @ Rz(-z)`, followed by scale/translation into the runtime frame.
The regression test must use combined rotations: yaw-only fixtures cannot
detect this error. Compare against OpenMW `Misc::Convert::makeOsgQuat` and its
direct scene-node rotation, accounting for OSG quaternion multiplication order.

## Deliverable sequence

1. Dock actor route and original speech, with explicit states for walking,
   speaking, choosing appearance and continuing. Pause timers in menus.
2. Race/appearance screen with an actual rotating head preview, race, sex,
   face and hair controls; keyboard and mouse; clear accept/cancel behavior.
   Race changes must rebuild valid head/hair choices and reset incompatible
   selections. Preview only one bounded appearance at a time and release replaced
   preview resources. Do not replace it with a text-only race picker.
3. Convert the required Census and Excise Office interior rooms and door links
   from the owned data. Include Socucius Ergalla, the hall guard and Sellus Gravius,
   their original placements, appearances and dialogue. Existing converted NPC
   models are inputs, not proof that their interiors or scripts work.
4. Class selection, birthsign and complete stat review, then papers, ring and
   captain checks. Preserve the order; do not move class/birthsign onto the dock
   merely to avoid building the office. Start with class-list selection, retaining
   quiz/custom-class work as explicit follow-ups if not yet implemented.
5. Make this same milestone saveable and loadable: persist the completed character
   attributes and story state through [the save implementation](SAVEGAME_PLAN.md),
   with player-adjustable retention of the last X autosave snapshots.
   Do not expose ordinary Save as complete while required state is discarded.

## Character record and OpenMW comparison

OpenMW 0.49.0 was used as a behavior/format reference, not copied as a native UI.
Its race dialog provides head rotation and distinct race, sex, head and hair
selections. Its body-part enumeration checks playable skin parts, part category,
sex, race and first-person exclusions. Follow the source flags and explicitly
check unusual/beast race combinations; the existing humanoid converter rejects
beast skeletons and cannot silently stand in for a complete creator.

The owned playable RACE records contain the eight attributes as interleaved
male/female pairs. OpenMW's RADT accessor confirms that indexing. Its player
rebuild uses race/sex values, then selected-class bonuses and birthsign powers.
Keep base values, active modifiers and current resources distinct.
Save name, stable race/head/hair/class/birthsign IDs, sex, level, all eight
attributes and skills; do not save only the displayed numbers or selector indices.
The current Nord hands are not proof that selected-race first-person appearance
has been implemented. Audit those assets as a separate acceptance item.

Race-based height is also original data. The complete male/female multiplier
table and its source are recorded in
[player movement](PLAYER_MOVEMENT.md#original-race-based-heights). Dev2 exports
those proportions for the first-person eye and applies the confirmed race/sex,
replacing the fixed Nord camera. This does not implement race-specific hands or
change the shared physical collision box.

## Acceptance before the next playable

- New Game through hatch, dock greeting, race choice and office entry without
  debug teleporting; menu cancellation/re-entry and speech timing remain correct.
- Authored barriers block unintended escapes during creation and are removed
  at the correct completion state; ordinary town/demo play stays available.
- Head rotation, all valid race/sex/face/hair combinations, switching repeatedly,
  and a measured memory plateau; no stale entity/model/preview pointers.
- Interior entry/exit, all three office NPCs, class/birthsign/stat review, papers,
  ring and captain completion; ship removal is source-driven and reversible via
  independent debug travel.
- Attribute values compared with the same selections in the source game/OpenMW;
  saved/reloaded selections and values match exactly.
- Repeat the ship-exit and dock/menu-idle cases on FS-UAE 3.1.66; record executable
  and HDF hashes. A passing character-creation run does not close the freeze report.

## References inspected

Owned Morrowind.esm: SCPT, ACTI, NPC_, CELL, PGRD and RACE records named above;
owned collision NIF. Raw extracts and fingerprints accompany private evidence.

- [OpenMW race dialog](https://github.com/OpenMW/openmw/blob/openmw-0.49.0/apps/openmw/mwgui/race.cpp)
- [Character-creation coordinator](https://github.com/OpenMW/openmw/blob/openmw-0.49.0/apps/openmw/mwgui/charactercreation.cpp)
- [Player stat construction](https://github.com/OpenMW/openmw/blob/openmw-0.49.0/apps/openmw/mwmechanics/mechanicsmanagerimp.cpp)
- [RACE accessor](https://github.com/OpenMW/openmw/blob/openmw-0.49.0/components/esm3/loadrace.cpp)

## Class mechanics reference checklist

Owner-supplied UESP Classes text is linked in REFERENCES.md. The existing
starting-stat builder uses the owned RACE/CLAS/SKIL records: two favored
attributes gain 10; skills start at 5, with an additional 25 for major or 10 for
minor, then race bonuses and 5 for matching specialization. Preserve the
interleaved minor/major CLAS layout. Twenty-one playable predefined classes,
NPC-only classes and future custom classes are distinct sets.

Future progression needs specialization experience factor0.8, major0.75,
minor1.0 and miscellaneous1.25, checked against game settings/OpenMW before
implementation. Only major/minor increases contribute to character leveling.
Keep skill experience, skill governing attributes and character level progress
separate. Quiz and custom-class creation remain pending; custom classes require
five distinct major and five distinct minor skills, two favored attributes and
one specialization. Choice review must permit changes until final confirmation.
This reference does not claim progression, class quiz or custom classes exist.

Architectural ACTI records may carry tutorial scripts while still providing real
walls and floors. `chargen stuff room` (reference172861) is one such room section:
its geometry/collision is permanent, even when its tutorial stops after release.
Do not classify all scripted activators as dispensable scenery or editor markers.


### Independent action and container facts (v0.0.21-dev3)

`CharGenDoorGuardTalker` enables fighting when it unlocks the hall after checking
papers. `CharGenDoorExit` and `CharGenFatigueBarrel` contain later safety enables.
The runtime uses the persisted hall acceptance for drawing/punching permission;
`CharGenState` still controls the outside enclosure. Release/demo allows both
attack and jump, while readers and character menus temporarily consume controls.
Future status effects add independent restrictions; clearing a tutorial gate must
not cancel Paralyze or treat Silence as a ban on physical attacks.

The courtyard barrel has a fixed Engraved Ring of Healing (`ring_keley`). Its
contents are independent of UI stage and the player's present item count.
The namespaced runtime fact `amiwind:ref:172851:ring_taken` records depletion;
atomic pickup changes that fact and inventory together. Returning, dropping or
losing the ring later cannot restock it. Full containers, loot lists, item icons
and Fargoth's keep/return dialogue remain on the roadmap.


## dev4 confirmation and review navigation

Choose is highlighted by default in character confirmation dialogs. Enter accepts;
move Left to Cancel when revising a choice. Character review has a centered title,
`Review your character (page 1/5)`, updated as pages change. During registration,
the Census front door back to the pier is locked; continue through the courtyard.

## dev5 playtest follow-up

Appearance entry selects Race; zero mouse movement preserves keyboard focus.
Race, sex, face and hair each have clickable gold left/right arrows. Label clicks
select a row; arrow clicks change that row. Choose remains the confirmation
default. The debug preset `dbg aw hors 0` uses normal catalogue rebuilding for
a male Nord, Barbarian and The Steed (source ID `Charioteer`), then applies the
post-Census quest/inventory state and starts in Seyda Neen square.

## Character UI V2: completion controls and remaining artwork

`aw_ui_mode 2` is the new default, retaining `aw_ui_mode 1` as the legacy layout.
All four selection/review pages have a visible bottom-right OK control alongside
their keyboard hints. Mouse OK and keyboard acceptance share the existing
validation/confirmation path. The appearance selector exposes OK as the next
focus after Hair. This does not alter the modal freeze/blackout flags or stop music.
Use `dbg tpscene headselection` for a fresh test entry; see DEBUG_OVERLAYS.md for
its unsaved-progress reset and prerequisites.

Missing components requested on 5 October 2026:

- Class illustrations: study the original class-selection assets and record-to-
  texture mapping, then show the matching owned-converted illustration in V2.
  Do not guess an image association or bundle proprietary art in public source.
  Retain a readable text-only fallback and bounded memory/draw cost when art is
  missing. Current class selection is functional but has no illustration panel.
- Custom class creation: retain as explicit missing functionality alongside the
  existing quiz follow-up. Specify specialization, favored attributes, major/
  minor skills, validation and saved-character representation before claiming
  support. Preset class selection is not custom-class creation.

The owner confirmed appearance/head rotation and class selection work in the
preceding target build. That observation does not verify the new V2 controls,
class artwork or custom-class functionality.
