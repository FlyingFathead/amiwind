# Character Model Gallery

The gallery is an isolated debug inspection scene. It loads one selected model
and its footprint square, at source scale, on a finite fogged plane. Its purpose
is to reveal conversion problems before actors are added to more towns.

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

## Building and staging the private catalogue

Run `prepare_gallery.py` with the owned Data Files, palette and external output
folder. Then run `audit_gallery_budgets.py --retry` against that folder. The audit
returns a nonzero result while any models remain unresolved; inspect the report.
`stage_gallery.py --gallery PATH --id1 PATH` copies successful assets, preserves
failed catalogue entries, regenerates byte-specific allowances, and collects
existing playable-resident greetings. Compile `charplane.map` with the same BSP,
lighting and standing-hull pipeline used for the runtime. No catalogue/model data
belongs in the public source ZIP. The gallery inspection table stays private.

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
