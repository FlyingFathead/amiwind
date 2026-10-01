# AmiWind v0.0.25-rc6

Complete source checkpoint updating rc3 directly. This package includes all
intervening host-tool changes, build output reporting and documentation. There
is no requirement to install rc4, rc5 or separate roadmap patches first.

Implemented changes since rc3:

- Hide the compass/heading HUD by default. Add saved `aw_compass` configuration
  and `dbg compass on/off`, `1/0`, `true/false`, independent of debug overlays.

- Fix image assembly after whole-world conversion: the world/journal receipt
  records only its four owned files, preserving `regions.awr` and strict checks.
- Validate world UI and actor contact before expensive terrain compilation on new full runs.
  Add checked [rc3 image recovery](IMAGE_RECOVERY.md), reusing completed terrain
  and rebuilding only the versioned engine and image into a new run.
- Host-aware executable/virtual-environment discovery and read-only `--host-plan`.
- Explicit propagation of the selected Python interpreter into the engine make
  invocation, an explicit/managed console-font path and a single-path MSYS2
  translation helper. Native Windows setup/QCC integration remain unimplemented.
- Terminal-width completion footer: start/end timestamps, elapsed time, output
  bytes/GiB and SHA-256, and recognized engine warning lines. Success is printed
  only after the selected build stages and final output hashing pass. Failure
  and cancellation have separate wording. See [build output](BUILD_OUTPUT.md).
- Repeat the detected Python/package and selected compiler/toolkit versions in
  the footer and JSON, preserving binary hashes and unknown-version labels.

The [build/compiler toolkit roadmap](BUILD_TOOLKIT_ROADMAP.md) makes world-terrain
build time the top engineering priority. Phase profiling, reuse across fresh
run names and reducing duplicate BSP/collision work come first. A source-based
scheduler audit covers late terrain startup, fixed stage
worker allocations, ordered-queue stalls and dependency-safe alternatives.
Within the [Windows roadmap](WINDOWS_BUILD_ROADMAP.md), native Windows/MSYS2 is preferred;
WSL2 is an optional fallback. Bundled QCC and GPU acceleration remain proposals.
No terrain speedup or working Windows backend is claimed for this checkpoint.

All 373 source tests pass, including external-qbsp collision checks. A fresh
Linux serial build compiled the rc6 engine/preflight and created and read back
an asset-free 8,421,376-byte HDF; its SHA-256 was checked independently. The
build reported 78 compiler-warning lines, retained without suppression.
Validation results are recorded in [the rc6 receipt](validation/rc6-source.json).
A successful native compile and asset-free test HDF are not a full game build.
The earlier cloud full conversion stopped on disk exhaustion during world-terrain
assembly. A reported rc3 workstation run completed terrain in 4232.5 seconds
and then failed the world/journal receipt check; no final HDF passed.
The receipt-only retry then encountered 23 pre-existing actor-contact findings.
The new early actor check reproduced all 23 from the retained rc3 scene before
world-terrain. These are unresolved unintended placement defects, not intentional
levitation. Strict production acceptance still requires zero findings.

An explicit `--allow-known-actor-ground-findings REPORT` option permits only a
private diagnostic image when the complete audit and BSP/actor-model hashes
match the reviewed report exactly. New/changed findings or payload fail. Invalid
classification/metadata failures cannot be waived. The raw audit stays failed;
separate acceptance metadata records `production_gate_passed: false`. The output
is named `-private-test.hdf`, and its footer does not claim an error-free compile.

The owner reported a successful rc3 private retry with these hotfixes: 144.664
seconds and 3,221,258,240 bytes. Its reported SHA-256 is
`b99358fc5342b8c8dfc827d4db8353acd113daad1420853d8b2a4865080acb47`.
This confirms the reported rc3 assembly result, not a strict actor pass, rc6 full
game build or emulator test. No private playable payload is supplied here.

The release contains complete public source, its updater and checksums. The
single local handoff bundle additionally includes apply, commit, tag, push and
GitHub prerelease instructions. Earlier version archives remain unchanged.
