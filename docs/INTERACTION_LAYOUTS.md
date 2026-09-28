# Interaction layouts

## npc_interaction_layout_template_001

Owner-selected default, 28 September 2026.

| Element | Rendering |
| --- | --- |
| Position | Right-aligned, immediately below the 3D viewport in the reserved lower strip |
| First line | NPC display name, e.g. Fargoth; small 12 px Morrowind font |
| Second line | `(Talk: E)`; current console font (tiny 4x6 default, normal 8x8 selectable) |
| Surround | No panel or new border; preserve health bars and coordinate strip |
| Availability | Aim, reach, line of sight and implemented current action must agree with E |
| UI priority | Hide while interaction is locked or a reader/character/menu interface owns input; subtitles draw over the hint |

Changing a menu font size does not enlarge the NPC-name hint. Reading's black
ink palette must not leak into this gold-on-dark name. Restore font/ink state
after drawing. Keep both existing console font modes and all UI font assets.
Existing supported objects provisionally reuse this placement (Read, Open,
Take ring, Locked, Empty). The owner considers wider reuse for Take/Steal/etc.
a possibility, not a finalized object UI decision. Do not advertise generic loot/dialogue
features before they exist. Current native NPC dialogue remains a prototype.


## Object interaction candidate

Keep the name/action two-line layout as an option for readable, collectible and
owned objects. Do not label Take as Steal without source ownership, faction,
permission and crime handling. Revisit with container/inventory UI; preserve the
NPC template as the settled default while object presentation remains provisional.
