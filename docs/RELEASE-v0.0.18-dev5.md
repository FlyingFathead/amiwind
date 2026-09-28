# v0.0.18-dev5 — menus, loading and entrance discovery

This checkpoint implements the latest UI/playtest requests and prepares the town
entrances for interior conversion. It does not complete character creation or
make the town interiors playable.

## Changes

- Restore the original main-menu artwork without the added project logo. Show
  AmiWind and its version at bottom right in the Morrowind font. New Game asks
  for confirmation, defaulting to Cancel, from both main and pause menus.
- Center the simplified project wordmark/rule in the Esc menu. Use common row
  geometry for labels, highlights and mouse clicks; request a full-screen redraw
  so the lower menu/footer cannot retain stale pixels. Disabled Save/Load stay
  unavailable. The original logo and all font fallbacks remain in source.
- Render the startup fade directly at 320×200 with a large wordmark and native
  font tagline. Stream the prophecy at 320×200/10fps; retain 160×100 support and
  `--low-res`. Three private native-font text cards replace unreadable burned-in
  lettering. Narration remains unchanged and Esc skips to Jiub. See INTRO_VIDEO.md.
- Convert and cycle the 11 original supplied Splash images, keeping only one
  64KB image resident. Missing Splash artwork falls back to the original menu.
  Hide the forced Quake console during loading/sign-on by default. Archived
  `aw_transition_console 1` restores the old forced console for diagnostics;
  `0` is default. F10 still explicitly opens the unchanged console.
- Default debug overlays to off; `dbg overlay on` restores them. The separate
  disk indicator remains off. This does not change camera height, FOV or maps.
- Restore the deck guard's original first greeting and nearby reminder cycle,
  using the converted voice clips and existing speech-driven facial poses.
  Rebind actors on map changes and extend body collision to that guard.
- Expose 22 entrance references with original destination labels and E prompts.
  The two ship transitions work. Attempting an unbuilt interior displays
  “Interior not found.” and leaves the player in place. Preserve the full
  41-link catalogue and private 14-cell interior object/layout reference.
- Default native compiler jobs to available CPU capacity, including affinity and
  container quota. `-j N`, `--jobs N`, `--j N`, `--jobs auto` and `--single-thread`
  are supported. Apply the limit to VIS/LIGHT; pinned QBSP stays serial. Ordered
  Python conversion stages and FFmpeg's own threading are unchanged.

## Scope and validation

179 host tests pass, including menu hit regions/confirmation, missing-interior
activation preserving state, job propagation, both movie dimensions and exact
movie-card ink colors. The 68040/FPU executable builds with eight automatically
selected jobs in this environment. The HDF builder independently reads back and
hashes every payload file. Native FS-UAE captures and logs are in the private
checkpoint; exact exercised paths are recorded in its handoff.

The world maps and camera settings retain dev4 bytes. The 9MiB game heap and
16MiB Fast RAM preset remain. The higher-resolution movie increases disk traffic
from about 171kB/s to 651kB/s and the fixed frame buffer from 16KB to 64KB; original
loading artwork adds one 64KB resident buffer. Physical Amiga throughput, WinUAE
and subjective audio playback were not certified by these emulator checks.

Census/dock registration, remaining interiors, day/night/waiting, full dialogue,
general town collision/combat and the recalled pier escape restriction remain
open. Research the original restriction mechanism before adding a boundary.
The title track is confirmed from owned data; the previously selected ship
track 04 is retained without claiming original cue-order parity.

## Checkpoints and publication

The complete public source includes the accumulated prior checkpoints. Use it
when updating an older GitHub checkout. The incremental ZIP requires exact dev4
source and includes its baseline receipt. Both contain source and project media
only. The private playable includes owned game/ROM assets and must stay private.
The owner runs commit/tag/push/release commands supplied in the separate handoff.
