# Movement speed study

14 October 2026. Source analysis for v0.0.39 and the v0.0.40-dev1 candidate. Current status: [PLAYER-MOVEMENT-STATS-PARITY-39](bugs/PLAYER-MOVEMENT-STATS-PARITY-39.md) remains open. No movement setting or implementation is changed by this study.

## What the current defaults request

AmiWind uses AmiQuake's client movement command, server friction, acceleration and collision. The generated defaults set forward/back/side movement to 120 and the held Shift multiplier to 1.8. The server caps the **requested vector length** at 320; it does not normalize ordinary diagonal input to the straight-line speed. This is a wish-speed limit, not a guarantee that every physical velocity from jumping, knockback or another force stays below 320. [Default generation](../tools/prepare_quake.py), [client input](../engine/aga/src/cl_input.c), [server movement](../engine/aga/src/sv_user.c).

The following are source-derived targets for sustained, unobstructed input, in AmiWind world units per engine second. Water values describe level horizontal input while the water movement path applies; that path multiplies wish speed by 0.7. Acceleration, friction, collisions, water transitions and scripted locks affect actual displacement.

| Input | Ground target | Level-water target |
| --- | ---: | ---: |
| Forward or sideways, walk | 120.00 | 84.00 |
| Forward or sideways, run | 216.00 | 151.20 |
| Forward + sideways, walk | 169.71 | 118.79 |
| Forward + sideways, run | 305.47 | 213.83 |

Diagonal input therefore gains about 41.4% under these defaults. Water pitch, the separate vertical movement command and jump/surface handling require their own controls; they are excluded from the level-water numbers. The reported sinking, water-walking and swimming-pose failures remain separately open under [WATER-GAMEPLAY-PARITY-38](bugs/WATER-GAMEPLAY-PARITY-38.md).

The converted world scale is 0.25, so 120 and 216 correspond to 480 and 864 original world units/s. `quake.rc` executes defaults, gameplay defaults, saved configuration, key maps and autoexec in that order. Saved or custom settings can therefore change the effective inputs. The running owner's cvars were not read for this study. [Startup order](../tools/build_aga.py).

## Original-data and OpenMW reference

The original base-master settings give minimum/maximum walk values 100/200, encumbrance movement factor 0.3, run base 1.75, Athletics run bonus 1, swim base 0.5 and swim Athletics factor 0.1. OpenMW's NPC movement implementation reads the effective, modified Speed and Athletics values. For ordinary gameplay with godmode off and positive carrying capacity, let S be Speed, A be Athletics, E be effective carried weight divided by capacity, and Q be Swift Swim magnitude:

```text
capacity = 5 * modified Strength
weight = max(0, carried weight - Feather + Burden)
walk = max(0, (100 + S) * (1 - 0.3 * E))
run = walk * (1.75 + A / 100)
swim_walk = walk * (0.5 + 0.001 * A) * (1 + Q / 100)
swim_run = run * (0.5 + 0.001 * A) * (1 + Q / 100)
```

