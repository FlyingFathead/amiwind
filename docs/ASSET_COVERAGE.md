# Asset coverage

## Current dev4 checkpoint — 6 October 2026

The **v0.0.29-dev4 development snapshot** now has an assembled game image and
bounded native checks. This supersedes the preparation-only status in the dated
history below. The public distribution contains source code, not game assets.

| Category | Available originals converted | Missing referenced originals | Conversion failures | Dev4 image/readback scope |
|---|---:|---:|---:|---|
| Videos | 17/17 | 0 | 0 | 17 videos; 16 new batch outputs plus the retained higher-resolution intro |
| Music | 18/18 | 0 | 0 | All 18 converted soundtrack streams included |
| Voices | 6,447/6,447 | 7 | 0 | Converted batch included |
| Sound effects | 717/717 | 2 | 0 | Converted batch included |

These denominators cover the inspected available input set. Missing references
are additional source gaps. Complete in-game event/playback acceptance is still
unknown; three original videos have no embedded audio and need correct separate
soundtrack/event handling. Included is not synonymous with individually played.

**Small mushrooms:** six original placements are integrated across overlapping
maps, using shared alias models in 32 town catalogues and embedded brush geometry
in nine world maps. One native Luminous Russula pickup granted one ingredient,
disappeared, resisted repeat pickup, and remained picked in the tested map-return
and save/load sequence. This is one accepted interaction, not six individually
accepted placements or worldwide coverage. Empty outcomes and dense maps still
need target checks. The compact/global follow-on is outside this dev4 snapshot.

The frozen dev4 suite ran 953 tests (949 passed, four skipped), and the 68040
engine/boot checker compiled. Four bounded native groups passed. See
[dev4 release notes](RELEASE-v0.0.29-dev4.md) for limitations, including the
quickload equipment reset, transition pauses and allocation reserve warnings.

## Earlier dated coverage snapshots


Last updated: **5 October 2026, 20:56 UTC**.
Snapshot: **v0.0.29-dev3 packaged output** and **v0.0.29-dev4 preparation**.
The public release remains v0.0.28; the development results below do not describe
that release's contents or announce a new public release.

All available audio and video files in the inspected input set have converted.
The larger media batch is staged for the next development build. Whole-game
import completion and complete runtime acceptance have **not** been established.

## Version history

| Version / snapshot | Packaged output | Conversion prepared for this version | Runtime acceptance |
|---|---|---|---|
| v0.0.28 public release | Historical category denominators not reconstructed here | See its [release notes](RELEASE-v0.0.28.md) | Use that release's recorded scope; do not infer current counts |
| v0.0.29-dev3 / 5 October | 10,766 files; 156 WAV, 23 lip, 3 AWV and 18 MWS artifacts; 3,551 gallery model keys and 275 head/hair parts | Complete historical source-conversion counts unknown | Bounded scene checks; whole-asset coverage unknown |
| v0.0.29-dev4 preparation / 5 October | No completed dev4 package claimed | 6,447 voices, 717 effects, 18 music tracks and 17 videos; 9 missing original audio references, 0 failed media outputs | Full-batch event/playback acceptance pending |
| v0.0.29-dev4 mushroom diagnostic / 5 October, 18:45 UTC | No new packaged count claimed | 6 original placements from 3 source models converted into a bounded diagnostic sample | Native appearance untested; harvest interaction not implemented |
| v0.0.29-dev4 harvest source candidate / 5 October, 19:15 UTC | 0 new mushroom placements in a delivered playtest | The same 6 diagnostic source placements now have original-content harvest catalogues and tested pickup/save logic | 0 native-accepted harvest placements; native pickup/appearance pending |
| v0.0.29-dev4 hand diagnostic / 5 October, 19:15 UTC | 40 MDLs plus catalogue/emitter read back from a separate diagnostic image; no delivered playtest count claimed | 20 race/sex model pairs generated | Nord punch/torch checks and Argonian demo selection observed; complete live race coverage pending |
| v0.0.29-dev4 mushroom cue/preview / 5 October, 19:30 UTC | 0 new packaged placements or cue outputs claimed | 1 selected source effect converted; source/runtime fixture passed; static preview owner-approved | Native pickup, appearance and audible cue remain unaccepted; requested interaction prompt pending |

