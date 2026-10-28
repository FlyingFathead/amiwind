# AmiWind v0.0.21-dev7 - visible startup preflight and dry-run boot order

Dev7 is a focused follow-up to dev6. Gameplay, converted content, renderer/audio
behavior and save format are unchanged.

## Startup behavior

`AmiWindCheck` still performs the dev6 guest-observable checks. After a successful
preflight, it now leaves the report visible for a default **five seconds**. The
countdown uses DOS input/timer services rather than a CPU-speed-dependent busy
loop. Press **Space** or **Enter** to continue immediately. Failure remains fatal to
the startup sequence.

This is intentional because the inherited Amiga boot console is not treated as a
portable/reliable scrollback interface. The short delay exposes the diagnostics
without leaving AmiWind stuck at a boot prompt.

## Asset-free dry-run image

The public dry-run HDF now contains both `C/AmiWindCheck` and `C/AmiWindDryRun`.
Its startup order is:

```text
FailAt 10
SYS:C/AmiWindCheck
SYS:C/AmiWindDryRun
```

A successful preflight therefore shows its five-second/skip-able report and then
continues to the original dry-run notice. A failed preflight returns 20 and stops
before the notice. The engine binary remains present only as the asset-free test
compile result; the dry-run does not start gameplay.

## Version identity

The root `VERSION` value is `0.0.21-dev7`. Generated native strings continue to
identify the preflight as `AmiWind v0.0.21-dev7` and `$VER: AmiWindCheck
0.0.21-dev7`. Current emulator presets and current documentation use the same
version. Historical release files remain unchanged.

## Predecessor evidence

Before this follow-up, the owner built dev6 on the normal Linux toolchain: the
68040 engine linked, `AmiWindCheck` assembled successfully with vasm 2.0f, and the
asset-free dev6 HDF booted in FS-UAE 3.1.66 to the original test-build notice.
That boot also demonstrated why the dry-run needed the checker wired into its
startup sequence: dev6's dry-run image skipped it.

## Validation boundary

Source-level tests verify the generated version strings, five-second input/timer
path and dry-run startup order. `tools/release.py --check` must pass before source
packaging. Native vasm assembly and an actual FS-UAE boot of the dry-run HDF are
the next acceptance steps on the owner's build machine; this source change does
not claim them before they are run.
