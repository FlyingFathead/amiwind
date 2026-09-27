# Checkpoint-014: pier repair, hands, menu and diagnostics

Runtime **v0.0.13-dev1**, public pipeline **0.10.0.dev1**, 27 September 2026.
Created by FlyingFathead a.k.a. Horstator. Thanks to ChaosWhisperer.

## Delivered scope

- Decode BSP face-plane indices as unsigned 16-bit and reject indices outside
  the plane lump. The original scene has 34,643 planes: signed-short decoding
  corrupts later dock/gate/rock faces. The extended-sea scene has 34,733 planes.
  No bank switching, larger face field or per-face RAM increase is needed.
- Set render buffers to 10,240 surfaces / 20,480 edges, up from 8,192 / 16,384.
  This costs 256 KiB inside the existing 8 MiB heap. It restores capacity, not
  a guarantee of fast rendering. Larger trial buffers caused model-cache churn.
- Bake Nord first-person hands: F draw/sheath, Mouse1 visual punch; no combat
  hit, damage or stamina system. Preserve Quake walking bob.
- Escape menu supports Return and confirmed Exit; New/Save/Load/Options are
  greyed out. Clear held input at menu boundaries. Music continues in the menu.
- Add live XYZ below the viewport, debug master/aliases and default-off showram.
  Include the reserved strip in the Amiga video-update rectangle.
- Extend the simple Z=0 sea/enclosure to +/-2048 local units. This is explicitly
  a temporary demo placeholder, not converted surrounding terrain or islands.
  `amiwind_debug_sealevel on/off` toggles its visible surface without changing
  water contents/collision/swimming. Default on; independent of debug text.
- Export private ordered voice records and static actor candidate indices through
  the guided builder. The runtime still uses one Hello per actor appearance.
- Add pitch-directed noclip flight with bounded speed/no inertia, numbered
  safe recall point 0 and a normal-exit restart reminder.
- Preserve owner-confirmed town-square repair, remaining shack-wall reports,
  vicinity/ship scope and interior work in docs.

## Correctness and native evidence

76 host tests pass, including real patched face loading across indices 32767,
32768, 34642 and 65535 and rejection outside the declared plane count. The same
fixture fails against the prior signed loader. Menu disabled-options/confirmation,
HUD booleans and refresh, held input, hand-only bake and ordered dialogue fixtures
join the existing collision, movement, culling, depth, audio and filesystem checks.
Public fixtures contain fictional/synthetic data only.

The old native dock view remains broken with distance culling off or depth slop
zero. Source/BSP deck polygons were present; correcting plane decoding restores
them at the same camera. A diagnostic attempt at r_novis was unsupported and is
not PVS-disable evidence. Private instrumented investigation builds are not shipped.

Native route `pier014-native-r8`: initial strafe, hand draw/punch/sheath, coordinates,
sea off/on, pier views at (540,-200,65), (340,-200,65), standing on the deck near
(545,-327,39), forward deck movement to about (505,-300,39), rock-side view,
recovery/walk, debug master off/on, menu and confirmed exit to DOS. Captures and
console queries confirm the actual settings and changing XYZ. A final focused native run checks pitch-directed flight, explicit vertical
movement, recall point 0, unsupported-ID rejection and the corrected loading
label/restart hint. Its evidence is recorded below.

Earlier r6 used emulator-reserved F11/F12; r7 used hardwired console F10 during
a scripted menu test. Neither is counted as a successful complete exit/profile
run. The corrected r8 harness uses ordinary numeric diagnostic bindings.
These bindings are test-only; the delivered image retains normal controls.

## Memory and rendering measurements

FS-UAE route r8, extended sea and final buffer sizes:

| Counter | Result |
| --- | ---: |
| Frames / elapsed | 1,417 / 69,281 ms |
| Surface / edge overflow frames | 0 / 0 |
| Maximum surfaces / edges observed | 8,587 / 17,167 |
| Hunk used | 6,935,536 bytes |
| Free Chip / Fast at exit | 1,796,432 / 6,106,576 bytes |
| World / entities / C2P | 59,320 / 631 / 189 ms |
| Worst frame, including startup | 1,013,963 us |
| Audio late updates, excluding warmup counter | 2 |
| Missed audio frames | 7,218 |
| Audio warmup updates / missed frames | 1 / 3,704 |
| Music read slices / bytes | 388 / 1,589,248 |
| Music read errors | 0 |

