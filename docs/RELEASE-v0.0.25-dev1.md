# AmiWind v0.0.25-dev1 — terrain and interface fixes

Development continuation of v0.0.24. Historical release archives remain unchanged.

- Centre journal headings within the left page; wrap headings and quest-index
  labels completely. Body pagination accounts for the heading height. Replace
  the main README journal image with a genuine corrected native capture.
- Restore unassigned J/M bindings after older saved configuration loads, while
  preserving custom bindings. J opens the journal; M opens the map.
- Enable the exact-model polygon allowance by default, with a one-time migration
  for older configurations. Dagoth Ur's 903-triangle gallery model retains its
  byte checks and the overall 1,024-triangle ceiling.
- Wheel down/up cycles gallery models; middle-click opens/closes the browser.
  Browser scrolling remains available. The current FS-UAE profile delivers the
  middle button to the game; F12+G releases input capture.
- Repair the isolated Balmora ground tile at the reported
  `2663,-1107,211 / 14 / 27`, using the surrounding dirt-road texture in all
  affected region copies. Geometry and collision are unchanged by that repair.
- Compile 2,526 terrain/water regions using the recovered polymap and subdivision
  estimates. Preserve **both detailed Seyda Neen and Balmora**, their NPCs and
  their converted interiors. Rebase local coordinates at terrain/town crossings;
  include the new region identities and content in saves and the map marker.

Outside those two towns the new content is terrain and water. Other scenery,
settlements and actors have not been converted in this pass. Scene changes still
load and can pause. See [terrain layout and rebuilds](WORLD_TERRAIN.md).

## Validation

- 329 source checks: 325 passed; four optional-dependency cases skipped.
  The available external QBSP case ran through the full suite.
- Fresh 68040 runtime/preflight build; all 201 runtime source files match its
  receipt. The build emitted 82 warnings, with no new signatures against the
  immediately preceding development build. Existing warnings remain visible.
- All 10,621 payload files independently read back and hashed from the final HDF.
- Native FS-UAE checks: corrected journal; exact Balmora repair viewpoint;
  Dagoth Ur with the default allowance; town/terrain crossings in both directions
  for both towns; ordinary walking across `vf0709`/`vf0790` and back; loading the
  largest-face and largest-clipnode terrain regions. Both route runs reported
  zero renderer surface/edge overflow frames.
- The single HDF is 3,221,258,240 bytes: two 1,536 MiB DOS1 FFS partitions plus
  the 32 KiB RDB cylinder. Total payload is 2,599,581,307 bytes. Free filesystem
  space is 286,693,888 bytes on `AMIWIND` and 290,965,504 on `AW_WORLD0`.
- A disposable writable copy booted from the HDF, loaded terrain `vf1839` from
  `AW_WORLD0:` at the highest used disk range, then saved and restored the character
  in terrain reached through the normal town transition,
  and exited cleanly. The delivered HDF hash remained unchanged.
- Lossless BSP sharing removed 382,833,220 bytes (17.24%) from the terrain data.
  See [storage measurements](WORLD_TERRAIN.md) and [Amiga limitations](RELEASE_WORKFLOW.md#amiga-limitations).

Native runs use Linux FS-UAE 3.1.66, A1200/AGA/PAL, 68040/FPU/JIT, 2 MiB Chip,
16 MiB Z3 and an 11 MiB heap. Audio used a null sink; no listening-quality claim.
Raw captures, commands, logs and exact file hashes accompany the private package.
The tests cover these routes and views, not every region or slope on the island.

The existing **23 strict NPC ground-contact findings remain unresolved**. The
normal production image builder and its audit are unchanged. This development
playable is not a passed production release or a complete-island walking
certification. No new claim is made for physical Amiga or Windows/WSL execution.
