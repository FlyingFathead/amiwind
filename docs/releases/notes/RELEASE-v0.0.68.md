# AmiWind v0.0.68: Solstheim Is Here

_Last updated with AmiWind v0.0.68 (24 November 2026)._

Release, 24 November 2026. Running on CHIM Engine v0.2.2. Previous release:
[v0.0.67: Tribunal Introduced](RELEASE-v0.0.67.md). Made from the twelfth development snapshot, v0.0.68-dev12, with the
line's last fixes on top (the open sea to Solstheim, the emergency memory purge and Water Walking), from the builds and
caches of the snapshots; it carries all twelve snapshots:
[dev1](RELEASE-v0.0.68-dev1.md), [dev2](RELEASE-v0.0.68-dev2.md), [dev3](RELEASE-v0.0.68-dev3.md),
[dev4](RELEASE-v0.0.68-dev4.md), [dev5](RELEASE-v0.0.68-dev5.md), [dev6](RELEASE-v0.0.68-dev6.md),
[dev7](RELEASE-v0.0.68-dev7.md), [dev8](RELEASE-v0.0.68-dev8.md), [dev9](RELEASE-v0.0.68-dev9.md),
[dev10](RELEASE-v0.0.68-dev10.md), [dev11](RELEASE-v0.0.68-dev11.md) and [dev12](RELEASE-v0.0.68-dev12.md). Each
snapshot's notes hold the full detail of its changes and how each was checked. Its emulator presets,
`AmiWind-v0.0.68-FS-UAE.fs-uae` and `AmiWind-v0.0.68-WinUAE.uae`, both start with 32 MB of Fast RAM, which the game needs.

## What v0.0.68 is

v0.0.68 brings Bloodmoon's island into the game. All 153 of Solstheim's cells are built, land and sea: the Mortrag
Glacier with its ice, its coast, the villages and the caves, and one open sea joins it to Vvardenfell, as in the
original. The quest entrances that a quest stage
opens, among them Stahlman's Gorge, the Caves of Fjalding and Glenschul's Tomb, were entered in play, and so was the
underwater entrance of the Unmarked Shipwreck. The people Bloodmoon's scripts turn into werewolves are drawn as werewolves
and fight with their claws, the player in werewolf form is drawn as the werewolf, and the scripted objects of Solstheim
and of Mournhold answer the use key and move as their scripts say. Every room of the three game files is in the game:
1,134 of 1,134 interiors of Morrowind, 96 of 96 of Tribunal and 98 of 98 of Bloodmoon, with the exterior cells of all
three.

Beside Solstheim, the version mends what the maintainer's playtest of v0.0.67 found in the hands, gives the game's menus
and the map the original's rows, questions and look, lays out the talk window as the original's, makes fights with
several fighters smooth, and brings the builder a cache that ages and a plan that fits a 32 GB machine.

The maintainer's playtests of the line were made on the PC emulator and on the Raspberry Pi 4B; what was seen in play is
said on each line below. A line that says "covered by tests" was checked by the test suite and the gates of its commits
and is still to be seen in play; the [bug tracker](../../BUGS.md) keeps its entry open until then.

## New

### Solstheim

- **All 153 cells of Solstheim are built.** The first 135 open terrain cells came in dev3 as a world of their own, the
  Mortrag Glacier's nine cells in dev8 (the way of fitting its ice into 32 MB is on the
  [glacier page](../../chim/SOLSTHEIM_GLACIER.md)), Solstheim's own sea cells in dev8 and its last two open-sea cells in
  dev9. The [CHIM progress tracker](../../chim/PROGRESS_TRACKER.md) counts each land and part.
- **Ice and snow keep a cool cast.** The game's palette has a ramp of cool off-white to blue-grey for them, chosen by the
  maintainer from the test pictures; they no longer turn brown-grey (dev7).
- **The entrances that a quest stage opens can be used.** The ice covers and the rock that a quest stage removes are
  hidden as they should be (840 placements of Mournhold are hidden by the same rule), a door under the crosshair takes the
  use key from a creature standing around the player, and a player put into water stays at that depth. Stahlman's Gorge,
  the Caves of Fjalding, Glenschul's Tomb and the Unmarked Shipwreck's entrance were entered in play on the PC emulator
  (dev9); the hiding of Mournhold's 840 placements and the depth of a player put into water are covered by tests, not yet
  seen in play.
