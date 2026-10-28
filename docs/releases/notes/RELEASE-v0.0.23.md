# AmiWind v0.0.23

29 September 2026. Regular release following v0.0.23-dev5.

- Restore the fourth window on the tall Seyda Neen facade. All four original
  references exist; the flattened panel clearance was too small for reliable
  rendering. Increase wall clearance from 0.05 to 0.5 runtime units, retaining
  the original placements and collision geometry.
- Correct wall breakthrough on both Census exterior doors with targeted visual
  clearance; retain their collision and interaction positions.
- Add Darvame Hleran's Silt Strider menu: Balmora, Gnisis, Suran, Vivec and
  Cancel. Aim at her at close range and press E. Arrows select, Enter chooses,
  Escape cancels. Your gold total is shown.
- All four destinations are currently unavailable. Selecting any of them says
  exactly "Destination not found." No money is charged and no map is queued.
  Paid travel and fares will become active when validated destination maps and
  arrival points are integrated. A stray BSP file alone cannot enable travel.
- Add `dbg hud on` as an alias for `dbg overlay on`.
- Boolean console cvars explicitly registered in `aw_boolean.h` accept
  on/off, true/false and 1/0, case-insensitively. Numeric and layout settings
  keep their existing numeric semantics. Existing debug toggle commands also
  accept these boolean spellings.

This regular release retains the existing experimental gameplay scope. It does
not claim a complete Morrowind implementation, seamless streaming, or resolved
performance at every exterior viewpoint. See the dev5 notes for inherited limits.

## Next work: Balmora exterior

Use the supplied map footprint: both river banks, temple and northern bridge,
western manors, eastern residential streets, Silt Strider and southern approach,
and the southwest surroundings of Tharys Ancestral Tomb. First convert original
LAND terrain and exterior references. Interior conversion is a later step.

The owned base-master audit identifies four named Balmora exterior cells:
(-2,-2), (-3,-2), (-3,-3), (-4,-2). These names alone do not define the pictured
boundary; adjoining cell references must also be selected by spatial coverage.
There are 41 Balmora interiors plus Tharys Ancestral Tomb in the source audit.
Keep original references and inspect cliffs, rocks and building attachments as
part of terrain integrity. Use the source travel arrival for the future ride.
