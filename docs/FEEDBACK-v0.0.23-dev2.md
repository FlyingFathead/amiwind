# Owner playtest feedback — v0.0.23-dev2

Received 29 September 2026 (Europe/Helsinki), following publication of commit
`e368511551657b67cf84049934b093c97749d0ae`. These are observed playtest reports;
a passing synthetic test does not close an owner-reported gameplay defect.

## Working in the owner's playtest

- The pier guard no longer spins around their axis during the escort.
- The introduction from the ship through the Census Office works reasonably well.

Preserve both while changing collision, menus and speech timing.

## Feedback and disposition

| Report / request | dev3 disposition / remaining work |
| --- | --- |
| Ship creaking/splashing drowns out opening speech | Boat Hull converted once from the original at -5 dB; unchanged speech/music. Measured -4.99 dB after quantization. Owner listening acceptance pending. |
| Player can walk off the deck/pier during creation | **Open regression.** All 22 authored collision boxes are present, and their source collision-mesh dimensions were rechecked. Existing synthetic box/stage tests are insufficient evidence of a closed route. Reproduce side escapes on deck, plank and pier; inspect physical rails and gaps as well as script gating. Do not mark fixed from source presence. |
| Pier appearance choice needs an overlay confirmation showing the selection | Added confirmation showing race/sex and face/hair selections; back preserves edits. |
| Census character choices/review need confirmation | Added confirmation showing selected race/sex, class and birthsign; progress advances only after Choose/Y. |
| Speaker names consume too much dialogue space | Voice headers hidden in default aim-only mode; the freed row is used for speech. Above-left, classic inside, target-only and upper-right speaker styles remain available in configured mode. Panel position/height unchanged. |
| NPC name disappears when Talk is unavailable | Aim identification now defaults on after creation and is independent of voice/cooldown availability; Talk is a separate action hint. |
| Voiceover speaker names should default off, with Interface controls | Added a voiced/unvoiced distinction, default-off voiceover identity, and persisted Interface options. |
| Need alternatives for aimed-at NPC labels | Separate on/off toggle and three placements: top right over world, lower right below world, left above status bars. Suppressed during creation until the Census review has completed. |
| Barrel/object labels should use configurable placement too | Same three positions exposed independently for interaction labels, keeping the action prompt separate. |
| F1 help needs logo and actual bindings in console format | Logo and paged console-font listing reads current key bindings, including customized and additional commands. |
| Interior doors lack open/close squeak | **Open.** Import the original DOOR sound references and test opening/closing cues across ordinary interaction and scene loading. Do not substitute music or full loading-screen audio. |
| Interior door movement appears almost instantaneous | Retained as a lower priority than missing sound. Any animation must respect the native frame/memory budget and preserve collision/interaction gates. |
| Bitmap text in papers remains visually poor (attached Sellus Gravius capture) | Confirmed visible rough/broken strokes; README and playtest handoff recommend the TTF-converted variant. Bitmap remains a compatibility/comparison build; no font-quality fix claimed. |
| Wait for X hours and configurable controls | T selector for 1–24 hours; saved clock/date and `dbg timeofday`; existing console `bind` supports changes. Graphical rebinding remains pending. |

| New residents do not turn toward the player (part 7) | **Open.** Existing greeting-only turning is not a complete conversation-facing state. Reproduce on local residents, extend contact/interaction behaviour, and preserve scripted escort control. |
| Sky-coloured holes in Vodunius Nuccius’ House (parts 8 and 10) | Fixed far-cull mismatch between world traversal and brush fragments. Native checks at `42 291 79 / 349 / 0`, `-13 288 76 / 353 / -1`, and `-12 190 72 / 4 / -2` plus screenshot heading 9/pitch -1. No renderer edge/surface overflow. |
| Open hillside at `263 463 19 / 352 / -17` (part 9) | Rock `terrain_rock_bc_18`, placed reference 251560, was included but transformed in the wrong compound order. Corrected and rebuilt exterior closes the reported gap; see [What are rocks?](WHAT_ARE_ROCKS.md). |
| Voice dialogue style 2 should override name settings (second part 10) | Added archived `aw_voice_dialogue_display_style`, default 2: aim-only identity overrides speaker-name layouts/toggle during sampled speech. No header, no reserved header row. |

## Next maintenance gate

Before claiming intro containment fixed, walk sideways against both edges of each
segment, test the forward route to the guard/office, repeat after race acceptance,
and verify release removes only the intended restrictions. Retain the successful
escort behaviour. Add recorded positions/headings for each failed and repaired
boundary. Door cues must be checked audibly at both ends of loading transitions.

See [dated work plan](PLAN-2026-09-29.md) and
[dev3 controls](DIALOGUE_AND_WAIT.md). Full voice behaviour remains the next content
milestone; UI placement experiments do not complete original dialogue semantics.
