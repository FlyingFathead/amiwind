# v0.0.16 validation

Date: 28 September 2026. This records local validation before owner publication.

## Completed

- **120 host tests passed** with no skips. They include compiled native palette
  checks for blue water, red damage on land, combined water/damage, damage fade
  and surfacing. Existing collision, menu, culling and other checks remain.
- Fog-depth coverage includes 540 and menu reset asserts 540. Version mismatch
  is rejected. Mocked publication checks reject a wrong account, prevent tagging
  after failed CI and permit only the explicitly named public source assets.
- Native 68040/FPU engine and 68000 boot preflight compiled using AmigaPorts
  GCC 16.2.0b20260825082934 and vasm 1.9d. Recorded source hashes match the
  packaged native tree. Amiga Hunk checks passed.
- Playable RDB/FFS image metadata and every filesystem payload were read back
  and compared with the build inputs. The two BSP scenes and 18 music streams
  remain byte-identical to the checkpoint-017 playable baseline.
- FS-UAE 3.1.66 booted a writable copy to the prison interior, changed to town
  and back, showed version v0.0.16, and exited cleanly to DOS. The normal boot
  output shows the owner-approved credits and project URL.
- Console reported the initial fog distance as 540. Native graphics menu showed
  540, adjusted to 530 and reset to 540.
- Native water check at player origin `(900,-900,-30)`, yaw 135, pitch 0 showed
  the blue tint. BSP contents at eye height were independently checked as water.
  Raising the player to Z=100 removed the tint. This used a diagnostic noclip
  camera; it is not certification of every swimming/collision path.
- The separate asset-free HDF booted to its notice with v0.0.16, exact boot
  credits and URL. It contains no ROM or game data.

The first automation pass confirmed boot/defaults/scene changes, but its menu
key sequence was mistimed and its underwater camera was inside solid terrain.
Those screenshots are not acceptance evidence for menu or water behavior. A
second pass used explicit diagnostic bindings and a verified water location.
Both runs remain in private evidence.

## Reference machine and scope

FS-UAE: A1200/AGA/PAL, 68040-NOMMU with internal FPU, JIT/max speed,
2 MiB Chip and 16 MiB Z3 Fast RAM, 24-bit addressing off. Kickstart 3.1 A1200
40.68 supplied privately. These are emulator checks, not stock-A1200 or physical
hardware performance measurements.

Existing prepared scenes and converted music were reused. Full clean conversion,
fresh dependency installation, Windows/WSL execution and hosted GitHub CI have
not been run here. The publisher waits for CI on the owner's pushed commit.
Native red damage application is exercised in the host-compiled real engine
routine; this update does not introduce or certify drowning/combat gameplay.

## Exact build identities

| Output | SHA-256 |
| --- | --- |
| `AmiWind-v0.0.16.hdf` | `2718e873abcc4c8eae573e3ba7c03f4f3b80c6311f35dd2e83f2316a6d9dea66` |
| Playable `AmiWind` executable | `b7d87bc141dd1b72d8b77f44b8011cd74b9968d5d50e31be2774005aa8a476b3` |
| `AmiWindCheck` | `9824a717f28cc6a35433eb69f1d3c1973d83622fd6a7937a04209aa9cfdcf03b` |

Private receipts include tool/source hashes and the supplied ROM identity.
Public ZIP checksums are sidecars rather than self-referential archive contents.
Source/patch/private archive gates are recorded in the delivery report after
packaging. Existing archives and original game inputs remain unchanged.
