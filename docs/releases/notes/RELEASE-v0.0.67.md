# AmiWind v0.0.67: Tribunal Introduced

_Last updated with AmiWind v0.0.67 (19 November 2026)._

Release, 19 November 2026. Running on CHIM Engine v0.2.2. Previous release:
[v0.0.66: Forward It Is](RELEASE-v0.0.66.md). Made from the third development snapshot, v0.0.67-dev3, from the builds and
caches of that snapshot; it carries all three snapshots: [dev1](RELEASE-v0.0.67-dev1.md),
[dev2](RELEASE-v0.0.67-dev2.md) and [dev3](RELEASE-v0.0.67-dev3.md). Each snapshot's notes hold the full detail of its
changes and measurements. Its emulator presets, `AmiWind-v0.0.67-FS-UAE.fs-uae` and `AmiWind-v0.0.67-WinUAE.uae`, both
start with 32 MB of Fast RAM.

## What v0.0.67 is

v0.0.67 introduces Tribunal, the first expansion, into the game, and mends the faults found in play on v0.0.66.
Tribunal's additions to Vvardenfell are in the build (Apelles Matius and Asciene Rane in Ebonheart). The way to Mournhold
works: on 17 November 2026, in the emulator on the Raspberry Pi 4B with the v0.0.66 image, Mournhold, Royal Palace:
Reception Area was reached from Ebonheart and Effe-Tei's answer there took the player back, with the two answers run
through the debug console. On 19 November 2026, on the v0.0.67-dev3 image in the emulator at 32 MB of Fast RAM, the trip
was made in the dialogue window used by hand: Asciene Rane's topic and choice in Ebonheart, Grand Council Chambers took
the player to Mournhold, Royal Palace: Reception Area at exactly her script's position; from there the player went out
through the palace door into the Royal Palace courtyard and through the gate into Plaza Brindisi Dorom; Effe-Tei's topic
and choice took the player back to Ebonheart, Grand Council Chambers at exactly his script's position, with Asciene Rane
still there. The Tribunal start state was set with the original's own journal command; the Dark Brotherhood's attack in
sleep that starts Tribunal was not played on the dev3 image, and was seen on the release image (see "Seen in play"). The five districts were each visited by teleport, with their arrival and open
area. Mournhold's five outdoor districts are a build module of their own in this release. Mournhold can be reached and
walked from the palace to the Plaza; its quests and much of its play are not ready yet, and Solstheim is not in the game
(see "Known in this build").

The release also brings the three critical faults of v0.0.66 back under control (the stop on a loading screen in busy
places, the missing autosaves, the missing wild creatures), the first-person hands of every race, the inventory's
actions, the confirmed look book that checks every confirmed look on each development build, and a builder that fails
fast, says why, and reuses earlier builds by default. The game needs 32 MB of Fast RAM.

Most changes below were checked by the test suite and the gates of the snapshots; what was seen in play is under "Seen in
play". Several fixes are made in source and covered by tests and are still to be seen in play: they say so, and the
[bug tracker](../../BUGS.md) keeps their entries open until then.

## New

### Tribunal and Bloodmoon in the game

- **Mournhold's five districts are a build module of their own** (`tribunal-mournhold`): their own CHIM world with the
  usual sky, weather and sun, keyed by their own inputs and read by no stage of Vvardenfell. Their containers, items,
  activators and doors are keyed outdoors at their moved places and their people stand in their frame maps, placed in
  source and still to be seen in play
  ([DISTRICT-PEOPLE-NOT-PLACED-67](../../bugs/DISTRICT-PEOPLE-NOT-PLACED-67.md),
  [DISTRICT-PLACED-THINGS-NO-ROW-67](../../bugs/DISTRICT-PLACED-THINGS-NO-ROW-67.md),
  [DOORS-DISTRICT-FRAMES-NOT-HOLDERS-67](../../bugs/DOORS-DISTRICT-FRAMES-NOT-HOLDERS-67.md); dev3).
  `dbg tp mournhold`, `solstheim`, `ravenrock` and `skaal` take the player to the expansions' fixed places and say so
  when the expansion is not in the build. The debug teleport to the Great Bazaar set the player about 470 units under its
  street, under the water surface the game's data gives the districts; a landing that searches for the floor at the asked point at
  once, instead of the first spot a blocked box gives, is made in source and was seen in play on the release image
  ([MOURNHOLD-BAZAAR-UNDER-WATER-67](../../bugs/MOURNHOLD-BAZAAR-UNDER-WATER-67.md), open). The two district doors into
  the Great Bazaar set the player on the street (see "Seen in play"). Observations on the
  districts: [Mournhold notes](../../MOURNHOLD_NOTES.md).
- **The expansions' scripts and people are bound.** The scripts of 1,150 of Tribunal's and 1,178 of Bloodmoon's placed
  objects run, and the scripted items carried by their people and creatures (77 of Tribunal, 42 of Bloodmoon) get their
  scripts. A new actor check counts the expansions' actors and stages per land, and the actor record audit reads a
  creature's animation table as the engine plays it (dev3).
- **Solstheim's and Mournhold's models have their collision rows**: the surface table has the rows of Solstheim's
  exterior models, of Mournhold's districts and of the Royal Palace courtyard's banner hanger; a layer's rows are
  append-only, so a new row re-keys nothing (dev2).
- **A place that cannot be loaded names its error.** A door, travel, a spell, a script or a debug teleport to a place the
  build does not hold leaves the player where he was and shows the game's box with the error and one button, **OK**
  ([when a place cannot be loaded](../../LOAD_ERRORS.md); dev2).
- **The Toolkit opens every room tile and every cell of the CHIM open world in the 3D Inspector**, reading every world
  format from 0.5 to 0.12, with a heatmap of the expansions' rooms (dev2; fixed in source, not yet checked in a build;
  [TOOLKIT-LOCAL-CHIM-CELL-NO-MAP-67](../../bugs/TOOLKIT-LOCAL-CHIM-CELL-NO-MAP-67.md)).

### The player

