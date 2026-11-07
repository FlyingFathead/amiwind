# AmiWind v0.0.62-dev1 (in development)

_Last updated with AmiWind v0.0.62-dev1 (7 November 2026)._

Development snapshot, 7 November 2026, in development. Running on CHIM Engine v0.2.2. Previous release:
[v0.0.61: Keep Your Lantern Lit](RELEASE-v0.0.61.md).

The first snapshot of v0.0.62. It carries alchemy as in the original, the creatures placed in tombs, caves and other
rooms, the scripts of a new game (the Dreamers and the falling mage near Seyda Neen), characters and objects that
scripts move, follow and place, falls with fall damage and Slowfall, tree fungi that can be picked, the first creature
and flora census pages, a generated tracker of the game's scripts, fixes from the in-game check of v0.0.61, and
repairs to the test tools. The game needs 32 MB of Fast RAM, and the emulator presets of this snapshot have it.

## Checked in game

The v0.0.61 release image was played through before this snapshot was cut (17 register entries confirmed fixed, 6
still persisting, 3 new). The falling mage's fall, the placed creatures, the placement of characters by scripts and the
recorder fixes were each checked in game on test images of this version, at 32 MB Fast RAM in the emulator, with the
measurements named under each heading below. The alchemy window was measured in a test image of Seyda Neen. What was
not seen in play is listed under "Not yet seen in game".

## New since v0.0.61

### Alchemy

- **Alchemy works as in the original.** A potion selected in the inventory is drunk (E, Enter or right-click) and all
  of its effects land at once; an ingredient is eaten for its first effect, which takes hold on a roll against Alchemy,
  Intelligence, Luck and fatigue and gives an Alchemy use; a piece of apparatus opens the **alchemy window**. In the
  window the best mortar and pestle, alembic, calcinator and retort carried are used, up to four ingredients are chosen
  from the list, the effects the skill reveals are shown (one more of an ingredient's effects for every 15 points of
  Alchemy), and Create makes one potion, named after its first effect, with the original's strength, value and
  weight rules (the apparatus quality, the retort, alembic and calcinator adjustments, and the roll that fails with
  "Your potion failed."). A potion made again with the same make-up is the same item. Made potions are saved with the
  other made items. Measured at 32 MB Fast in the emulator: the window opens in 52 to 64 ms, Create takes 104 to
  269 ms, a drink or a meal 18 to 21 ms; nothing runs while the window is closed, and no new save block is added.
  Page: [ALCHEMY](../../ALCHEMY.md) (`ALCHEMY-MISSING-61`).
- Not yet: several potions at once, typing the potion's name, pictures of ingredients and apparatus in the window, and
  potions drunk by non-player characters. A made potion shows an empty picture in the inventory list
  ([MADE-ITEM-NO-PICTURE-62](../../bugs/MADE-ITEM-NO-PICTURE-62.md)).

### Creatures

- **The creatures placed in rooms are built and placed.** Ghosts, skeletons, rats, kwama and the other creatures the
  game places in tombs, caves, mines and other rooms are now in the rooms: the build counts 228 creature records built
  (100 in v0.0.61), 860 of 1,357 placements, and 527 of the 904 room placements (4 in v0.0.61). A creature comes back
  after its death only when its record says it respawns, as in the original. A creature model stays under 600
  triangles; with every room creature in view at once the rooms that have them draw 3.4 percent more triangles
  (median room 3.2 percent), which is decided for the project in crowded rooms. In Thelas Ancestral Tomb with an ancestor
  ghost close in view the frame rate was 66.9 against 69.9 without the creatures, and 4.1 MB of the heap stayed free
  in the rooms measured. The disk grows by about 29 KB (`TOMB-NO-CREATURES-61`, `INTERIOR-CREATURES-MISSING-41`).
  Three placements in Balmora houses wait for the town's conversion, and the intro tombs' levelled creatures are not
  placed yet ([ROOM-LEVELLED-INTRO-ROOMS-62](../../bugs/ROOM-LEVELLED-INTRO-ROOMS-62.md)).
