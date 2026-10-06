# Original door mapping

The converter reads base DOOR records and their placed CELL references from the
owner's Morrowind.esm. A door's model/name/script and open/close sound IDs belong
to its base record. Each placement has its own reference number, transform,
scale and optional teleport destination. Do not infer a return link from a shared
base model: the other side is a separate placed reference.

| Source field | Meaning | AmiWind conversion |
| --- | --- | --- |
| DOOR NAME/MODL/FNAM | Base ID, model and displayed name | Retained in the private catalogue |
| DOOR SCRI/SNAM/ANAM | Script, opening sound, closing sound | Audited; general script/lock/audio handling still pending |
| CELL FRMR/DATA/XSCL | Placed ID, XYZ/rotation and scale | Stable audit identity and transformed mesh bounds |
| DODT | Destination XYZ and rotation | Quarter-scale coordinates and destination yaw |
| DNAM | Named interior destination | Empty/absent means an exterior world position |

Interior coordinates are local to that cell. Exterior positions are world
coordinates; AmiWind subtracts the current exterior origin before quarter scaling.
The destination is a feet position, converted to the standing body's origin and
checked against collision/floor geometry when the destination map loads.

`tools/prepare_doors.py` now resolves the configured area through
`config/seyda_area.json`. The private audit contains 43 teleport placements,
including Addamasartus and both Tradehouse entrances. `scene-doors.txt` stores
source/target map IDs, transformed activation bounds, arrival, yaw and the
original destination label. All configured destinations have converted maps.
An unsupported destination still displays “Interior not found.” and preserves
location/state. Lock/key rules and general door scripts remain unfinished.

The Tradehouse front-door round trip passed a native emulator check. All scenes
also loaded through the inspector. This is not exhaustive validation of all
43 links or the introductory quest route. Original arrival coordinates are
retained, then checked with the standing hull and floor search. The private
catalogue retains each placed reference, including separate basement doors.

The prison hatch is `chargen_shipdoor`, an overhead teleport door. Activate its
visible surface to load the exterior deck. It does not require a physically
swinging lid. The exterior hatch is the separate `CharGen_ship_trapdoor`
reference. Aiming uses the transformed model bounds with half-unit padding,
a 56-unit reach and a world occlusion trace. AWD1 and the old single-origin format remain
readable for older conversion bundles. Both supported directions preserve current
health/hand state and queue at most one map load per activation.

Hostile-pursuit, companion eligibility and original teleport-door rules are recorded in the planned [NPC cell-traversal requirements](NPC_CELL_TRAVERSAL.md); no cross-boundary NPC gameplay is claimed as shipped.

This remains one active BSP at a time. Door mapping does not implement general lock/key rules, ownership,
character-creation gates or persistent reference state. Original transition sound IDs are catalogued but not yet played.

Reference: [OpenMW, Doors and Connecting Cells](https://openmw.readthedocs.io/en/latest/reference/modding/doors-and-teleports.html)
corroborates the interior-name/exterior-coordinate distinction. The owned master
is the source of the specific prison/town links.
