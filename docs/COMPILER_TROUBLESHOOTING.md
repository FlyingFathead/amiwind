# Compiler troubleshooting options and evidence

Producer requirement, 3 October 2026: compiler configuration must provide explicit
options for troubleshooting. Diagnostic experiments are part of the development
pipeline, not undocumented manual edits to production defaults. This document
records the required contract; the full configuration interface is **not yet
implemented**. Existing tools and private controls below have different status.

## Required option groups

| Group | Options / questions | Current implementation status |
| --- | --- | --- |
| Visibility | Matched `fast` versus full VIS; exact decoded-row checks; codec baseline/candidate comparisons | Bounded builder uses fast VIS; isolated full-VIS control stopped/checkpointed on 3 October, with comparison incomplete and resumption unverified; new codec not implemented |
| Render cost | Matched position/view/build; requested and effective distance; frame time; tested/rejected/clipped/drawn geometry; separate fog pass from culling | Balmora owner observation remains unprofiled; counter collection/control required |
| Allocation | Per-map ordered peak/resident/temporary allocations, used/free, mandatory reserve and growth margin | Target-ABI estimator and final-payload gate implemented |
| Node roles | World-render reachability, inline point-collision reachability, shared nodes, avoidable duplicate representations | Node-role audit and loader representation change included in v0.0.27; host checks passed, target gameplay pending; zero face count alone is insufficient |
| Retention | Explain why terrain, visibility, textures, model parts and actors remain: view, crossing, collision/traces, simulation or dependency | Required future resource ledger; not complete |
| Loader paths | Loose BSP, pack-member offset, additional-HDF search route, streamed versus whole-file fallback | Source/host regressions exist; packaged target coverage pending |
| Scope | One map, selected cells, affected neighbors, dense views, teleport/restart, save loading | Normal bounded town layouts and complete static map gates passed for v0.0.27; complete target suite pending |
| Runtime telemetry | Outgoing/unload/BSP/actors/restore/first presentation/gameplay, cache events, zone fragmentation, external Fast/Chip blocks | Event-driven watcher implemented; target trace acceptance pending |
| Cache conditions | Cold and warm paths, bounded read-ahead mode and prefix size | Explicit comparative target experiments required |
| Negative cases | Truncated/malformed sections, incompatible region directories, index limits, stale engine/loader receipt | Focused host/build checks exist; extend with each new format/path |
| Visualization | Polycount density, original cells, subcells/coverage, margin colors and threshold exploration | Separate asset-free generator being validated against private local maps |

## Configuration and receipt rules

- Every option must have a documented default, supported values, scope and output
  artifact. Distinguish implemented switches from proposed controls.
- Capture exact effective settings, source/engine/compiler hashes, ABI, inputs,
  selected cells and output hashes. Keep both sides of a matched experiment.
- Change one factor first. Combined savings must be measured on the combined final
  payload; estimates from different candidates cannot simply be added together.
- A diagnostic profile must not silently lower the non-map reserve or safety
  margin, remove required assets, trim coverage, or bypass the release gate.
  Keep the current 3 MiB non-map reserve and 2 MiB safety floor explicit.
- A memory-margin slider in a visualization is a scenario display, not authority
  to alter compiler acceptance. Keep the actual receipt policy visible.
- Diagnostic results retain estimate/host/runtime status separately. Audit final
  prepared maps after regeneration/annotation, then test the exact packaged build
  through complete unload/load/restoration/presentation/gameplay cycles.
- Archive failures as well as passes. Record affected version, circumstances,
  reproduction, cause, corrective change, remaining limits and verified-fixed
  version. Mitigation is a bandage, not incident closure.

## Relevant implemented tools

See [heap watcher](HEAP_WATCHER.md), [memory allocation](MEMORY_ALLOCATION.md),
[bounded-world candidates](BOUNDED_WORLD_CANDIDATES.md), and the map estimator
`tools/check_world_map_heap.py`. `tools/adaptive_town_regions.py` accepts a
measured candidate evaluator and exposes fixed overlap, reserve, planning target,
minimum core and region-capacity parameters; it emits proposals, not an installed
or accepted town. Production compiler configuration integration remains required.
