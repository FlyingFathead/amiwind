# IMAGE-BOOT-PAYLOAD-OVER-2GIB-48: the boot payload outgrew one partition and the layout could not split it

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | build |
| First noticed | 23 October 2026, in v0.0.48-dev2 |
| Where | tools/layout_plan.py plan_compact and tools/payload_preflight.py check_disk_layout |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.48-dev2 (last seen) |
| Severity | critical: the v0.0.48 release build cannot make its image: every build with the default v0.0.48 content stops in the image step |
| Family | Disk images, partitions and launchers (`disk-image-layout`) |
| CHIM | Builder ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | 2026_10_23_v0.0.48-dev2_dev2-try8_0754e9bc |
| From commit | source 0754e9b, engine 0754e9b, CHIM world 0754e9b |
| CHIM engine version | CHIM 0.2.1, engine 0754e9b, world format 0.7 |
| Platform or emulator | not in game (builder) |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.48-dev2 (23 October 2026)._

## Status: 23 October 2026

Repaired on the v0.0.48 development line (23 October 2026): a boot payload over one partition moves the files the
engine finds through its search path to the world volume, as many as the boot partition needs, planned from the
measured sizes; the payload preflight now counts the room batches and the CHIM interior store. Found by the
v0.0.48-dev2 build, which stopped in its image step before writing anything.

## Symptom

The image step's finalize stopped in its payload preflight with
`disk-layout: Boot payload 2751137598 bytes in 27785 files + 100 MiB headroom needs a 2778 MiB partition (limit below
2147483648 bytes, 2 GiB): it cannot be split` (run `2026_10_23_v0.0.48-dev2_dev2-try8_0754e9bc`, 53 minutes in).
The image step's first preflight, two minutes earlier, had planned the boot partition at 768 MB.

## Where

`tools/layout_plan.py` `plan_compact` (only the open-world maps could leave the boot partition),
`tools/payload_preflight.py` `check_disk_layout` (what the plan counts) and `tools/world_volumes.py` `write_layout`.

## How it happened

v0.0.48 puts the actors on stage in 935 batch rooms and the interiors on CHIM. The boot payload of the dev2 build,
by folder: `id1/progs` 1.90 GB (1.66 GB of it the batch rooms' resident models, `a_<id>` model, mover, layout and tag
files; 0.14 GB the actor library), the CHIM interior store `id1/chimi/` 321 MB, `id1/sound` 236 MB, `id1/intro`
137 MB, `id1/music` 56 MB, the room maps 31 MB once they are CHIM room maps. Kickstart 3.1 limits every partition to
below 2 GiB. The compact layout could move only the open-world maps off the boot partition, so a boot payload over
2 GiB had no layout.

Two counting gaps hid it until the end of the image step: the image step copies the room batches into the payload
after its first preflight (1.66 GB that plan did not see), and it installs the interior store after the finalize
preflight (321 MB in, 368 MB of room `.bsp` maps replaced by small `.chim` room maps; that plan did not see it either).

## Why it was not caught

The batch rooms and the interior store are new in v0.0.48; v0.0.47 had a boot partition of about 1.2 GB. No test
planned a boot payload over 2 GiB with content that can move, and no test planned the room batches or the interior
store.

## Reproduction

The v0.0.48-dev2 build with the room batches and the CHIM interiors (the default content):
run `2026_10_23_v0.0.48-dev2_dev2-try8_0754e9bc`.

## Repair

- `layout_plan.movable_unit`: the boot files the engine opens only through its search path (the boot volume's `id1`,
  then `AW_WORLD0..7:id1`, `common.c`) may live on a world volume, in units that move together: the interior store
  `id1/chimi/` whole, a map with its sidecars, an actor model with its mover, layout and tag files. Music (opened by
  its own path), saves, settings and the rest stay on the boot partition.
- `plan_compact`: when the boot payload does not fit, the largest units move first, only until the boot partition
  fits with twice its headroom (the image step may find it up to one headroom larger); they go to the world volumes
  (the CHIM world volume first), and only when none has room to a further partition (role `store`). A payload that
  still cannot fit is refused with the largest boot folders named. The plan records each partition's units; the image
  step follows that placement and refuses a unit on another partition.
- `write_layout` writes the units on their volume at their boot path and puts them back if a write fails.
- `check_disk_layout` counts the room batches and the interior store (each held room's map at its entity lump plus
  the shell world).
- No engine, startup or emulator preset change: the engine already finds a file on any world volume, and the layout
  stays one drive image when two partitions hold the payload.

On the dev2 run's staged payload (read only): 578 units (818 MB: the interior store, 575 actors, 2 maps) move to
AW_WORLD0; DH0 1,947 MiB (payload 1,894 MB), DW0 1,972 MiB (payload 1,907 MB) starting at 1,947 MiB; one drive image
of 4,109,402,112 bytes.

## Verification

`tests/test_layout_plan.py`: `test_movable_units_are_the_search_path_files`,
`test_boot_over_the_limit_moves_the_largest_units_to_the_chim_volume`,
`test_units_open_a_store_volume_when_no_world_volume_has_room`, `test_a_payload_that_cannot_split_names_its_folders`,
`test_the_image_step_follows_the_planned_units`, `test_the_plan_counts_the_room_batches_and_the_interior_store`,
`test_engine_search_path_finds_the_moved_boot_units` (written with xdftool, every moved file found on its world
volume by the engine's search order) and `test_a_failed_write_puts_the_boot_units_back`.

## Prevention

Those tests. A future boot payload grows into the world volumes the same way; when the units the engine can find
elsewhere are not enough, the plan stops in the first preflight, seconds into the image step, naming the folders.

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
- [IMAGE-DUPLICATE-FILES-46](IMAGE-DUPLICATE-FILES-46.md): 26 MB of byte-identical files on the boot disk (actor models, voice lines, sprites under two names)
- [IMAGE-LAYOUT-PLAN-ACTOR-LIBRARY-48](IMAGE-LAYOUT-PLAN-ACTOR-LIBRARY-48.md): The image step stopped at its disk layout check: the layout plan left out the actor library it installs (+145 MB on a MiniWind boot partition)
- [IMAGE-MEDIA-CATALOGUE-ON-DISK-46](IMAGE-MEDIA-CATALOGUE-ON-DISK-46.md): A 64 MB build report (the media catalogue) shipped on the Amiga boot disk; nothing in the game reads it
- [IMAGE-ONE-HDF-TARGET-36](IMAGE-ONE-HDF-TARGET-36.md): The game ships on two drive images and three world partitions; the project target is the whole game on one HDF
- [ROOM-RESIDENT-MODELS-SIZE-48](ROOM-RESIDENT-MODELS-SIZE-48.md): The batch rooms' resident models take 1.66 GB in about 10,800 files, more than all the rooms themselves
- [WORLD-HDF-OVER-2GIB-32](WORLD-HDF-OVER-2GIB-32.md): The world hard disk image is 32,768 bytes over 2 GiB
- [WORLD-THIRD-PARTITION-32](WORLD-THIRD-PARTITION-32.md): The world image now needs a fourth partition (DW2); launchers were only used with three

Related bugs in other categories:

- [BUILD-PARTITION-GROWTH-UNGATED-36](BUILD-PARTITION-GROWTH-UNGATED-36.md): Nothing gates the number of world partitions or the growth of the image

<!-- END GENERATED CATEGORY -->
