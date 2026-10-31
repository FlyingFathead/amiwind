# AmiWind v0.0.57-dev1 (in development)

Development snapshot, 30 October 2026, in development. Running on CHIM Engine v0.2.2. Previous release:
[v0.0.56](RELEASE-v0.0.56.md).

The first snapshot of v0.0.57: shorter fog by default to win back frame time in the busiest places, lighter versions
of the heaviest models, and plainer public docs. The game needs 32 MB of Fast RAM, and the emulator presets of this
snapshot have it. What v0.0.56 brought is listed in its [notes](RELEASE-v0.0.56.md).

## New since v0.0.56

- **Fog at 300 by default.** The fog distance starts at 300 instead of 540, which brings back a good share of the
  frame rate in heavy places such as central Ald'ruhn; it can still be changed in the console. Fog can also be set
  per place, and large interiors now fade into fog at the draw distance and draw nothing past it.
- **Lighter heavy models.** The models that cost the most to draw go through the shared mesh optimizer, with a check
  that keeps the edges where their parts meet closed.
- **Plainer public text.** Bug pages and topic pages describe what was seen and decided in plain project words, and the
  gate now refuses assistant or model names anywhere in the tree and swearing in public text.
- **Toolkit world map**: copying works with a single selected cell; empty sea cells blend into the background; a new
  colour mode shows the faces placed per cell from the newest CHIM build, so the slowest places stand out; the map is
  fed from every delivered build.
- **Docs**: a section on running the game on a PiStorm-accelerated Amiga, and the plan for importing saves from the
  original game and from OpenMW into AmiWind's own save format (roadmap and save plan).

## Known in this build

- Creatures are placed in the world but stand still and do not attack on sight
  ([ACTOR-WANDER-AGGRO-52](../../bugs/ACTOR-WANDER-AGGRO-52.md)); the fix is in testing for the next snapshot.
  Flying creatures such as cliff racers stay on the ground (ACTOR-MOVING-RUNTIME-GROUND-48).
- Some rooms still load in after you arrive ([CHIM-ROOM-POPIN-51](../../bugs/CHIM-ROOM-POPIN-51.md)).
