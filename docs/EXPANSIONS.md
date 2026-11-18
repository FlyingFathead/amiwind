# The expansions: Tribunal and Bloodmoon

_Last updated with AmiWind v0.0.67-dev1 (17 November 2026)._

<!-- contents start -->
## Contents

- [What the expansions are, and your own copies](#what-the-expansions-are-and-your-own-copies)
- [What the builder does with them today](#what-the-builder-does-with-them-today)
- [What you can see in the game today](#what-you-can-see-in-the-game-today)
- [What you cannot see yet](#what-you-cannot-see-yet)
- [The three stages, and where each land stands](#the-three-stages-and-where-each-land-stands)
- [How the two places fit into the game](#how-the-two-places-fit-into-the-game)
- [The plan](#the-plan)
- [How the expansions are implemented](#how-the-expansions-are-implemented)
- [Known issues](#known-issues)

<!-- contents end -->

AmiWind's world comes from the original Morrowind game, and Morrowind has two expansions: **Tribunal**, which adds the
city of Mournhold, and **Bloodmoon**, which adds the island of Solstheim. This page says what the builder does with
them today, what can be seen in the game now, how the two places are planned to fit into the game, and what is known to
be missing. The short version: the data of both expansions is part of the build by default since v0.0.66-dev2 and
their rooms are in the image, but Mournhold's outdoor districts and Solstheim's ground are not built yet.

## What the expansions are, and your own copies

- **Tribunal** (`Tribunal.esm` and `Tribunal.bsa`) adds Mournhold and its rooms, a set of new quests and scripts, and
  small additions to places of the base game.
- **Bloodmoon** (`Bloodmoon.esm` and `Bloodmoon.bsa`) adds Solstheim, its rooms, its quests and its scripts.

AmiWind ships none of the original game's files. Like the base game, the expansions come from **your own copy** of
Morrowind, in the Game of the Year edition that holds all three games (see
[Morrowind editions](MORROWIND_EDITIONS.md) and [Known inputs](KNOWN_INPUTS.md)). Without the expansion files the
builder warns, names the missing expansion and builds the base game alone.

## What the builder does with them today

- **Both expansions are selected by default.** The builder uses every expansion it finds. `--no-dlc` (the same as
  `--dlc none`) builds the base game alone, and `--dlc tribunal`, `--dlc bloodmoon` or `--dlc both` choose the set. The
  chosen set is printed as the expansion layers of the build ([Known inputs](KNOWN_INPUTS.md#expansions-found-or-not)).
- **One reader merges the files.** The reader merges the base game file with the selected expansions' files by the rules
  a load order has, and the archives are read in load order, the later one winning. A stage that reads the game's cells,
  rooms and records sees the merged result.
- **The cache keys follow the selection.** A build's stage keys, unit caches and CHIM unit keys follow the expansions
  that are selected, and the unit caches are keyed by what each unit reads. Switching the expansions on rebuilds only
  what the expansion files change; a build for the base game alone keeps the keys it had. Measured against the dev1
  units, with both expansions selected 55 of the 1,769 room residents change, 4 of the 80 player view units and about
  3 % of the NPC library's appearances ([v0.0.66-dev2 notes](releases/notes/RELEASE-v0.0.66-dev2.md)).
- **The lists include the expansions' places.** When Bloodmoon is selected, Solstheim's cells are added where they are
  finished, and the expansions' rooms, Mournhold's five districts among them, are added as their own batches after the
  island's, so the island's batches and ids do not change.
- **The tables are being made to read the expansions.** Every table the builder makes from the game data is meant to read
  the selected expansions too. Done: the focus boxes of named objects, the rooms in the focus, item and area tables, the
  world survey, the exterior plan (the merged game data over the base game's exterior grid, as the survey reads it), the
  actor library's creatures (the 37 creature meshes only the expansion archives hold), and the archives of the selected
  expansions in every stage that reads the merged game data. Still read from the base game alone: the magic and travel
  tables, the dialogue lookup, the container census room numbers and the harvest catalogue; the creature census is not
  yet checked. The open entries are in the [bug register](BUGS.md).
- **What the build does not hold yet is set aside, named.** The placements of the exterior cells only Bloodmoon adds are
  left out of the scenery and flora stages and counted, and the doors and markers that lead into Solstheim's exterior,
  Mournhold's five districts or an expansion room the room stage could not convert are held back in the world door
  table with their reason, so they stay inert in the game instead of stopping the build. Every other door must still be
  linked.
- **The expansion files are checked before any stage.** Since v0.0.66-dev3 every selected expansion file must be in
  the data folder with a known SHA-256 ([Known inputs](KNOWN_INPUTS.md)); a missing or different file stops the build
  before its first stage with one line that names the file and the fix (the files in the data folder, or `--no-dlc`).

## What you can see in the game today

- **The place list.** The `dbg tp` list of places reads the selected expansions as well as the base game. Mournhold's
  and the other expansion rooms the image holds are listed by name (a search for "Mournhold" finds them), and a
  Solstheim place is listed only where the build holds its world. With the base game alone the list is as before
  ([console commands](AMIWIND_CONSOLE_COMMANDS.md)).
- **The data in the tables.** The [MWScript tracker](MWSCRIPT_FEATURES.md) counts every script of the three game files
  and says which run: of Tribunal.esm's 255 scripts, 236 are used (45 run, 4 wait for a function, 187 belong to
  Mournhold); of Bloodmoon.esm's 336, 310 are used (48 run, 17 wait for a function, 245 belong to Solstheim). The
  [world mechanisms](WORLD_MECHANISMS.md) page lists the switches and levers of Mournhold and Solstheim, marked as not in
  the image yet, and the [survey](WORLD_SURVEY.md) lists Solstheim's exterior cells. The
  [census](performance/EXPANSIONS-CENSUS-v0.0.64.md) counts the places, placements and models of both.

- **The rooms of both expansions.** The room stages convert the expansions' rooms with the island's: Mournhold's palace,
  temple, shops and houses and Solstheim's rooms are in the image and can be entered with `dbg tp` and a room's map
  name. Checked on the v0.0.66 image on a Raspberry Pi 4B (17 November 2026): the two transport scripts of the trip
  between Ebonheart's Grand Council Chambers and Mournhold's Royal Palace, run through the console's test aid for a
  dialogue answer's result script, move the player to the Reception Area beside Effe-Tei and back in front of Asciene
  Rane. The trip through the dialogue window itself has not been played yet.

## What you cannot see yet

No finished Mournhold or Solstheim is in the game. Mournhold's five outdoor districts are not built, so the doors that
lead out of the palace and the temple lead nowhere; there is no Solstheim ground to walk on and no boat to it; and no
script attached to a person, creature or object of the two expansions runs yet (the build does not bind them).
The data being selected by default is the road to them, not their arrival.

## The three stages, and where each land stands

Each expansion is brought in the way the base game was, in three stages, each with a count that is measured on a build:

1. **The world.** Every exterior cell and every room converted and reachable.
2. **The people and creatures.** Everyone the expansion places, in its own places and in Vvardenfell, present where the
   original puts them and complete: attributes and other stats, inventory and equipment, combat style, animations, and
   the scripts attached to them.
3. **The script logic.** Global and start scripts, quest and dialogue result scripts, the dialogue's choices and
   filters, message boxes, stats set by scripts, and the expansions' movies.

Counted on the v0.0.66 build (17 November 2026):

| | The world | People and creatures: placed / complete, of all placements | Scripts: compiled / attached to a placement |
| --- | --- | --- | --- |
| Mournhold (Tribunal) | the five districts 0 of 5; the rooms in the image except the districts and two set-aside cells | 354 / 90 of 412 | 194 / 0 |
| Solstheim (Bloodmoon) | 0 of 144 land cells; its rooms in the image | 274 / 8 of 476 | 256 / 0 |
| Placed in Vvardenfell by the expansions | (base game cells) | 59 / 12 of 59 | Tribunal 42 in use, all run; Bloodmoon 54 in use, 48 run |

Most of the incomplete ones lack one of three things: the script attached to them, a place that is not built yet (57
stand in Mournhold's districts, 202 outdoors on Solstheim), or an inventory rolled from a levelled list, a gap the base
game shares. No stat and no combat style is missing.

## How the two places fit into the game

### Mournhold

Mournhold has no real outdoors of its own: the base game's exterior cells that Tribunal touches hold one new placement
in all. The city is made of interior cells, and in Tribunal's data five of them carry the flag that makes a cell behave
like an exterior. They are reached by travel and not by the world grid, each is its own space, and they are joined to one
another by doors. The five are **Godsreach**, the **Great Bazaar**, **Plaza Brindisi Dorom**, the **Royal Palace
courtyard** and the **Temple courtyard**. The base game has no such cell. Counted placements: Great Bazaar 315, Temple
Courtyard 302, Godsreach 282, Plaza Brindisi Dorom 187, Royal Palace courtyard 126
([census](performance/EXPANSIONS-CENSUS-v0.0.64.md)).

The plan for Mournhold:

- The five districts are built into **one unified exterior of their own**, apart from the island's map. It shares the
  game's universal sky, the weather of Mournhold's region and the sun, and the districts stay joined by their load
  doors, as in the original.
- The city's **ordinary rooms** (103 interior cells, 98 with placements) are built like every other interior, entered
  and left through doors like any town, through the normal room path.
- The **weather** is the weather of Mournhold's region, which the original gives as clear, cloudy, foggy, overcast, rain
  and thunder with set chances, and which Tribunal's own scripts change at story events. Where the story calls for it,
  the scripts, not a fixed setting, decide the weather.
- Each district has its **own local map**, drawn like a room's, and the world map keeps your marker at Ebonheart while
  you are in Mournhold (see Getting to Mournhold below).

In the v0.0.66-dev2 snapshot the five districts are set aside: the room stages skip them and list them, and they come
with Mournhold's own exterior.

How they reach the outdoor converter (in work for v0.0.67): the converter reads squares of exterior grid cells, and a
district is an interior cell with its own coordinates and no terrain. `tools/presented_exterior.py` therefore writes
a presented copy of the merged game data in which each district is a block of exterior cells of its own, in a row
south of every island and apart from the other blocks, with its placements moved by one offset and every door or
marker that names the district pointing at the moved position; everything else is copied unchanged. The blocks
come from `config/presented-exteriors.json` and the districts' names, so the same game files always give the same
places. On the Game of the Year files: Godsreach 1 by 2 cells, the Great Bazaar and Plaza Brindisi Dorom 2 by 1, the
Royal Palace courtyard 1 by 1, the Temple courtyard 2 by 2; 40 door and marker destinations are rewritten. No
district is in a build yet.

The outdoor converter reads that presented copy from a **presented data folder**, one folder for both expansions
(`tools/presented_data.py`): the merged game data with the presented districts under the base game file's name, so
Solstheim's cells and land are read from the same file as Vvardenfell's; the selected expansion files as empty
stand-ins, so the same expansions stay selected and their archives are read in load order as in any build; and
every other file and folder of your data folder as a link, never a copy. With the base game alone no such folder is
made and the build reads your data folder as before.

### Getting to Mournhold

In the original game the way in is a teleport, and AmiWind plans to keep it as a teleport:

- From the start of the Tribunal expansion, **Asciene Rane**, who stands in Ebonheart's Grand Council Chambers,
  teleports you to Mournhold: you arrive in the Royal Palace's Reception Area, an ordinary room. **Effe-Tei**, there,
  sends you back to the Grand Council Chambers.
- Later in the main quest, **Almalexia** gives **Barilzar's Mazed Band**, which teleports you from anywhere to Vivec's
  Temple, to Sotha Sil or to Mournhold's Temple; in Mournhold you land in the Temple's High Chapel.

AmiWind has no separate travel system for this. These are dialogue choices whose result scripts move the player, and
they run on the dialogue and script support the game already has ([dialogue features](DIALOGUE_FEATURES.md),
[MWScript tracker](MWSCRIPT_FEATURES.md)). The rooms named above are read from Tribunal's data. Mournhold is not
converted yet: the Reception Area is a room and converts with the other rooms, and the five districts are converted as
described above, so the trip works once they are. The way there, through Ebonheart and the Grand Council Chambers,
still needs a playtest.

While you are in Mournhold, the world map keeps your marker at Ebonheart, the last place outdoors you left from. Each of
the five outdoor districts has its own local map, drawn like a room's.

### Solstheim

Solstheim is an outdoor island and becomes **an extension of the island's grid**, built like the rest of the exterior:
through the same conversion and the same reduction methods (the mesh optimizer, the collision optimizer and the
per-mesh visual recipes), with no special handling.
Bloodmoon's data holds 173 exterior cells; 18 of them are base game cells, and **155 are new ground** (144 of them with
land, 6 seabed and 5 open water). The island lies at cells x -29 to -16, y 14 to 28. The median new cell holds 120
placements and the densest 579. Its forests are heavy: a dense forest view draws about six times the faces of a median
Vvardenfell view, and the densest forest region lies at exterior cell (-27, 25) ([census](performance/EXPANSIONS-CENSUS-v0.0.64.md)).
The survey keeps the 155 cells in its list of expansion-only cells and plans none of them until the exterior is
converted ([world survey](WORLD_SURVEY.md)). The sea around the island and between it and Vvardenfell has to be
generated.

## The plan

- **Tribunal (Mournhold):** the five districts as one exterior of their own, the ordinary rooms, the weather driven by Tribunal's
  scripts, the teleport trip above, then the 187 scripts that belong to Mournhold.
- **Bloodmoon (Solstheim):** the exterior cells as part of the outdoor map, with the tree method its forests need (the
  star-shaped spruces and tree crowns are test-build methods that are measured but not settled), then its rooms and the
  245 scripts that belong to Solstheim.
- **Both:** the builder checks the expansion files before any stage, and every table reads the expansions. The
  [roadmap](ROADMAP.md) has the order and the current state.

## How the expansions are implemented

The order of the work, from the files to the playtests. Each step is tracked in the [roadmap](ROADMAP.md).

**What dev2 has and does not have.** dev2 has the data of both expansions in the build by default, the merged reader, the
archives read in load order, keys that follow the selection and lists that include the expansions' places. It does not
have Mournhold's five districts (they are set aside, so the doors leading out of the palace and the temple lead nowhere
yet), Solstheim's ground, the expansions' scripts running, or the check of the expansion files. The census of the changes
the expansions make to the base game is being made; the chains below are what is known so far from the game files.

1. **The files.** Both expansions' files are required and checked against known SHA-256 values before any stage (done
   in v0.0.66-dev3), and every stage reads the selected archives (done in dev2).
2. **The changes to Vvardenfell.** Every record the expansions add to or change in the base game's world is listed from
   the game files (references placed in base cells, changed people and creatures, lines in base topics, new topics,
   scripts and start scripts, globals, the journal) and each is checked in the build. A chain works when four things hold:
   the speaker is placed, the dialogue line can be reached, its script is compiled and attached, and the destination is
   present.
   - **Tribunal, to Mournhold:** **Asciene Rane** in Ebonheart's Grand Council Chambers offers the trip; the dialogue's
     result script (the transport script) moves the player to the Royal Palace's Reception Area. **Effe-Tei** there sends
     the player back to the Grand Council Chambers. Needs: Asciene Rane placed in Ebonheart, her line reachable, the
     script running, the Reception Area present, and Effe-Tei's way back.
   - **Tribunal, the Mazed Band:** the ring, given later in the main quest, moves the player to Vivec's Temple, Sotha Sil
     or Mournhold's Temple High Chapel. Needs the Temple High Chapel present and the ring's script running.
   - **Tribunal, the Dark Brotherhood:** assassins attack while the player rests, from the start of the expansion. Needs
     the script that runs on resting and the assassin's records.
   - **Bloodmoon, to Solstheim:** the shipmaster at Khuul takes the player to Fort Frostmoth and back; Khuul also gains a
     dialogue topic of its own among the topics. Needs the shipmaster and the boat placed at Khuul's pier, the topic
     present in the lists, the script running, Fort Frostmoth present, and the way back.
   - **Bloodmoon, The Patchwork Airship:** **Louis Beauchamp** stands outside the Mages Guild in Ald'ruhn and asks the
     player to find his airship, which lies at a crash site in central Solstheim, west of the Altar of Thrond. Needs him
     placed in Ald'ruhn, his quest in the journal, and the crash site present on Solstheim.
3. **Solstheim.** The next island of the one outdoor grid, built through the same conversion and reduction methods as
   Vvardenfell. Raven Rock's stages are measured one by one, the sea between the islands is generated, and its rooms are
   ordinary rooms.
4. **Mournhold.** The five districts become one exterior of their own, joined by their doors; the rooms are ordinary
   interiors. The trip there and back gets its own playtest.
5. **Scripts and dialogue.** Both expansions' scripts are compiled and attached, with the journal and the topics. The
   game's limit of 256 script instances (Raven Rock's frame alone has 353 scripted placements; up to 350 in one 3 by 3
   block) and the store of script variables are widened in source in v0.0.66-dev12, sized from the game's counts, to be
   confirmed in a session (`EXPANSION-SCRIPT-LIMITS-66`).
6. **The save.** The save holds the expansions' counts: about 13,800 placed actors and about 3,300 scripted references
   with variables.
7. **The Toolkit.** A Solstheim view and a Mournhold screen with the completion map and the heatmap.
8. **Playtests.** Every chain above in game, the Mournhold transfer, Raven Rock's stages and a walk across Solstheim.

The census also covers the items placed in the world: every placed item of the three game files is counted by cell and
checked against the build, including loose items in the wild.

## Known issues

The open entries are in the [bug register](BUGS.md):

- `BUILD-EXPANSION-INPUTS-UNCHECKED-66`: the expansion files were not required nor checked against known SHA-256
  values (fixed in v0.0.66-dev3).
- `INTERIOR-RECEPTION-AREA-FPS-67`: Mournhold's Royal Palace Reception Area, the arrival room of the trip, runs at
  about 3 frames a second on the Pi 4B (open).
- `EXPANSION-TABLES-BASE-ONLY-66`: some tables still read the base game only (open); `EXPANSION-BASE-ONLY-TABLES-66`
  (the focus table) and `EXPANSION-ARCHIVE-READERS-66` (the archives) are its fixed parts (fixed in v0.0.66-dev2).
- `WORLD-SURVEY-EXPANSION-ATLAS-66`: the world survey stopped on a terrain subdivision outside the island's atlas with
  both expansions selected (fixed in v0.0.66-dev2).

Other open entries are listed in the register and in the [v0.0.66-dev2 notes](releases/notes/RELEASE-v0.0.66-dev2.md).
