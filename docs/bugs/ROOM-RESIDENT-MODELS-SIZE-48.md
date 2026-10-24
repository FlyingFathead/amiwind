# ROOM-RESIDENT-MODELS-SIZE-48: the batch rooms' resident models take 1.66 GB in about 10,800 files, more than all the rooms themselves

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | build |
| First noticed | 23 October 2026, in v0.0.48-dev2 |
| Where | tools/chim_room_batches.py residents, tools/prepare_area.py resident bakes |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.48-rc1 (last seen) |
| Severity | medium: 1.66 GB of the image and about 180 MiB left on the one-HDF drive |
| Family | Disk images, partitions and launchers (`disk-image-layout`) |
| Playtest version | 2026_10_23_v0.0.48-dev2_dev2-try8_0754e9bc |
| From commit | source 0754e9b, engine 0754e9b, CHIM world 0754e9b |
| CHIM engine version | CHIM 0.2.1, engine 0754e9b, world format 0.7 |
| Platform or emulator | not in game (image size) |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.48 (23 October 2026)._

## Status: 23 October 2026

Fixed for v0.0.48 on the branch v0.0.48-fix-resident-models: the batch rooms stage writes identical resident files
once. Measured on the real v0.0.48-dev2 try 9 output (read only); not yet in a build or in game.

## Symptom

The image's id1/progs was 1.90 GB on the v0.0.48-dev2 try 8 payload, of which the batch rooms' residents (the
NPC and creature models of about 935 converted interior rooms, with their animation layouts, item tags and mover
models) were most. The boot payload has to stay under 2 GiB per partition and the one-HDF drive had about 180 MiB
left, so the question was how much of it is the same model written more than once.

## Cause

Measured on the try 9 output, read only (2026_10_23_v0.0.48-dev2_dev2-try9_9ad40fdf):

- The residents are not baked per room or per reference: prepare_area.populate bakes one per NPC or creature
  record (1,769 records, progs/a_<12 hex of the id>), already shared by every room that places it.
- Their model sets are almost all different: 1,743 distinct sets (model, layout .anm, item tag .tag, mover model and
  its .anm and .tag) for 1,769 records. Only 26 records repeat another's whole set (127 files, 19.0 MB).
- The greetings are the same few files: 1,702 greeting sounds (sound/npc/a_<..>.wav, 26.6 MB) hold 21 distinct
  contents.
