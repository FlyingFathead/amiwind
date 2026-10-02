# Docker validation - 2 October 2026

## Historical cold rc1 conversion and runtime checkpoint

A cold full conversion using Docker Desktop on Windows 11 with the WSL 2
backend passed. The tools/source-only image used the existing Linux pipeline,
24 workers, read-only owner-provided game inputs in a Linux named volume,
a separate writable Linux build/cache volume and `--network none`.

- All 3,551 NPC gallery models converted; zero failures.
- All 2,526 terrain regions completed.
- Strict packaged actor-ground audit passed: zero unresolved findings.
- Final HDF assembly, validation and output hashing passed; container exit 0.
- Build timing: 2102.905 seconds (35 minutes 3 seconds), excluding provisioning
  and emulator testing; container lifetime about 35 minutes 9 seconds.
- Image: 3,489,693,696 bytes, SHA-256
  `47c07eac806af1ebe21d12e2eaf17daacdbec36d56bfc314ba425be2f7a1398e`.
- Actual runtime identity: **0.0.26-rc1**, not the final v0.0.26 release.
- Engine compiler log contained 78 warning lines; this is not a warning-free build.

A private HDF copy booted in WinUAE 6.0.3, played the opening movie and entered
Jiub's prison scene. Enter accepted the name prompt; Escape opened the menu.
This is limited game-entry/input smoke testing, not complete gameplay testing.
The emulator was closed afterward. Configuration: AGA/PAL, owned A1200
Kickstart 3.1, 2 MiB Chip, 16 MiB Z3, 68040/FPU, JIT and fastest CPU.

## Windows mount performance observation

An initial read-only Windows bind-mount attempt was interrupted before
conversion because input verification remained waiting on filesystem RPCs for
more than 195 seconds. Its exit 130 records deliberate cancellation, not a
compiler crash. Streaming the private inputs into a Linux named volume took
107.765 seconds; the next input verification completed in 5.4 seconds.
Linux-managed storage is recommended for Windows Docker conversion workloads.
These timings describe one run and do not establish a universal speedup.

## Tools image and CI scope

The tested tools/source image occupied 2,119,141,968 bytes in Docker's image
inventory. A Docker save archive was 535,948,800 bytes; this is not a measured
registry download size. Exported layer names were checked for private input,
build paths, game archive/master files, ROMs and HDFs; none were found. Inputs
and outputs were runtime volumes, excluded from the allowlisted build context.

The historical rc1 public-wrapper check passed 430 tests with 3 skips and compiled the
asset-free Amiga image. A dedicated Docker GitHub Actions job is implemented
locally. That historical checkpoint alone did not establish final-version
acceptance; the final-version results are recorded below. Hosted CI gates publication.
Keep native Linux and Windows parity checks alongside Docker validation.

Reserve 30-40 GiB of free host storage provisionally. This is headroom, not
preallocated space or a measured minimum. Build caches, temporary image assembly,
private staging, exported output and emulator working copies have overlapping
lifetimes; final retained size is not peak consumption.

## Final v0.0.26 acceptance

The final public runtime helper completed full conversion and exported the
result successfully using 24 workers and offline runtime networking. All 3,551
NPC models and 2,526 terrain regions completed; the strict packaged actor-ground
audit passed with zero unresolved findings. The cached conversion elapsed
1,566.061 seconds (26 minutes 6 seconds), excluding provisioning, export and
emulator testing. Engine compilation retained 78 warning lines.

The exported HDF is 3,489,693,696 bytes, independently hash-verified as
`da3f80b3d7ebefe30c53031fdd29c34a094d0b486328daa46739a4a5ad6364a3`.
WinUAE 6.0.3 displayed final v0.0.26, played the opening movie, entered Jiub's
scene, accepted a fantasy character name and responded to the Escape menu.
This is a game-entry/input smoke test, not a complete gameplay playthrough.
The emulator was closed after testing.

The final local wrapper check passed 433 tests with 3 skips and produced the
asset-free Amiga image. Final tools image inventory: 2,119,364,274 bytes; saved
archive: 535,999,488 bytes. All layer member names were checked; no BSA, ESM,
ROM, HDF or private input/build paths were found. Hosted CI remains the
publication gate for the exact pushed commit.
