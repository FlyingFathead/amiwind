# v0.0.19 — intro, menus, entrances and quiet debug defaults

The music player previously called Con_Printf on every successful track change,
even when the debug overlay was disabled. Dev5 gated the gameplay notification
draw; 0.0.19 also gates the message at its source.

With `dbg overlay off`, startup, manual next/previous/group changes and natural
track completion do not emit a routine OST notice. `dbg overlay on` restores
those notices. Music playback, shuffle/history and the private music-events.csv
log are unchanged. Explicit `aw_music_status` still prints the requested status
in the console. No separate option is needed.

The production-player host test exercises both switch states, natural completion,
manual changes, event logging and the explicit status command. The final fix follows dev5; the public v0.0.19 source ZIP includes the whole accumulated snapshot.

The incremental targets exactly dev5. The complete public source contains all
prior checkpoints. The private playable remains owner-only. Prior ZIPs/tags stay
immutable; the owner handles publication with the supplied commands.

## Accumulated changes

- Original-font UI, colored status bars, bottom dialogue area and optional gold frame.
- Startup logo fade, original main-menu artwork and title music; New Game confirmation.
- Optional 320×200 prophecy movie with readable title cards and Esc skipping.
- Voiced Jiub/name-entry opening, speech-driven face poses, guard movement/collision
  and an activatable hatch transition to the ship deck.
- Refined Esc menu; original loading screens; transition console and debug off by default.
- Deck-guard greeting/reminders, town entrance names and safe missing-interior feedback.
- Automatic compiler job selection, with explicit job-count and single-thread options.

This remains an early playable concept. Dock/Census character creation, most town
interiors, day/night and waiting, general combat and the full original intro script
remain unfinished. Exact original ship music cues remain unverified. See
RELEASE-v0.0.18-dev5.md for detailed inherited validation and limitations.

## Validation

179 host tests passed; native 68040/FPU build and every-file HDF readback passed.
The final 0.0.19 build boots with the correct menu version. FS-UAE verified
silent Next/group changes with debug off, restored notices with debug on, and
silence after toggling off again. All changes remain in the music event log;
explicit status output remains available. Natural completion and Previous are
covered by the production-player host test. Physical Amiga and WinUAE testing
remain outstanding. Earlier full intro/movie/hatch/door evidence is from dev5.
