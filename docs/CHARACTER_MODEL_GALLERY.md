# Character Model Gallery

rc10 adds [verified persistent NPC model reuse](NPC_MODEL_CACHE.md). Full gallery
coverage and protected model quality remain mandatory.

**Outside approval is required for any exception affecting either gallery.**
Neither the NPC gallery nor the upcoming static-asset gallery may be disabled,
reduced or bypassed, including model/asset generation, catalogue coverage,
quality and validation, without a specific documented case or scenario **and
explicit approval from the project owner**. A builder or contributor cannot
approve its own exception. Build time, disk pressure and convenience do not
supply that approval. An opt-out flag is a mechanism for an approved exceptional
debugging case, not permission to choose that exception independently.

All NPCs and other game assets must remain intact, packaged and loadable by the
engine for the complete game to function properly. Skipping their creation
alongside either gallery is pointless and counterproductive: the final product
requires those assets anyway. An exceptional debug build must be labelled
incomplete and cannot redefine the complete game's required content. Runtime
loading may be on demand; this does not require every asset to reside in RAM
simultaneously. The static-asset gallery is still planned, not implemented.

**First prerequisite: sufficient build capacity.** Before starting, verify
usable space for all required models/content, intermediates, staging copies,
temporary images, final outputs, verification copies and a safety margin. Check
the actual output filesystem and quota. RAM-backed scratch also consumes the
process/container memory budget; it is not extra independent disk capacity.
If space is insufficient, provide capacity before expensive conversion begins.
Do not skip NPC models or gallery creation to make the build fit.

**All NPCs must be included and loadable by the engine for the game to be complete.
NPC gallery creation MUST NOT be skipped except for exceptional, explicitly
requested debugging purposes. Build time and disk usage are not reasons to omit it.**

Skipping NPC model creation together with the gallery is pointless and
counterproductive for a complete build: all character models are still required
in the final product. Exceptional debugging may temporarily isolate the gallery;
it cannot reduce the final game's required content.

The gallery is an isolated debug inspection scene. It loads one selected model
and its footprint square, at source scale, on a finite fogged plane. Its purpose
is to reveal conversion problems before actors are added to more towns.

**Build requirement: normal game builds and image recovery MUST include the NPC
gallery. Do not skip it, change the default, or silently reduce its catalogue to
save conversion time or disk space. Missing inputs/models are build failures.**

A complete Morrowind implementation requires all original NPCs and creatures,
with their required assets available to the engine. The gallery is the required
way to inspect and regression-test that content; omitting it is not a valid
content optimization. Share/cache converted assets with verified dependencies
instead of removing coverage. The current demake does not yet place every original world reference.

Only the owner's explicit `--no-npc-gallery` permits a **debugging-only** build
without the inspection gallery. It must never remove required game NPCs, models,
placements, dialogue or dependencies, and must never become the normal default.
The future static-asset gallery must follow the same rule once implemented.

## Controls

| Action | Control |
| --- | --- |
| Enter the gallery | `dbg gallery`, `dbg aw charplane`, `dbg modelgallery`, `dbg npcgallery` |
| Browse friendly names | Tab, B or middle-click |
| Search the browser | Type case-insensitive keywords; Enter applies the filter |
| Move through results | Arrows, wheel, Page Up/Down; Shift+Up/Down on classic Amiga keyboards |
| Show a browser result | Enter after selecting it, or click its row |
| Scroll with the pointer | Click or drag the right-hand scrollbar |
| Close the browser | Tab, Escape or middle-click |
| Next / previous model | Wheel down/up or Shift+N / Shift+P |
| Equipped / base body | Shift+B |
| Exact source ID, display name or conversion number | Enter in the gallery |
| Preview an available converted greeting | E |
| Gallery-only help | F1; F1 or Escape closes it |
| Return to the captured game | Ctrl+X or F10, then `dbg gallery exit` |

The selected name stays at the bottom right below the viewport. The Talk hint
appears only for entries with a converted greeting. Repeated friendly names may
represent different original records; the browser shows IDs and stable
conversion numbers as well. Exact-name lookup reports ambiguity and chooses the
first stable number. Use the original ID to select a particular variant.

