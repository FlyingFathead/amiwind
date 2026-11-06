# AmiWind v0.0.58: Time To Talk

Release, 1 November 2026. Running on CHIM Engine v0.2.2. Previous release: [v0.0.57](RELEASE-v0.0.57.md).

v0.0.58, "Time To Talk", is the conversation and the character: most of the original's dialogue window now works
(links, persuasion, services, choices, journal links), character creation at the Census and Excise Office follows the
original's pages, and you can aim at things, take them, read books and sneak. The game needs 32 MB of Fast RAM, and the
emulator presets of this release have it. This release is the sixth development snapshot of v0.0.58 (dev6) with its final version
number: what was planned beyond it moves, openly, to v0.0.59.

## Checked in game

The dev6 snapshot was played in game before this release. Confirmed: character creation runs in order, with the chosen
name on the review sheet, the class questions button greyed out when the install has no question data and the birthsign
page with its art; the game's scripts load (8,618 kept, none refused); E steals an owned item (the red "E: Steal") and it
stays taken through a normal save and load; creatures get no aim box; residents walk by their Wander packages; and the
debug restart from the main menu starts outdoors. Not yet checked in game is listed at the end of these notes.

## New since v0.0.57

### Dialogue

- **Links in the conversation.** Topic names in an answer show as links, made by the builder with OpenMW's rule; a
  click, or Tab and Enter, asks about that topic.
- **Persuasion.** Admire, Intimidate, Taunt and Bribe 10, 100 or 1000, with the original's rules; bribes you cannot pay
  are greyed out. Disposition also decides when a character attacks, in the conversation and in the world.
- **Services from the conversation.** Travel, Training, Spells, Barter (buy and sell, one thing at a time), Repair and
  Spellmaking, each refused when the character's own refusal answer applies. Things you sell to a merchant who does
  not stock them can be bought back. Every word in these windows is the game's own text.
- **Enchanting** at an enchanter: name the item, pick a filled soul gem, choose how it casts and its effects, with the
  original's limits and prices. Soul gems keep their souls, and spells you make are kept in your saved game.
- **Answers that do things.** The scripts attached to answers run when the answer is shown: choices to pick from,
  conversations that end with only Goodbye, and answers that change how factions regard each other. Places an answer
  reveals on the map are remembered for when the map shows them.
- **The greeting is picked at talk time,** and the spoken greeting follows the one picked; characters greet by the
  original's first-match rule, and several can greet at once in a crowd. The known topics follow the saved set.
- **The journal's topic pages** reach the dialogue, exhausted topics are drawn dimmer, topic names on those pages are
  links that open the topic, and a "journal updated" notice shows whenever a quest advances (without a sound, as in
  OpenMW). Links inside the dated quest entries come later.
- **Faction rank and conditions.** Rank requirements come from the factions' rank tables and the rank difference from
  the player's own rank. Same sex, same race and "should attack" are read live; disease, a drawn weapon and the Charm
  effect count in the disposition.

### Character creation

- **The class page** is a scrolled, clickable list with the class's specialization, favoured attributes and major and
  minor skills beside it.
- **The birthsign page** lists the signs with each sign's abilities, powers and spells by name.
- **The class questions** of the install's `Morrowind.ini` run through a stage of their own, and the player can make a
  class of their own.
- **The review sheet** shows name, level, race, class, sign, health, magicka and fatigue.

### The world

- **The aim box.** Aiming at something within reach shows a framed box. For an item it holds the name, the weight and
  the value, and the name is red when the item is owned; a door shows its name or,
  when it leads outside, the place it leads to. It works in rooms and outdoors.
- **Placed items can be picked up.** E on an aimed item that the room draws as an object takes it into the inventory,
  and the taking is kept in the saved object state.
- **E: Take and E: Steal.** An aimed item that can be taken shows "E: Take", or a red "E: Steal" when it is owned, with
  the wording of the game's own take string. Plants keep their "E: Pick".
- **Books and letters are read in place.** A readable book or letter shows "E: Read" (red when owned) and opens a
  reader that pages the text, with "E: Take" (red "E: Steal" when owned) and "Esc: Close". Magic scrolls are taken
  directly. A builder stage of its own prepares the texts of the books (445 books).
- **The Census and Excise Office's small items** are placed objects, so they are drawn, aimed at and taken. Equal items
  share one model, which keeps the office map within the engine's model limit (about 217 of 256 models); the census
  stage refuses an office map over 240 models, and the builder counts each converted room's models against the limit.
