# RAM-REQUIREMENT-32MB-48: 16 MB of Fast RAM no longer holds the whole game; 32 MB is the safe minimum

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 23 October 2026, in v0.0.48-dev2 |
| Where | Fast RAM requirement: boot check, engine start, launcher and emulator presets |
| Reproduction | always |
| Duplicate of | no |
| Persists in | fixed in v0.0.48-dev2 |
| Severity | medium: on 16 MB 14 outdoor frames overflow the model cache: models are evicted and loaded again, slower, not a crash |
| Family | Map heap and memory budget (`heap-memory`) |
| Playtest version | unknown |
| From commit | source unknown, engine unknown, CHIM world unknown |
| CHIM engine version | CHIM unknown, engine unknown, world format unknown |
| Unknown because | a memory budget measured over the whole world's placements, not one build |
| Platform or emulator | not in game (measured from the placed actors and room sets per frame, 22-23 October 2026) |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.48-dev2 (23 October 2026)._

<!-- contents start -->
## Contents

- [Status: 23 October 2026](#status-23-october-2026)
- [Symptom](#symptom)
- [Where](#where)
- [How it happened](#how-it-happened)
- [Why it was not caught](#why-it-was-not-caught)
- [Reproduction](#reproduction)
- [Repair](#repair)
- [Verification](#verification)
- [Prevention](#prevention)
- [Bugs in the same category](#bugs-in-the-same-category)

<!-- contents end -->

## Status: 23 October 2026

Fixed in v0.0.48-dev2 (branch v0.0.48-fast-ram-32). Decided for the project, 23 October 2026: for now the game
requires 32 MB of Fast RAM, the safe minimum, which should be enough for the entire game. More RAM is used
automatically. 16 MB still starts, with a warning, and loads more often.

## Symptom

With every outdoor NPC and creature placed, some outdoor frames need more model cache than a 16 MB machine has
room for. The engine then evicts models and loads them again from the disk: slower, not a crash. Until this change
the start-up check, the documentation and the emulator presets still named 16 MB as enough for the whole game.

## Where

The Fast RAM requirement: the start-up check (`engine/aga/boot/bootcheck.asm`, run by `S:startup-sequence` before
the engine), the engine's start (`engine/aga/src/sys_amiga.c`), the playtest launcher
(`tools/AmiWind-FS-UAE-launcher.py`), the emulator configs written with every build and playtest package
(`tools/emulator_configs.py`) and the play presets in `resources/emulators/`.

## How it happened

Measured 22 and 23 October 2026 with every outdoor NPC and creature placed (781 actors in the 336 CHIM region
frames):

- The 16 MB baseline leaves about 2.1 MB of model cache. 14 region frames need more; the worst, `rcp2_m7`, needs
  2.0 MB more. Actor models per frame are 624 KB at the median and 4.13 MB at most.
- With more RAM (measured with a 24 MiB game heap, about 15.7 MB of cache) every frame fits.
- Interiors share CHIM's room store: the largest Balmora room set is 4.10 MB against a 7.03 MB room zone.

The 16 MB figure dates from the first towns, before the whole island was on CHIM and before the actors outside the
towns were placed.

## Why it was not caught

The memory gates check each map against its heap and zone, not the model cache the actors of a frame need on the
smallest machine; the playtests ran with 128 MB from 21 October 2026.

## Reproduction

Start the game on 16 MB of Fast RAM and travel through the frames with the most actors (for example `rcp2_m7`):
the model cache evicts and reloads.

## Repair

- **Start-up check:** below 32 MB of Fast RAM (Exec's total, with 64 KiB of slack for the bytes Exec keeps) the
  Fast RAM row reads `Fast RAM: 16 MB (32 MB needed) [!] WARN` instead of `[x] OK`, never a failure. Under the
  checklist's closing line it prints

      -----------------------------------------------------
      NOTE: AmiWind has grown since v0.0.48: 32 MB of Fast RAM is now
      the minimum. Only 16 MB Fast RAM found, hence the game will
      start but may load more often.
      Press ENTER to continue anyway.
      Starting in 10 s...

  with the size found (rounded down to whole MB). The countdown never blocks (the maintainer, 23 October 2026:
  "let it run then even with 16MB but at least so that the user/player is warned"): after ten seconds, or at once
  with ENTER, it reads `Starting now.` and the game starts, so unattended runs at 16 MB go on by themselves.
  32 MB and more: the `[x] OK` row and the five-second countdown, as before. No new Amiga programs on the disk;
  the waits are in `engine/aga/boot/boot_wait.asm`.
- **Engine:** the same note, without the ENTER sentence (the start-up check already counted down), on the CLI before the
  heap is taken, on the console after start-up and on the startup logo. Nothing at 32 MB and more.
- **Heap sizing unchanged:** 16 MB keeps the built 11 MiB heap, 32 MB grows it to 13 MiB, 64 MB to 20 MiB and
  128 MB to 24 MiB, as since v0.0.45 ([ENGINE-HEAP-FIXED-SIZE-43](ENGINE-HEAP-FIXED-SIZE-43.md)); CHIM's caches and
  the read-ahead take what is left, as before.
- **Launcher and presets:** the playtest launcher, the emulator configs written with every build and playtest
  package, the play presets and the current version's presets start with 32 MB. 16 MB stays a launcher choice
  (entry 2, `--fast-ram 16`) with a warning; 64 and 128 MB are choices too. The measurement presets keep their
  16 MB on purpose (their figures stay comparable), and the A4000 presets keep the tester's 128 MB.
- The text and the 32 MB figure come from one place (`tools/project_version.py`, generated into the boot check and
  the engine).

## Verification

`tests/test_heap_size.py` (FastRamSafeMinimumTests): the maintainer's text word for word, the size rule at 16, 24,
31, 32, 64 and 128 MB, the generated boot rows, the assembled start-up check, and the engine's note compiled on the
host at 16 MB (shown) and at 32, 64 and 128 MB (nothing), and `boot_wait.asm` run on the host line by line:
nobody pressing a key (ten one-second rows, then the start), ENTER in the fourth second (the wait ends there),
another key (the count goes on), no console input (Delay), and the 32 MB five-second countdown; AutoHeapTests: the heap at 16, 32, 64 and 128 MB.
`tests/test_launcher_fast_ram.py`: the 32 MiB default, the 16 MiB warning, the presets. Not yet seen in the
emulator at 16 and 32 MB (an in-game measurement had the emulator).

## Prevention

A frame whose actors need more model cache than the safe minimum leaves should fail the memory gate: noted for the
gate work.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Map heap and memory budget (`heap-memory`). The heap model must match what the loader actually allocates; strict heap gate, hard ceiling always fatal. See [families](README.md#families).

- AW-20260929-06 (no report page): Expanded scene exhausts 9 MiB heap
- [BUILD-CHIM-HULL-RING-33](BUILD-CHIM-HULL-RING-33.md): Routed and compiled CHIM model hulls grew Balmora's ring past the zone
- [CHIM-ARENA-HUNK-GAP-36](CHIM-ARENA-HUNK-GAP-36.md): The Vivec Arena frame leaves less than 2 MiB of hunk gap (memory review before Vivec stage B)
- [CHIM-AUTO-BANK-CLIFF-51](CHIM-AUTO-BANK-CLIFF-51.md): 32 MB of Fast RAM got no automatic CHIM cache bank: 13 MiB free gave a 7 MiB budget and the first bank needed 8 MiB
- [CHIM-BALMORA-RING-GROWTH-36](CHIM-BALMORA-RING-GROWTH-36.md): Balmora's CHIM ring grew past the zone after v0.0.36-dev3 with the converter mesh method
- [CHIM-BALMORA-RING-OVER-33](CHIM-BALMORA-RING-OVER-33.md): CHIM heap gate fails on Balmora in the first full v0.0.33 build: the south-west active ring needs 136,160 bytes more than the zone holds
- [CHIM-BITTERCOAST-HEAP-SHAPEGUARD-43](CHIM-BITTERCOAST-HEAP-SHAPEGUARD-43.md): Two Bitter Coast CHIM frames over the heap zone after the trunk shape guard
- [CHIM-COLLISION-UNION-FALLBACK-41](CHIM-COLLISION-UNION-FALLBACK-41.md): Daedric ruin collision falls back to raw piece chains and puts Hla Oad's frames over the CHIM memory budget
- [CHIM-HEAP-CHECK-33](CHIM-HEAP-CHECK-33.md): The heap check does not account for a CHIM map's zone bank
- [CHIM-HULL-SURFACE-HEAP-46](CHIM-HULL-SURFACE-HEAP-46.md): The walkway collision fix put six CHIM frames over the zone: every point of a convex piece kept, sides included
- [CHIM-LAVA-HUNK-GAP-38](CHIM-LAVA-HUNK-GAP-38.md): Lava MiniWind first presentation falls below the 2 MiB hunk-gap safety
- [CHIM-ROOM-HEART-CHAMBER-LOAD-50](CHIM-ROOM-HEART-CHAMBER-LOAD-50.md): Entering Akulakhan s Chamber (the Heart Chamber) ends the game: a model of its room store does not load, and the engine stops with Host_Error instead of refusing at the door
- [CHIM-SEYDA-HUNK-GAP-33](CHIM-SEYDA-HUNK-GAP-33.md): Seyda Neen's CHIM map leaves less than the 2 MiB Hunk-gap safety at the default zone
- [CHIM-SEYDA-MEMORY-33](CHIM-SEYDA-MEMORY-33.md): Seyda Neen's CHIM ring was modelled larger than Balmora's: the irregular ground's routed standing hull
- [CHIM-STRIDER-RING-33](CHIM-STRIDER-RING-33.md): The closed-hull strider (MESH-LOD-OPEN-SEAMS-33, variant E) puts CHIM Balmora's active ring over the heap budget
- [CHIM-ZONE-BUDGET-33](CHIM-ZONE-BUDGET-33.md): The engine's default CHIM zone does not hold the active ring of Seyda Neen or of Balmora's south-west corner
- [CHIM-ZONE-RESERVE-EARLY-33](CHIM-ZONE-RESERVE-EARLY-33.md): chim_reserve_kib is checked before the map's actors and precaches load, so it cannot keep the Hunk gap
- CRASH-01 (no report page): Heap exhaustion on sn012 after Hors travel from Jiub name entry
- [ENGINE-HEAP-FIXED-SIZE-43](ENGINE-HEAP-FIXED-SIZE-43.md): The game heap is a fixed 11 MiB from the build: with 128 MB of RAM Vivec still runs under the 2 MiB safety gap and loads pause
- [ESTIMATE-HEAP-STALE-32](ESTIMATE-HEAP-STALE-32.md): World estimate heap coefficients were fitted to the old loader model
- [HEAP-12MB-FAST-ROOM-33](HEAP-12MB-FAST-ROOM-33.md): A 12 MiB game heap leaves 342 KB of Fast RAM in one block: the guard torch's 1 MiB probe can never pass
- [HEAP-MODEL-SUM-32](HEAP-MODEL-SUM-32.md): Summing per-object costs overestimates a map's heap (11 % median, 39 % worst)
- HUNK-RESERVE-SN012-29 (no report page): Dev4 first-presented sn012 reserve below 2 MiB target
- [LOADER-STAGING-PEAK-32](LOADER-STAGING-PEAK-32.md): Map loading stages most lumps in temporary memory before decoding, raising the heap peak
- [MAP-UNUSED-HULL2-32](MAP-UNUSED-HULL2-32.md): Shipped maps carry about 1.1 MB of collision data for a hull the engine never uses
- MEM-GEOMETRY-01 (no report page): Light-range sharing could copy a too-short byte span
- MEM-TOWN-02 (no report page): Bounded Balmora maps exceeded the modeled map heap limit
- [NPC-ANIM-MEMORY-33](NPC-ANIM-MEMORY-33.md): Full animation kit models are 2.2 times the idle models; four Balmora residents exceed the 512 KiB alias staging buffer
- [VIVEC-HEAP-31](VIVEC-HEAP-31.md): Dense Vivec maps exceed the loader heap budget once mappings and extents no longer stop them
- WORLD-FLORA-HEAP-010 (no report page): Seyda sprite payload exceeds the final map heap headroom

Related bugs in other categories:

- CHIM-FRAME-16MB-REFUSAL-48 (no report page): Five CHIM region frames are over or within 64 KiB of the 16 MB heap budget: on 16 MB of Fast RAM (or with Extra RAM off) their rings may not fit the zone
- CHIM-ROOM-16MB-REFUSAL-48 (no report page): On 16 MB of Fast RAM (or with Extra RAM off) a CHIM room larger than the zone ended the game with a host error at its door
- [ENGINE-FRAME-REFUSE-PROTOTYPE-48](ENGINE-FRAME-REFUSE-PROTOTYPE-48.md): The engine build stops on a missing prototype: AW_SceneFrameRefuse has no declaration

<!-- END GENERATED CATEGORY -->
