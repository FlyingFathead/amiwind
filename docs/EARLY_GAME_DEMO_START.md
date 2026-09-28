# early_game_demo_start_1

This is the default AGA demo opening for v0.0.17:

- Load the Seyda Neen exterior (`seyda`) at its existing town-center player start.
- Retain the standing-hull spawn clearance and nearby-exit checks.
- Start exploration track 04 (`track04.mws`) from the beginning.
- Continue with the other exploration tracks through the normal shuffle.

In the owner's verified conversion manifest, track 04 comes from
`Music/Explore/mx_explore_3.mp3`. The owner confirmed that this is the intended
recording. We identify it by converted track number and source path; no
unverified soundtrack title is assigned. Audio remains privately converted
from the user's installed game files.

The town-center `info_player_start` is generated from TES3 X/Y
(-11200, -71504), terrain height plus the existing spawn offset, facing 90
degrees. The normal runtime clearance search may adjust the final position
nearby. Interior door arrivals continue to use their own destinations.

## Selection and startup order

`early_game_demo_start_1` is a runtime console variable with default value `1`.
The generated `quake.rc` executes `default.cfg`, then `autoexec.cfg`, then
`aw_demo_start`. This lets a local `autoexec.cfg` choose another setting before
the initial map loads. Merely including the prison-ship map no longer selects
it as the initial scene.

To restart the demo opening from the console:

```text
early_game_demo_start_1 1
aw_demo_start
```

To select the earlier ship-first opening, put this in the private image's
`id1/autoexec.cfg`, or run it followed by `aw_demo_start` in the console:

```text
early_game_demo_start_1 0
```

With the option disabled, `aw_demo_start` loads the ship interior if included,
otherwise Seyda Neen, and does not force track 04. Ordinary scene changes do
not restart the demo opening or its music. The chosen first track is retained
in Previous/Next history and excluded from the remainder of the first shuffle
bag. If track 04 is missing or unusable, the runtime reports the problem and
uses normal music selection.

The builder prints the default profile and the source mapped to track 04 in
the image stage, and records the default opening in the private `build.json`.
The asset-free dry-run remains a notice screen, with no game scene or music.

## Validation

The native Amiga engine and boot checker compile with this change. Host tests
exercise the production scene-start command, default and disabled selection,
track-04 playback against synthetic PCM, complete-track transitions, shuffle
history, and missing-track fallback. The existing standing-hull tests pass.
The updated default still requires the owner's emulator playtest before the
v0.0.17 publication step. Compiler warnings remain recorded for review.
