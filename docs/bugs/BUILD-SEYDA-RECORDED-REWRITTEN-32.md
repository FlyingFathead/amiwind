# BUILD-SEYDA-RECORDED-REWRITTEN-32: Later image passes rewrite the recorded Seyda Neen maps, so the exception is not the recorded stage

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 8 October 2026, in v0.0.32-dev1 |
| Where | image step recorded Seyda Neen maps (tools/build_aga.py image) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.32-dev1 (last seen) |
| Severity | high: Image passes silently rewrote maps meant to ship byte for byte, including seyda.bsp. |
| Family | Seyda Neen recorded stage (`seyda-recorded`) |
| Playtest version | v0.0.32-dev1 |
| From commit | source and engine 978475d |
| CHIM engine version | none: legacy engine |

<!-- END GENERATED FACTS -->

## Status: 8 October 2026

Open: repaired in source (v0.0.32-final-blockers), not yet in a built image. High priority for
v0.0.32 final. Found in the v0.0.32-dev1 delivery and smoke test (FS-UAE, playtest profile).
Relates to [BUILD-SEYDA-REGEN-30](BUILD-SEYDA-REGEN-30.md).

## Symptom

Under the recorded-stage exception (BUILD-SEYDA-REGEN-30) the image step installs the recorded
v0.0.31 Seyda Neen maps, but the dev1 image's Seyda Neen maps are not byte-identical to v0.0.31.
In dev1, `seyda.bsp` has the same bytes as `sn029` (3,892,672 B) instead of v0.0.31's full town
(4,411,968 B), and `dbg tp seydaneen` now lands in sn029.

## Where

`tools/build_aga.py image`: the actor ground bake (`tools/actor_grounding.py bake_ground`) and the
town flora step, which copies the fallback region over `seyda.bsp`. In dev1 the exception itself was
a private wrapper around the builder, not a builder option.

## How it happened

Traced 8 October 2026 by comparing the 69 recorded files (identical to the v0.0.31 payload) with the
dev1 image readback and the dev1 image step's receipts:

- 64 of the 66 recorded region maps (sn000..sn063) differ from v0.0.31 in the entity lump only: the
  ground bake re-fitted one placement, Indrele Rathryon (reference 128961), whose copy appears in
  every Seyda Neen region, from z 18.20184 to 18.20856 (a 0.0067-unit change) and rewrote its ground
  keys. intro_docks and sncourt and both region tables are byte-identical.
- `seyda.bsp`: after the town flora step, `build_aga.py image` copies the fallback region named in
  `seyda-regions.json` (sn029) over `seyda.bsp`, as the builder's own region conversion also does.
  The private wrapper skipped the flora installation for Seyda Neen but not this copy, so the
  v0.0.31 complete town (4,411,968 bytes) was replaced by sn029 (3,892,672 bytes). This is the
  builder, not the wrapper.
- The exterior sky cleanup, the hidden-surface cull, the first-person hand stamp and the world map
  optimisation did NOT change the recorded maps: their receipts give the same input and output
  SHA-256 for all 67 Seyda Neen maps (the v0.0.31 maps were already processed).
- `dbg tp seydaneen` landing in sn029 is not caused by `seyda.bsp`: the engine takes the arrival
  region from `seyda-regions.txt` (byte-identical to v0.0.31), whose arrival point lies in sn029;
  `seyda.bsp` is used only when the region table is missing.

## Why it was not caught

The exception was checked as "recorded maps installed", not as "shipped maps byte-identical to the
recorded stage"; no from-scratch comparison of the Seyda Neen maps against v0.0.31 ran before dev1
was packaged.

## Reproduction

Compare `maps/seyda.bsp` and `maps/sn*.bsp` of the dev1 payload with v0.0.31 (sizes and SHA-256);
`dbg tp seydaneen` in FS-UAE.

## Repair

The exception is a builder option and is honoured byte for byte (`tools/recorded_stage.py`):