- **Every race and sex has its own first-person hands**, in its own skin, joined to its own wrist and forearm
  ([FP-HANDS-PER-RACE-67](../../bugs/FP-HANDS-PER-RACE-67.md),
  [FP-BARE-HAND-OTHER-SKIN-67](../../bugs/FP-BARE-HAND-OTHER-SKIN-67.md)). Four of the game's hand records name another race's or
  sex's mesh; they now draw their own, a deliberate departure from the original's data, decided for the project on
  18 November 2026. The colour step at the wrist and forearm is gone (the Nord man's was 54.9 per colour channel; the
  image step stops on a step over 16). In third person the High Elf man draws his own upper legs. A race, sex or outfit
  change lets go of the parts it replaces at once, so the first-person arms no longer fall back to an old hand model with
  holes ([FP-ARMS-NO-MODEL-SLOT-67](../../bugs/FP-ARMS-NO-MODEL-SLOT-67.md); [the player's body](../../PLAYER_BODY.md)).
  `dbg race [N / NAME] [m / f]` swaps race and sex in place (dev3).
- **The inventory shows one action per kind of item** (Equip, Unequip, Use, Steal in red for an owned container's
  contents) with the Equipped tag in a highlight colour; scrolls are cast once from the inventory; an item information
  key opens a box with the item's properties; `dbg give spell` lists and adds spells ([INVENTORY.md](../../INVENTORY.md);
  dev3). Arrows and bolts, lockpicks and probes cannot be equipped yet
  ([INVENTORY-EQUIP-KINDS-NOT-YET-67](../../bugs/INVENTORY-EQUIP-KINDS-NOT-YET-67.md)). A pick-up says what happened
  ("Picked up Bottle."), with the original's silence as a setting.
- **Nothing is taken, opened or harvested before the census papers allow the inventory**, as in the original, and a
  placed object shows no name or action line before then (dev2; fixed in source, still to be seen in play;
  [PRISON-SHIP-ITEMS-TAKEABLE-65](../../bugs/PRISON-SHIP-ITEMS-TAKEABLE-65.md)).
- **Seyda Neen's crates, barrels, chests and sacks are drawn and open**: its frame places the 19 containers that open in
  its cells, the 14 that were not drawn among them (dev2; fixed in source, still to be seen in play;
  [SEYDA-CONTAINERS-NOT-DRAWN-67](../../bugs/SEYDA-CONTAINERS-NOT-DRAWN-67.md)).

### Debug and test tools

- `dbg netstat` shows the last frame's update against the room in the frame message ([the frame
  message](../../NET_MESSAGES.md); dev2). `dbg spawn` opens a list box over every creature and person of the build and
  `dbg despawn` takes the spawned one away; `dbg setpov 1|2|3|off`, `dbg lighttest` and `dbg cycleitems` check held items
  in first and third person ([item cycling](../../ITEM_CYCLING.md)); the image step writes the index of those items, 632
  on the current data (dev3).
- **The confirmed look book.** Every look and behaviour the maintainer confirmed in play is a page with its numbers (its
  saved pictures follow once each page has a reference picture), checked on every development build before it is
  delivered; six pages exist, three of them run in the emulator on each build and two are drafts. The code a page guards
  is marked so that a change to it fails the gate until the page has passed ([the look book](../../LOOKBOOK.md); dev3).
- **A model census and a mesh converter.** `tools/model_census.py` lists every model the game files place with its
  original triangles and what each reduction method makes of it ([model census](../../MODEL_CENSUS.md));
  `tools/mesh_convert.py` converts a game model to OBJ+MTL and back in Morrowind units, Quake units or any scale, from
  your own game files ([mesh converter](../../MESH_CONVERT.md)). A replacement made for one model is used wherever it is
  placed (dev3).
- A page on [Morrowind units and AmiWind units](../../UNITS.md) (dev2).
- `dbg dbattack`: where the rest window offers Rest, an 8-hour rest on which Tribunal's own Dark Brotherhood script
  attacks for certain (its roll made sure for that one rest, the script's own path otherwise); each step, and any that
  fails, is reported on the console.

## Fixed

- **Arriving in a flooded room puts the player in its water** instead of on top of the room: the first flooded hall
  of the Clockwork City, entered by its teleport, its door or the debug teleport, had the player standing on the
  hall's roof. A room arrival whose feet are in water is now taken where it is, wading or swimming, as the original
  does; dry arrivals are unchanged. Of the image's 6,217 room arrivals, 140 move from the top of a room into its water
  (fixed in source; its entry is under "Known in this build" until a played game shows it).
- **The game no longer stops on a loading screen in busy places** (the Bitter Coast, Vivec). Each frame's update is built whole and copied in only where it fits, the
  player, the actors and the nearest things first; a message that cannot fit is dropped whole and the screen side drops
  an update it cannot read instead of ending the game. In the emulator no "packet overflow" line was printed at Vivec,
  against 4,668 with the previous engine (dev2; [the frame message](../../NET_MESSAGES.md)).
- **Autosaves are written again** on every map change, and a script error no longer holds every later save (dev2). In the emulator a teleport wrote "Saved Autosave 1" and the next "Saved Autosave 2".
- **Wild creatures are back outdoors** (dev2): the cell the player arrives in gets its levelled creatures and a new map drops the old map's
  queue. In the emulator the Bitter Coast had 7 creatures alive 30 seconds after arriving against 1 before, Red Mountain
  12, Pelagiad 21 and the Moonmoth Legion Fort 13.
- **Spell effects show the original's egg-shaped shell** sized to each character, and in first person as a tint; the
  player takes a short red hue when hurt (dev3).
- **Creatures move and fight by the original's rules**: a nix-hound moves with its own animations, a defender the player
  misses side-steps only where the original lets it, the cliff racer is whole again (dev3).
- **Dialogue**: no empty rank words for people without a faction, six conditions read as the original reads them, Goodbye
  and the topics greyed while an answer waits for Continue; every topic's answer is checked against an independent
  reading of the original's filter rules, with no difference on Morrowind.esm ([dialogue
  features](../../DIALOGUE_FEATURES.md); dev3).
- **The opening**: the dock guard walks the middle of the pier to his post and faces the player, also after a load; the
  birthsign window explains every sign's ability and the character gets its sign's spells (dev3).
- **The prison ship's hold** draws its masts and the iron bands of its tables as the original does (dev3).
- **The map**: the World tab opens on the player with the explored land in view and shows only places the player has been
  to (dev3).
- **One focus under the crosshair**: the title, the action line and the use key follow the nearest thing along the view
  ray (dev3). **Menus and boxes share one layout** with a check that fails a text or button out of its box (dev3).
- **An error in play sends the player back instead of ending the game**: a place that fails to load is loaded again, else
  the newest autosave, else the previous map; memory that runs out and a damaged map file still end the game
  ([LOAD-FATAL-ERRORS-67](../../bugs/LOAD-FATAL-ERRORS-67.md), still open) (dev3).
- **Scripts see the player asleep while a rest passes**, among them the Dark Brotherhood's attack in sleep that starts
  Tribunal: the engine handed the sleep check to the scripts as a fraction, so their comparison never held, and all the
  hours of a rest passed at once; the hours now pass over the following frames with the check a whole number, and a
  script that wakes the player stops them ([resting](../../RESTING.md); seen in play on the release image: a 12-hour rest
  in the wilderness at level 40 brought the attack, with its wake message on screen, and `dbg dbattack` brought it on an
  8-hour rest; see "Seen in play").
