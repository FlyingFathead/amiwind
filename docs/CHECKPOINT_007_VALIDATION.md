# v0.0.9 checkpoint-007: startup dependency hotfix

Date: 27 September 2026. Pipeline source: 0.8.1. Supersedes checkpoint-006 for
boot compatibility; the old image and performance evidence remain immutable.

## Failure and cause

The user reported a LIBS/icon.library requester followed by return code 20 in
WinUAE. The old binary linked GetDiskObject/FindToolType through an unused
Workbench tooltype path; the C runtime requested icon.library before main.
This was reproduced with the user's uploaded 3.1.4 A1200 ROM. The user also
reported failure after selecting the supplied 3.1 ROM; the effective WinUAE
settings for that attempt were not captured, so a ROM change is not a proven
workaround for that setup.

The fix removes icon/tooltype parsing and desktop close/reopen code. It also
removes the explicit icon library open from the experimental CLIB2 adapter.
Shell command arguments and PROGDIR content loading are retained. Launching
without shell arguments uses the default argument list; icon tooltypes are no
longer supported. No Workbench or icon library files were added to the HDF.

Hyperion documents that icon.library and workbench.library are not resident in
its 3.1.4 ROMs. This explains why an otherwise unnecessary dependency can become
a boot failure in a bare-ROM image:
https://www.hyperion-entertainment.com/index.php/frequently-asked-questions/55-amigaos-314/196-why-are-workbenchlibrary-and-iconlibrary-no-longer-in-rom

## Artifact identity

| Item | SHA-256 / value |
| --- | --- |
| HDF | `fd7c88a5f34af455c587942cf6c453ad7f8355dcab2d303466ea17e562d22035` |
| Executable | `7fe43d89d6005f98c74b0c003402fc7eba13b3fa3a40bba3136660572600db77` |
| Base checkpoint-006 HDF | `8055c8bc26340166f93179246a0a1fe96fe90822739942e413f19dca134df7d7` |
| KS3.1 A1200, 40.68 | `6d43840d4099a74170ea0f0425b6257c3891ebcaa39c4d1840075a9ab22b5707` |
| KS3.1.4 A1200, 46.143 | `f797db0b99856d9c8219ee1f11e16285fd7dbdc0cbca2e149befd3a3986eb007` |
| FS-UAE executable | `b729fe233a6507daed7fea6fbe8cfc417da523239d4a43037dd57203858e4f37` |
| HDF size | 134,250,496 bytes; 128 MiB FFS partition inside RDB |
| Executable size | 512,248 bytes, 584 bytes smaller than checkpoint-006 |

Compiler: AmigaPorts GCC 16.2-rc11, 16.2.0b20260825082934, 68040/FPU,
-O1, independent C2P, GPL C spans. Built from a fresh pinned upstream extraction
and the public patch. The corresponding-source package includes the modified
runtime source and build instructions. No extracted assembly is compiled.

The filesystem audit finds exactly one changed payload: `AmiWind`.
All world, texture, configuration and music files match checkpoint-006 byte for
byte. A fresh light compilation produced different packing, so the hotfix
reuses the previous compiled BSP to preserve this boundary. Every payload was
read back from the final HDF and compared with its expected SHA-256.

## Regression checks

All **40 host tests passed**, including the new executable dependency tests.
The linked-binary checker rejects the actual old executable for icon.library
and accepts the new one. The engine builder and image assembler both invoke
this check. It checks Hunk identity and known desktop-library strings; it is
not a complete dynamic dependency resolver or a substitute for native boot tests.

The boot banner, HUD and executable version identify v0.0.9. The release HDF
was tested through copies and its original hash was verified after validation.
Archive candidates are checked in incoming storage before immutable promotion.

## Native smoke tests

FS-UAE 3.1.66, Ubuntu package 3.1.66-2build2. Both final-HDF runs used A1200/AGA,
PAL, 68040/FPU, 2 MiB Chip, 16 MiB Zorro III memory, JIT, maximum CPU speed,
320 x 200 and the UAE RDB hardfile controller. Effective settings were checked
from debug.uae. This is emulator functional validation, not physical Amiga
performance. Zorro III here describes UAE's memory setup, not a stock A1200.

| Check | KS3.1 A1200 | KS3.1.4 A1200 |
| --- | ---: | ---: |
| Boot to textured scene | Passed | Passed |
| Movement / mouse look / distance input | Passed | Passed |
| Music next/mode input | Passed | Passed |
| Escape returns to DOS prompt | Passed | Passed |
| Frames / measured ms | 4,682 / 65,050 | 4,030 / 55,992 |
| Worst frame, microseconds | 25,992 | 27,564 |
| Hunk use, bytes | 3,766,368 | 3,766,368 |
| Music read errors | 0 | 0 |
| Late mixer updates / missed frames | 1 / 1,745 | 1 / 1,380 |
| Track history | 6,0,11 | 6,0,11 |

Neither final-image run displayed the icon requester or wrote ERROR.TXT. Captured
scene and exit screenshots, coordinate logs, counters and effective settings are
in the private package. The source HDF hash is unchanged after both tests.

These short tests target the startup fix. They do not replace checkpoint-006's
four-minute song-completion test or demonstrate an audio/performance improvement.
The late-update issue remains. WinUAE itself and physical hardware have not
been tested here. The 020/no-FPU target remains unresolved; use 040/FPU settings
for this binary. No NPC, geometry, streaming scheduler or gameplay changes are
part of the hotfix.
