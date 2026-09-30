# Character Model Gallery

The gallery is an isolated debug inspection scene. It loads one selected model
and its footprint square, at source scale, on a finite fogged plane. Its purpose
is to reveal conversion problems before actors are added to more towns.

## Controls

| Action | Control |
| --- | --- |
| Enter the gallery | `dbg gallery`, `dbg aw charplane`, `dbg modelgallery`, `dbg npcgallery` |
| Browse friendly names | Tab or B |
| Search the browser | Type case-insensitive keywords; Enter applies the filter |
| Move through results | Arrows, wheel, Page Up/Down, Home/End |
| Show a browser result | Enter after selecting it |
| Close the browser | Tab or Escape |
| Next / previous model | Shift+N / Shift+P |
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

## Optional 777-triangle trial

The original software alias renderer permits 2,000 vertices. The existing
face-local texture layout consumes three vertices per triangle, so ordinary
conversions retain their previous 666-triangle budget. The gallery converter can
trial 777 triangles (2,331 vertices); this does not force every model to grow.

The engine defaults to `aw_allow_poly_budget_over false`. Use
`aw_allow_poly_budget_over true` and `aw_poly_budget_over_cap auto` to use each
listed model's recorded allowance. `auto` is the default cap setting, with the
extension disabled by default. A numeric cap (666–777 in this first trial) adds
an overall ceiling; for example `aw_poly_budget_over_cap 777`.
Both settings persist. Existing shared-vertex models within 2,000 vertices keep
their original allowance. Invalid cap values are rejected through the console;
programmatic invalid values cannot enable an oversized render.

The ordinary draw path retains 2,000-vertex work arrays. Only an extended model
uses the expanded draw frame: 14,564 additional bytes (about 14.2 KiB) for vertex
work arrays, plus that asset's additional model/skin data. The 11 MiB engine arena
is unchanged. Native stack and frame-time checks are required before this trial
is accepted. The pre-experiment engine source is retained separately with a
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