- Across the whole image (every stage's residents) the a_ files are 1,711 MB, 1,666 MB by distinct content.

So the size is the residents themselves: 1,700 mover models are 877 MB and 1,769 standing models 482 MB
(project decision 2026-10-09: residents stand in the smaller react model and wear the full mover only while they
move). Content sharing takes off about 45 MB, not the bulk.

## Fix

tools/resident_share.py, called by tools/chim_room_batches.py after the residents step: a resident whose whole
model set is the same file for file as an earlier one (identifier order; the standing layout's reference to its own
mover compared as a placeholder) uses the earlier one's paths, and its copies are deleted; the same for a greeting
sound with the same bytes. The room maps' entities (model, aw_voice) are pointed at the kept files and the
residents report (room-batches-residents.json) records the shared paths (shared_model, shared_voice). The engine
needs no change: it keeps one layout and item tag per model path (aw_anim.c, aw_items.c), and a shared path has the
same files beside it by construction. A record with near/far level files (npc_lod) keeps its own name. The previous
method stays reachable: `tools/chim_room_batches.py --resident-files per-resident`. The stage record
(room-batches.json residents.shared_files) gives the counts.

The resident bakes are untouched (prepare_area.py is not edited), so their unit cache keys stay the same and no
resident is baked again; the stage key covers tools/resident_share.py (tests/test_resident_share.py).

Measured by applying the fix to the try 9 output (deletions recorded, not made; every placed model and voice of the
rewritten maps checked present):

| | files | bytes |
| --- | --- | --- |
| residents output before (progs/a_*, sound/npc/a_*.wav) | 10,881 | 1,397,241,009 |
| residents output after | 9,073 | 1,351,954,320 |
| stage OUT/id1 before | 13,141 | 1,418,725,373 |
| stage OUT/id1 after | 11,333 | 1,373,438,684 |

1,808 files and 45.3 MB (43.2 MiB) less; 591 room maps change (1,931 fields); the step takes about 1.5 s.

## Left open

The remaining 1.35 GB is one model set per resident. Making it smaller means fewer or smaller models (for example
movers shared by body and outfit with the head on its own, or a smaller mover), which changes what the residents
look like or what the engine loads; not part of this fix.

## Verification

- tests/test_resident_share.py: identical sets written once, any differing file keeps a set apart, creatures and
  corpses, greetings, npc_lod records left alone, room maps and report rewritten, per-resident mode unchanged, and
  the stage key covers the module while the resident bake key does not.
- The measurement above on the real try 9 output.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Disk images, partitions and launchers (`disk-image-layout`). Classic FFS limits: partitions under 2 GiB, few files per directory; launchers list every disk. See [families](README.md#families).

- [AMIGA-DISK-2GIB-LIMIT-33](AMIGA-DISK-2GIB-LIMIT-33.md): Amiga disk limits: partitions below 2 GiB and starting below 2 GiB, files well under 2 GiB, drive images below 4 GiB
- AW-20260928-17 (no report page): FS-UAE 24-bit-addressing option rejected
- [BENCH-FSUAE-PLAIN-HDF-32](BENCH-FSUAE-PLAIN-HDF-32.md): FS-UAE does not mount a plain 1.5 GiB partition hard file
- [BUILD-HDF-BUFFERS-32](BUILD-HDF-BUFFERS-32.md): Hard disk buffer and MaxTransfer defaults depend on the disk type
- [BUILD-IMAGE-ALL-CHIM-PREFLIGHT-43](BUILD-IMAGE-ALL-CHIM-PREFLIGHT-43.md): The first build with every exterior on CHIM stops in the image preflight: with no classic world maps left, the disk layout check refuses with a message that names no file or limit
- [BUILD-LAYOUT-GATE-AFTER-WRITE-33](BUILD-LAYOUT-GATE-AFTER-WRITE-33.md): The disk-layout gate ran only after the partitions and drives were written, and not on the dry-run image
- [BUILD-WORLD-PARTITION-MOUNT-33](BUILD-WORLD-PARTITION-MOUNT-33.md): Full v0.0.33-dev1 image stops at 'Please insert volume AW_WORLD3': a partition starts beyond 2 GiB
- [EMULATOR-TEMPLATES-WORLD-32](EMULATOR-TEMPLATES-WORLD-32.md): The static emulator templates list only the boot disk, not the world disk
- [FFS-DIRECTORY-HASH-32](FFS-DIRECTORY-HASH-32.md): Thousands of files in one directory are slow to open on a real FFS disk
- HDF-WRITER-01 (no report page): Private image refresh left file-owned blocks marked free
- [IMAGE-ACTOR-SKIN-REPEATS-46](IMAGE-ACTOR-SKIN-REPEATS-46.md): Every actor skin is stored twice (standing and mover model): 65 MB of repeated skin pixels
- [IMAGE-BOOT-PAYLOAD-OVER-2GIB-48](IMAGE-BOOT-PAYLOAD-OVER-2GIB-48.md): The v0.0.48-dev2 image stopped in its payload preflight: the boot payload (2.75 GB with the batch room residents and the CHIM interior store) is over one partition and the layout could not split it
- [IMAGE-DUPLICATE-FILES-46](IMAGE-DUPLICATE-FILES-46.md): 26 MB of byte-identical files on the boot disk (actor models, voice lines, sprites under two names)
- [IMAGE-LAYOUT-PLAN-ACTOR-LIBRARY-48](IMAGE-LAYOUT-PLAN-ACTOR-LIBRARY-48.md): The image step stopped at its disk layout check: the layout plan left out the actor library it installs (+145 MB on a MiniWind boot partition)
- [IMAGE-MEDIA-CATALOGUE-ON-DISK-46](IMAGE-MEDIA-CATALOGUE-ON-DISK-46.md): A 64 MB build report (the media catalogue) shipped on the Amiga boot disk; nothing in the game reads it
- [IMAGE-ONE-HDF-TARGET-36](IMAGE-ONE-HDF-TARGET-36.md): The game ships on two drive images and three world partitions; the project target is the whole game on one HDF
- [WORLD-HDF-OVER-2GIB-32](WORLD-HDF-OVER-2GIB-32.md): The world hard disk image is 32,768 bytes over 2 GiB
- [WORLD-THIRD-PARTITION-32](WORLD-THIRD-PARTITION-32.md): The world image now needs a fourth partition (DW2); launchers were only used with three

<!-- END GENERATED CATEGORY -->
