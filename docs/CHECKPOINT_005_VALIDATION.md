# AmiWind v0.0.6 / checkpoint-005 validation

Tested 27 September 2026. Source release 0.7.0. This checkpoint changes playlist
selection and adds host scenery conversion. The native renderer remains the
A500 terrain renderer; no expanded-Amiga or native-scene performance is claimed.

## Build and baseline

- vasm 1.9d; M68k backend 2.6a; Motorola syntax 3.17a; hunk backend 2.14c.
  Arguments: `-m68000 -Fhunkexe -kick1hunks -nosym`.
- Assembler executable SHA-256:
  `0c0a04ff4a3e213f98498c25988d9a2ec292d3a32590a810b5fde5f042fbb2ae`.
- amitools 0.8.1; Python 3.12; original music converted using FFmpeg.
- FS-UAE 3.1.66, Ubuntu amd64 package 3.1.66-2build2. Executable SHA-256:
  `b729fe233a6507daed7fea6fbe8cfc417da523239d4a43037dd57203858e4f37`.
- PAL A500, 68000 at real speed, OCS, 512 KiB Chip + 512 KiB slow RAM, no
  Fast/Z3/RTG RAM or JIT. CPU, memory and blitter cycle-exact on; immediate blits
  off. Effective UAE values were checked, not just requested in the launcher.
- Kickstart 1.3 revision 34.5, 262144 bytes, SHA-256:
  `ee05862d8102a08436ac4056da7d549db31625c7d47b24dfb7b3c9a5c113ca53`.
  See OPENING_VALIDATION.md for original member, CRC and the separate doubled
  ROM variant. No new ROM was required for this demo.
- UAE RDB hardfile, 3073 cylinders / 1 head / 64 sectors, 512-byte blocks,
  three 32 MiB OFS partitions. Tests run on copies, preserving the release image.
- Host window 640x512, video sync off; OpenAL stereo float capture at 48 kHz.

The released HDF is 100696064 bytes, SHA-256:
`f6624aa750fda6365f70397c42a27259f6ebe940d394e9f2ddb3f942311e25c8`.
The executable SHA-256 is:
`25580961051f2f117fe00b2347a4d257ab93685112e3f572e22677fa8baba6d7`.
Chip hunks use 202852 bytes and all hunks 276984 bytes across 14 segments;
OS/stack/filesystem overhead is additional. Audio buffers remain 49152 bytes.

## Native checks

The released executable is checked through startup, walking, the complete title
track reaching EOF, exploration F6/F7 selection, F8 battle audition, a full battle
cycle, return to exploration, fog changes and Escape. Native profile and track
trace writes are read back after allowing filesystem flush time.

Final run: 1316 presented solid frames / 10362 PAL ticks =
**6.3501 fps**, including manual song changes and fog changes.
20 successful track opens, **zero reported starvations or read errors**.
The first automatic successor differs from the title, no canonical track repeats
consecutively, and special cues are absent. Maximum frame interval was
1800 ms, including blocking manual switches; maximum refill interval was
560 ms. This is a mixed interaction check, not a matched renderer benchmark.
The loading banner and opening version both come from `DEMO_VERSION`.

A targeted automatic-EOF stress test used the preceding pre-banner candidate
with identical playlist code. Only its *working HDF copy* replaced music files
with four complete valid blocks each. It opened 25 tracks, consumed three full
eight-song exploration bags, and had no consecutive duplicate identities,
special/battle tracks, reported audio starvation or read errors. Release tracks
are full-length and were never replaced by these short test fixtures.

The canonical title and duplicate source map to track 0; track 1 is never selected.
The no-repeat guard is by converted content identity, not filename. F8 remains
a manual test control; no combat state or game event is inferred from it.

## Host and asset checks

All 33 host tests pass using synthetic, non-game fixtures. Checks cover geometry
index/length validation, archive extent/hash validation, shared residency,
bounds crossing a query edge, door destinations, playlist aliases, audio channel
layout/padding, existing terrain formats and public release policy.

The scenery exporter processed 74 original NIF models and 62 textures into
272 references without errors. It retains 24 door references, including 21
with destinations. Every payload was read independently from the indexed archive
and SHA-256 checked. The host turntable was visually inspected for an original
tree and shack; it is not a screenshot of native Amiga scenery.

Opening stills were rebuilt from checkpoint-004's privately converted PNGs,
with regenerated captions. No fresh OpenMW capture was performed in this
checkpoint. Converted opening artwork may have minor palette changes from that
second quantization. Geometry, textures, music and ROM remain private.

Physical storage/controllers, WinUAE execution, NTSC, expanded hardware, native
static-object rendering and gameplay are untested in this release. The owner
reports good music streaming on their own earlier build; that is separate from
these FS-UAE checks. Manual song switches still block during open/preload.
