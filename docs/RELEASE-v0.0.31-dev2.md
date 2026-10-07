# AmiWind v0.0.31-dev2 - Revisiting Seyda Neen

Development build: everything in [dev1](RELEASE-v0.0.31-dev1.md), plus much
faster loading, the entity tracker and a debug headlamp. Everything else is as
in [v0.0.30](RELEASE-v0.0.30.md).

## Faster loading everywhere

Game files used to be read 1 KiB at a time, one disk call per KiB. They are now
read through a 16 KiB buffer. On the FS-UAE test route, Seyda Neen region
crossings drop from 0.70-0.91 s (dev1) and 0.54-0.71 s (v0.0.30) to
0.39-0.48 s, and the disk part of each crossing is less than half. Every other
map load reads the same way. How it was found:
[performance lessons](performance/LESSONS_LEARNED.md),
[SEYDA-READ-SLOW-31](bugs/SEYDA-READ-SLOW-31.md).

## Debug headlamp

`dbg headlamp on` (or `hlamp`; on/off, true/false, 1/0) gives you the torch's
light without holding a torch: a steady light for looking around dark rooms.
Off by default and not saved.

## Entity tracker

The image build now counts what the original game places against what AmiWind
places, by category and cell, and stops if a category goes missing. See the
[entity tracker](trackers/ENTITIES.md).

## Known in this build

- With the new buffer, the newer engine still reads 10-15 % slower than the
  v0.0.30 engine would ([SEYDA-READ-SLOW-31](bugs/SEYDA-READ-SLOW-31.md)).
- Everything listed in the [dev1 notes](RELEASE-v0.0.31-dev1.md), the
  [v0.0.30 notes](RELEASE-v0.0.30.md) and the [bug register](BUGS.md).
