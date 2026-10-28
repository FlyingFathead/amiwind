# AmiWind v0.0.37 - Proofreading the Cantons

**AmiWind v0.0.37, running on CHIM Engine v0.2.0.** A small fix release for v0.0.36: the game is the same,
the documentation now matches it.

## Fixed since v0.0.36

- Release notes: shared terrain stored once is described as on by default, as the builder builds it
  (`--chim-terrain-hull compiled --chim-terrain-refs on`).
- Release notes: CHIM cells in the open world are off in a plain build and on in the release; the release recipe
  `config/recipes/release-coast2.json` builds the whole coast (`coast2`). Use it to reproduce the release.
- Release notes: the Vivec section no longer calls the Temple, Ebonheart and room stairs blocked; they were fixed
  in v0.0.36, as its fixed list says.
- Release notes: the death scene and **Retry fight** are in v0.0.36; the old "no way out after death" entry now
  says it is repaired and waits only for an in-game check.
- README: the top of the page describes the released version instead of a version in development.
- Media assets: the logo and the wordmark images are fixed (the pictures are unchanged).
- New page: [running AmiWind on real Amiga hardware](../../REAL_HARDWARE.md): what the game needs, the 68060 FPU library,
  `awbench` first, and the memory settings that already exist for machines with lots of Fast RAM (`-chimcache`,
  `-heapmb`, prefetch and lookahead), linked from the FPU, benchmark, engine and memory pages.
- Release notes: the default world format sentence now says that only a build with `--chim-terrain-refs off`
  keeps world format 0.5; the default is 0.7.
- Release notes: three bugs that v0.0.36 fixed were also still listed as known; they are now only in the fixed list.
- CHIM file format page: CHIM 0.2.0 shipped with v0.0.36, and terrain references (world format 0.7) are the default.
- The public progress reference (`docs/chim/cell-progress-reference.json`) and the cell tracker page are generated
  again from the same tracker data (1,240 of 1,292 cells done), and the README says that "done" means converted
  and audited, not yet in the game.
- Reproducing the release: the release recipe reads the CHIMport progress file of the run that closed the coast
  ring; point it at your own with `--recipe-input chim-regions-status=PATH` (see the recipe's `how`).

## Known in this build

Next, v0.0.38 moves every finished (green) cell on the CHIM progress map onto CHIM ([roadmap](../../ROADMAP.md)).

- [CHIM-HANDOFF-POPIN-36](../../bugs/CHIM-HANDOFF-POPIN-36.md): buildings in a CHIM area appear when the player crosses into it; seen from the legacy land the area shows its ground and rocks.

- [CHIM-NATIVE-HARVEST-MISSING-36](../../bugs/CHIM-NATIVE-HARVEST-MISSING-36.md): harvestable plants in CHIM areas beyond Seyda Neen and Balmora have no harvest catalogue yet.

- [CHIMPORT-RETRY-LAVA-STALE-SOURCE-36](../../bugs/CHIMPORT-RETRY-LAVA-STALE-SOURCE-36.md): 21 inland lava cells no longer convert (their source stages are older than the lava work); first item of v0.0.38.

- [COLLISION-ROUTE-NO-SPLIT-36](../../bugs/COLLISION-ROUTE-NO-SPLIT-36.md): some thin underwater plants (kelp, kreshweed) keep a collision chain that cannot be split; the kelp of cell -9,-4 is kept that way by owner decision.

- [ANIMKIT-COVERAGE-35](../../bugs/ANIMKIT-COVERAGE-35.md): many NPCs that move or fight have no walk, run or attack animation (carried over from v0.0.35).

- [NPC-WANDER-NOT-EXECUTED-35](../../bugs/NPC-WANDER-NOT-EXECUTED-35.md): residents stand still instead of following their original wander behaviour.

- [PLAYER-DEATH-LIMBO-35](../../bugs/PLAYER-DEATH-LIMBO-35.md): repaired in this release (the death scene and **Retry fight** above);
  it stays listed until it is checked in game.

- [COMBAT-MUSIC-AIR-SWING-35](../../bugs/COMBAT-MUSIC-AIR-SWING-35.md): swinging at the air can start the combat music.

- [BUILD-REUSE-PLAN-ENV-36](../../bugs/BUILD-REUSE-PLAN-ENV-36.md): the standalone reuse plan can report environment changes the build does not have; the build's own preflight is correct.

The open sea beyond the coast rings is not placed in the game yet: CHIMport has converted it (one shared ocean chunk), but the engine does not read it in this build; the water past the coast rings comes from the coastal maps, as before.

See the [bug register](../../BUGS.md).
