# Residents' recipe tables: the area pack against the earlier files

_Last updated with AmiWind v0.0.60-dev3 (4 November 2026)._

The residents drawn from parts (`dbg camera npcs on`) look up their appearance in small tables per exterior cell and
per interior. Since v0.0.60 those tables are also written into one pack, `id1/npc-parts.awa`, on the same per-area
layout as the container tables (`areas.awa`) and the walking residents' tables (`npc-ambient.awa`). The setting
`aw_npc_tables_areas` chooses the method: 1 (the default) reads the pack, 0 reads the earlier files
(`view/npc_parts/cells.awnp`, one `<map>.awnb` file per room, and `view/npc_parts/dir.awnd`).

## The record

| | |
| --- | --- |
| Build | MiniWind of Seyda Neen, `2026_11_04_v0.0.60-dev3_miniwind-seyda-tables2_a7f9a9f` (source a7f9a9f6) |
| Engine | SHA-256 9534f33a... (68040 build) |
| Emulator | FS-UAE, JIT preset, 32 MB Fast RAM |
| Script | the in-game check of the recipe pack (SHA-256 ccfa8687...): Seyda Neen, a cell crossing, Arrille's Tradehouse, then the same with the setting at 0 |
| Data | 20 residents from parts in 10 places (4 exterior cells, 6 rooms); pack 4,067 bytes, its index 136 bytes and its directory 160 bytes |
| Previous line | none: the first measurement of either method in play |

## What each method did

| Event | `aw_npc_tables_areas 1` (the pack) | `aw_npc_tables_areas 0` (the earlier files) |
| --- | --- | --- |
| First use | 1 open of `npc-parts.awa`, index and directory read (280 bytes held) | 1 open of `cells.awnp` (56-byte index held); `dir.awnd` opened and read (224 bytes held) at the first resident outside the loaded places |
| Arrival in Seyda Neen | 3 areas read, 1,084 bytes, 1.8 ms in all (one seek and one read each) | no cell table read on the arrival in this session (no arrival event for the town's own cells); the room's table stayed held, and residents found their recipes through the directory in play |
| Room entry (Arrille's Tradehouse) | 1 seek and 1 read, 924 bytes, 1.7-2.3 ms, no file opened | 1 open of `tradehouse.awnb` and 1 read, 924 bytes, 1.3 ms |
| A resident outside the loaded places (Nels Llendo, cell 0,-9) | read at the place change, 303 bytes, 0.8 ms; never in play | read in play when first drawn, 303 bytes, 4.4 ms |
| Cell crossing (the three cells west of Seyda Neen hold no residents from parts) | 0 reads | 0 reads |

## Reading it

In the emulator a file open costs little (FS-UAE moves about 90 MB/s and opens a file in well under a millisecond),
so the room entry is a little faster with the earlier file. On an Amiga IDE disk each open is a directory search
that costs tens of milliseconds, and the pack saves that open on every room entry. The narrow load of a resident
outside the loaded places moves from the middle of play to the place change. Neither method changes what is drawn:
the same residents from the same parts.

The resident registry grew by one setting (`aw_npc_tables_areas`). Memory held while residents from parts are on:
the index and directory (280 bytes) and the tables of the places loaded now, the same tables as before.

The next step is to read each area's recipe and walking tables together with its container table in one read; it is
planned, not measured.