- **A wilderness rest that is cut short brings its creature**: one creature of the region's sleep list, picked at the
  player's level, appears in front of the player as in the original, and the interrupted line also goes to the log
  ([resting](../../RESTING.md); seen in play on the release image: the creature came from the region's list at the right
  hour).
- **A wilderness rest is cut short as often as the original's rule gives, not more**: in one session the creature came far
  too often, because every start of the game replayed the same random numbers. The game now seeds its rolls once at
  start from the clock, and the game's rolls draw from one generator of their own (fix 4d1ca449; fixed in source for
  the respin of this release, still to be seen in play; the rest entry is under "Known in this build").
- **What a script keeps out of the world stays out when the place loads again**: a teleport inside the place the player
  was in drew the people and creatures the game's scripts had disabled (the Plaza's four fabricants; in Seyda Neen two of
  the main quest's later Dreamers and one more person). Every load of a map now hides them again, as a change of place,
  a loaded save and a new game already did (fix fe36d037; fixed in source for the respin, still to be seen in play; its
  entry is under "Known in this build").

- **Scripts place levelled creature lists and scripted objects no map places**: Tribunal's centurions after the
  Bamz-Amschend fight, the Old Mournhold mine's projectile, Solstheim's transformation effects; a reference a script
  made and deleted leaves for good ([MWScript bytecode](../../MWSCRIPT_BYTECODE.md);
  [MWSCRIPT-PLACE-OTHER-KINDS-62](../../bugs/MWSCRIPT-PLACE-OTHER-KINDS-62.md), the entry still open; fixed in source,
  still to be seen in play).
- **Third person**: the walk and run no longer stay stuck after the idle camera (dev3, fixed in source).
- **The held light in first person is in the left hand again** (FP-TORCH-OUT-OF-HAND-67, a regression since v0.0.61): the
  light's grip lands on the left hand's bone. Seen in play on the v0.0.67-dev3 image and confirmed by the maintainer; see
  "Seen in play".
- A screen recording of an emulator session that stalls stays playable up to the cut (dev3).
- **Mournhold greets a new character in peace**: the fabricants of Plaza Brindisi Dorom, which their own scripts keep out
  of the world until the attack on the city begins, no longer attack while disabled, and a fight no longer follows the
  player into the next place, where it had made both Gaenors of the Temple Courtyard and two merchants of the Great
  Bazaar attack on arrival ([combat](../../COMBAT.md); seen in play on the release image, in Vvardenfell and in
  Mournhold). The hidden Infected
  Rats of the Hall of Ministry, which their script keeps out of the world until a later quest stage, start no fight
  either; the rats are hidden, not alive ([ROOM-HALL-OF-MINISTRY-RATS-NOT-DISABLED-67](../../bugs/ROOM-HALL-OF-MINISTRY-RATS-NOT-DISABLED-67.md);
  seen in play on the release image, the entry still open).
- **Godsreach's gate to the Plaza can be used from both sides of the cell border it stands on**: a district door within
  use reach of an inner border of its block is also written into the table of the cell beside it (seen in play on the
  release image;
  [DISTRICT-GATE-ON-CELL-BORDER-67](../../bugs/DISTRICT-GATE-ON-CELL-BORDER-67.md), the entry still open).

## Performance

- **A busy frame no longer costs a stop**: the frame message is built whole and paced across frames, nearest first
  ([the page](../../performance/NET_FRAME.md) holds the two methods and the rule that picks the default; dev2, dev3).
- **A cell that cannot pass the collision check fails in seconds**: the gate runs on the plain meshes before any stair
  collision unit is made, so a model it refuses no longer holds a core for tens of minutes first (dev2).
- The frame rate on the Raspberry Pi 4B is still to be measured on a v0.0.67 build.

## Builder and tools

- **A plain build reuses earlier builds by default** in a workspace that holds them, says in its first minute what it
  reuses and what it makes again and why, and asks once in a terminal whether to reuse (dev3).
- **One failure page**: a failed build's `FAILURE.md` holds the failed stage, its error and traceback, what was not
  completed, the settings the build ran with and the command that builds again; the report names the machine and classes
  an out-of-memory or out-of-disk failure (dev1).
- **One list of early checks of seconds** (`EARLY_CHECKS`), run before the first stage on the inputs and on the stored
  outputs the build reuses; new ones: the outdoor creature models, the presented districts, every CHIM frame map's sky,
  the stage plan's arguments (dev1 to dev3).
- **Live numbers from the first second**, also in the Toolkit Monitor's runs list (dev1); the strict reuse stop counts
  what one build looks up (REUSE-STOP-OLD-GROUPS-67; dev1); a CHIMport cell's key no longer takes in the request id
  (CHIMPORT-CELL-KEY-REQUEST-ID-67; dev1); the performance database goes on past a changed file (dev1).
- **Test sessions** never time a warped emulator ([EMULATOR-WARP.md](../../performance/EMULATOR-WARP.md); dev1); the gate
  and delivery smoke fail on engine error lines, a map change without an autosave, no creatures at Seyda Neen or a wild
  stop (dev2).
- **The bug tracker** has its report page for every entry, made by the register tool; the tool and the pregate refuse an
  entry without one (dev3).

## Seen in play

