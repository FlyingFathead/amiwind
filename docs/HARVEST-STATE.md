# Persistent harvest state

The v0.0.29-dev4 source candidate gives harvestable placements a dedicated
state store. It holds up to **4,096 original placement facts**, separately from
the 32-entry global/quest tables. Inventory still has its existing 32 item-type
limit; this change does not implement a complete inventory interface.

## Identity across maps

AWH3 catalogues assign one dense index to each supported source placement.
The converter derives the complete index from the source census, independently
of which map is being converted. Original master, cell and reference identity
are retained in each full placement key. A SHA-256 catalogue identifier binds
the sorted keys to their indices. Multiple loading copies of one placement use
the same index. Incompatible catalogues fail closed.

The current census scope is the base master's numeric small-mushroom model
family, including reserved interior identities. Reserving an index does not
convert a model, add it to a map, or enable unsupported interior/script/ownership
semantics. This is not a claim of all-species or expansion coverage.

Each encountered placement retains its random seed and encounter level. Empty
results are absent before drawing or highlighting. A successful pickup grants
the complete resolved contents and then keeps the placement hidden across map
changes and compatible saves. No respawn is implemented in this first stage.
If the inventory cannot accept every item, it grants nothing and keeps the
plant available with the original roll. `dbg shroomtracker` counts collected
placements; empty results and repeated visits do not increase it.

## Saves and compatibility

AWS3 serializes only encountered placement facts as ascending index/value
pairs, with the catalogue identifier and bounded count. The save limit is
64 KiB. The runtime uses 16 KiB for the dense fact array, plus 36 bytes for its
count and identifier, per state snapshot. Pickup transaction scratch copies
only the inventory table. Save-file I/O buffers are allocated off the Amiga
task stack and released after use; allocation failure retains earlier saves.

AWS1 and AWS2 remain decodable. States with no indexed harvest catalogue still
encode as AWS2. Exact legacy placement keys migrate on encounter, freeing their
old global slots without rerolling or double-counting. Mixed legacy and indexed
map catalogues are rejected after an indexed state is bound. Existing build
content-fingerprint compatibility checks still apply: this is not a promise
that saves can be moved between different converted asset sets.

The source tests cover 4,096 placements, repeated map copies, a fully occupied
quest/global table, complete inventory-transfer failure, empty/picked state,
exact-key migration, maximum serialized state and corrupt-save rejection.
Actual map conversion, emulator pickup/save acceptance and measured native
memory headroom remain separate release gates.

## Proximity and persistent existence: next optimization

Keep original placement state separate from temporary runtime presence. The
saved facts already say whether the original mushroom has been picked or rolled
empty. Those facts survive leaving a cell, changing sub-cells and loading a
compatible save. Distance must never reset that state or roll new contents.

The proposed next step is a bounded nearby set for visible mushroom models and
interaction checks. Use different enter/leave distances to avoid repeated
activation at one boundary; preserve original coordinates and a single identity
across overlapping map copies. Save while a mushroom is inactive, then return,
without respawn, a duplicate grant or a stale targeting label.

Current mushrooms are embedded BSP submodels. Merely hiding one or skipping its
interaction does not release its geometry from the loaded map. Actual memory
savings require changing representation or admission, such as shared external
models with bounded residency. That remains an investigation, not an implemented
proximity loader. Check camera height, view range, collision, target occlusion,
frame cost and model/heap limits before accepting a smaller nearby set. A
proximity cutoff must not disguise a map-capacity failure or break normal travel.
