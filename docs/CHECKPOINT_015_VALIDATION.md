# Checkpoint-015: arrival ship and readable debug console

Runtime **v0.0.14-dev1**, public pipeline **0.11.0.dev1**, 27 September 2026.
Created by FlyingFathead a.k.a. Horstator. Thanks to ChaosWhisperer.

## Delivered scope

- Select the hull, gangplank, hatch and cabin door as one named assembly. Admit
  the specific ACTI hull; do not indiscriminately render activators/editor shapes.
  This is a **static arrival preview**, with no opening-script/removal logic.
- Reduce exterior detail on the host, preserve material/component groups and
  approximately project source UVs; ship material textures use 32-pixel tiles.
  Use the authored hidden collision subtree for separate approximate colliders.
- Add `debug`, `dbg` and `amiwind debug` space-separated commands and `debug help`.
  Existing underscore commands remain. Examples: `dbg coords on`,
  `dbg reset location 0`, `dbg pos`, `dbg console bg color black`.
- Fill the console with a solid configurable palette color, default black.
  No opacity, extra framebuffer or background disk read per draw.
- New original readable 5x7 bitmap font in existing 8x8 cells. Preserve the previous
  atlas on disk: `dbg font retro`; restore with `dbg font readable`. Choice affects
  all UI text and lasts for this session. One 16 KiB active atlas; an explicit
  switch temporarily uses a 16 KiB stack buffer and validates the file first.
- Retain pier index repair, hands/menu, movement/noclip, actor auditions, music
  shuffle/history and the temporary expanded sea from checkpoint-014.

## Host checks

**84 tests pass** against the final native source, including actual console
translation/dispatch, palette selection, clamped row fill, malformed/missing font
files and valid font replacement. Synthetic geometry tests cover assembly
completeness, ambiguous/deleted members, bounds selection, material/component LOD
and hidden RootCollisionNode separation with accumulated transforms. Existing
unsigned-face, depth, collision, movement, audio and filesystem tests remain.
No commercial assets appear in these fixtures.

| Conversion measure | Full exterior trial | Selected candidate |
| --- | ---: | ---: |
| Ship visible input/output triangles | 5908 | 1954 |
| Ship BSP surfaces after UV splitting | 9976 | 3931 |
| Ship approximate collision pieces | 217 from visual mesh | 60 from authored collision |
| Whole-scene BSP bytes | 4,130,044 | 3,382,832 |
| Whole-scene faces | 25,442 | 19,397 |

The authored collision source contains 581 triangles. There are 157 selected
static mesh instances / 57 unique variants in the final mesh report. Full-detail
and reduced counts are host results, not a matched native FPS benchmark. Source
triangles and runtime surfaces are different units. Small disconnected details
remain costly; a fine-detail texture bake is still future work.

## Failed trial retained

Native run `ship015-native-r1` used an 8 MiB heap. It rendered the ship and walked
part of the deck, then failed with `Cache_TryAlloc` for a 253,632-byte allocation.
Its hunk snapshot reached 7,927,984 bytes. Later captures from that failed run are
not successful menu/exit evidence. The typed blue-color test also had an extra
character from the harness's paging key mapping; it was repeated cleanly.

The final build reserves **9 MiB** inside the **same 16 MiB Fast RAM** reference
machine. Preflight requires 12 MiB free Fast and a contiguous 9 MiB plus 16 bytes.
This provides cache room; it is not a frame-rate optimization or proof of future
whole-world residency. Do not increase hardware requirements silently or compare
a failed run's temporary high-mark snapshot as a memory saving.

## Final native route

`ship015-native-r2`, delivered executable/image on a writable diagnostic copy:
startup walking before recovery; dock and broadside ship views; collision enabled
on the hatch/deck; forward movement from approximately (670,-507,75) to
(709,-467,69); gangplank standing near (628,-377,53); safe recall and walking;
help, blue/black background, retro/readable font, `amiwind debug reset location 0`,
`dbg coords on`, `dbg pos`; close/reopen console; draw/sheath hands; Escape menu
and confirmed Exit to the shell with the restart reminder.

Screenshots and logs confirm actual movement, settings, readable/retro glyph
changes and solid reopened background. This is a bounded deck/gangplank check,
not certification of every ship rail, stair or complete shore-to-deck route.
No ERROR.TXT was produced. Actor/hand model files each opened once; no repeated
cache reloads occurred on this route. The private harness bindings are not in
the delivered default controls. Host paging-key behavior needs care; the actual
command dispatch was exercised by typing clean command lines.

