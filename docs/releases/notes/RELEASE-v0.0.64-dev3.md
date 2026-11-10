# AmiWind v0.0.64-dev3 (in development)

_Last updated with AmiWind v0.0.64-dev3 (10 November 2026)._

Development snapshot, 10 November 2026, in development. Running on CHIM Engine v0.2.2. Previous snapshot:
[v0.0.64-dev2](RELEASE-v0.0.64-dev2.md). Previous release: [v0.0.63: Every Script Of Vvardenfell](RELEASE-v0.0.63.md).

The third snapshot of v0.0.64, "Gone Beyond The Gate". Spells, powers and enchantments of the game take effect again (a
fault present since v0.0.63 left every game spell without its effects), the console can activate the Ghostgate's
switches and the cursed coins by id, the Red Mountain lava is stood in and kills, the journal sorts a quest's state by its
endings, the renderer has a see-through face pass for cobwebs and hanging growths (off by default), and the builder has a
test-only star-shaped copy of Solstheim's spruces that brings a forest view from 45,964 faces at the median to 6,096.
No expansion area is part of the game image yet. 605 of the 1,207 scripts run as scripts and 9 more are carried by
AmiWind's own code, as in v0.0.64-dev2 (measured again for this snapshot). The game needs 32 MB of Fast RAM, and the
emulator presets of this snapshot have it.

This snapshot carries v0.0.64-dev1 and v0.0.64-dev2 as well. Neither was published on its own, so this is the first
snapshot of v0.0.64 on GitHub, and their changes (listed in [the dev1 notes](RELEASE-v0.0.64-dev1.md) and
[the dev2 notes](RELEASE-v0.0.64-dev2.md), summarised below) arrive together with these.

## Checked in play on a test build

Four changes were looked at in play on a test build with the fixed engine:

- **Argonian Breathing** was cast and the character stayed under water for its 120 seconds.
- **The Ghostgate's switches,** activated by id from the console, raised the portcullises.
- **The door list's arrival lines** (the line a room prints when it is reached through a town's door list) were printed.
- **Lava** was stood in with `dbg tp` and killed the character.

These are checks on a test build, not on this snapshot's image; the in-game checklist below asks for them again.

## Checked by tests, not yet in play

Every other change below is checked by the test suite and the gate of this snapshot. None of it has been seen in play on a
build of this snapshot yet. The register keeps an entry open until its change is seen on an image, so several entries named
below are open although their change is made.

## New since v0.0.64-dev2

### Spells, powers and enchantments

- **Game spells take effect again.** The engine's actor table read only 32 of the sections of the compiled scripts file,
  which has 39 since v0.0.63, so the spell effects, magic effects, enchantments and starting spells were never found and
  every game spell, power and enchantment did nothing when cast (`SPELL-EFFECTS-TABLE-CUT-64`, present since v0.0.63;
  open until seen in play on an image). The engine reads up to 64 sections and refuses a file with more, and a gate test
  checks the limit against the builder's section list, so a section can no longer fall outside the table unnoticed.
- **The console's id search finds what it looked for.** The sorted id search treated a successful read of the actor table
  as a failure, so `getspell`, a trap's spell and `additem` of a known item missed every id (`UNDERWATER-BREATH-62`, the
  cause of its second report).
- **Argonian Breathing is the race's castable spell:** Water Breathing for 120 seconds on the caster, and it works when
  cast. The race power was checked in play on a test build (see above); `UNDERWATER-BREATH-62` stays open until it is seen
  on an image.

### The world and the console