- **The creature census.** Every build counts every creature record of the three masters with its placements, the
  levelled lists that name it, the scripts that place it and the summoning settings, says whether the image builds it
  and why not otherwise, and stops on anything it cannot account for. The result is on
  [CREATURES](../../CREATURES.md): 396 creature records; the 136 creatures of Tribunal and Bloodmoon and the 16
  summoned creatures are not built yet
  ([CREATURE-EXPANSION-62](../../bugs/CREATURE-EXPANSION-62.md),
  [CREATURE-SUMMONED-62](../../bugs/CREATURE-SUMMONED-62.md)).
- **Creatures that resist normal weapons.** The abilities in a creature's own record count, so a ghost takes no harm
  from an iron weapon and the game says so; silver, magical and enchanted weapons still hurt it. The combat
  playground draws a cliff racer as itself, and a creature that starts a fight while walking keeps its walking model
  (`RESIST-NORMAL-WEAPONS-61`, `RACER-STRIKES-58`, `CREATURE-FIGHT-MOVER-61`).

### Flora

- **The bracket fungi on the Bitter Coast trees can be picked** like the ground mushrooms, with the same pick, sound
  and saved state: 813 placements (724 outdoors), in Seyda Neen's sub-cells 20 to 32 each. Saves made before keep
  their picks. A census of all harvestable plants runs on every build and classifies the 25,695 organic placements; the
  rest of the plants, the egg sacks and the ore rocks are listed as pending
  ([HARVEST-TREE-FUNGUS-62](../../bugs/HARVEST-TREE-FUNGUS-62.md),
  [HARVEST-ORE-ROCKS-62](../../bugs/HARVEST-ORE-ROCKS-62.md),
  [HARVEST-EXPANSION-FLORA-62](../../bugs/HARVEST-EXPANSION-FLORA-62.md)).

### Scripts of a new game, and scripted events

- **The new-game scripts run.** The game's start script holds back 102 story references until their scripts enable
  them, so the Dreamers and other spawns that the original enables only later in the story appear only then
  (`NPC-STORY-DISABLED-AT-START-42`, `DREAMERS-TOO-EARLY-62`).
- **The falling mage.** Tarhiel, the Wood Elf who falls to his death on the Bitter Coast north of Seyda Neen, is held
  on his platform until the player comes near, then the platform goes, he falls with his two screams, takes fall
  damage, dies on landing, and his body is drawn and can be searched with its original loot. A script that enables an
  actor in an area that is loaded spawns the actor at once. In game the fall was seen and the body searched; the scripts
  that test the player's distance are listed in a census (90 scripts, 25 placed in Vvardenfell)
  (`SCRIPTED-EVENT-FALLING-MAGE-61`).
- **Falls.** Actors and the player fall with the original's gravity, take fall damage by the original's rules (the
  fall damage settings, Acrobatics, jumping and fatigue; none in water or in god mode), and a Slowfall effect slows the
  fall. Held actors fall when what they stood on is removed.
- **Moved by scripts.** PositionCell moves characters and creatures to another place, kept on the world change list;
  AIFollowCell, AIEscort and AIEscortCell make companions follow or lead the player, also through doors (followers
  within 800 units come along); PlaceAtPC, PlaceAtMe, PlaceItem and PlaceItemCell place actors and items as the
  original does, and the placed actors are kept in saves and respawned. In game a ghost, an ash zombie and a dremora
  lord were placed where asked and were still there after a save and a reload
  (`MWSCRIPT-POSITIONCELL-NPC-62`, `MWSCRIPT-PLACE-OBJECTS-62`). Placing a character that has no placed reference in
  Vvardenfell, and placing activators, containers and levelled lists, are not done yet.
- **The player control switches** (controls, fighting, jumping, looking, magic, view switching, vanity mode,
  teleporting, levitation, and the readers of each) work as in the original.
- **The first scripted batch of the gap list:** FadeIn, FadeOut and FadeTo; ForceSneak, ClearForceSneak and
  GetForceSneak (the forced sneak and the screen fades are kept in saved games); Get, Set and Mod of the ten
  resistances; and HasSoulGem and RemoveSoulGem, which let the soul dialogue scripts run.
