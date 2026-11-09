# AmiWind v0.0.62-dev2 (in development)

_Last updated with AmiWind v0.0.62 (8 November 2026)._

**This snapshot was not delivered.** Its builds failed. A third snapshot (dev3) was to follow and became the release
[v0.0.62](RELEASE-v0.0.62.md), which carries this snapshot's work. One point below is superseded there: in v0.0.62 the
characters are baked with the new seam and floor method, and the Imperial guard has a face entry of 963 triangles.

Development snapshot, 7 November 2026, in development. Running on CHIM Engine v0.2.2. Previous release:
[v0.0.61: Keep Your Lantern Lit](RELEASE-v0.0.61.md). Previous snapshot: [v0.0.62-dev1](RELEASE-v0.0.62-dev1.md).

The second snapshot of v0.0.62. A room that fails to load no longer locks the game, and a New Game starts from a clean
state. The census office runs the game's own scripts, the captain talks through the dialogue window, and persuasion
works again. Guards who see a crime come to arrest, and the arrest, fine and jail follow the original. Dialogue links
stay clickable, the bodies of characters are measured at their joints when their models are reduced, and the
inventory, class and container windows were reworked. The game needs 32 MB of Fast RAM, and the emulator presets of this
snapshot have it.

## Checked in game

This snapshot's own image was not played yet. The changes below were tested by the build's own checks and by the
tests that come with each change. During the work, the fine, resisting arrest, a guard's attack on sight at a high bounty and the jail
were seen working in a test image of Seyda Neen (the guard's Pay Gold took 40 gold, Resist Arrest made the guard attack,
a bounty of 10,000 made a guard attack on sight, and jail passed 15 days and let the player out at the prison marker);
the fixes to the crime rules that came after that session are not seen yet. What was not seen in play is listed under
"Not yet seen in game".

## New since v0.0.62-dev1

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
  and the CHIM engine version.
