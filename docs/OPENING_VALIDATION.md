# Demo v0.0.5 / checkpoint-004 validation

Test date: 27 September 2026, Europe/Helsinki. Source release 0.6.0.
Interactive build uses the corrected async4k scheduler. Prior releases are immutable.

## ROM identity (metadata only)

| Field | Value |
| --- | --- |
| Build-validation ROM | Kickstart 1.3 revision 34.5, A500/A1000/A2000 |
| Original member | `Kickstart v1.3 r34.005 (1987-12)(Commodore)(A500-A1000-A2000-CDTV)[!].rom` |
| Private filename | `kickstart-1.3-a500.rom` |
| Bytes | 262,144 |
| SHA-256 | `ee05862d8102a08436ac4056da7d549db31625c7d47b24dfb7b3c9a5c113ca53` |
| CRC32 | `c4f0f55f` |
| End-around ROM checksum | `ffffffff` |

The owner also reported that the `[o]` variant works in their setup. Its uploaded
`kick34005.A500` member is 524,288 bytes, exactly two copies of the 256 KiB ROM
above. Its SHA-256 is
`1d68ba18412501d2a4b307a0a632b94a50b839c2c7c5ff2df6de2c38b99a921f`.
That is a user-reported result plus a byte comparison, not a second emulator run
in this build's validation. Other uploaded ROM collections were not needed.

Public source/docs contain these identifiers only. ROM bytes are excluded from
the source ZIP. The owner explicitly requested the tested ROM in the private
package; it is included there alone.

## Emulator and effective settings

FS-UAE **3.1.66**, Ubuntu amd64 package **3.1.66-2build2**, running on Linux.
The effective UAE configuration is included with private validation evidence.

| Setting | Value |
| --- | --- |
| Machine | A500 |
| CPU | 68000, `cpu_speed=real`, compatible mode, 24-bit addressing |
| Timing | CPU, CPU memory and blitter cycle-exact enabled |
| Chipset / television | OCS / PAL; NTSC not tested |
| Chip RAM | 512 KiB (`chipmem_size=1`, UAE encoded value) |
| Slow expansion RAM | 512 KiB (`bogomem_size=2`, units of 256 KiB) |
| Fast/Z3/RTG RAM | None |
| JIT / immediate blits | None / false |
| HDF | UAE controller; RDB, 3073 cylinders / 1 head / 64 sectors, 512-byte blocks; three 32 MiB OFS partitions |
| Display | 640x512 host window, windowed, video synchronization off |
| Audio observation | OpenAL wave output, 48 kHz stereo float capture |

The image uses UAE's virtual controller. Physical drive/controller latency and
bandwidth remain unmeasured. WinUAE itself was not run for this release.

## Results

- vasm 1.8g, M68k backend 2.3f, Motorola syntax 3.13;
  `-m68000 -Fhunkexe -kick1hunks -nosym`.
- A 100,696,064-byte RDB HDF contains three 32 MiB OFS partitions, all 18 installed
  Music files and the bootable demo. Tracks are converted in full to nominal
  11,015 Hz stereo signed 8-bit PCM. Independent MWA1 decoding and filesystem
  readback verified every converted track. No runtime MP3 decoding.
- Matched initial strategy tests are recorded in PROFILING.md. The initial
  per-frame 4 KiB scheduler passed the fixed scene but reported 14 starvations
  in the longer moving/fog run. This prompted cooperative audio service during
  long rendering passes; that failed candidate is not the released build.
- Corrected scheduler, stationary dense-fog 30-second benchmark: 220 frames /
  1504 PAL ticks = **7.3138 fps**. Median frame 100 ms, p95 240 ms, p99 280 ms,
  maximum 300 ms. 43 complete refills, maximum refill 19 ticks (380 ms),
  zero reported starvations/errors. Async refill intervals include rendering
  and polling between requests; they are not isolated disk-handler CPU costs.
- Boot-partition native file creation/write and stopped-image readback passed.
  The MWP1 result contains all 832 bytes with internally consistent histograms.
  Tests allow at least ten seconds after returning to DOS for buffered writes.
- Missing-file and truncated-file benchmark injections each recorded one error,
  kept rendering and auto-exited to DOS. The missing-file case completed 300
  frames / 1500 ticks; the truncated case completed 294 / 1500. These fault
  injections preceded the rendering-service correction; the later interactive
  truncated-file recovery test exercises that corrected build separately.
- Chip hunks: **202,852 bytes**; total executable hunks: **275,860 bytes**, 14
  segments. This excludes OS, stack, loader and filesystem memory. Music buffers
  remain 49,152 bytes. No extra Chip/Fast RAM was added to pass the test.
- All **28 host tests** passed, including synthetic conversion, packet, stream,
  profile and source-release checks. Test fixtures include no original assets.

Interactive recovery with the corrected build: truncate the first track after
three complete blocks plus 100 bytes, then enter walking, exercise WASD/Shift,
mouse and Tab, and press F6. The run recorded exactly one read error, opened the
next track, completed eight reads and returned to DOS with a valid 832-byte
profile. Zero starvations were reported. Music stopped safely at the bad data
and track selection recovered it. The higher frame rate while music was stopped
is not a normal-streaming performance result.

The corrected sustained replay crossed the full title-track boundary, exercised
18 next selections and one previous selection across all three partitions, then
ran both longer fog presets. It recorded **332 complete refills, 21 track opens,
zero starvations and zero errors**. Maximum complete refill: 25 PAL ticks
(500 ms). The combined movement/track-switch/fog run presented 1461 solid frames
in 10,932 ticks = **6.6822 fps**. Its worst frame was 1.6 seconds; this includes
blocking track selection and is not the steady-state benchmark. Escape restored
the DOS prompt and the profile was read back successfully from the working HDF.

Captured output is nonzero stereo. Hardware channel allocation still follows
the Commodore manual (0/3 right, 1/2 left); the earlier OpenAL capture channel
order appeared reversed. Physical channel wiring and subjective audio quality
remain untested.
No buildings/trees, collision or effects were added in this checkpoint. The full
installed music is present, but the validation does not claim 42 minutes of
uninterrupted listening, physical-HDD performance, WinUAE testing or A1200 testing.

## Host tools and evidence

OpenMW 0.48.0 / OSG 3.6.5 rendered the opening stills on the host. FFmpeg converts
music and voice; OpenMW and Hunter code are not included in the native runtime.
The private package includes selected screenshots, effective UAE configuration,
ROM identity, executable/disk hashes, conversion manifest and test counts.
