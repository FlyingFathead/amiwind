# AmiWind v0.0.47: CHIM: The More, The Merrier

Released 21 October 2026. Running on CHIM Engine v0.2.1. Previous release: [v0.0.46](RELEASE-v0.0.46.md).

More of the world is on CHIM and more of it is alive. The builder in this repository now builds every exterior cell
on CHIM by default, so a build from the repository makes the same world as the project's own builds. Crossing a
frame border outdoors is no longer a level change, creatures and people appear outside the towns, and mushrooms
can be picked indoors. Under the hood the terrain is generated from the game's heights, repeated files and skins are
stored once, and the builder rebuilds less and uses more cores.

## What changed since v0.0.46

### The builder in this repository builds the CHIM exteriors

Since v0.0.36, every CHIM build the project shipped (playtests and releases) was made with a CHIM cell list that was
not in this repository, and the builder's own `--chim-regions` option stayed off by default. A build from this
repository therefore made the old open-world region maps for every exterior cell instead of CHIM, so it could not
reproduce the builds the release notes described. A tester's default build stopped on exactly that path
([BUILD-LAVA-TERRAIN-BUDGET-38](bugs/BUILD-LAVA-TERRAIN-BUDGET-38.md)).

The cell list is now part of the repository (`config/chim-cells.json`) and is the default for the CHIM builder: a
plain build puts every exterior cell of the game (1,404, plus five open-sea routing cells) on CHIM, the set the
project's own builds use. `--chim-regions none` keeps the old open-world maps for comparisons. A test fails the gate
if the default plan and the shipped list ever differ, and the release checks refuse a release built with any input
from outside the repository
([BUILD-CHIM-CELLS-PRIVATE-LIST-47](bugs/BUILD-CHIM-CELLS-PRIVATE-LIST-47.md)). The seven world-scenery regions that
a public default build found over the 4 MiB limit are split, and a recorded scan of a public default build (2,417
regions) finds none over a limit.

### The world

- **Type 1 crossings.** The world around you streams in as one window; crossing a frame border is no longer a level
  change, and followers, pursuers and the dead keep their state. `chim crossing 0` in the console gives the old
  crossing for a comparison ([CHIM-CROSSING-SLUGGISH-43](bugs/CHIM-CROSSING-SLUGGISH-43.md)). Walking into or out of
  a town is still a level change.
- **Creatures and people outside the towns.** Every exterior NPC and creature reference of the game is in one table,
  levelled lists are rolled when a cell joins, creatures have their walk, attack and death frames, and the NPCs
  outside the towns stand in place. The game's setting for the table is now turned on whenever the image ships it;
  before, the table was on the disk and nothing switched it on
  ([CHIM-EXTERIOR-ACTORS-MISSING-46](bugs/CHIM-EXTERIOR-ACTORS-MISSING-46.md),
  [CHIM-ACTOR-TABLE-OFF-IN-GAME-47](bugs/CHIM-ACTOR-TABLE-OFF-IN-GAME-47.md)). Kills, moves, health and the levelled
  picks of these actors survive a save and a load.
- **Mushrooms indoors can be picked.** A mushroom in a converted interior disappears when picked and stays gone
  after you leave the room and after a save and load, as outdoors (305 in 8 rooms; owned ones stay as they are)
  ([HARVEST-INTERIOR-PICK-47](bugs/HARVEST-INTERIOR-PICK-47.md)).
- **The Ghostfence shimmers.** Shapes whose texture scrolls in the original (the Ghostfence curtain, the Vivec
  waterfalls, the ash mire) ripple by default; `dbg ghostfence off` draws them still
  ([GHOSTFENCE-NO-ANIMATION-46](bugs/GHOSTFENCE-NO-ANIMATION-46.md)).
- **Pursuers and spawned actors.** An actor's step follows a walkable slope, and an actor spawned before the streamed
  ground was there no longer floats
  ([COMBAT-PURSUIT-SLOPE-STALL-46](bugs/COMBAT-PURSUIT-SLOPE-STALL-46.md),
  [COMBAT-CHASE-CHIM-STUCK-46](bugs/COMBAT-CHASE-CHIM-STUCK-46.md)).
- **Weather changes gradually** between regions ([SKY-REDMOUNTAIN-BLUE-44](bugs/SKY-REDMOUNTAIN-BLUE-44.md)).
- **Workbench icon.** The boot volume has an icon labelled with the version; a double-click starts the game.

