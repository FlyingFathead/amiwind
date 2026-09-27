# Morrowind demo v0.0.6 — checkpoint-005

A native opening study for an A500 with 512 KiB Chip plus 512 KiB expansion RAM,
Kickstart 1.3 and OCS. Source release: 0.7.0. Both version numbers are recorded
because the host pipeline existed before the first native opening demo.

The boot console prints `Loading AmiWind v<demo version>...`; the builder also
places the same version on the opening image. Keep this generated from
`DEMO_VERSION` for every checkpoint.

## What runs

Two 320x200, 16-colour stills captured from the owner's Morrowind installation
through OpenMW: the ship deck and a Seyda Neen street. The native runtime fades
in the image, streams complete stereo music tracks and plays a short
original voice cue after two seconds. The voice is centred and ducks the music.

- Left mouse: next view. Click once to capture the mouse in the emulator first.
- Right mouse: exit and restore the AmigaDOS display.
- Enter: leave the opening and enter the filled terrain walk.
- Walking: W/S forward/back, A/D strafe, mouse yaw/pitch, left Shift run.
- Tab: filled/wireframe. Keys 1/2/3: dense, medium or longer fog distance.
- F6/F7: next/previous song in the active group; EOF uses a shuffled bag.
- F8: battle/exploration audition. This is a test control, not combat detection.
- Escape: exit to AmigaDOS from either mode and print frame/streaming counters.
- Jump, activation, inventory, combat and NPC animation are not implemented.

The opening displays prepared bitplanes. Walking uses a filled 97x97 heightfield
with dense fog and colours baked from the original terrain textures. Tab switches
to wireframe; 1/2/3 select fog distance. The starting camera is ashore near Seyda
Neen's street location. Geometry, images and the voice cue are preloaded; music is streamed.

See FILLED_TERRAIN.md for the renderer, host baking, distance settings and limits.
Escape prints solid/wire frame counts and average presentation rates. Restart
between comparisons and keep the same fog preset and movement route.

## Run the private build

Mount `MorrowindDemo-v0.0.6.hdf` as an RDB/full-drive hardfile using UAE's
virtual hard-drive controller. The image is approximately 96 MiB and contains
three 32 MiB OFS partitions, all installed music tracks and a bootable DH0.
Use RDB autodetection; the previous plain-partition geometry no longer applies.
There is no ADF for this HDD-streaming checkpoint.

Use a stock-speed A500/68000, OCS, PAL, 512 KiB Chip and 512 KiB slow expansion
RAM, with no Fast RAM or JIT. Use the owner's supplied Kickstart 1.3 identified
in OPENING_VALIDATION.md. The private bundle may contain that ROM only when
explicitly requested by its owner. The public source archive never includes it.

The standalone `MorrowindDemo` executable can also be launched from AmigaDOS.
Music uses volume-qualified paths recorded in `music-assets.i`. When copying to
another installation, preserve `MWBOOT:`, `MWMUSIC1:` and `MWMUSIC2:` as volume
names or assigns, with their respective `music/` files. On physical hardware,
an HDF still needs a compatible storage interface/image solution; no physical
A500 controller has been validated. The earlier checkpoint-002 ADF remains an
immutable preloaded fallback.

Escape writes `MWBOOT:MWPROFILE.BIN` and the first 64 opened track IDs to
`MWBOOT:MWMUSIC.BIN`. Wait at least ten seconds at the DOS prompt
before shutting down the emulator, allowing filesystem metadata to reach disk.
The current image's boot partition has passed native write/readback validation.

## Rebuild on a PC

Requirements: Python 3.10+, Pillow 9.1+, FFmpeg, amitools 0.8.1 (`xdftool` and `rdbtool`) and a
vasm m68k/Motorola assembler. The tested assembler is vasm 1.9d. A newer vasm is
not automatically validated. Compilers and emulator binaries are not bundled.

Run the normal `tools/mwad.py setup` and `convert` against your original game
folder first. The walk expects the default nine-cell Seyda Neen terrain export.
For existing OpenMW screenshots, supply one to three external PNGs:

```sh
python tools/build_opening.py --workspace ../morrowind-amiga-workspace --out ../morrowind-amiga-workspace/build/my-opening --scene /path/to/ship.png --scene /path/to/street.png
```

The build converts all MP3 files under the installed Music directory and the
base-game character-generation captain voice file. Override `--voice` if needed;
its path is relative to Data Files. Music conversion preserves whole tracks.
Pass `--vasm`, `--ffmpeg` `--xdftool` or `--rdbtool` for tools outside PATH. Output directories
must be new and outside the source repository. The builder checks hunk memory
budgets and reads the executable/startup file back from each generated image.

## Optional OpenMW capture automation

On an X11 Linux desktop, OpenMW 0.48.0 and xdotool can make the two stills:

```sh
python tools/capture_opening.py --workspace ../morrowind-amiga-workspace --out ../morrowind-amiga-workspace/build/captured-opening
```

This opens and controls its own OpenMW window. Leave it focused while capturing.
It uses the stock console/F12 bindings and original base-game content. Inspect
`scene-0.png` and `scene-1.png` before building: loading time, window focus and
NPC positions can vary. `--settle-seconds` adjusts the initial loading delay.
Windows users can take F12 screenshots manually and use the same build command.
This is exterior still capture, not the deterministic character-animation baker.

## Storage and profiling

The builder packs converted music into small OFS partitions in one RDB image,
then reads back every track, executable and startup file and checks their hashes.
`soundtrack.json` records source and converted hashes/durations.

Three queued stereo blocks keep 48 KiB resident; each plays about 0.744 seconds.
The default `--stream-mode async4k` schedules four 4 KiB DOS packet reads per
16 KiB refill, allowing rendering between completions. Alternatives are `sync`
(blocking 16 KiB), `async` (one async 16 KiB) and `async8k` (two 8 KiB requests).
Initial preload and track/header changes still use blocking DOS calls.

See [profiling workflow](PROFILING.md) for matched benchmarks and the measured
trade-off, [audio design](AUDIO.md), [storage options](STORAGE.md) and
[roadmap](ROADMAP.md). The scheduler balances audio deadlines and frame pacing; the terrain renderer
and visible scenery remain the same as checkpoint-002.
