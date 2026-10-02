# Native Windows 11 build and WinUAE checkpoint, 2 October 2026

**AmiWind's complete current v0.0.25 conversion recipe was built on native
Windows 11, packaged into a verified HDF after an image-stage correction, and
booted into the 3D prison scene in WinUAE.** Linux remains the established build
baseline; native Windows is experimental with unresolved intermittent worker
failures. This checkpoint does not claim all original Morrowind content or
gameplay has been implemented, or that every scene has been playtested.

## Scope and provenance

The Windows port starts from cloned Linux baseline v0.0.25 commit
`3433922c40a48ffd20a0362ed58407298221686a`. The public working tree adds native
Windows launch/setup scripts and host fixes; the engine source remains unchanged.
Portable asset identifiers use forward slashes and generated Amiga scripts use
LF, preserving Linux's existing formats. Windows image packing uses bounded
xdftool commands. Linux invocation branches were compared structurally with the
cloned baseline; this Windows result is not a fresh Linux runtime test.

All 25 pre-image stages passed with the full gallery and all 2,526 world terrain
regions. The original full-run receipt correctly remains **failed**, because
image assembly hit Windows' command-line length limit (WIN-03). After correcting
only Windows packing, a separate image-stage retry verified retained terrain
hashes and allowed source differences, reran the normal image gates into a fresh
directory, and passed. This establishes a successful Windows conversion/image
checkpoint after recovery, not an uninterrupted first-attempt build or general
automatic resume support.

No gallery omissions, model-quality reductions or actor-ground waivers were used.
The instrumented conversion recorded 1,925 worker lifecycles with no invalid
queue handles. WIN-01 remains open because earlier full attempts failed
intermittently; one successful conversion does not identify its cause or frequency.

## Tested environment and commands

Windows 11 Pro, AMD64; 24 logical processors, 64 GiB installed RAM. Official
CPython 3.12.10; NumPy 2.5.3, SciPy 1.18.1, Pillow 12.3.0, PyFFI 2.2.3,
fast-simplification 0.2.0 and amitools 0.8.1. The AmigaPorts v16.2-rc11 Windows
SDK provides GCC 16.2.0b20260825082934 and vasm 2.0f; ericw-tools 0.18.1,
FFmpeg 9.0.1 and the provisioned QCC were used. Engine compilation reported
78 warning lines and passed its binary checks. See the setup receipt/toolchain
manifest for the executable/version checks; newer or older versions alone are
not proof of compatibility or incompatibility.

Normal public entry points, with example paths:

```powershell
.\setup-windows.cmd -Yes
.\build.cmd --data-files 'C:\Games\Morrowind' --workspace C:\AmiWindBuilds --name win-full --jobs 24
```

Keep the input game installation read-only. Use a fresh name for a failed-run
retry and preserve logs/validated model caches. The bounded local image retry
used for this checkpoint is not a new public generic-resume command.

## Validation and timing

- Full NPC gallery: 3,551 models covering 2,935 records; 7,107 payload files
  passed catalogue/payload validation. The full-run gallery reused validated
  models. A preceding independent conversion processed 2,761 models freshly,
  reused 790 and had zero failures.
- Complete terrain: 2,526 regions, no diagnostic subset; stage elapsed 572.34 s
  (9 min 32 s). A 24-worker sample reached 100% host CPU with RAM headroom.
- Original run to image failure: 1,861.64 s (31 min 2 s), including cached gallery
  stage 75.64 s and Balmora 316.12 s. These are not cold whole-game timings.
- Corrected image-stage retry: 433.078 s (7 min 13 s). Production actor-contact
  gate passed with zero unresolved findings against the complete packaged payload.
- Final readback passed for every file: DH0 8,974 files; DW0 1,651 files.
  Total stored payload: 2,702,239,783 bytes. HDF: 3,489,693,696 bytes (3.25 GiB).
- This run's HDF SHA-256:
  `37ec9c66924b1d7a61c0ec070cec7689535b14fa9c10a178462702d924ca4864`.
  This is an evidence checksum, not a claim of byte-identical images across builds.

The observed retained run occupied 12.578 GiB including its failed image staging
and successful retry. Excluding the 2.524 GiB failed staging gives approximately
10.054 GiB for the completed conversion and image. Temporary partition overlap
and a 3.25 GiB emulator working copy require additional space. Installed native
tools/downloads were 2.989 GiB before the separate Docker installer was cached;
validated model cache was 0.242 GiB. These snapshots are not a measured peak-space
minimum; see the [Docker capacity plan](DOCKER_BUILD_ROADMAP.md).

## WinUAE smoke test

WinUAE 6.0.3 used an owned complete A1200 Kickstart 3.1 ROM, AGA/PAL, 2 MiB Chip,
16 MiB Z3 Fast, 68040/internal FPU, JIT and fastest possible CPU. A working copy
matched the built HDF checksum before boot. Observed sequence: successful
preflight, main menu, New Game confirmation, opening movie, rendered prison
scene with Jiub, keyboard entry and acceptance at the player-name prompt, then
the in-game HUD and functioning pause/main-menu navigation. Exit returned cleanly
to AmigaDOS. The test emulator was closed afterward.

This confirms boot, game entry and basic keyboard/menu input. It does not certify
all maps, saves, audio quality, sustained play, physical Amiga performance or
lower-spec hardware. Runtime screenshots/configuration stay private because they
contain the owner's converted game assets and host paths.

## Remaining release work

WIN-01's intermittent worker-handle failure remains unresolved. WIN-02's cancelled
worker-descendant cleanup candidate needs integration. WIN-03's corrected packing
passed this full image; retain its regression tests. See [the bug journal](BUG_JOURNAL.md).
The planned v0.0.26 release also includes the [Docker builder](DOCKER_BUILD_ROADMAP.md),
its input helpers and container validation. Those are still pending. The Windows
port and fixes are packaged as **v0.0.26-rc1**; the historical full image and
WinUAE evidence above retain their actual v0.0.25 runtime identity. See the
[rc1 release notes](RELEASE-v0.0.26-rc1.md) for version-specific checks. Validate
the Linux source path before publishing.