- **On the v0.0.67-dev3 image, from whose builds and caches this release is made** (the release differs from it in its
  version label and its two emulator presets), at 32 MB of Fast RAM in the emulator: the boot smoke passed (boot, Seyda
  Neen and Balmora loaded, music plays and can be switched off and on, an autosave on every map change, creatures alive
  outdoors, no wild stop at Seyda Neen), and the six town hops (Seyda Neen, Balmora, Vivec, the Vivec arena pit,
  Ald'ruhn and Khuul) all loaded. The release's own delivery repeats the boot smoke, the six hops and the look book on
  the release image before the kit; a page that misses stops the release.
- **The look book passed 3 of 3 pages on the dev3 image** (the journey page of the dock guard's post is not among them,
  and two pages are drafts): the held light (the debug torch, the glass lantern and a candle)
  within 1.8 units of the left hand in first person and 1.9 in third, the worn robe, and the teleport arrivals. The
  maintainer confirmed the held lights in the left hand in first and third person.
- The first-person hands of every race were seen in play on a test build of this line; the frame message, the
  autosaves and the wild's creatures were measured in the emulator on the dev2 engine (see "Fixed").
- **The trip to Mournhold and back in the dialogue window used by hand**, on the dev3 image on 19 November 2026 (see "What
  v0.0.67 is"): Asciene Rane's topic and choice in Ebonheart, Grand Council Chambers, the arrival in Mournhold, Royal
  Palace: Reception Area, the way out through the palace door into the courtyard and through the gate into Plaza
  Brindisi Dorom, and Effe-Tei's topic and choice back to Ebonheart. The five districts were visited by teleport. Earlier,
  on 17 November 2026 on the Raspberry Pi 4B with the v0.0.66 image, the two answers had been run through the debug
  console.
- **The Great Bazaar's two district doors, the levelling and the rests**, on the v0.0.67-dev3 image on 19 November 2026,
  at 32 MB of Fast RAM in the emulator, walking: the Plaza's door and the Temple Courtyard's door into the Great Bazaar
  were both usable and both set the player down on the street (height 363.4 in the original's units, the street at 297
  with the 67 every standing reads above its floor). Levelling: raising Axe by 10 shows the game's rest line and a full
  level progress (10 of 10); a 12-hour rest that ran its full length opened the level-up box with three coins; with
  Strength x5, Speed and Endurance chosen the character went from level 40 to level 41, Strength 60 to 65, Speed 50 to 51,
  Endurance 50 to 51 and health 250 to 255 (a tenth of Endurance 51); the same numbers stayed after a map change and back,
  after a quicksave and after loading it (the save list shows level 41). Rests: in the checks of the day 2 of 14
  twelve-hour rests on the Bitter Coast were cut after 9 hours, as the rule gives (a cut rest brings no level-up);
  no creature was placed when a rest was cut, and four 1-hour rests and six 12-hour rests at level 40 brought no attack
  of the Dark Brotherhood (that was the dev3 image; the release image is below).
- **On the release image** (the run 2b086671), in the emulator: the Dark Brotherhood's attack on a rest came by the
  debug command and, naturally, on a 12-hour rest in the wilderness at level 40, with its wake message on screen; the
  wilderness creature that cuts a rest came from the region's list at the right hour (it came too often in one session,
  see "Fixed"). Mournhold's start state on a new game was peaceful in the Plaza, the Temple Courtyard and the Hall of
  Ministry; the Great Bazaar's teleport arrival put the player on the street; Godsreach's gate to the Plaza opened; and
  a fight was not carried to the next map, in Vvardenfell and in Mournhold. Levels 10 and 20 for the Dark Brotherhood are
  still being tested and are not claimed here.

## Scripts and progress

Of the 1,074 scripts the original game uses, 925 run and 9 more are carried by AmiWind's own code; 2 use a function the
interpreter lacks (the two water levers of Old Mournhold: a room's water is fixed in its converted map,
[MWSCRIPT-WATER-LEVEL-STATIC-67](../../bugs/MWSCRIPT-WATER-LEVEL-STATIC-67.md)) and 138 belong to places the image does
not hold yet, Solstheim's outdoor regions nearly all of them. Tribunal.esm: 233 of its 236 used scripts run. The
tracker now counts the expansions' rooms and Mournhold's districts the image holds, and the interpreter carries out
PlaceItem and the player's sleep ([MWScript tracker](../../MWSCRIPT_FEATURES.md), measured for this version on 19
November 2026 on the v0.0.67-dev3 build; 611 run, 21 lacking a function and 433 counted as add-on only before). The
[CHIM progress tracker](../../chim/PROGRESS_TRACKER.md) holds the state of every land and part for this version:
Vvardenfell's 1,408 exterior cells (1,292 land and 116 sea) and 1,121 of its 1,123 rooms are on CHIM; Mournhold's 11
exterior cells, built as a world of their own, are counted beside them, 87 of Mournhold's 93 rooms and all 96 of
Solstheim's are in the image, and none of Solstheim's land cells is on CHIM
([TRACKERS-COUNT-MOURNHOLD-OUT-67](../../bugs/TRACKERS-COUNT-MOURNHOLD-OUT-67.md), fixed in source, to be confirmed on a
build of the release).

## Needs 32 MB Fast RAM

The game needs 32 MB of Fast RAM. At 16 MB parts run and over-limit interiors show the warning box.

## What to check in play

- Start as each race, in both sexes, and look at the hands in first person, with a held light; `dbg race` swaps race.
- Walk the Bitter Coast and Vivec for a few minutes: the game keeps running and creatures are around you.
- Change maps and look in Load game for the autosaves; open the crates and barrels of Seyda Neen.
- Open the inventory and cast a scroll; aim at a person with a door behind him: only the person is named.
- Talk to Asciene Rane in Ebonheart, Grand Council Chambers and take her offer to Mournhold; `dbg tp mournhold` and walk a
  district: its doors, containers and people.
- Rest 12 hours in the wilderness a few times: now and then the rest is cut by a creature of the region, and with Tribunal's
  start state the Dark Brotherhood's attack can come; `dbg dbattack` brings it at once.

## Known in this build

The [MWScript tracker](../../MWSCRIPT_FEATURES.md) shows how many of the game's scripts run; the
[CHIM progress tracker](../../chim/PROGRESS_TRACKER.md) shows how far each land and part has come.

- **Not yet working in Mournhold: its quests and much of its play.** What already works there is under "Seen in play"
  (the way there and back, the walk from the Reception Area to Plaza Brindisi Dorom, both district doors into the Great
  Bazaar; this replaces the line of the earlier notes that the way there is not in the game). Not yet shown in play: the
  journal entries, a save and a load in Mournhold, and the quests. The Dark Brotherhood's attack in sleep that starts
  Tribunal was seen on the release image at level 40 only, naturally on a 12-hour rest and by `dbg dbattack`; other
  levels are still being tested
  ([GETPCSLEEP-NOT-CARRIED-OUT-67](../../bugs/GETPCSLEEP-NOT-CARRIED-OUT-67.md), the entry still open until a played
  game shows it). The palace's Reception Area ran at about 3 frames a second on the Raspberry Pi 4B with the
  debug display on (3.0 to 5.7 in the readings), still to be measured
  ([INTERIOR-RECEPTION-AREA-FPS-67](../../bugs/INTERIOR-RECEPTION-AREA-FPS-67.md)). Solstheim is not in the game; two of
  its models, the icebergs of the Mortrag Glacier, cannot be converted yet
  ([COLLISION-ICEBERG-CLIPNODE-BUDGET-67](../../bugs/COLLISION-ICEBERG-CLIPNODE-BUDGET-67.md)).
