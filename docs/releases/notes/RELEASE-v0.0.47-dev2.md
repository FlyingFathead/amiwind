# AmiWind v0.0.47-dev2: type 1 crossings, outdoor actors, indoor mushroom picking (in development)

Development snapshot, 21 October 2026, in development. Running on CHIM Engine v0.2.1. Previous development
snapshot: [v0.0.47-dev1](RELEASE-v0.0.47-dev1.md); previous release: [v0.0.46](RELEASE-v0.0.46.md).

The same source as v0.0.47-dev1, built with the experimental switches on, so they can be played and measured
together for the first time. Compare it with v0.0.47-dev1, which has them off. Each switch is described in
[EXPERIMENTAL_FLAGS](../../EXPERIMENTAL_FLAGS.md).

## New since v0.0.47-dev1

- **Mushrooms indoors can be picked.** A mushroom in a converted interior disappears when picked and stays gone
  after you leave the room and after a save and load, as outdoors (305 in 8 rooms; owned ones stay as they are)
  ([HARVEST-INTERIOR-PICK-47](../../bugs/HARVEST-INTERIOR-PICK-47.md)).
- **The outdoor actors' changes are saved.** Kills, moves, health and the levelled picks of the open world's actors
  survive a save and a load.
- **Builder.** Adding a build option no longer makes the CHIM stages run again
  ([BUILD-OPTION-RECORD-KEYS-STAGES-47](../../bugs/BUILD-OPTION-RECORD-KEYS-STAGES-47.md)).

## What is on in this build

- **Type 1 crossings** (`--chim-crossing 1`): the world around you streams in as one window; crossing a frame border
  is no longer a level change, and followers, pursuers and the dead keep their state.
  `chim crossing 0` in the console gives the old crossing for a comparison
  ([CHIM-CROSSING-SLUGGISH-43](../../bugs/CHIM-CROSSING-SLUGGISH-43.md)).
- **Creatures and people outside the towns** (`--chim-actor-table on`): every exterior NPC and creature reference
  of the game in one table, levelled lists rolled when a cell joins, creature models with their walk, attack and
  death frames, and standing models for the NPCs outside the towns
  ([CHIM-EXTERIOR-ACTORS-MISSING-46](../../bugs/CHIM-EXTERIOR-ACTORS-MISSING-46.md)).
- **Terrain generated from heights** (`--chim-terrain-pack generate`): the engine rebuilds most terrain records from
  the game's own heights instead of reading them.
- **Shared files and skins** (`--file-aliases on`, `--shared-skins on`): byte-identical files and repeated actor
  skins are stored once.

## Known in this build

- Not played before this build: doors, plant picks and interior crossings with type 1 crossings.
- Towns keep the old crossing: walking into or out of a town is still a level change, so the town and its people
  load whole ([CHIM-ACTORS-TOWN-RETURN-EMPTY-47](../../bugs/CHIM-ACTORS-TOWN-RETURN-EMPTY-47.md): the streamed window
  could drop a town and leave it empty; fixed this way for now).
- Only small mushrooms can be picked, indoors and out; other plants and placed items are not pickable yet
  ([HARVEST-ORGANIC-PLANTS-47](../../bugs/HARVEST-ORGANIC-PLANTS-47.md),
  [INTERIOR-PLACED-ITEMS-47](../../bugs/INTERIOR-PLACED-ITEMS-47.md)).
- The NPCs outside the towns stand only: no walking, fighting or dialogue yet.
- No real-hardware timing for any of the above.
- Not in this build: one stored model per mesh (world format 0.8). With it, four frames around the large Dwemer
  and Daedric ruins did not fit the engine's memory zone (over by up to 85 KB), because each model kept both its new
  collision table and its old stored hull. It returns once the old hull is left out where the table covers the model
  ([CHIM-TILT-VARIANTS-SPLIT-33](../../bugs/CHIM-TILT-VARIANTS-SPLIT-33.md)).

The rest is as in the [v0.0.47-dev1 notes](RELEASE-v0.0.47-dev1.md#known-in-this-build); everything else is in the
[bug register](../../BUGS.md).
