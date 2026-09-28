# v0.0.20: quieter ship ambience and stability reports

The ship's two wave/hull ambience emitters now play at -5 dB relative to v0.0.19
(amplitude multiplier 0.5623413). The adjustment is applied to static mixer channels
for `env/boat_hull.wav` only while the prison interior is active. Original audio,
converted samples and authored emitter values are unchanged. The same sample
in other locations, other effects, dialogue and music keep their normal gain.
Ambience positioning and distance attenuation retain their previous settings.

The bug register records two intermittent owner reports on FS-UAE 3.1.66:

- Freeze when exiting the prison ship during the intro; a second attempt worked.
- Freeze after reaching the dock and staying in the menu, with a short fragment
  of the song repeating like a stuck record.

Both remain open and undiagnosed. Incomplete map cleanup or stale references are
investigation hypotheses. This release does not claim a freeze fix.
See [the full observations and limits](BUGS.md).

## Compiler-warning corrections

Two inherited loops crossed the declared row bounds of C arrays, in map texture
loading and particle initialization. Both faults were reproduced with the
undefined-behavior sanitizer and corrected with row-bounded indexing. Expected
texture coordinates and particle random-number order are preserved. These are
confirmed code defects; their relationship to the freeze reports is unknown.

## Overlay and emulator preset

`debug overlay on` and its existing aliases now also enable coordinates, even
when the saved coordinate setting was off. `debug coords off` can hide them
again. Master-off sets coordinates off too. Startup overlays remain off; FPS and
cache indicators stay independent.

The current FS-UAE preset uses `uae_cpu_24bit_addressing = false`, correcting the
rejected `uae_address_space_24` option observed in the owner's 3.1.66 launch log.
This is a configuration correction, not a demonstrated fix for the freezes.

The permanent build workflow now requires warning inspection and baseline
comparison after every compile; see [DEVELOPMENT.md](DEVELOPMENT.md).

## Validation

Validation results accompany the matching release handoff. The requested 5 dB
reduction is an emitter-gain change, not a claim about measured loudness at every
position or final mixed output. The engine sends static gains at 8-bit precision,
and mixer channel volumes are integers, so the applied in-game reduction is
approximately 5 dB. Listening approval and
physical Amiga/WinUAE testing remain outstanding.

## Next milestone

The owner selected maintenance first. Dock race/head preview, Census Office
interiors and NPCs, character attributes and working save/load are the next
milestone, including adjustable retention of X autosave snapshots. See
[character creation](CHARACTER_CREATION.md) and [save/load](SAVEGAME_PLAN.md).

## Host-tool packaging revision 2 — 28 September 2026

Separately named `-r2.zip` archives add the portable FS-UAE launcher, settings,
latest-image selection, checksum warnings and configuration backups. Runtime
version and HDF bytes remain unchanged; prior release archives are retained.
See [launcher instructions](FS-UAE-LAUNCHER.md).

Validation for this follow-up: 206 host tests pass, including 25 new launcher
cases; warning-as-error Python compilation and the focused suite pass. Config-only
verification with the existing actual HDF/reference ROM confirms checksum matching,
input preservation and no rewrite on rerun. No new native compilation or interactive
emulator session is claimed. The prior native build still has 93 warnings.