- **`dbg memcensus`** prints the free Fast RAM, its largest block, the map and the Hunk in use, in one line.
- **The console pager.** `dbg`, `dbg help` and `dbg help WORD` show one console screen at a time.
- **The mouse pointer in message boxes.** Every message box (the scripts' boxes, the failed-load box and the death box)
  shows the pointer and takes clicks on its buttons ([MSGBOX-NO-CURSOR-62](../../bugs/MSGBOX-NO-CURSOR-62.md)).
- **A New Game starts as the first did.** A New Game from the menu had kept the script interpreter's instances, locals,
  timers and running scripts of the game before, and the session tables that a load resets (standing and crime,
  effects, actor packages, merchants, made items, gems, faction reactions, revealed places, topic pages, forced sneak and
  fades, the object state). New Game and `dbg restartgame` now reset through one registry, and the console names any state
  that differs from a fresh start. Page: [GAME_STATE_RESET](../../GAME_STATE_RESET.md)
  ([NEWGAME-STATE-RESET-62](../../bugs/NEWGAME-STATE-RESET-62.md)).

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
  opens his conversation. The interpreter carries out 326 functions
  ([CENSUS-INTRO-SCRIPTS-62](../../bugs/CENSUS-INTRO-SCRIPTS-62.md)).
- The count of the MWScript tracker is now 499 of 1,207 scripts running (479 in dev1), 107 use a function the interpreter
  lacks (130), 44 are attached, not run, 557 are compiled, not attached; 7,410 of 7,411 dialogue results run whole. The
  scripts also gained Resurrect, Drop and HurtStandingActor, and the placing functions now make a character that has no
  placed reference, and an activator, static or container from a placed reference of its record
  (`MWSCRIPT-PLACE-NO-MODEL-62`). The game's lava script now hurts the player standing on its object.

### Dialogue

- **Links stay clickable.** A topic link in the conversation text worked once and then clicks stopped, because the set of
  linkable topics was rebuilt only while the topic list showed. The set now follows the topic list after every change in
  every mode, and clicks, Enter and the arrow keys ask the topic exactly as the list does.
- **Only answered topics light up.** A word is drawn and answered as a link only when its topic is in the current topic
  list (the topics the player knows that this speaker answers), as in the original, and it must end the word (no longer
  "plan" inside "Plantation"; a plural still links). Over every response of the three masters the links went from 79,265
  to 75,200; the 4,065 removed end inside a longer word.
- **Thin scroll bars** (3 pixels) on the text pane and the topic list, always drawn: dim when the pane fits, lit with a
  thumb sized to the content when it overflows. Arrow ends step a line, a click above or below the thumb pages, the
  thumb drags, and Page Up and Down and the arrow keys keep working
  ([DIALOGUE-LINKS-62](../../bugs/DIALOGUE-LINKS-62.md), `DIALOGUE-SCROLLBARS-62`).
- **Persuasion works again.** Admire, Intimidate, Taunt and the bribes had opened or changed enchanting pages, because both
  used the same list codes. The persuasion rows have their own range (`PERSUASION-BROKEN-62`).
- **A fight that an answer sets.** A speaker whose answer sets Fight to 100 and says Goodbye now attacks when the talk
  closes, and an answer's StartCombat starts the fight at once; the three masters hold 343 answers that start combat
  (`DIALOGUE-AGGRO-62`).
- Not done yet: dialogue choices and the outcomes that depend on them. They lead the next landmark of the scripting work
  (`DIALOGUE-CHOICES-62`).

### Crime

- **Guards who see a crime come to arrest.** The rules of the original are written for every kind of crime, not only
  theft: assault (the first blow or harmful spell on a character who is not hostile), murder, and sleeping in or trespassing
  at someone else's bed. A guard who reports a crime is marked Alarmed, follows the player and talks when near and in
  sight, also in the opening's census office, whose guard's own greeting for a crime during character creation can now be
  chosen. A bounty over the crime threshold makes a guard pursue on sight, and ten times it makes him attack.
- **The arrest dialogue.** Paying the fine takes the gold (the compiler had set the explicit reference before the count, so
  the guard paid instead of the player), calms every character that reacted to the crimes paid for and puts the stolen
  goods in the nearest prison's evidence chest. Resisting arrest makes the guard attack. Jail passes the days as a rest,
  changes a skill a day by the original's rule and lets the player out at the nearest prison marker. The crimes' numbers
  are saved with the player's standing, and older saves still load.
- Test aids: `aw_placed crime kill REF` and `aw_placed crime hit REF`, and `dbg kill crime`.
- Not yet: pickpocketing and picking an owned lock have their rules but no event (there is no pickpocket window and no
  lockpicks yet) (`CRIME-ONLY-THEFT-62`).

### Characters, bodies and creatures

- **A new body reduction method, in the code but not used for this snapshot's characters.** The method measures every
  reduced model against its original (each seam between two parts, each limb's thickness), locks the seams, keeps each
  limb a minimum thickness, gives every body part its share beside a large hair or helmet, and merges the pieces of one
  armour slot. Measured on 65 bodies, the number passing at today's total went from 20 to 31, and limbs under half their
  width over every sixth character from 162 to 7. In the full build it did not yet bake every character of the game
  within the model format's budget, so this snapshot's characters are reduced as in v0.0.62-dev1, and the stick-thin
  limbs and joint gaps reported for v0.0.62-dev1 remain. The method returns when it bakes the whole cast. Pages:
  [MODEL_REDUCTION](../../MODEL_REDUCTION.md), [AMIWIND_TOOLKIT](../../AMIWIND_TOOLKIT.md) (`MESH-SEAM-METHOD-62`,
  `NPC-BODY-REGRESSION-62`, `NPC-JOINT-GAPS-33`, [CREATURE-MESH-HOLES-62](../../bugs/CREATURE-MESH-HOLES-62.md)).
- **The Alit with every seam point locked** has no new open edge at 792 faces, its entry 475 / +319 / 794; the list of
  per-model face entries was measured for 14 creatures and a character. A player part that overflows the vertex budget is
  baked again at smaller caps instead of dropped, and the Tarhiel robe's chest part now bakes on the human skeleton
  (`ROBE-PART-NOT-BAKED-62`).
- **Summoned creatures.** The 16 summoned creatures of the game (the settings of the masters, including those with a
  space in their id, such as the golden saint and the winged twilight) are built, and a summoning effect on the player
  calls its creature up 120 game units in front of the caster. It follows the player, comes back beside him after a door or
  a load, and goes with a flash when the effect ends; when it dies, the effect ends and its body goes a few seconds later.
  It does not yet fight for the player ([CREATURE-SUMMONED-62](../../bugs/CREATURE-SUMMONED-62.md),
  `COMBAT-SUMMON-ALLY-62`). The test route is in [MAGIC_EFFECTS](../../MAGIC_EFFECTS.md).
- **The falling mage** is released in the tick his platform goes, and a held actor is drawn over the fog past the draw
  distance, so a scripted fall can be seen. The falling mage's script fires at the original's 2000 units again
  (`SCRIPTED-EVENT-PAST-DRAW-DISTANCE-62`).

### The player's gear, the use key and the windows

- **The V key lights only an equipped light.** An equipped torch takes the carried-left slot only and is drawn on the
  assembled body, so a torch no longer hides the helm and every other worn piece. `dbg torch` (also `give dbgtorch`) adds a
  never-burning debug torch (`TORCH-HIDES-HELM-62`).
- **The use key takes the nearest thing along the view.** An item, container or plant under the crosshair could not be used
  when a character or a body stood close. The use now goes to the nearest thing along the view ray within the activation
  distance, as in OpenMW; an actor wholly in front of the item is still talked to or searched. The prompt, the use key and a
  body's search ask the same choice (`FOCUS-NPC-OVERRIDES-ITEM-62`).
- **Item pictures in the container window.** Every item with an icon shows its picture in the inventory and container
  windows with one slot fit, empty slots are black, Take All, Close, OK, Cancel and the class window use the same thin
  button, and taking an item prints a Took line in the name-label style (`ITEM-ICONS-MISSING-62`, `UI-THIN-BUTTON-62`,
  `CONTAINER-TAKE-NO-CONFIRM-62`).
- **Beast races are refused helmets and footwear** with the game's own lines; a build check goes over every worn part of
  every skeleton. The inventory offers Equip or Unequip by item class, and a scripted wearable (the Census Office dagger)
  can be equipped unless its script forbids it. Books and scrolls offer Read in the inventory
  ([EQUIP-ACTION-REGRESSION-62](../../bugs/EQUIP-ACTION-REGRESSION-62.md)).
- **One list rule for every list window.** Up and Down and W and S and the wheel move the selection, Page Up and Down a
  page, Home and End the ends, and the list scrolls with it; the inventory uses it first. The cursor keys no longer carry an
  Amiga qualifier on the game screen: a lost key-up from the host had made the keyboard mouse take every menu's arrow
  keys ([INVENTORY-ARROWS-SCROLL-62](../../bugs/INVENTORY-ARROWS-SCROLL-62.md)).
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

### Register

Reports from the playtest of dev1 and the following days were entered in the register; they are not
fixed in this snapshot: lava in god mode, breath under water, the world buttons, `dbg superspeed`, floating creatures, the
date form, the firepit flames, the enemy health bar, the animations of creatures and characters without walk or attack
animations, holes in the ash trees, combat style presets and the arena opponent picker (`GODMODE-LAVA-DEATH-62`,
`UNDERWATER-BREATH-62`, `WORLD-BUTTONS-62`, `DBG-SUPERSPEED-62`, `CREATURE-FLOATING-62`, `LORE-DATE-FORMAT-62`,
`CHIM-EXTERIOR-FLAMES-MISSING-48`, `ENEMY-HEALTH-BAR-62`, `CREATURE-BIPED-ANIMS-62`, `ASH-TREE-HOLES-62`,
`COMBAT-STYLE-PRESETS-62`, `DBG-ARENA-PICKER-62`).

## Needs 32 MB Fast RAM

The game needs 32 MB of Fast RAM. At 16 MB parts run and over-limit interiors show the warning box.

## In-game checklist for this snapshot

- A teleport to a room that does not load (the Heart Chamber with `dbg tp`, and `dbg loadfail`): the player is back where he
  started, the message box shows the pointer, OK and Load Game work.
- `dbg restartgame` and a New Game from the menu, twice: the second game starts as the first did; `dbg ver`, `dbg memcensus`
  and the pager in `dbg help`.
- A new game in the census office: the clerk's windows, the captain through the dialogue window, the door guard and the
  hall door, the papers and the ring, the barrel and the doors; `dbg census legacy 1` for the old path.
- Dialogue: a link clicked twice and then another, only known and answered topics lit, the scroll bars, persuasion
  (Admire, Intimidate, Taunt, a bribe), a refused demand that ends in a fight.
- A theft, an assault and a murder seen by a guard: he arrives and talks; pay the fine, resist arrest, go to jail, a
  bounty of 10,000.
- Characters: Jiub and the guards of the prison ship, Sellus Gravius, a guard in bracers and pauldrons, the Alit.
- A summoning spell: the creature appears in front of the caster, follows, and goes with the effect.
- A torch equipped with a helm worn; the use key beside a character with an item under the crosshair; item pictures and the
  Took line in a container; a beast race with a helmet; Read on a book.
- Lists with the keyboard and the wheel in the inventory and the class windows; a door with a long name.
- Carried over from dev1: the alchemy window, Tarhiel's fall (now released in the tick the platform goes, and drawn past the
  draw distance), the rooms' creatures and their frame times on the Raspberry Pi 4B.

## Not yet seen in game

- Everything on the checklist above. The failed-load recovery was exercised with the forced-failure test aid (`dbg loadfail`), not with
  the Heart Chamber itself.
- The census office on the new path in a full new game, and the crime rules after the test session of Seyda Neen.
- The seams of the reduced bodies in play; the numbers above are measurements of the models, not of a play session.
- The summoned creatures and the use key's new choice.
- The frame times of any of this on the Raspberry Pi 4B.

## Known in this build

- The character bodies of this snapshot are reduced with the rules of v0.0.62-dev1. The new method that locks the
  seams between body parts and keeps every limb a minimum thickness is in the code, but did not yet bake every character
  of the game within the model format's budget; it returns when it does. The joint gaps listed for v0.0.62-dev1 remain.
  One model differs from v0.0.62-dev1 even so: the generic Imperial guard (two of them stand in Seyda Neen) has 1,022
  triangles instead of 606; the cause is being looked into.
- The Heart Chamber's own load failure is recovered but not repaired: the room may still not load at 32 MB Fast RAM
  ([CHIM-ROOM-HEART-CHAMBER-LOAD-50](../../bugs/CHIM-ROOM-HEART-CHAMBER-LOAD-50.md)); the Heart of Lorkhan is
  not drawn with its textures and does not beat yet.
- Dialogue choices and the outcomes that depend on them are not done yet. Pickpocketing, picking an owned lock and a summoned
  creature that fights for the player are not done.
- Thirteen scripts of the census office opening are still hand-written. A script cannot place a levelled list
  ([MWSCRIPT-PLACE-OTHER-KINDS-62](../../bugs/MWSCRIPT-PLACE-OTHER-KINDS-62.md)).
- A hard landing does not knock down the player or an actor
  ([FALL-LANDING-KNOCKDOWN-62](../../bugs/FALL-LANDING-KNOCKDOWN-62.md)).
- The register entries named under "Register" above are open. The held weapon can show a wrong model
  ([HELD-WEAPON-WRONG-MODEL-62](../../bugs/HELD-WEAPON-WRONG-MODEL-62.md)) and the release line after jail is cut (`CRIME-RELEASE-LINE-CUT-62`).
- The robe's chest part still does not fit on the beast skeleton and stays listed; a corpse's clothes are not updated
  (`CORPSE-CLOTHES-NOT-UPDATED-62`).
- From [v0.0.62-dev1](RELEASE-v0.0.62-dev1.md) and [v0.0.61](RELEASE-v0.0.61.md): the ore and gem rocks cannot be mined and the
  plants of the add-on masters cannot be picked; the creatures of Tribunal and Bloodmoon are not built; a dropped light
  gets no flame; a Shield effect does not soften blows; an ended Fortify effect counts as damage; the worn Constant Effect
  items of non-player characters are not applied; the trip from Seyda Neen to Balmora sometimes stalls on the loading
  screen in the emulator ([CHIM-SEYDA-BALMORA-LOAD-HANG-43](../../bugs/CHIM-SEYDA-BALMORA-LOAD-HANG-43.md)); some rooms still
  load in after you arrive ([CHIM-ROOM-POPIN-51](../../bugs/CHIM-ROOM-POPIN-51.md)).
