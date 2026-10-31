# Animation kit

_Last updated with AmiWind v0.0.57-dev4 (30 October 2026)._

<!-- contents start -->
## Contents

- [The build switch](#the-build-switch)
- [Skeletal actors: the layout from the table](#skeletal-actors-the-layout-from-the-table)
- [Console: dbg animkit](#console-dbg-animkit)
- [Morrowind's groups: wired and not wired yet](#morrowinds-groups-wired-and-not-wired-yet)
- [Every group hooked up](#every-group-hooked-up)
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
as a one-frame model.

### An NPC's own animation file

An NPC record can name an animation file of its own (its model field). The base game has one,
`anim_dancingGirl.nif`, named by the three dancers of Desele's House of Earthly Delights in Suran and by Yakov
of the Suran slave market. Its only group is `idle9`: the dance. As OpenMW does, its groups play over the common
and female ones. The builder appends the file's groups to `progs/humanoid.awsk` under `d:` (`d:idle9`, about
115 frames), built from your own game data like the rest of the table, and the NPC's model names the view
`progs/humanoid.awsk|d`, or `progs/humanoid.awsk|d|f` for a woman: her own file's groups first, then the female
ones, then the common ones. The original picks a standing NPC's idle by the eight idle chances of its wander
package. The dancers' `idle9` chance is 80 against 20 or less, so they loop the dance while they stand (the
entity's `aw_idle_base` and `aw_idle_count`). Yakov's is 5 against 40, so he stands as before.
`dbg animkit play idle9` (or `d:idle9` on any humanoid) plays the dance. The files the table appends are listed
in `tools/skeletal_actor.py` (`OWN_ANIMATIONS`). An NPC naming a file that is not listed plays the common table. The carried weapon and shield hang on the table's weapon and shield bones (the item tag
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

The table above is the kit's own (the engine groups the game logic drives). On a skeletal actor (the default) every
other group of the table is played as well, by the actor's state: see the next section. `dbg animkit list` prints
the kit's table; the engine table is `engine/aga/src/aw_animkit_rules.c`.

## Every group hooked up

From v0.0.54 every group of the humanoid tables is played by the game, not only by name from the console. The
drivers (combat, the companion, the residents' idle, the walk) still move an actor through the kit's groups; just
before the server sends the frames, a skeletal actor's frame is moved into the group the original game (as OpenMW
plays it) shows in the same state, and given back after the send, so no driver sees a changed frame. A one-shot or a
gait keeps the driver's progress through its group (its timing, the attack's hit, the feet's speed); a standing
group plays on its own clock. `dbg animkit pick off` is the previous method: the kit's groups only (not saved).

| State | Groups | Rule (OpenMW 0.51, read, not copied) |
| --- | --- | --- |
| Moving | `walk`/`run`/`sneak`/`swimwalk`/`swimrun` + `forward`/`back`/`left`/`right` by the motion against the facing; with a weapon drawn the stance's own set (`walkforward1h`, `runleft2c`, `sneakbackhh`, ...) | `mwmechanics/character.cpp` `refreshMovementAnims`; a missing stance group falls back to the long blade's (`1s`, `1b`, `bow`, `1t` to `1h`, `2b` to `2c`), a missing swim group to its land group, a missing run to walk |
| Turning on the spot | `turnleft`/`turnright` (+ stance), `swimturnleft`/`-right`, `spellturnleft`/`-right` | `refreshMovementAnims` (not while sneaking) |
| Standing | `idle`, `idlehh`, `idle1h`, `idle2c`, `idle2w`, `idlespell`, `idlecrossbow`; `idlesneak`, `idleswim`; the wander idles `idle2` to `idle9` by the package's chances; `idlestorm` on the arm facing an ash or blight storm (a layer over the rest) | `refreshIdleAnims`, `aiwander.cpp` `getRandomIdle`, `updateIdleStormState` |
| Hit | `hit1` to `hit5` at random, `knockdown`, `knockout` (held down while out), `swimknockdown`, `swimknockout`, `shield` (block) | `refreshHitRecoilAnims` |
| Death | `death1` to `death5` at random, `deathknockdown`, `deathknockout`, `swimdeath`, `swimdeathknockdown`, `swimdeathknockout` | `playRandomDeath` |
| Attack | the weapon's group (`handtohand`, `weapononehand`, `weapontwohand`, `weapontwowide`, `bowandarrow`, `crossbow`, `throwweapon`) from `chop`/`slash`/`thrust` (or `shoot`) `start` to its follow | `updateWeaponState`, `getWeaponAnimation` |
| Drawing, putting away | the same group's `equip start` to `equip stop` when a fight starts, `unequip` when it ends | `updateWeaponState` |
| Casting | `spellcast` from `self`/`touch`/`target start` to its `stop` (the beast file keeps these keys in its second `spellcast` place) | `updateWeaponState` |
| Others | `jump` + stance, `pickprobe`, the `inventory` poses, `torch` (the left arm while a light is carried) | `refreshJumpAnims`, `characterpreview.cpp` |

The stance is the actor's own weapon (its record's weapon type), drawn while it fights; the swing (chop, slash,
thrust) is the one combat chose. A woman's own groups and an NPC's own animation file (the Suran dancers) answer the
plain names first, as before.

Some groups wait for a caller from other work: the wander idles need the package chances from the ambient tables, a
cast needs an NPC that casts (the spell effects work), sneaking needs MWScript's `ForceSneak`, NPCs do not jump yet,
and `pickprobe` and the inventory poses are the player's. Their entry points are in the engine
(`engine/aga/src/aw_animpick.h`) and the console reaches them now:

| Command | What it does |
| --- | --- |
| `dbg animkit pick` | On or off, frames placed, and the group and rule of the NPC under the crosshair. |
| `dbg animkit pick on` / `off` | Every group by state, or the kit's groups only (not saved). |
| `dbg animkit pick cast self` / `touch` / `target` | The NPC under the crosshair casts. |
| `dbg animkit pick sneak on` / `off` | It sneaks (the sneak gaits and `idlesneak`). |
| `dbg animkit pick idle C2 C3 C4 C5 C6 C7 C8 C9` | Its wander idle chances (0 to 100 each). |
| (creatures) | A creature on its own table attacks with a random one of its own `attack1`..`attackN` (`swimattackN` in water), start to stop, as the original picks a creature's attack; hits and deaths take a random `hitN` / `deathN` of its table (v0.0.57). |
| `dbg animkit tables` | The animation tables' bytes: index blocks, frames held against frames on disk (v0.0.57). |
| `dbg animkit tables paged` / `whole` | Frames read when posed (the default) or the whole file in one block, for the next table loaded. |

The coverage: `python3 tools/anim_coverage.py <build>/.../progs/humanoid.awsk <build>/.../progs/humanoid_kna.awsk
--markdown coverage.md` lists every group of a build's tables: in which table, hooked by what, and the caller still
to come; a group nothing plays is reported as never played (`--check` fails on it). The gate test
(`tests/test_anim_coverage.py`) proves every group reachable through the rules.

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

- On a baked actor (`--npc-anim-type 1`) only the kit's groups play; every group by state needs the skeletal
  tables (the default).
- A group the state picks plays over the driver's timing: a variant longer or shorter than the kit's group plays
  faster or slower to fit it. OpenMW blends groups per body part (a weapon stance over the legs, the storm pose on the
  upper body); here one group plays on the whole body, the carried torch's left arm excepted.
- The near and far NPC models (`--npc-lod on`) are for idle-only residents; with the baked kit
  (`--npc-anim-type 1`) an actor has one model plus its mover, and a skeletal actor has none.
- A skeletal actor's head is reduced to the budget detail for now: the skeletal block is read only by the
  alias stream reader, which takes at most 2,000 vertices
  ([SKEL-VERTEX-LIMIT-52](BUGS.md)).
- The mimic speed mode differs from the original follower rule (above).
- `dbg animkit play` drives one NPC at a time and is not saved.