- **Every weather has its own look.** A blizzard is a storm blowing north, characters facing into it shield their eyes,
  and each weather has its own fog distance and cloud speed. Seen in play on a test image at the glacier: a blizzard's fog
  is about four times nearer and its clouds six times faster (dev11); the eye-shielding is covered by tests.
- **The outdoor draw distance can differ by region** (the Options entry **Fog distance auto**, on by default); Solstheim's
  six regions carry a trial distance that applies only when the trial switch is on (dev8).
- **One open sea joins Vvardenfell and Solstheim, as in the original.** The 982 cells of the map's box that hold no
  record of the game files are built as open sea, so the sea runs from Vvardenfell's coast to Solstheim's with no wall
  between them; the walls stand only at the outer edge of the map. The far sea has a store of its own, so Solstheim's
  world keeps its memory headroom, and the boat from Khuul still takes the player across. Seen in play on the release
  build: Water Walking from Khuul across the open sea to the shore under Fort Frostmoth, staying on the surface the whole
  way, and the boat both ways, from S'virr at Khuul to Fort Frostmoth's dock and back with Basks-In-The-Sun, six hours
  each as in the original.
- **The world map spans the whole sea.** Map v2 shows Solstheim as it is explored, by the same rule as Vvardenfell, and
  the debug map (`dbg maptype 1`) shows all of it.

### The werewolf

- **The player in werewolf form is drawn as the werewolf**, in third person, with its claws in first person, at its
  race's and sex's size; the change comes by a script, the console, `dbg werewolf on|off` or the robe, and the change back
  is the original's (dev9, dev10; seen in play for six races).
- **The characters a script turns into werewolves are drawn as werewolves,** hold nothing in their hands, fight with their
  claws only, and a dead one stays a werewolf corpse; the Skaal hunt's characters were seen attacking the honor guards with
  their claws only (dev10).
- **A character in werewolf form cannot be talked to,** as in the original, and a script's ForceGreeting opens the
  conversation as the original does (dev9, dev11).

### Scripts and objects

- **Placed objects answer the use key as their scripts say:** 1,712 named activators whose script reads OnActivate,
  among them beds, levers, cave-ins and shrines; containers and bodies whose script takes their use give it to the script
  (dev8, dev9). The Halls of Penumbra's ice wall asks whether to throw the flaming eye at it.
- **A script's animation on a placed object leaves it in the end pose,** drawn, collided and kept in the save: the ice
  wall breaks and the Sotha Sil lever doors open (dev10).
- **The scripted objects of Mournhold's five districts run on their frames:** 366 objects, among them the courtyard's
  living and dead trees, the districts' ambient sounds, the Plaza's fabricant attacks and Azura's statue (dev6; covered
  by tests, not yet seen in play).
- **Every invisible wall of the game is a solid box a script can switch,** among them the five lids over Mournhold's
  districts (dev4). **A load door that a script has switched off is not taken by the use key** (dev6).
- **Scripts that wait for the player's blow see it** (OnPCHitMe, 32 scripts of the three game files), and **fights ordered
  by scripts wait for their turn** with sixteen slots instead of four (dev8).
- **More of the original's console commands,** typed on the console: weather, werewolf, script, sound and placing
  commands (dev2), spells, items and topics (dev3), the interpreter's own opcodes, the cell commands and every other
  function of the script language (dev4). The list of console commands names all of them.

### Fights, water and the hands

- **Fights no longer stutter when blows land:** the worst frame of a fight with six fighters went from 219 ms to 50 ms,
  seen in play (dev11). `dbg combat` says where a fight's time goes.
- **A light and a one-handed weapon are held together and both are drawn,** the third-person fists draw and punch with the
  original's animations, readied magic stays readied through doors, and Enter only closes the item information box (dev2;
  seen in play).
- **Moving water in rooms and drowning, seen in play:** `SetWaterLevel` and `ModWaterLevel` move a room's water, the water
  levers of Old Mournhold move it, and people drown under water by the original's rule (dev2). A person knocked out in
  water drowns at once and makes the drowning sound (dev5; covered by tests, not yet seen in play).
