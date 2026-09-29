# Dialogue, character confirmation and waiting — v0.0.23-dev3

## Dialogue display

Options → Interface exposes UI font, voice identity, dialogue style, aimed NPC
names, NPC placement and object placement. These are archived settings.

**Default: `aw_voice_dialogue_display_style 2` — Aim only.** Sampled speech never
shows a speaker header in this mode, overriding all four dialogue methods and
`aw_show_speaker_name_during_voiceovers`. The freed row holds dialogue text.
After Census review, a close, unobstructed aiming ray identifies the NPC under
the pointer during speech, even if the ordinary aim-name toggle is off. Looking
away removes that identification. NPC placement still selects the label position;
character-creation/menu gates still apply. Unvoiced messages retain their method.

`aw_voice_dialogue_display_style 1` restores the configured behaviour: the saved
`aw_show_speaker_name_during_voiceovers` switch (default 0) controls speaking
names. Set both style 1 and that switch to 1 to show them. The Interface row
cycles **Aim only → On → Off → Aim only**, with no additional panel.

The panel keeps its existing position, height, slide animation and artwork.
At the reference 320 × 200 view it rests at y=152 and is 48 pixels high.

| Method | Speaker name | Body |
| --- | --- | --- |
| `aw_dialogue_box_display_method 1` | Inside panel, previous layout | Previous paging/spacing |
| `aw_dialogue_box_display_method 2` (default) | Above left edge, no filled background | Two rows at 14/16 px; three at 12 px or fallback |
| `aw_dialogue_box_display_method 3` | No speaker name; use optional aim label only | Same body capacity as method 2 |
| `aw_dialogue_box_display_method 4` | Speaking name at upper right over the viewport | Same body capacity as method 2 |

`dbg ui dialogue 1/2/3/4` selects the method. `dbg ui font 12/14/16/fallback`
selects font size. Long lines wrap and paginate; long names are bounded to screen
width. When enabled for the current message type, the speaker is identified independently
of where the player is looking (except target-only method 3).
Name-entry and movement prompts are not speakers: their label and input remain
inside the existing panel, without a stale speaker label above them.

The separate `dbg ui targetnames on/off` option defaults on. After Census review
(stage Papers onward), or in the inspection demo, it shows the NPC under the
centre aiming point. Upper right is the default, with these placement options:
| Position | NPC aim label | Object/interaction label |
| --- | --- | --- |
| Right below viewport | `dbg ui targetplace below` | `dbg ui labels below` (default) |
| Top right over viewport | `dbg ui targetplace topright` (default) | `dbg ui labels topright` |
| Left above status bars | `dbg ui targetplace hudleft` | `dbg ui labels hudleft` |

Archived parameters `aw_target_name_style` and `aw_interaction_label_style` use
1, 2 and 3 respectively. Labels have no filled background. A method-4 speaking
name takes priority over a target/object name in the same upper-right position.
Lower-strip labels are covered while the dialogue panel occupies that strip.
Method 3 never displays a speaker identity. The target-name toggle controls
ordinary identification; voice style 2 overrides it while a sampled subtitle is active.

Targeting uses a 96-unit solid-world/entity ray,
not the broad greeting cone. Walls and other solid entities block it. Menus,
reading and character selectors suppress it. Identification is independent of speech availability/cooldowns; `(Talk: E)` is
shown only when a supported manual greeting can target that same NPC.

Pier appearance, Census choices and final review require confirmation: **Really choose this
character?** The overlay shows the selected race/sex and face/hair or class/birthsign.
Go back is selected initially. Esc/N returns to review, preserving
edits; choose the right button then Enter, click it, or press Y to accept.

## Wait and game time

**T** opens the wait selector after character registration/release, while alive
and standing on dry ground, with no character menu, reading screen or speech
active. Select 1–24 hours with arrows/A/D, Enter to wait, Esc to cancel. The modal
uses the existing single-player menu pause; music remains serviced. Waiting is
an immediate, bounded clock advance; it does not run hours of native frames.

The clock starts at 09:00 on 16/08/427, matching the base master's GameHour,
Day, Month and Year globals. Normal play advances at 30 game seconds per real
second (`aw_timescale`, 30 by default). Menus, loading work and locked character
creation do not consume game time. Dates use a twelve-month, 365-day calendar.
Time is held in three bounded persistent globals and travels with ordinary saves
and scene changes. Earlier saves without those fields initialize at the start
value; malformed existing clock values are not silently reset.

`dbg timeofday` reports the current time and date. Named settings:

| Name | Hour |
| --- | --- |
| morning | 09:00 |
| night | 00:00 |
| midday | 12:00 |
| day | 14:00 |
| evening | 18:00 |
| sunset | 19:00 |
| sunrise | 06:00 |

A numeric value in [0,24), including fractions, is also accepted. Debug changes
keep the current date; waiting across midnight advances it. These are diagnostic
presets, not a season-dependent astronomical model.

Sky rendering still uses the existing renderer. Sun disc, directional sunrise/
sunset gradients, night sky, weather, NPC schedules, rest healing and fatigue
recovery remain pending. This is waiting, not a claim of full Morrowind rest rules.

**F1** opens AmiWind quick help with the logo and a paged console-font list of
actual current bindings. Arrows/PageUp/PageDown change pages. Customized bindings
are reflected immediately and can be changed in the console: `bind <key> <command>`, e.g.
`bind g aw_wait`. Config saving persists them. A graphical binding editor is not
implemented. The help action remains reachable via a bound function key during
character input without typing into the name field.

## Ship ambience

Only `env/boat_hull.wav` receives a host-side `volume=-5dB` filter. Each conversion
reads the original owned asset; it never uses a previously attenuated build as
input. The output remains mono 11025 Hz unsigned 8-bit PCM with one loop cue.
The two authored emitters, spatial falloff, speech and music gain are unchanged.
The conversion receipt records source/output hashes and gain. Quantization gives
-4.99 dB RMS versus the previous converted sample; repeat conversion produces
identical bytes. Listening feedback should guide further mix changes.