- **Activating by id.** Buttons and objects that no script names (the Ghostgate's gate switches, the cursed coin) are now
  found by the console's Activate through a new on-disk name section, which lists every placed scripted reference by the
  hash of its id; the console takes the nearest attached instance. The gate switches raise the portcullises
  (`WORLD-BUTTONS-62` and `MARKS-SUMMON-CARRIERS-NOT-LIVE-63`; the switches checked in play on a test build, the coin
  not).
- **The door list shows each door's arrival point,** as a room start does (`DBG-TP-DOORLIST-NO-ARRIVAL-LINE-63`).
- **Lava is stood in and kills.** A debug teleport onto lava was refused as a water surface and fell back to the centre of
  the frame; the feet now stand in the liquid on its bed (`GODMODE-LAVA-DEATH-62`, `LAVA-NO-DAMAGE-63`).
- **`dbg tp X Y Z` takes the nearest floor beside the point** when the point itself has none (rings of 32 units out to 128;
  `DBG-TP-NO-FLOOR-FALLBACK-63`).
- **God mode stays on across map changes.** A map change makes a new player, so `tgm` and `dbg god` were lost on every
  teleport, door and load; the switch is kept and put back on the new player, and a new game clears it
  (`GODMODE-LOST-ON-MAP-CHANGE-64`).

### The journal and the factions

- **A quest's state follows its entries.** The journal book replays each quest's entries in the order earned against the
  journal table's finished and restart marks: a success or failure ending finishes the quest, a restart entry reopens it,
  and an index without an entry changes nothing. The active and finished lists are split by that.
- **The expulsion shows the game's own message.** A reported crime against a faction member or a faction's item shows the
  original's expulsion message with the faction's name; changed and checked by tests, not yet seen in play
  (`FACTION-EXPEL-MESSAGE-64`, open until it is). The factions row of the
  [game features page](../../GAME_FEATURES.md) lists what is carried and what is missing; the stats page still lists no
  factions, reputation or bounty (`FACTION-STATS-PAGE-64`, open).

### The renderer

- **A see-through face pass.** Cobwebs, the growths hanging under giant mushrooms and trees, and decals were drawn as solid
  sheets because world, room and model faces had no see-through texel kind. The converter marks a texture whose alpha
  leaves at least 1 % of its texels under half alpha as a see-through texture (its own unit kind, so every other
  texture keeps its key), and the engine draws those faces in a separate pass after the opaque world: lit, clipped,
  one span per row, the see-through texels skipped. The switch `dbg fence` (`aw_fence`) is **off by default** until a
  measured comparison on a full build decides (`ROOM-DECAL-ALPHA-62`, open). Model faces still cannot be alpha-tested, so
  crossed tree panels cannot be model variants (`CHIM-MODEL-FENCE-FACES-64`, open).
- **The Heart of Lorkhan's fire shield and hidden glows no longer cover it.** The room creature bake took every shape the
  model shows at rest, including a translucent scrolling shield and six glow quads seen only while it dies; a model skin
  has no translucency, so the shield hid the heart. Such shapes are left out of a creature and listed in its record; the
  heart bakes at 480 triangles (562 before reduction; `HEART-EFFECT-SHELLS-OPAQUE-64`).

### The builder

- **Star-shaped tree copies for Solstheim's spruces (test builds only, option unset by default).**
  `--chim-sol-tree-copies star` draws each Solstheim tree model as a closed star-shaped crown on a six-sided bark trunk,
  30 faces per tree instead of 472 to 724, with the needles baked opaque from the model's side view so the star has no
  black gaps; a new stage bakes the billboard and four oriented views per tree model. Measured on the Solstheim forest
  frame -23,20 with the same source and command: faces per view at the median 45,964 to 6,096 (maximum 61,175 to 16,942),
  placed faces 238,504 to 43,494, stored model faces 50,387 to 30,885, peak ring model bytes 3,084,564 to 1,769,176. The
  settings are in `config/tree-copies.json`; unset, nothing changes and the base CHIM stage reads none of it
  (`CHIM-SOLSTHEIM-TREE-FACES-64` stays open until the method is measured on a full build). The numbers are
  in [the first Solstheim frame, measured](../../performance/SOLSTHEIM-FIRST-FRAME-v0.0.64.md).
- **The unit cache keeps entries across expansion rows.** The dev2 build baked all 418 NPC appearances and every creature
  model again although their keys were unchanged: the entries record the collision hull table whole, and the Bloodmoon
  rows added to it changed the whole-table decision. A whole-table record now also matches the table without its
  expansion rows; a base row change, a layer row changed after an entry recorded it, or a single mesh row still re-keys.
  The cause of `NPC-LIBRARY-NO-UNIT-CACHE-63`; the creatures still rebake, which stays open.
- **The resident budget tool keeps its caps block.** Raising or lowering the budget dropped the command cap block and its
  note from the budget file (`BUILD-RESIDENT-BUDGET-CAPS-DROPPED-64`, fixed).
- **The load stall experiments.** The boot smoke can run without the remote console and judge by screenshots, add extra
  emulator lines and check they were taken, and alternate two variants and count passes and stops
  (`CHIM-SEYDA-BALMORA-LOAD-HANG-43`, still open).
- **The Solstheim test image** takes the Bloodmoon frames as their own store (`--chim-sol-test` only).

### The Toolkit

- **Three map panes on the CHIM Progress Tracker:** Vvardenfell, Solstheim (the same grid framed on the island, its rooms
  under the map) and Mournhold (a screen of its own). Each has its own done, partial and missing counts, and the
  completion line keeps one rate per pane. A data set without an expansion hides its pane
  ([CHIM Progress Tracker](../../chim/PROGRESS_TRACKER.md), [the Toolkit](../../AMIWIND_TOOLKIT.md)).

### The register

- Entries of the day: `RACE-RESIST-NOT-ON-SPELL-DAMAGE-64` (open: a race ability's resistance is not applied to spell
  and trap damage), `BUILD-ACTOR-LIBRARY-UNDERUSED-54` (seen again),
  `BUILD-RESIDENT-BUDGET-CAPS-DROPPED-64` (fixed), `FACTION-EXPEL-MESSAGE-64` and `FACTION-STATS-PAGE-64`, the findings of
  the dev2 build and delivery, and what assumes one island once Solstheim joins the exterior world.

## Carried from v0.0.64-dev2 and v0.0.64-dev1

- **From dev2:** a trapped door, load door or container springs its trap on the player instead of opening (the key
  disarms it; 457 trapped references with 85 spells in Morrowind.esm); a switchable load trace (`dbg loadtrace on|off|dump`)
  and a memory line per load for the Seyda Neen to Balmora stall; the Toolkit's expansion views; the first Solstheim frame
  as a test build (`--chim-sol-test`); the [world mechanisms census](../../WORLD_MECHANISMS.md).
- **From dev1:** the builder's expansion switch (`--dlc tribunal|bloodmoon|both|none`, `--no-dlc`) with the base world's
  keys independent of the expansion files; master-list cell and room readers; the expansions' own room id ranges and
  store units; the [census of Tribunal and Bloodmoon](../../performance/EXPANSIONS-CENSUS-v0.0.64.md); Activate on
  world objects that are not characters; `dbg tp` with the floor under the feet as its height; scripts that cast on other
  characters; the Argonian's water breathing as the original's cast spell; sessions that examine every stop before a
  retry.

## Needs 32 MB Fast RAM

The game needs 32 MB of Fast RAM. At 16 MB parts run and over-limit interiors show the warning box.

## In-game checklist for this snapshot

- Cast Argonian Breathing as an Argonian and stay under water: 120 seconds, with the breath bar not running out.
- The Ghostgate's switches on both sides: the portcullises rise (the console's Activate by id on a switch).
- A quest with two endings in the journal (for example one that can fail or succeed): it moves from the active to the
  finished list at its ending, and back on a restart entry.