- **Fixed in source, still to be seen in play on a build of this release:** the districts' containers, items, activators,
  doors and people
  ([DISTRICT-PEOPLE-NOT-PLACED-67](../../bugs/DISTRICT-PEOPLE-NOT-PLACED-67.md),
  [DISTRICT-PLACED-THINGS-NO-ROW-67](../../bugs/DISTRICT-PLACED-THINGS-NO-ROW-67.md),
  [DOORS-DISTRICT-FRAMES-NOT-HOLDERS-67](../../bugs/DOORS-DISTRICT-FRAMES-NOT-HOLDERS-67.md)), the person's use box, the
  shared layout of menus and boxes, the prison ship's masts and table
  ([PRISON-SHIP-FLOOR-STUCK-67](../../bugs/PRISON-SHIP-FLOOR-STUCK-67.md)), the dock guard's post
  ([PIER-GUARD-WALKS-INTO-DOOR-65](../../bugs/PIER-GUARD-WALKS-INTO-DOOR-65.md), seen again on the dev2 image), the
  dialogue changes, the map's World tab, the birthsign window, the egg shell's look in first person, the third-person
  walk after the idle camera
  ([PLAYER-VANITY-WALK-STUCK-67](../../bugs/PLAYER-VANITY-WALK-STUCK-67.md)), the container fixes, the teleports to
  Tribunal's characters
  ([TP-BEING-TRIBUNAL-FALLS-THROUGH-67](../../bugs/TP-BEING-TRIBUNAL-FALLS-THROUGH-67.md)), the creatures' return on a
  reload ([ACTOR-TABLE-SAME-MAP-RELOAD-67](../../bugs/ACTOR-TABLE-SAME-MAP-RELOAD-67.md)), the error chain, the arrival
  in a flooded room ([ROOM-ARRIVAL-FLOODED-ON-ROOF-67](../../bugs/ROOM-ARRIVAL-FLOODED-ON-ROOF-67.md)). Their entries
  stay open until then.
- **Measured in the emulator, entries open until a played game of this release shows them:** the stop on a loading
  screen in busy places
  ([NET-VIVEC-ENTITY-PACKET-OVERFLOW-66](../../bugs/NET-VIVEC-ENTITY-PACKET-OVERFLOW-66.md)), the missing autosaves
  ([SAVE-AUTOSAVE-NOT-WRITTEN-67](../../bugs/SAVE-AUTOSAVE-NOT-WRITTEN-67.md)) and the missing wild creatures
  ([OUTDOOR-CREATURES-REGRESSION-66](../../bugs/OUTDOOR-CREATURES-REGRESSION-66.md),
  [OUTDOOR-CREATURES-HOME-CELL-67](../../bugs/OUTDOOR-CREATURES-HOME-CELL-67.md),
  [ACTOR-QUEUE-OTHER-MAP-67](../../bugs/ACTOR-QUEUE-OTHER-MAP-67.md)).
- **Mournhold's districts, open in the bug tracker:** they draw at 8 to 16 frames a second on the test build
  ([DISTRICT-FRAME-RATE-LOW-67](../../bugs/DISTRICT-FRAME-RATE-LOW-67.md)); the player drifts a few units after arriving
  in three of them ([DISTRICT-ARRIVAL-DRIFT-67](../../bugs/DISTRICT-ARRIVAL-DRIFT-67.md)); the debug teleport to the
  Great Bazaar landed under its street and under water on the dev3 image and was seen to land on the street on the
  release image (see "Seen in play"); the Plaza's fabricants,
  which belong to a later quest, attacked from the start of a new game
  ([PLAZA-FABRICANTS-LIVE-AT-START-67](../../bugs/PLAZA-FABRICANTS-LIVE-AT-START-67.md)); two Gaenors, one at level 50,
  attacked a new player in the Temple Courtyard
  ([GAENOR-ATTACKS-AT-START-67](../../bugs/GAENOR-ATTACKS-AT-START-67.md)); after a map change the new place's actors
  that took the old fighters' places in memory attacked at once, so peaceful people attacked a player who arrived from a
  fight ([COMBAT-FIGHT-CARRIED-TO-NEW-MAP-67](../../bugs/COMBAT-FIGHT-CARRIED-TO-NEW-MAP-67.md)); these three are fixed
  in source and were seen in play on the release image (see "Seen in play"; the entries stay open until the
  maintainer closes them); Godsreach's canal is reported dry, which is not proven: the
  first readings were taken while flying through walls, and a view from under the streets is the underwater one
  ([GODSREACH-CANAL-NO-WATER-67](../../bugs/GODSREACH-CANAL-NO-WATER-67.md), open, not proven); the water levers of Old
  Mournhold do not move the water
  ([MWSCRIPT-WATER-LEVEL-STATIC-67](../../bugs/MWSCRIPT-WATER-LEVEL-STATIC-67.md)); the Tower of Dusk is drawn
  with holes ([ROOM-TOWER-OF-DUSK-HOLES-67](../../bugs/ROOM-TOWER-OF-DUSK-HOLES-67.md)); the two frames of Plaza Brindisi Dorom are over the 16 MB zone
  budget ([CHIM-MOURNHOLD-PLAZA-OVER-16MB-67](../../bugs/CHIM-MOURNHOLD-PLAZA-OVER-16MB-67.md)); the Plaza is not drawn
  looking south from its arrival point
  ([DISTRICT-PLAZA-NOT-DRAWN-FROM-ARRIVAL-67](../../bugs/DISTRICT-PLAZA-NOT-DRAWN-FROM-ARRIVAL-67.md)); Godsreach's gate
  to the Plaza stood on a cell border and could not be used; its door is now written into both cells' tables and the gate
  was seen to open on the release image
  ([DISTRICT-GATE-ON-CELL-BORDER-67](../../bugs/DISTRICT-GATE-ON-CELL-BORDER-67.md), open until then); the Hall of
  Ministry holds seven Infected Rats at the start of a new game, hidden by their script rather than alive, and one
  attacked; no attack was seen on the release image
  ([ROOM-HALL-OF-MINISTRY-RATS-NOT-DISABLED-67](../../bugs/ROOM-HALL-OF-MINISTRY-RATS-NOT-DISABLED-67.md)); two of the
  three atronachs of Norenen-dur are dead seconds after they attack
  ([ROOM-NORENEN-DUR-ATRONACHS-DIE-67](../../bugs/ROOM-NORENEN-DUR-ATRONACHS-DIE-67.md)).
- **An actor placed by `dbg spawn` is booked in cell 0,0** instead of the player's cell, so nothing is drawn
  ([DBG-SPAWN-CELL-ZERO-67](../../bugs/DBG-SPAWN-CELL-ZERO-67.md), open).
