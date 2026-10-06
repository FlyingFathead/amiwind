# Voiced dialogue: event lookup and runtime plan

AmiWind currently auditions one generic voiced HELLO for a small NPC set. The
source records contain a wider event vocabulary, ordered response records,
conditions, response scripts and voice-file references. A static match cannot
prove that a line would play in a particular game state. This note records the
current boundary and a source-only plan for extending it.

## Event types

The names below are dialogue topic IDs found by the current private indexer. A
candidate list is not a trigger implementation. OpenMW's public implementation
provides a useful reference for several event call sites and their shared voice
selection path; it does not establish Bethesda's exact implementation.

| Event | Trigger evidence in OpenMW | AmiWind status |
| --- | --- | --- |
| `hello` | Actor AI proximity greeting after range, visibility and awareness checks. | Current bounded NPC audition topic. |
| `idle` | Probabilistic ambient voice check near the player with line of sight. | Indexed as a candidate topic; no ambient runtime trigger. |
| `attack` | Combat start can request an attack taunt. | Indexed; no combat dialogue runtime. |
| `hit` | Damage can request a hit line using `iVoiceHitOdds`; death animation also requests `hit`. | Indexed; no damage/death voice runtime. |
| `thief` | Crime reporting can request a theft line from a reporting witness. | Indexed; no crime dialogue runtime. |
| `intruder` | Trespass reporting can request an intruder line. | Indexed; no crime dialogue runtime. |
| `flee`, `alarm` | Present in AmiWind's bounded voice-topic index and represent event topics. This research did not verify an OpenMW call site for either. | Indexed only; trigger and selection remain unimplemented. |

