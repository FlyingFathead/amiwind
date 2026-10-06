# v0.0.29-rc1 — private playtest and bounded acceptance

Recorded 6 October 2026. The RC1 image, playable archive and independent
launcher extraction are verified locally. The exact package completed a bounded
FS-UAE run from 12:15:54 to 12:23:24 UTC and returned cleanly to AmigaDOS.
The private playtest checkpoint was delivered on 6 October 2026 and its
catalogue listing was confirmed by the playtester. Public GitHub source
publication remains pending. Final More Mushrooms remains open; this
checkpoint does not certify complete world, appearance or audio coverage.

## Packaged scope

Complete readback records 18,374 payload files /4,794,099,302 bytes: 382 new,
53 replaced and 17,939 unchanged against dev4, with no relocated files. New
files comprise 330 harvest catalogues, eight shared mushroom MDLs, 40 hand MDLs
and four support files. Packaging counts are not new source-conversion totals
or unique original-placement counts; those unmeasured totals remain unknown.
The source suite ran 1,041 tests with no failures/errors and four skips; the
68040 engine linked. The source correspondence is the frozen candidate used
for this package; later documentation edits do not change that executable.

## Bounded native acceptance

| Area | Established by this exact run | Still open |
| --- | --- | --- |
| Launch and exit | Bundled FS-UAE entry booted the verified extraction and quit to AmigaDOS | Windows batch execution and physical-hardware coverage |
| Audio menu | Four sliders displayed; ordinary Left/Right changed Master 70→65→70; Escape/reopen worked | Native mouse dragging, Master-zero independence and every slider interaction |
| Mixer and saved levels | Command-driven zero-dialogue case produced zero PCM; dialogue with Effects zero and pickup effect with Dialogue zero produced nonzero PCM; final config retained Master/Music/Effects/Dialogue 100/100/50/25 | Perceptual listening acceptance and the original WinUAE Enter symptom |
| Character flow | Ordinary New Game/name Enter; head-preview race/sex/face arrows and selection Enter worked | Exact follow-guard Enter event and full appearance OK exit were not separately established |
| Hands and torch | Nord hands, short forward/back motion, nearby NPC and held night torch captured; brightbase/sparks commands exercised | Paw-like silhouette, detached grip/race coverage, final-run punch and controlled NPC illumination/cost |
| Mushrooms | Prompt, two distinct pickups, F5/F9, two inventory items and two persisted picked facts; picked plants absent after reload | Same-plant duplicate-negative, natural empty outcome, world/interior traversal and complete overlap acceptance |

### Two distinct pickups

The second E targeted another overlapping plant. Save decoding records two
different original references and two Russula items. This verifies persistence
for two plants; it does not establish same-plant duplicate suppression in this
run. Earlier dev4 repeat-pick evidence retains its own dated scope.

### Audio limits

Nonzero music PCM was established before the timing markers. The final profile
records 2,232 read slices, 9,142,272 bytes, zero read errors and one natural
completion. The sole late update equals the sole warmup update (1,236 missed
frames); no additional late update was recorded. These counters do not supply
a perceptual listening verdict or resolve the original WinUAE Enter cut.
The later prison Return lacked a visible follow-guard prompt. An attempted
Home/End slider change did not occur, so it is not a music-mute test.

## Open release gates

- **AUDIO-ENTER-29:** original WinUAE Enter/music report remains open; exact
  follow-guard event and broader listening acceptance remain unverified.
- **TORCH-HAND-NORD-29:** normals change shading; the paw-like silhouette and
  broader connected-grip/race/animation acceptance remain open.
- **TORCH-NPC-LIGHT-29 / TORCH-FLAME-VISIBILITY-29:** earlier bounded guard
  off/on and flame-style evidence remains valid; final screenshots do not
  establish a controlled illumination comparison or every appearance.
- **HUNK-RESERVE-SN012-29:** 44 of 2,723 maps retain modeled reserve warnings,
  down from 59 with no new warning maps and no hard allocation-ceiling failure.
  Worst sn012 loader peak is 7,857,120 bytes; total with allowances is 13,210,500,
  still 1,676,164 above the 11 MiB gate. Baseline 3 MiB and safety 2 MiB are
  unchanged. Native endpoint heap use 8,874,464 and free Fast RAM 1,681,872 bytes
  are separate observations, not proof that the modeled reserve passed.
- **HARVEST-WORLD-29:** modeled exterior admission remains 347/390 maps with
  43 withheld. Dense maps, interior routes, unsupported states and worldwide
  original placement/picking remain incomplete. Two native pickups do not
  establish complete coverage.
- **PERF-READAHEAD-29:** outdoor transition pauses remain open. Five logged
  long frames include scene/save-load work; no blanket freeze-free or speedup
  claim follows from this run.

The [issue index](BUGS.md), [detailed RC1 tracker](BUGS-v0.0.29-RC1.md),
[audio notes](AUDIO.md) and [asset coverage](ASSET_COVERAGE.md) separate source,
packaging, bounded native and playtester acceptance. A screenshot/GIF gallery
may document this same run without widening those claims.