Each of the Nord hand, Fargoth and guard models was opened once on this route.
The deliberately oversized 16,384/32,768 trial added 1 MiB and repeatedly reloaded
models as cache room shrank. The selected 10,240/20,480 buffers add 256 KiB.
The sea also increases world data; total hunk change is not just buffer growth.
Amiga-compiled struct sizes are 64 bytes per surface and 32 per edge.

These are mixed acceptance-route counters, not a controlled paired frame-rate
benchmark. Restored faces add real rendering work; comparing against a broken
scene that drops faces is not evidence of an optimization. World rendering still
dominates. Audio deadlines remain imperfect, especially around startup/stalls;
zero file read errors does not imply glitch-free audio. All 18 installed tracks
are included, with the existing shuffle/history implementation, but this short
route does not repeat the earlier multi-song natural-completion validation.

## Exact runtime context

FS-UAE **3.1.66**, A1200/AGA/PAL, **68040-NOMMU + internal FPU**, 2 MiB Chip,
16 MiB Z3 Fast, JIT/max, 24-bit addressing off, keyboard joystick disabled.
Resolved reference: CPU=68040, FPU=68040, MMU=0, JIT CPU/FPU=8192.
No Workbench desktop. No stock-A1200 speed or physical-Amiga certification.
WinUAE versioned preset is guidance, not a local WinUAE execution result.

Kickstart 3.1 A1200 **40.68**, 524,288 bytes, SHA-256:
`6d43840d4099a74170ea0f0425b6257c3891ebcaa39c4d1840075a9ab22b5707`.
FS-UAE executable SHA-256:
`b729fe233a6507daed7fea6fbe8cfc417da523239d4a43037dd57203858e4f37`.

Compiler: AmigaPorts GCC 16.2-rc11 / 16.2.0b20260825082934, 68040/FPU.
Pinned AmiQuake: `9c62d905151614af3e788ae3145a0d4ecc8a7bb8`.
Archive SHA-256: `43353034beb2a43b1af82c735f93c0a8bee8129c1b93d7ba152dd8e60ad3721c`.
Image: 134,250,496 bytes, RDB with one 128 MiB FFS partition, normalized legacy
root field. Every image payload is read back and compared by the builder.
Final executable/image hashes follow below.

## Known limits and next milestone

Position-specific shack-wall disappearance remains open. Expanded sea does not
restore omitted land or objects. The prison-ship hull is excluded by object type
and the origin cutoff, while its hatch can render; this is not implemented
character-generation departure logic. See SEYDA_NEEN_SCOPE.md.

World geometry remains resident. Census and Excise interior/linked entry-exit,
complete vicinity/NPC registry, varied voice filtering, dialogue presentation,
walking routes, combat damage, Balmora and saves
remain on ROADMAP.md. Current noclip E/Q provides explicit up/down; aw_recover
returns to a safe town spawn. No owner confirmation of checkpoint-014 yet.

## Final flight/relaunch check and hashes

`flight014-native-r1` uses the delivered executable and image on the same
reference machine. At pitch -60, forward flight rises from (100,100,-40) to
about (100,178,84), then remains there with movement released. Shift+forward
reaches about (100,224,156). At pitch +60, forward flight lowers Z from 180
to 98; E raises it to 176 and Q lowers it to 92. Recall point 0 returns to
(16,44,60), movement type WALK, and subsequent strafe works. The script also
sends an unsupported recall ID before recovery; only ID 0 is implemented.

Normal exit visibly prints the correct version and restart reminder. Typing
`amiwind` at DOS relaunches the scene, and a second confirmed Exit returns to DOS
with the reminder again. Screenshots retain the first flight sequence; the final
profile/debug files belong to the second, shorter launch and must not be used
as aggregate measurements of the first flight. No ERROR.TXT was produced.

Host flight checks use a 0.5% velocity tolerance because the engine uses
approximate vector normalization. They cover pitch, explicit vertical motion,
release-to-stop, diagonal speed bounds and boosted input speed.

| Artifact | SHA-256 |
| --- | --- |
| Final HDF | `17d805f00aa990acbdb72d6bfb6c4d849caa73e9a6007e8048c2d07ad31285ee` |
| Final AmiWind executable | `fa63e8ef4f95c90dbba16d5f0894e544632b538ab389a99e1d11c9b501a539eb` |
| 68000 preflight | `2b67e576a2add2479f654c8183c75c9c2cc3625dc343f28d2033c95db836aa02` |
