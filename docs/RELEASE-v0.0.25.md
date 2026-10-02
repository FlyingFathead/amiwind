# AmiWind v0.0.25

A substantial development milestone: full-island terrain traversal, source-derived
region navigation, stricter actor placement, the original-model carried torch,
and the complete NPC inspection gallery, with reusable character conversion.

- 2,526 terrain regions cover the base-game island; detailed Seyda Neen and
  Balmora scenes remain. Broader scenery, settlements and actors are ongoing work.
- Region labels come from the game's own records and coordinates. The world map
  also provides explicit debug teleport selection and confirmation.
- Actor-contact corrections retain strict production checks. Earlier diagnostic
  waivers are not a substitute for passing those checks.
- The carried torch uses the original game model; compass visibility is optional.
- Normal builds include the complete NPC/creature gallery and its model budgets.
  Verified persistent caching reuses compatible models across build/recovery runs.
- Build summaries include dates, elapsed time, tool identities, warnings, output
  size and SHA-256. Recovery retains completed terrain and music.

### Build scheduling in this milestone

NPC gallery workers now collect finished jobs immediately and refill a bounded
submission window before reporting results. Slow earlier models no longer block
later submissions. Existing order-dependent scene stages retain ordered execution.

The stage heading explicitly reads
`npc-gallery (pre-baking in-game character models...)`.
Progress reports cumulative reused, successfully converted, failed and remaining
model counts, with elapsed seconds. It prints at 25 completions, on failure, at
completion, or on the first result after five seconds without a report. The outer
build heartbeat still reports elapsed time while no model has finished.

The complete catalogue is restored to original source order before export.
All NPC/creature models, gallery content, protected geometry and strict validation
remain mandatory. This changes host scheduling only. The converter, polygon
budgets, bounded retry policy and model-cache identities are unchanged, so valid
rc10 cache entries remain reusable. No extra work is moved onto the Amiga.

Apply after the current build finishes. Image recovery retains the original rc3
terrain/music and uses the persistent model cache produced by rc10. No rc10 seed
import is needed: use the same workspace or explicitly select its gallery cache.
The optional stopped-rc9 import remains available for older completed pairs.

See [NPC model reuse](NPC_MODEL_CACHE.md) and the
[validation receipt](validation/v0.0.25-source.json). A complete cold-gallery speedup
has not been measured; cache checking and individual model conversion costs still
exist. Scheduling changes do not alter process interruption handling.

v0.0.25 marks a substantial development milestone. Full game HDF assembly and target gameplay
acceptance are separate checks. The longstanding fist blink, unknown F-toggle
state bug, static asset gallery and mutable character equipment remain open.
