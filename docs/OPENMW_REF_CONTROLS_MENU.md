# First-person hands and menu reference

Checkpoint-014 provides an independent prototype of the requested controls.
No OpenMW implementation or Morrowind interface artwork is copied into source.

| Input | Implemented behavior |
| --- | --- |
| F | Toggle Nord male unarmed draw/sheath |
| Mouse1 | Start one visual punch when drawn; release before another |
| Escape in game | Open/close the menu |
| Escape in console | Close console |
| Arrows/Enter or mouse in menu | Choose Return or confirmed Exit |

New Game, Save, Load and Options are visible but disabled. Exit confirmation
starts on Cancel. Opening/closing the menu clears held movement/attack inputs
and preserves mouse-look. The local scene pauses while the menu is open; music
continues. This is not yet a save system or the planned bottom-up dialogue UI.
After confirmed Exit, wait for writes and type `amiwind` at the DOS prompt.

The host reads the owned first-person skeleton, Nord body records and authored
text-key clip ranges. The Nord hand record references a shared Imperial mesh;
we follow that record, rather than inventing a separate hand asset. Wrists and
arms use the available Nord body parts. The initial bake is 28 sampled poses:
8 idle, 6 draw, 4 lower and 10 punch; 311 triangles, 933 packed vertices and a
512 x 256 skin. Appearance and motion are deliberately coarse at this stage.

The hidden/draw/idle/punch/lower state machine uses the authored clip durations.
There is no punch collision, stamina, damage, charge strength or hit reaction.
Clothing/equipment on the first-person arms and other races remain future work.
All generated models, skins and reports stay outside public source.

Behavior references, pinned OpenMW revision
`46bd4599203ee52ffc0f3e8edb3fc159a0303a49`:

- [Default bindings](https://github.com/OpenMW/openmw/blob/46bd4599203ee52ffc0f3e8edb3fc159a0303a49/apps/openmw/mwinput/bindingsmanager.cpp)
- [Main menu availability and confirmation](https://github.com/OpenMW/openmw/blob/46bd4599203ee52ffc0f3e8edb3fc159a0303a49/apps/openmw/mwgui/mainmenu.cpp)

AmiWind's implementations and artwork for this menu are independent. The
readable dialogue font and Morrowind-inspired dialogue panel remain on ROADMAP.md.