- `--seyda-recorded DIR` (`tools/build.py`, passed to `check_scene_actors.py` and
  `build_aga.py image`) checks `DIR/id1` against the pin `config/seyda-recorded-v0.0.31.json`
  (names, sizes, SHA-256) before any conversion, and `prepare_seyda_regions.convert_builder_scene`
  installs the recorded set instead of converting. The private wrapper is no longer needed.
- Later passes skip the recorded maps: the Seyda Neen town flora keeps the recorded maps and only
  installs the sprites they use, the fallback alias copy is not applied, and the actor annotation
  and ground bake exclude them (`exclude=`).
- `recorded_stage.check` runs after the image map passes, the sky preparation and exterior sky, the
  hidden-surface cull, the hand stamp, the world map optimisation and, last, on the final payload
  before the content fingerprint; any recorded file that differs from its recorded bytes stops the
  build and names the pass. The checks are listed in the receipt and in `build.json`
  (`recorded_stage`).
- The one named difference (owner decision, option A, 8 October 2026): `seyda.bsp` ships as the
  fallback region sn029, as the builder writes it, not as v0.0.31's complete town. Measured: the
  v0.0.32 release actor audit refuses the complete town's seven actor copies (failed contact, and
  the copies then differ from their owner regions), while the 66 recorded region maps with the
  sn029 alias pass with all 24 placements grounded. The alias is in the pin with its reason
  ([BUILD-SEYDA-REGEN-30](BUILD-SEYDA-REGEN-30.md)).

## Verification

- `tests/test_recorded_stage.py`: the pin is the v0.0.31 set with exactly one alias; the recorded
  folder must match the pin; install writes the recorded bytes and the alias; every check stops on
  a rewritten region map, on the complete town back in place of the alias and on a missing file;
  the real annotate and bake passes leave an excluded map byte-identical; static order in
  `build_aga.py`: a check after every map-writing pass and before the fingerprint, the alias copy
  only without the exception; the guided build passes the option to actor-contact and image only.
- Real data (Docker, 8 October 2026): the recorded folder from the owner's v0.0.31 image passes the
  pin; installed with the repository pin, all 69 files pass the check, `seyda.bsp` equals the
  recorded sn029, and the v0.0.32 actor audit passes (24 of 24 grounded).
- Pending: an image built with `--seyda-recorded` whose Seyda Neen maps match the pin, and the
  from-scratch comparison.

## Prevention

The builder itself checks every file under the exception against its recorded bytes after each
map pass and on the final payload, and the from-scratch comparison checks the shipped maps against
the pin.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Seyda Neen recorded stage (`seyda-recorded`). Recorded v0.0.31 maps are kept byte for byte; their heap headroom limits what can be added and the public builder cannot regenerate them. See [families](README.md#families).

- [BUILD-SEYDA-CONVERTED-NOT-STAGED-35](BUILD-SEYDA-CONVERTED-NOT-STAGED-35.md): A default CHIM build stopped at the image step's payload preflight: the Seyda Neen region maps are converted later in that step
- [BUILD-SEYDA-CULL-STABLE-32](BUILD-SEYDA-CULL-STABLE-32.md): From-scratch builds stop in Seyda Neen terrain culling (fragment not repeat-stable)
- [BUILD-SEYDA-PRIVATE-STAGES-31](BUILD-SEYDA-PRIVATE-STAGES-31.md): Repository builder cannot regenerate the shipped Seyda Neen maps
- [BUILD-SEYDA-REGEN-30](BUILD-SEYDA-REGEN-30.md): Public build cannot regenerate the Seyda Neen sub-cells
- [HARVEST-SEYDA-HEAP-REFUSED-32](HARVEST-SEYDA-HEAP-REFUSED-32.md): Seven Seyda Neen sub-cells lose harvest to the heap check, six of which had it in v0.0.31
- [HEAP-SEYDA-OVERLAP-32](HEAP-SEYDA-OVERLAP-32.md): Shipped Seyda Neen maps fail the current heap model (harvest and guard overlap allowance)
- [SEYDA-REGIONS-PIN-33](SEYDA-REGIONS-PIN-33.md): The recorded Seyda Neen region table differs from what the region layout writes, and its only copy was inside a build volume

<!-- END GENERATED CATEGORY -->