- `dbg fence on` at a cobweb in the Andrano tomb: the web is see-through; then `dbg fence off`.
- A game spell, a power and an enchantment from the spell list: each has its effect.
- The Red Mountain lava with `dbg tp` and god mode, across a door or a load.
- Carried over from v0.0.64-dev2 and v0.0.64-dev1: a trapped chest or door, `dbg loadtrace` on the trip from Seyda Neen to
  Balmora, the Toolkit's three map panes with a build that holds an expansion, and a script that casts at another
  character.

## Known in this build

- **Spells, powers and enchantments** take effect by the test suite; only Argonian Breathing was cast on a test build, and
  none is seen on an image (`SPELL-EFFECTS-TABLE-CUT-64`).
- **A race ability's resistance does not reduce spell and trap damage** (`RACE-RESIST-NOT-ON-SPELL-DAMAGE-64`).
- **The see-through pass is off by default** and not measured on a full build (`ROOM-DECAL-ALPHA-62`).
- **The Solstheim star trees are a test-build option;** Solstheim is not in the game image, and its forests are not
  measured on a full build (`CHIM-SOLSTHEIM-TREE-FACES-64`).
- **Akulakhan's Chamber loads three times at 32 MB Fast RAM** (`AKULAKHAN-CHAMBER-32MB-STALL-53`), and the end of the main
  quest cannot play yet: the heart is not placed in the room and the chamber's collapse is not animated
  (`ENDGAME-CHAMBER-COLLAPSE-63`, `CHIM-ROOM-HEART-CHAMBER-LOAD-50`).
- **The stats page lists no factions, reputation or bounty** (`FACTION-STATS-PAGE-64`).
- **The builder's creature models still rebake on a rebuild** after the unit cache fix for the NPC appearances
  (`NPC-LIBRARY-NO-UNIT-CACHE-63`), and the actor-library stage runs under its cores again
  (`BUILD-ACTOR-LIBRARY-UNDERUSED-54`).
- Tribunal and Bloodmoon are not built into the image yet (`BUILD-EXPANSIONS-31`).
- The trip from Seyda Neen to Balmora sometimes stalls on the loading screen in the emulator; the cause is not found
  ([CHIM-SEYDA-BALMORA-LOAD-HANG-43](../../bugs/CHIM-SEYDA-BALMORA-LOAD-HANG-43.md)).
- A player who becomes a werewolf is not drawn as the werewolf (`WEREWOLF-BODY-NOT-DRAWN-63`).
- The shores and pond edges still run in saw-tooth steps; the fix needs a world rebuild
  ([INLAND-SHORE-29](../../bugs/INLAND-SHORE-29.md)).
- The game image is still larger than the original game data (`IMAGE-BIGGER-THAN-ORIGINAL-62`).
- From [v0.0.63](RELEASE-v0.0.63.md): the open entries of its Known list stand, among them pickpocketing and owned
  locks not done. Every other open entry is in the [bug register](../../BUGS.md).
