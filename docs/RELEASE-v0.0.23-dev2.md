# AmiWind v0.0.23-dev2 — interiors and local cast checkpoint

29 September 2026. Based on published v0.0.23-dev1 revision 2, commit
`51636780d12d93d62abfdf687d55a6fcdcc9ad07`. This checkpoint prioritizes inspectable
interiors; complete voice behaviour is the next milestone.

## Playable scope

- All thirteen Seyda Neen town interiors, the existing prison ship, Addamasartus
  and a larger exterior: sixteen selectable scenes. Original furniture, placed
  lights, door destinations and resident appearances are converted privately.
- Thirty ordinary NPC placements / twenty-seven appearances alongside the eight
  scripted introduction roles. Includes beast residents and Darvame Hleran at
  her original port placement, with the original Silt Strider model.
- Shared solid-body NPC collision, stable scene IDs, expanded debug scene picker,
  and a save-content fingerprint covering every scene.
- Full object-bounds selection retains a previously omitted rock mound near the
  port. Terrain sampling is denser around the approach. Final visual acceptance
  at the owner's reported coordinates remains open.
- Default parallel builds retained; independent interiors also use bounded
  parallel jobs within the global worker budget.

## Loading and sound

`aw_loading_style normal|blank` is reusable. Normal is the default; movie-to-Jiub
uses a one-shot blank override. Captured native loading frames were entirely
black before the ship view appeared. Ordinary doors retain the owned loading art.

Music continues to be mixed while common file reads, BSP/model decoding and
entity spawning run. Loading no longer clears the music DMA buffer. Effects from
the old scene are cleared; the current music track stays open. Repeated room
loads and an actual Tradehouse front-door round trip reported no read errors or
post-startup audio underruns. This is measured emulator evidence, not a guarantee
for every future blocking operation or physical hardware.

The two original ship-wave emitters were present and looping. Their additional
hardcoded 5 dB reduction has been removed, restoring the converted sound-record
volume and script multiplier. Native channel gain changed from 39 to 71, with
non-zero mixed output at the starting position. The original sample and spatial
falloff remain. Owner listening acceptance of the balance is still needed.
`soundinfo` now prints live channels and playback positions for diagnosis.

## Build and font evidence

| Input / run | Complete pipeline | Worker budget |
| --- | --- | --- |
| TTF-present initial expanded build | 409.511 seconds; all 18 stages | 6 |
| Separate no-TTF input copy | 401.139 seconds; all 18 stages | 6 |
| Final TTF conversion rerun | 422.728 seconds; all 18 stages | 6 |

The delivery images were assembled again with the final matching engine and
preflight after correcting the larger heap's startup checks. Every image payload
was independently read back from its finished HDF and compared with its input.
Timings exclude setup/input checks; they are not a controlled speedup benchmark.

TTF-present input uses usable Magic Cards / Gothic fonts; the supplied Daedric
TTF falls back safely when it exceeds native glyph limits. With all three loose
TTFs absent, the original FNT/TEX fonts compile instead. Filled bitmap paper ink
is the default. This checks both input conditions from the supplied owned data;
it does not claim an independently acquired Steam installation. The owner's
successful Steam test is separate evidence. `--bitmap-paper-ink` selects bitmap
paper coverage, not TTF source selection.

## Validation

- 252 host tests pass. Includes production swept NPC collision, unsigned BSP
  collision children, bounded visibility lists, shared collision traversal,
  loading-mixer DMA wrap behaviour, blank UI, save IDs, build scheduling and
  whitespace/media release gates.
- Native cross-compilation succeeds with the same 87 warning diagnostics as the
  v0.0.22 baseline; no new warning is introduced.
- All sixteen scenes loaded in FS-UAE 3.1.66. The native NPC approach test stops
  against Fargoth. Darvame and Fargoth render after fixing visibility capacity.
- Actual Tradehouse entry and exit pass. Its final-capacity run kept track 04
  open, with zero read errors, zero post-startup underruns, and no surface/edge
  overflow. The sixteen-scene run also reported no surface/edge overflow or
  post-startup audio underruns. Peak visibility links: 2,524 of 8,192.
- The reference profile remains A1200 / AGA / PAL / 68040 + FPU + JIT,
  2 MiB Chip and 16 MiB Z3 Fast RAM. Around 2.3 MiB Fast RAM remained free in
  recorded runs. The game heap is 11 MiB; startup requires 14 MiB free Fast RAM,
  including one contiguous 11 MiB + 16-byte block, before loading the engine.
- Both final font images boot through the versioned startup, menu, movie skip,
  blank transition and readable Jiub/name prompt. Private packages contain the
  exact image hashes, receipts and bounded run evidence.
- Public source allowlist, whitespace checks, ZIP hashes and incremental-source
  reconstruction are mandatory. The exact owner-run publish script is checked
  before delivery and checks its own trailing whitespace before acting.

## Limits and next work

This is an inspection build, not a claim of 100% room coverage. All 43 original
door links have not been walked in both directions; stairs, thresholds and the
full introductory quest route still need inspection. The earlier Census missing
room repair is preserved; the separate captain-wing out-of-bounds and intermittent
freeze reports remain open. Scene loading alone does not close them.

Addamasartus uses shared ambient lighting to bound repeated cave geometry; its
placed-light rendering needs improvement. NPC greetings are still a bounded
prototype, not complete original voice pools/conditions/cycles. Strider travel,
fares/affordability, calendar/wait/day-night sky and experimental blight remain
planned. The Strider has no animated idle or travel service yet. No Windows/WSL
or physical-Amiga validation is claimed here.

See the maintained [29 September plan](PLAN-2026-09-29.md),
[interior inventory](SEYDA_NEEN_INTERIORS.md) and [bug register](BUGS.md).
Publish only the full/incremental public source ZIPs and their checksum sidecars.
Private HDFs, game assets, ROMs and conversion evidence must remain private.
