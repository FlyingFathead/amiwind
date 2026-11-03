# Next milestone: dock and Census Office character creation

_Last updated with AmiWind v0.0.59-dev5 (3 November 2026)._

<!-- contents start -->
## Contents

- [Census Office registration plan (v0.0.58)](#census-office-registration-plan-v0058)
  - [Class questions and the own class (step c)](#class-questions-and-the-own-class-step-c)
- [Original source audit](#original-source-audit)
  - [Authored barriers](#authored-barriers)
  - [Persistent rule: opening access is conditional world state](#persistent-rule-opening-access-is-conditional-world-state)
- [Diagnostic race shortcut, 14 October 2026](#diagnostic-race-shortcut-14-october-2026)
- [Deliverable sequence](#deliverable-sequence)
- [Character record and OpenMW comparison](#character-record-and-openmw-comparison)
  - [View Stats on the race page (v0.0.57)](#view-stats-on-the-race-page-v0057)
- [Acceptance before the next playable](#acceptance-before-the-next-playable)
- [References inspected](#references-inspected)
- [Class mechanics reference checklist](#class-mechanics-reference-checklist)
  - [Independent action and container facts (v0.0.21-dev3)](#independent-action-and-container-facts-v0021-dev3)
- [dev4 confirmation and review navigation](#dev4-confirmation-and-review-navigation)
- [dev5 playtest follow-up](#dev5-playtest-follow-up)
- [Character UI V2: completion controls and remaining artwork](#character-ui-v2-completion-controls-and-remaining-artwork)
- [Levelling](#levelling)

<!-- contents end -->

**Status:** bounded implementation present in v0.0.21-dev1; acceptance remains
in progress. See [checkpoint scope](releases/notes/RELEASE-v0.0.21-dev1.md). The audit below
remains the behavioral target. Numeric journal indices, globals and inventory
counts are distinct from the intro UI stage; no universal linear quest enum.
NPCs retain individual local state and timers. A general script/condition
interpreter and full dialogue-topic state remain future work.
The maintainer chose maintenance first on 28 September 2026, then this work. Keep
[the intermittent freezes](BUGS.md) open throughout implementation and testing.

## Census Office registration plan (v0.0.58)

The original registers the character in this order (the CharGen scripts in
Morrowind.esm): race and appearance on the dock, then in the Census Office the
class (chosen from the list, by answering the questions, or made by the player),
the birthsign, and the review sheet. The engine already has the race page, a
class page, a birthsign page and a review page; this work completes them.

| Step | Content | Data | State |
| --- | --- | --- | --- |
| (a) | Class list: the playable classes as a scrolled list, chosen by arrows or a click; beside it the class's specialization, two favored attributes, five major and five minor skills. Review sheet: name and level, race, class and sign, the eight attributes, health, magicka and fatigue, then the skills grouped major, minor and miscellaneous. | CLAS and SKIL records in `character/catalog.awc` (unchanged) | done |
| (b) | Birthsign page: the signs as a scrolled, clickable list beside the sign's picture and its abilities, powers and spells by name and kind. The names are read once each time another sign is shown, never while drawing; a spell without a name shows its record ID. | BSGN records; spell names from `character/spells.aws` (unchanged) | done |
| (c) | The class questions: Q or the Questions button on the class page asks the ten questions; each first answer counts toward combat, each second toward magic, each third toward stealth, and the original's rule turns the three counts into a class, which the list then shows chosen. The own class: M or the Make own button sets the specialization, two different favored attributes and five major and five minor skills, all different; OK makes "Custom class". | The questions come from the install's `Morrowind.ini` through a build stage of its own (`tools/prepare_chargen.py`, `character/questions.awq`); the rule is engine code | done |

### Class questions and the own class (step c)

The original keeps the ten questions in the install's `Morrowind.ini`
(sections `[Question 1]` to `[Question 10]`), not in `Morrowind.esm`. The
builder looks for that file beside the `Data Files` folder or inside it, and
its stage depends on nothing else, so no other stage's cache key changes. When
the install has no `Morrowind.ini` (a game data folder copied on its own), the
stage writes an empty question file: the class page then shows the Questions
button greyed out and offers only the list and the own class. Greyed out means a
dotted dark overlay across the button: a dimmer text colour alone did not show,
because the menu font recolours only the brightest shade of each letter
(CHARGEN-BIRTHSIGN-REVIEW-58, seen on v0.0.58-dev5).

The debug pages (`dbg characterchange PAGE`, `dbg quickchar ...`) keep the
original order: a page asked for while another is still open replaces it, the
open one closing unchanged, and a review asked for before any name was given
asks for the name first. The review sheet never shows an empty name.

The class the answers give follows the original's rule, as OpenMW 0.51 applies
it: eight or more answers of one kind give the Warrior, Mage or Thief; otherwise
the combat count, then the magic count, then the stealth count picks the class,
some counts split further by another count. The rule is engine code, not game
data. Escape leaves the questions or the own class and returns to the list
unchanged.

The own class is held in the slot after the game's classes. Its ID carries its
whole definition (specialization, favored attributes, skills), so a save names
it like any other class and the save format is unchanged. The own class has a
fixed name, "Custom class"; typing a name is not supported yet. The questions
take memory only while they are being asked (at most 6 KB).

Not yet compared: the class each set of answers gives has not yet been checked
side by side against OpenMW 0.51 running the same answers.

Starting values follow the original's rules (checked against OpenMW 0.51):
attributes are the race's for the chosen sex, plus 10 for each favored
attribute; every skill starts at 5, plus the race's bonus, plus 5 when it is of
the class's specialization, plus 25 for a major or 10 for a minor skill. Health
is half of Strength plus Endurance; magicka is Intelligence times one plus the
race's and the sign's magicka bonuses (a tenth per point); fatigue is Strength,
Willpower, Agility and Endurance added together.

Steps (a) and (b) add no data: the pages read the catalogue the race page
already holds and the existing spell name table. The resident cost is the added
code, a few counters and about 300 bytes for the shown sign's spell names. No
builder stage changes in steps (a) and (b); step (c) adds the question stage
and the image's copy of its file, and no other stage's key changes.

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

## Diagnostic race shortcut, 14 October 2026

The new source candidate accepts dbg set race or dbg set playerrace with a
strict zero-based loaded-catalogue ID or a case-insensitive name, ignoring
spaces/underscores/hyphens. No value or list prints IDs/names and the current
race. Print the current catalogue before choosing an ID; the mapping is not a
fixed original-game enumeration.

The refined testing contract preserves gender, name, class, birthsign, level,
attributes/skills, resource maxima/current health and equipment. It validates a
temporary character through AW_CharacterSet, then changes only race and valid
head/hair choices plus live eye height; body and hands use the existing race
detection. Choose the first valid target race/gender head and hair. A same-race
request does nothing and preserves the selected head/hair. This shortcut deliberately does not reapply racial statistics.
Use normal character creation/review for a character with race-derived stats.

A live local game and permitted story/menu/death state are required for a
change; bad input and unavailable contexts are refused.
Route this diagnostic through the existing on-demand AWDC1 dbg dispatcher;
its first direct registration exceeded the resident budget and was rejected.
The corrected existing setter dispatch and unchanged registry budget pass in
twenty focused checks. New exact target/full-gate/native/package verification
remains pending. Full selected-head/hair
body composition remains a separate limitation. Fourteen final focused
preservation/command checks pass; new target/native behavior and package
acceptance remain pending. The existing
[characterchange record](bugs/PLAYER-READY-MOVEMENT-39.md) separates older menu
checks from this new shortcut.

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

### View Stats on the race page (v0.0.57)

The race page has a **View Stats** button under the four choices, between Hair
and OK: arrows up and down reach it (Race, Sex, Face, Hair, View Stats, OK),
Enter or V opens it, and the mouse clicks it. A box shows the race's base
attributes for the chosen sex, its skill bonuses and its specials, from the
same catalogue the page already reads (`character/catalog.awc`, built from the
game's RACE records: attributes, skill bonuses, powers), so nothing more is
loaded. The original's race menu lists the skill bonuses and specials (the
rule as OpenMW 0.51 shows it: `apps/openmw/mwgui/race.cpp`, updateSkills and
updateSpellPowers); the base attributes are the record's own, shown beside
them. Enter, Escape, V or a click closes the box.

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

User-supplied UESP Classes text is linked in REFERENCES.md. The existing
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

The maintainer confirmed appearance/head rotation and class selection work in the
preceding target build. That observation does not verify the new V2 controls,
class artwork or custom-class functionality.

## Levelling

Since v0.0.59 the character levels up as in the original game. The rules are the original's, written
independently; OpenMW 0.51 is the reference used to check them (`files/data-mw/scripts/omw/playerskillhandlers.lua`,
`apps/openmw/mwgui/levelupdialog.cpp`, `apps/openmw/mwmechanics/npcstats.cpp`). Every number is read from your own
master file when the image is built (`levelup/settings.txt`, written by `tools/prepare_levelup.py`); nothing of the
game is kept in the source tree.

**Skills rise with use.** Each use adds the skill's own use value (the skill record's four values, one per kind of
use) divided by the progress the skill needs for its next point: (current value + 1) x fMajorSkillBonus (0.75) for a
major skill, fMinorSkillBonus (1.0) for a minor one, fMiscSkillBonus (1.25) for the rest, and x fSpecialSkillBonus
(0.8) when the skill belongs to your class's specialization. When the progress reaches the requirement the skill
rises by one, the game's "Your ... skill increased to ..." line shows and the skill-raise sound plays. A skill at
100 gains nothing.

| Use reported today | Skill | Kind of use |
| --- | --- | --- |
| Your blow lands | the weapon's skill, Hand-to-hand for fists | successful hit |
| You block a blow | Block | successful block |
| A blow hurts you | the armour skill of the piece it lands on, Unarmored for an empty slot | hit by an opponent |
| You jump | Acrobatics | jump |
| A second of running on the ground (not sneaking) | Athletics | run one second |
| A second of swimming | Athletics | swim one second |
| A trainer's lesson | the skill trained (one point, its progress kept) | trainer |
| A persuasion in conversation (admire, intimidate, taunt, bribe) | Speechcraft | success or failure |
| A trade accepted in Barter | Mercantile | success, scaled by the share haggled (0 at the merchant's own price) |

The other uses of the original wait for their part of the game; until then `dbg levelup use SKILL [N [TYPE]]` raises
any skill by the same rules. Where each will report:

| Use | Skill | Waits for |
| --- | --- | --- |
| Casting a spell | the spell's school | spell casting (today only the test casts) |
| Using or recharging a magic item, casting on strike, making one | Enchant | casting from items, recharging, the enchanting window of your own |
| Making a potion, eating an ingredient | Alchemy | the alchemy window, eating from the inventory |
| Picking a lock, disarming a trap | Security | lockpicks and probes (doors are locked by the debug switch only) |
| Not being noticed while sneaking, picking a pocket | Sneak | the detection rule and pickpocketing |
| Haggling a better price | Mercantile | an offer you can change: every accepted trade already reports its use, scaled by the share haggled, and Barter takes the merchant's own price today, so it adds nothing yet (as in the original) |
| Repairing with a hammer | Armorer | repairing your own items (a merchant's repair trains nothing) |
| Ranged hits | Marksman | bows, crossbows and thrown weapons in combat |
| Taking fall damage | Acrobatics | fall damage |

**Level progress.** Every rise of a major or minor skill adds iLevelupMajorMult or iLevelupMinorMult (1) to the
level progress; misc skills add nothing. Every rise also counts for the skill's governing attribute
(iLevelupMajorMultAttribute, iLevelupMinorMultAttribute, iLevelupMiscMultAttriubte) and for its specialization. When
the level progress reaches iLevelupTotal (10), the game's "You should rest and meditate on what you've learned."
shows. The Stats window (P) shows the level progress as a bar under the level.

**The level-up box** opens when a rest ends with the level-up due. Until resting itself lands,
`dbg levelup rest [HOURS]` rests (moves the clock) and opens it. The box shows the level's picture (by how your
raises split over combat, magic and stealth, as the original picks it), "You have ascended to Level N", the level's
own sentence (from the install's Morrowind.ini when it has one, else the game's general line), the three gold coins,
and the eight attributes with their multipliers: x2 to x5 by the number of raises of each attribute since the last
level (iLevelUp01Mult .. iLevelUp10Mult). Click an attribute (or press 1 to 8) to place a coin on it; click it again
to take the coin back; a fourth pick replaces the last. Fewer coins are given when fewer than three attributes are
below 100. OK (or Enter) is accepted only with every coin placed. The level-up music plays when the box opens.

On OK each picked attribute rises by its multiplier (at most 100), the level rises by one, health (maximum and
current) grows by a tenth of Endurance (fLevelUpHealthEndMult, after this level's raise), the level progress drops by
iLevelupTotal (any extra carries over) and the attribute and specialization counts start again. The raised stats are
your character's own, so the combat rolls ([COMBAT.md](COMBAT.md)), fatigue and the Stats window use them at once.

**Saved.** Each skill's progress, the level progress and the counts travel with the save (save format AWS4 feature
64; older saves load with all of it at 0).

**Debug route** (`dbg levelup`, also `dbg skill progress`; saved like play):

| Command | What it does |
| --- | --- |
| `dbg levelup` | level, level progress, each attribute's raises and multiplier, every skill's value, progress and requirement |
| `dbg levelup use SKILL [N [TYPE]]` | N uses of a skill (name, its start, or 0..26) by the rules above; TYPE 0..3 the kind of use |
| `dbg levelup raise SKILL [N]` | N rises of a skill, as if by use |
| `dbg levelup check` | the level-up box, when it is due |
| `dbg levelup rest [HOURS]` | rest HOURS (default 8), then the level-up box when it is due |

As in the original, the box has no cancel: Esc does nothing, the box stays until every coin is placed and OK is
pressed. Only the console key (a debugging aid) closes it; the level-up then stays due and the next rest opens the box
again. Not yet: jail time and skill books come with those parts of the game.
