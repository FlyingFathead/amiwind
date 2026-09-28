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

`tools/prepare_doors.py` audits 41 teleport placements around Seyda Neen and its
named interiors in the supplied base master. The private `door-conversion.json`
preserves IDs, transforms, destinations and sound/script names. `scene-doors.txt`
is bounded AWD2 data: source/target map, transformed activation bounds, arrival,
yaw and a CP1252 destination label. Dev5 exposes 22 entrances in the two resident
scenes: 21 exterior references and the interior ship hatch. Two have working
transitions. Aim at a door for its name and E prompt; activation of an unavailable
destination displays exactly “Interior not found.” and preserves location/state.
The original full cell name remains in the catalogue; the repeated “Seyda Neen,”
prefix is omitted from the narrow on-screen label. A target `-` means unavailable.
The converter also writes private interior-reference.json/md for 14 source cells,
including object transforms, lights, actors and per-reference destination points.
These are conversion references, not 14 playable interiors.

The prison hatch is `chargen_shipdoor`, an overhead teleport door. Activate its
visible surface to load the exterior deck. It does not require a physically
swinging lid. The exterior hatch is the separate `CharGen_ship_trapdoor`
reference. Aiming uses the transformed model bounds with half-unit padding,
a 56-unit reach and a world occlusion trace. AWD1 and the old single-origin format remain
readable for older conversion bundles. Both supported directions preserve current
health/hand state and queue at most one map load per activation.

This remains one active BSP at a time. Door mapping does not implement all town
interiors, lock/key rules, ownership, character-creation gates or persistent
reference state. Original transition sound IDs are catalogued but not yet played.

Reference: [OpenMW, Doors and Connecting Cells](https://openmw.readthedocs.io/en/latest/reference/modding/doors-and-teleports.html)
corroborates the interior-name/exterior-coordinate distinction. The owned master
is the source of the specific prison/town links.
