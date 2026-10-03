# Docker builder roadmap
## Current evidence - 2 October 2026

The allowlisted source/tools image, runtime input/export helper and asset-free
Docker CI job are implemented locally. The wrapper suite passed 433 tests with
3 skips and compiled the asset-free Amiga image. The final v0.0.26 helper/export
run passed all 3,551 NPC models, 2,526 terrain regions, strict actor-ground audit
with zero unresolved findings and verified HDF assembly. Its 3,489,693,696-byte
HDF has SHA-256 `da3f80b3d7ebefe30c53031fdd29c34a094d0b486328daa46739a4a5ad6364a3`;
Conversion elapsed was 1,566.061 seconds (26 minutes 6 seconds), excluding export, provisioning and emulator testing; the cached run reported 78 warnings. WinUAE 6.0.3
played the opening movie, entered Jiub's prison scene and responded to Enter/Escape.
Exported image-layer inventory review passed: image payload 2,119,364,274 bytes,
save archive 535,999,488 bytes, with no BSA, ESM, HDF, ROM or private input/build
paths in image layers. Hosted Docker CI is required before publication.

The earlier cold 35-minute-3-second run used rc1 identity; see its historical
[validation record](VALIDATION-DOCKER-2026-10-02.md).

The planning and native storage snapshots below are historical estimates; they
do not override the current evidence or establish a measured Docker peak.


Status: **local v0.0.26 helper/export validation passed; hosted CI and publication
remain pending**. Native Windows conversion and WinUAE game entry also passed,
with experimental Windows reliability limits still documented. The Docker
builder, read-only input helper and dedicated CI job are implemented. The local
wrapper suite passed 433 tests with 3 skips; full final-identity conversion,
strict actor-ground validation, verified HDF export and WinUAE game entry passed.
See [Docker builder](DOCKER_BUILD.md) and [v0.0.26 release notes](RELEASE-v0.0.26.md).
The first implementation should wrap the established Linux pipeline with its
full-content defaults and existing validation gates. Native Linux remains the
foundation; native Windows 11 remains experimental. A Linux container build on
Windows is a separate build-host result, not a native Windows validation result.

## User-supplied inputs and persistent outputs

Publish only AmiWind source and redistributable tools/dependencies. Every user
must provide their own Morrowind files. Never put original game files, converted
game assets, playable HDFs, ROMs, private test packages or machine notes in the
Docker build context or image layers, including intermediate/cache layers.

Use an explicit small build context and an allowlist; add `.dockerignore` as a
second boundary. Verify an exported image/layer inventory before publication.
Do not accept game files as `docker build` arguments or COPY sources.

At runtime, accept separate paths for a read-only game-data mount, a writable
build/output mount and persistent validated caches. Use the existing converter;
keep output ownership usable by the host user. An emulator remains a separate
host-side test using the user's own ROM and locally generated image.
Docker's [bind mounts](https://docs.docker.com/engine/storage/bind-mounts/) support
read-only inputs and persistent host outputs. Mounted files still occupy host
disk space; they need not be duplicated inside an image.

## Disk budget: measured starting point, not a container requirement

A native Windows snapshot taken during the full v0.0.25 conversion on 2 October
2026 measured these logical file sizes. Terrain and HDF assembly were unfinished.
These figures describe this recipe and input edition, not a guaranteed minimum.

| Component | Observed GiB | Interpretation |
| --- | ---: | --- |
| Active build | 3.061 | Partial run, including 1.176 GiB terrain work |
| Shared validated model cache | 0.242 | Reusable across build names |
| Installed Windows tools and downloads | 2.989 | Includes 0.461 GiB download cache; Linux image size unmeasured |
| Existing game installation | 3.352 | User supplied; can remain in a read-only host mount |
| Older build runs | 2.259 | Retained development history, excluded from one fresh build's budget |