- **Eighteen smaller script functions** (GetAngle, GetDetected, GetLOS, Move, Rotate, SetPos, SetAtStart and others)
  follow OpenMW. `dbg mwscript result TOPIC NPC` runs a dialogue answer's result script for testing.

### The MWScript tracker

[MWSCRIPT_FEATURES](../../MWSCRIPT_FEATURES.md) is generated from the game's masters and lists every script of the
game, where it runs, the functions and conditions it uses, and its state in AmiWind. Count at this snapshot:

| State | Scripts |
| --- | ---: |
| Run | 479 of 1,207 (409 when the page first appeared) |
| Use a function the interpreter lacks | 130 |
| Attached, not run | 52 |
| Compiled, not attached (their areas are not in the image) | 546 |
| Not converted | 0 |

The dialogue results, which run as scripts of their own: 7,390 of 7,411 run whole, 21 lack a function. The page also
marks where OpenMW deliberately differs from the original and AmiWind follows OpenMW.

### Fixes from the in-game check

- **Ctrl+R in every window.** The recorder's key works in every window while it is armed; a start inside a window says
  to close the window first. Every random stream is seeded from the recording at its first frame, so a recording made
  during a fight replays exactly: a fight recording held 10 of 10 checkpoints, 0.0 units off, with the guard's seven
  blows identical. The version line is drawn over windows (`GAME-RECORDER-HOTKEY-DIALOGUE-61`,
  `GAME-RECORDER-FIGHT-SEED-61`).
- **The inventory window refreshes** when something outside it changes the carried or worn items
  (`INVENTORY-EQUIP-CLOTHES-PREVIEW-61`).
- **The benchmark writes its result file** with the frame times and the drawing and disk time apart, so a run can be
  read and compared later.
- **Debug commands:** the commands added in v0.0.61 are in `dbg help` and on the
  [console commands page](../../AMIWIND_CONSOLE_COMMANDS.md).

### Test tools

- A MiniWind session starts in its image's own map, quoted record ids with spaces work in every debug route, and
  `dbg tp` works inside the loaded map of a small test image (`DEBUG-TP-MINIWIND-36`, `DBG-QUOTED-ID-REFUSED-62`).
- **Long debug listings no longer stall a frame.** With the remote console on, every console print was written to the
  console folder on its own, and one entity listing of about 300 prints cost 1 to 1.2 seconds on a quiet machine and 3
  to 7 seconds on a loaded one; test sessions then judged the game frozen. The prints are now collected and written
  twice a second, and the test probe waits out long frames: 10 of 10 sessions with the long prints ran without a stop
  ([SESSION-STALL-AFTER-LONG-FRAME-62](../../bugs/SESSION-STALL-AFTER-LONG-FRAME-62.md),
  [REMOTE-CONSOLE-LOG-COST-32](../../bugs/REMOTE-CONSOLE-LOG-COST-32.md)).
- The sweep tells actors hidden on purpose from broken ones, and counts the Say calls scripts make.
- The register and the work list were brought into step.

## Needs 32 MB Fast RAM

The game needs 32 MB of Fast RAM. At 16 MB parts run and over-limit interiors show the warning box.

## In-game checklist for this snapshot

- Alchemy: carry a mortar and pestle and two or more ingredients, open the window, make a potion, drink it, drink one
  made twice, eat an ingredient, fail a Create, save and load with a made potion.
- Tarhiel: walk the road north of Seyda Neen, see him fall and the body with its loot; try a Slowfall or Levitate
  on him first; check the draw distance (see known issues).
- A new game: the Dreamers do not appear at the start; Tarhiel is not in the world before the trigger.
- Tombs and caves: Samarys, Thelas and Dubdilla tombs show ghosts, skeletons and other creatures; a creature
  comes back after death only when its record says so; frames in the crowded rooms.
