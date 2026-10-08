# CENSUS-LOAD-SLOW-32: The Census and Excise Office takes 8-10 s to load in FS-UAE; other scenes 0.2-1.5 s

## Status: 8 October 2026

Open; tagged performance. Cause confirmed (8 October 2026, A/B/C/D in FS-UAE): the slow load occurs only
with the remote debugging console on (`aw_remote 1`, used by test sessions). With it off, as in normal
play, the dev3 image loads the Census office in 0.13-0.16 s; with it on, 8.8-20.9 s, because each of the
about 1,170 flame error lines per load ([QC-AW-FLAME-SPAWN-32](QC-AW-FLAME-SPAWN-32.md)) is appended to
the remote console log ([REMOTE-CONSOLE-LOG-COST-32](REMOTE-CONSOLE-LOG-COST-32.md)). Found in the v0.0.32-dev3 smoke test (FS-UAE,
build from source 91a7eeb, boot image f6e0d057..., world image 8c14d525...).

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

## How it happened

Likely cause, not yet confirmed by an A/B: load time follows the number of `aw_flame` entities.
A straight line through census and prison gives about 150 ms per flame and a base of about 360 ms,
in line with the scenes without flames. Each flame makes about 23 console calls
([QC-AW-FLAME-SPAWN-32](QC-AW-FLAME-SPAWN-32.md)); each call is written to the debug log file and,
with the remote console on (as in this session), appended to the session's console log on a host
folder volume, which opens and closes the file for every call. About 1,170 calls per Census load
at a few milliseconds each matches the measured time.

If this is the cause, normal play (remote console off) pays only the debug-log part; the owner's
load times for the Census office are not measured yet.

## Why it was not caught

Load times are read per scene by hand; no benchmark compares scene load times with each other, and
the remote console is on in every test session, so its cost is in every measurement.

## Reproduction

FS-UAE, the dev3 image: enter the Census office from Seyda Neen (or `dbg tp census`) and read the
"Scene ready: census, <ms>" line; repeat with another scene for comparison.

## Repair

Not yet. First an A/B/C/D in one session: A as above; B remote console off; C a build without
flames (`AMIWIND_NO_FLAMES=1`); D game logic that accepts `aw_flame` silently; plus a rerun of A.
If the flames' console output is the cause, the repair of QC-AW-FLAME-SPAWN-32 fixes this too.

## Verification

Pending: Census "Scene ready" within the range of the other interiors, remote console on and off.

## Prevention

Proposed: the smoke test records every "Scene ready" time and fails on a scene far above the
others or above its previous build.
