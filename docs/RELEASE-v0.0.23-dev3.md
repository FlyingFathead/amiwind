# AmiWind v0.0.23-dev3 — dialogue and waiting checkpoint

Based on published v0.0.23-dev2, commit
`e368511551657b67cf84049934b093c97749d0ae`.

- Default voice identity is **Aim only**, `aw_voice_dialogue_display_style 2`.
  It suppresses every voiced speaker header, even when legacy name settings are
  enabled. After review, close aiming identifies the targeted NPC during speech.
  Options → Interface cycles Aim only / On / Off. Four general dialogue methods
  remain available; default method 2 places enabled unvoiced names above left.
  The same panel fits two default-font rows or three compact-font rows.
- Fix the reported house visibility holes by matching world/brush far culling.
  Correct compound rock transforms at the port and reduce terrain rocks toward
  64 visual triangles. See [What are rocks?](WHAT_ARE_ROCKS.md).
- Aim identification defaults on after creation, independently of Talk availability.
  Independent aimed-NPC and object label placement: upper right, lower right,
  or above the left status bars; optional NPC aiming names after character review.
- Pier appearance and Census choices/review show selections and ask for confirmation before committing the choice.
- Ship water reduced 5 dB from the owned original during conversion. No stacked
  runtime reduction; dialogue and music levels unchanged.
- T opens waiting for 1–24 hours; F1 opens a logo/paged help screen showing actual bindings in console font. Saved clock/calendar,
  30× normal time passage, midnight/date rollover, and named/numeric
  `dbg timeofday` settings. Existing console key rebinding remains available.

## Verification

260 host tests pass. The native 68040/FPU build uses six compiler workers and
retains exactly the same 87 warning diagnostics as the baseline. Regression
coverage includes transparent labels/panel geometry, compact/default/classic
text capacity, target ray gating, character cancel/confirm, wait/cancel bounds,
calendar rollover, saved clock fields, and one-time audio gain/loop preservation.

Both TTF-present and TTF-absent bitmap input variants were assembled, fonts
reconverted and filesystem payloads read back. The exterior static mesh BSP was rebuilt with corrected reference rotations and
a 64-triangle terrain-rock target. Interiors, actors and music reuse dev2
conversions; this does not claim another complete asset conversion. Both finished HDFs booted through the
versioned menu, movie skip, blank transition, Jiub dialogue and name entry in
FS-UAE on the unchanged 2 MiB Chip / 16 MiB Fast profile.

Native captures cover the unchanged dialogue panel and font variants; optional
speaker identity and placement modes remain configurable.
Control inspection covers classic/compact layout, target name on/off, waiting,
clock reporting and quick help. The water sample measures -4.99 dB RMS versus
dev2 after 8-bit quantization; authored spatial channel gain remains 71.

The TTF-converted playtest is recommended, particularly for paper text. Bitmap
paper strokes remain visibly rough, as reported in the owner's dev2 capture.

## Limits and next work

This remains a development checkpoint. The retained 13 town interiors and
Addamasartus still need exhaustive floor/door inspection. Full NPC voice pools,
conditions and cycling remain the next content priority. Silt Strider travel,
sun/sky rendering, NPC schedules, rest recovery, weather and a graphical key
binding editor remain unfinished. The wait feature advances time/date, not those
unimplemented systems. Owner-reported deck/pier escape and missing door squeaks remain open; see
[dev2 feedback](FEEDBACK-v0.0.23-dev2.md). Earlier freeze/console-close observations remain
open; physical Amiga hardware and Windows/WSL were not tested here.

The owner runs publication. Public release assets contain source and selected
promotional screenshots only. Private playtests contain owned game assets/ROMs
and must not be uploaded publicly. The full/incremental source packages and the
exact apply/publish helper must pass whitespace checks before delivery.

### Final feedback additions

`aw_voice_dialogue_display_style 2` defaults to aim-only identity and overrides
other voiced speaker-name settings. Interface cycles Aim only / On / Off.
House visibility now uses consistent far culling for world and brush fragments.
The large port rock was included but misrotated; corrected transforms and reduced
rock meshes close the reported gap. See `docs/WHAT_ARE_ROCKS.md` for source findings,
triangle budgets and the workflow. NPC conversation-facing remains open.
