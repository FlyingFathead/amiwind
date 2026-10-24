# IMAGE-LAYOUT-PLAN-ACTOR-LIBRARY-48: the disk layout plan left out the actor library the image step installs

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | build |
| First noticed | 22 October 2026, in v0.0.48-dev2 |
| Where | tools/payload_preflight.py check_disk_layout: DH0 plan without the installed actor library |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.48-rc1 (last seen) |
| Severity | high: every MiniWind build with the actor table on (the default) stops at the end of its image step |
| Family | Disk images, partitions and launchers (`disk-image-layout`) |
| Playtest version | 2026_10_22_v0.0.48-dev2_miniwind-balmora-rooms-bsp_dd768704 |
| From commit | source dd76870, engine dd76870, CHIM world dd76870 |
| CHIM engine version | CHIM 0.2.1, engine dd76870, world format 0.7 |
| Platform or emulator | not in game (builder) |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.48-dev2 (22 October 2026)._

## Status: 22 October 2026

Repaired on the v0.0.48 development line (22 October 2026): the payload preflight counts the actor library in the
layout plan. Found by the MiniWind Balmora rooms build (v0.0.48-dev2, BSP rooms), which stopped at the end of its
image step.

## Symptom

The image step's finalize stopped after about four minutes with
`The staged payload no longer matches the layout plan: DH0 payload 547531283 bytes, planned 420706413 bytes:
+144688064 bytes, more than its 100 MiB headroom`.

## Where

`tools/payload_preflight.py` `check_disk_layout` (the layout plan of the boot partition) and `tools/build_aga.py`
`finalize_image` (the actor table step, which installs the actor library stage with `actor_library.install`).

## How it happened

The payload preflight plans the disk layout from the staged files, the soundtrack and the media the image step adds
later. With the actor table on (the builder default since v0.0.47), `finalize_image` then copies the actor library
stage (`actor-library/id1/progs`: the exterior creature and NPC models, 1,047 files, 148.8 MB in this build) into the
payload, after the plan was written. The layout check before the partitions are written compares the staged payload
with the plan and allows 100 MiB either way. In this build 126.8 MB of the library was new to the payload, plus
17.9 MB that the payload sharing removed afterwards and adds back for the comparison: 144.7 MB over the plan.

## Why it was not caught

The full builds stage most of these models already (town NPCs, the NPC gallery), so the library added only about
69 MB over their plan, inside the headroom (v0.0.47-dev2: planned 1,227 MB, 1,215 MB staged after 82 MB of
sharing). A MiniWind build stages few of them, and the whole library is still installed. No test planned a payload
with the actor library.

## Reproduction

A MiniWind Balmora build with the actor table on (the default), either interior form: run
`2026_10_22_v0.0.48-dev2_miniwind-balmora-rooms-bsp_dd768704`.

## Repair

`check_disk_layout` counts every file of the actor library stage at its install path and size, over a staged file of
the same name it replaces (`actor_library_additions`). The image step passes the library only when it installs it
(`build_aga.installed_actor_library`: `--chim-actor-table on` with `--actor-library`), and the install uses the same
rule. The headroom is unchanged.

## Verification

`tests/test_layout_plan.py` `test_the_plan_counts_the_actor_library_the_image_step_installs`: a staged payload and an
actor library of 3 MiB with a 1 MiB headroom; the plan with the library equals the payload after the install (bytes
and files) and is followed, the plan without it is refused with the build's error. It fails on the code before the
repair.

## Prevention

That test. Open question, not repaired here: a MiniWind installs the whole island's actor library, most of it for
places outside its scope.

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
- [IMAGE-MEDIA-CATALOGUE-ON-DISK-46](IMAGE-MEDIA-CATALOGUE-ON-DISK-46.md): A 64 MB build report (the media catalogue) shipped on the Amiga boot disk; nothing in the game reads it
- [IMAGE-ONE-HDF-TARGET-36](IMAGE-ONE-HDF-TARGET-36.md): The game ships on two drive images and three world partitions; the project target is the whole game on one HDF
- [ROOM-RESIDENT-MODELS-SIZE-48](ROOM-RESIDENT-MODELS-SIZE-48.md): The batch rooms' resident models take 1.66 GB in about 10,800 files, more than all the rooms themselves
- [WORLD-HDF-OVER-2GIB-32](WORLD-HDF-OVER-2GIB-32.md): The world hard disk image is 32,768 bytes over 2 GiB
- [WORLD-THIRD-PARTITION-32](WORLD-THIRD-PARTITION-32.md): The world image now needs a fourth partition (DW2); launchers were only used with three

Related bugs in other categories:

- [BUILD-PARTITION-GROWTH-UNGATED-36](BUILD-PARTITION-GROWTH-UNGATED-36.md): Nothing gates the number of world partitions or the growth of the image

<!-- END GENERATED CATEGORY -->
