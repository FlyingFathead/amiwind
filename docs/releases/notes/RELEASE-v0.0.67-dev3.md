# AmiWind v0.0.67-dev3 (in development)

_Last updated with AmiWind v0.0.67-dev3 (19 November 2026)._

Development snapshot, 19 November 2026, in development. Running on CHIM Engine v0.2.2. Previous release:
[v0.0.66: Forward It Is](RELEASE-v0.0.66.md). Previous snapshot: [v0.0.67-dev2](RELEASE-v0.0.67-dev2.md).

The third snapshot of v0.0.67. Its headline is the first-person hands, the first use of Mournhold's districts and the
inventory. Every race and sex now draws its own first-person hands with no colour step at the wrist, and a race or
outfit change lets go of the parts it replaces; Mournhold's five districts are a build module of their own, with their
containers, items, activators, doors and people keyed outdoors; the inventory shows one action per kind of item, casts
scrolls, tells a worn item and describes any item; and the dialogue is checked by number against the original's rules
for every topic. Besides them it carries the shared layout of menus and message boxes with one focus under the
crosshair, creatures and spell effects that look and move as in the original, a look book that checks every confirmed
look and behaviour on each development build, and a builder that reuses earlier builds by default. Its emulator
presets, `AmiWind-v0.0.67-dev3-FS-UAE.fs-uae` and `AmiWind-v0.0.67-dev3-WinUAE.uae`, both start with 32 MB of Fast RAM,
which the game needs. The changes below are checked by the test suite and the gate of this snapshot; where a number
comes from a session in the emulator, it says so, and what has not been seen in play on a build of this snapshot says
so as well. Of this snapshot's changes only the first-person hands of every race were seen in play on a test build; the
rest is fixed in source and covered by the test suite and the gate.

## New since v0.0.67-dev2

### New

