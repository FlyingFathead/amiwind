# Intended host-to-Amiga build pipeline

## Geometry import validation update: 2026-10-06T20:06:10+03:00

The RC1 Temple investigation confirmed that nearly collinear leading vertices
can produce incorrect exported BSP planes despite retained source triangles.
Use [the geometry import checks](MESH_TIPS_AND_TRICKS.md) and retain
[the Temple regression](bugs/BALMORA-TEMPLE-GEOMETRY-29.md) for future imports.
The repair candidate is Temple-only; the wider interior audit is read-only.

The goal is one host-side build process: provide original Morrowind files, choose
a hardware/storage profile, then generate a locally playable Amiga build. The
host performs expensive preparation; the target runs a purpose-built native
runtime over the converted data. All game-derived outputs stay external.

| Stage | Work | Status |
| --- | --- | --- |
| Discover | Read owned installation and resolve records/references | Bounded terrain/STAT/DOOR placements plus the explicit ACTI arrival-ship assembly, initial actors/hands and ordered voice lookup; complete vicinity/containers pending |
| Reduce | Select detail and sampled animation poses | Terrain sampling, shared scenery variants, ship material/component reduction and bounded actor/hand poses; broader reduction planned |
| Bake | Assemble meshes/skins/poses and resample audio on host | Dressed idle actors, hands, foliage sprites and PCM; no integrated OpenMW baking backend |
| Map | Quantize palettes and index source-to-runtime identities | Shared appearance/mesh records and private voice candidates; complete stable world-state mapping pending |
| Pack | Build reusable assets and bounded target data | Resident AGA BSP/MDL scene, music blocks and experimental terrain packets; no gameplay world-chunk streaming |
| Build runtime | Compile native display, input and audio code | Preserved A500 experiments plus current AGA 040/FPU runtime; music streams during play |
| Assemble target | Combine runtime and locally converted data | Versioned private HDF and public source/presets; original ROM/data kept external |
| Verify | Check formats, memory budgets and execution | Host fixtures and native routes with hardware/hashes recorded; stock-CPU A1200 unproven |

The final output needs both the native runtime and converted game data. Asset
conversion alone cannot supply rendering, game rules, interaction or I/O logic.

This status reflects checkpoint-015. Follow [LINUX_BUILD.md](LINUX_BUILD.md) for
the current guided build. Verified mappings and causes/fixes are recorded in
[IMPLEMENTATION_JOURNAL.md](IMPLEMENTATION_JOURNAL.md). Next coverage is the
connected [starting-area exteriors](SEYDA_NEEN_SCOPE.md), then separately loaded
interiors and local game systems such as [containers](CONTAINERS.md).

## Output profiles

For development, a mounted directory or hard-drive image can hold the executable
and data. A physical A500 build must match its actual storage interface and
driver. Boot media and bulk data may be separate; a small boot/test floppy does
not imply that the full converted game and soundtrack fit on a floppy.

Do not settle the final disk/image format before the native renderer and storage
path are measured. The image assembler must use external output paths, include
an asset manifest and record the target profile. Emulator ROMs and any required
third-party system files remain user supplied and outside the source package.

## Rebuilds and budgets

Cache host results by source hashes, conversion settings and converter version.
Reuse a baked appearance wherever its recipe matches. Rebuild only assets whose
dependencies changed, then repack the affected bundles. Keep temporary captures,
compressed caches and final data in separate external workspace directories.

Report disk bytes, decoded RAM bytes, Chip RAM residency and worst read/decode
latency separately. A smaller on-disk asset is not necessarily cheaper to decode
on a 68000. Native tests must include graphics and audio running concurrently.

The `setup`/`convert` commands produce verified terrain data. The separate
opening tools produce a bootable vignette and filled/wireframe terrain camera; neither workflow is a complete game port.

## Arrival assembly and collision separation

`config/scenery_groups.json` declares the complete arrival ship: hull, gangplank,
hatch and cabin door. Missing, deleted or ambiguous members fail conversion.
Runtime-region intersection selects this assembly as a unit; unrelated statics
still use the existing origin filter, whose broader coverage replacement is pending.
Grouped geometry goes directly to the BSP mesh pass instead of a throwaway MDL.
Ship visual reduction is host-side and preserves material/component grouping;
source UV transfer is approximate. Its authored hidden collision subtree is
packed separately and converted to bounded approximate convex pieces. Those
collision faces are not visible scenery. See [area journal](journals/SEYDA_NEEN.md).
