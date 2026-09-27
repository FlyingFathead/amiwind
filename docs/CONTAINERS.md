# Town containers and inventory plan

Planning status, 27 September 2026, after checkpoint-014. Native containers and
player inventory are not implemented. The current scenery pass selects STAT and
DOOR placements; including a CONT mesh alone would not implement its contents.

## Host mapping

Audit CONT base records and their placed CELL references within the agreed
[starting area](SEYDA_NEEN_SCOPE.md), including later interior destinations.
Keep a shared base definition separate from each placed container's identity.
Retain model, name, inventory entries/counts, capacity/flags and script links;
preserve placement metadata relevant to ownership, locks, traps and initial
state. Verify exact field semantics against owned records and primary reference
implementation before enabling a rule. Unsupported fields must be reported.

Resolve item IDs through an indexed item table, including their type, name,
weight and required presentation resources. Preserve leveled-list references
instead of pretending that the list ID is an ordinary item. Export provenance,
dependency hashes and missing-reference diagnostics. Original item data, text,
icons and meshes remain in the private converted output.

Do not infer that every visible barrel, sack or chest is interactive by its mesh
name. Use the record type and placement. Conversely, shared mesh identity must
not cause two containers to share mutable inventory.

## Small implementation stages

| Stage | Intended result | Acceptance gate |
| --- | --- | --- |
| Placement | Recognizable containers with appropriate collision and stable placed-reference IDs | No missing/duplicate placements or new blocked walking routes; source flags remain visible in the audit. |
| Basic interaction | Activate one supported container within reach/line of sight; readable item list, take/put/close | Correct quantities, no duplication/loss, no movement or attack input leaking through the panel. |
| Local state | Changes survive closing/reopening and exterior/interior round trips | Two instances of the same base remain independent; unloaded geometry does not reset contents. |
| Gameplay rules | Ownership, capacity, locks/traps, scripts, leveled contents and respawn behavior where supported | Match documented source behavior with focused fixtures; unsupported rules remain explicit. |
| Persistent saves | Player and container state survive quit/restart | Versioned state, consistent item counts and safe interrupted-write recovery. |

Start with a deliberately selected, audited simple container. Do not enable
general town looting before ownership/crime and script dependencies are understood.
Unsupported locked, trapped, scripted or unresolved containers should remain
noninteractive with clear prototype feedback. This is a temporary feature limit,
not an invented replacement for their original behavior.

Item transfers need one validated state change covering both inventories: check
item identity, quantity, available capacity and supported rules before committing.
Once leveled contents are supported, their resolved state must survive ordinary
area reloads; regeneration/respawn follows an explicit source-compatible policy.
Full equipment, barter, theft witnesses and quest reactions build on this layer.

## Memory, lookup tables and tests

Perform record resolution and dependency gathering on the host. Share immutable
base/item definitions; keep only nearby container headers, the open inventory
and needed text/icons resident. Store mutable changes by placed-reference ID.
Evaluate sparse deltas against bounded snapshots instead of assuming either is
always smaller. Disk storage is not permission for unbounded lookups per frame.

Measure open latency, lookup/cache reads, UI memory, state size and audio deadline
misses during interaction and scene transitions. Test identical-base instances,
partial stack transfers, zero/invalid quantities, capacity rejection, missing
item IDs, close/reopen and repeated scene round trips. Add save/restart and
interrupted-write tests when persistence exists. Public fixtures use fictional
items and records, never extracted game data.

## Refresh policy and safer behavior

The owner specifically requests sensible refresh/persistence. Ordinary scene
unload/re-entry is not a refresh trigger. Preserve taken/added items by placed
reference, including player storage, and resolve leveled contents once per
initialization/explicit reset event. Audit original flags, delays, scripts and
cell-reset eligibility before choosing compatibility semantics. Any safer-storage
or no-respawn alternative must be an explicit rule recorded in saves, rather than
silently changing source defaults. Tests must cover time jumps, unloaded cells,
re-entry, player-added items, quest containers and repeated save/load.

The private vicinity audit now inventories CONT references and retains ordered
base/reference fields; flag semantics are not yet implemented by that audit.
