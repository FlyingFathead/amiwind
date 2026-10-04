# OpenMW music and audio reference

Behaviour reference for AmiWind, recorded 27 September 2026. This document is
also a regression checklist: having all OST files on disk does not establish
correct playback, automatic rotation, or uninterrupted audio.

## Native filename regression found in v0.0.11 development

The selected SDK's `libamiga` supplies `sprintf` through Exec `RawDoFmt`, whose
unqualified decimal conversion consumes a word. Passing our 32-bit track ID to
`%02d` formatted `track00.mws` for every small ID. Playlist history therefore
appeared to rotate while playback repeatedly opened the title file. This is
why old track-open counters did not prove that different music was heard.

The player now constructs the two filename digits directly and records the
filename plus played/total frames. Native testing opened track02 and track03
with their distinct expected frame counts and consumed every frame before
advancing. Shift+F6 Next, Shift+F5 Previous and battle-mode audition were also
exercised. Keep this case in native acceptance; an ordinary Linux printf test
alone cannot reproduce the Amiga formatting behaviour.

The world playlist also excludes the title's decoded-content identity. Both
fixes are necessary. Late mixer updates remain a separate measurement; successful
song selection does not establish uninterrupted playback. Diagnostic event
writes are buffered and flushed on close, not forced from the mixer.

## Inspected sources

- OpenMW revision `46bd4599203ee52ffc0f3e8edb3fc159a0303a49`:
  [music.lua](https://github.com/OpenMW/openmw/blob/46bd4599203ee52ffc0f3e8edb3fc159a0303a49/files/data-mw/scripts/omw/music/music.lua)
  and [helpers.lua](https://github.com/OpenMW/openmw/blob/46bd4599203ee52ffc0f3e8edb3fc159a0303a49/files/data-mw/scripts/omw/music/helpers.lua).
- [SoundManager implementation](https://github.com/OpenMW/openmw/blob/master/apps/openmw/mwsound/soundmanagerimp.cpp),
  inspected 27 September 2026: `update`, `updateMusic`, and `streamMusicFull`.
  The mutable master link is a reference, not a pinned build dependency.

The Lua helper gathers tracks from `music/<playlist>/`, constructs an index
list, and shuffles it with Fisher-Yates. Playback consumes that list and refills
it when exhausted. Exploration is active by default; battle has higher priority
when combat is active. The current song continues while its playlist remains
selected and the stream is playing. SoundManager separately starts title music
when in the main menu with no game loaded and no music playing.

Do not describe this as a verified reconstruction of Bethesda's closed-source
implementation. OpenMW is the inspected, open-source behaviour reference.
No OpenMW implementation source is copied into AmiWind's Amiga runtime.

## AmiWind behaviour contract

- Title music belongs to the title/menu context. It must not enter exploration
  or battle, even if an installation duplicates it into an Explore directory.
- Preserve every owned music file in the private asset store; construct playback
  groups using canonical decoded-content identities, not filenames alone.
- Exploration and battle each have their own shuffled order. Play full songs;
  advance at actual EOF, refill the exhausted bag, and avoid adjacent repeats
  when another valid track exists. An intentional Previous action can replay
  history; it is not an automatic-shuffle regression.
- Shift+F5 selects the previous song in playback history. Shift+F6 moves forward
  through that history, then selects the next shuffled song at the newest entry.
  These are AmiWind audition controls, not claimed original-game shortcuts.
- Combat selection will follow actual combat state when gameplay supports it.
  Until then the exploration/battle switch is an explicit audition control.
- Moving, turning, changing fog, or loading scenery must not restart a song.

## Reported regression and required evidence

The owner reports repeated title music and small snaps/glitches in v0.0.10.
That release contains 18 files, including two byte-identical title copies. Its
exploration list incorrectly includes their canonical title entry. Removing it
addresses menu/exploration separation. Subsequent native investigation found
the filename-formatting fault described above; it explains continuous title
repetition despite apparently rotating internal track IDs.

The AGA reader and software mixer currently run from the game loop. File read
success does not prove DMA deadlines were met. Retain separate counters for
I/O errors, late audio updates, natural completions, manual changes, and actual
track identities. Test the output across block boundaries and final partial
blocks, not merely the file header or the Next command.

Acceptance requires multiple complete, distinct exploration songs advancing
without key input; bag rollover without an immediate duplicate; Previous/Next
history checks; mode changes; and a matched movement run with audio capture and
deadline counters. Record emulator version/settings, ROM SHA-256, image hash,
and whether the run uses synthetic short fixtures or full original tracks.
Do not report a synthetic transition test as a full-OST listening test.

## Scope and rights

See [AUDIO.md](AUDIO.md), [OPTIMIZATION_HISTORY.md](OPTIMIZATION_HISTORY.md), and
[LICENSING_AND_CREDITS.md](LICENSING_AND_CREDITS.md). Dialogue and effects are
separate sound sources; they must share the output budget without restarting
music. Their AGA integration remains future work. Original audio and converted
samples remain outside the public source repository.

For the first Fargoth/guard milestone, see [NPC and greeting behaviour](OPENMW_REF_NPCS_AND_DIALOGUE.md), including the requested UESP voice reference and OpenMW selection/trigger paths.

## Intermittent clicks: recovered WinUAE report

Owner still hears occasional clicks/pops in v0.0.15-dev1. Local FS-UAE final
3D route logged 2 late mixer updates / 9,325 missed frames, plus startup warmup;
read_errors=0 and one synchronous source fill. No matched WinUAE audio capture
is available, so these counters do not identify every reported click.

Source inspection for that historical report: 2 x 8,192-frame stereo source blocks, 4 KiB synchronous refill
slices, a 32 KiB 8-bit stereo DMA ring, configured `_snd_mixahead 0.3` seconds.
The ring can hold more than is routinely mixed ahead. A roughly 995 ms worst
frame in the acceptance route exceeds that 300 ms margin. Source prefetch and
ready-to-play mixed audio are different queues. Increasing HDD size does not
prevent main-loop blocking. A larger mix-ahead can trade response latency for
headroom but is not proof of a root-cause fix.

Next: correlate late events with frame/load/read timestamps and queue occupancy;
measure block-boundary discontinuities independently; A/B the same route and
track under matched emulator settings. Consider bounded loader work and an audio
producer task with safe buffer ownership. Do not perform filesystem reads in a
hardware interrupt or assume raising the whole game's priority fixes starvation.
Also distinguish host/UAE output-buffer underruns from emulated-side misses.

## v0.0.28 music-only read-ahead candidate — 4 October 2026

The current OST source queue has four 8,192-frame stereo blocks (64 KiB),
with the same 4 KiB refill slices. The shared mixer schedule, DMA buffer,
speech and guard voices are unchanged. Host suites and matching Amiga
compiles pass. The owner initially rated the current WinUAE opening-session
audio 5/5, then immediately reported remaining audible trouble, mostly at
load-ins and in heavy scenes. That qualification supersedes the initial verdict.
Publication proceeds with this known issue; further audio investigation is
deferred until after publication. The audio issue stays open;
read-ahead is a functionally tested mitigation, not a verified fix for clicks
or a proven hardware/backend diagnosis. [Current diagnostics and scope](AUDIO.md).