Above capacity, movement is refused. Sneaking has its own multiplier; levitation follows a separate formula. These are compatibility-source calculations, not measured vanilla executable speeds. Zero-capacity handling has explicit OpenMW deviations and is excluded from these examples. [OpenMW NPC formulas](https://github.com/OpenMW/openmw/blob/openmw-0.48.0/apps/openmw/mwclass/npc.cpp), [reference swim calculation](https://github.com/OpenMW/openmw/blob/a882697616a186ef394ae049df79f96de793d053/apps/openmw/mwclass/actor.hpp), [effective carried weight](https://github.com/OpenMW/openmw/blob/a882697616a186ef394ae049df79f96de793d053/apps/openmw/mwclass/actor.cpp).

### Calculated comparison before actor and race scaling

All speeds below have already been multiplied by 0.25 to use AmiWind units. Actor scale and race-weight factor are both 1, Swift Swim is 0, and stats are modified values. These rows are reference arithmetic, not universal traversal predictions.

| Speed | Athletics | Weight/capacity | Walk | Run | Swim walk | Swim run |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 20 | 5 | 0 | 30.00 | 54.00 | 15.15 | 27.27 |
| 50 | 50 | 0 | 37.50 | 84.38 | 20.63 | 46.41 |
| 100 | 100 | 0 | 50.00 | 137.50 | 30.00 | 82.50 |
| 50 | 50 | 0.5 | 31.87 | 71.72 | 17.53 | 39.45 |
| 50 | 50 | 1 | 26.25 | 59.06 | 14.44 | 32.48 |
| 50 | 50 | 1.01 | 0.00 | 0.00 | 0.00 | 0.00 |

At 50/50 and no load, current straight-line targets are 3.20 times the unit-race reference walk and 2.56 times its run. At 100/100 they are 2.40 and 1.57 times. Increased load widens the gap. This supports investigating the owner's fast-traversal report, but does not measure that particular running session.

### Race, direction and effects matter

The inspected OpenMW reference also scales final horizontal motion by actor reference scale and, with its default `normalise race speed = false`, the race's sex-specific weight value. The original Nord male value is 1.25; female is 1.0. For an unscaled Nord male at 50/50, unloaded, the reference walk/run become 46.88/105.47, making the current default targets 2.56/2.05 times those values. Race height is not a substitute for this weight factor. Match race, sex, reference scale and that setting before comparing timings.

OpenMW normalizes movement direction and applies a 0.75 factor to movement classified as strafing; its camera/turn-to-movement and smoothing settings affect that classification and the transient. Holding two direction keys should not be compared as if it were the same test as forward input. [Reference direction, race scaling and final motion](https://github.com/OpenMW/openmw/blob/a882697616a186ef394ae049df79f96de793d053/apps/openmw/mwmechanics/character.cpp).

Fortify/Drain/Damage changes to Speed, Athletics or Strength affect the terms they modify. Feather and Burden change load; Swift Swim changes swimming only. For example, Swift Swim 100 doubles reference swim speed. Do not clamp these examples to 100 as if modified attributes could never exceed the unfortified range. Paralysis, knockdown, death, water walking and levitation require state-specific checks. AmiWind's audited normal movement paths do not read Speed, Athletics, carried weight or these movement effects. An inventory weight display alone does not establish movement encumbrance support.

## Fatigue is a separate comparison

The original-data movement debits per second of active full input are run `5 + 2*E`, swim-walk 2.5 and swim-run 7; ordinary walking has no running debit. The reference applies input/time factors and skips these debits in godmode; its player godmode also ignores Burden, without automatically granting maximum Speed or Athletics. Passive fatigue recovery is separately `2.5 + 0.02*modified Endurance` per second below the allowed maximum. Thus at Endurance 50 an unloaded run has gross debit 5 and recovery 3.5, for a nominal net loss of 1.5; quoting only one term would misstate the result. Fatigue is not a direct multiplier in the displayed walk/run formulas. Negative fatigue, incapacitation and boundary clamping must be checked separately. [Reference movement debit](https://github.com/OpenMW/openmw/blob/a882697616a186ef394ae049df79f96de793d053/apps/openmw/mwmechanics/character.cpp), [passive recovery](https://github.com/OpenMW/openmw/blob/a882697616a186ef394ae049df79f96de793d053/apps/openmw/mwmechanics/actors.cpp).

AmiWind already has recovery and combat fatigue costs, but the audited code does not add a moving-run/swim debit. [Combat recovery](../engine/aga/src/aw_combat_rules.c), [runtime update](../engine/aga/src/aw_combat.c). The proposed maximum-stat/debug-speed extension remains a proposal; it is not implemented by this study.

## Next acceptance step

First record effective movement cvars, character stats, effects, load, race/sex, camera, water state and exact build. In matched OpenMW and AmiWind scenes, use an unobstructed segment with no cell crossing: measure a five-second steady-state forward walk, run and level swim after a separate acceleration interval. Record start/end positions, velocity and simulated elapsed time, and also wall-clock duration. Use normal emulator pacing with warp off and record frame timing; the inherited engine caps an ordinary frame's simulation step at 0.1 seconds, so wall time alone is insufficient. [Time handling](../engine/aga/src/host.c).

Repeat sideways/diagonal controls, loaded/over-capacity cases and low/middle/high stats before selecting any faithful movement formula. Then cover both views, readied fists/weapon/torch, water transitions and save/load. Keep convenient fast debug movement separately selectable as requested. A source formula, arithmetic check or host test cannot close the native parity or owner acceptance gate.
