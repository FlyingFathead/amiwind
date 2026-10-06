# Missing media references and separate video soundtracks

Status: investigation open, 5 October 2026. This supplements
[complete media import](MEDIA_IMPORT.md). It records source references and
validation tasks; it does not distribute game audio, video or dialogue.

## Nine unresolved audio references

An import of the installed Morrowind, Tribunal and Bloodmoon masters found seven
voiced `INFO` references and two `SOUN` references whose requested source files
were not present in the inspected archive/loose-file inventory. These are
**missing source references**, not failed conversions. They do not establish
that the files are missing from every edition or that every reference is active
during normal gameplay.

Paths below are relative to the original `Sound/` directory. Spelling and case
are retained from the records for reproducibility; resolution is case-insensitive
and normalizes separators.

| Master | Type and record ID | Requested relative sound path |
|---|---|---|
| Morrowind.esm | INFO `100895772021910289` | `Vo/v/CrAtk_NF002.mp3` |
| Morrowind.esm | INFO `7252113851652132572` | `Vo/v/CrAtk_NF003.mp3` |
| Morrowind.esm | INFO `3083298241703228067` | `Vo/v/CrAtk_NF004.mp3` |
| Morrowind.esm | INFO `5768283312980027048` | `Vo/v/CrAtk_NF005.mp3` |
| Morrowind.esm | INFO `22437481287205476` | `vo/d/f/Hit_DF007.mp3` |
| Bloodmoon.esm | INFO `1901427015312973655` | `vo/d/m/bIdl_DM001.mp3` |
| Bloodmoon.esm | INFO `725228951789219466` | `vo/n/f/bIdl_NF021.mp3` |
| Morrowind.esm | SOUN `Sound Test` | `Fx/Jetsons Doorbell.wav` |
| Bloodmoon.esm | SOUN `spriggan resurrect` | `Cr/sggn/sggn magic.wav` |

The import currently checks a requested `.wav` path and then a same-stem `.mp3`
fallback. It does not invent an alternate filename for a missing `.mp3`, infer
that a test-named record is unused, or substitute unrelated speech. The preserved
lookup provenance must remain available for investigating eligibility and
overrides.

Investigation and acceptance checklist:

- [ ] Recheck the original archive inventory, loose overrides and case/extension
  resolution using the same installed master set and recorded input hashes.
  Compare another legally available installation or edition only as a separately
  identified source; do not copy unverified replacements into the baseline.
- [ ] Follow each record's identity, deletion/override state, dialogue conditions
  or sound-event caller. Establish whether it can actually be selected before
  calling the absence a gameplay bug or unused data.
- [ ] Check OpenMW's resource fallback and missing-sound handling against the
  same records, and compare observable original-game behavior where available.
  Source code alone does not prove the original executable's behavior.
- [ ] Record each result separately: recovered exact source, verified alias,
  inaccessible/deleted record, intentionally absent source, or still unknown.
  Preserve the original reference and evidence; never silently count a
  replacement or unresolved row as covered.
- [ ] If a resolver or event mapping changes, add a synthetic regression for
  that rule, then verify the corresponding converted file and actual playback.
  An imported file alone does not close event-wiring acceptance.

## Three videos without embedded audio

The inspected `mw_credits.bik`, `mw_logo.bik` and `mw_menu.bik` contain no embedded
audio stream. Their conversions completed with `audio_status` set to
`synthesized_silence`: this is a duration-matched PCM track required by the AWV1
container, **not a conclusion that the game's presentation should be silent**.
An audio decoder error must still fail conversion; it must never take this
no-stream fallback.

| Original video | Stable video ID | Converted relative payload | Open investigation |
|---|---:|---|---|
| `mw_credits.bik` | 13 | `intro/video/13.awv` | Identify the credits entry point and any separately selected music. |
| `mw_logo.bik` | 16 | `intro/video/16.awv` | Identify the startup/logo sequence and whether music begins before, during or after it. |
| `mw_menu.bik` | 17 | `intro/video/17.awv` | Identify the menu-background loop and its separate soundtrack lifecycle. |

### Source evidence and remaining uncertainty

The inspected reference is OpenMW's `openmw-0.48.0` tag, resolved to commit
`81ab0feb2ec2fda488eec043f6fa3d9b020f1521`. This matches the reference runtime's
0.48 version family. It establishes that source version's control flow, not
complete audible behavior or the original executable's implementation.

