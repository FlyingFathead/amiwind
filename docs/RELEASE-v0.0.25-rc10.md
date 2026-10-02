# AmiWind v0.0.25-rc10

Character conversion now uses a persistent, verified host-side appearance cache
across build and recovery runs. Unchanged models are reused; corrupt, partial or
incompatible entries are rebuilt. The complete NPC gallery, strict actor/model
gates, protected geometry and Amiga model representation remain required.

- Default cache: `WORKSPACE/cache/npc-gallery-v1`; optional `--gallery-cache`.
- Optional `--gallery-seed-run` imports completed compatible pairs from a stopped
  rc9 run after input/source/environment and output verification.
- Stage label: `npc-gallery: pre-baking in-game character models...`, followed by
  verified hit/conversion counts and a machine-readable reuse report.
- Gallery storage estimates include output, new cache entries, auxiliaries and
  a margin. They do not replace full-image capacity planning.
- No added rendering work on the Amiga; converter quality settings are unchanged.

See [cache behavior and recovery](NPC_MODEL_CACHE.md) and the
[validation receipt](validation/rc10-source.json) for measured results and scope.
Cold conversion of an empty cache is still required. Per-component baking reuse
and runtime modular NPC assembly remain future work. The
[equipment roadmap](CHARACTER_EQUIPMENT_ROADMAP.md) explicitly requires partial
corpse looting and equipment changes; fixed outfits are not the final design.

Inherited rc9 features include the original-model torch, region HUD and restored
default NPC gallery. The longstanding momentary fist blink and separate unknown
F-toggle state issue remain open. The static-asset gallery remains planned.
Target playtesting and explicit owner acceptance are required before final
v0.0.25 promotion. Public packages contain source, not owned game payloads.
