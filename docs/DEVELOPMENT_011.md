> Historical dev1 snapshot. Subsequent fixes and native results are in
> [v0.0.11-dev2 / checkpoint-009](CHECKPOINT_009_VALIDATION.md). The unresolved
> filename and mesh experiments described here were investigated in dev2.

# v0.0.11-dev1 archived development record — 27 September 2026

This is a development source checkpoint, not a replacement for released
v0.0.10/checkpoint-008. Host package: 0.8.3.dev1. Runtime builds identify
themselves as v0.0.11-dev1. Native geometry and sustained audio acceptance are
in progress; this is not yet a fixed or faster playable release.

## Implemented in this source snapshot

- Restored the requested README introduction, credits, community thank-you,
  upstream acknowledgements and direct GOG/Steam links.
- Clarified public exclusions, GPLv2 runtime / GPLv3 host boundary, original
  copyright ownership and OpenMW's reference role in static asset conversion.
  Earlier opening captures used an external OpenMW.
- Added Linux `build.sh`, Python coordinator, prerequisite checks, stage logs,
  source hashes, immutable run names and failure receipts. Inputs and outputs
  stay external. See [Linux build](LINUX_BUILD.md).
- Removed canonical title PCM from both world music groups, including copies
  under different names. Added separate shuffle/history state, Shift+F5/F6,
  two PCM buffers and 4 KiB refill slices.
- Added music events with played/total frames and renderer overflow counters.
- Recorded the graphics/audio/Balmora/NPC/dialogue/interior/relaunch queue in
  [ROADMAP.md](ROADMAP.md); later gameplay features are not claimed complete.

## Checks completed

All 47 host tests passed. Generated PCM is checked sample by sample against the
actual C player across buffer boundaries, tails and at least 18 full track
completions. Tests also cover Previous/Next history, modes, malformed playlists
and truncated streams. These checks are not emulator audio evidence.

The guided AGA build completed all eight stages from the owner's installed base
files using the documented SDK, qcc and ericw-tools. It generated an RDB HDF and
independently read back every payload. The qcc compile command was checked here.
A fresh Linux distribution or different toolchain has not been tested.

Source packaging checks an explicit file list, text-only contents, ZIP entries
and byte-for-byte source matching. ZIPs retain executable permission on
`build.sh`; `sh build.sh` also works when extraction drops it.

## Reproduction findings and open risks

The v0.0.10 renderer reported **Short 35 surfaces** in a town view. Its
800-surface pool can drop geometry, then fog colours the missing foreground.
Increasing the pool needs overflow and RAM measurements. This is separate from
the coarse convex building bake that fills recesses and merges pier decks with
supports. Full transforms, scales and finer terrain also need attention.

Replacement geometry experiments remain outside the public pipeline. Triangle
prisms and multipart world brushes exceeded BSP29 limits. A direct-surface
submodel trial separates visual meshes from collision; it must pass native
loading, rendering, collision and memory checks before adoption.

The owner's continuous-title report remains an acceptance case. The old
manifest demonstrably included title music in exploration. An unattended
reference run opened multiple songs, so continuous repetition was not reproduced
there; open counts alone do not prove full-song completion. New transition
events record exact progress to resolve that ambiguity on the native runtime.

Reference: FS-UAE 3.1.66, 68040/FPU, AGA, 2 MiB Chip, 16 MiB Fast, JIT/maximum
CPU, Kickstart 3.1 A1200 40.68. Existing hashes/settings are in
[checkpoint-008 validation](CHECKPOINT_008_VALIDATION.md). This is not evidence
of stock A1200 playability. Record subsequent native results separately.
