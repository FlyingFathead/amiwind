# Storage profiles and disk-backed preprocessing

_Last updated with AmiWind v0.0.59 (3 November 2026)._

<!-- contents start -->
## Contents

- [Compatibility profiles](#compatibility-profiles)
- [Current AGA image layout](#current-aga-image-layout)
- [Drive size and IDE cylinders](#drive-size-and-ide-cylinders)
- [The image layout gate](#the-image-layout-gate)
- [Historical v0.0.25 single-HDF layout](#historical-v0025-single-hdf-layout)
- [Preferred future content placement](#preferred-future-content-placement)
- [Historical A500 image layout](#historical-a500-image-layout)
- [Capacity budget](#capacity-budget)
- [Proposed raw asset archive](#proposed-raw-asset-archive)
- [Profiling decisions](#profiling-decisions)

<!-- contents end -->

Disk capacity is a design resource. Bake sprite directions, animation frames,
scaled variants, surface colours and simplified geometry on the PC, then load
only the active working set. Bigger images are acceptable when measurements show
less runtime computation or fewer stalls. Extra bytes alone do not accelerate
rendering. Repeated disk reads can consume CPU time and compete with audio.

## Compatibility profiles

| Profile | Intended storage | Status and limits |
| --- | --- | --- |
| Current AGA emulator baseline | Simultaneously mounted RDB HDFs, DOS1 FFS, UAE controller, A1200 KS 3.1 | v0.0.27 private builds span two HDFs. Every device stays below 4 GiB and each filesystem partition below 2 GiB; generated configurations include all required disks. |
| Historical A500 checkpoint-004 | Three 32 MiB OFS partitions, UAE controller, KS 1.3 | Earlier 1 MiB A500 prototype; not the current AGA image |
| Physical A500 candidate | Named controller/driver plus a modest boot volume and asset files | Keep the entire addressed range below 4 GiB; choose smaller volumes where the actual controller requires them. Hardware not yet validated. |
| Large UAE candidate | RDB boot partition plus separate asset area, potentially 8/16/32 GiB | Proposal only. Requires tested driver/API support for every offset used, and documented emulator version/settings. |
| Expanded Amiga alternative | A1200 or accelerator/Fast RAM with a named storage stack | Separate target; never presented as stock A500 performance. |

The classic 32-bit byte-offset device path has a 4 GiB addressing boundary.
Keep offset + length inside that range. Staying below it is necessary for that
path, but is not sufficient to establish compatibility with arbitrary old
controllers, ROMs, filesystems, geometries or transfer restrictions.

A conservative FFS planning option is partitions below 2 GiB, within a device
below 4 GiB. These are upper planning bounds, not a promise that a KS 1.3 system
supports a 3.9 GiB disk. The current AGA image uses DOS1 FFS from its owned
Kickstart 3.1 ROM; the older A500 prototype used OFS. Filesystem and driver versions must be recorded
before choosing a larger physical-machine layout.

64-bit disk extensions require capability discovery and suitable device-side
support. TD64 and the NSD 64-bit command family are distinct interfaces; do not
send either blindly. The emulator's ability to hold a huge host file does not
by itself make that file accessible through every Amiga-side driver.

## Current AGA image layout

Stable v0.0.27 private assembly uses two simultaneously mounted HDFs. The verified
build receipt supplies the complete drive list to both FS-UAE and WinUAE
configuration generation. Missing world disks stop configuration; this is not
disk swapping. Both final HDF filesystem readbacks passed. The complete static
heap gate covered 2,717 maps, but storage capacity does not add runtime heap or
certify target gameplay. See [release evidence](releases/notes/RELEASE-v0.0.27.md) and
[build output](BUILD_OUTPUT.md).

Keep each HDF below 4 GiB and each partition below 2 GiB. Measure the current
payload and allocated/free space separately; the earlier single-HDF sizes below
are historical measurements, not the size of a current v0.0.27 build.

### The boot volume seen from Workbench

The game starts by booting from the image's first partition (volume
`AMIWIND`), whose `S:startup-sequence` runs the boot check and the engine.
When someone boots their own Workbench with the AmiWind disk attached instead,
the volume carries a project icon named `AmiWind v<VERSION>` that starts the
game from Workbench (or, built with `--workbench-icon requester`, says to boot
from the disk). The engine binary itself has no icon. See
[Workbench icon](WORKBENCH_ICON.md).

## Drive size and IDE cylinders

An IDE port reads a drive's size as whole cylinders of 16 heads x 63 sectors
(1008 sectors, 516,096 bytes). Anything after the last whole cylinder is not
seen: a read there fails, and Kickstart shows the requester "has a read error
on disk block N" on the screen, which the game cannot show or answer.

What happened with v0.0.59-dev6 (3 November 2026): the drive file had 6,266,944
sectors, which IDE reads as 6217 cylinders (6,266,736 sectors). The last
partition, AW_WORLD0 (DW0), ends at sector 6,266,880, so its last 144 sectors
lay past what IDE sees. Khuul's files were stored there, and the teleport from
Ald'ruhn to Khuul stopped on that requester. It did not show earlier because the
UAE hard-file controller sees the whole file; the test sessions moved to the
emulated A1200 IDE port on 3 November. The dev5 image has the same layout and
stops the same way on IDE.

The fix: after rdbtool writes a drive, the builder pads it with zeros to whole
IDE cylinders (under 1008 sectors, under 0.5 MB per drive; nothing changes in
the game). The cylinder rule is one rule of the image layout gate (below), judged
at plan time on the padded size (the plan records it as `ide_bytes`) and again
on the written drive. See `IMAGE-IDE-CYLINDER-TAIL-59` in the bug register.

If you write an image to a CF card or an IDE drive, write the whole drive file
(its padded size) and keep the card or drive at least as large; never cut or
re-create the file at its unpadded length. The partition table (RDB) in the
image describes the partitions; the padding after the last partition is empty
and is only there so the drive's size is whole cylinders.

## The image layout gate

The image layout gate is one check that covers the whole image. It passes the
image or stops the build, naming every failing rule in one message
(`require_disk_layout` in `tools/world_volumes.py`, which the layout self-test
exercises). It runs on the plan of every drive before any partition is written,
and again on every drive as written (after the partition table is read back).
The rules:

| Rule | Limit |
| --- | --- |
| Format | The drive is an RDB; the partition table holds exactly the partitions the layout wrote (DOS1 FFS, the filesystem and every file read back first) |
| Partition size | Each partition below 2 GiB |
| Partition start | Each partition starts below 2 GiB of its drive (Kickstart 3.1 does not mount it otherwise) |
| File size | Each file below 1 GiB |
| Drive size | Each drive below 4 GiB, judged on the padded size |
| IDE cylinders | Each drive is whole cylinders of 16 heads x 63 sectors, and every partition ends inside the last whole cylinder |

The finished image is checked again where it is accepted or shipped: the master
builder's build result has an `ide-cylinders` step (`tools/ide_cylinders.py`), the
gate's boot smoke refuses a smoke image whose drive is not whole cylinders before
it boots, the Raspberry Pi image script and stick update refuse such a drive, and
the release guard checks the drives of the release image.

## Historical v0.0.25 single-HDF layout

The v0.0.25-rc1 HDF was **3,489,693,696 bytes**: two **1,664 MiB**
partitions plus a 32 KiB RDB cylinder. The payload is 2,711,140,228 bytes, with
364,228,608 bytes free on AMIWIND and 368,716,288 on AW_WORLD0. All 10,622 files
were independently read back and hashed. The refined shoreline data still fits
below the same 2 GiB partition and 4 GiB device planning bounds.

The historical v0.0.25-dev1 HDF is 3,221,258,240 bytes: two 1,536 MiB partitions plus
a 32 KiB RDB cylinder. Its payload is 2,599,581,307 bytes; independent readback
covers all 10,621 files. Native loading from the highest used disk range passed.

That island-terrain build used one RDB HDF with two FFS partitions, each below
2 GiB and the complete device below 4 GiB. The boot/save partition also carries
some terrain; the second carries the rest. The packer balances actual payload
bytes before adding filesystem/free-space allowance. There is no artificial
1 GiB cap on either partition.

Original installation size cannot determine the converted budget: overlapping
BSPs duplicate geometry, visibility and collision. The v0.0.25-dev1 lossless pass
removes 382,833,220 bytes of repeated lighting/visibility data, taking terrain from
2,220,222,432 to 1,837,389,212 bytes. The existing town/gallery/audio payload adds
about 762 MB. Both costs are measured, not inferred from the original BSA size.
See [terrain storage details](WORLD_TERRAIN.md).

Verify every file from both partitions after packing and record the actual free
space and highest used device offset. Native reads beyond the first 2 GiB are a
separate gate from ordinary host readback.

## Preferred future content placement

The maintainer's preference is to keep the main Morrowind game together on partition
1 if the measured, deduplicated payload fits. If two larger partitions are
eventually needed, use the following order of priority:

| Partition | Preferred contents |
| --- | --- |
| 1: main game and boot/save volume | Base-game exterior terrain, detailed towns, frequently visited interiors, shared resources, regularly used audio, executable, configuration and saves. |
| 2: additional content | Future Bloodmoon and Tribunal conversions, videos and other infrequently accessed assets. Move selected base-game interiors here only if capacity requires it. |

Interiors are not automatically infrequent: guilds, shops and quest hubs can be
visited repeatedly. Keep those with the main game where possible. Keep expansion
assets together because they become frequently accessed while that expansion is
being played. Store shared assets once, with explicit ownership/routing, rather
than duplicating them on both volumes. Videos still need adequate read throughput
and buffering during playback even if they are opened rarely.

This is a preferred future packing policy, not the current implementation.
For the historical v0.0.25-rc1 measurement, there were no expansion conversions;
its base-game terrain alone was
split across both volumes by measured payload size. Its combined 2,711,140,228-byte
payload cannot fit on one partition below 2 GiB. Reaching the preferred layout
therefore requires further measured reductions or selective base-game overflow.
Do not relabel the present terrain volume as an expansion partition.

Keep each partition **below 2 GiB** and the entire device **below 4 GiB**, including
RDB/alignment space. Two partitions of exactly 2 GiB plus an RDB would exceed
the classic device boundary. Budget filesystem overhead and useful free space
inside each partition as well; capacity is not all available to asset bytes.

Every partition must also **start below 2 GiB** of its device: Kickstart 3.1
(measured in FS-UAE 3.1.66) does not mount a partition whose first byte lies at
or beyond 2 GiB ("Not a DOS disk"), although partitions may end beyond it. The
image step orders each drive so every partition starts below 2 GiB (largest
partition last when needed) and refuses a written drive that breaks the rule
(BUILD-WORLD-PARTITION-MOUNT-33).

### CPU, memory and loading costs

Two partitions in one HDF share the same backing device. Partition 2 has no
inherent speed advantage, and selecting it does not require loading or swapping
an entire partition into RAM. Our plain Kickstart 3.1 baseline has no automatic
virtual-memory paging. Scene replacement is explicit engine loading and occurs
on either volume; it is distinct from operating-system swapping.

The additional filesystem handler and its buffers do consume memory, and file
lookup/read processing consumes CPU time. Buffer memory depends on filesystem
and configuration, so account for it in the existing RAM budget. There is no
measured zero-overhead claim. In the current `COM_FindFile` implementation,
`AW_WORLD0:id1` is appended after the primary search paths: a file on partition
2 incurs failed earlier lookups before it is opened there. Subsequent reads use
that open handle; they do not search both volumes for every byte or frame.

Future content packing should pair an asset-to-volume index with direct routing
so second-volume assets avoid unnecessary failed lookups. This routing is not
implemented yet. Group assets used together and measure actual read patterns;
the partition number alone is not a performance optimization. On a physical
rotating disk, placement can also affect seek distance; one emulated HDF does
not provide two independent storage channels.

Before claiming a performance benefit, compare identical assets and routes with
the same ROM, CPU, RAM and filesystem-buffer settings. Record cold/warm load
times, failed lookups, read bytes, CPU/frame stalls, free memory and audio refill
failures. The current high-offset native test proves correct access to partition
2, not a speed advantage or a comparative performance result.

## Historical A500 image layout

The checkpoint-004 image is 100,696,064 bytes (96 MiB plus one 32 KiB RDB
cylinder). `MWBOOT:` contains the executable/startup file and the first music
files; `MWMUSIC1:` and `MWMUSIC2:` contain the rest. A conservative sequential
packer leaves spare space within each 32 MiB OFS partition. Volume-qualified
paths make the playlist independent of the shell's current directory.

A single 64 MiB OFS image read successfully in checkpoint-003, but a later native
write test produced a volume-not-validated requester. The smaller RDB partitions
were introduced to avoid that observed case; its precise root cause has not
been established. The current boot partition has passed native file creation,
write and host readback under the recorded KS 1.3 setup. This does not validate
all controllers or every possible filesystem operation. Allow filesystem buffers
to flush before stopping an emulator; the test harness waits at least ten seconds.

## Capacity budget

The maintainer's roughly 1.2 GB original installation fits inside a 2 GiB planning
budget. This is not a requirement to carry all original files onto the Amiga.
Converted sprite directions, animations and scale variants can exceed the source
size; streamable PCM can also be larger than MP3. Budget the converted runtime
set and its index/cache metadata, rather than inferring capacity from BSA size.
The complete base Music conversion currently occupies about 56 MB.

## Proposed raw asset archive

A future RDB image could contain a small boot/save filesystem partition and a
separate, explicitly reserved read-only raw asset partition. A PC-built index
would map asset IDs to aligned extents, lengths, formats and checksums. This
could avoid repeated filesystem block processing and improve batching.

The runtime must query the configured device/unit, enforce archive and device
bounds, and use only supported commands. Raw access does not bypass 32-bit
offsets. Never append unreserved data to filesystem free space or overlap the
boot/save partition. A single indexed archive inside the filesystem is the
simpler comparison implementation before adding raw device support.

This layout is not implemented. There is no reason to allocate multi-gigabyte
images until baked assets or a controlled throughput experiment require them.

## Profiling decisions

Compare identical routes, audio, ROM and CPU/memory settings. Record read sizes,
read-latency distribution, rendering/frame intervals, starvation count, bytes
read and memory use. Distinguish emulated driver/CPU cost from physical disk
latency. Test file boundaries, track changes, missing/truncated data and escape
while I/O is pending. Prefer the measured winner, not the largest image.

Audio has refill priority. Cache nearby world chunks and likely sprite variants;
prepare them before the camera can expose them. Fog bounds rendering demand but
does not remove the need for surrounding data or cover arbitrary storage stalls.

References: [AmigaOS 64-bit disk standard](https://wiki.amigaos.net/wiki/TrackDisk64_Standard),
[Cloanto on host filesystems and hardfiles](https://www.amigaforever.com/kb/13-156),
[AmigaDOS filesystem buffers](https://developer.amigaos3.net/autodocs/dos.library/AddBuffers.html),
and [Exec memory allocation](https://wiki.amigaos.net/wiki/Exec_Memory_Allocation)
(its pre-4.0 comparison applies to our baseline; its OS4 paging APIs do not).