The [machine-readable history](asset-coverage/history.json) records units and
dated stages for later comparison. Append snapshots when a version's conversion,
packaging or acceptance status changes; keep earlier snapshots intact. A staged
conversion is not counted as packaged. Current-input content revalidation is a
separate field: recorded conversion results do not prove unchanged source bytes
when only the path inventory has been rescanned.

## What the counts mean

The inventory contains **20,943 unique source paths**, merging the standard
Morrowind, Tribunal and Bloodmoon archives with loose-file overrides. Archive
and master containers themselves are excluded. Counts describe this inspected
input set; other editions, languages and mods can differ.

Dev3 contains **10,766 payload files**. Source paths and output files are different
units: several inputs can form one atlas or character model, while one input can
produce several outputs. Dividing these totals would give a misleading overall
completion percentage. Placed objects, towns, quests and runtime behavior also
need separate coverage measurements.

## Media

| Category | Available source files | Converted for next build | Missing referenced sources | Failed outputs | Exact new output also present in dev3 |
|---|---:|---:|---:|---:|---:|
| Voices | 6,447 | 6,447 | 7 | 0 | 0 |
| Sound effects | 717 | 717 | 2 | 0 | 0 |
| Music | 18 | 18 | 0 | 0 | 18 |
| Videos | 17 | 17 | 0 | 0 | 0 |

The last column compares paths, sizes and SHA-256 hashes from the new conversion
batch against the frozen dev3 image. **Zero does not mean dev3 has no audio or
video:** it already contains 156 WAV files, 23 lip files and three AWV videos
from earlier conversions. The complete new media batch was prepared afterward.
All 18 soundtrack streams match the packaged dev3 outputs.

Seven voice references and two sound-effect references request absent original
files. They are missing input, not conversion failures. The exact references,
source evidence and investigation checklist are in
[missing media references](MEDIA_MISSING_REFERENCES.md).

Three videos have no embedded audio stream. Their duration-matched silent PCM
allows conversion, but separate soundtrack/event mapping remains an open task.
Successful conversion does not prove that every game event finds or plays the
correct audio/video. Complete per-asset runtime acceptance counts are unknown.

## Other source files

| Category | Available source paths | Complete source-to-output coverage |
|---|---:|---|
| NIF meshes | 7,319 | Unknown |
| KF animation files | 162 | Unknown |
| Textures | 4,783 | Unknown |
| Icons | 1,427 | Unknown |
| Font files | 8 | Unknown |
| Other files | 45 | Unknown |

Unknown means a complete mapping has not yet been established. It does not mean
none of these assets are used. Scenery can be embedded in BSPs; character models
combine source parts; textures may be remapped or combined into atlases.

## Verified conversion and packaging subsets

| Scope and unit | Converted/catalogued | Packaged evidence | Runtime coverage limit |
|---|---:|---|---|
| Base-master gallery character identities | 2,935: 2,675 NPC records and 260 creature records | Catalogue selects the appearance models below | Not proof of placement, AI or dialogue for every character |
| Gallery appearance models | 3,551 distinct ready model keys | All 3,551 hashes reconciled: 1,197 direct, 2,354 through recorded palette postprocessing | All 5,870 presentation inspection rows remain unreviewed in the catalogue |
| Character-creation definitions | 10 playable races, 21 classes, 13 birthsigns | AWC1 catalogue checked | Selected screens observed; every combination not individually accepted |
| Selected head/hair parts | 275 | 275 AWH files accounted for | Complete preview-by-preview acceptance unknown |
| Soundtrack tracks | 18 | All 18 converted MWS stream hashes match | Complete track/event playback acceptance unknown |
| Journal metadata | 629 topics, 2,489 entries | Associated world UI files match conversion receipt | Does not mean 629 functioning quests |

The gallery has two presentation rows per character identity, with shared models
between some identities. Its 7,102 physical MDL files include companion
footprints; this is not 7,102 unique NPCs. Later palette transformations are
tracked through input/output hash pairs, not mistaken for missing models.

## World and gameplay coverage

