# AmiWind v0.0.47-dev3: the public builder builds CHIM by default, type 1 crossings, outdoor actors, indoor mushroom picking (in development)

Development snapshot, 21 October 2026, in development. Running on CHIM Engine v0.2.1. Previous development
snapshot: [v0.0.47-dev2](RELEASE-v0.0.47-dev2.md); previous release: [v0.0.46](RELEASE-v0.0.46.md).

## Fixed: the builder in this repository now builds the CHIM exteriors by default

Since v0.0.36, every CHIM build the project shipped (playtests and releases) was made with a CHIM cell list that was
not in this repository, and the builder's own `--chim-regions` option stayed off by default. A build from this
repository therefore made the old open-world region maps for every exterior cell instead of CHIM, so it could not
reproduce the builds the release notes described. A tester's default build stopped on exactly that path
([BUILD-LAVA-TERRAIN-BUDGET-38](bugs/BUILD-LAVA-TERRAIN-BUDGET-38.md)).

From this snapshot the cell list is part of the repository (`config/chim-cells.json`) and is the default for the
CHIM builder: a plain build puts every exterior cell of the game (1,404, plus five open-sea routing cells) on CHIM,
the set the project's own builds use. `--chim-regions none` keeps the old open-world maps for comparisons. A test
fails the gate if the default plan and the shipped list ever differ, and the release checks now refuse a release
built with any input from outside the repository
([BUILD-CHIM-CELLS-PRIVATE-LIST-47](bugs/BUILD-CHIM-CELLS-PRIVATE-LIST-47.md)).

## v0.0.47-dev2's switches are now the defaults

Type 1 crossings, the outdoor actor table, terrain generated from heights and shared files and skins are on in a
default build; each old method stays selectable ([EXPERIMENTAL_FLAGS](EXPERIMENTAL_FLAGS.md)).

- **Outdoor actors are on in the game.** v0.0.47-dev2 carried the outdoor actor table on its disk, but the game's
  setting for it was off and no shipped configuration turned it on, so a default v0.0.47-dev2 showed no creatures or
  people outside the towns. The builder now turns the table on in the game configuration whenever the image ships it
  ([CHIM-ACTOR-TABLE-OFF-IN-GAME-47](bugs/CHIM-ACTOR-TABLE-OFF-IN-GAME-47.md)).

Everything else is as in the [v0.0.47-dev2 notes](RELEASE-v0.0.47-dev2.md).

## Known in this build

- No playtest image of this snapshot yet: it is the source for the next one.
- Towns keep the old crossing: walking into or out of a town is still a level change
  ([CHIM-ACTORS-TOWN-RETURN-EMPTY-47](bugs/CHIM-ACTORS-TOWN-RETURN-EMPTY-47.md)).
- Only small mushrooms can be picked, indoors and out
  ([HARVEST-ORGANIC-PLANTS-47](bugs/HARVEST-ORGANIC-PLANTS-47.md),
  [INTERIOR-PLACED-ITEMS-47](bugs/INTERIOR-PLACED-ITEMS-47.md)).
- Not in this build: one stored model per mesh (world format 0.8)
  ([CHIM-TILT-VARIANTS-SPLIT-33](bugs/CHIM-TILT-VARIANTS-SPLIT-33.md)).
- The rest of [v0.0.47-dev2's known items](RELEASE-v0.0.47-dev2.md#known-in-this-build) still apply; everything else
  is in the [bug register](BUGS.md).
