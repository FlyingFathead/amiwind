# Waiting and resting: the original's rules

Status: study, 10 October 2026. Not implemented yet; planned for a later version (see [ROADMAP.md](ROADMAP.md)).
Today **T** only moves the clock forward ([DIALOGUE_AND_WAIT.md](DIALOGUE_AND_WAIT.md)).

Every rule below comes from the original's own data (the three master files: game settings, cell flags, region
records, scripts) or from OpenMW 0.51's source, which reproduces the original's engine. Nothing is invented. Where
the two disagree with other descriptions of the original, the open question is listed at the end.

## Rest or wait

| Rule | Value | Source |
| --- | --- | --- |
| T offers resting, unless the cell forbids sleeping or the player is a werewolf; then only waiting | cell flag "sleeping is illegal" | master files: cell flags; OpenMW `World::canRest` |
| Cells that forbid sleeping | 736 of 1,328 interiors (every Seyda Neen and Balmora interior), 67 of 1,559 exterior cells (town grids: Seyda Neen 2, Balmora 4, Vivec 17, ...) | master files, all three merged |
| Using a bed always offers resting | - | OpenMW `waitdialog.cpp` |
| Neither waiting nor resting with the feet in water, in the air or levitating (a bed lifts the air rule only) | - | OpenMW `World::canRest` |
| Neither with enemies near: an actor within 7,168 units that is fighting the player, or that is not a follower and passes the attack test | Fight + 20 - 0.005 x distance + 0.2 x (50 - disposition) >= 100 | OpenMW `getEnemiesNearby`, `isAggressive` |
| Hours | 1 to 24, or "until healed" | OpenMW wait dialogue |
| Owned bed, seen sleeping in it | a trespass crime (5 gold) | game settings `iCrimeTresspass`, `iDispTresspass`, `iFightTrespass` |
| Inn bed | rented for 10 gold; the bed is the player's until the day changes | game dialogue and scripts (21 rent globals) |

## What an hour restores

| Stat | Resting (sleeping) | Waiting | Source |
| --- | --- | --- | --- |
| Health | + 0.1 x Endurance | nothing | OpenMW `getRestorationPerHourOfSleep` (fixed factor) |
| Magicka | + `fRestMagicMult` (0.15) x Intelligence; none with the Atronach's Stunted Magicka | nothing | game setting; OpenMW `restoreDynamicStats` |
| Fatigue | full within one hour | full within one hour | OpenMW `restoreDynamicStats` with the game's fatigue settings |

In real time, fatigue returns at 2.5 + 0.02 x Endurance per second, a different formula from the per-hour one.
AmiWind's combat already uses the real-time one.

## What time does not heal, and what keeps running

- Diseases and blight stay until cured.
- Timed effects keep running: each hour counts as 120 seconds of effect time (3,600 / time scale 30), so a poison
  can kill a sleeping player. Magic items recharge the same way.

## Sleep interrupted

Only outside, in a region that has a sleep creature list. For a rest of *h* hours: a roll from 0 to *h* - 1 below
0.25 x *h* stops the rest after *h* - int(0.3 x *h*) hours, and one creature from the region's list appears 220
units ahead. Rests of 1 to 3 hours are never interrupted; longer ones roughly 25 to 40 % of the time. Source:
OpenMW `waitdialog.cpp`, game settings `fSleepRandMod` and `fSleepRestMod`, the regions' sleep lists.

## Level-up

Only when a sleep ends normally and the level progress has reached `iLevelupTotal` (10). Source: OpenMW
`onWaitingFinished`.

## Rules that live in the game's scripts

Vampires gaining no health from sleep, becoming a vampire, the main quest's dreams and attacks during sleep, the
Dark Brotherhood attacks and some expansion events are written in the game's own scripts, which check whether the
player is sleeping. They need a script runtime or a native port of each script.

## Plan for AmiWind (nothing kept in memory that is rarely needed)

- Where sleeping is allowed: the builder writes one bit per exterior cell into a small table indexed by the cell's
  coordinates; pressing T reads the one byte holding the current cell's bit from disk. An interior carries its flag
  in its own map, which is loaded anyway. A region's sleep list is read only when an interruption is rolled.
- The game settings and messages above are carried into the game's settings file by the builder, as for combat.
- The engine gets the rules as one file the host tests can run (like the combat rules), and the wait steps hour by
  hour.
- Known now: [WAIT-FEET-IN-WATER-36](bugs/WAIT-FEET-IN-WATER-36.md) (waiting is allowed with the feet in water).
- One "are we in a fight?" check for everything: the same test that switches on the battle music also refuses
  waiting and resting (in the original neither is possible during a fight). Today's wait has no such check; it is
  being added now, ahead of the rest of this work. The original's own rest test is wider (any actor that would
  attack, within 7,168 units) and comes with the full rules.

## Open questions (sources disagree)

1. Does an interrupted rest still level up? OpenMW: no; other descriptions of the original: yes.
2. Can sleep be interrupted in dungeons? OpenMW: never (only outside, by region lists, which matches the data);
   other descriptions: yes.
3. Can a werewolf wait? OpenMW: yes; other descriptions: no.
4. Do guards chasing the player (not yet fighting) stop resting? Other descriptions: yes; OpenMW: only actors in
   combat or about to attack.

To be settled by watching the original or by an owner decision.