- A ghost against iron (no harm and the message) and silver (harm).
- Bracket fungi on Bitter Coast trees can be picked and stay picked after a save and load.
- A companion that follows or escorts through a door; a character moved by a dialogue answer.
- Ctrl+R in a dialogue window and in a fight, and the replay of both.
- Fall damage from a height, none in water, less with Slowfall.
- Carried over from v0.0.61: the Ebonheart lantern outdoors, a weapon that casts on strike used by a non-player
  character, the shore wall pose in Seyda Neen, the glass lantern in first person, the first-person bow, crossbow and
  thrown stances, the sway styles, Until Healed after damage, and frame times on the Raspberry Pi 4B and in the emulator.

## Not yet seen in game

- Everything on the checklist above that is not named under "Checked in game"; the potion drunk and made in the
  alchemy window was measured, but a full play session with it was not.
- The version line over windows during a recording.
- The scripts of the first gap batches (fades, forced sneaking, resistances, soul gems) and the player control switches: tested by
  the interpreter's tests, no scripted scene run yet.
- The frame times of the rooms' new creatures on the Raspberry Pi 4B.

## Known in this build

- The falling mage plays out past the default draw distance: on his platform and for most of the fall he is too far
  up to be drawn from where the player stands on the road
  ([SCRIPTED-EVENT-PAST-DRAW-DISTANCE-62](../../bugs/SCRIPTED-EVENT-PAST-DRAW-DISTANCE-62.md)).
- A hard landing does not knock down the player or an actor
  ([FALL-LANDING-KNOCKDOWN-62](../../bugs/FALL-LANDING-KNOCKDOWN-62.md)).
- A script cannot place a character with no placed reference in Vvardenfell, nor an activator, a container or a levelled
  list ([MWSCRIPT-PLACE-NO-MODEL-62](../../bugs/MWSCRIPT-PLACE-NO-MODEL-62.md),
  [MWSCRIPT-PLACE-OTHER-KINDS-62](../../bugs/MWSCRIPT-PLACE-OTHER-KINDS-62.md)); a character a script sends outdoors
  appears there only while its home area is loaded
  ([MWSCRIPT-POSITIONCELL-OUTDOOR-62](../../bugs/MWSCRIPT-POSITIONCELL-OUTDOOR-62.md)).
- Scripts of items that are carried, given or sold, and of characters from levelled lists, are compiled but not run
  ([MWSCRIPT-UNPLACED-RECORD-SCRIPTS-61](../../bugs/MWSCRIPT-UNPLACED-RECORD-SCRIPTS-61.md)); Tribunal and Bloodmoon
  scripts are not attached because those worlds are not in the image.
- The ore and gem rocks cannot be mined, and the plants of the add-on masters cannot be picked.
- The creatures of Tribunal and Bloodmoon and the summoned creatures are not built; Addamasartus and Tharys Ancestral
  Tomb have no levelled creatures yet.
- From [v0.0.61](RELEASE-v0.0.61.md): a dropped light gets no flame; a Shield effect does not soften blows; an ended
  Fortify effect counts as damage; several witnesses starting fights in one frame hold that frame for about 0.6 s; the
  baked light of a room stays when a light in it is taken; the worn Constant Effect items of non-player characters are
  not applied; the first frame in Seyda Neen takes about a second; the Vivec town's resident bake costs about three and
  a half times its earlier CPU
  ([PERF-GUARD-RESIDENT-BUSY-HOST-57](../../bugs/PERF-GUARD-RESIDENT-BUSY-HOST-57.md)); the trip from Seyda Neen to
  Balmora sometimes stalls on the loading screen in the emulator
  ([CHIM-SEYDA-BALMORA-LOAD-HANG-43](../../bugs/CHIM-SEYDA-BALMORA-LOAD-HANG-43.md)); some rooms still load in after
  you arrive ([CHIM-ROOM-POPIN-51](../../bugs/CHIM-ROOM-POPIN-51.md)).
- Not in the recorder yet: the mouse pointer inside windows, segment marks, frame times per segment, replay on the
  Raspberry Pi 4B and the smoke suite made from recordings.