| Counter | Final route |
| --- | ---: |
| Frames / elapsed | 2184 / 97,615 ms |
| Surface / edge overflow frames | 0 / 0 |
| Maximum surfaces / edges | 7365 / 13,436 |
| Hunk used at exit | 7,674,432 bytes |
| Reserved game heap | 9,437,184 bytes |
| Free Chip / Fast at exit | 1,796,432 / 5,054,552 bytes |
| World / entities / C2P | 83,531 / 1434 / 288 ms |
| Worst frame, including startup | 999,411 us |
| Audio late updates / missed frames | 2 / 7114 |
| Audio warmup updates / missed frames | 1 / 4258 |
| Music read slices / bytes | 540 / 2,211,840 |
| Music read errors | 0 |

This mixed route includes console/menu time and is not a controlled performance
comparison with checkpoint-014. The lower observed surface peak does not prove
all cameras got cheaper. World rendering still dominates. Audio deadlines are
still imperfect; zero read errors is not glitch-free playback. All 18 installed
tracks are included, but this short route does not repeat prior multi-song
natural-completion verification. No new playlist algorithm is introduced here.

## Exact environment and artifact identity

FS-UAE **3.1.66**, A1200/AGA/PAL, **68040-NOMMU / internal 68040 FPU**, JIT/max,
2 MiB Chip + 16 MiB Z3 Fast, 24-bit addressing disabled, keyboard joystick off.
Resolved CPU/FPU JIT cache 8192. No Workbench desktop. No physical-Amiga or
stock-A1200 performance certification. WinUAE preset is configuration guidance;
no local WinUAE test is claimed.

ROM: Kickstart 3.1 A1200 **40.68**, 524,288 bytes, SHA-256:
`6d43840d4099a74170ea0f0425b6257c3891ebcaa39c4d1840075a9ab22b5707`.
FS-UAE executable SHA-256:
`b729fe233a6507daed7fea6fbe8cfc417da523239d4a43037dd57203858e4f37`.

Compiler: AmigaPorts GCC 16.2-rc11 / 16.2.0b20260825082934, 68040/FPU.
Pinned AmiQuake commit: `9c62d905151614af3e788ae3145a0d4ecc8a7bb8`.
Upstream archive SHA-256:
`43353034beb2a43b1af82c735f93c0a8bee8129c1b93d7ba152dd8e60ad3721c`.
The builder read back every HDF payload and verified the FFS root metadata.

| Artifact | SHA-256 |
| --- | --- |
| HDF (134,250,496 bytes, 128 MiB FFS in RDB) | `e0cc8d4f69bdecc73d3a2d83fd3f9b246dbc8dc046e94fb17a5fe97702c841d1` |
| AmiWind executable | `d8b1e1433d978542406c55fee5c8338c1a6f6cdb374bb609efd02f23ebbec080` |
| 68000 preflight | `63e07999dbdb051cd6e3ee69fa3ac9c79996799e5e69fa28053a8e879d675277` |

## Relaunch acceptance

A separate focused run, `ship015-relaunch-r1`, walks and draws/sheathes hands,
exits normally, types `amiwind` at the DOS prompt, then repeats walking/hands
and confirmed Exit. Both shell captures show the restart reminder. No ERROR.TXT
was produced. The second launch retained 1,796,432 free Chip bytes; no repeated
actor/hand loads or renderer overflows were recorded. Its profile belongs only
to that second launch and is not part of the main route counters above.
The bare `amiwind` command launches the executable directly; use `AmiWindCheck`
separately to rerun the preflight report. Startup-sequence runs preflight on boot.

## Remaining work

The reported incomplete terrain/rock formation is open and needs a source/camera
comparison. Shack disappearance is owner-reported no longer reproducing in the
prior checkpoint; preserve that route. The ship is simplified and its authored
collision still becomes approximate convex pieces. No ship interior, door entry,
opening quest or departure/removal state is implemented. Unrelated scenery still
uses the old origin cutoff; expanded sea does not fill missing map coverage.
NPCs remain nonblocking with limited Hello auditions and no wandering/combat.

Next: connected starting-area exteriors, then the dim prison-ship opening and
separately loaded Census office. Day/night, exact-hour/freeze debug controls,
cheap sun/sky gradients and night backdrops are design notes only; see
[DAY_NIGHT_AND_SKY.md](DAY_NIGHT_AND_SKY.md). No owner acceptance of checkpoint-015
is claimed before delivery.
