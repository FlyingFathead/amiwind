# AmiWind v0.0.66: Forward It Is

_Last updated with AmiWind v0.0.66 (16 November 2026)._

Release, 16 November 2026. Running on CHIM Engine v0.2.2. Previous release:
[v0.0.65: Reintroducing Vvardenfell](RELEASE-v0.0.65.md). Made from the twelfth development snapshot and the changes
after it; it carries all twelve snapshots: [dev1](RELEASE-v0.0.66-dev1.md), [dev2](RELEASE-v0.0.66-dev2.md),
[dev3](RELEASE-v0.0.66-dev3.md), [dev4](RELEASE-v0.0.66-dev4.md), [dev5](RELEASE-v0.0.66-dev5.md),
[dev6](RELEASE-v0.0.66-dev6.md), [dev7](RELEASE-v0.0.66-dev7.md), [dev8](RELEASE-v0.0.66-dev8.md),
[dev9](RELEASE-v0.0.66-dev9.md), [dev10](RELEASE-v0.0.66-dev10.md), [dev11](RELEASE-v0.0.66-dev11.md) and
[dev12](RELEASE-v0.0.66-dev12.md). Each snapshot's notes hold the full detail of its changes and measurements.

## What v0.0.66 is

v0.0.66 is the release that takes the game forward on the road to the two expansions and brings a large round of the
original's rules to the people and creatures of Vvardenfell. The builder now reads Tribunal and Bloodmoon with the base
game by default, and every stage, table and cache key knows which expansions are selected; the save holds the game's
changes without the fixed limits that could refuse it or drop state; the script engine is sized for the whole game with
both expansions. In play: characters cast spells, shoot bows and move at their own speeds, the dead stay dead with the
original's body clearing, the map shows the explored land with a local map and your own markers, and the opening holds
its controls and doors as the original does.

