# Source-bound mushroom interiors

The opt-in `tools/prepare_harvest_room.py` prototype builds one original interior,
its external mushroom catalogue/models and original directed door-bank deltas.
It requires the owned standalone base master and assets. Generated game data and
source-reference receipts do not belong in the public repository.

`prepare_area.build_room` retains its previous behavior by default. The new
entry options request incoming interior doors, exact harvest exclusions, and
retention of every reference selected by the existing scenery policy. Other
containers, architecture, lights and selected dressing remain. Actors and small
loose items still follow the existing deferred-content policy; this converter
does not claim a complete original room simulation.

Harvest exclusions must match the master digest, exact interior name, original
reference number, CONT identity, model, position, rotation and scale. The loot
graph is checked before building. Unsupported ownership, scripts or contents
stop the build; they are not silently converted into free loot. The BSP digest
is recorded with the exclusion report and checked again before catalogue output.
The existing global master/cell/reference identities and saved pickup slots are
reused. Empty/picked behavior remains the compact runtime's responsibility.

Doors come from actual DOOR records and DODT placements in all source cells.
An interior-to-interior entrance works without an exterior entrance. No reverse
door is inferred from a matching destination name. Each source reference,
authored destination, yaw, transformed model bounds and metadata is retained.
Original lock/owner/trap/script fields remain a blocked routing case. NAM0 is
retained as a cell temporary-reference-section marker, rather than being mistaken
for lock state of the preceding door. This follows the primary
[OpenMW 0.48 CellRef reader](https://github.com/OpenMW/openmw/blob/openmw-0.48.0/components/esm3/cellref.cpp).

The map registry is **a proposal, not runtime registration**. Existing static IDs
0–59 and reserved terrain IDs60–8251 stay unchanged. New interiors append from
8252; adding another name never reorders earlier entries. Source-bound filenames
use `mi` plus12 hexadecimal digits, with collisions rejected. They fit the
current15-character door-map limit and30-character legacy catalogue filename
limit. Full original identity is retained separately; the filename is not a
replacement pickup-state key.

The current runtime still needs the appended map registry/save mapping and
terrain door-bank support. Emitted door banks are deltas: merge them with any
existing banks, validate every destination BSP and preserve original entries
before installation. A directory match does not prove traversable collision or
native reachability. Door-bank and BSP/model bytes must all enter the final
content fingerprint.

Every room needs exact target-ABI heap admission after complete dependency
staging. Charge all used mushroom models, loader scratch, dictionary/proxies,
allocator allowance and the unchanged engine/safety reserves. Do not credit
hidden/picked geometry as freed memory. A failed allowance remains a failed
candidate; conversion success is not permission to install it.

The first private room trial preserves119 selected scenery references and8
original mushrooms, using all8 original mushroom model variants. Its modeled
total is12,459,996 bytes, exceeding the11MiB allowance by925,660 bytes. The
largest allocations are faces, planes and texture mappings. No map, native
gameplay or broader interior coverage is accepted by that conversion result.
Lossless geometry deduplication is the next measured experiment; no reserve
waiver or content omission is proposed.

## Adopted approach for oversized interiors

Oversized interiors will be divided at natural room boundaries: doorways,
corridors and cave bends. Smaller interiors may remain whole when they fit.
This design is adopted; interior subdivision is not implemented by this
prototype. Lossless deduplication and the existing polygon/memory inspection
tools will inform where subdivision is necessary and which sections fit.

Sections must share one logical original interior identity for saves, quests,
NPCs and harvest facts. Residency is temporary and must not create new pickup
keys, reroll empty plants or resurrect picked plants. Crossing a section must
preserve camera direction, equipment, active voice and music. Use visibility and
collision overlap around natural boundaries rather than an arbitrary dense
grid that interrupts movement throughout a room. Appended physical map IDs and
their relation to the original logical cell need explicit save/routing tests
before any native acceptance or full interior build.