| Area | Current scope | Still to establish |
|---|---|---|
| Seyda Neen | Detailed town content; dev3 package boot/gameplay checked; restored Indrele shack front walls verified natively and confirmed by the playtester | Exhaustive buildings/interiors, collision, flora, lights, event audio and crossing acceptance |
| Balmora | Detailed region outputs included | Complete original-reference coverage and current per-area gameplay acceptance |
| Other Vvardenfell regions | Terrain and selected scenery outputs exist | Complete scenery, actors, interactions, interiors and regional gameplay |

Dev3's 2,723 BSP files include split/overlapping runtime regions and special
scenes. They are not 2,723 original cells or proof that all towns are populated.
The 31 reading artifacts likewise do not establish coverage of every original
book: the files include layouts and other text resources.

Future geographic percentages require a declared area boundary and original
cell/placement denominator. Each source placement must have an explicit outcome;
overlap copies must not inflate the number successfully imported. Small flora,
interiors and other reported omissions remain open until those checks resolve
them. See [the asset catalogue plan](ASSET_CATALOGUE_AND_GALLERY.md) and
[roadmap](ROADMAP.md).

### Dev4 extra: More mushrooms!

An [optional small-mushroom conversion path](SMALL_MUSHROOMS.md) now preserves
original Luminous Russula placement and container metadata. A bounded dev4
diagnostic converted **6 original placements from 3 source models** through the
actual geometry exporter and region mesh overlay. Existing source identity,
transforms, container flags/items and scripts remain in the receipts. All six
use `mesh_pending_interaction`; none became decorative sprites.

The geometry sample uses a synthetic retained base and remains diagnostic.
The original 28 converter checks passed, including old flora behavior and
rejection of partial diagnostic input by full-world assembly. The later dev4
source candidate adds the requested default: **interact, transfer the original
contents, then remove the mushroom from view**. Twelve focused Docker checks and
m68k object compilation passed for the original-content catalogue, transactional
pickup, inventory-capacity failures, saved state and existing scene/scenery
behavior. Original leveled contents retain their chance-none and selection rules;
the first activation's roll is retained across failed transfer retries.

This changes the source implementation status, not the released asset counts:
**0 new mushroom placements are in a delivered playtest, and 0 have native
harvesting acceptance.** Native appearance, actual-region installation and pickup
remain pending. The initial implementation has no respawn; source Respawn flags
are retained for a later cell-reset policy. The original item pickup cue is selected and source-tested; native audible
acceptance is pending. A classic container interface is deferred. The new flora category
still requires an explicit conversion flag/policy. This addition does not close
the reported rock-surface rendering regression.

### Dev4 hand catalogue diagnostic

A separate diagnostic generated **20 race/sex model pairs (40 MDL files)**,
plus one selection catalogue and one torch-emitter sidecar. All **42 files** were
read back from the diagnostic image with matching hashes. These are generated
artifacts and presentation combinations, not a count of unique original meshes.

The bounded native check observed six Nord punches and torch on/off, plus actual
Argonian model selection during demo playback. Complete demo EOF handling was
also checked. Live beast-race punch/torch behavior, punch framing/self-occlusion,
every race/sex combination and physical target cost remain open. This diagnostic
does not switch the production default or modify any sealed dev3 package. See
[first-person hands](FIRST_PERSON_HANDS.md) for implementation scope.

## Keeping this report current

Update this report whenever a build changes asset coverage, a missing asset is
reported or resolved, conversion fails or recovers, packaging differs from its
conversion report, or runtime testing changes an acceptance result. Record the
date, source scope, build identity and reason for each changed count. Keep
missing input, failed conversion, missing packaged output and unwired/incorrect
runtime use separate. Preserve unresolved entries instead of counting them as
complete.

Before a development handoff or release, reconcile this report with the build's
category summaries and verified image readback. State unavailable evidence as
unknown; do not infer zero or carry acceptance from a different build. Retain
dated evidence for previous snapshots rather than changing sealed artifacts.

The [asset progress helper](ASSET_PROGRESS.md) generates the path inventory and
media/readback comparison. Converter-specific provenance supplies the other
tables. Original assets, full private inventories and machine-specific paths
are not part of this public report.

### Dev4 mushroom cue and preview update

The owner approved the **static converted-mesh preview** (“mushrooms look great!”).
That feedback applies to the preview image only; native in-game appearance remains
untested. The selected pickup cue has one present source file, one converted
output and zero conversion failures. Its source/runtime fixture passed, but no
new package contains the cue and no native audible pickup has been accepted.