- **Startup logo:** `Engine::go()` selects the main menu, calls
  `playTitleMusic()`, then plays the configured `Movies_Morrowind_Logo` with
  `overrideSounds=false`. `SoundManager::playTitleMusic()` selects
  `music/special/morrowind title.mp3` if present. This supplies a concrete
  separate-music mechanism for the logo; the active fallback configuration must
  still be checked to bind it to the exact installed `mw_logo.bik`.
  [Engine sequence](https://github.com/OpenMW/openmw/blob/81ab0feb2ec2fda488eec043f6fa3d9b020f1521/apps/openmw/engine.cpp#L1065-L1077),
  [title music selection](https://github.com/OpenMW/openmw/blob/81ab0feb2ec2fda488eec043f6fa3d9b020f1521/apps/openmw/mwsound/soundmanagerimp.cpp#L330-L357).
- **Credits:** `MainMenu::onButtonClicked()` calls
  `playVideo("mw_credits.bik", true)`. `WindowManager::playVideo()` pauses other
  sound categories only when sound override is requested **and** the movie
  actually has an audio stream. A no-stream credits movie therefore does not
  trigger that pause. This supports continued existing audio, but does not
  identify a dedicated credits track or prove uninterrupted/repeated music for
  the entire movie; that requires an audible timing check.
  [Credits entry](https://github.com/OpenMW/openmw/blob/81ab0feb2ec2fda488eec043f6fa3d9b020f1521/apps/openmw/mwgui/mainmenu.cpp#L92-L105),
  [movie audio ownership](https://github.com/OpenMW/openmw/blob/81ab0feb2ec2fda488eec043f6fa3d9b020f1521/apps/openmw/mwgui/windowmanagerimp.cpp#L1813-L1891).
- **Menu background:** the inspected `MainMenu` checks and loops
  `video/menu_background.bik`, with an image fallback. It does not directly
  select `mw_menu.bik` in these paths. The importer lists the original
  `Movies:Options Menu` setting, but that alone is not proof that this menu code
  consumes it. Treat the `mw_menu.bik` event mapping as unresolved; do not rename
  or alias it automatically merely because the names suggest a relationship.
  [Menu selection and loop](https://github.com/OpenMW/openmw/blob/81ab0feb2ec2fda488eec043f6fa3d9b020f1521/apps/openmw/mwgui/mainmenu.cpp#L24-L38),
  [background playback](https://github.com/OpenMW/openmw/blob/81ab0feb2ec2fda488eec043f6fa3d9b020f1521/apps/openmw/mwgui/mainmenu.cpp#L162-L211),
  [imported movie settings](https://github.com/OpenMW/openmw/blob/81ab0feb2ec2fda488eec043f6fa3d9b020f1521/apps/mwiniimporter/importer.cpp#L247-L251).

No soundtrack event mapping was changed by this investigation. The AWV1 silent
PCM fallback cannot stand in for this separate event/audio ownership work.

### Playback acceptance checklist

- [ ] Keep no-embedded-audio detection separate from intentional silence. Record
  the original video identity, stream probe and conversion outcome.
- [ ] Trace each original video/fallback setting to its startup, menu, credits
  or scripted entry point, then trace any separate music start/stop/loop event.
- [ ] Record exact public source revision and function names for source findings;
  retain original configuration and game-data evidence privately. Do not choose
  a soundtrack merely because a filename or theme seems plausible.
- [ ] Compare entry, natural completion, repeat/loop, skip and return-to-menu
  behavior. Check for duplicate music, unwanted silence, abrupt restarts and
  leaked previous tracks, including muted/music-volume-zero configurations.
- [ ] Preserve continuous background music through ordinary full-screen modal
  views. A cinematic or explicit music transition may deliberately take audio
  ownership; define that transition instead of freezing the sound service with
  the world renderer.
- [ ] Accept a pairing only after the correct event plays the intended source
  with timing and clean stop/resume behavior on the target. Conversion, image
  readback and runtime playback remain separate gates.

The nine unresolved audio references and the three separate-soundtrack questions
remain open. Complete conversion of available inputs does not resolve either
set automatically.
