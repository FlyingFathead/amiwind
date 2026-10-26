# Animation kit

_Last updated with AmiWind v0.0.52-dev (26 October 2026)._

<!-- contents start -->
## Contents

- [The build switch](#the-build-switch)
- [Skeletal actors: the layout from the table](#skeletal-actors-the-layout-from-the-table)
- [Console: dbg animkit](#console-dbg-animkit)
- [Morrowind's groups: wired and not wired yet](#morrowinds-groups-wired-and-not-wired-yet)
- [Walk or run: the rules and their sources](#walk-or-run-the-rules-and-their-sources)
- [MiniWind sandbox](#miniwind-sandbox)
- [Known limits](#known-limits)

<!-- contents end -->

The animation kit maps Morrowind's own animation groups (the text keys of the skeleton files, such as
`walkforward: loop start`) onto the engine's actor models. The builder samples the groups an actor needs
into its model and writes a layout beside it; the engine plays walk, run or swim by the actor's real speed,
at a playback rate matched to that speed, and plays hit, knockdown, death, attack and block when they
happen. How the frames are baked: [ANIMATION.md](ANIMATION.md).

## The build switch

| Switch | Default | Meaning |
| --- | --- | --- |
| `--anim-kit on` | on | Residents get the `react+full` kit: a standing model with idle, hit and death, and a full model (walk, run, swim, knockdown, attack) worn only while the actor moves. |
| `--anim-kit off` | | The previous method: 8 idle frames per resident (`--npc-anim idle`). |
| `--npc-anim PROFILE` | from `--anim-kit` | Picks a profile directly (`idle`, `react`, `move`, `full`, `react+full`) and wins over `--anim-kit`. |
| `--npc-anim-type 2` | 2 | Skeletal actors (from v0.0.52): every humanoid resident and actor-library model is one rest frame on the shared animation table of its skeleton, and its layout names the table's frames. No mover models, no baked frames. |
| `--npc-anim-type 1` | | The baked kit as before: each actor's groups baked into its own vertex frames, a standing model and a mover. Only for a build compiled with it on purpose (an A/B test build). |

In the engine the kit can also be switched at run time (`aw_animkit 0` or `dbg animkit off`): movers then
play their idle frames, as before. Both methods stay selectable.

## Skeletal actors: the layout from the table

With `--npc-anim-type 2` (the default) the kit's game logic is unchanged: the engine reads the same layout
beside each model (`NAME:BASE:COUNT:STEP[:X]`, events, sounds, voice lines) and plays it the same way. Only
the numbers come from somewhere else: a skeletal model's frames are the frames of its shared animation table
([MODULAR_NPCS.md](MODULAR_NPCS.md#getting-npc-movement-right)), so the builder looks each kit group's start
and stop keys up among the table's text keys (`tools/npc_anim.py` `table_groups`):

| Kit group | Table group and keys |
| --- | --- |
| `idle` | `idle`: start to stop |
| `walk`, `run` | `walkforward`, `runforward`: loop start to loop stop |
| `swim`, `swimidle` | `swimwalkforward` loop, `idleswim` |
| `hit`, `knock`, `death` | `hit1`, `knockdown`, `death1` |
| `attack` | `handtohand` (or the weapon stance's set, `weapontwowide` for spears): chop start to chop large follow stop |
| `block` | `shield`: block start to block stop (the enhanced combat's shield block) |
| `dodgel`, `dodger` | the `walkleft` / `walkright` loops (the enhanced combat's dodge; the table also names them `dodgel` and `dodger`) |

Loops and one-shot groups end before the stop key's frame (it is the start's pose again), held groups (death,
jump) end on it, as the baked kit samples them. Each group plays at its own frame time in the table (about 8
frames a second); the own speed of walk and run (so feet do not slide) and the attack's hit fraction are the
baked kit's, from the same skeleton; footsteps are the table's `soundgen` keys inside the group. A group the
table lacks stands on the idle's first frame, as OpenMW falls back to idle. Every actor plays every group of
the profile (`react+full`: idle, walk, run, swim, hit, knockdown, death, attack, block and both dodges), so the
region NPCs move and fight like the town NPCs.

The tables, each written once into the image: `progs/humanoid.awsk` (every humanoid, and a female human's own
groups under `f:`: her walk and two idles from `base_anim_female.nif`, which OpenMW stacks over `base_anim.nif`;
her model names the view `progs/humanoid.awsk|f`, one loaded table for both), `progs/humanoid_kna.awsk`
(Argonians and Khajiit, their own walk and
tail; a beast female plays it alone, as the baked kit does). An actor that starts dead keeps its one death pose
as a one-frame model. The carried weapon and shield hang on the table's weapon and shield bones (the item tag
`AWTS1` beside the model: the item models, the two bone indices and the actor's scale).

## Console: dbg animkit

Open the console (F10) and type:

| Command | What it does |
| --- | --- |
| `dbg animkit` | Status: on or off, playback speed, a forced group. |
| `dbg animkit on` / `dbg animkit off` | Walk, run and swim by speed, or idle frames only. Kept in the configuration. |
| `dbg animkit list` | The groups of the NPC under the crosshair with their frame counts, then Morrowind's whole group table: which rows are wired to an engine group, and which are present in the data but not wired yet. Without a target it shows the table. |
| `dbg animkit groups` | The groups of the skeletal NPC under the crosshair's shared table: number, name and table frames. |
| `dbg animkit play <group>` | Plays a group on the NPC under the crosshair until `dbg animkit stop`. A skeletal NPC plays any group of its table by its Morrowind name (`sneakforward`, `weapontwohand`, `spellcast`, `idle7` ...), from its first to its last table frame, looped. Engine names (`idle`, `walk`, `run`, `swim`, `hit`, `knock`, `death`, `attack`, `block`) and their wired rows (`runforward`, `death1` ...) work on every NPC; on a baked NPC a row that is not wired yet says so. |
| `dbg animkit stage [1..8]` | The animation stage: lines up to 8 skeletal NPCs of the map (default 8) in a row in front of you, nearest first: a guard with his carried torch, an Argonian or Khajiit (the beast table), a woman (the female table), an armed NPC (weapon and shield shown), a man of the common table, then the nearest others. Each stands still with its items shown until `dbg animkit stop` puts it back. |
| `dbg animkit cycle` / `cycle all` | The full animation cycle: every group of the table one after another, each once, its name, frame count and time into the cycle on the console (`124/141 weapononehand (41 frames) at 300.2 s`). `cycle` plays it on the NPC under the crosshair; `cycle all` on the whole stage, every NPC playing the same group by name from its own table (a group its table lacks stands on its idle). Ends with the time it took. |
| `dbg animkit stop` | Ends every forced group and the stage. |
| `dbg animkit speed <x>` | Scales every kit playback rate (0.1 to 4; 1 = matched to the real speed). Not saved. |

Examples: `dbg animkit play run`, `dbg animkit play death1`, `dbg animkit play crossbow`, `dbg animkit speed 0.5`,
`dbg guardtorch on`, `dbg animkit stage`, `dbg animkit cycle all`.

### The animation stage (MiniWind)

```sh
python3 tools/build.py --miniwind-anim-stage --data-files "<Data Files>"
```

builds Balmora's exterior with skeletal NPCs (the default `--npc-anim-type 2`) and boots into the stage: the
guard torches forced on (`dbg guardtorch on`), the cast lined up (`dbg animkit stage`) and the full cycle running
(`dbg animkit cycle all`). Nothing is baked: every frame shown is posed from the shared tables at run time. Built
with `--npc-anim-type 1` the same stage has no skeletal NPCs and says so (the baked kit's A/B is
`--miniwind-animkit`).

## Morrowind's groups: wired and not wired yet

A player-body candidate adds `jump` takeoff/held-air and landing sections, plus
bare-hand `idlehh`, `walkforwardhh`, `runforwardhh` and `jumphh`. It
is separate from the NPC profiles below: compilation, body bakes, model-budget
gates and native comparison remain pending. Bare-hand equip/lower now has source
wiring through offline movement/arm grids and the authoritative QuakeC clock;
its appearance and cost remain unverified. Punch overlays, other weapon variants
and torch-holding poses remain open. See [player-body coverage](THIRD_PERSON.md#the-players-body)
and [PLAYER-JUMP-THIRDPERSON-38](bugs/PLAYER-JUMP-THIRDPERSON-38.md).

Wired (Morrowind group -> engine group): `idle` -> idle, `walkforward` -> walk, `runforward` -> run,
`swimwalkforward` -> swim, `idleswim` -> swimidle, `hit1` -> hit, `knockdown` -> knock, `death1` -> death, `handtohand` -> attack,
`shield` -> block. The sidesteps `dodgel` / `dodger` are an AmiWind extension sampled from `walkleft` /
`walkright` (Morrowind has no dodge group).

Present in the data, not wired yet: the idle variants (`idle2` to `idle9`, `idle1h`, `idle2c`,
`idle2w`, `idlespell`, `idlecrossbow`, `idlesneak`, `idlestorm`, `torch`), `hit2` to `hit5`,
the swimming hits, `death2` to `death5` and the knockdown, knockout and swimming deaths, `knockout`,
walking and running backwards and sideways, turning, sneaking, swimming in other directions,
the weapon attack sets (`weapononehand`, `weapontwohand`, `weapontwowide`, `bowandarrow`, `crossbow`,
`throwweapon`), `spellcast` and the inventory poses. `dbg animkit list` prints the full table; the
engine table is `engine/aga/src/aw_animkit_rules.c`.

## Walk or run: the rules and their sources

The rules come from the OpenMW 0.51 source (the behaviour of the original game as OpenMW reproduces it)
and the game's own settings (GMSTs). None is invented.

| Rule | Source |
| --- | --- |
| A follower runs when it is more than 450 units from its leader and walks again under 325 (in between it keeps what it was doing); it does not look at whether the leader runs. | `apps/openmw/mwmechanics/aifollow.cpp`, `AiFollow::execute` |
| An escort always walks. | `aiescort.cpp` |
| A hostile in combat always runs (unless sneaking). | `aicombat.cpp`, `AiCombat::execute` |
| Walk speed = fMinWalkSpeed + Speed/100 x (fMaxWalkSpeed - fMinWalkSpeed), less fEncumberedMoveEffect x encumbrance; run speed = walk x (fBaseRunMultiplier + Athletics/100 x fAthleticsRunBonus). Defaults 100, 200, 0.3, 1.75, 1.0. | `apps/openmw/mwclass/npc.cpp` `getWalkSpeed`, `getRunSpeed` |
| Creatures move at their walk speed even when running; only the animation differs. | `apps/openmw/mwclass/creature.cpp` |
| Playback rate = actual speed / the animation's own speed (its root bone's travel between the group's text keys), so feet do not slide. | `mwmechanics/character.cpp`, `mwrender/animation.cpp` |
| A missing run group falls back to walk, played at the run speed. | `mwmechanics/character.cpp` |

In AmiWind: the engine picks walk or run by the speed an actor really moves at, nearer to the walk or the
run group's own speed, and scales the playback rate by speed / own speed (0.25 to 4). Fighters in combat
play their run group (walk when a model has no run group). The companion's default **mimic speed** mode
(`dbg companion mimic speed on`) copies the player's speed, so it runs when the player runs: this is an
AmiWind extension, not the original rule (the original follower runs only when it falls behind). With
mimic speed off it follows the distance rule.

## MiniWind sandbox

```sh
python3 tools/build.py --miniwind-animkit --data-files "<Data Files>"
```

builds a quick test of Balmora's exterior with the kit on and starts there. The preset sets the scene up on
arrival (its `boot_commands`: `dbg companion test` spawns a companion, `dbg combat on` makes the NPCs
fight). Run and walk to compare the gaits; `dbg combat loadout NAME` gives the test fighters their
equipment.

The kit can also be compiled out: build the engine with `-DAW_ANIMKIT=0` (movers then play idle and
`dbg animkit` says the kit is not in the build). The default is 1.

## Known limits

- Only the groups listed as wired are picked by the game logic; the rest of the table plays only when asked for
  by name (`dbg animkit play`, `cycle`) on a skeletal NPC.
- The near and far NPC models (`--npc-lod on`) are for idle-only residents; with the baked kit
  (`--npc-anim-type 1`) an actor has one model plus its mover, and a skeletal actor has none.
- A skeletal actor's head is reduced to the budget detail for now: the skeletal block is read only by the
  alias stream reader, which takes at most 2,000 vertices
  ([SKEL-VERTEX-LIMIT-52](BUGS.md)).
- The mimic speed mode differs from the original follower rule (above).
- `dbg animkit play` drives one NPC at a time and is not saved.
