# One possible approach: terrain cuts and compact shared surfaces

Recorded 4 October 2026 from an owner-supplied external proposal. This is **one
possible approach**, not a selected complete architecture or an implementation
claim. The original text is preserved privately with its SHA-256. Its diagnosis
and requirements must be tested against each new candidate.

The attachment reports a historical diagnostic with 8,562 additional stored
faces (+32.7%) and 969,192 additional file bytes (+21.3%). Those figures describe
that earlier comparison, **not candidate020 or the current output**. Removing
2,581 placed faces does not offset stored growth automatically: many placements
can reference one stored surface. A fresh candidate needs its own exact baseline,
hashes and cost breakdown.

## Proposed geometry pipeline

Use the canonical `terrain-source.npz`, its original diagonals and the exact
source-to-compiled transform. Water is not terrain, including where the terrain
is submerged seabed. The visible terrain must cover what is removed: if a coarse
rendered patch lies below the canonical cut, refine that affected patch and stitch
its boundary. Revalidate the contact region. Querying a fine canonical heightfield
does not require rendering the entire town at that resolution; blanket fine-grid
replacement is not the proposal.

For a placed static surface, keep the part at or above the canonical height
`H(x,y)` and remove the strictly buried part, subject to an explicit numerical
contact tolerance. Each terrain triangle supplies a sloping plane and triangular
XY footprint extending downward without a lower cutoff. Preserve the visible
terrain itself. Missing source coverage remains an unresolved acceptance failure.

Perform the clipping in the source face's own two-dimensional plane. A vertical
wall has nonzero area there even when its XY projection collapses to a line.
Spatial indexing and conservative height bounds can accept clear cases quickly;
testing only the original vertices is insufficient where intervening terrain
triangles cross the face.

Union all buried pieces for each original face, subtract that union once, and
reconstruct the surviving contour. Internal terrain-grid edges used during the
calculation should disappear unless they define a real visible boundary. Merge
compatible coplanar output, then partition it into renderer-supported convex
polygons while preserving openings, material boundaries and UV mapping. Robust
side/orientation predicates, deterministic intersections and validation after
serialization rounding are separate obligations. A tiny positive-area visible
piece is not disposable merely because it is small.

## Proposed representation and stage order

Store unchanged and identical surviving surfaces once. Give each placement a
precompiled list of only its finished surfaces: shared roof/walls plus its own
cut foundations. A full wall needed elsewhere may remain in the pool but must
not be referenced by a placement that requires a clipped wall. Remove globally
unused pool entries; share identical cut results when beneficial. Compare the
cost before introducing additional common/variable splits.

The inherited brush-model format uses a contiguous `firstface`/`numfaces` range.
The attachment therefore calls for real engine/data-format support for lists or
runs. AmiWind now has a bounded render-range helper with focused native parser/
view fixtures and an Amiga compile pass. That narrower result does **not** prove
this complete contour, packing and lighting proposal is implemented or accepted.

Geometry sharing must account for mutable per-surface dynamic-light and surface-
cache state. Differently placed instances may require separate lighting/cache
state even when geometry is identical. Include that allocation and update work;
preserve torch behavior rather than assuming all state is immutable.

The proposed production order is:

```text
canonical terrain + source surfaces + placements
  -> contact correctness and targeted terrain conformity
  -> buried-region union, subtraction and contour reconstruction
  -> compatible merging and required texture/renderer splits
  -> final lighting generation
  -> shared packing and deduplication
  -> serialization and independent checks of reloaded output
```

Use original surfaces or a defined pre-light intermediate with stable provenance.
Repeatedly clipping an already fragmented rejected BSP is not the preferred
baseline. Changed geometry receives lighting for its final shape; existing
lightmaps are not an exemption from clipping.

Keep collision and structural BSP processing independent. A render-only cut must
not create a newly textured underside or closing cap. Compiler-only closure can
retain solid behavior without rendering its faces, but actual exported arrays
must be checked. If terrain repair changes collision, validate that repair as a
separate baseline; preserve the validated collision during later render culling.
Remove every local sky-enclosure render face by generator provenance separately
from terrain clipping, retaining the authorized shared sky resource and renderer.

## Cost and acceptance

Measure final unique geometry, placement references, lighting/cache state and
loader overhead against the exact baseline. Break growth into terrain repair,
unique cut contours, duplicated unchanged surfaces and required texture splits.
For the attachment's historical 8,562-face growth, a 64-byte target surface record
would add 547,968 surface-record bytes alone. This is conditional arithmetic under
that ABI, not a current heap measurement. Other arrays, textures and loader peaks
remain separate. Exact placement-specific clipping can genuinely increase cost;
it does not guarantee a smaller map.

Acceptance requires independent checks on the reloaded serialized output:

- No positive-area buried render portion remains in any placement outside the
  documented contact tolerance; no intended above-ground surface is lost.
- Actual rendered terrain covers removed regions without cracks or mismatched
  joins. Unknown coverage and unsupported cases block acceptance.
- No local sky-enclosure render faces, duplicate fragments or zero-area output
  remain; shared references and lighting/cache state are valid for every use.
- Matching-ABI peak memory, collision/visibility and matched target rendering,
  lighting and frame-time checks pass for the complete resident map.

See [Hidden in dirt](HIDDEN_IN_DIRT.md) for mandatory terrain/sky and continuous
central-area requirements, and [Exterior hidden surfaces](EXTERIOR_HIDDEN_SURFACES.md)
for the separate one-sided drawing and interior-cell provenance investigation.

## Primary references supplied with the approach

- [Robust geometric predicates](https://www.cs.cmu.edu/~quake/robust.html):
  classification near numerical degeneracy; not a complete polygon-union solver.
- [Quake BSP structures](https://github.com/id-Software/Quake/blob/master/WinQuake/bspfile.h):
  inherited contiguous model face ranges.
- [Quake model structures](https://github.com/id-Software/Quake/blob/master/WinQuake/model.h):
  surface geometry alongside mutable light/cache state.
- [Ericw QBSP documentation](https://ericwa.github.io/ericw-tools/doc/qbsp.html):
  compiler surface semantics, including `skip`; verify final serialized omission
  rather than inferring it from a material label.
