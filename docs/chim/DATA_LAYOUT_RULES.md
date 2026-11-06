# Data layout rules: small lookup tables, per area

_Last updated with AmiWind v0.0.61-dev1 (5 November 2026)._

A rule of thumb for everyone who adds data the game reads while it runs: lookup tables stay small and belong to an
area. The game needs consistency that follows the player through the world, but loading the whole world's data at once
is too heavy for the target machines, and a large table clogs the loader, the memory and the disk. So the data a place
needs is loaded with that place and freed with it. Every design that adds run-time data states its numbers against the
rules below (RAM, CPU, disk and load time, see [the CHIM engine](ENGINE.md#memory)).

## The rules

1. **Per cell or room, never world-wide.** Run-time data lives in the area record of the cell or room it belongs to,
   read in the one read the area load already does, and freed with the area. There is no run-time file that covers the
   whole world and no search across the world. Files that only the builder reads (the item index is an example) may
   cover the world; the image never reads them.
2. **The player's saved change list is the only world-wide state.** One small list of what the player changed (items
   taken or moved, doors, containers, ranks, about 6 KB) is applied to an area when it loads. Consistency comes from
   that list, not from loading the world.
3. **The size yardsticks.** Measured on the current build: an area record has a median of about 5.7 KB. One system's
   section per area has a median well under 1 KB (the actor stats section: 131 bytes) and its largest area takes a few
   KB (stats: 1.7 KB). All shared resident vocabularies together come to a few tens of KB (the shared stats record is
   4.7 KB, plus the item chunks). A new section that is past 4 KB in its largest area, or a resident table past 16 KB,
   needs a named reason in the design's budget sheet.
4. **Shared once, unless that costs a seek per room.** A block that repeats across areas is stored once, kept resident
   and referenced by number. The exception is a room load: when sharing would cost an extra seek when a room loads, the
   rooms keep their own copy, because one read per room beats a smaller file.
5. **Compact binary with direct offsets; no parsing in play.** Fields use their natural widths, optional fields use
   present masks, and the placement refers to its data by offset or index. There is no hash search on the spawn path
   and no text parsing while playing.
6. **The added load time is always stated.** A design lists the bytes it adds to an area load and the time they take at
   2 MB/s (the speed of the emulated A1200 IDE disk), typical and worst. It adds no new file open per load.
7. **Staggered decode outdoors, through the prefetch ring.** Outdoors, a new area's sections ride the CHIM streamer's
   prefetch of the ring of cells ahead of the player and are decoded a little per frame (a fixed number of entries per
   frame, for example the live blocks of a few actors), so a cell crossing never does all of it in one frame. A cell's
   actors appear as their blocks become ready. Rooms load everything at once behind the loading screen, in one read.
   Every design states its worst crossing frame cost.

## Checking

The plan is a builder or gate check that reports every run-time table's per-area and resident sizes and fails when a
table goes past the limits of rule 3 without a recorded reason. Until it exists, the budget sheet of each design shows
the numbers by hand.

## Where it applies

The per-area tables of the residents, containers, doors, items and creatures follow these rules, as does the
per-area actor stats section. See [the CHIM engine](ENGINE.md), [the roadmap](../ROADMAP.md) for the work that uses them
and the [performance records](../performance/) for how numbers are kept.