- **Every race and sex has its own first-person hands**, in its own skin, joined to its own wrist and forearm
  ([FP-HANDS-PER-RACE-67](../../bugs/FP-HANDS-PER-RACE-67.md)). Four of the game's first-person hand records name another
  race's or sex's mesh (the Nord man's, the Imperial woman's, the Dark Elf man's and the Redguard man's); they now draw
  the hand of their own race and sex, a deliberate departure from the original's data, decided for the project on
  18 November 2026. The colour step where the hand met the wrist and the wrist the forearm is gone: the skins are matched
  along each arm for every race and sex (the Nord man's step was 54.9 per colour channel; the match aims within one
  palette step, and the image step stops on a step over 16 per colour channel). In third person the High Elf man draws his
  own upper legs. In the emulator, on a test build of this line, the hands were seen in play in every race. How the parts are chosen and
  let go: [the player's body](../../PLAYER_BODY.md). A race, sex or outfit change lets go of the parts it replaces at
  once, so the first-person arms no longer fall back to an old hand model with holes
  ([FP-ARMS-NO-MODEL-SLOT-67](../../bugs/FP-ARMS-NO-MODEL-SLOT-67.md)).
- **`dbg race [N / NAME] [m / f]`** swaps the player's race and sex in place: the stats stay, what the new race cannot
  wear goes back into the inventory, and the model table is read back.
- **Mournhold's five districts are a build module of their own** (`tribunal-mournhold`): their own CHIM world, with the
  usual sky, weather and sun, keyed by their own inputs and read by no stage of Vvardenfell. Their containers, items,
  activators and doors are keyed outdoors at their moved places, and their people stand in their frame maps
  (MOURNHOLD-EXTERIOR-CELLS-66). `dbg tp mournhold`, `solstheim`, `ravenrock` and `skaal` take the player to the
  expansions' fixed places and say so when the expansion is not in the build. A teleport that asks for a height far below
  the floor not yet loaded holds the player until the floor is there; this is fixed in source, so the Great Bazaar
  should no longer land under the water (MOURNHOLD-BAZAAR-UNDER-WATER-67; still to be seen in play). Observations on how the districts work are in the
  [Mournhold notes](../../MOURNHOLD_NOTES.md).
- **The expansions' scripts and people are bound.** The scripts of 1,150 of Tribunal's and 1,178 of Bloodmoon's placed
  objects run, and the scripted items carried by their people and creatures (77 of Tribunal, 42 of Bloodmoon) get their
  scripts. A new actor check counts the expansions' actors and stages per land, and the actor record audit reads a
  creature's animation table as the engine plays it (about 160 records lack a kind instead of up to 561).
- **The inventory.** One action per kind of item (Equip, Unequip, Use, Steal in red for an owned container's contents),
  with the Equipped tag in a highlight colour; scrolls are cast once from the inventory; an item information key opens a
  box with the item's properties; `dbg give spell` lists the spells and adds one or all
  ([INVENTORY.md](../../INVENTORY.md)).
- **A pick-up says what happened** ("Picked up Bottle." or "Picked up 3 Bottle."), with the original's silence as a
  setting.
- **`dbg spawn`** opens a list box like `dbg tp`'s, with find and friendly names, over every creature and person of the
  build; `dbg despawn` takes the spawned one away.
- **Debug tools for held items.** `dbg setpov 1|2|3|off` locks the view for test pictures; `dbg lighttest` enters a dark
  corridor with nothing in it for checking every held light; `dbg cycleitems` goes through every item the hands can hold,
  in first and third person ([item cycling](../../ITEM_CYCLING.md)); the image step writes the index of those items,
  632 on the current data.
- **The confirmed look book.** Every look and behaviour the maintainer confirmed in play is a page with its saved
  pictures and numbers, checked on every development build before it is delivered, and the code a page guards is marked
  so that a change to it fails the gate until the page has passed ([the look book](../../LOOKBOOK.md)).
- **A model census and a mesh converter.** `tools/model_census.py` lists every model the game files place, its original
  triangles and what each reduction method makes of it, with its quality; every build writes it
  ([model census](../../MODEL_CENSUS.md)). `tools/mesh_convert.py` converts a game model to OBJ+MTL and back, in
  Morrowind units, Quake units or any scale, from your own game files ([mesh converter](../../MESH_CONVERT.md)). A
  replacement made for one model is used wherever the model is placed, outdoors and in every room, and a hand-made
  low-polygon model can stand in for a game model (the travel lantern is the first).

### Fixed

- **Spell effects show the original's egg-shaped shell** from the feet to above the head, sized to each character, and in
  first person as a tint instead of a grid of squares (MAGIC-SHELL-EGG-STYLE-67); the player takes a short red hue when
  hurt, as the original's hit overlay does (DAMAGE-RED-HUE-67).
- **Creatures move and fight by the original's rules.** A nix-hound moves with its own animations instead of a person's
  and its bite is no longer called a chop; a defender the player misses side-steps only where the original lets it;
  every creature's own animation table holds its walk in place. The cliff racer is whole again (wings joined to the
  body, no holes), and a surface check compares every creature model with its source.
- **Dialogue.** The rank rule no longer gives people without a faction empty rank words (the Background answer);
  six dialogue conditions are read as the original reads them; Goodbye and the topics are greyed while an answer waits
  for Continue; the console font's letters show in game. The answer chosen for every topic is checked against an
  independent reading of the original's filter rules, with no difference on Morrowind.esm
  ([dialogue features](../../DIALOGUE_FEATURES.md)).
- **The opening.** The dock guard walks the middle of the pier to his post and faces the player, also after a load; the
  birthsign window explains every sign's ability, and every birthsign spell has its row, so the character gets its sign's
  spells.
- **The prison ship's hold** draws its masts and the iron bands of its tables as the original does, so the player no
  longer walks into an invisible post and the table has no dark triangle.
- **The map.** The World tab opens on the player with the explored land in view, and the map shows only places the player
  has been to.
- **One focus under the crosshair.** The title, the action line and the use key follow the nearest thing along the view
  ray, so a door behind a person is no longer aimed at and the person's name and the door's are never drawn on one spot;
  an item beside a person is no longer taken from him by the box of his one stored frame.
- **Menus and boxes share one layout.** A helper places a box's title, content and centred buttons by one table, buttons
  use the regular frame and stand clear of the bottom edge, the class window's rows use the console font, and a check
  fails a text or button out of its box or two texts on one another.
- **No error in play ends the game.** An engine error, a server message the screen side cannot read or an allocation
  that fails in play loads the place again, else the newest autosave, else the previous map, and the box says which.
- **Third person.** The player's walk and run no longer stay stuck after the idle camera, and switching between first and
  third person keeps them playing (fixed in source).
- **Containers and the held light.** The container aim check, the container window and the view had three engine fixes
  from the in-game containers check; in first person a held torch is drawn in the left hand again (fixed in source,
  [FP-TORCH-OUT-OF-HAND-67](../../bugs/FP-TORCH-OUT-OF-HAND-67.md)).
- **A screen recording of an emulator session that stalls** stays playable up to the cut, and the session check no
  longer calls a running game stalled when its state file is read half written.

### Performance

- **The frame message's cost is measured.** [The page](../../performance/NET_FRAME.md) holds the two methods, sending
  everything and pacing it nearest first, and the rule that picks the default.

### Builder and tools

- **A plain build reuses earlier builds by default.** In a workspace that holds earlier builds, a build with no reuse
  option takes every stage they hold unchanged, says in its first minute what it reuses and what it makes again and why,
  and asks once in a terminal whether to reuse; a build from scratch only when asked.
- **The builder's checks come earlier.** The stage plan is checked for recordable arguments in its first second, the
  presented districts and every CHIM frame map's sky in the first minute, and the stage that runs alone no longer holds
  a stage down to its last units.
- **The bug register** has its report page for every entry, made by the register tool from the entry itself; the tool
  and the pregate refuse an entry without one.

## What the v0.0.67 line works on

- **Tribunal and Bloodmoon in the game.** The order is the one of [v0.0.67-dev1](RELEASE-v0.0.67-dev1.md#what-the-v0067-line-works-on):
  the expansions' files checked; the changes they make to Vvardenfell; Solstheim built like the island; Mournhold's
  five districts as one exterior; scripts and dialogue; the save with their counts; the Toolkit's views; playtests.
  This snapshot adds Mournhold's districts as a build module with their things and people, and the expansions' scripts
  bound. The [roadmap](../../ROADMAP.md) holds the order.

## Needs 32 MB Fast RAM

The game needs 32 MB of Fast RAM. At 16 MB parts run and over-limit interiors show the warning box.

## In-game checklist for this snapshot

- Start as each race, in both sexes, and look at the hands in first person, with a held light; `dbg race` swaps race in
  play.
- Open the inventory: the key line follows the selected item; cast a scroll; try the item information key.
- Aim at a person with a door behind him: only the person is named. Open the map's World tab.
- `dbg tp mournhold`, then walk the district: its doors, containers and people.
- Spells and hurt: the egg-shaped shell around the character, the short red hue.
- The checklist of [v0.0.67-dev2](RELEASE-v0.0.67-dev2.md#in-game-checklist-for-this-snapshot) stands for the rest.

## Known in this build

The [MWScript tracker](../../MWSCRIPT_FEATURES.md) shows how many of the game's scripts run; the
[CHIM progress tracker](../../chim/PROGRESS_TRACKER.md) shows how far each land and part has come.

- **Mournhold and Solstheim are not playable yet.** Mournhold's districts are in the image as a module, but the way
  there, their quests and most of their scripts are not. Corrected for v0.0.67: the way to Mournhold works (see [the
  v0.0.67 notes](RELEASE-v0.0.67.md#known-in-this-build)); its quests and much of its play are not ready. Two of Solstheim's models, the icebergs of the Mortrag Glacier,
  cannot be converted yet (COLLISION-ICEBERG-CLIPNODE-BUDGET-67).
- **Fixed in source, still to be seen in play on a build of this snapshot:** the districts' containers, items,
  activators, doors and people, the arrival hold at the Great Bazaar, the person's use box, the shared layout of menus
  and boxes, the prison ship's masts and table, the dock guard's post, the dialogue changes, the map's World tab, the
  birthsign window, the egg shell's look in first person, the held torch, the third-person walk after the idle camera,
  the container fixes and the error chain. Of this snapshot's changes the first-person hands of every race are the ones
  seen in play on a test build. Their register entries stay open until then.
- **Mournhold's districts, open in the register:** the two frames of Plaza Brindisi Dorom are over the 16 MB zone
  budget ([CHIM-MOURNHOLD-PLAZA-OVER-16MB-67](../../bugs/CHIM-MOURNHOLD-PLAZA-OVER-16MB-67.md)); the Plaza is not drawn
  looking south from its arrival point
  ([DISTRICT-PLAZA-NOT-DRAWN-FROM-ARRIVAL-67](../../bugs/DISTRICT-PLAZA-NOT-DRAWN-FROM-ARRIVAL-67.md)); Godsreach's gate
  to the Plaza stands on a cell border and cannot be used
  ([DISTRICT-GATE-ON-CELL-BORDER-67](../../bugs/DISTRICT-GATE-ON-CELL-BORDER-67.md)); the Hall of Ministry holds seven
  Infected Rats at the start of a new game
  ([ROOM-HALL-OF-MINISTRY-RATS-NOT-DISABLED-67](../../bugs/ROOM-HALL-OF-MINISTRY-RATS-NOT-DISABLED-67.md)); two of the
  three atronachs of Norenen-dur are dead seconds after they attack
  ([ROOM-NORENEN-DUR-ATRONACHS-DIE-67](../../bugs/ROOM-NORENEN-DUR-ATRONACHS-DIE-67.md)).
- **An actor placed by `dbg spawn` is booked in cell 0,0** instead of the player's cell, so nothing is drawn
  ([DBG-SPAWN-CELL-ZERO-67](../../bugs/DBG-SPAWN-CELL-ZERO-67.md), open).
- **A locked container never opens**: no key, lockpick or Open spell works on it
  ([LOCKED-CONTAINERS-NEVER-OPEN-67](../../bugs/LOCKED-CONTAINERS-NEVER-OPEN-67.md)).
- **The conversion makes models heavier than the original game** (CONVERT-HEAVIER-THAN-ORIGINAL-67); the census lists
  them.
- **A resident standing in front of a door**
  ([WANDER-DOOR-RULE-66](../../bugs/WANDER-DOOR-RULE-66.md)): fixed in source, and the opening journey's step 9 passed on
  a test build of this line; the entry stays open until a snapshot's journey passes.
- **Bloodmoon's werewolves have no model yet** (`PLAYER-WEREWOLF-ROBE-NOT-BAKED-66`, `NPC-WEREWOLF-NO-MODEL-66`).
- **A hostile scrib walks off instead of attacking**: measured to be the original's rule for the scrib; the scamp's case
  is still to be settled ([CREATURE-HOSTILE-FLEES-67](../../bugs/CREATURE-HOSTILE-FLEES-67.md), open).
- **The Heart Chamber's collapse is not animated, so the end of the main quest cannot play yet**
  (`ENDGAME-CHAMBER-COLLAPSE-63`).
- **A load can stop in the emulator**
  ([CHIM-SEYDA-BALMORA-LOAD-HANG-43](../../bugs/CHIM-SEYDA-BALMORA-LOAD-HANG-43.md)): it happens in test sessions that use the remote console; players do not use it.
- **In the builder:** the image step and the room batch stages use too few cores
  ([BUILD-IMAGE-UNDERUSED-32](../../bugs/BUILD-IMAGE-UNDERUSED-32.md)), and the resident bake of Vivec costs about three
  and a half times what it did (RESIDENT-BAKE-VIVEC-COST-59).
- From [v0.0.67-dev2](RELEASE-v0.0.67-dev2.md) and [v0.0.66](RELEASE-v0.0.66.md): their Known lists stand for what is
  not named here. Every other open entry is in the [bug register](../../BUGS.md).
