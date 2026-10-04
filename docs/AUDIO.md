# Streamed music and speech

## Current AGA candidate: music-only read-ahead, 4 October 2026

The v0.0.28 candidate keeps four 8,192-frame stereo PCM source blocks
(64 KiB total), up from two blocks (32 KiB). Refills remain bounded to
one 4 KiB read per service call. `music_status` reports the block count,
buffer bytes and queued frames; `music-profile.txt` records `buffer_blocks`
and `buffer_bytes` after normal shutdown.

The PCM queue adds 32,768 static bytes; the complete executable's allocation
totals are recorded separately in the bug journal. The shared mixer schedule,
DMA buffer, speech and guard voices are unchanged. A proposed increase of shared
`_snd_mixahead` from 0.1 to 0.25 seconds was withdrawn, with the original mixer
source restored before compilation.

The synthetic player fixture verifies 30,000 prebuffered stereo frames without
another file read or synchronous fill, alongside track/tail/history checks.
Both full host suites and matching Amiga compiles pass. The owner initially
reported 5/5 audio in the current WinUAE opening session, then immediately
qualified that impression because audible trouble remained, mostly at load-ins
and in heavy scenes. The later report supersedes the initial verdict:
**the audible issue remains OPEN**. Publication proceeds with this known
limitation; further audio investigation is deferred until after publication. Additional
read-ahead is a functionally tested mitigation, not a verified cure or a proven
hardware/backend diagnosis. The complete attempts, corrected test oracle,
memory accounting and listening chronology are in
[WIN-05](BUG_JOURNAL.md#win-05-intermittent-winuae-background-music-snapping---investigation-open).

## Earlier audio design and implementation records

Both target machines have Paula's four 8-bit DMA audio channels. DMA playback
buffers must be in Chip RAM. The storage driver, refill scheduling and any
software mixing still consume resources; DMA does not perform disk streaming.

Convert the player's music and voice files on the PC to signed 8-bit PCM with
proper low-pass resampling and dithering. Do not make a 7 MHz 68000 decode the
original MP3 files during gameplay. The opening builder performs this conversion; the native v0.0.4 runtime streams the resulting music blocks.

| PCM stream | Bytes/second | KiB/second |
| --- | ---: | ---: |
| 11,025 Hz mono | 11,025 | 10.77 |
| 22,050 Hz mono | 22,050 | 21.53 |
| 22,050 Hz stereo | 44,100 | 43.07 |
| 22,050 Hz stereo music + 11,025 Hz mono speech | 55,125 | 53.83 |

These are payload calculations, not measurements. Paula's integer period means
the actual rate is slightly different: convert against a chosen PAL/NTSC
playback period to avoid pitch drift. For example, PAL period 161 is about
22,030.4 samples/second; a nominal 22,050 Hz budget remains a useful estimate.

The preferred first policy keeps music in stereo on channels 0 (right) and
1 (left). Channels 2 (left) and 3 (right) form a shared speech/effects pair:

| Active sounds above music | Channel 2, left | Channel 3, right |
| --- | --- | --- |
| Dialogue only | Dialogue | Same dialogue |
| One effect only | Effect | Same effect |
| Dialogue and effect | Dialogue | Effect |
| Neither | Silent | Silent |

A lone sound is centred by playing the same mono buffer on both sides. This
does not double disk data or buffer storage. On overlap, reclaim one side for
the new sound and let the existing sound continue on the other. When only one
sound remains, duplicate its current playback position onto both sides again.
The stereo music channels remain allocated throughout.

The full effects/voice sharing policy is proposed; stereo music plus centred
speech is implemented in the demo. Buffer-boundary
handoffs must preserve sample position; blindly restarting a sample on the
returned channel would create an echo. Brief fades may be needed to avoid clicks.
The audible tradeoff is movement from centre to one side during overlap.
Simultaneously centred dialogue and effects require software mixing or another
compromise. Multiple effects need a priority/voice-stealing policy as well.

As a bandwidth fallback, dual-mono music can read one shared music buffer on two
opposite-side channels. That halves music storage/reads compared with stereo at
the same sample rate. It still occupies two hardware channels.

Use two or more buffers and refill before a buffer finishes. A total 16 KiB
mono buffer holds about 0.74 seconds at 22,050 Hz; with two 8 KiB halves the
refill deadline is about 0.37 seconds, not 0.74. Storage stalls and competing
world reads must fit this deadline. Prioritize audio requests; postpone scenery
work when needed. A fade before a known interruption is preferable to underrun.

Cache a few probable nearby greetings in advance. Play speech over the music,
with optional music volume reduction. Dialogue selection, conditions and voice
timing require game logic separately from sample playback.

The base BSA inspected for the initial experiment had no audio entries. The ESM
references voice MP3 paths under `Data Files/Sound/Vo`; the soundtrack is under
`Data Files/Music` in an installed copy. Supply those external folders for future
audio conversion; they are not included in the source repository.

Reference: Commodore's [Audio Hardware chapter](https://www.theflatnet.de/pub/cbm/amiga/AmigaDevDocs/hard_5.html).

## Opening / terrain walk implementation (v0.0.1–v0.0.3)

Those early builds used channels 0/right and 1/left for an eight-second stereo loop
at nominal 11,015 Hz (8-bit signed PCM). Channels 2/left and 3/right share one
mono voice buffer, so the voice is centred while the music continues at a lower
volume. Paula reloads a silence word after the voice to prevent repetition.
PAL period 322 and NTSC period 325 are selected by raster timing; only PAL has
been emulator-tested. This is preloaded audio. Streaming, effects/voice
arbitration and general sample mixing remain planned.

## Complete soundtrack streaming (v0.0.4)

The host converts every installed Music MP3 without clipping its duration.
MWA1 consists of a 16-byte big-endian header (magic, u16 rate, u16 block frames,
u32 original frame count, u32 block count), followed by right/left planar signed
8-bit blocks. Each side has 8192 frames; only the final block is zero-padded.
The format is independently decoded during conversion to verify its PCM bytes.

Three stereo blocks occupy 49,152 Chip bytes. At nominal 11,015 Hz each lasts
0.7437 s; when one completes, about 1.49 s of queued audio remains. Task-context
DOS reads refill only completed buffers, then queue one write per side. Device
BeginIO preserves ADIOF_PERVOL; Exec SendIO clears that flag. Stop/Start on both
channels synchronizes initial stereo playback. AbortIO/WaitIO collect all
requests before switching tracks or unloading the program. Input goes through
input.device instead of taking its CIA keyboard events.

In v0.0.4, F6/F7 selected tracks and EOF advanced through the full playlist,
including battle and special cues. The v0.0.6 policy below supersedes that behaviour. A track
may have up to 0.744 s of final zero padding. No MP3 decoder runs on the Amiga.

The first saved streaming implementation uses synchronous DOS reads, so refill
latency also stalls rendering. Native exit counters record completed 16 KiB
reads, maximum latency, detected queue starvations, track opens and read errors.
The measured sustained test had zero starvations/errors; this does not establish
all controllers or worst-case scenery. Audio quality was not listening-tested.
Full effects/voice arbitration remains separate work.

## Async refill scheduler (v0.0.5)

The default scheduler fills each completed 16 KiB stereo block with four 4 KiB
ACTION_READ packets. Rendering continues between replies. A separate aligned
message/packet and reply port track one outstanding read; shutdown and track
changes collect it before closing a file or reusing its buffer. The 48 KiB audio
queue remains unchanged. Long terrain/wireframe passes service the scheduler at
coarse row/depth boundaries after four PAL ticks, so refills do not depend only
on whole-frame completion. `sync`, `async` and `async8k` build options preserve the
comparison strategies. See PROFILING.md for measured frame pacing and what the
elapsed refill counters include.

Music files span three OFS partitions in one RDB image. Paths use volume names,
so shell working-directory changes do not affect selection. A missing or truncated
file disables further refills and records an error; native fault-injection tests
verify that rendering continues and the program returns to DOS.

## Playlist policy (v0.0.6)

The installed `Special/morrowind title.mp3` and `Explore/Morrowind Title.mp3`
are byte-identical. The old sequential playlist played them consecutively.
The converter now computes canonical identities using converted PCM hashes.
All 18 source files remain available, but duplicate content occupies one entry
in a playback group. Exploration has eight unique songs; battle has seven.
Death/triumph remain in the archive for later event use, outside both groups.

The title starts once, continues into exploration without restarting, and reaches
EOF normally. Automatic exploration selection consumes a shuffled bag, then
refills/shuffles it. A boundary guard skips the current canonical identity when
another song is available. A singleton group must repeat. Empty exploration is
rejected by this prototype's converter; empty battle falls back to exploration.
This is not full OpenMW behaviour for every modded/empty playlist.

F6/F7 are ordered audition controls within the current group. F8 switches between
exploration/battle for testing; there is no implemented combat-state detection.
Manual changes retain the existing blocking stop/open/preload behaviour. Normal
walking, turning and fog changes do not restart the current song. Shuffle state
is in-memory for one run; it is not saved across launches.

OpenMW's music scripts were reviewed as a behaviour reference, without copying
code. See LICENSING_AND_CREDITS.md for the pinned revision. The Amiga implementation
uses a small independent shuffled bag and canonical content identities.
`MWBOOT:MWMUSIC.BIN` is a 136-byte big-endian diagnostic: `MWM1`, uint16 count,
uint16 final group (0 exploration, 1 battle), then 64 uint16 track IDs. It records
the first 64 successful opens. It does not claim to record audible start times.

## Authored door sounds (dev5)

`prepare_door_audio.py` resolves placed DOOR references, their SNAM/ANAM IDs and
the corresponding SOUN files/volumes. It converts only sounds needed by the
entrance catalogue and the Census hall door, sharing identical source files.
The bounded AWSFX1 catalogue stores paths, volumes and durations. Native
`aw_door_sounds` defaults on and persists; `dbg door sounds on/off` is the short
command. Transition openings play before the map change (at most a one-second
lead-in); their closing sample plays after sign-on. The existing Census hall
action plays the opening sample without adding a close action.
