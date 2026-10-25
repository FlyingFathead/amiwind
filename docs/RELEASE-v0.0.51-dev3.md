# AmiWind v0.0.51-dev3 (in development)

Development snapshot, 25 October 2026, in development. Running on CHIM Engine v0.2.2. Previous release:
[v0.0.50](RELEASE-v0.0.50.md). Previous snapshot: [v0.0.51-dev2](RELEASE-v0.0.51-dev2.md).

## New since v0.0.51-dev2

- **Interiors get their light from above.** Every interior cell of the game has a "sunlight" colour that the
  original lights the room with, as one directional light from a fixed direction; our rooms were baked without it,
  only with their ambient and lamps, so rooms lit mostly by it came out dim, and Akulakhan's Chamber almost black.
  Every interior is baked again with it ([INTERIOR-SUNLIGHT-UNBAKED-51](bugs/INTERIOR-SUNLIGHT-UNBAKED-51.md)). The prison ship keeps the light it
  was judged with. The interior brightness default goes back to 1.0, the original light: the 1.2 default made up for
  the missing sunlight. Options > Video > Graphics and `dbg luma interior` still set 1.0 to 1.5, and a saved setting
  keeps its value ([interior lighting](INTERIOR_LIGHTING.md)).
- **The load meter.** The "Loading audio" console line names the step of the load where the music waited longest,
  and leaves out the intro movie, which pauses the music on purpose (the first load's long "gap" in the earlier
  snapshots was the movie) ([AUDIO-LOAD-29](bugs/AUDIO-LOAD-29.md)).
- **Fewer console lines.** The fires of Seyda Neen no longer print "'aw_flame_light' is not a field" on every load.
- **Builds.** Stages that read nothing new are no longer rebuilt because of the file reads of their own cache keys.

## Known in this build

- Everything in [v0.0.51-dev2's known items](RELEASE-v0.0.51-dev2.md#known-in-this-build) still applies.
- Everything else is in the [bug register](BUGS.md).