- **Sneaking.** Holding Left Ctrl sneaks: the player walks slower, the view sits lower, sneaking uses fatigue, and the
  HUD shows a sneak indicator. The key has its own row in the Options controls page, and saved key bindings are moved
  to the new command. In the debug free-fly mode Left Ctrl keeps its fast-flight use. Sneak animation and detection
  come in a later version.

### Creatures and sound

- **The cliff racer is drawn whole.** The creature bake keeps a thin part whole when its size reduction would have
  collapsed it, so the wings join the body and the stray spike is gone. Every creature model is checked for the same
  fault; the one still found is listed below.
- **Creature sounds.** Creatures make their own sounds as they move and fight (steps, moans, roars, screams), and the
  creature sound test no longer stops: the vanity camera never starts while the combat playground or an Arena fight
  runs.
- **Combat sounds on by default.** The swing, armour, miss and punch sounds play as OpenMW plays them, and the sounds
  of one blow no longer cut each other off. Your own footsteps are a separate setting, off by default
  (`dbg footsteps on` or Options > Audio).
- **Voices.** Two Orcs whose names carry accented letters greet and talk again; you say your race's pain and death
  lines in a fight; a spell's sound no longer cuts a character off mid-line. A sound name slot nothing uses is reused,
  so voice lines and effects stay audible in long sessions.

### Fixes

- **The game's scripts run.** The script file holds 8,618 scripts (most of them dialogue results), and the engine
  refused any file over 2,048, so no script ran in the development snapshots from dev2 to dev5. The engine now takes up
  to 16,384 scripts, and the builder refuses a script file over the engine's limits instead of shipping it
  (MWSCRIPT-REFUSED-SCRIPT-COUNT-58).
- **Taking items works.** E on an aimed item takes it, an owned item as stolen; taken and disabled objects are also kept
  hidden on every map when scripts are off (PICKUP-E-OWNED-NO-TAKE-58). The aim box is for items and doors; creatures
  and people no longer get it, since their name already shows under the view.
- **Character creation runs in order.** The birthsign page no longer jumps to the class confirm box, the review sheet
  asks for a name first and shows it, and the class questions button is greyed out when the game install has no
  question data (CHARGEN-BIRTHSIGN-REVIEW-58).
- **The debug restart lands in Seyda Neen.** `dbg aw hors` without a number means 0, so after the Halloween scene it
  moves the player to Seyda Neen instead of leaving them in the Arena Pit (HORS-AFTER-HALLOWEEN-STAYS-ARENA-58).
- **Text macros are filled.** Books, the journal, message boxes and dialogue fill the game's text macros (the player's
  name, race, class and the like) from one table, and book and journal texts store each macro as a one-byte code
  written when the game is built (BOOK-TEXT-MACROS-58).
- **The character restart debug command no longer crashes** when it is used after the Halloween scene in Seyda Neen: a
  new server, a reload of the same map included, resets the scene and the ambient sound slots first. It also works from
  the main menu, where it starts a new game straight into Seyda Neen as the census would leave you.
- **An NTSC machine starts.** Without a PAL screen mode the engine takes the default monitor's mode instead of stopping.
- **The presets show only the drawn picture.** The FS-UAE and WinUAE presets (the slow accelerator preset too) crop to
  the 320x200 picture, which fills a widescreen monitor at no cost to the game. The Raspberry Pi boot image does the
  same and no longer prints the first-login SSH banner that did not apply.
- **Seyda Neen.** The wedge-shaped gap in the shore wall is closed: flora cards push back in depth only on the card's
  bottom quarter, the trunk base.

### Builds and the Toolkit

- **Steadier, faster builds.** The actor library uses every core it is allowed, the boot check tells a game that stops
  answering apart from an emulator that stalls on its disk, and the performance check of a build judges a section run
  on other cores than its baseline by CPU seconds per unit, with each row naming its basis.
- **Build reports** give the voice coverage (people voiced, creatures with sounds, named ones unmapped).
- **Toolkit build monitor (Toolkit 0.1.19).** A build whose stages passed and whose only failed step is the
  performance check shows as "passed, perf guard failed". One overall progress bar shows the percentage and the
  expected finish, a machine view lists gates, tests and pregates with the cores they use, and the timeline has boxes
  for cores used and memory used.
- **Documents.** The building guide says what a build costs in time and in machine; the Raspberry Pi 4B reference
  figures, the PAL ceiling for European machines and what the published PiStorm numbers mean are written down; the
  mixer's limits are documented.

