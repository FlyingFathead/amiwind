# Intro script mapping — v0.0.18-dev2

The owned base master and its ordered script/voice records are authoritative.
Private conversion writes `intro-conversion.json` with extracted scripts, source
voice hashes, actor appearances, navigation and sound-emitter provenance. The
public repository carries the converter and adapter, not those extracted assets.

## Runtime approach

Use a small native state adapter for the currently supported opening scripts.
The host resolves appearances, source paths, head morphs, animation groups and
speech envelopes; the Amiga reads bounded data and advances explicit states.
There is no Lua runtime or general MWScript compatibility claim. This avoids
adding another interpreter before the required state/actions have been mapped.
A later compact instruction format can share the same action interfaces once
more scripts require them; benchmark it before choosing a broader VM.

Each future placed reference needs stable identity, enabled/deleted state,
script locals, inventory and position across scene changes. The player needs one
character record shared by name/race/class/birthsign/review, game time, quest
state and saved data. The current name is transient; this persistence layer is
still open. Original commands must not silently become successful no-ops.

## Authored order and current coverage

| Stage | Source behavior | Current coverage |
| --- | --- | --- |
| Initial setup | Player placement; restrict movement, jumping, fighting, magic, view changes and menus | Ship placement and initial movement/action gates; camera still the calibrated Nord fixture |
| Jiub | First speech, name menu, further speech and guard-proximity response | Original clips/subtitles, name input, playback-clock completion and bounded state transitions |
| Escort | Eight-second pause; travel downstairs; first instruction; movement help; escort upstairs; final instruction/reminders | Original path grid, walk poses, collision sweeps and player-distance wait; inspect checkpoint evidence for route coverage |
| Upper guard | Two proximity lines with a six-second repeat timer | Converted and connected, with global speech-overlap prevention |
| Deck guard | Direct the player toward the dock; repeat reminder | Clips/appearance prepared; exterior script stage pending |
| Dock guard | Travel to plank; lock controls; first line; race/sex/head/hair menu; follow-up and travel to office | Clips/appearance prepared; movement and creation UI pending |
| Socucius | Greeting, class choice, birthsign, review, creation approval and papers | Clips/appearance prepared; Census scene, tables and menus pending |
| Door guard | Require registration papers; explain when absent | Prepared speech; item and door gates pending |
| Ring and captain | Ring-dependent entry, release conversation/package and final state | Source audit only; inventory, dialogue and release gates pending |

The original ship has a CharGen collision activator tied to progression. Its
geometry and disable condition need direct conversion/audit; do not assume that
all introductory restrictions are invisible walls, or that no such barrier exists.
Dev4 adds body collision for the three ship actors. General NPC collision,
combat/crime and dialogue conditions remain separate work.

## Voices and faces

AWL1 envelopes store four mouth levels at 25Hz plus the exact converted PCM
sample count. Native poses follow the audio playback sample clock; missing or
invalid envelopes close the mouth. Original Talk/Blink morph targets supply the
poses. Blinking uses the maximum authored closed-eye key; walking uses loop
keys with root XY displacement removed. This is amplitude synchronization, not
phoneme/viseme recognition. Legacy eight-frame actors remain supported. Final packed models were checked:
talk alters 111–161 vertices and blink alters 8–20 vertices across the ten
appearances, so byte quantization retains both effects.

## Light, time, ambience and music

The base source starts GameHour at 9, TimeScale at 30, Day at 16, Month at 7 and
Year at 427. A dark ship hold therefore does not establish a night-time start.
Dev2 removes the exterior ambient-light minimum inside the ship and retains
baked localized lighting. It does not implement a game clock, day/night, weather
or waiting. Waiting must be gated by actual character-creation/release state.

Two placed hull barrels run the original Boat Hull loop at scripted volume.
Their runtime attenuation is a Quake approximation, not original sound-distance
parity. Available creak sound records alone do not establish a placed creak
emitter. Swinging lamp scripts and their dynamic shadows are not implemented.

Dev4 boots with `Music/Special/morrowind title.mp3`. New Game resets the
established exploration track 04 (`Music/Explore/mx_explore_3.mp3`) first. No exact intro
song was established by the audited CharGen scripts, so this choice is not
claimed as original intro music parity. The owner subsequently supplied the original prologue video; it is included
in the private dev4/dev5 conversions. Dev5 adds 320×200 playback and optional
readable native-font cards. The exact original ship music sequence remains open.


## Dev5 deck guard

Rebind introductory actor references whenever a map spawns. The original
CharGenBoatNPC adapter greets once when within 180 source units (45 runtime
units) and when speech is idle. Its reminder timer advances only nearby and
without speech; after six seconds it repeats the second line. The timer pauses
in menus. New Game resets this local state; a hatch round trip preserves it.
Deck-guard body collision is enabled; dock race-selection menus remain pending.
