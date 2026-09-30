# Interior geometry lost to an exterior distance filter

Discovered during the v0.0.24-rc1 Balmora conversion, 30 September 2026.

## 1. What was broken

Some converted interiors contained their enclosing compiler box but almost none
of the original room geometry. Balmora's East Guard Tower first produced a
5,428-byte BSP with zero mesh models; the two West Guard Towers produced
6,448-byte BSPs. This was a conversion failure, not an empty source CELL.

## 2. Why it happened

`prepare_area.build_room()` exported the selected CELL geometry correctly, then
called `prepare_mesh_bsp.append_meshes()` without an explicit reference list.
That function fell back to `select_runtime_refs(..., extent=736)`, the bounded
starting-area selection policy. Although the interior caller supplied centre
`(0, 0)`, it did not replace the exterior distance policy.

TES3 interiors have independent local coordinate systems. They need not be
centred on zero. For example, East Guard Tower placements have original X
coordinates about 3636–4371 and Y coordinates about 3594–4316. At the converter's
0.25 scale, the entire room lies beyond the default 736-unit selection extent.
The selector therefore rejected its assembly as `outside assembly bounds`.

The 736 limit is measured in AmiWind runtime units after the 0.25 coordinate
scale, not in original CELL units. Setting the origin to `(0, 0)` changes the
coordinate transform; it does not disable selection. The bug was the reuse of
an exterior selection policy during interior assembly, not missing source
meshes or a malformed guard-tower CELL.

## 3. Implications

- A successful mesh export and successful BSP compiler exit do not prove that
  the playable map contains the room.
- Doors, NPCs and destination coordinates can be present while their floors,
  stairs and walls are absent. Arrival, floor placement and interaction may
  consequently fail or appear to be collision/height problems.
- Increasing player clearance, changing FOV or adding replacement floors would
  hide the selection error without restoring the original layout.
- The same implicit policy can affect future interiors located far from zero.
  Exterior streaming bounds remain appropriate for exterior sub-cells.

## 4. Correction and future procedure

Balmora's interior builder now supplies every reference number from its exported
`scenery-index.json` explicitly to `append_meshes()`. Room geometry continues to
use the existing documented `select_geometry()` content policy; the second
assembly pass must not silently impose a town-centred distance filter.

When this symptom returns:

1. Identify the original CELL and its placed reference IDs. Inspect its local
   bounds and original door destination positions before changing transforms.
2. Compare the source selection, exported index and final BSP entities. Inspect
   the conversion report's `selection.omitted` reasons and `unique_models` count.
3. Look for a missing `references=` argument, a default extent, or an exterior
   coordinate origin reused for an interior.
4. Pass the explicit room selection. Preserve the original local coordinates,
   scale and matching DODT arrival transforms. Avoid a blanket radius increase.
5. Reassemble from the original exported geometry; rebuild the packaged BSP.
   Reusing an old BSP does not apply the source-code correction.
6. Require every selected reference to appear in the output, with no unexplained
   assembly rejection. Check budgets, floors, both directions of each door,
   NPC placement and native memory use before accepting the room.

For a prepared room, compare `area-work/<map>/source/scenery-index.json`
`references[].number` with the `aw_ref` fields of the assembled `func_wall`
entities in `area-work/<map>/room.bsp`. Consult
`area-work/<map>/conversion.json` for `instances`, `unique_models` and
`selection.omitted`. Its `models` list describes mesh conversion, not a
reference-ID ledger; checking only model counts, file size or a compiler
success message is insufficient. Preserve the earlier `select_geometry()`
omission report separately: intentionally excluded content is different from
geometry exported successfully and then accidentally culled during assembly.

Also inspect the assembler's `retain_dressing` policy. Its legacy default
excludes model names containing `flora_`, `marker_`, `scum_`, `lantern_hook` or
`furn_de_rope` after reference selection. Those exclusions are not currently
listed in `selection.omitted`, so an empty list alone does not establish full
reference coverage. Account for each missing ID explicitly; review whether
that policy belongs in the particular room before accepting the result.

The implemented change applies to the Balmora room builder. When bringing in
other interior families, inspect their callers as well; this finding does not
establish that every legacy interior caller has been corrected. Keep exterior
sub-cell selection bounded.

A regression check should include a room whose entire assembly lies beyond
the former origin-centred extent, and a near-origin control. Require identical
reference coverage after shifting the room and its door arrivals together.
That check supplements the native arrival/traversal gates; it cannot replace
them.

## Evidence and status

After explicit selection, the inspected geometry builds contain:

| Interior | Map | Selected references retained | BSP bytes | Assembly omissions |
| --- | --- | ---: | ---: | ---: |
| East Guard Tower | `bmeastguard` | 85 / 85 | 2,111,300 | 0 |
| West Guard Tower, North | `bmwestnorth` | 79 / 79 | 1,859,780 | 0 |
| West Guard Tower, South | `bmwestsouth` | 78 / 78 | 1,947,880 | 0 |

These sizes describe the geometry assembly evidence, before later NPC/entity
updates; they are not final release checksums or expected packaged file sizes.
These are conversion results; native traversal and arrival validation remain
separate RC1 acceptance gates. Source CELL/BSA data and detailed private build
reports are not part of the public source package.

A subsequent reference-ID audit initially found exact coverage in 24 rooms.
The other 19 omitted 99 references through the separate legacy dressing policy,
with no further distance rejections. The Balmora builder now sets
`retain_dressing=True`: `select_geometry()` has already made the room's content
selection, so assembly must retain its exported dressing too. Rebuilding those
rooms produced exact coverage in all 43 final maps: 3,408 selected references,
3,408 placed references, no missing IDs or duplicates. The final entity pass
also retained 90 living NPC placements and three authored corpses.

That rebuild detected four truncated intermediate `scenery.mwpak` caches. The
converter correctly rejected their short payloads. They were re-exported from
the owned source data; every indexed payload's length and SHA-256 now verifies
across all 43 rooms. Keep these integrity checks: do not pad a short asset or
weaken validation to get through a build.

A subsequent native smoke pass loaded and captured all 43 final rooms, including
the three far-origin towers, then exited cleanly after 899 frames with zero
surface or edge overflow frames. This verifies loading and initial rendering;
it does not certify all walking routes, NPC interactions or two-way arrivals.
