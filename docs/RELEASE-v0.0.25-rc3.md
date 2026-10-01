# AmiWind v0.0.25-rc3 — interior window conversion repair

Source checkpoint fixing the rc2 `area` failure:
`ValueError: No supporting façade geometry`.

Exterior-named Nord window meshes also occur inside the Tradehouse, Warehouse
and other interiors. Exterior panel mounting incorrectly assumed those interior
placements had an exterior house supporting mesh. Flattening profiles now state
their scene scope. The shipped profiles apply to exteriors; interior windows
retain authored visual geometry and collision. Missing exterior support still
fails validation. Scenery archives close even when conversion fails.

## Verification

- Reproduced the original error on the real Warehouse cell with untouched rc2.
- The fixed Warehouse conversion succeeds. The full build passes `area`, both
  Balmora stages, character conversion and the other stages listed in the receipt:
  21 stages passed at the checkpoint, with `world-terrain` still incomplete.
- Native AGA engine and preflight compile successfully. Engine sources are
  unchanged from rc2; the compile emits 78 existing warnings. These are retained
  findings, not a warning-free result or runtime-safety certification.
- All 336 distinct host tests pass, including the compiled collision test run
  separately with the external map compiler enabled.
- With identical inputs, the exterior comparison BSP is byte-for-byte identical
  to rc2: 5,533,976 bytes, SHA-256
  `f1db47dd521949f39a5cfde236c82ba210eaaf881a3e3f9bd3ce6b5695802ff5`.
- Source allowlist, whitespace, archive hashes/modes and exact-baseline patch
  application are checked before handoff.

See [validation receipt](validation/rc3-source.json) and
[local build instructions](LOCAL-RC3.md).

## Remaining limits

Whole-island terrain conversion did not finish in this verification run. Final
HDF assembly, boot and native rc3 playtesting have not passed. The unchanged
production image gate can still stop on the 23 historical NPC ground-contact
findings; this repair does not resolve or waive them. Compile success must not
be described as a successful complete `build.sh` run.

This checkpoint includes source archives only. Original game inputs, converted
assets, ROMs, executables and private playtest images are excluded. The installed
GOG layout is documented with generic paths in [GAME_INPUT_LAYOUT.md](GAME_INPUT_LAYOUT.md).
Published rc2 and earlier tags/archives remain unchanged.
