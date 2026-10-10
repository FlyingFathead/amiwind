# CENSUS-LOAD-SLOW-32: The Census and Excise Office takes 8-10 s to load in FS-UAE; other scenes 0.2-1.5 s

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 8 October 2026, in v0.0.32-dev3 |
| Where | Census and Excise Office scene load |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.32-dev3 (last seen) |
| Severity | medium: Census office loads in 8-10 s against 0.2-1.5 s elsewhere in the emulator. |
| Family | Loading and disk reads (`disk-loading`) |
| Playtest version | v0.0.32-dev3 |
| From commit | source and engine 91a7eeb |
| CHIM engine version | none: legacy engine |

<!-- END GENERATED FACTS -->

## Status: 8 October 2026

Open: cause confirmed, repaired in source with [QC-AW-FLAME-SPAWN-32](QC-AW-FLAME-SPAWN-32.md),
not yet in a built image. Tagged performance. Cause confirmed (8 October 2026, A/B/C/D in FS-UAE): the
slow load occurs only with the remote debugging console on (`aw_remote 1`, used by test sessions). With
it off, as in normal play, the dev3 image loads the Census office in 0.13-0.16 s; with it on, 8.8-20.9 s,
because each of the about 1,170 flame error lines per load is appended to the remote console log
([REMOTE-CONSOLE-LOG-COST-32](REMOTE-CONSOLE-LOG-COST-32.md)). Found in the v0.0.32-dev3 smoke test
(FS-UAE, build from source 91a7eeb, boot image f6e0d057..., world image 8c14d525...).

## Symptom

"Scene ready" times from one FS-UAE session (A1200 with 68040, JIT on, CPU speed max, remote
console on; emulator numbers are relative):

| Scene (map) | Scene ready | `aw_flame` entities |
| --- | --- | --- |
| census (`census.bsp`) | 7,816 ms, then 10,320 ms | 51 |
| prison (`prison.bsp`) | 1,530 ms | 8 |
| seyda (`sn029.bsp`, `intro_docks.bsp`) | 816, 296, 309, 364 ms | 0 |
| balmora (`bm019.bsp`) | 493 ms | 0 |
| vivec_arena | 239, 214 ms | 0 |

Every Census load also prints 51 blocks of entity errors
([QC-AW-FLAME-SPAWN-32](QC-AW-FLAME-SPAWN-32.md)).

## Where

Scene loading of maps with placed flames; the Census office is the map with the most flames.
The time goes into `Con_DebugLog` (`engine/aga/src/console.c`), which the remote console
(`aw_remote.c`) uses to append every console call to `AWCTL:console.log`.

## How it happened

Each flame makes 23 console calls ([QC-AW-FLAME-SPAWN-32](QC-AW-FLAME-SPAWN-32.md)): about 1,170
per Census load, 180 per prison ship load. With the remote console on, every call opens the session
log on the emulator's host-folder volume, seeks to its end, writes and closes it (Quake's
`-condebug` method). In FS-UAE that costs about 7-18 ms per call, so the flame errors alone take
8-21 s. With the remote console off the same lines still go to the engine's debug log file and the
console buffer, which costs almost nothing (B below). Normal play never had the slow load; test
sessions, which always run with the remote console on, did.

Measured 8 October 2026, A/B/C/D in one container (fresh copies of the dev3 image on a Docker
volume; one emulator per game logic, booted one after the other; `dbg tp` to each scene, three
rounds; host busy: other containers at 14-23 of 24 threads, so the absolute numbers are inflated and
only the ratios count). C and D use the dev3 image with only `progs.dat` replaced by the
QC-AW-FLAME-SPAWN-32 repair.

