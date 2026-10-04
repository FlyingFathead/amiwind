# v0.0.28-rc1 — Trees and Grass, Day and Night

Historical V1 development checkpoint. Stable identity0.0.28 is now in preparation;
this record and its rc1-labelled captures are preserved and do not certify the
current V3/night/guard runtime or final package. See [stable preparation](RELEASE-v0.0.28.md).

Candidate record, 4 October 2026. Bounded native day/night checks passed;
canonical terrain joins and NPC owner/overlap support errors still block full
release acceptance. Publication is pending; v0.0.27 remains the latest release.

## What is in the candidate

- Original-placement exterior foliage using 76 shared sprite types, while
  preserving rocks, joined giant mushrooms and detailed Balmora mesh foliage.
- A shared exterior sky resource and scrolling clouds, with all 301,751 local
  sky-enclosure faces removed from the checked 2,664 exterior maps. Interiors
  retain their separate environment policy.
- Persistent day/night time, coordinated sky colors and distant fog, and a
  default-on automatic cycle. `dbg daynightcycle` accepts `1/0`, `true/false`
  and `on/off`. Explicit time changes and T waits remain available when paused.
- Static foliage-link growth with bounded overflow pages and matching memory
  accounting, plus the current standalone 3D Map Inspector and optimization tools.

The sky/fog colors use source Clear-weather references quantized to the existing
palette. This first approximation has no integrated sun, moons, stars/nebula
texture, regional weather or nearby-world relighting. Those are follow-up work.

## Validation checkpoint

| Check | Recorded result |
| --- | --- |
| Linux Docker full suite | 764 discovered, 760 passed, 4 explicit skips, zero failures/errors |
| Windows full suite | 764 discovered, 678 passed, 86 explicit skips, zero failures/errors |
| Amiga target cross-compile on both hosts | Passed; 205 normalized engine sources matched, and complete executables are byte-identical |
| New clock/sky/fog native fixtures | 63 Linux methods passed, including sanitized sky/fog and static-link cases |
| Refreshed HDF assembly and integrity | All 10,748 files read back; zero allocation-ownership defects |
| Native009 bounded checks | Exercised aliases/clock, profile time, wait-dialog rendering and shutdown passed; 4,024 frames with zero edge/surface overflows |
| Full terrain/NPC gameplay acceptance | Blocked by regional terrain joins and owner/overlap support inconsistencies |
| Public release / hosted CI | Pending |

Linux skips three Windows-only tests and the Node wrapper unavailable in the
offline container. Windows runs its platform and inspector checks; the native
C fixtures execute in Linux. Both actual normalized-source target compiles produce
the same 719,636-byte engine, SHA-256
`f19ea3089bfb73b3bea801334f51a76a722c54316f471d8d1271807347f3d2d2`.
The earlier 757-test checkpoint and image006 native route remain historical
evidence; image006 predates the current sky/fog and cycle-toggle correction.

Native009 restored a profile's saved 15:45 after the clock was changed to 21:15.
The later autosave rejection followed a raw debug map load that reset health
to 100 against the retained profile maximum of 55. Validation retained the prior
saves. This establishes a debug-route state inconsistency, not an ordinary
transition defect; a valid-profile normal-transition native retest remains pending.
Wait-dialog rendering does not establish every wait duration. The native result
is bounded to its recorded WinUAE route and does not certify whole-world gameplay.

The checked conversion includes 2,723 maps. Aggregate sky conversion saved
137,703,336 disk bytes against the untouched exterior set, counting the single
32,768-byte shared asset once. Reserve warnings, actual heap limits and native
measurements remain separate; this disk total is not a RAM saving and predates
the larger diagnostic canonical terrain replacement. The 16 modeled reserve
shortfalls remain warnings needing adjustment; actual allocation failures remain
errors.

Canonical terrain clipping remains under repair. Candidate034 passes its local
geometry checks but introduces mismatches at three neighboring joins and requires
coherent NPC fitting across owner cores and their overlap copies. It is not accepted,
and candidate035 remains pending. Rejected terrain trials and the current
regional blockers are retained with their costs and causes in the
[terrain record](CANONICAL_TERRAIN_CULLING.md) and [bug journal](BUG_JOURNAL.md).
No complete world-wide buried-geometry removal is claimed.

## Public and private outputs

The public handoff contains source, documentation and explicitly selected
development screenshots. Game HDFs, converted assets, original game files and
ROMs remain private. The owner publishes the checked source from Linux after the
final package gates. The private reference profile is A1200/AGA/PAL, 68040/FPU/JIT,
2 MiB Chip and 16 MiB Z3 Fast RAM; physical-hardware performance is unverified.

See [day/night controls](DAY_NIGHT_AND_SKY.md), [gameplay media](GAMEPLAY_MEDIA.md),
[project state](PROJECT_STATE.md) and [known issues](BUG_JOURNAL.md).
