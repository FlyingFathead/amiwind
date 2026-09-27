# Checkpoint-011 — v0.0.11-dev4 / source 0.8.3.dev4

27 September 2026. Focused repair of a blocked fresh-boot player spawn.
NPC conversion research is saved; NPCs are not in this playable image yet.

## Reproduced fault and repair

The owner reported working mouse look but no WASD movement, then confirmed
that noclip released the player. A fresh native dev3 test reproduced this:
W/S/A/D and jump left the player at exactly (16, 44, 74). Input was reaching
the engine. The nominal spawn intersects converted architectural collision.
The prior checkpoint's movement test ran after recovery and therefore missed
this startup regression. Its floor sweep was not a walking-start acceptance test.

`AW_FindSafeSpawn` now tests the actual standing hull against world and entity
collision. A bounded 9 x 9 neighborhood search selects grounded space with
headroom and a supported short step in all four cardinal directions. It rejects
initial overlaps, blocked sweeps, steep hits and unsupported ledges. The search
runs once on new player placement or explicit recovery, not each frame. Failure
leaves the existing position intact and prints a console diagnostic.

New-player placement and `aw_recover` share this check. The native search selected
(-48, -20, approximately 61); normal movement subsequently settles on the local
sloped terrain. This is not a general repair of every approximate collision hull.
Sliding on slopes, ledge handling and tight approaches still need work.

## Native acceptance

FS-UAE 3.1.66, A1200/AGA/PAL, 68040/internal FPU, 2 MiB Chip, 16 MiB Z3,
JIT enabled, CPU maximum, 24-bit addressing off, UAE RDB hardfile and no keyboard
joystick. Emulator SHA-256:
`b729fe233a6507daed7fea6fbe8cfc417da523239d4a43037dd57203858e4f37`.
No local WinUAE or physical-machine test is claimed.

From a fresh copy, before noclip or recovery, all four WASD directions changed
the player position. Console screenshots and the native walk profile record
before/after positions. Recovery was then tested separately and walking resumed.
The game quit cleanly to the shell. This is a startup check, not a full town sweep.

58 host tests passed. A new synthetic test exercises an overlapping preferred
spawn, rejection of a narrow obstacle top, grounded placement and preservation
of the old pose when no solution exists. Existing actual-runtime collision,
culling and door-depth tests still pass.

The BSP is byte-identical to dev3. Renderer, input and music implementation files
are unchanged. The owner reports that dev3 doors now behave correctly and town
details are present. This repair preserves that work.

## Artifact identity

| Item | SHA-256 |
| --- | --- |
| HDF, 134,250,496 bytes | `f6ebed78e9c805522bf85bef174f0ed04b0cdb876a15deb220497f82c2a9847e` |
| Runtime | `9b0580ad5a0981415267ee4be0cfbba56ecec7b5c271179cc6901cfff7e2722c` |
| Boot checker | `d297f41be6f96fabc27074d34a073782f053e72c14dcf78ca9a4c7a1254c75d7` |
| KS3.1 A1200 40.68, 524,288 bytes | `6d43840d4099a74170ea0f0425b6257c3891ebcaa39c4d1840075a9ab22b5707` |

The ROM in the preceding ZIP matches the tested local bytes; its CRC32 is
1483A091 and its native longword checksum is FFFFFFFF. The owner resolved their
ROM-selection problem but has not supplied the hash of their effective working
ROM. Do not declare that selection identical or claim that the supplied ROM was
repaired. Public packages contain no ROM. Keep the owner's working licensed
A1200 ROM selected and record its hash for future reports.

## Resource measurements and limits

The diagnostic run recorded 1,363 frames / 78,739 ms, 6,304,688 hunk bytes,
5,769 peak surfaces and 9,979 peak edges, with zero surface/edge overflow.
The previous baseline remained trapped in a different view; these are not
matched performance routes and establish no speedup or regression percentage.
At quit the runtime reported 1,796,432 free Chip bytes and 6,084,552 free Fast
bytes before releasing its own allocations.

There were two late audio updates, including one warm-up event, and zero read
errors. One approximately one-second frame remains in this diagnostic run.
Audio is not certified glitch-free; no full song completed in this short test.
The 18-song on-disk collection and playlist/history code are unchanged.

The builder verified the clean image payload and normalized legacy FFS root
metadata. The distributed HDF is the unmodified build output, not the emulator
working copy. Earlier immutable ZIPs remain available. New source/private
archives are staged and checked before promotion.

See [NPC research](OPENMW_REF_NPCS_AND_DIALOGUE.md), [roadmap](ROADMAP.md) and
[optimization history](OPTIMIZATION_HISTORY.md) for the next work.
