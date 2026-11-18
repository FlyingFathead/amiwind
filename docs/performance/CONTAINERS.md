# Containers: what opens

_Last updated with AmiWind v0.0.67-dev1 (17 November 2026)._

Every placed container of the game (baskets, crates, barrels, chests, urns, sacks, closets, desks) of Morrowind,
Tribunal and Bloodmoon, counted against what a build makes openable. The builder counts it after every full build
(`container-census.json` in the run folder); this page and [CONTAINERS.json](CONTAINERS.json) keep the measurements,
newest last, and a gate test reads the newest: a container that stops opening, or a new reason for one not to, fails
the gate.

## The columns

For every container that opens in the original (a container that is not a plant; plants are harvested), five answers
read from the build's own files, by the rules the engine uses. The 46 containers of the Imperial Prison Ship never open
in the original: nothing is taken or opened before the release papers allow the inventory, and the ship is left behind
before them; they are counted apart ("closed in the original"). The 12 of the Census and Excise Office open after the
papers.

| Column | Means |
| --- | --- |
| In the build | The master that places it is one the build reads. |
| Drawn | Indoors its room draws it (a CHIM room's placement, or a compiled room's own brush); outdoors a CHIM world region draws it. |
| Aimable | It has a container row in the use table the engine reads, and the engine aims at it: where the view ray meets its placement box in a room, its own brush, or its measured box. |
| Opens | The use key opens its strip: unlocked, or locked with its key named (the player then needs the key). |
| Contents filled | Its area record holds every entry of its contents: items and levelled lists (rolled on the first open). |

Each container also counts its kind: fixed items, levelled lists, empty, scripted, a script that takes the activation,
owned (taking is theft), locked, trapped, keyed, respawning.

## Measurements

### v0.0.66 release build, by the v0.0.66 engine (17 November 2026)

Build `2026_11_17_v0.0.66_full-v0.0.66-release-try2_ad5e9a0`, counted with tools/container_census.py
(`--engine-rules v0.0.66`).

| Master | Side | Placed | Open in the original | In the build | Drawn | Aimable | Opens | Contents filled |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Morrowind | interior | 17,180 | 13,409 | 13,409 | 13,409 | 13,397 | 12,371 | 13,409 |
| Morrowind | exterior | 22,225 | 987 | 987 | 973 | 972 | 960 | 987 |
| Tribunal | interior | 1,271 | 872 | 872 | 826 | 826 | 744 | 872 |
| Bloodmoon | interior | 916 | 883 | 883 | 883 | 883 | 728 | 883 |
| Bloodmoon | exterior | 452 | 152 | 152 | 0 | 0 | 0 | 152 |
| All | | 42,044 | 16,303 | 16,303 | 16,091 | 16,078 | 14,803 | 16,303 |

Besides these, 46 containers of the Imperial Prison Ship (closed in the original) and the plants (harvested).

Why the rest did not open:

| Containers | Cells | Reason | Register |
| ---: | ---: | --- | --- |
| 1,139 | 520 | Locked, no key: no lockpick or Open spell in the game, and the engine used no key on a container | [LOCKED-CONTAINERS-NEVER-OPEN-67](../bugs/LOCKED-CONTAINERS-NEVER-OPEN-67.md) |
| 136 | 99 | Locked, its key in the game data, the engine did not use it | [LOCKED-CONTAINERS-NEVER-OPEN-67](../bugs/LOCKED-CONTAINERS-NEVER-OPEN-67.md) |
| 152 | 45 | Solstheim's exterior is not in the CHIM world yet | [BUILD-EXPANSIONS-31](../bugs/BUILD-EXPANSIONS-31.md) |
| 14 | 5 | Seyda Neen's frame leaves its containers out | [SEYDA-CONTAINERS-NOT-DRAWN-67](../bugs/SEYDA-CONTAINERS-NOT-DRAWN-67.md) |
| 12 | 1 | Drawn as a brush of its own, its row skipped (the Census and Excise Office) | [CONTAINER-BRUSH-ROWS-67](../bugs/CONTAINER-BRUSH-ROWS-67.md) |
| 46 | 2 | Mournhold's Great Bazaar and Godsreach are not in the build | [BUILD-EXPANSIONS-31](../bugs/BUILD-EXPANSIONS-31.md) |
| 1 | 1 | The courtyard barrel is the opening's own object: E takes Fargoth's ring | [CHIM-COURT-BARREL-USE-33](../bugs/CHIM-COURT-BARREL-USE-33.md) |

Besides: in the 150 built rooms of Tribunal and Bloodmoon the room records name their placements by the merged master's
number, so 1,709 containers there were aimed by their measured box only, and a placed item there could not be taken
(REF-IDENTITY-MERGED-MASTER-66 in [the register](../BUGS.md)). 35 containers have a script that takes
the activation; they open directly ([CONTAINER-SCRIPT-ACTIVATE-67](../bugs/CONTAINER-SCRIPT-ACTIVATE-67.md)).
For a new game this meant: no container of the Census and Excise Office or Seyda Neen could be opened (the Imperial
Prison Ship's stay closed in the original; its dishes could be taken, PRISON-SHIP-ITEMS-TAKEABLE-65).

### The same build, by the v0.0.67 engine's rules (17 November 2026)

The engine fixes alone (a container drawn as a brush keeps its row; a room's placement is matched by its stable
reference id; a locked container opens with its key; nothing is taken or opened before the release papers allow the
inventory), judged on the same build's data. The builder fixes (every container's key in its area record; Seyda
Neen's containers drawn, a later build) show in the next counts.

| Master | Side | Open in the original | Drawn | Aimable | Opens |
| --- | --- | ---: | ---: | ---: | ---: |
| Morrowind | interior | 13,409 | 13,409 | 13,409 | 12,380 |
| Morrowind | exterior | 987 | 973 | 972 | 960 |
| Tribunal | interior | 872 | 826 | 826 | 744 |
| Bloodmoon | interior | 883 | 883 | 883 | 728 |
| Bloodmoon | exterior | 152 | 0 | 0 | 0 |
| All | | 16,303 | 16,091 | 16,090 | 14,812 |

## How to count

In the build's container (the game data folder and a finished full build's run folder):

    python3 tools/container_census.py --data-files DATA --run RUN [--summary FILE] [--out FILE] [--engine-rules v0.0.66]

It prints one line per master and side, the gaps with the number of containers and cells, and the verdict against the
gaps the register allows (`KNOWN_GAPS`). The builder runs the same count after every full build; it never fails the
build, and its verdict is printed.
