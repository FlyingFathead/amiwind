# AmiWind v0.0.26 — validation notes

## Local validation result

The final helper/export run completed the full conversion on Windows 11 using
Docker Desktop's WSL 2 Linux engine. All 3,551 NPC models and 2,526 terrain
regions passed. The strict packaged actor-ground audit passed with zero unresolved
findings, and HDF assembly and export completed successfully.

The verified v0.0.26 HDF is 3,489,693,696 bytes with SHA-256
`da3f80b3d7ebefe30c53031fdd29c34a094d0b486328daa46739a4a5ad6364a3`. The cached
conversion elapsed was 1,566.061 seconds (26 minutes 6 seconds), excluding export, provisioning and emulator testing, and it reported 78 warnings. The
local wrapper suite passed 433 tests with 3 skips. The exported image-layer
inventory audit passed: image payload 2,119,364,274 bytes and save archive
535,999,488 bytes. No BSA, ESM, HDF, ROM, or private input/build paths were found
in the image layers.

WinUAE 6.0.3 played the opening movie, entered Jiub's prison scene and responded
to Enter/Escape controls. This records emulator game-entry validation; it does
not establish real-hardware performance or a complete gameplay playthrough.

## Historical cold run

The earlier cold Docker conversion took 35 minutes 3 seconds and produced an
HDF of the same size with rc1 runtime identity. It passed the full content and
strict actor-ground checks and entered the game in WinUAE. Its detailed receipt
is preserved in [the Docker validation record](VALIDATION-DOCKER-2026-10-02.md).

## Publication status

Public publication requires hosted Docker CI to pass for the exact release
commit. This local validation record does not itself establish publication.
Native Windows/MSYS2 remains experimental, with worker and cancellation limitations
recorded in the [Windows build roadmap](WINDOWS_BUILD_ROADMAP.md).

AmiWind is GPL-licensed source and tooling. Users must provide their own legally
obtained Morrowind files and Amiga Kickstart ROM; no proprietary game data, ROMs
or generated playable HDFs are included in the public source package.