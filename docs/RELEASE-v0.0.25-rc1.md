# AmiWind v0.0.25-rc1 — terrain, shorelines and navigation

**Source reconciliation:** see [RECONCILE-v0.0.25-rc1.md](RECONCILE-v0.0.25-rc1.md). Earlier native results describe the original candidate, not the merged runtime.

Release candidate following the owner's v0.0.25-dev1 regression report. This is
**rc1**, not v0.0.25 final; previous archives and tags remain unchanged.

- Seyda Neen's handoff now lies inside its ground coverage. The former boundary
  came from the larger sea/enclosure bounds, leaving a gap before terrain loading.
  Preserve **detailed Seyda Neen AND Balmora**, their interiors and actors.
- Keep the recovered polygon survey's 1,404 cells and 2,526 divisions. Refine
  shoreline triangles at original samples where coarse conversion changed dry
  land into submerged terrain. Keep the source sea datum at zero; correct
  ocean-only enclosure ceilings and replace flat default-land/water swatches
  with original textures in the existing palette.
- Show GLOBAL source XYZ and LOCAL scene XYZ in compact console-font rows,
  retaining heading/pitch. `aw_pos` includes scene identity and source cell.
  A normal-view compass is visible without debug mode.
- Refresh the M player cross from the simulated source position. Keep zoom/pan
  when reopening the map and show source XYZ in its header. P centres the player.
- Protect M/N before the Amiga system's screen-shortcut handler, including
  console typing. Debug Alt+M deliberately shows the desktop. Ctrl debug noclip
  flight is twice Shift speed, without an extra diagonal or Ctrl+Shift multiplier.
- Put bindings in their own editable configuration, with a maintained
  [key and command list](KEYMAPS.md). Settings remain in `config.cfg`.
- Record unexplored-map masking as a TODO; do not implement it in this candidate.

## Verification

- 332 source checks: 328 passed; four optional-dependency cases skipped. The
  external QBSP fixture ran. Fresh 68040 runtime/preflight compilation emitted
  78 warnings, down from 82, with no new warning signatures. Three key-event
  format arguments now have the required type, and the FPS buffer is large
  enough. The 78 retained warnings remain work, not a warning-clean claim.
- The original-height audit found 10,282 dry samples submerged by the coarse
  dev1 mesh. The corrected mesh has zero wet/dry mismatches in 321,775 checks
  across all 12,871 refined source tiles. Unchanged tiles retain their original
  classification. This does not reconstruct all terrain between the samples.
- Native raw input verifies M opens the map, console input receives `nm`, debug
  Alt+M sends the screen back, and the normal system shortcut brings it forward.
  This includes injected Left Amiga qualifiers on M/N, reproducing the system
  shortcut path that must be blocked while the game is in front.
- Native ordinary walking passes Seyda Neen -> `vf0847` -> Seyda Neen, plus
  three Balmora -> `vf0864` -> Balmora routes. The largest new terrain BSP loads
  successfully. These runs report zero renderer surface/edge overflow frames.
- All 2,526 BSPs match their conversion hashes and original region plan. All
  385,326 compiled horizontal water faces have global Z=0. Every surveyed LAND
  cell belongs to the same connected footprint; the isolated extra survey cell
  has no LAND. Terrain-only data is 1,948,944,656 bytes after lossless sharing.
- The final HDF has two 1,664 MiB DOS1 FFS partitions in one 3,489,693,696-byte
  device. All 10,622 payload files passed independent readback and hashes.
  A disposable native copy loads `vf1953` from the highest used second-partition
  range, walks from Seyda into terrain, saves/restores successfully, and writes
  bindings to `keymaps.cfg` separately from settings. The delivered HDF is unchanged.
- Normal-view compass, paired coordinate rows and movement of the map's white
  player cross were checked in native captures. Retained conversion warnings and
  their follow-up are listed in [WORLD_TERRAIN.md](WORLD_TERRAIN.md).

## Scope and remaining work

Outside the two detailed towns, this pass contains terrain and water. Other
settlements, scenery and actors remain unconverted. Loading is still synchronous.
The original waterline is not derived from a Seyda-only plane, and the available
source data does not justify a curvature correction. The reported local
`9,484,102 / 298 / 50` camera lacks its terrain region ID, so it cannot be matched
uniquely; record GLOBAL/LOCAL coordinates or `aw_pos` for any remaining pit.

The **23 existing strict NPC contact findings remain unresolved**. The normal
production image gate still fails on them; this candidate does not claim
production acceptance. Older saves with a different content fingerprint are
rejected. Start a new candidate character. Physical Amiga, Windows/WSL, complete
island routes and subjective audio quality require separate validation.

Native checks use Linux FS-UAE 3.1.66, A1200/AGA/PAL, 68040/FPU/JIT, 2 MiB Chip,
16 MiB Z3 and the existing 11 MiB heap. No expansion content is included.
