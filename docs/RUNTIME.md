# Runtime component status

`runtime/include/terrain_packet.h` and `runtime/src/terrain_packet.c` implement
an allocation-free decoder for the experimental MWT0 terrain packets. They use
explicit byte reads, so input alignment and host endianness do not affect parsing.
Signed height and negative chunk-coordinate conversion are explicit.

`mwad_terrain_open` validates the magic, version, dimensions, payload size and
zero padding before returning a view into the caller-owned buffer. It returns
zero on failure and leaves the output view unusable. Accessor functions require
a successful open. The input buffer must remain valid while its view is in use.

The C reader is checked on the host against packets produced by Python at all
four grid strides, including unaligned data, negative coordinates, truncation
and corruption. It has not been cross-compiled or run on a 68000 in this version.

`runtime/src/opening.asm` is a separate 68000/OCS opening runtime. It takes over
the display after loading, uses Chip-resident bitplanes and PCM, changes scenes
by updating copper pointers, fades palettes and restores AmigaDOS on exit.
`tools/build_opening.py` generates its assets, executable, ADF and HDF externally.
`runtime/src/walking.asm` adds a bounded wireframe camera over a generated 33x33
lattice. It polls the keyboard with CIA acknowledgement, reads relative mouse
counters, uses fixed-point transforms and clips pixel writes to a one-plane
viewport. The blitter copies the HUD while the CPU projects; the CPU draws lines.
The CIA vertical-event counter drives elapsed movement/audio timing, with a
50-tick cap per update. Keyboard and mouse latency still depend on render time.
It does not yet use the C terrain reader or issue disk reads after loading.
See OPENING_DEMO.md for controls and rendering limits.

ROMs, game content, compilers and emulator installations are not shipped with
this source. A user-authorized private bundle can include the user's ROM.

`runtime/src/solid.asm` adds front-to-back filled heightfield columns, a per-column
occlusion boundary, distance fog and the exit timing report. The blitter fills
long spans; the CPU handles short spans and terrain sampling. All visible
buffers stay in Chip RAM. See FILLED_TERRAIN.md for budgets and approximations.
