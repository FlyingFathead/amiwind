# AmiWind v0.0.29 - Let There Be (Just a Bit More) Light

AmiWind brings Morrowind's landscapes and interiors to the Amiga through a
GPL-licensed conversion pipeline and native engine. This source release includes
project code and documentation; it does not include Morrowind game files.

## Changes

- Independent interior and exterior brightness settings in Options > Graphics,
  with six steps from 1.0x to 1.5x, persistent settings and console controls.
  Defaults are 1.2x indoors and 1.0x outdoors. Builds can omit the controls with
  `--no-luma-controls` or `--disallow-luma-controls`.
- Effects volume defaults to 75%; existing saved mixer settings are retained.
- Options selection stops at either end, and console wheel events at scroll
  boundaries no longer produce unbound-key feedback.
- A guard prevents an occupied Census door's opening hull from turning onto the
  player's position. The RC2 playtester confirms the reported trap is gone; other positions,
  save/reload and return cases remain part of ongoing coverage.
- Consistent exterior ambient-light selection for empty and unused lighting
  lumps; the RC2 playtester confirms the reported Seyda shack brightness jump is gone.
  Broader traversal coverage remains open.
- A repair for the near-plane opening at maximum punch extension, demonstrated
  in sampled default and Argonian Female views and an RC2 High Elf playtest. Brief disappearance at the start
  of a punch and broader race/pose coverage remain separate work.
- Combat and torch inspection rooms restore their input/timing behavior after
  appearance selection. Torch flame style and configurable strength are included, with positive
  RC2 feedback at the default settings.
- Framed Cancel and action buttons in New game, Return to main menu and Exit
  confirmation dialogs, matching the existing character-confirmation style.
  Their sizes and hit areas are unchanged.

## Known issues

- **Bitter Coast mushrooms:** only one of three nearby mushrooms was reportedly
  usable in an RC2 playtest. Luminous Russula identity is tentative, and world
  pickup versus inventory consumption still needs clarification. Map/reference
  IDs, reproduction and cause remain open. See [the report](bugs/HARVEST-BITTERCOAST-29.md).
- **Balmora Temple:** major partial geometry and collision holes remain in lower
  rooms. Upper rooms and stairs provide intact controls. A Temple-only numerical
  export correction did not resolve the broad holes; the original map is retained.
- **WinUAE music:** crackle and pauses persist at guard-follow Enter, rotating
  race-selection entry and heavy loads. Race-selection audio is reopened after
  an earlier RC1 positive report. Streaming mitigations and FS-UAE audio capture
  do not establish a WinUAE continuity fix.
- **Hands and combat:** brief idle-to-punch disappearance, alternating punches,
  original punch sound/event coverage, and complete race/pose coverage remain.
- **Lighting and torches:** Census static-NPC sampling, outdoor torch strength,
  style-3 embers, the dim test-room floor, and compact unlit/fuel state need work.
- **Memory and content:** 2,724 maps passed the hard allocation ceiling, with
  44 modeled reserve warnings remaining. This is not physical-Amiga RAM acceptance.
  World, interior, quest and Windows-launch coverage remain incomplete.

Brightness has a bounded measurement: three alternating Census renderer pairs
at 1.0x/1.2x produced medians of 1.175745/1.189845 seconds per 128 renders,
about +1.199% or +0.110 ms/render. This is a small FS-UAE renderer sample, not
physical-Amiga FPS or normal gameplay performance. Current playtest feedback
describes brightness as more tolerable; the player's exact factor is unknown.

[Current issue checkpoint](RC2_ISSUE_CHECKPOINT.md) |
[Bug register](BUGS.md) | [Lighting measurement](bugs/INTERIOR-LIGHT-29.md)