- **Water Walking holds the player on the water's surface,** as in the original: he stands, walks, runs and jumps on it,
  steps onto it from a quay, is lifted onto it when the spell takes hold under water, and drops in and swims as before
  when the effect ends; swimming itself is unchanged. Seen in play at 32 MB of Fast RAM: cast in the sea off Vvardenfell,
  walked on the water across into Solstheim's world, a jump landed back on the surface. The original refuses the spell on
  someone too deep under the water; here it is applied and lifts him to the surface
  ([WATER-WALKING-DEEP-CAST-NOT-REFUSED-68](../../bugs/WATER-WALKING-DEEP-CAST-NOT-REFUSED-68.md)).

### Menus, map and talking

- **The game's own colours in every window,** also after a start from the main menu by a console command; Escape in play
  opens the in-game menu with the original's rows (Return To Game, New Game, Save Game, Load Game, Options Menu, Exit
  Game) and its questions with Yes and No (dev8; seen on the PC emulator).
- **The map is the original's map in the menus' framed style,** with World and Local, the place's own name on the title bar
  and the zoom and pan keys named in the footer; the earlier map is kept behind `dbg maptype 1` (dev8; seen on the PC
  emulator).
- **The talk window is laid out as the original's:** the disposition bar with its number on top (a person only), only the
  services the speaker offers in the original's order, a divider, the topics, Goodbye at the bottom and the speaker's name
  on the title bar. Persuasion works: Admire, Intimidate, Taunt and the three bribes answer and move the disposition (dev12;
  seen in play).
- **The creatures that have lines have rows in the dialogue and voice tables:** 46 creatures over the three game files,
  nine of them with recorded voices (dev11).

### Seyda Neen and the opening

- **The census back room answers the use key again after a visit to the courtyard,** and switching the debug free flight
  off where the player's box touches the world lifts the player clear (dev7). The opening journey, run as a check on the
  dev6 image with the dev7 engine, passed all 50 of its checks.

## Memory

- **Every place and every way between places is measured at 32 MB before an image is made:** each frame of each world
  with its own store index, each room, each switch between worlds and each door between a room and the land. An overflow
  stops the build and names the place; on this release's data, 1,515 frames, 1,326 rooms and 721 doors fit.
- **The emergency purge when memory fills.** A load that runs out of memory first gives back every cache the game can
  make again (the animation tables, the posed frames, the cached area tables) and is tried once more. If it still does
  not fit, a box names the place, the memory it needs and the memory available, and OK returns the player to where he
  came in. A room whose models do not fit is reported the same way (covered by tests, not yet seen in play). `dbg mempurge` shows the purges and switches the
  purge off or on; `dbg mempurge test` makes the next load short of memory once. Seen in play at 32 MB of Fast RAM: the
  purge gave back 516 KiB and the load went through on its second try; with the purge off the box came up and OK went
  back to Seyda Neen.

## Builder and tools

- **A build that stops ends with a plain block** that says why, that the finished work is kept and the command that
  continues it; the build guide has a section for it; the build report gains the swap and the memory peaks (dev1).
- **The build's memory plan** plans a full build's memory from the reference build's measured stage peaks, so a build fits a
  32 GB machine (dev1, dev2).
- **The build cache ages:** an entry no build used or wrote within 14 days and no kept run needs expires with its files,
  and the collector walks the build runs on all its worker processes (dev12).
- **A rebuilt CHIM world compares equal to the cached one,** so the stages after it keep their cached work: compiled
  collision memos and the mesh-method diagnostics are left out of the comparison
  ([CHIM-REBUILD-NOT-IDENTICAL-68](../../bugs/CHIM-REBUILD-NOT-IDENTICAL-68.md)).
- **The door check judges by what play showed:** it walks the lands that have a store of their own, uses the original's
  reach, and treats a door under water as a swimming player does (dev5, dev9).