## Moved to v0.0.59

The conversation's remaining parts and the bigger items move, openly, to v0.0.59 as they stand, in the
[roadmap](../../ROADMAP.md):

- World models and object placement: every item with its own model when dropped or placed, every item the original
  places in its place from one shared model table, and a larger model table per map than the present 256 (the 512-entry
  model table).
- What the player wears and wields shown in first person and on the third-person body.
- The crime system (theft, pickpocketing, attacks, killing and trespass seen by witnesses, bounties and guards).
- Player casting and a spell-effect system; weapons and shields of every type in first and third person.
- Levelling as in the original, with the level-up box.
- The full trade window, links in the journal's dated quest entries, and companions following through doors.
- Characters and creatures placed by scripts through one shared spawn, and more of the game's scripts run as bytecode.
- Saves that keep the whole game, the save import, the original-style map, weather by region, moving gates and
  trapdoors, lighter large interiors and trees with depth by distance.
- Sneak animation and detection, the area sounds of the invisible sound markers, and Morrowind's own mouse cursor.
- Dialogue texts and the time of day filled from the written name at run time, and action-key macros that show the
  bound key's name.

## Known in this build

- The back-room table of the Census and Excise Office is not drawn, so the dagger on it is not seen
  (CENSUS-BACK-TABLE-NOT-DRAWN-58, open in the [register](../../BUGS.md)).
- The aim box measures the reach to an item's origin, not to its nearer surface as the original does
  (FOCUS-REACH-ITEM-ORIGIN-58, open in the [register](../../BUGS.md)).
- The netch bull's reduced model loses a stretch of one leg
  (CREATURE-NETCH-BULL-LEG-REDUCED-58, open in the [register](../../BUGS.md)).
- The player can hold only 8 spell changes, so a ninth bought spell is refused, and an actor keeps only 12 item changes,
  so a merchant refuses the thirteenth kind of item sold to it (PLAYER-SPELL-CAP-58 and MERCHANT-ITEM-CAP-58, open in
  the [register](../../BUGS.md)).
- Casting the spells you make, and using items you enchant, wait for player casting (v0.0.59).
- NPCs do not yet say their Intruder or Thief lines: no engine event says them until the crime system is in
  (NPC-VOICE-INTRUDER-THIEF-NO-EVENT-58, open in the [register](../../BUGS.md)).
- The prison ship's hold draws slower than the Arena Pit, and Seyda Neen is heavy on the Raspberry Pi 4B
  ([PRISON-SHIP-RENDER-COST-56](../../bugs/PRISON-SHIP-RENDER-COST-56.md)).
- A build's performance check can fail on loaded machines when other builds run beside it
  ([PERF-GUARD-RESIDENT-BUSY-HOST-57](../../bugs/PERF-GUARD-RESIDENT-BUSY-HOST-57.md); the fix is in, to be confirmed
  on the next loaded full build).
- A rare fault in sprite data was seen on arrival at Gnisis; the sprite is left out of the frame instead of ending the
  game, and its cause is still being looked for
  ([SPRITE-BAD-TYPE-THREADED-56](../../bugs/SPRITE-BAD-TYPE-THREADED-56.md)).
- A few places are slow right after arriving ([SWEEP-SLOW-ARRIVALS-57](../../bugs/SWEEP-SLOW-ARRIVALS-57.md)), and
  the Manor District of Ald'ruhn ([INTERIOR-FAR-BLANK-MANOR-56](../../bugs/INTERIOR-FAR-BLANK-MANOR-56.md)).
- On FS-UAE with a loaded machine, a load now and then waits forever on the emulated hard disk; restarting the emulator gets
  past it ([CHIM-SEYDA-BALMORA-LOAD-HANG-43](../../bugs/CHIM-SEYDA-BALMORA-LOAD-HANG-43.md)).
- Some rooms still load in after you arrive ([CHIM-ROOM-POPIN-51](../../bugs/CHIM-ROOM-POPIN-51.md)).
- Dialogue texts and the time of day still fill their macros from the written name at run time, and action-key macros
  show the action's word, not the bound key (both in the next version).

## Not yet checked in game

- The filled text macros in books and the journal.
- Taking a free (unowned) item with E.
- The aim box on doors.
- The Fargoth greeting at talk time.
- Your own footsteps (`dbg footsteps on`) and the creature sound test.
- Character creation: the class questions with the install's question data, a class of your own and the class list.
- Dialogue conditions, faction rank and the services in play.
