# AmiWind v0.0.21-dev6 - versioned startup environment preflight

Dev6 is a focused diagnostics and playtest-configuration update. It preserves
v0.0.21-dev5 gameplay, converted-content behavior and save format.

## Native boot preflight

`AmiWindCheck`, which runs from `S/startup-sequence` before the 68040 engine, now
prints a versioned checklist instead of only terse failure messages. The exact
project version is generated from the root `VERSION` file and appears in the
preflight banner, successful-start footer, failure footer and embedded
`$VER: AmiWindCheck ...` identity.

The Amiga-side checker reports only values that can be observed honestly from
the guest:

- Exec API version, requiring version 40 / Kickstart 3.1 class or newer;
- 68040/68060-class CPU and the internal 040/060-compatible FPU flag;
- PAL / 50 Hz timing, reported as a warning rather than a hard failure;
- AGA capability through `graphics.library` / `SetChipRev`;
- installed, free and largest-block Chip and Fast RAM;
- whether the required Zorro III / 32-bit Fast-RAM path is usable.

The exact Kickstart ROM build is deliberately **not** inferred from the
`exec.library` revision. In particular, Exec's library revision is not the same
number as the ROM build label such as 40.68. JIT state, fastest-possible versus
real/cycle-exact CPU mode and the exact ROM-file identity are host-emulator facts,
so the native screen labels those fields as host checks instead of making a false
claim.

## FS-UAE host preflight

`tools/AmiWind-FS-UAE-launcher.py` now supplies the complementary host check. For
the managed AmiWind playtest profile it enforces and prints:

```text
Amiga type:           A1200
CPU:                  68040-NOMMU
FPU:                  68040 internal
CPU speed:            Fastest possible
JIT:                  ON
24-bit addressing:    OFF
Chip RAM:             2048 KiB
Z3 Fast RAM:          16384 KiB
Cycle-exact speed:    OFF (cpu_speed=max)
```

The launcher continues to preserve unrelated custom options. If a version-matched
existing config has different managed machine settings, it keeps the old file in
the existing numbered backup directory and writes the known AmiWind profile.
This closes the gap where a stale/custom FS-UAE config could silently request a
slow CPU profile while still pointing at the correct HDF and ROM.

The known ROM SHA-256
`6d43840d4099a74170ea0f0425b6257c3891ebcaa39c4d1840075a9ab22b5707`
is identified by the launcher as **Kickstart 3.1 A1200 40.68**. A different ROM
remains an explicit compatibility warning; it is not mislabeled.

## Validation completed in this source workspace

- `tools/release.py --check`: passes with 527 allowlisted source files.
- `tests.test_project_version` and `tests.test_fs_uae_launcher`: 29/29 pass.
- Release/layout/FS-UAE-runner regression subset: 21/21 pass.
- Full Python discovery ran 219 tests: 215 completed successfully, 2 optional
  geometry tests skipped, and 2 unrelated environment/dependency errors remain
  (`fast_simplification` is not installed; Python 3.13's mocked
  `os.process_cpu_count()` path raises the already-known `OSError`).
- The launcher regression proves that deliberately wrong A500/68020/JIT-off/
  real-speed/24-bit settings are backed up, corrected to the accelerated AmiWind
  profile and reported in the versioned checklist.
- Generated native include text is checked for the versioned banner, pass/fail
  footer and `$VER` identity.
- Python compilation of the modified launcher/tests passes.

The sandbox used for this source update does **not** contain the AmiWind m68k
SDK/vasm toolchain or owned game data. Therefore no new `AmiWindCheck` Hunk, engine
binary, playable HDF or interactive FS-UAE boot is claimed here. The assembly
change must still pass the ordinary native build and boot validation before a
private playable dev6 package is promoted.

## Compatibility and scope

- No game assets, ROM bytes or private HDF are added to public source.
- No gameplay, renderer, audio mixer or save-format change is claimed.
- The WinUAE public preset is version-bumped in parallel, but this update was
  motivated by FS-UAE/Linux playtesting and the new host checklist is implemented
  in the portable FS-UAE launcher.
- v0.0.21-dev5 and all earlier release artifacts remain immutable.