### The image

- **Terrain generated from heights.** The engine rebuilds most terrain records from the game's own heights instead
  of reading them from disk.
- **Shared files and skins.** Byte-identical files and repeated actor skins are stored once.
- **A lighter image.** The 64 MB media catalogue, a build report nothing in the game reads, is no longer on the boot
  disk ([IMAGE-MEDIA-CATALOGUE-ON-DISK-46](bugs/IMAGE-MEDIA-CATALOGUE-ON-DISK-46.md)).
- Each old method stays selectable ([EXPERIMENTAL_FLAGS](EXPERIMENTAL_FLAGS.md)). Emulator presets start with 128 MB
  of Fast RAM; 16 MB, the smallest machine the game runs on, stays a choice.

### The builder

- **`--clean` and `--public-defaults`.** A first-time or release from-scratch build can ask for a clean start, and
  `--public-defaults` builds with only the repository's own defaults and refuses the old methods.
- **Faster and leaner.** No stair walk by default; rebuilds reuse more (code keys of the functions a unit runs, and
  a unit whose output is unchanged does not rebuild what depends on it); adding a build option no longer makes the
  CHIM stages run again
  ([BUILD-OPTION-RECORD-KEYS-STAGES-47](bugs/BUILD-OPTION-RECORD-KEYS-STAGES-47.md)); the player body bake, the
  source manifest and the frame lookups no longer repeat work.
- **Full width while memory allows.** The builder keeps `--jobs` at full width below 96 % memory: the memory guard
  no longer cuts workers it cannot free. A from-scratch build's CHIM stage had run on 1 of 24 cores for an hour
  ([BUILD-SCHEDULER-MEMORY-STARVED-42](bugs/BUILD-SCHEDULER-MEMORY-STARVED-42.md)).
- **Faster flat planes.** Floors and walls that face straight along an axis take Quake's fast paths again
  ([CHIM-PLANE-TYPE-ALL-SLANTED-46](bugs/CHIM-PLANE-TYPE-ALL-SLANTED-46.md)).
- **Stricter engine warnings** ([ENGINE-STRICT-WARNINGS-36](bugs/ENGINE-STRICT-WARNINGS-36.md)).

### Docs

- The architecture page and the README front page are current, and the roadmap and the bug register were audited.

## Known in this build

- [CHIM-ACTORS-TOWN-RETURN-EMPTY-47](bugs/CHIM-ACTORS-TOWN-RETURN-EMPTY-47.md): towns keep the old crossing, so
  walking into or out of a town is still a level change.
- [HARVEST-ORGANIC-PLANTS-47](bugs/HARVEST-ORGANIC-PLANTS-47.md) and
  [INTERIOR-PLACED-ITEMS-47](bugs/INTERIOR-PLACED-ITEMS-47.md): only small mushrooms can be picked, indoors and out.
- The NPCs outside the towns stand only: no walking, fighting or dialogue yet.
- [CHIM-TILT-VARIANTS-SPLIT-33](bugs/CHIM-TILT-VARIANTS-SPLIT-33.md): one stored model per mesh (world format 0.8) is
  not in this release.
- [CHIM-CROSSING-SLUGGISH-43](bugs/CHIM-CROSSING-SLUGGISH-43.md): there is no real-hardware timing for the streamed
  crossing yet.
- [CHIM-HULL-SURFACE-HEAP-46](bugs/CHIM-HULL-SURFACE-HEAP-46.md): a few frames have little memory to spare.
- [CHIM-ROCKS-OPEN-SHELLS-43](bugs/CHIM-ROCKS-OPEN-SHELLS-43.md): some rocks still show open faces in game.
- [HORIZON-HOLES-31](bugs/HORIZON-HOLES-31.md): the sky can show through distant geometry.
- [AW-20260928-10](bugs/AW-20260928-10.md): interior doors do not open or close.
- [BUILD-STAIR-WALK-BRUTE-FORCE-46](bugs/BUILD-STAIR-WALK-BRUTE-FORCE-46.md): the optional full stair walk is still
  slow.

The rest is as in the [v0.0.46 notes](RELEASE-v0.0.46.md#known-in-this-build); everything else is in the
[bug register](BUGS.md), and what comes next is in the [roadmap](ROADMAP.md).
