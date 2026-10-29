# AmiWind v0.0.55-dev2 (in development)

Development snapshot, 28 October 2026, in development. Running on CHIM Engine v0.2.2. Previous snapshot:
[v0.0.55-dev1](RELEASE-v0.0.55-dev1.md); previous release: [v0.0.54](RELEASE-v0.0.54.md).

The second snapshot of v0.0.55, a small one: the build monitor now gathers every warning of a build in one place.
The game is the one of dev1; it needs 32 MB of Fast RAM, and the emulator presets of this snapshot have it. What dev1
brought (builds that survive memory pressure on any machine, memory in the monitor, the organised docs, DemoWind) is
listed in its [notes](RELEASE-v0.0.55-dev1.md).

## New since v0.0.55-dev1

- **A warnings row in the Toolkit's build monitor.** Under the RAM line a yellow `Warnings: N [view]` row counts every
  warning the build has printed in its stage logs: the WARNING lines (a worker lost to memory, nearly no RAM left, a
  slow section), the lines of stages that ran on too few cores and the scheduler's alarms and memory cuts, each with
  the time and the stage; `[view]` opens the list. The row is hidden while there are none
  ([MONITOR-WARNINGS-ROW-54](../../BUGS.md), [AmiWind Toolkit](../../AMIWIND_TOOLKIT.md#monitor)).

## Known in this build

- The CHIM stage's main process still holds a lot of memory of its own, which keeps its workers few on a small
  machine ([BUILD-CHIM-MAIN-MEMORY-46](../../bugs/BUILD-CHIM-MAIN-MEMORY-46.md)).
- Some rooms still load in after you arrive ([CHIM-ROOM-POPIN-51](../../bugs/CHIM-ROOM-POPIN-51.md)).