OpenMW sends these requests through `DialogueManager::say(actor, topic)`. That
shared path refuses to speak while that actor has an active voice, while an NPC
is submerged, or while the actor is knocked down. It searches the requested
topic without falling back to `Info Refusal`. The first INFO record that passes
actor, player, select and disposition filters wins. `say` can show the response
as a subtitle, play the INFO sound at the actor's head, execute its result
script, and call the Lua response hook. If no INFO matches, it returns false.
See [OpenMW dialogue manager](https://github.com/OpenMW/openmw/blob/master/apps/openmw/mwdialogue/dialoguemanagerimp.cpp#L570)
and [filter order and predicates](https://github.com/OpenMW/openmw/blob/master/apps/openmw/mwdialogue/filter.cpp#L666).

The HELLO trigger checks the actor's Hello AI setting times
`iGreetDistanceMultiplier`, player alive state, actor paralysis, magical
concealment, line of sight and awareness. It requires two qualifying 0.25
second updates. Combat, swimming and AI packages outside Wander, Travel or no
package clear the greeting state. After a successful `say`, the actor faces the
player for `iGreetDuration`; leaving `fGreetDistanceReset` range rearms the
state. See [OpenMW actor greeting logic](https://github.com/OpenMW/openmw/blob/master/apps/openmw/mwmechanics/actors.cpp#L446).
The idle voice check uses `fVoiceIdleOdds`, line of sight, a 3000-unit limit,
nonzero Hello rating, and excludes swimming, combat, Follow and Escort. It also
requires no voice already active. See [OpenMW idle voice logic](https://github.com/OpenMW/openmw/blob/master/apps/openmw/mwmechanics/actors.cpp#L387).

Combat and crime call sites confirm event triggers, not random selection among
matching INFO records: [attack requests](https://github.com/OpenMW/openmw/blob/master/apps/openmw/mwmechanics/mechanicsmanagerimp.cpp),
[damage and death requests](https://github.com/OpenMW/openmw/blob/master/apps/openmw/mwclass/npc.cpp),
and [crime witness requests](https://github.com/OpenMW/openmw/blob/master/apps/openmw/mwmechanics/mechanicsmanagerimp.cpp).
OpenMW's `say` then uses the same first eligible INFO rule. Randomness is in
some trigger probabilities (such as idle and hit odds), not in the observed
response-record selector.

## Conversation GREETING is a separate path

When the player opens conversation, OpenMW scans Dialogue records of type
GREETING in store order and uses the first record with a matching INFO. It
presents the text, runs its result script and response hook, and records that
topic as the last topic. The current OpenMW code marks the sound playback there
as TODO; conversation opening does not call ambient `say`. Later conversation
responses are evaluated through the dialogue filter as the player chooses
topics. See [OpenMW conversation start](https://github.com/OpenMW/openmw/blob/master/apps/openmw/mwdialogue/dialoguemanagerimp.cpp#L130)
and [topic selection](https://github.com/OpenMW/openmw/blob/master/apps/openmw/mwdialogue/dialoguemanagerimp.cpp#L260).

For ambient `say`, the filter returns the first passing INFO in the topic's
record order. Predicates can depend on speaker identity/race/class/faction,
player faction/rank/cell, disposition and select conditions such as globals,
locals, journal, inventory, AI settings and quest state. A reliable evaluator
must retain order and evaluate all relevant predicates; choosing the most
specific-looking line or the first static identity match is not equivalent.

## Current AmiWind implementation

`src/mwad/dialogue_lookup.py` builds a lossless, ordered private index for
`hello`, `idle`, `intruder`, `thief`, `hit`, `attack`, `flee` and `alarm`. It
preserves INFO order, IDs, linked-record fields, condition bytes, sound path,
response text, result script and raw subrecords. Its actor index applies only
static identity filters (deleted status, sex, actor ID, race, class and faction).
It intentionally does not merge mods or evaluate player/context conditions.
The generated voice lookup is written outside the public repository by
`tools/prepare_dialogue_lookup.py`.

`greeting_fixture` in `src/mwad/npc.py` is narrower still: it rejects scripted,
quest/context, faction/rank and location-dependent rows; among the accepted
plain HELLO candidates, it selects the highest disposition threshold and keeps
file order for ties. This is a bounded audition fixture, not OpenMW's general
first-eligible evaluator and not a claim about the original engine's selector.
`tools/prepare_npcs.py` currently uses it for three nonblocking town actors,
converts the chosen owned voice file to mono 11025 Hz unsigned 8-bit PCM, and
sets one `aw_voice` and one `aw_line` per actor. Current nearby greetings use
that one line and the authored distance/reset/duration values. Idle, combat,
crime and conversation dialogue are not wired into this NPC runtime.

## Implementation and verification plan

1. Extend the private audit report to show each event's ordered INFO chain,
   identity candidate count, condition count/types, disposition and faction
   gates, sound availability metadata and result-script presence. Keep source
   paths, response text, original audio and generated indexes outside public
   artifacts.
2. Implement a conservative ordered evaluator for supported conditions. It
   must distinguish “static identity candidate” from “eligible now”, stop at
   the first eligible INFO, preserve unsupported predicates as explicit
   unknowns, and refuse to claim a match when an earlier record is unknown.
   Add test fixtures for precedence, tied records, quest/global/local gates,
   disposition, gender, actor-specific rows, missing sound and scripted rows.
3. Add event triggers incrementally: HELLO state and reset, idle probability,
   combat attack/hit, then crime reporting. Define per-actor voice-busy rules,
   subtitles, range and cooldown behavior before connecting further topics.
   Conversation GREETING and topic selection need their own UI/state design.
4. Test media conversion separately with owner-provided files: codec and sample
   rate acceptance, duration bounds, deterministic output metadata, missing or
   corrupt input, playback completion and actor voice-busy behavior. Keep audio
   and outputs private. Do not include original dialogue, sound files, extracted
   assets or playable asset-bearing builds in public source or CI.
5. Compare the evaluator and trigger edge cases against documented OpenMW
   behavior and synthetic fixtures. OpenMW is an independent GPL reimplementation;
   its behavior is a reference, not proof of Bethesda's source or exact runtime.

## Sources and limits

The topic list and fixture shape were also informed by a private local copy of
the UESP article “Morrowind:Generic Dialogue Voiced”. That corpus is incomplete,
contains expansion material and needs cleanup; it was used as a discovery aid,
not copied into this document or treated as exhaustive. No original dialogue
text or audio is reproduced here.

OpenMW source links above are public and support the stated implementation
behavior. Bethesda's original engine source is not available to this project.
OpenMW details should not be presented as verified original-engine internals.

## Automatic cell-handoff voice continuity candidate

The v0.0.29 source candidate preserves already-playing NPC/intro voice tails
across implicit streaming teardown, without restarting the line or retaining
map-owned cache/entity/lip references. At most four detached tails share128KiB,
including PCM headers; refusal paths are explicit. Existing gain and background
music buffering are unchanged. Source mixer tests pass, but audible target
continuity and worst-case memory acceptance remain open. See
[TRANSITION-VOICE-29](BUG_JOURNAL.md#transition-voice-29-active-speech-stops-during-automatic-cell-handoff-open).

Modal background freeze/blackout is independent of audio. Character selection,
journals and other blocking overlays keep the soundtrack serviced continuously;
only an explicit music stop or shutdown should intentionally interrupt it.
