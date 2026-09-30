# v0.0.24-dev4 — Seyda Neen sub-cells and opening follow-up

30 September 2026. Delivered dev3 archives remain unchanged.

## Commands and menu

During play, `dbg tp` or `dbg tp menu` opens the existing destination picker.
Direct shortcuts include:

```text
dbg tp balmora
dbg tp seydaneen
dbg tp prisonship
dbg tp census
dbg tp tradehouse
dbg tp lighthouse
dbg tp addamasartus
```

All 17 converted logical scene names work, case-insensitively; `town`, `seyda`
and `ship` aliases remain. `debug` and `amiwind debug` prefixes also work.
The older `dbg scene change` and `dbg scene <destination>` commands remain valid.
This is a debug shortcut accessed through the console, not a new normal travel
service or pause-menu button. It can bypass the intended opening route.

The picker already existed. The short `tp` spelling and `seydaneen`/`prisonship`
names are new. Interior entrance lookup now chooses the destination catalogue:
previously a Seyda Neen interior selected from Balmora searched only Balmora's
unconverted entrances. Missing map files are rejected before leaving the current
scene. Census shortcuts prefer the inspected pier-side registration entrance;
the first catalogue entry is an alternate doorway with an unsafe converted
arrival. Teleport shares existing state capture and checked arrival behavior.

## Seyda Neen sub-cells

Thirty overlapping regular regions now cover Seyda Neen. The first ship-exit
exterior uses a compact arrival pier; the Census ring courtyard has its own BSP.
Whole selected objects remain intact. Unused models, geometry, collision nodes
and textures are physically removed from each loaded file, and unmarked terrain
faces are pruned. The pier BSP falls from 5,567,884 to 3,938,380 bytes.

Shared coordinates, stable references, checked arrivals and state restoration
extend the Balmora approach. Keep the accepted frozen last frame and small top
Loading... box; Black screen remains selectable. The loader still replaces one
BSP synchronously. Effective view distance is capped at 540 in both exterior
region sets to match their overlap. Larger requested values remain stored for
other scenes. This is not asynchronous streaming or a guarantee of higher FPS.

## Opening, controls and collision

- Shift+V cycles requested 450/540/1000 distance. Bare 1/2/3 are freed; only exact
  legacy generated distance bindings are migrated, preserving custom bindings.
- Choose is highlighted by default in character confirmations. Review has a
  centered current/total page title.
- The Census front door back to the pier stays locked during registration.
- Supplement the long pier's side/shore containment while preserving the
  ship/plank connection and guard navigation. Full opening playtest stays open.
- Preserve authored shell collision for `ex_hlaalu_b_17` in nineteen Balmora
  regions. The earlier Nord stair entrance is traversable in the focused native
  test. Visible geometry, player dimensions, FOV and bob are unchanged.

## Accepted behavior and open findings

The owner accepts the Balmora region method and Silt Strider in dev3. Keep both;
do not modify the Strider further. Jagged door arches and other blocked/deformed
stairs remain open under **FIXES NEEDED IN BALMORA** in the roadmap. A reusable
Balmora stairway optimizer is proposed, not implemented in this checkpoint.
The whole-map high/low polygon-density study is explicitly next-version work.

The distance-1000 speed-up report is view-dependent in the initial native sweep:
one heading is modestly faster, two are slower. Its cause and the owner's large
improvement remain unresolved. Ship interior optimization is still separate.
Balmora interiors and background loading remain unfinished.

## Validation and compatibility

283 host tests pass. Native GCC warning comparison is 82 to 82, with no new or
removed diagnostic; existing warnings remain work. Native checks cover pier
side stops and forward travel, character review/Choose presentation, compact
courtyard residency and the earlier b17 stair entrance. Complete source logs,
conversion receipts and focused evidence are in the private playable package.
All 706 HDF payload files were read back and hashed. A diagnostic copy boots the
final packaged executable, visits the teleport destinations, crosses Seyda region
boundaries with both loading choices and walks the corrected b17 stair, without
surface/edge overflow. Census arrival is visually checked inside the room.

The profile remains 68040/FPU/JIT, 2 MiB Chip, 16 MiB Z3 and an 11 MiB game heap.
Focused native tests use an offscreen emulator and null audio sink; deterministic
walking tests are not FPS benchmarks. See [findings, causes, fixes and limits](INVESTIGATION-v0.0.24-dev4.md).

**Start a new game or Demo Game.** New region files and collision changes alter
the content fingerprint, so dev3 saves are incompatible. Delivered dev3 archives
remain unchanged. The owner handles commits, pushes and publication.