- **The open sea's land records without heights are built.** An expansion's land record that has no heights and is the
  only land record of its cell (the open sea beside Bloodmoon's cells -18,28 and five more) takes the base game's
  default-height rule, so the world build no longer stops on it
  ([OCEAN-APRON-EXPANSION-HEIGHTLESS-68](../../bugs/OCEAN-APRON-EXPANSION-HEIGHTLESS-68.md)).
- **The image's door check names the far sea's maps apart from Solstheim's.** The stores' frame maps are named all at
  once, so the far sea's maps take the names after Solstheim's and Solstheim's doors are traced in Solstheim's world;
  before, 83 of its doors were counted as unreachable and the check fell to 1,139 of 1,217
  ([DOOR-CHECK-SEA-STORE-NAMES-68](../../bugs/DOOR-CHECK-SEA-STORE-NAMES-68.md)).
- **A release is refused while a space is missing.** The release check refuses a release while any cell, room or load door
  of a shipped master is missing from the build; no kind of space is a reason to leave one out (dev9).
- **For Solstheim:** the region converter for its open terrain, named sets of mesh methods for the glacier, collision for
  its ice in the larger map format, and the outer-hull measure that decides whether a reduced model may draw the werewolf
  (dev2 to dev4). The rally-game trees and the see-through fix for outdoor models are in behind switches that are off; the
  maintainer chooses the trees' method from the pictures.
- **The automated playthroughs wait for the game by condition,** not for a fixed number of seconds (dev1); the private word
  lists left the public tree (dev1).
- **The smaller items** (the console function GetEffect knowing all 143 magic effects, the glow and curtain layers of the
  Ghostfence behind switches, the image disk plan counting the expansions' stores, the debug teleport list counting
  Solstheim's places, two debug camera moves for video, the completeness plan counting the cells inside the towns' frames
  and the rewritten public progress tracker) are in the snapshot notes.

## Fixed

- The census back room answers the use key after a visit to the courtyard; the debug free flight lifts the player clear;
  a door that a script switched off is not taken; a door under the crosshair is not lost to a creature standing around
  the player; a player put into water stays at that depth (dev9; covered by tests, not yet seen in play).
- A script's region is the region it names (dev2); the taken and disabled outdoor pieces have no limit and the pieces a
  script switches off are hidden (dev3); a scripted `Drop` leaves what the actor carries (dev3).

## Documentation

- **The main page is a short summary of where the project stands,** with the framework of the Game of the Year edition,
  what works and what comes next, and a test that refuses a stale status (dev12). The [roadmap](../../ROADMAP.md), the
  [changelog](../../CHANGELOG.md) and the [MWScript tracker](../../MWSCRIPT_FEATURES.md) are brought to this version; the
  [CHIM progress tracker](../../chim/PROGRESS_TRACKER.md) is brought to the release build after it is made.

## Needs 32 MB Fast RAM

The game needs 32 MB of Fast RAM. At 16 MB parts run and over-limit interiors show the warning box.

## What to check in play

The checklists of the snapshots stand ([dev12](RELEASE-v0.0.68-dev12.md#in-game-checklist-for-this-snapshot),
[dev11](RELEASE-v0.0.68-dev11.md#in-game-checklist-for-this-snapshot),
[dev10](RELEASE-v0.0.68-dev10.md#in-game-checklist-for-this-snapshot),
[dev9](RELEASE-v0.0.68-dev9.md#in-game-checklist-for-this-snapshot)). In addition, for the release:

- **The crossing to Solstheim.** Take the boat from Khuul to Fort Frostmoth and back. Then cross the sea from
  Vvardenfell's north-west coast by swimming or by Water Walking: no wall stops the player on the way, and
  the world map shows Solstheim as it is explored.
- **A load at the edge of memory.** Type `dbg mempurge test` and travel: the load goes through on its second try. Then
  `dbg mempurge off`, `dbg mempurge test` and travel again: the box names the place and the memory, and OK takes you back
  to where you came in. `dbg mempurge on` turns the purge back on.

## Known in this build

The [MWScript tracker](../../MWSCRIPT_FEATURES.md) shows how many of the game's scripts run and what each function does in
play; the [CHIM progress tracker](../../chim/PROGRESS_TRACKER.md) shows how far each land and part has come.

- **The release is made from the snapshots' builds and caches.** A build from nothing is checked on its own afterwards.
- **No ripples on the water** under a swimmer or a player walking on water
  ([WATER-RIPPLES-UNDER-ACTORS-MISSING-68](../../bugs/WATER-RIPPLES-UNDER-ACTORS-MISSING-68.md)).
- **The journal's topic list has no letter index yet:** every topic is in one scrolling list
  ([JOURNAL-TOPIC-LETTER-INDEX-68](../../bugs/JOURNAL-TOPIC-LETTER-INDEX-68.md)).
- **The memory box can name the target by its map file label:** when a load runs out of memory the box writes the target
  as an internal label (for example rifa4ef181ed) instead of the place's name
  ([LF5-BOX-DESTINATION-MAP-NAME-68](../../bugs/LF5-BOX-DESTINATION-MAP-NAME-68.md)); the box offers OK only, and Load
  Game and New Game follow.
- **Water Walking is applied deep under the water too,** where the original refuses the spell
  ([WATER-WALKING-DEEP-CAST-NOT-REFUSED-68](../../bugs/WATER-WALKING-DEEP-CAST-NOT-REFUSED-68.md)).
- **An object in Solstheim's eastern waters is not drawn but still stops a player walking on the water** (cell -19, 17,
  on the way from Khuul); walking around it reaches Solstheim
  ([SOL-SEA-INVISIBLE-BLOCKER-68](../../bugs/SOL-SEA-INVISIBLE-BLOCKER-68.md)).
- **Creatures that have lines cannot be talked to yet** ([DIALOGUE-CREATURE-SPEAKERS-66](../../bugs/DIALOGUE-CREATURE-SPEAKERS-66.md), open), and
  **a companion has no Companion Share entry** ([DIALOGUE-COMPANION-SHARE-MISSING-68](../../bugs/DIALOGUE-COMPANION-SHARE-MISSING-68.md)).
- **A video started by a script can always be skipped,** also the ones the original plays to the end
  ([MWSCRIPT-PLAYBINK-SKIP-FLAG-68](../../bugs/MWSCRIPT-PLAYBINK-SKIP-FLAG-68.md)).
- **Solstheim's weather:** each weather's own cloud picture is left
  ([WEATHER-CLOUD-TEXTURES-68](../../bugs/WEATHER-CLOUD-TEXTURES-68.md)) and the walk is not slowed in storms
  ([STORM-WALK-NOT-SLOWED-68](../../bugs/STORM-WALK-NOT-SLOWED-68.md)).
- **The werewolf:** silver weapons' extra damage, the werewolf's own sounds and the readier attack on a werewolf are left
  ([WEREWOLF-FIGHT-RULES-LEFT-68](../../bugs/WEREWOLF-FIGHT-RULES-LEFT-68.md)).
- **The broken ice wall cannot be passed:** the chamber behind it cannot be entered
  ([PENUMBRA-ICE-WALL-NO-PASSAGE-68](../../bugs/PENUMBRA-ICE-WALL-NO-PASSAGE-68.md)).
- **Mournhold's districts run at a low frame rate** ([DISTRICT-FRAME-RATE-LOW-67](../../bugs/DISTRICT-FRAME-RATE-LOW-67.md));
  the cost of the districts' scripts in frames is not measured.
- **Trees and distance:** the rally trees and the see-through fix are off by default and not seen in play; the region
  distance of Solstheim is a trial until the frame rate is measured on real hardware. Akulakhan's Chamber keeps its old
  look, as it cannot hold its end poses within 32 MB yet.
- **Builder:** the reuse keys read by lookup record no use, so the collector keeps them whole
  ([CACHE-KEY-LOOKUP-NO-USE-68](../../bugs/CACHE-KEY-LOOKUP-NO-USE-68.md)); the build volume's cleanup keeps the runs a
  finished build request named
  ([JANITOR-KEEPS-RUNS-OF-FINISHED-REQUESTS-68](../../bugs/JANITOR-KEEPS-RUNS-OF-FINISHED-REQUESTS-68.md), open).
- From [v0.0.68-dev12](RELEASE-v0.0.68-dev12.md#known-in-this-build) and its earlier snapshots, and
  [v0.0.67](RELEASE-v0.0.67.md#known-in-this-build) and its snapshots: their Known lists stand for what is not named here,
  among them the census courtyard re-entry stop, Mournhold's and Solstheim's unfinished play, the open builder entries and
  the look book's open entries. Every other open entry is in the [bug tracker](../../BUGS.md).