At that snapshot the log had reported about 1,591 of 2,526 terrain regions.
A simple linear projection puts conversion work at roughly 4 GiB before image
assembly; region sizes vary and log output is ordered, so this is only a rough
projection. The builder additionally stages payloads, creates temporary partition
images and assembles the combined HDF. A private emulator working copy adds
another HDF. Final HDF readback currently reads files into memory; it does not
require another complete on-disk readback copy. Temporary partitions are removed
after successful final verification, so final retained size understates peak use.

**Initially reserve 40 GiB free for a container build**, beyond
an existing mounted game installation. Use this starting budget provisionally; reduce it only after measuring
a complete build. It is a conservative planning allowance
for conversions, staging, images, dependencies and Docker image/build caches,
not a measured Docker minimum or a claimed container download size. Multiple
retained builds, toolchain versions and Docker VM storage can require more.
Replace the allowance with measured cold-build peak usage before publishing
installation requirements. Do not promise that containerization reduces space.

## Implementation and acceptance

1. Preserve the current native build and record its complete outcome. Re-measure
   disk use before and during image staging, partition creation, combined-image
   validation and the emulator working copy. Record logical versus allocated
   size, cleanup and overlapping lifetimes; keep old runs separately accounted.
2. Produce a tool-only Linux Dockerfile from official sources with recorded
   dependency versions/checksums, a pinned base digest and tool license review.
   Maintain one conversion implementation; expose input/workspace/jobs options.
3. Add a disk preflight that examines the actual output/cache filesystems and
   estimates the remaining peak requirement plus margin. Preserve completed
   outputs on failure; never omit models, galleries or validation to save space.
4. Verify a fresh full build, a build reusing validated caches, interruption and
   child-process cleanup. Document exact cache reuse; do not promise general
   resume support that the pipeline does not implement.
5. Test Linux and a supported Docker Desktop Windows backend independently.
   Compare cold/cached elapsed time, CPU/RAM limits and mount I/O. On Windows,
   benchmark host mounts against Linux-managed storage before recommending a
   layout; account for Docker's VM disk and user-accessible output exports.
6. Publish measured image download size, unpacked tool size, workspace peak and
   recommended free space. Document offline operation after provisioning,
   volume ownership, removal/retention of caches and an input/output CLI example.

Container implementation and validation follow rc1. Preserve local conversion
outputs and validated caches during provisioning; do not move active workspaces. The 40 GiB figure is a free-space
budget, not the published image size or an automatically imposed VM disk cap.
See the [main roadmap](ROADMAP.md#docker-builder-planned-for-v0026),
[capacity requirements](BUILD_TOOLKIT_ROADMAP.md#capacity-before-conversion) and
Docker's [Windows WSL 2 backend](https://docs.docker.com/desktop/features/wsl/).

### Later staging observation

After all 2,526 terrain regions passed, but before partition/final-HDF creation,
the same active run had grown to **8.009 GiB**: 2.471 GiB image staging,
2.446 GiB scene payload (including copied world maps), 1.837 GiB terrain work
and the other conversion directories. This supersedes the simple 4 GiB partial
projection for total conversion/staging needs. Keep the earlier snapshot as an
example of why a mid-build size cannot establish peak usage.

## Input helper scripts

Provide Windows `.cmd`/PowerShell and Linux shell entry points that accept a
Morrowind installation or Data Files directory and a separate writable workspace.
Validate the required files, resolve paths with spaces, and construct `docker run`
arguments without shell interpolation. Show the selected input/output paths and
mount the original game installation read-only. The wrapper should handle the
container's fixed internal paths, worker budget and persistent cache automatically;
users should not have to write Docker volume syntax. Reject input/output overlap.
Record the image digest and build receipt; preserve normal failure exit codes.

## Required pre-handoff Linux validation

Run the complete Linux test suite and an asset-free Amiga compile gate inside the
project Docker environment before every production handoff. Record commands,
tool versions, logs, exit status, skips and failures. Focused tests do not replace
the full suite. Report native Windows checks separately: Docker on Windows is a
Linux build host, not native Windows validation. Do not create or execute native
Windows helper binaries for this gate. Clean up only Docker/WSL resources started
for the run and confirm prior state restoration. Publication is the owner's
Linux-only step. Failed or unrun gates remain open.
