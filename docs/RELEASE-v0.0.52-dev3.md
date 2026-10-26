# AmiWind v0.0.52-dev3 (in development)

Development snapshot, 26 October 2026, in development. Running on CHIM Engine v0.2.2. Previous snapshot:
[v0.0.52-dev2](RELEASE-v0.0.52-dev2.md); previous release: [v0.0.51](RELEASE-v0.0.51.md).

The third snapshot of "Skeletons Of Society, Vvardenfell Edition", with what the in-game check of dev2 found.

## New since v0.0.52-dev2

- **Akulakhan's Chamber on 32 MB, coming from a town.** On dev2 the chamber could not load on 32 MB after Balmora:
  the skeletal characters' memory (their animation tables and posed frames, kept for the whole session) still held
  1.6 MB of the Fast RAM the room grows into. Memory that can be made again is now given back first, through one list
  every large allocation consults (the room's growth, the CHIM cache banks), and the room's bank grows in 64 KiB
  steps instead of whole MiB: after Balmora the chamber takes 3,456 KiB and leaves 804 KiB of its zone free
  ([CHIM-ROOM-HEART-CHAMBER-LOAD-50](bugs/CHIM-ROOM-HEART-CHAMBER-LOAD-50.md)). The build's room check now counts the
  route through a town and the room's own actors, so a room that would not fit stops the build instead of the game.
- **Guards hold their torches at night again.** A skeletal guard who shows his torch holds it up with his left arm on
  the table's torch group ([SKEL-ITEM-TAGS-52](BUGS.md)).
- **Skeletal characters drawn only when on screen.** A posed character is culled by the box of the pose it stands
  in; at Balmora's arrival on a slow 68040 a frame is as fast as with baked characters
  ([SKEL-RUNTIME-COST-52](BUGS.md)).

## Known in this build

- Residents idle in place; they do not wander yet (v0.0.53).
- Some large interiors, in Vivec above all, are still loading in when you are already there
  ([CHIM-ROOM-POPIN-51](BUGS.md)).
- Doors of the region frames do not open after walking across a frame border until the next load
  ([DOOR-BANK-STREAMED-FRAME-51](BUGS.md)): the first fix of v0.0.53.
- Everything else is in the [bug register](BUGS.md).