- **A locked container never opens**: no key, lockpick or Open spell works on it
  ([LOCKED-CONTAINERS-NEVER-OPEN-67](../../bugs/LOCKED-CONTAINERS-NEVER-OPEN-67.md)).
- **The conversion makes models heavier than the original game**
  ([CONVERT-HEAVIER-THAN-ORIGINAL-67](../../bugs/CONVERT-HEAVIER-THAN-ORIGINAL-67.md)); the census lists them.
- **A resident standing in front of a door**
  ([WANDER-DOOR-RULE-66](../../bugs/WANDER-DOOR-RULE-66.md)): fixed in source, and the opening journey's step 9 passed on
  a test build of this line; the entry stays open until a snapshot's journey passes.
- **Bloodmoon's werewolves have no model yet**
  ([PLAYER-WEREWOLF-ROBE-NOT-BAKED-66](../../bugs/PLAYER-WEREWOLF-ROBE-NOT-BAKED-66.md),
  [NPC-WEREWOLF-NO-MODEL-66](../../bugs/NPC-WEREWOLF-NO-MODEL-66.md)).
- **A hostile scrib walks off instead of attacking**: measured to be the original's rule for the scrib; the scamp's case
  is still to be settled ([CREATURE-HOSTILE-FLEES-67](../../bugs/CREATURE-HOSTILE-FLEES-67.md), open).
- **The Heart Chamber's collapse is not animated, so the end of the main quest cannot play yet**
  ([ENDGAME-CHAMBER-COLLAPSE-63](../../bugs/ENDGAME-CHAMBER-COLLAPSE-63.md)).
- **A load can stop in the emulator**
  ([CHIM-SEYDA-BALMORA-LOAD-HANG-43](../../bugs/CHIM-SEYDA-BALMORA-LOAD-HANG-43.md)): so far it has been seen only in
  test sessions that use the remote console.
- **In the builder:** the image step and the room batch stages use too few cores
  ([BUILD-IMAGE-UNDERUSED-32](../../bugs/BUILD-IMAGE-UNDERUSED-32.md)), and the town stages' resident bake costs about 18
  to 20 times the CPU per resident of earlier builds, cause not yet found
  ([BUILD-RESIDENT-BAKE-CPU-18X-67](../../bugs/BUILD-RESIDENT-BAKE-CPU-18X-67.md)).
- **Resting and the stats window, open in the bug tracker:** a wilderness rest that is cut short brought no creature and
  no message on the dev3 image; on the release image the creature came from the region's list
  ([REST-CUT-NO-CREATURE-67](../../bugs/REST-CUT-NO-CREATURE-67.md)), but it came far too often in one session, fixed in
  source for the respin and still to be seen in play
  ([REST-CUT-TOO-OFTEN-67](../../bugs/REST-CUT-TOO-OFTEN-67.md)); the Stats window draws a raised attribute
  almost black and the birthsign icons brown until a saved game is loaded; the numbers are right
  ([STATS-WINDOW-COLOURS-UNTIL-LOAD-67](../../bugs/STATS-WINDOW-COLOURS-UNTIL-LOAD-67.md)); `dbg tp` with a room name
  that has a comma, as the place list shows it, is refused
  ([DBG-TP-ROOM-NAME-COMMA-67](../../bugs/DBG-TP-ROOM-NAME-COMMA-67.md)); `dbg tp ghostgate` says the place is not found
  ([DBG-TP-TYPED-PLACE-NOT-FOUND-67](../../bugs/DBG-TP-TYPED-PLACE-NOT-FOUND-67.md)).
- **Open in the bug tracker, creatures, people and the player's body:** a nix-hound moves like a person
  ([CREATURE-NIXHOUND-HUMAN-MOVES-67](../../bugs/CREATURE-NIXHOUND-HUMAN-MOVES-67.md)); the cliff racer's model is fixed
  in source and not yet checked in play ([CREATURE-RACER-MESH-SPIKE-58](../../bugs/CREATURE-RACER-MESH-SPIKE-58.md)); a
  creature whose root bone is not named Bip01 is drawn coarsely and away from its place
  ([CREATURE-TABLE-ROOT-TRAVEL-67](../../bugs/CREATURE-TABLE-ROOT-TRAVEL-67.md)); with a robe on the third-person body
  shows a cut at the waist ([PLAYER-ROBE-WAIST-SEAM-67](../../bugs/PLAYER-ROBE-WAIST-SEAM-67.md)); a turn of the view
  made while the idle camera orbits was undone, fixed in source and still to be seen in play
  ([VIEW-VANITY-UNDOES-SET-VIEW-67](../../bugs/VIEW-VANITY-UNDOES-SET-VIEW-67.md)); after a teleport to the Heart Chamber
  the player's punch does not land or show in third person
  ([PUNCH-3P-HEART-CHAMBER-67](../../bugs/PUNCH-3P-HEART-CHAMBER-67.md)); a spell effect on the player shows the dotted
  orb in some cases ([MAGIC-SHELL-ORB-NOT-EGG-67](../../bugs/MAGIC-SHELL-ORB-NOT-EGG-67.md)); the screen's red hue when
  the player takes damage is requested and its first version is in
  ([DAMAGE-RED-HUE-67](../../bugs/DAMAGE-RED-HUE-67.md)).
