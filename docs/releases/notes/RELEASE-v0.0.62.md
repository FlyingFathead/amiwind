# AmiWind v0.0.62: Stick To The Script

_Last updated with AmiWind v0.0.62 (8 November 2026)._

Release, 8 November 2026. Running on CHIM Engine v0.2.2. Previous release: [v0.0.61](RELEASE-v0.0.61.md).

v0.0.62, "Stick To The Script", is the scripts, crime and alchemy release. Alchemy works as in the original, the creatures placed in rooms are
built, 588 of the game's 1,207 scripts run (479 in the first snapshot), the census office runs its own scripts, dialogue
choices are rows to pick, and guards who see a crime come to arrest, with the fine and the jail of the original. A room
that fails to load no longer locks the game, and a New Game starts from a clean state. The inventory equips and uses an
item with a double-click, the characters are reduced with a method that measures their joints, and new debug commands
give gold, remove the carrying limit and set the level. The game needs 32 MB of Fast RAM, and the emulator presets of
this release have it.

This release is what was to be the third development snapshot of v0.0.62, with its final version number and the release
documents. The second snapshot, [v0.0.62-dev2](RELEASE-v0.0.62-dev2.md), was not delivered: its builds failed, and its
work ships here.
The third snapshot, dev3, became this release and has no notes of its own. The notes below cover the whole of v0.0.62
since v0.0.61, by area. The notes of the earlier snapshots are [dev1](RELEASE-v0.0.62-dev1.md) and
[dev2](RELEASE-v0.0.62-dev2.md) (not delivered).

## Checked in game

The v0.0.61 release image was played through before the first snapshot was cut (17 register entries confirmed fixed, 6
still persisting, 3 new). The falling mage's fall, the placed creatures, the placement of characters by scripts and the
recorder fixes were each checked in game on test images of this version, at 32 MB Fast RAM in the emulator. During the
work on the crime rules, the fine, resisting arrest, a guard's attack on sight at a high bounty and the jail were seen
working in a test image of Seyda Neen (the guard's Pay Gold took 40 gold, Resist Arrest made the guard attack, a bounty
of 10,000 made a guard attack on sight, and jail passed 15 days and let the player out at the prison marker); that was
during the dev2 work, and the later crime fixes (saved pursuers, the full release text) are not seen yet. The
alchemy window was measured in a test image of Seyda Neen. This release's own image was not played yet: the new fixes of
the last snapshot were checked by the build's own checks and by the tests that come with each change, not yet in play.
What was not seen in play is listed under "Not yet seen in game".

## New since v0.0.61

### Alchemy

- **Alchemy works as in the original.** A potion selected in the inventory is drunk (E, Enter or right-click) and all
  of its effects land at once; an ingredient is eaten for its first effect, which takes hold on a roll against Alchemy,
  Intelligence, Luck and fatigue and gives an Alchemy use; a piece of apparatus opens the **alchemy window**. In the
  window the best mortar and pestle, alembic, calcinator and retort carried are used, up to four ingredients are chosen
  from the list, the effects the skill reveals are shown (one more of an ingredient's effects for every 15 points of
  Alchemy), and Create makes one potion, named after its first effect, with the original's strength, value and
  weight rules. A potion made again with the same make-up is the same item. Made potions are saved with the other made
  items. Measured at 32 MB Fast in the emulator: the window opens in 52 to 64 ms, Create takes 104 to 269 ms, a drink or
  a meal 18 to 21 ms. Page: [ALCHEMY](../../ALCHEMY.md) (`ALCHEMY-MISSING-61`).
- Not yet: several potions at once, typing the potion's name, pictures of ingredients and apparatus in the window, and
  potions drunk by non-player characters. A made potion shows an empty picture in the inventory list
  ([MADE-ITEM-NO-PICTURE-62](../../bugs/MADE-ITEM-NO-PICTURE-62.md)).

### A room that fails to load, and a new game