This is not the arrival of Mournhold or Solstheim. Their rooms are converted and in the image (the debug teleport reaches
them), but their outdoors, the way there in play and their quests are not in the game yet: the expansions' finished
content and the rest of the open plan move to v0.0.67 and later ([roadmap](../../ROADMAP.md); corrected for v0.0.67: the
way to Mournhold works, see [the v0.0.67 notes](RELEASE-v0.0.67.md#known-in-this-build)). The game needs 32 MB of
Fast RAM.

Most of the changes below were checked by the test suite and the gates of the snapshots; what was seen in play is under
"Seen in play". Several fixes of the last snapshots are made in source and covered by tests, and are still to be
confirmed in play: they say so, and the [bug tracker](../../BUGS.md) keeps their entries open until then.

## New

### Tribunal and Bloodmoon in the build (the road, not the arrival)

- **One reader for the base game and the expansions** merges Morrowind with the selected expansions' files by the load
  order rules of the reference engine, and the room converter, the scenery export and every stage that reads models or
  textures read the expansions' archives over the base archive in load order (dev1, dev2;
  `ASSETS-ARCHIVE-ORDER-32`, `ACTOR-LIBRARY-BASE-ARCHIVE-66`).
- **Both expansions are selected by default, and the keys know it.** Stage keys, unit caches and CHIM cell keys follow
  the selected layers, so switching an expansion on or off rebuilds only what it changes; a unit is keyed by what it
  reads (a "layer view"), and with both expansions on 55 of the 1,769 room residents and about 3 % of the NPC appearances
  change (dev1, dev2; `CHIMPORT-CELL-KEY-LAYERS-65`, `BUILD-UNIT-KEYS-LAYER-BLIND-66`). `--no-dlc` builds the base game
  alone with the keys it had.
- **The expansions' files are checked like the base game's**: with an expansion selected, `Tribunal.esm`,
  `Tribunal.bsa`, `Bloodmoon.esm` and `Bloodmoon.bsa` are required and compared by size and SHA-256 with the Game of the
  Year files before any stage (dev3; `BUILD-EXPANSION-INPUTS-UNCHECKED-66`).
- **Every table the build makes reads the expansions' data**: travel, magic, container rooms, the reference file list,
  dialogue choices, the journal (a later master's entry replaces the earlier one), the exterior plan and the world
  survey; a table of tables in the docs index shows each one ([expansion tables](../../EXPANSION_TABLES.md); dev2, dev3;
  `EXPANSION-TABLES-BASE-ONLY-66`, `JOURNAL-EXPANSION-OVERRIDES-66`, `EXTERIOR-PLAN-MASTER-LAYERS-66`).
- **The expansions' rooms are built**: their 630 residents are classified like the base game's and checked in the build's
  first minute; the 86 large rooms of at least 1,024 units fade into their fog (the table holds 410 rooms); the seven
  rooms the room stage refused are built or listed (Sotha Sil's hot oil acts as a molten pool, the Dome of Sotha Sil
  leaves out an effect model with no drawn surface, four empty cells are listed); one Hound of Hircine of the Mortrag
  Glacier keeps its authored spot (dev2 to dev4; `CHIM-LARGE-ROOMS-EXPANSIONS-66`, `LAVA-POOL-NOT-LAVA-NAMED-66`,
  `ROOM-EFFECT-MODEL-NO-TRIANGLES-66`, `ROOM-GROUND-STEEP-ICE-66`).
- **What is held back is named**: Mournhold's five outdoor districts, Solstheim's 108 new exterior cells with their 2,960
  scenery and 4,857 flora placements, and the 273 doors and markers that lead there are listed in the build report and
  not converted yet (dev2; `EXTERIOR-EXPANSION-ONLY-CELLS-66`, `EXPANSION-DOORS-HELD-BACK-66`). The 37 creature meshes
  only the expansions hold are baked (dev2).
- **The script engine is sized for the whole game with both expansions**: 791 attached instances, 1,475 local values,
  5,478 parked objects and 12,811 parked values, about 83 KB more resident memory; a map with more than 256 scripted
  objects runs every one, a script reading another object's variable does it in one step, and a change a shared script
  makes wakes the scripts that read it; `dbg mwscript status` prints the planned tables. Fixed in source and covered by
  tests, to be confirmed in a session (dev12; `MWVM-INSTANCES-256-66`, `MWVM-PARKING-STORE-SMALL-66`,
  `MWSCRIPT-MEMBER-LOOKUP-COST-66`, `MWSCRIPT-MEMBER-QUIET-READER-66`).
- `dbg tp` lists the expansions' rooms the image holds by their names, and a Solstheim place only where the build holds
  its world (dev2; `TP-LIST-UNBUILT-EXTERIORS-66`).
- A merged master's reference keys read as those of the master they name, so the expansion build passes its focus stage,
  and a room without an ambient light record takes the reference engine's default (dev2, dev3;
  `REF-IDENTITY-MERGED-MASTER-66`, `INTERIOR-NO-AMBI-66`).

### The save holds every change

- The saved state of people and creatures has no fixed cap: their rows live on the world change list, which grows with
  the game, and are written only for an actor whose state differs from the game data; the people of the expansion rooms
  are saved too (dev3; `SAVE-STATE-FIXED-CAPS-66`, `SAVE-ACTOR-ROWS-256-66`, `SAVE-ACTOR-ROWS-EXPANSION-ROOMS-66`).
- The explored map has a section of its own and never stops a save; more than 256 rooms are remembered
  (`MAP-EXPLORED-SAVE-BLOCK-66`, `MAP-EXPLORED-ROOMS-CAP-66`).
- A save is all or nothing and names the part that failed; script values come back by name, items' too; two copies of
  one item keep their own condition and charge; a save asked for inside a script step waits for it
  (dev2, dev3; `SAVE-EXPORT-FAILURE-ACCEPTED-65`, `SAVE-SCRIPT-ROW-HINT-ONLY-65`, `SAVE-ITEM-SCRIPT-LOCALS-66`,
  `SAVE-ITEM-INSTANCES-ONE-PER-KIND-66`, `SAVE-INSIDE-SCRIPT-STEP-66`).
- Every other part is a guard sized above the game's own counts with both expansions: map markers 4,096, script values
  65,536, changed actors 32,768, made spells, enchanted items, potions and filled soul gems 1,024 each, crime witnesses
  1,024, revealed places 1,024, explored land 8,192 cells (dev3; `SAVE-MADE-RECORDS-64-CAP-66`,
  `SAVE-ACTOR-ROWS-BOUND-UNDER-GAME-66`, `SAVE-LOCALS-BOUND-UNDER-GAME-66`, `SAVE-CRIME-MARKS-32-ROWS-66`,
  `SAVE-REVEALED-PLACES-128-CAP-66`). How it works: [the saved game plan](../../SAVEGAME_PLAN.md).

### Map and finding your way

- An explored-land map with fog over the rest (lava stays under it), a local map, a plan of the room you are in with fog
  over the parts not yet seen, places named when the pointer is over them, up to 256 named markers with a Markers menu, a
  quick "hot" marker with a compass, and a land-colours look as a switch, off by default (dev2;
  [world map and journal](../../WORLD_MAP_AND_JOURNAL.md)).
- Signposts show the place they name, and named objects such as beds and shrines show their name, as in the original
  (dev2; `SIGNPOST-NAMES-MISSING-65`, `NAMED-ACTIVATOR-FOCUS-66`, `FOCUS-ROWS-WINDOW-OVERFLOW-66`).

### Magic, fights and the people of the game

- **Characters cast spells**: people and creatures weigh their spells against their weapon about once a second in a
  fight, cast from range with their cast animation and pay the magicka; the cast look (hand glow, sprites, sound, the
  shell) starts with the animation and is on by default (dev2; `NPC-NO-SPELLCASTING-65`, `CAST-LOOK-AFTER-RELEASE-66`,
  `CAST-EGG-SYNC-62`; [magic effects](../../MAGIC_EFFECTS.md)).
- **Readied magic shows the open spell-casting hands**, whatever is equipped; a torch or light is put away while magic is
  ready (dev2; `READY-MAGIC-SHOWS-WEAPON-65`). The player body sneaks, turns on the spot and reacts to blows in third
  person (`PLAYER-ANIM-GROUPS-NOT-PLAYED-66`).
- **Fighters by the original's rules**: each moves at its own speed, the load carried counts in fatigue and speed, bows
  and crossbows are drawn and shot and thrown weapons thrown, each picks its weapon by its own skills (35 of 3,437
  records chose differently before, none now), fighters flee by their Flee rating, and a paralysed victim takes punch
  damage to health ([mechanics parity](../../MECHANICS_PARITY.md); dev2, dev3; `COMBAT-CHASE-SPEED-FIXED-66`,
  `ACTOR-RANGED-COMBAT-MISSING-66`, `COMBAT-WEAPON-CHOICE-SKILL-66`, `COMBAT-FLEE-RULE-PARTIAL-66`,
  `COMBAT-PARALYSED-PUNCH-66`, `ACTOR-LOAD-NOT-COUNTED-66`). `dbg combat spells off` and `dbg combat flee off` keep the
  old rules.
- **Death and respawn as in the original**: the dead stay dead across area changes and saves; a body that does not
  respawn is cleared after the original's delay (outdoors too, and it can be looted before that); killing an essential
  character shows the original's message once per death; killing someone adds the original's murder bounty (dev2, dev3;
  `ACTOR-STATE-NOT-READ-ON-SPAWN-54`, `ACTOR-RESPAWN-CORPSE-RULES-66`, `ESSENTIAL-DEATH-MESSAGE-66`,
  `OUTDOOR-DEAD-BODY-GONE-66`, `CRIME-KILL-BOUNTY-65`).
- **Dagoth Ur has his own animations** on a 948-face model with every seam locked, and the Heart of Lorkhan is a resident
  of its room that stays in its place (dev1, dev2; `HEART-OF-LORKHAN-FOLLOWS-DAGOTH-65`, `DAGOTH-UR-NO-ANIMATIONS-65`).
- **Every actor's record is audited** against the original's data, creatures are baked on the skeletal method, creatures
  fight with their weapons and the NPC library carries its items ([actor records](../../ACTOR_RECORDS.md); dev2;
  `CREATURE-COMBAT-WEAPON-54`, `NPC-WEAPON-MESH-33`).

### The interface and character creation

- The active effects on the player are a row of icons under the view, with the same icons on the Stats window and V for
  the full list (dev1; [active-effect HUD](../../HUD_ACTIVE_EFFECTS.md)).
- The birthsign and race windows list each ability, power and spell with its effects under it, as the original does
  (dev2; `CHARGEN-ABILITY-DESCRIPTIONS-65`; [character creation](../../CHARACTER_CREATION.md)).
- `dbg tp` chooses All, Exteriors, Interiors or Beings and takes the player to a person or creature by name; a teleport
  typed during a load runs on arrival (dev3, dev4; `DBG-TP-BEINGS-66`, `DBG-TP-DURING-LOAD-66`).

## Fixed

### The opening and Seyda Neen

- The opening holds fighting, magic and the other controls switched off from the prison ship until the release papers,
  from the original scripts' own calls; the ready-magic key follows them (dev5; `OPENING-FIGHTING-ON-BEFORE-PAPERS-66`).
- Scripted doors that opened only once open every time their script allows: the census captain's two doors after the
  opening (dev4; `CAPTAIN-EXIT-DOOR-DEAD-AFTER-REENTRY-66`).
- Of two items lying one on the other, the use key goes to the one the view meets first: the crab meat on the census
  back room's plate is taken, not the plate (dev5; `CENSUS-CRAB-PLATE-FOCUS-66`).
- The dock guard walks round the pier pylon on his way to the census office (dev2; `PIER-GUARD-WALKS-INTO-DOOR-65`).
- The towns' scripted objects run their scripts again: Tarhiel falls near his journal and dies on landing, checked by a
  play journey; the entries are still open until the fall is seen in play (dev2;
  `TOWN-OUTDOOR-SCRIPTS-NOT-ATTACHED-66`, `SCRIPTED-EVENT-FALLING-MAGE-61`).
- Wandering residents keep off doors by the original's rules (dev11; reopened, see "Known in this build").
- The player no longer ends inside an actor at a door's or a teleport's arrival point; fixed in source and covered by
  tests, still to be seen in play (dev9).

### The script engine

- A script's read or write of another object's local variable reaches that object (464 operations in 186 scripts gave
  0 or were lost; dev11, confirmed in the end of the main quest session; `MWSCRIPT-MEMBER-READS-ID-AS-SCRIPT-66`).
- `SetHealth 0` kills: EndGame's call killed Dagoth Ur and two of the three dreamer workers; the third is still open
  (dev11, dev12).
- `SetDelete` removes an object for good and stops its script (dev2; `MWSCRIPT-SETDELETE-STOPS-66`).
- A fighter's spell costs its magicka again; fixed in source and covered by tests, the entry still open until it is
  confirmed in a game (dev12; `NPC-CAST-MAGICKA-NOT-PAID-66`).

### The world

- Bracket fungi sit on their trees (106 floated beside them), outdoor containers can be pointed at and opened, the
  mudcrabs and slaughterfish of the town cells are placed again, and the container window's page arrows are the race
  page's triangles; the builder checks the fungi and the placed creatures, and the entries are still open until each is
  seen in play (dev2; `FUNGI-FLOATING-62`, `HARVEST-HYPHA-FACIA-FLOATING-65`, `OUTDOOR-CONTAINER-AIM-66`,
  `CHIM-EXTERIOR-ACTORS-MISSING-46`, `OUTDOOR-CREATURES-REGRESSION-66`).
- Area loads read their sounds quickly again: the image step orders the disk's folder chains busiest first and gives each
  partition the buffers its longest name lookup needs (dev5; [IMAGE-LOADS-SLOWER-66](../../bugs/IMAGE-LOADS-SLOWER-66.md),
  [BUILD-HDF-BUFFERS-32](../../bugs/BUILD-HDF-BUFFERS-32.md)).

## Performance

All figures, with what measured them and what is not measured yet, are on the
[v0.0.66 performance page](../../performance/V0.0.66-PERFORMANCE.md); the frame rate on the Raspberry Pi 4B is still
to be measured on a v0.0.66 build.

- **Area loads**: the sound stage of a map load took 59 ms at Seyda Neen, 118 and 147 ms at Balmora and 147 and 165 ms at
  Vivec on the dev6 image, against 139, 139 and 306 ms on dev1 and 480, 777 and 1,078 ms on dev2; the disk buffers that
  did it cost 72 to 73 KiB of Fast RAM (dev7).
- **The prison ship's hold** is drawn in tiles of at most 512 faces with its small hammock parts boxed: the faces tested
  per view fell from 14,128 to 10,749 on average, the collision clipnodes from 29,182 to 18,054 (dev2;
  [ship interior](../../SHIP_INTERIOR.md#the-weight-of-the-hold)).
- **The save** of a synthetic long game is about 985 KB, saved in 45 ms and loaded in 120 ms on the host; the Amiga
  times are still to be measured ([saved game budget](../../performance/SAVE-BUDGET.md); dev3).
- **The Heart Chamber** loads in play at 32 MB from Seyda Neen, with 1,943 KiB of Fast RAM free inside, in one load frame
  of about 42 seconds (dev11; [ROOM-LOAD-LONG-FRAME-63](../../bugs/ROOM-LOAD-LONG-FRAME-63.md)).
- **Scripts and fights**: the interpreter's timers share their work and script lookups are cheaper; a fighter's spells
  are read once per fight and shots come from a pool with no allocation in play (dev2; `MWSCRIPT-TICK-SHARE-66`).
- **The image's partitions** are written in one pass, measured on the dev11 inputs at 16.8 s instead of 115.5 s for the
  boot partition and 22.1 s instead of 41.8 s for the world volume; an unchanged partition is copied from a cache
  (dev12; to be confirmed on the release build).

## Builder and tools

- **The build finds problems early**: new work runs first (stages with no history, then units with no recorded time); the
  plan check runs the build's own reuse stop; the reuse check plans the same commands as the build and runs once per
  snapshot instead of twice; the image step checks its file formats and every actor against the original's count and
  record before the long steps ([build profile](../../BUILD_PROFILE.md); dev2 to dev11; `BUILD-NEW-WORK-NOT-FIRST-66`,
  `PLAN-CHECK-UNIT-STOPS-66`, [BUILD-REUSE-STOP-COUNTS-STORED-GROUP-64](../../bugs/BUILD-REUSE-STOP-COUNTS-STORED-GROUP-64.md),
  [BUILD-CHECK-ONE-CORE-66](../../bugs/BUILD-CHECK-ONE-CORE-66.md), `IMAGE-FORMAT-EFFECTS-AWE-66`).
- **A build that stalls or fails says so**: the builder writes its live numbers and a stall alert from its first second,
  the master builder flags a step under half its planned cores, a failed build writes a failure page the build monitor
  links, and, new since dev12, one report file `logs/BUILD-REPORT-<run>.txt` with everything needed to find the cause
  (the stage's own log, every setting, the versions, the game data copy, the stage plan) to send in
  ([when a build fails](../../LINUX_BUILD.md#when-a-build-fails); `BUILD-NO-STALL-ALERT-66`,
  `BUILD-FAILURE-NO-DETAILS-66`, `BUILD-FLAGS-MARK-SILENT-REFUSAL-66`, `BUILD-FAILURE-REPORT-66`,
  `SHELL-ORPHAN-STARVES-GATE-66`).
- **The build's pre-flight** runs its cache walk and the stage source analysis on a pool of workers and keeps the
  analysis of a source tree for the next check or build of the same tree (dev4; `BUILD-PREFLIGHT-SERIAL-REPEATED-66`).
  The Raspberry Pi 4B drive image step makes its own work folder when the system half comes from the cache (dev2;
  `PI-IMAGE-WORK-FOLDER-65`), and the actor frames check passes a skeletal actor that loops its own idle span inside its
  table (dev4; `DAGOTH-IDLE-BASE-CHECK-66`).
- **A build started without the release build's NPC bake settings bakes as the release build does**: those settings are
  the builder's defaults, set with the stage environment, so a contributor's intro stage no longer stops on the class
  NPC's seam check (after dev12; `BUILD-INTRO-SEAM-STOP-CHARGEN-CLASS-64`).
- **The image's partition writer** makes every folder and file in one pass (`tools/ffs_write.py`; the dev11 boot partition
  written both ways had the same SHA-256), and the partition cache (`tools/partition_cache.py`) hashes on the stage's own
  worker allowance (dev12; [BUILD-IMAGE-LAYOUT-WRITE-SLOWER-66](../../bugs/BUILD-IMAGE-LAYOUT-WRITE-SLOWER-66.md),
  `PARTITION-CACHE-FIXED-WORKERS-66`).
- **The AmiWind Toolkit's build monitor** shows a stall alert first when no build runs, the started and ended times, the
  failed stages counted from the stage list and the failure details under the progress bar
  ([AmiWind Toolkit](../../AMIWIND_TOOLKIT.md)).
- **Testing tools**: the play journey walks the opening on foot as a player plays it, nine steps and 42 checks from the
  game state ([gameplay journeys](../../GAME_RECORDER.md#gameplay-journeys)); a test session plays the end of the main
  quest from the Heart Chamber to Azura; the stall examination reads the running game, the game's own disk request and the
  file a stuck request asks for; session scripts can set emulator options (`emu KEY=VALUE`), `chim actors summon` takes a
  reference, and the remote console's log of the test sessions can be switched off (`aw_remote_log`).
- **The bug tracker** records each fix's commit, date and planning item, and public texts name who raised an issue by role
  and date only.
- **Documents**: two study pages, [AmiWind on a PiStorm-equipped Amiga 500](../../PISTORM_RTG_STUDY.md) and
  [the THEA1200 as a target](../../THEA1200_STUDY.md) (nothing has been run on either machine); the
  [expansions page](../../EXPANSIONS.md) on the order of the Tribunal and Bloodmoon work; the
  [v0.0.66 performance page](../../performance/V0.0.66-PERFORMANCE.md) and the
  [saved game budget](../../performance/SAVE-BUDGET.md); a note on host folders mounted as drives in FS-UAE
  ([FS-UAE development access](../../FS-UAE-DEVELOPMENT.md#engine-boot-and-map-load-smoke)).

### Smaller changes

Changes that the snapshots' notes do not list one by one:

- The release file list names every new test and page; the docs index and every touched page's "Last updated" line
  follow each snapshot; the builder savings chart is drawn again from its data.
- The previous-release pin and the size baseline name the published v0.0.65; the resident registry of the tests caps the
  console variables and the commands at 1,024 each.
- The test fixtures, stubs and source checks follow each change above (the native harnesses of the stats window, the
  hand models, the map, the actors and the save writer; the wiring tests of the world change list); new reports write
  their files with LF line ends.
- The cell tracker page is the one the newest snapshot build's tracker ingest rendered.

## Seen in play

On the snapshots' images in the emulator at 32 MB Fast:

- The opening journey passed all nine steps, 42 of 42 checks, on the dev7 and the dev11 images: the papers, the back room
  and its crab meat, the courtyard and Fargoth's ring (the Engraved Ring of Healing, `ring_keley`), Sellus Gravius and the
  release, a kill and the interiors, a spell and a fight, the game's own quicksave and a door after the load. On the dev12
  image part B stopped in its step 9, where the use key aimed at the census office's street door went to Fargoth
  standing in front of it.
- The opening held fighting and magic until the papers (dev5), the census captain's doors opened every time (dev4), and
  the sound loading of three area loads was timed below the dev1 figures (dev6).
- The end of the main quest session (dev10 and dev11 images): the Heart's script took Sunder's strike, five Keening
  strikes destroyed the Heart of Lorkhan, Dagoth Ur's shield followed the Heart's strike count, and the end script ran
  (the quest at its stage 20, the blight ended, Red Mountain's weather changed); no run has reached the ending video.

## Needs 32 MB Fast RAM

The game needs 32 MB of Fast RAM. At 16 MB parts run and over-limit interiors show the warning box. The emulator presets
of this release, `AmiWind-v0.0.66-FS-UAE.fs-uae` and `AmiWind-v0.0.66-WinUAE.uae`, have it.

## The game's scripts and the progress trackers

- [The MWScript tracker](../../MWSCRIPT_FEATURES.md), measured for v0.0.66: the three game files hold 1,207 scripts, 1,074
  of them used by the original game. 611 run as scripts and 9 more are carried by AmiWind's own code; 433 belong to
  Mournhold and Solstheim and wait for those worlds, 21 wait for a function not carried out yet, and 133 are named or
  started by nothing in the original game.
- [The CHIM progress tracker](../../chim/PROGRESS_TRACKER.md), from the tracker data of the snapshot builds: all 1,390
  eligible exterior cells of Vvardenfell are done, and 1,409 cells are in the game; of Vvardenfell's 1,123 rooms 1,121 are
  CHIM rooms and 2 (the prison ship and the census office) room maps of their own; Solstheim's 96 rooms and 87 of
  Mournhold's 93 are built as CHIM rooms. None of Solstheim's land cells is on CHIM yet.

## What to check in play

- A fight with people and creatures that cast spells, shoot bows or flee; one with little magicka stops casting.
- A kill, an area change and a return, a save and a load: the dead stay dead, bodies are cleared after the delay.
- A long walk saved and loaded: the people you hurt or killed are as you left them; two weapons of one kind with different
  condition come back as two.
- The map: explored land, the local map, a room plan, a named marker and the hot marker's compass.
- Readied magic (R) with a weapon, a torch and nothing equipped: the open hands each time.
- Leave the census office by its street door while a resident stands near it: the player arrives clear of him.
- A map with many scripted objects, with `dbg mwscript status`.

## Known in this build

- **Mournhold and Solstheim are not playable yet.** Their rooms are in the image, but not their outdoors, the way there
  or their quests; they come with v0.0.67 and later. Corrected for v0.0.67: the way to Mournhold works (see [the v0.0.67
  notes](RELEASE-v0.0.67.md#known-in-this-build)); its quests and much of its play are not ready.
- **The Heart Chamber's collapse is not animated, so the end of the main quest cannot play yet**
  (`ENDGAME-CHAMBER-COLLAPSE-63`).
- **One of the three dreamer workers stays alive after EndGame's `SetHealth 0`**
  ([MWSCRIPT-SETHEALTH-ZERO-NO-DEATH-66](../../bugs/MWSCRIPT-SETHEALTH-ZERO-NO-DEATH-66.md)): the scripted death reaches
  the record of changed actors but not the live actor of the one that had not moved.
- **A resident can still stand in front of a door** (`WANDER-DOOR-RULE-66`, reopened): the rule of dev11 held on the dev11
  journey, but on the dev12 image Fargoth stood in front of the census office's street door again.
- **Coming back out of a door onto a resident standing on its arrival point**
  ([DOOR-ARRIVAL-INSIDE-ACTOR-66](../../bugs/DOOR-ARRIVAL-INSIDE-ACTOR-66.md)): fixed in source and covered by tests,
  still to be seen in play.
- **Fixed in source, to be confirmed**: the script engine's tables for the whole game (`MWVM-INSTANCES-256-66`), a
  fighter's spell cost (`NPC-CAST-MAGICKA-NOT-PAID-66`) and the image's partition write
  ([BUILD-IMAGE-LAYOUT-WRITE-SLOWER-66](../../bugs/BUILD-IMAGE-LAYOUT-WRITE-SLOWER-66.md)).
- **The script engine keeps one limit** (`MWVM-PLACE-COPIES-FOUR-66`): 4 live copies per scripted Place row in one map.
- **A load can stop in the emulator in test sessions**
  ([CHIM-SEYDA-BALMORA-LOAD-HANG-43](../../bugs/CHIM-SEYDA-BALMORA-LOAD-HANG-43.md)): an interrupt request lost in the
  drive that serves the test sessions' remote-console folder; with the emulator's deterministic option 8 valid runs gave
  80 loads and no stop, against 76 loads and 2 stops as the sessions run today. Players have no such drive.
- **The save's whole round trip is not proven in play** (`SAVE-STATE-FIXED-CAPS-66`): a long game saved and loaded in
  the emulator, with the times on the 68040 preset and the Raspberry Pi 4B, is still to be done.
- **The console's item count, equip, position and ShowVars reads**
  ([CONSOLE-GETITEMCOUNT-UNNAMED-ITEM-66](../../bugs/CONSOLE-GETITEMCOUNT-UNNAMED-ITEM-66.md),
  `CONSOLE-EQUIP-SKIPS-ONPCEQUIP-66`, `CONSOLE-GETPOS-SCRATCH-ORIGIN-66`, `CONSOLE-SHOWVARS-SCRATCH-INSTANCE-66`): the
  game's own routes are not affected.
- **Bloodmoon's werewolves have no model yet** (`PLAYER-WEREWOLF-ROBE-NOT-BAKED-66`, `NPC-WEREWOLF-NO-MODEL-66`).
- **In Vivec the server's entity update overflows the client's packet every frame**
  (`NET-VIVEC-ENTITY-PACKET-OVERFLOW-66`).
- **The census courtyard arrival got stuck once** (`COURTYARD-ARRIVAL-STUCK-66`), and the game can stop in an ancestral
  tomb with its sound in a loop (`CRASH-ANCESTRAL-TOMB-AUDIO-LOOP-65`).
- **From v0.0.65**: a carried light shows in the hand only when it is equipped while the hands are raised
  (`HELD-LIGHT-NOT-IN-HAND-65`), a player jailed in Seyda Neen may be placed where the census office has no floor
  (`CENSUS-JAIL-SPOT-NO-FLOOR-65`), the pack guar at Ahemmusa Camp is drawn with its parts apart
  (`ACTOR-PACK-GUAR-MESH-BROKEN-64`), shalks on Azura's Coast hang in the air (`CREATURE-FLOATING-SHALK-64`), and the
  battle music can keep playing after a fight (`COMBAT-MUSIC-STUCK-64`).
- **The shores and pond edges still run in saw-tooth steps**; the fix needs a world rebuild and is deferred to v0.0.67
  ([INLAND-SHORE-29](../../bugs/INLAND-SHORE-29.md)).
- **In the builder**: the performance guard judges the partition write by the number of partitions
  (`PERF-GUARD-BASIS-BY-COUNT-66`); `tools/mwad.py` still has the name of the `src/mwad` package (`MWAD-NAME-CLASH-66`);
  the reuse check stops stages whose key changed only in code they never ran (`BUILD-REUSE-NEVER-READ-STOPS-66`); the
  image step's room resident step takes about two minutes on one core when every room is cached
  (`IMAGE-ROOM-RESIDENTS-CACHED-ONE-CORE-66`); checks in the development container can fail on a file read with "Cannot
  allocate memory" ([CONTAINER-READ-ENOMEM-66](../../bugs/CONTAINER-READ-ENOMEM-66.md)). Deferred to v0.0.67: the
  under-used image and room batch stages (`BUILD-IMAGE-UNDERUSED-32`, `BUILD-IMAGE-SCAN-GROUND-UNDERUSED-52`,
  `BUILD-ROOM-BATCHES-UNDERUSED-54`), the unit keys that re-key on settings they never read (`BUILD-UNIT-KEYS-REACH-64`),
  the memory leases (`AW-LEASE-MEMORY-DEADLOCK-36`) and the gate smoke's remote control (`GATE-SMOKE-NO-REMOTE-CONTROL-60`).
- Every other open entry is in the [bug tracker](../../BUGS.md).
