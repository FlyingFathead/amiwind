# AmiWind v0.0.30-dev3 - The Temple

Development build. It fixes the long-standing Balmora Temple geometry and the
same converter fault in several other interiors. Everything else is unchanged
from v0.0.29.

## Fixed: walls turned the wrong way in some interiors

Some Morrowind meshes carry a rotation on their NIF root node. The game ignores
that rotation (it keeps the root's position offset and scale). The scene
converter applied it, so those meshes were turned around their own origin.
Most meshes have no root rotation and were never affected, which is why the
fault only showed in a few places.

- **Balmora Temple:** the lower-level Velothi wall, room and corner pieces were
  a quarter turn off. That caused missing walls, walls seen edge-on as thin
  slits, black see-through holes and objects that seemed to float. The rebuilt
  Temple matches the original layout at the reported entrance views.
  ([BALMORA-TEMPLE-GEOMETRY-29](bugs/BALMORA-TEMPLE-GEOMETRY-29.md))
- **Tharys Ancestral Tomb:** the same kit pieces left see-through holes; the
  walls are solid again.
- **Arrille's Tradehouse, Eldafire's House, Draren Thiralas' House, Terurise
  Girvayne's House, Census and Excise Office:** the Nord fireplace faced away
  from the room; it faces the room again. A few objects the converter had
  dropped as buried inside the misplaced fireplace are back (a lantern hook,
  ferns and grass).
  ([CONVERTER-ROOT-ROTATION-30](bugs/CONVERTER-ROOT-ROTATION-30.md))

Each rebuilt map was checked against the previous conversion: every mesh
without a root rotation is unchanged, textures are unchanged, and only the
listed pieces moved. A regression test covers the converter rule.

## New tool

`tools/analyze_subcell_redundancy.py` measures how much geometry neighbouring
sub-cell maps duplicate and draws a cell map of polygon density with the cell
cores on top. See [sub-cell redundancy](SUBCELL_REDUNDANCY.md). Its first use
found that Seyda Neen's 64 sub-cells store each face about 24 times, which is
why cell crossings there pause longer than in Balmora or the open world. That
work continues; this build does not change cell loading.

## Still open

- One Balmora exterior placement (`furn_pathspear_03`) still has the root
  rotation; it uses a separate exterior pipeline and is not rebuilt yet.
- Walking and collision through every rebuilt interior, and playtest acceptance.
- Known issues from v0.0.29 remain, including WinUAE music crackle at Enter and
  race selection, the idle-to-punch hand transition, Seyda Neen cell-crossing
  pauses and memory limits. See the [tracker](BUGS.md).