- **A failed load goes back.** In the first snapshot the debug teleport to the Heart Chamber (Akulakhan's Chamber) stopped
  on the Loading screen and the session could not recover. A load that fails (a door, a teleport, a script move or any
  other map load that does not spawn) now brings the player back to the exact place the move started from, with the game
  running and the game's message box: "Unable to teleport, see debug console with F10." for a teleport, a line of its own
  for a door or a script. OK stays; Load Game opens the load menu, and the load menu also opens when the way back fails.
  The console keeps the reason. `dbg loadfail N` makes a load fail for testing. The cause of the Heart Chamber
  stop itself is not found yet: a Fast RAM census was used to look for what takes the room of the 32 MB minimum
  ([HEART-CHAMBER-LOAD-HANG-62](../../bugs/HEART-CHAMBER-LOAD-HANG-62.md),
  [CHIM-ROOM-HEART-CHAMBER-LOAD-50](../../bugs/CHIM-ROOM-HEART-CHAMBER-LOAD-50.md)).
- **`dbg restartgame`** ends the game cleanly (memory back to the start-up level, with Boot and Restart lines in the
  console) and shows the logo and the main menu again.
- **`dbg ver`** (also `dbg version`) prints the AmiWind version, the build commit and date when the image records them,
  and the CHIM engine version. **`dbg memcensus`** prints the free Fast RAM, its largest block, the map and the Hunk in
  use, in one line. **The console pager:** `dbg`, `dbg help` and `dbg help WORD` show one console screen at a time.
- **The mouse pointer in message boxes.** Every message box (the scripts' boxes, the failed-load box and the death box)
  shows the pointer and takes clicks on its buttons ([MSGBOX-NO-CURSOR-62](../../bugs/MSGBOX-NO-CURSOR-62.md)). A message
  box shows all of its lines, and the release from jail lists every skill it changed (`CRIME-RELEASE-LINE-CUT-62`).
- **A New Game starts as the first did.** A New Game from the menu had kept the script interpreter's instances, locals,
  timers and running scripts of the game before, and the session tables that a load resets (standing and crime,
  effects, actor packages, merchants, made items, gems, faction reactions, revealed places, topic pages, forced sneak and
  fades, the object state). New Game and `dbg restartgame` now reset through one registry, and the console names any state
  that differs from a fresh start. Page: [GAME_STATE_RESET](../../GAME_STATE_RESET.md)
  ([NEWGAME-STATE-RESET-62](../../bugs/NEWGAME-STATE-RESET-62.md)).

### The game's scripts

- **588 of 1,207 scripts run** in the count of the MWScript tracker (409 when the page first appeared, 479 in the first
  snapshot). The count is measured from the game's masters; records that nothing makes are counted as inert, scripts of
  add-on records wait for the add-ons, and a script with no function counts as running. The interpreter carries out 336
  functions. [MWSCRIPT_FEATURES](../../MWSCRIPT_FEATURES.md) is generated from the game's masters and lists every script
  of the game, where it runs, the functions and conditions it uses, and its state in AmiWind. 7,410 of 7,411 dialogue
  results run whole.
- **The new-game scripts run.** The game's start script holds back 102 story references until their scripts enable
  them, so the Dreamers and other spawns that the original enables only later in the story appear only then
  (`NPC-STORY-DISABLED-AT-START-42`, `DREAMERS-TOO-EARLY-62`).
- **The falling mage.** Tarhiel, the Wood Elf who falls to his death on the Bitter Coast north of Seyda Neen, is held
  on his platform until the player comes near, then the platform goes, he falls with his two screams, takes fall
  damage, dies on landing, and his body is drawn and can be searched with its original loot. He is released in the tick
  his platform goes, a held actor is drawn over the fog past the draw distance, and his script fires at the original's
  2000 units (`SCRIPTED-EVENT-FALLING-MAGE-61`, `SCRIPTED-EVENT-PAST-DRAW-DISTANCE-62`).
- **Falls.** Actors and the player fall with the original's gravity, take fall damage by the original's rules (none in
  water or in god mode), and a Slowfall effect slows the fall. Held actors fall when what they stood on is removed.
- **Moved by scripts.** PositionCell moves characters and creatures, AIFollowCell, AIEscort and AIEscortCell make
  companions follow or lead the player, also through doors, and PlaceAtPC, PlaceAtMe, PlaceItem and PlaceItemCell place
  actors and items as the original does; the placed actors are kept in saves and respawned. The placing functions make a
  character that has no placed reference, and an activator, static or container from a placed reference of its record
  (`MWSCRIPT-POSITIONCELL-NPC-62`, `MWSCRIPT-PLACE-OBJECTS-62`, `MWSCRIPT-PLACE-NO-MODEL-62`).
- **Items that are carried, bought, given or kept in containers run their scripts**, and so do characters made from
  levelled lists, as in the original (`MWSCRIPT-UNPLACED-ATTACH-62`, `MWSCRIPT-INVENTORY-HITONME-62`).
- **HitOnMe** keeps the player's weapon per victim, so the Heart of Lorkhan reacts to the blow that strikes it.
  **OnPCEquip and PCSkipEquip** of the player's items work, and the scripts' message boxes, their use take-overs and the
  locals that a dialogue reads are seen (15 scripts attached again).
- **New functions.** PlayBink plays the converted video over the scene, which goes on after it. ChangeWeather and ModRegion
  change a region's weather, so the end of the main quest clears Red Mountain. The shrines' blessings land their effects
  that name no attribute or skill (Shield, the resistances, Levitate, Fortify Attack). Resurrect, Drop and HurtStandingActor
  were added, and the game's lava script hurts the player standing on its object (`MWSCRIPT-GAP-FUNCTIONS-62`).
  Earlier batches: the player control switches, FadeIn, FadeOut and FadeTo, ForceSneak, the ten resistances, soul gems,
  and eighteen smaller functions that follow OpenMW. `dbg mwscript result TOPIC NPC` runs a dialogue answer's result script
  for testing.

### The census office runs the game's own scripts

- **The clerk, the captain, the door guard, the papers, the ring, the fatigue barrel and the office doors** now run the
  game's own scripts instead of the project's hand-written opening. The clerk says his own lines and opens the class,
  birth and review windows; the door guard says his two lines and unlocks the hall door when the papers are carried; the
  doors say what the captain wants done first; the barrel turns on the map menu; the census papers and the courtyard
  ring run their scripts when they enter the player's inventory (a rule of the original, now in the engine for every
  item). The menu switches the scripts use (stats, inventory, magic and map) are saved with the game.
- **The captain talks through the dialogue window.** Sellus Gravius had opened an early hand-written box. He now uses
  the ordinary dialogue window with his own records: his greetings (the first takes the identification papers), his
  hello line and his topics, with the duties topic running its result script (the journal entry, the package, the
  directions, 87 gold and the added topics). A dialogue result that runs while the speaker's script is not attached keeps
  the speaker's locals, so he no longer asks for the papers twice.
- **`census legacy`** (`dbg census legacy`) switches back to the old hand-written path for a comparison of the two. The
  new path is the default. Thirteen other scripts of the opening are still hand-written.
- A script's Activate on a placed item opens its reader with Take, or takes it; a script's Activate on a character
  opens his conversation ([CENSUS-INTRO-SCRIPTS-62](../../bugs/CENSUS-INTRO-SCRIPTS-62.md)).

### Dialogue

- **Dialogue choices are rows to pick.** A choice in a conversation shows as rows in the conversation text, picked by row
  with the mouse or the keys, and each one leads to the answer the original gives, such as paying only when you have the
  gold. A check over every Choice branch of the three masters goes with it (`DIALOGUE-CHOICES-62`).
- **Links stay clickable.** A topic link in the conversation text worked once and then clicks stopped, because the set of
  linkable topics was rebuilt only while the topic list showed. The set now follows the topic list after every change in
  every mode, and clicks, Enter and the arrow keys ask the topic exactly as the list does.
- **Only answered topics light up.** A word is drawn and answered as a link only when its topic is in the current topic
  list (the topics the player knows that this speaker answers), as in the original, and it must end the word (no longer
  "plan" inside "Plantation"; a plural still links). Over every response of the three masters the links went from 79,265
  to 75,200; the 4,065 removed end inside a longer word. Topic colours are speaker-specific and mark an exhausted topic,
  behind one switch that is on by default.
- **Thin scroll bars** (3 pixels) on the text pane and the topic list, always drawn: dim when the pane fits, lit with a
  thumb sized to the content when it overflows. Arrow ends step a line, a click above or below the thumb pages, the
  thumb drags, and Page Up and Down and the arrow keys keep working
  ([DIALOGUE-LINKS-62](../../bugs/DIALOGUE-LINKS-62.md), `DIALOGUE-SCROLLBARS-62`).
- **Persuasion works again.** Admire, Intimidate, Taunt and the bribes had opened or changed enchanting pages, because both
  used the same list codes. The persuasion rows have their own range (`PERSUASION-BROKEN-62`).
- **A fight that an answer sets.** A speaker whose answer sets Fight to 100 and says Goodbye now attacks when the talk
  closes, and an answer's StartCombat starts the fight at once; the three masters hold 343 answers that start combat. A
  check over every answer of the game covers fights from dialogue (`DIALOGUE-AGGRO-62`).

### Crime

- **Guards who see a crime come to arrest.** The rules of the original are written for every kind of crime, not only
  theft: assault (the first blow or harmful spell on a character who is not hostile), murder, and sleeping in or trespassing
  at someone else's bed. A guard who reports a crime is marked Alarmed, follows the player and talks when near and in
  sight, also in the opening's census office, whose guard's own greeting for a crime during character creation can now be
  chosen. A bounty over the crime threshold makes a guard pursue on sight, and ten times it makes him attack.
- **The arrest dialogue.** Paying the fine takes the gold (the compiler had set the explicit reference before the count, so
  the guard paid instead of the player), calms every character that reacted to the crimes paid for and puts the stolen
  goods in the nearest prison's evidence chest. Resisting arrest makes the guard attack. Jail passes the days as a rest,
  changes a skill a day by the original's rule and lets the player out at the nearest prison marker, with every changed
  skill listed. The crimes' numbers are saved with the player's standing, and older saves still load.
- **Pursuers and marks are saved.** A guard who is pursuing the player, and the marks a crime leaves on people, are kept in
  saved games (`CRIME-SAVE-PURSUERS-62`).
- Test aids: `aw_placed crime kill REF` and `aw_placed crime hit REF`, and `dbg kill crime`.
- Not yet: pickpocketing and picking an owned lock have their rules but no event (there is no pickpocket window and no
  lockpicks yet) (`CRIME-ONLY-THEFT-62`).

### Creatures, characters and bodies

- **The creatures placed in rooms are built and placed.** Ghosts, skeletons, rats, kwama and the other creatures the
  game places in tombs, caves, mines and other rooms are now in the rooms: the build counts 228 creature records built
  (100 in v0.0.61) and 527 of the 904 room placements (4 in v0.0.61). A creature comes back after its death only when its
  record says it respawns. A creature model stays under 600 triangles; with every room creature in view the rooms that
  have them draw 3.4 percent more triangles (median room 3.2 percent), which is decided for the project in crowded
  rooms. In Thelas Ancestral Tomb with an ancestor ghost close in view the frame rate was 66.9 against 69.9 without the
  creatures (`TOMB-NO-CREATURES-61`, `INTERIOR-CREATURES-MISSING-41`). Three placements in Balmora houses wait for the
  town's conversion, and the intro tombs' levelled creatures are not placed yet
  ([ROOM-LEVELLED-INTRO-ROOMS-62](../../bugs/ROOM-LEVELLED-INTRO-ROOMS-62.md)).
- **The creature census** on [CREATURES](../../CREATURES.md) counts every creature record of the three masters: 396
  records; the 136 creatures of Tribunal and Bloodmoon are not built yet
  ([CREATURE-EXPANSION-62](../../bugs/CREATURE-EXPANSION-62.md)). Creatures that resist normal weapons take no harm
  from an iron weapon and the game says so; silver, magical and enchanted weapons still hurt them.
- **A new body reduction method, used for the characters of this release.** The method measures every reduced model
  against its original (each seam between two parts, each limb's thickness), locks the seams, keeps each limb a minimum
  thickness, gives every body part its share beside a large hair or helmet, and merges the pieces of one armour slot. The
  characters are baked with the new seam and floor method. Measured on 65 bodies, the number passing at today's total went
  from 20 to 31, and limbs under half their width over every sixth character from 162 to 7. Pages:
  [MODEL_REDUCTION](../../MODEL_REDUCTION.md), [AMIWIND_TOOLKIT](../../AMIWIND_TOOLKIT.md) (`MESH-SEAM-METHOD-62`,
  `NPC-BODY-REGRESSION-62`, `NPC-JOINT-GAPS-33`, [CREATURE-MESH-HOLES-62](../../bugs/CREATURE-MESH-HOLES-62.md)).
- **The Imperial guard has a face entry again.** The generic Imperial guard (two of them stand in Seyda Neen) gets its entry
  in the master builder's list of per-model face budgets: 963 triangles, against 606 in v0.0.62-dev1. This was decided for
  the project, to keep the seam at the guard's joints closed.
- **The Alit with every seam point locked** has no new open edge at 792 faces, its entry 475 / +319 / 794; the list of
  per-model face entries was measured for 14 creatures and a character. A player part that overflows the vertex budget is
  baked again at smaller caps instead of dropped, and the Tarhiel robe's chest part now bakes on the human skeleton; on the
  beast skeleton it is baked without whole panels where no edge opens (`ROBE-PART-NOT-BAKED-62`).
- **Summoned creatures.** The 16 summoned creatures of the game (the settings of the masters, including those with a
  space in their id, such as the golden saint and the winged twilight) are built, and a summoning effect on the player
  calls its creature up 120 game units in front of the caster. It follows the player, comes back beside him after a door or
  a load, and goes with a flash when the effect ends; when it dies, the effect ends and its body goes a few seconds later.
  Its first frame reads its files and took 570 ms on FS-UAE at 32 MB Fast RAM (`SUMMON-SPAWN-FRAME-62`). It does not yet
  fight for the player ([CREATURE-SUMMONED-62](../../bugs/CREATURE-SUMMONED-62.md), `COMBAT-SUMMON-ALLY-62`). The test route
  is in [MAGIC_EFFECTS](../../MAGIC_EFFECTS.md).
- **Held items use their own model.** An item held by a guard or another character always uses its own item model, also
  after a reload of the same world (`HELD-WEAPON-WRONG-MODEL-62`).

### Flora

- **The bracket fungi on the Bitter Coast trees can be picked** like the ground mushrooms, with the same pick, sound
  and saved state: 813 placements (724 outdoors). Saves made before keep their picks. A census of all harvestable plants
  runs on every build and classifies the 25,695 organic placements; the rest of the plants, the egg sacks and the ore
  rocks are listed as pending ([HARVEST-TREE-FUNGUS-62](../../bugs/HARVEST-TREE-FUNGUS-62.md),
  [HARVEST-ORE-ROCKS-62](../../bugs/HARVEST-ORE-ROCKS-62.md),
  [HARVEST-EXPANSION-FLORA-62](../../bugs/HARVEST-EXPANSION-FLORA-62.md)).

### The player's gear, the use key and the windows

- **Double-click in the inventory.** What can be worn goes on or comes off at once, with an Equipped or Unequipped notice
  box; a book is read; an apparatus opens alchemy; a potion or an ingredient asks first in a box with OK and Cancel and,
  for a stack, a count slider and a number field (`INVENTORY-DOUBLECLICK-62`). The inventory window refreshes when
  something outside it changes the carried or worn items.
- **The V key lights only an equipped light.** An equipped torch takes the carried-left slot only and is drawn on the
  assembled body, so a torch no longer hides the helm and every other worn piece. `dbg torch` (also `give dbgtorch`) adds a
  never-burning debug torch (`TORCH-HIDES-HELM-62`).
- **The use key takes the nearest thing along the view.** An item, container or plant under the crosshair could not be used
  when a character or a body stood close. The use now goes to the nearest thing along the view ray within the activation
  distance, as in OpenMW; an actor wholly in front of the item is still talked to or searched
  (`FOCUS-NPC-OVERRIDES-ITEM-62`).
- **Item pictures in the container window.** Every item with an icon shows its picture in the inventory and container
  windows with one slot fit, empty slots are black, Take All, Close, OK, Cancel and the class window use the same thin
  button, and taking an item prints a Took line in the name-label style (`ITEM-ICONS-MISSING-62`, `UI-THIN-BUTTON-62`,
  `CONTAINER-TAKE-NO-CONFIRM-62`).
- **Beast races are refused helmets and footwear** with the game's own lines; a build check goes over every worn part of
  every skeleton. The inventory offers Equip or Unequip by item class, and a scripted wearable (the Census Office dagger)
  can be equipped unless its script forbids it. Every weapon, armour piece and piece of clothing can be equipped from the
  inventory again. Books and scrolls offer Read in the inventory
  ([EQUIP-ACTION-REGRESSION-62](../../bugs/EQUIP-ACTION-REGRESSION-62.md)).
- **One list rule for every list window.** Up and Down and W and S and the wheel move the selection, Page Up and Down a
  page, Home and End the ends, and the list scrolls with it. The cursor keys no longer carry an Amiga qualifier on the game
  screen: a lost key-up from the host had made the keyboard mouse take every menu's arrow keys
  ([INVENTORY-ARROWS-SCROLL-62](../../bugs/INVENTORY-ARROWS-SCROLL-62.md)).
- **The class and birthsign lists** have one hint row per window, a Cancel button that does what Esc does, rules above and
  below the skill lists, and scroll triangles (dim when there is no more) in place of the text mark
  ([CLASS-LIST-LAYOUT-62](../../bugs/CLASS-LIST-LAYOUT-62.md)).
- **Long door names.** A door's name over 35 characters continues in the focus row's id field, up to 66 characters.
  Options > Prefs > Name labels (`dbg ui namelabels`) chooses AmiWind (the title and action below the view, the default)
  or Morrowind (the framed box only) ([INFO-BOX-TEXT-CUT-62](../../bugs/INFO-BOX-TEXT-CUT-62.md)).
- **Combat block.** The original's automatic block is the default again; holding to block stays an option
  (`COMBAT-BLOCK-DEFAULT-62`).
- **Levelling in play.** A tapped jump counts for Acrobatics, the skill-raise line stays on screen for 3 seconds, a landing
  that hurts is an Acrobatics use, and the first read of a skill book raises its skill by one (`LEVEL-UP-INGAME-62`,
  `SKILL-BOOKS-MISSING-62`).

### Debug commands and test tools

Every command below is in the in-game `dbg help` menu, in `config/debug-commands.txt` and in
[AMIWIND_CONSOLE_COMMANDS](../../AMIWIND_CONSOLE_COMMANDS.md).

- **`dbg give`** opens an item picker over the whole catalogue (name with the record id beside it, kinds as groups, then a
  count); `dbg give ID [N]` gives an item, `dbg give money`, `coin` or `rich` gives gold (1,000,000 by default), and
  `dbg additem` works as well. Gold is kept to a limit of 999,999,999 on every gain (`DBG-GIVE-MONEY-62`).
- **`dbg noburden`** (also `unburdened`, `noweight`) removes the carrying limit: the load counts as 0 in every movement,
  fatigue and rest rule, and the burden bar shows the load over 999999. It prints a message on and off, is not saved and
  is off after a New Game (`DBG-NOBURDEN-62`).
- **`dbg superspeed`** gives endless stamina and reads Speed, Athletics and Acrobatics as 100 while on
  (`DBG-SUPERSPEED-62`). Every on/off debug command now turns the other way when it is typed bare (the debug overlays, hud,
  music, footsteps, doorlocks, daynight, creatures, casting and the settings routes among them), checked over the whole
  catalogue; the camera and cast routes keep their own word (`DBG-SUBWORD-ROUTE-DROPPED-62`).
- **`dbg setlvl`** (also `setlevel`) sets the level, 1 to 83, with a list box when typed alone; **`dbg restorestats`** and
  **`dbg maxstats`** go through the levelling command and show the sheet before and after (`DBG-STATS-COMMANDS-62`).
- **The recorder:** Ctrl+R works in every window while it is armed, and every random stream is seeded from the recording,
  so a fight recording replays exactly (10 of 10 checkpoints, 0.0 units off). The benchmark writes its result file with
  the frame times and the drawing and disk time apart. A MiniWind session starts in its image's own map, and `dbg tp`
  works inside the loaded map of a small test image.
- **Long debug listings no longer stall a frame.** The console prints are collected and written twice a second instead of
  one by one ([SESSION-STALL-AFTER-LONG-FRAME-62](../../bugs/SESSION-STALL-AFTER-LONG-FRAME-62.md),
  [REMOTE-CONSOLE-LOG-COST-32](../../bugs/REMOTE-CONSOLE-LOG-COST-32.md)).

### Builder

- **Every finished unit is kept the moment it is done.** The image step's player view stored its finished bodies only when
  its whole pool map ended, so a step that stopped midway kept none of them and every resume baked every player body
  again. Each unit now goes into the checksummed unit cache as it comes back, a failing unit is named and the rest kept,
  and the unit key covers only the code the bake runs, so a change elsewhere in the step keeps every stored body. Units
  stored under the earlier key are found under it while the bake code is unchanged
  ([UNIT-STORED-AT-MAP-END-62](../../bugs/UNIT-STORED-AT-MAP-END-62.md)). A build test fails when any stage stores its
  units only after a whole pool map.
- **The player view prints `[done/total]`** for every unit as it comes back, with its time, and the cached count at the
  start.
- One cave resident who no longer fits his floor with the new character bodies is kept where the game data puts him, as
  his two neighbours in the same cave are (`ACTOR-CONTACT-NEW-BODY-62`).

### Register

Reports from the playtests and the following days were entered in the register; they are not fixed in this release: lava
in god mode, breath under water, the world buttons, floating creatures, the date form, the firepit flames, the enemy
health bar, the animations of creatures and characters without walk or attack animations, holes in the ash trees, combat
style presets and the arena opponent picker (`GODMODE-LAVA-DEATH-62`, `UNDERWATER-BREATH-62`, `WORLD-BUTTONS-62`,
`CREATURE-FLOATING-62`, `LORE-DATE-FORMAT-62`, `CHIM-EXTERIOR-FLAMES-MISSING-48`, `ENEMY-HEALTH-BAR-62`,
`CREATURE-BIPED-ANIMS-62`, `ASH-TREE-HOLES-62`, `COMBAT-STYLE-PRESETS-62`, `DBG-ARENA-PICKER-62`).

## Needs 32 MB Fast RAM

The game needs 32 MB of Fast RAM. At 16 MB parts run and over-limit interiors show the warning box.

## Not yet seen in game

These are checked after the release, on the v0.0.63 builds. This release's new fixes were checked by tests, not yet in
play:

- A teleport to a room that does not load (the Heart Chamber with `dbg tp`, and `dbg loadfail`); `dbg restartgame` and a
  New Game from the menu, twice.
- A new game in the census office on the new path: the clerk's windows, the captain through the dialogue window, the door
  guard and the hall door, the papers and the ring.
- Dialogue choices in play (for example paying only with the gold), a link clicked twice and then another, persuasion,
  and a refused demand that ends in a fight.
- A theft, an assault and a murder seen by a guard after the test session of Seyda Neen; a save during a pursuit.
- The seams of the reduced bodies in play, and the Imperial guard at 963 triangles: the numbers above are measurements of
  the models, not of a play session. A guard's own weapon after a reload.
- The summoned creatures and the use key's new choice; a double-click on armour, a book, a potion and a stack of
  ingredients; the debug commands on screen.
- Alchemy in a full play session, Tarhiel's fall seen from the road, the rooms' creatures, and frame times of all of this
  on the Raspberry Pi 4B.
- Carried over from v0.0.61: the Ebonheart lantern outdoors, a weapon that casts on strike used by a non-player
  character, the shore wall pose in Seyda Neen, the glass lantern in first person, the first-person bow, crossbow and
  thrown stances, and Until Healed after damage.

## Known in this build

- The Heart Chamber's own load failure is recovered but not repaired: the room may still not load at 32 MB Fast RAM
  ([CHIM-ROOM-HEART-CHAMBER-LOAD-50](../../bugs/CHIM-ROOM-HEART-CHAMBER-LOAD-50.md)); the Heart of Lorkhan is
  not drawn with its textures and does not beat yet.
- 619 of the game's 1,207 scripts do not run yet. Pickpocketing, picking an owned lock and a summoned creature that fights
  for the player are not done. Thirteen scripts of the census office opening are still hand-written. A script cannot place
  a levelled list ([MWSCRIPT-PLACE-OTHER-KINDS-62](../../bugs/MWSCRIPT-PLACE-OTHER-KINDS-62.md)).
- A hard landing does not knock down the player or an actor
  ([FALL-LANDING-KNOCKDOWN-62](../../bugs/FALL-LANDING-KNOCKDOWN-62.md)).
- The register entries named under "Register" above are open. The fix for a held weapon that showed a wrong model
  ([HELD-WEAPON-WRONG-MODEL-62](../../bugs/HELD-WEAPON-WRONG-MODEL-62.md)) is checked by tests only. A corpse's clothes are
  not updated (`CORPSE-CLOTHES-NOT-UPDATED-62`).
- The ore and gem rocks cannot be mined, and the plants of the add-on masters cannot be picked. The creatures of Tribunal
  and Bloodmoon are not built; Addamasartus and Tharys Ancestral Tomb have no levelled creatures yet.
- From [v0.0.61](RELEASE-v0.0.61.md): a dropped light gets no flame; a Shield effect does not soften blows; an ended
  Fortify effect counts as damage; the worn Constant Effect items of non-player characters are not applied; the trip from
  Seyda Neen to Balmora sometimes stalls on the loading screen in the emulator
  ([CHIM-SEYDA-BALMORA-LOAD-HANG-43](../../bugs/CHIM-SEYDA-BALMORA-LOAD-HANG-43.md)); some rooms still load in after you
  arrive ([CHIM-ROOM-POPIN-51](../../bugs/CHIM-ROOM-POPIN-51.md)).

## Moved to v0.0.63

Pickpocketing and picking owned locks, enchanting at an altar and spellmaking, the rest of the game's scripts, per-area
data tables for containers, doors, items, activators and creatures, outdoor items that can be picked up, dropped lights
with their flame, the worn Constant Effect items of non-player characters, summoned creatures that fight for the player,
and the in-game check of the pieces listed above. The list is in the [roadmap](../../ROADMAP.md).