The browser draws its own cursor and captures mouse motion from the camera.
Wheel scrolling works in the browser and cycles models in the inspection view.
The current preset sets `middle_click_ungrab = 0`; use F12+G to release mouse
capture. See [FS-UAE middle-button settings](https://fs-uae.net/docs/options/middle-click-ungrab/). The FS-UAE preset explicitly maps host
PageUp/PageDown to raw navigation codes 0x68/0x69; its unmodified classic layout
maps those host keys to keypad ')' and Right Amiga instead. The engine also
accepts standard extended Amiga page-key codes 0x48/0x49. See
[FS-UAE keyboard mapping](https://fs-uae.net/docs/keyboard-mapping/).

## Memory and return state

The catalogue stays on disk. Opening the browser allocates at most eight rows;
opening, applying a filter or changing pages scans it one line at a time. Typing
and drawing do not reread the catalogue. Closing the browser frees those rows.
Normal gameplay performs no gallery catalogue scans. Selecting another character
replaces the inspection scene rather than keeping earlier models resident.

Entry captures a temporary snapshot of the supported save state: actor positions
and greeting counters, character data, story, inventory/global/journal state,
world clock, scene, player position and view. Health, movement mode and hand state
are restored as well. This uses no normal save slot and is not a crash-recovery
save. A missing return map retains the snapshot and reports the problem. A new
game or unrelated explicit map load abandons the excursion; use the gallery exit
command when you want to return. State outside the current save implementation,
such as future combat or schedules, needs corresponding snapshot support.

## Dialogue and coverage boundaries

The current E action previews the bounded greetings already converted for
playable residents. It is not a complete original dialogue-tree interpreter.
The same one-character scene is intended for future topic, condition and result
script testing; those tests should start from a declared state and roll back on
exit. Long dialogue and topic menus need reusable vertical scrolling.

A complete source-record inventory is distinct from complete visual acceptance.
Keep failed conversions in the catalogue with an explicit error, preserve their
original identities in the private audit, and never silently omit them from
coverage counts. Native model-load and visual checks are required before claiming
that every creature renders correctly. Equipped and base-body views do not imply
working equipment removal in normal gameplay.

## Model identity and inspection ledger

`gallery/inspection.tsv` is a generated private conversion table. Every row links
an original `NPC_` or `CREA` record, friendly name and gallery number to an
equipped/base-body asset, its SHA-256, conversion result and inspection status.
Gallery numbers are deterministic for the same base-master inventory; they are
AmiWind numbers, not original Morrowind placed-reference numbers. The source ID
remains authoritative if the master inventory changes.

Inspect a distinct model once and reuse that decision for records whose converted
asset is byte-identical. Do not conflate character identity with appearance:
shared names can have different outfits, and many distinct residents can share
one appearance. Dialogue and world placement still need their own checks.

An optional private `--reviews` JSON maps a model key to `sha256`, `status`
(`accepted` or `rejected`) and any owner notes. Only a matching content checksum
carries the decision into the next table. A changed asset returns to `unreviewed`;
conversion success alone never means visual acceptance.

## Optional per-model geometry allowance

The original software alias renderer permits 2,000 vertices. The existing
face-local texture layout consumes three vertices per triangle, so ordinary
conversions retain their previous 666-triangle budget. The gallery converter can
allow up to 1,024 triangles (3,072 face-local vertices) for a recorded model;
this does not force every model to grow. The original 777 trial is retained as
a selectable restrictive cap.

The engine defaults to `aw_allow_poly_budget_over true` and
`aw_poly_budget_over_cap auto` to use each
listed model's recorded allowance. A numeric cap (666–1,024) adds
an overall ceiling; for example `aw_poly_budget_over_cap 777`.
Both settings persist. Existing shared-vertex models within 2,000 vertices keep
their original allowance. Invalid cap values are rejected through the console;
programmatic invalid values cannot enable an oversized render.

The ordinary draw path retains 2,000-vertex work arrays. Only an extended model
uses the expanded draw frame: 47,168 additional bytes (about 46.1 KiB) for vertex
work arrays, plus that asset's additional model/skin data. The 11 MiB engine arena
is unchanged. The measured native draw frames are 88,044 bytes for the original path and
135,212 bytes for the extended path, within the unchanged 300,000-byte task
stack. Focused native checks pass; physical-hardware performance remains open. The pre-experiment engine source is retained separately with a
checksum so the exact original implementation remains recoverable.

## Per-model budget exceptions

The host-side `tools/audit_gallery_budgets.py` finds failed oversized conversions,
optionally retries them under the tested larger budget, and emits the private
`model-budgets.txt` table. Successful ordinary models are retained. Each exception
contains its model path, exact vertex/triangle counts, file length and CRC-32;
the private audit also records SHA-256, source records and the reason. The runtime
checks the matching bytes once on load. It does not scan this table during an
ordinary model's load or in the draw loop. CRC-32 detects stale/mismatched bytes;
it is not a security signature. Build/readback verification uses SHA-256.

The runtime requires all three: the opt-in switch, a matching model-specific
exception, and a sufficient numeric cap (or `auto`). A changed model cannot reuse
a stale exception. Models beyond the current tested renderer ceiling remain
reported failures. Neither automatic exception generation nor a higher polygon
count constitutes visual acceptance; the inspection ledger remains authoritative.

## Default NPC gallery: required unless explicitly disabled

Every normal AGA game build and image recovery includes the NPC/creature gallery.
It is a debugging and regression-inspection tool, not optional content selected
silently by the builder. A missing catalogue, selected model, footprint,
inspection map or budget receipt fails the default build.

Only the owner's explicit `--no-npc-gallery` flag permits an exceptional
debugging build without it, for example to isolate a gallery-specific failure.
This must not be used as a time/space optimization. The build receipt, final
summary and image metadata record the choice; the console explains
that the gallery was disabled. The separate asset-free CI/dry-run recipe does not
contain owned game assets and therefore cannot include the game catalogue.

The `npc-gallery` stage converts the complete source catalogue and compiles
`charplane.bsp`, with bounded model-budget retries and byte-specific allowances.
It reads the reserved scene palette after Census; its own files live in a separate
output tree. World-terrain waits for it, exposing failures before the expensive
island pass. Image assembly checks the required file inventory and every checksum,
stages existing greetings, then verifies the final filesystem payload on readback.
A gallery visual inspection is still required; conversion success is not visual
approval of every model.

Recovery reuses terrain and music but creates the missing gallery in the new run.
The first recovery with this fix therefore has a substantial additional conversion
stage. An older image's missing catalogue never implies an opt-out. rc10 uses a verified persistent model cache across runs while still assembling
each new output independently. See [cache identity, compatible rc9 import and
capacity checks](NPC_MODEL_CACHE.md).

## RC3 conversion coverage and authored poses

The base master contains 2,935 NPC/creature records (260 creature records),
sharing 3,551 distinct equipped/base assets. All 3,551 convert in RC3; 29 require
the opt-in allowance. The preceding RC2 had 25 failed conversions and three
smaller trial allowances. No missing entry is hidden or replaced with a generic
actor. Conversion success remains separate from individual visual acceptance.

`config/gallery_model_quality.json` records targeted profiles. Dagoth Ur keeps
all 240 mask, 47 crest and 30 neck-piece triangles; the complete model has 903
triangles and uses 16-pixel face tiles to retain more of the original gold texture.
Both source records share the same result. Gallery models receive steady daylight
for inspection; normal scene lighting is unchanged. Skin-tone table repairs
are documented in [the conversion journal](IMPLEMENTATION_JOURNAL.md#j027--pale-faces-mapped-back-to-sky-grey).

Vivec uses the authored crossed-leg idle-loop key; the cliff racer uses its
authored airborne idle entry. `gallery/poses.txt` carries their source-derived
height offsets. The selected model reads that small table only when loaded;
normal gameplay does not scan it. Nonlinear animation curves are accepted only
at an exact authored key, outside the key range, or on a constant interval;
other samples fail explicitly. These two static poses do not implement flight,
scripted falls, AI or the full animation set. Other creatures retain their rest
mesh until an inspected pose profile is added.

The startup command `aw_gallery_migrate` enables the previously disabled shipped
allowance once. The archived `aw_gallery_defaults` marker preserves subsequent
explicit opt-outs. Exact model-byte checks and the 1,024-triangle ceiling still apply.

**Warning: gallery omission is for debugging builds only. All NPCs and their
required assets remain necessary for a complete game. `--no-npc-gallery` skips
inspection-only conversion/packaging; it must never remove world NPC placements,
models, dialogue or other gameplay dependencies, or be advertised as a complete
content profile. Normal builds include the NPC gallery for debugging and
regression inspection. This requirement does not claim that every original
world NPC has already been converted or placed by the current demake.**

## rc9 preservation check

Dagoth Ur's `dagoth-mask-v1` profile, gallery converter, budget-audit tool and
shared bake/MDL encoder remain unchanged from rc8. Re-conversion with the old
and new source on the same owned input/palette produced byte-identical Dagoth Ur
models: 903 triangles, 2,709 face-local vertices, 16-pixel atlas tiles. The mask,
mask-part and neck minimums remain 240, 47 and 30 faces. Runtime allowance defaults,
the `auto` cap and the 1,024-triangle ceiling are unchanged. The private SHA-256
comparison is recorded in the rc9 validation receipt. Target visual retesting is
still required, and no historical inspection approval is invented.