- **Open in the bug tracker, the inventory, containers, dialogue and the journal:** an item already worn showed
  "E/Enter equip", and its row now ends in Equipped; fixed in source and still to be seen in play
  ([INVENTORY-EQUIPPED-LABEL-67](../../bugs/INVENTORY-EQUIPPED-LABEL-67.md)); the item information box is in (see
  "New"), fixed in source and still to be seen in play
  ([INVENTORY-ITEM-INFO-67](../../bugs/INVENTORY-ITEM-INFO-67.md)); the aim hint of an owned container reads
  "Steal" instead of "Open" in red, repaired in source
  ([CONTAINER-OWNED-PROMPT-WORDING-67](../../bugs/CONTAINER-OWNED-PROMPT-WORDING-67.md)); a faction-owned container is
  free to take for any member whatever rank it asks
  ([OWNED-FACTION-RANK-GLOBAL-IGNORED-67](../../bugs/OWNED-FACTION-RANK-GLOBAL-IGNORED-67.md)); the container window
  stayed open when the player was moved to another place, fixed in source and still to be seen in play
  ([CONTAINER-WINDOW-SURVIVES-PLACE-CHANGE-67](../../bugs/CONTAINER-WINDOW-SURVIVES-PLACE-CHANGE-67.md)); accented
  letters and curly quotes in the console font showed as other characters, fixed in source and still to be seen in play
  ([UI-CONSOLE-FONT-SPECIAL-LETTERS-67](../../bugs/UI-CONSOLE-FONT-SPECIAL-LETTERS-67.md)); the debug command list can
  end a page on a group's title, repaired in source
  ([DBG-HELP-PAGER-TITLE-SPLIT-67](../../bugs/DBG-HELP-PAGER-TITLE-SPLIT-67.md)); a person answered Background with empty
  rank and faction words, fixed in source and still to be seen in play
  ([DIALOGUE-BACKGROUND-EMPTY-RANK-67](../../bugs/DIALOGUE-BACKGROUND-EMPTY-RANK-67.md),
  [DIALOGUE-RANK-WITHOUT-FACTION-67](../../bugs/DIALOGUE-RANK-WITHOUT-FACTION-67.md)); Goodbye did nothing, with no
  sign, while an answer waited for Continue, fixed in source and still to be seen in play
  ([DIALOGUE-GOODBYE-BLOCKED-HINT-67](../../bugs/DIALOGUE-GOODBYE-BLOCKED-HINT-67.md)). Not yet in, or not yet seen in a
  built game: the original's trade window
  ([BARTER-TRADE-WINDOW-MISSING-67](../../bugs/BARTER-TRADE-WINDOW-MISSING-67.md)), the expansions' dialogue
  ([DIALOGUE-ADDON-TOPICS-NOT-PLAYABLE-67](../../bugs/DIALOGUE-ADDON-TOPICS-NOT-PLAYABLE-67.md)), the sound of an answer
  ([DIALOGUE-ANSWER-VOICE-MISSING-67](../../bugs/DIALOGUE-ANSWER-VOICE-MISSING-67.md)), the dialogue's comparison with
  the reference engine
  ([DIALOGUE-OPENMW-AB-MISSING-67](../../bugs/DIALOGUE-OPENMW-AB-MISSING-67.md)), the topics a talk teaches
  ([DIALOGUE-KNOWN-TOPICS-NOT-CHECKED-67](../../bugs/DIALOGUE-KNOWN-TOPICS-NOT-CHECKED-67.md)), some text defines and
  conditions
  ([DIALOGUE-TEXT-DEFINES-PARTIAL-67](../../bugs/DIALOGUE-TEXT-DEFINES-PARTIAL-67.md),
  [DIALOGUE-CONDITIONS-PARTIAL-67](../../bugs/DIALOGUE-CONDITIONS-PARTIAL-67.md)), Charm's effect on disposition
  ([DIALOGUE-DISPOSITION-CHARM-ZERO-67](../../bugs/DIALOGUE-DISPOSITION-CHARM-ZERO-67.md)), the greyed topics and the
  Goodbye-only window
  ([DIALOGUE-EXHAUSTED-TOPICS-NOT-SEEN-67](../../bugs/DIALOGUE-EXHAUSTED-TOPICS-NOT-SEEN-67.md),
  [DIALOGUE-GOODBYE-ONLY-NOT-SEEN-67](../../bugs/DIALOGUE-GOODBYE-ONLY-NOT-SEEN-67.md)), and in the journal the links in
  quest entries, the notice for an empty entry, the values of a topic page, and the quest marks
  ([JOURNAL-HYPERLINKS-QUEST-ENTRIES-67](../../bugs/JOURNAL-HYPERLINKS-QUEST-ENTRIES-67.md),
  [JOURNAL-NOTICE-EMPTY-ENTRY-67](../../bugs/JOURNAL-NOTICE-EMPTY-ENTRY-67.md),
  [JOURNAL-TOPIC-PAGES-VALUES-AT-READ-67](../../bugs/JOURNAL-TOPIC-PAGES-VALUES-AT-READ-67.md),
  [JOURNAL-QUEST-ENTRIES-NOT-SEEN-67](../../bugs/JOURNAL-QUEST-ENTRIES-NOT-SEEN-67.md)).
- **Open in the bug tracker, loading and the debug aids:** memory that runs out or a damaged map file while a place
  loads ends the game instead of going back
  ([LOAD-FATAL-ERRORS-67](../../bugs/LOAD-FATAL-ERRORS-67.md)); a missing model file or a bad server message leaves the
  game on the loading screen ([LOAD-CLIENT-HALF-CONNECTED-67](../../bugs/LOAD-CLIENT-HALF-CONNECTED-67.md)); a place that
  cannot be loaded for another reason than not being in the build (a damaged map file, memory that runs out, a bad
  server message) is not named in the box
  ([LOAD-ERROR-NOT-NAMED-67](../../bugs/LOAD-ERROR-NOT-NAMED-67.md)); `dbg aw hors 0` started during play keeps the
  earlier game's script state
  ([HORS-IN-PLAY-NO-NEW-GAME-RESET-67](../../bugs/HORS-IN-PLAY-NO-NEW-GAME-RESET-67.md)); the container aim of
  `aw_placed` stood past the reach, fixed in source and still to be seen in play
  ([DBG-CONTAINER-AIM-OUT-OF-REACH-67](../../bugs/DBG-CONTAINER-AIM-OUT-OF-REACH-67.md)); the inspect line's health
  ([INSPECT-ACTOR-HEALTH-ZERO-67](../../bugs/INSPECT-ACTOR-HEALTH-ZERO-67.md), fixed in source).