The original-map mushroom placements are retained as requested. This update
claims no newly packaged placements or native placement acceptance. The requested
crosshair label using the mushroom name and “(E: Pick)” is implemented and
fixture-tested in the dev4 source; native interaction acceptance is pending.

### Dev4 global mushroom census and persistent state

A base-master census now establishes **2,083 original placements** in the
supported numeric small-mushroom family: **934 exterior and 1,149 interior**,
across **8 models**. This denominator covers Luminous Russula and Violet
Coprinus, not every mushroom species or expansion load order. It does not
increase the six diagnostic placements already converted or establish native
acceptance. Eight additional placed activators on two other mushroom-like
models remain outside the supported taxonomy and interaction scope.

The [dedicated harvest store](HARVEST-STATE.md) is integrated in unsealed dev4
source: 4,096 catalogue-bound placement facts, independent of quest/global slots,
with persistent encounter rolls, picked/empty state and atomic inventory grants.
The deduplicated Docker source checks passed 94 tests; six Amiga target objects
compiled. The real six-placement catalogue indexes into all 2,083 source
identities. Native pickup/save acceptance remains pending.

Whole-world map admission is still open. The current runtime limit is 24 plants
per loaded map; an origin-only census found up to 75 in one coverage region,
before considering intersecting mesh bounds. The map capacity and geometry,
collision, memory and frame-cost gates therefore need further work. These are
source findings, not a claim that global mushrooms have shipped.

### Dev4 actual-map mushroom candidate

The same six original placements now have candidate overlays on nine real
maps, producing 54 resident copies with shared original identities. The 19
changed/new payload files comprise nine maps, nine AWH3 catalogues and one
pickup cue; this is not 54 unique mushrooms. All nine target heap estimates
pass the unchanged budget and reserves; the worst estimate leaves 1,908,464
bytes clearance. Actual native peak use remains unmeasured.

The converter's shared-seam correction passed 28 focused Docker checks, including
an old-control failure. Five picked and one original empty result survive eight
map handoffs and nine save roundtrips in the real state/codec fixture without
duplicate grants. Native appearance, E: Pick, occlusion, audible cue and save/load
acceptance are still pending. Delivered new placements and native-accepted
harvest placements remain zero at this checkpoint.

### Reconciled dev4 media payload

Fresh source-byte verification passed for all 7,199 recorded included media
sources. The reconciled staging directory has 7,202 files /394,812,125 bytes,
including catalogues and the retained higher-resolution story intro. The intro
output and its original-source digest match the earlier conversion receipt.
There are still 6,447 voices, 717 effects, 18 music tracks and 17 videos, with
zero missing converted outputs and nine unresolved original audio references.
This is a staged payload, not a completed image or game-event playback result.
The guest catalogue retains the earlier lookup schema; detailed ordered source
record provenance remains a separate development reference.

Normal-travel mushroom acceptance also needs town maps: all six sample source
positions select the Seyda Neen town core before the general world directory.
The nine world-map overlays alone therefore do not establish normal-travel
coverage. Matching town overlays are being prepared; native-accepted and
delivered new harvest placements remain zero at this checkpoint.

### Dev4 town harvest admission and Caius house clutter

The six diagnostic mushrooms now also have 32 candidate town/intro-map overlays,
with 174 resident copies. Their original identities are shared with the earlier
world-map copies. The town candidate is **not admitted**: intro_docks newly
exceeds its modeled memory allowance by 87,328 bytes, and inherited town
allowance deficits also grow. Source state/codec fixtures do not override this
limit. Shared external mushroom models are being investigated to reduce actual
geometry memory; proximity hiding alone does not release embedded BSP data.
No additional harvested placement has shipped or received native acceptance.

A cached source census for Caius Cosades' house contains 57 placed references
and 42 distinct nonempty model paths, including editor/light models. This is a
source inventory, not a converted/visible-object count. The registered room's
geometry-selection policy defers small items: its four ordinary bottle
placements, skooma pipe and loose moon sugar therefore need explicit conversion
coverage. The cache has no placed skooma potion record; container inventories
were not part of this inspection. Preserve source object types and placements
rather than inferring potion contents from a bottle model. These are open
interior-content tasks for "Just an Old Man with a Skooma Problem".
