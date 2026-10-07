# GATE-EMBERS-31: ember commit broke native torch tests and a header format check

## Status: 7 October 2026

Repaired in source before v0.0.31-dev1 was packaged. Never shipped; found by
the release gates on the development branch.

## Symptom

The v0.0.31-dev1 gates failed in two places:

- Preflight: `engine/aga/src/d_iface.h:230: blank line at EOF`, then, once
  that was removed, trailing whitespace at line 125.
- Linux suite: three native torch tests did not link
  (`test_guard_torches_source_registry_cycle_pose_lights_and_depth`,
  `test_torch_controls_bounded_light_surface_illumination_and_overlay`,
  `test_guard_diagnostics_distinguish_flames_from_admitted_lights`), with
  undefined references to `host_frametime` and `AW_EmberSpawn`.

The engine build itself was clean (zero warnings) and the host-parity tests
passed.

## Where

`engine/aga/src/d_iface.h` (particle type list) and the native test fixtures
`tests/aga_guard_torch_test.c` and `tests/aga_torch_test.c`. The game is
unaffected.

## How it happened

The torch-ember change added the `pt_awember` particle type, left an extra
blank line at the end of `d_iface.h`, and made `aw_torch.c` and
`aw_guard_torch.c` call `AW_EmberSpawn` (in `r_part.c`) at a rate scaled by
`host_frametime` (in `host.c`). The native fixtures compile those two files
on their own with test stand-ins for everything else, and had no stand-ins
for the two new symbols.

`d_iface.h` is an original Quake header. Its blank last line and three
trailing spaces in comments come from the original source; the preflight
accepts unchanged historical files byte for byte, but checks every changed
file in full, so editing the header made its old formatting count.

## Why it was not caught

The ember change was verified with full engine builds and in-game clips, and
was committed before the full gate set ran on it. The gates ran only at the
dev1 version bump.

## Reproduction

Run the full Linux suite on the ember commit: the three tests fail to link.
Run the preflight on it: the format check reports the blank line.

## Repair

The two fixtures define `host_frametime` (left at zero, so no embers spawn and
the fixtures' expected results are unchanged) and a no-op `AW_EmberSpawn`.
The header's blank last line and the trailing spaces in three comment lines
are removed (no code change).

## Verification

Preflight, the full Linux suite, the host-parity tests (Linux and Windows) and
the zero-warning engine build pass on the repaired source.

## Prevention

Engine changes that add calls across source files run the full gate set
before they are committed, not only at the version bump.

While recording this bug, its own report page was first left out of
`tools/release-files.json`, so the format preflight did not check it and the
release would have shipped a register link to a missing page. The bug-tracker
test now also requires every tracker file to be in that list.