| Variant | Game logic | Remote console | census (51 flames), ms | prison (8), ms | balmora (0), ms |
| --- | --- | --- | --- | --- | --- |
| A | dev3 | on | 8,780 / 16,052 / 18,014 | 3,041 / 2,104 / 3,505 | 1,148 / 378 / 847 |
| B | dev3 | off | 129 / 130 / 161 | 169 / 200 / 174 | 222 / 261 / 291 |
| C | repaired | on | 215 / 200 / 414 | 559 / 246 / 258 | 765 / 343 / 466 |
| D | repaired | off | 131 / 216 / 115 | 209 / 137 / 186 | 245 / 211 / 399 |
| A again (drift control) | dev3 | on | 20,878 / 13,525 / 17,357 | 4,001 / 1,967 / 3,818 | 651 / 433 / 343 |

Other dev3 loads with the remote console on in the same container: Census 5,531, 7,625, 9,245,
20,358 and 21,668 ms. Census with the repaired game logic is within the range of the other scenes,
remote console on or off. The remaining spread of the remote-console runs (and the slower first
loads) is the per-call log cost, registered as
[REMOTE-CONSOLE-LOG-COST-32](REMOTE-CONSOLE-LOG-COST-32.md).

## Why it was not caught

Load times are read per scene by hand; no benchmark compares scene load times with each other, and
the remote console is on in every test session, so its cost is in every measurement.

## Reproduction

FS-UAE, the dev3 image, `aw_remote 1`: `dbg tp census` and read the "Scene ready: census, <ms>"
line; then the same command after `aw_remote 0` (read the line in the console).

## Repair

The Census office's console output comes from the flame entity errors; the repair of
[QC-AW-FLAME-SPAWN-32](QC-AW-FLAME-SPAWN-32.md) (game logic accepts `aw_flame`) removes it. No
engine change. The per-call cost of the remote console log itself stays open as
[REMOTE-CONSOLE-LOG-COST-32](REMOTE-CONSOLE-LOG-COST-32.md).

## Verification

Census "Scene ready" 200-414 ms with the remote console on and 115-216 ms with it off (variants C
and D above), against 8.8-20.9 s for the dev3 game logic with the remote console on. Pending: the
same check on the next image built from source.

## Prevention

`tests/test_entity_spawn_contract.py` keeps converter entities from printing load errors. Proposed:
the smoke test records every "Scene ready" time and fails on a scene far above the others or above
its previous build; load-time measurements state whether the remote console was on.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Loading and disk reads (`disk-loading`). Load time follows bytes read and seeks on FFS; measured with read counters, not wall time alone. See [families](README.md#families).

- [CHIM-READ-RUNS-33](CHIM-READ-RUNS-33.md): CHIM crossings read little but in many separate runs, so FFS seeks dominate
- [ENGINE-FOPEN-TEXT-MODE-35](ENGINE-FOPEN-TEXT-MODE-35.md): Binary files (paks, maps) were opened in text mode
- [ENGINE-PAK-HEADER-TRUST-35](ENGINE-PAK-HEADER-TRUST-35.md): The pak loader trusted the header: a negative or oversized directory length sized a read into a 128 KiB stack array, and entry offsets were never checked
- [LOADER-STALL-32](LOADER-STALL-32.md): One unexplained stall while loading the Mages Guild with the new loader
- PERF-READAHEAD-29 (no report page): Outdoor cell/sub-cell crossing pauses and lost read-ahead
- [SEYDA-LOAD-HANG-30](SEYDA-LOAD-HANG-30.md): Rare freeze during a Seyda Neen region load
- [SEYDA-READ-SLOW-31](SEYDA-READ-SLOW-31.md): dev1 Seyda crossings read slower than the ov700 test image
- [STREAM-FFS-SEEK-32](STREAM-FFS-SEEK-32.md): Random 16 KiB reads on FFS run at 0.44 MB/s and take most of the CPU

Related bugs in other categories:

- [QC-AW-FLAME-SPAWN-32](QC-AW-FLAME-SPAWN-32.md): Every aw_flame entity prints load errors: the game logic has no aw_flame spawn function or aw_flame_size/aw_flame_shape fields
- [REMOTE-CONSOLE-LOG-COST-32](REMOTE-CONSOLE-LOG-COST-32.md): With the remote console on, every console line costs about 7-18 ms in FS-UAE

<!-- END GENERATED CATEGORY -->
