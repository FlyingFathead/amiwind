# BUILD-NIGHT-TABLES-31: Repository image builds have no night lamp, glowing glass or location fog tables

## Status: 8 October 2026

Open. Repaired in source; not yet in a built image. Present in every
repository build since the first table was introduced (v0.0.31-dev4).

## Symptom

An image built from the repository (`build.sh`, `build.cmd`, `build.ps1`,
`tools/build.py`, `tools/build_aga.py image`) has dark street lamps at night,
no glowing window or lantern glass, and `dbg fog location 1` does nothing.
The playtest disks had all three because the tables were added to them by
hand.

## Where

The engine reads `id1/world/lamps.awl` (`engine/aga/src/aw_lamps.c`),
`id1/world/night-windows.txt` (`aw_lamps.c`) and
`id1/world/fog-locations.txt` (`engine/aga/src/aw_fog_location.c`). Nothing in
the image builder wrote them. The engine treats a missing table as "none",
so the image still boots and plays.

## How it happened

The tables were developed one at a time beside the image builder:
`tools/light_sources.py lamp-table` (dev4), `tools/night_windows.py` (dev5)
and `config/fog-locations.txt` (after dev5). Each playtest disk was made by adding
the new table to the previous disk, so the builder step was never needed for
a playtest and was never written.

## Why it was not caught

No gate lists the files an image must contain for night lighting, and the
engine falls back silently when a table is absent.

## Reproduction

At v0.0.31-dev5 (`d237561`), `git grep` for `lamps.awl`,
`night-windows.txt` and `fog-locations.txt` finds them only in the engine and
its tests, the debug command catalogue, the night window tool and its test,
the release file lists and the docs; no image builder code writes them, so
`id1/world/` on a repository-built boot partition lacks all three.

## Repair

`tools/night_lighting.py`, called from `finalize_image` after the final map
optimisation, writes all three tables into the boot image:

- `lamps.awl` from the owned `Morrowind.esm` (`--data-files`).
- `night-windows.txt` from the final town maps and the scenery they were
  converted from: `--balmora-scenery` (default `--balmora-cache`/scenery),
  `--town-scenery` (default the directory of `--town-flora-source-index`),
  the scene's `opening-barrel-source` and the `--world-flora` overlay. The
  guided build passes the first two. A missing source is skipped and listed
  in the receipt (status `partial`); a town without its own scenery gets no
  line rather than a guessed one.
- `fog-locations.txt`, a copy of `config/fog-locations.txt` checked for ASCII,
  LF and "name day night" lines in the engine's range.

Each table is checked against the engine's format before anything is
written. The receipt (`image/night-lighting/night-lighting.json` and
`build.json` `night_lighting`) records each table's size and SHA-256, and the
tables join the save-content fingerprint.

## Verification

- `tests/test_night_lighting.py`: synthetic stage, all three tables written
  with correct headers and format, receipt hashes, missing optional scenery
  reported and not fatal, missing town scenery never guessed, fingerprint,
  builder and guided-build wiring.
- Same inputs as the private dev5 table (dev2 town maps and the private
  scenery caches, Docker): the builder's window table is byte-identical
  (1,682 bytes, 79 maps, 119 textures). The lamp table has the same 694
  placements; only the colour byte differs, because the dev5 table predates
  it (it was all 0).
- Pending: a full repository image build and an in-game night check.

## Prevention

The builder writes and checks the tables itself and records them in the
receipt; the test fails if the step moves before the final maps or after the
save fingerprint.