- **Open in the bug tracker, the builder, the test tools and the trackers:** the image step's room actor bake runs on one
  core when every resident is cached
  ([IMAGE-ROOM-RESIDENTS-CACHED-ONE-CORE-66](../../bugs/IMAGE-ROOM-RESIDENTS-CACHED-ONE-CORE-66.md)); a stair collision
  unit of a Solstheim glacier cell takes 19.5 minutes on one core
  ([CHIM-MESH-STAIR-UNIT-SLOW-67](../../bugs/CHIM-MESH-STAIR-UNIT-SLOW-67.md)); a tester's build on a machine with 32 GB
  of memory ran out of memory after about 32 hours
  ([BUILD-TESTER-32GB-OOM-67](../../bugs/BUILD-TESTER-32GB-OOM-67.md)); the first `--npc-lod` build stopped again in the
  builder, fixed in source and to be confirmed on a build ([BUILD-NPCLOD-PATH-ARG-34](../../bugs/BUILD-NPCLOD-PATH-ARG-34.md)); the stage plan cannot read the
  creature-model unit keys ([BUILD-PLAN-UNIT-KEY-UNREADABLE-67](../../bugs/BUILD-PLAN-UNIT-KEY-UNREADABLE-67.md)); the
  actor library's two pools wrote through one temporary file name
  ([BUILD-ACTOR-LIBRARY-SHARE-RACE-67](../../bugs/BUILD-ACTOR-LIBRARY-SHARE-RACE-67.md), fixed in source); no build stage
  proves it read the game files the build selected
  ([STAGE-READS-SELECTED-MASTERS-67](../../bugs/STAGE-READS-SELECTED-MASTERS-67.md)); the per-model replacements of the
  everywhere recipe reach the outdoor frames only
  ([VISUAL-EVERYWHERE-ROOMS-67](../../bugs/VISUAL-EVERYWHERE-ROOMS-67.md)); a default build with the expansions took none
  of their outdoor cells, the door check and the stage of the districts stopped or re-keyed, and the CHIM tracker and
  region checks did not know the districts' cells, all fixed in source
  ([BUILD-LAYER-SETS-NEVER-TAKEN-67](../../bugs/BUILD-LAYER-SETS-NEVER-TAKEN-67.md),
  [DOOR-CHECK-MODULE-FRAME-MAPS-67](../../bugs/DOOR-CHECK-MODULE-FRAME-MAPS-67.md),
  [BUILD-MODULE-UNIT-CACHE-IN-KEY-67](../../bugs/BUILD-MODULE-UNIT-CACHE-IN-KEY-67.md),
  [BUILD-VISUAL-RECIPES-LAYER-ROWS-KEY-67](../../bugs/BUILD-VISUAL-RECIPES-LAYER-ROWS-KEY-67.md),
  [BUILD-PRESENTED-DATA-NO-WAIT-67](../../bugs/BUILD-PRESENTED-DATA-NO-WAIT-67.md),
  [BUILD-REGION-NO-LAND-PRESENTED-67](../../bugs/BUILD-REGION-NO-LAND-PRESENTED-67.md),
  [TRACKER-PRESENTED-CELLS-UNKNOWN-67](../../bugs/TRACKER-PRESENTED-CELLS-UNKNOWN-67.md),
  [CHIMPORT-LAYER-CELL-EMPTY-67](../../bugs/CHIMPORT-LAYER-CELL-EMPTY-67.md)); measured tables of a second expansion
  layer would re-key finished units, fixed in source and to be confirmed
  ([MESH-TABLE-SECOND-LAYER-REKEY-67](../../bugs/MESH-TABLE-SECOND-LAYER-REKEY-67.md),
  [MESH-TABLE-LAYER-GROWS-67](../../bugs/MESH-TABLE-LAYER-GROWS-67.md)); two of Tribunal's Dark Elf hairs stopped the
  player-view stage, fixed in source
  ([PLAYER-PARTS-HAIR-FALSE-STOP-67](../../bugs/PLAYER-PARTS-HAIR-FALSE-STOP-67.md)); the room actor fit's inputs leave
  out the room's placements
  ([BUILD-ROOM-ACTOR-INPUT-RECORD-67](../../bugs/BUILD-ROOM-ACTOR-INPUT-RECORD-67.md)); `--check` cannot read a
  read-only workspace
  ([BUILD-CHECK-READONLY-WORKSPACE-67](../../bugs/BUILD-CHECK-READONLY-WORKSPACE-67.md)); the chimport region route
  copies reused units
  ([AW-CHIMPORT-REGION-POOL-COPY-67](../../bugs/AW-CHIMPORT-REGION-POOL-COPY-67.md)); a version opening leaves the
  Toolkit header and baselines at the old release
  ([VERSION-BUMP-TOOLKIT-HEADER-67](../../bugs/VERSION-BUMP-TOOLKIT-HEADER-67.md)); the actor grounding census and the
  container count read some cases wrongly
  ([ACTOR-GROUNDING-CENSUS-CONFLICTS-67](../../bugs/ACTOR-GROUNDING-CENSUS-CONFLICTS-67.md),
  [CENSUS-DISTRICT-CONTAINERS-AS-ROOMS-67](../../bugs/CENSUS-DISTRICT-CONTAINERS-AS-ROOMS-67.md)); the Toolkit's headline
  and local view
  ([TOOLKIT-HEADLINE-EXPANSIONS-NOT-STARTED-67](../../bugs/TOOLKIT-HEADLINE-EXPANSIONS-NOT-STARTED-67.md)); the mesh
  export's texture names and the CHIMport page are fixed in source
  ([MESH-EXPORT-FULL-67](../../bugs/MESH-EXPORT-FULL-67.md),
  [DOCS-CHIMPORT-EXPANSIONS-67](../../bugs/DOCS-CHIMPORT-EXPANSIONS-67.md)); things the maintainer confirmed in play
  come back broken, and the look book is the guard, repaired in source
  ([REGRESSION-GUARD-MISSING-67](../../bugs/REGRESSION-GUARD-MISSING-67.md)); test and tool faults: an emulator session
  given a non-file engine, a session ended by one empty state read, the Ghostgate still facing rock, a startup-watch
  timing test and a process-pool test that failed once on a busy machine, the register tool's write errors and lost
  concurrent write, and generated pages left stale after a register change
  ([SESSION-ENGINE-NOT-A-FILE-67](../../bugs/SESSION-ENGINE-NOT-A-FILE-67.md),
  [SESSION-STALL-EMPTY-STATE-READ-67](../../bugs/SESSION-STALL-EMPTY-STATE-READ-67.md),
  [TEST-GHOSTGATE-ARRIVAL-FACES-ROCK-67](../../bugs/TEST-GHOSTGATE-ARRIVAL-FACES-ROCK-67.md),
  [TEST-BUILD-STALL-STARTUP-TIMING-67](../../bugs/TEST-BUILD-STALL-STARTUP-TIMING-67.md),
  [TEST-ACTOR-GROUND-SLICED-POOL-LOAD-67](../../bugs/TEST-ACTOR-GROUND-SLICED-POOL-LOAD-67.md),
  [REGISTER-WRITE-EINVAL-67](../../bugs/REGISTER-WRITE-EINVAL-67.md),
  [REGISTER-CONCURRENT-WRITE-LOST-67](../../bugs/REGISTER-CONCURRENT-WRITE-LOST-67.md),
  [DOCS-REGENERATE-ALL-MISSING-67](../../bugs/DOCS-REGENERATE-ALL-MISSING-67.md)).
- From [v0.0.67-dev2](RELEASE-v0.0.67-dev2.md) and [v0.0.66](RELEASE-v0.0.66.md): their Known lists stand for what is
  not named here, except their lines that the way to Mournhold is not in the game: the first lines of this list replace
  them ([NOTES-MOURNHOLD-WAY-STALE-67](../../bugs/NOTES-MOURNHOLD-WAY-STALE-67.md)). Every other open entry is in the
  [bug tracker](../../BUGS.md).
