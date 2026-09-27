# Storage profiles and disk-backed preprocessing

Disk capacity is a design resource. Bake sprite directions, animation frames,
scaled variants, surface colours and simplified geometry on the PC, then load
only the active working set. Bigger images are acceptable when measurements show
less runtime computation or fewer stalls. Extra bytes alone do not accelerate
rendering. Repeated disk reads can consume CPU time and compete with audio.

## Compatibility profiles

| Profile | Intended storage | Status and limits |
| --- | --- | --- |
| Current emulator baseline | RDB HDF with three 32 MiB OFS partitions, UAE controller, KS 1.3 | Complete installed OST, 1 MiB A500 configuration; per-build validation required |
| Physical A500 candidate | Named controller/driver plus a modest boot volume and asset files | Keep the entire addressed range below 4 GiB; choose smaller volumes where the actual controller requires them. Hardware not yet validated. |
| Large UAE candidate | RDB boot partition plus separate asset area, potentially 8/16/32 GiB | Proposal only. Requires tested driver/API support for every offset used, and documented emulator version/settings. |
| Expanded Amiga alternative | A1200 or accelerator/Fast RAM with a named storage stack | Separate target; never presented as stock A500 performance. |

The classic 32-bit byte-offset device path has a 4 GiB addressing boundary.
Keep offset + length inside that range. Staying below it is necessary for that
path, but is not sufficient to establish compatibility with arbitrary old
controllers, ROMs, filesystems, geometries or transfer restrictions.

A conservative FFS planning option is partitions below 2 GiB, within a device
below 4 GiB. These are upper planning bounds, not a promise that a KS 1.3 system
supports a 3.9 GiB disk. The current image uses OFS, not FFS, and bundles no
proprietary filesystem binary. Filesystem and driver versions must be recorded
before choosing a larger physical-machine layout.

64-bit disk extensions require capability discovery and suitable device-side
support. TD64 and the NSD 64-bit command family are distinct interfaces; do not
send either blindly. The emulator's ability to hold a huge host file does not
by itself make that file accessible through every Amiga-side driver.

## Current image layout

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

The owner's approximately 792 MB installation fits inside a 2 GiB planning
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
[Cloanto on host filesystems and hardfiles](https://www.amigaforever.com/kb/13-156).
