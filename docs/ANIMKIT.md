# Animation kit

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

In the engine the kit can also be switched at run time (`aw_animkit 0` or `dbg animkit off`): movers then
play their idle frames, as before. Both methods stay selectable.

## Console: dbg animkit

Open the console (F10) and type:

| Command | What it does |
| --- | --- |
| `dbg animkit` | Status: on or off, playback speed, a forced group. |
| `dbg animkit on` / `dbg animkit off` | Walk, run and swim by speed, or idle frames only. Kept in the configuration. |
| `dbg animkit list` | The groups of the NPC under the crosshair with their frame counts, then Morrowind's whole group table: which rows are wired to an engine group, and which are present in the data but not wired yet. Without a target it shows the table. |
| `dbg animkit play <group>` | Plays a group on the NPC under the crosshair until `dbg animkit stop`. Engine names (`idle`, `walk`, `run`, `swim`, `hit`, `knock`, `death`, `attack`, `block`) and their Morrowind rows (`runforward`, `death1` ...) both work; a row that is not wired yet says so. |
| `dbg animkit stop` | Ends the forced group. |
| `dbg animkit speed <x>` | Scales every kit playback rate (0.1 to 4; 1 = matched to the real speed). Not saved. |

Examples: `dbg animkit play run`, `dbg animkit play death1`, `dbg animkit speed 0.5`.

## Morrowind's groups: wired and not wired yet

Wired (Morrowind group -> engine group): `idle` -> idle, `walkforward` -> walk, `runforward` -> run,
`swimwalkforward` -> swim, `idleswim` -> swimidle, `hit1` -> hit, `knockdown` -> knock, `death1` -> death, `handtohand` -> attack,
`shield` -> block. The sidesteps `dodgel` / `dodger` are an AmiWind extension sampled from `walkleft` /
`walkright` (Morrowind has no dodge group).

Present in the data, not wired yet: the idle variants (`idle2` to `idle9`, `idlehh`, `idle1h`, `idle2c`,
`idle2w`, `idlespell`, `idlecrossbow`, `idlesneak`, `idlestorm`, `torch`), `hit2` to `hit5`,
the swimming hits, `death2` to `death5` and the knockdown, knockout and swimming deaths, `knockout`,
`jump`, walking and running backwards and sideways, turning, sneaking, swimming in other directions,
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

- Only the groups listed as wired play; the rest of the table is listed, not played.
- The near and far NPC models (`--npc-lod on`) are for idle-only residents; with the kit an actor has one
  model plus its mover.
- The mimic speed mode differs from the original follower rule (above).
- `dbg animkit play` drives one NPC at a time and is not saved.
