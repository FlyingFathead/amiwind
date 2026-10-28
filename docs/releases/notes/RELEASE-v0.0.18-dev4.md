# v0.0.18-dev4 — menu startup and ship-exit corrections

This checkpoint fixes the next set of ship-playtest issues. It is still the ship
portion of character generation; dock/Census creation is unfinished.

## Changes

- Fade in the supplied AmiWind logo from black, then enter the main menu with
  the converted original title track. A scaled logo sits above the menu; the
  original transparent PNG is also at the top of README and in resources/media.
  New Game resets the previously chosen track 04 before starting Jiub's scene.
  Title identity comes from the conversion manifest, not a hard-coded file index.
  Title playback loops without entering the exploration shuffle. Pause/Options
  retain their current music; returning to Main Menu selects the title again.
- Optional New Game movie conversion and streamed native playback: 160×100,
  10 fps, a movie palette, mono narration and Esc to skip. The ship music begins
  afterward. Missing video starts directly in the ship. See INTRO_VIDEO.md.
- Use actual transformed hatch bounds for activation, with world occlusion and
  bounded reach. E activates the door and queues the destination map. The target
  prompt lives below the world view. Audit 41 original town/interior door links;
  enable only the two ship links whose maps are converted. See DOOR_MAPPING.md.
- Ship actor bodies now block the player. The escort pauses while the player
  occupies the route, retaining its destination, then resumes when clear.
  General town collision, combat and crime are not included.
- `aw_showdisk 0` is the default. `aw_showdisk 1` enables the old disk-activity
  marker for diagnostics. The separate RAM/cache indicator remains off.
- Actor file/staging buffers no longer consume cache space at the final cache
  allocation. Transient heap buffers are each capped at 512KiB with the legacy
  loading path retained when allocation is unavailable. The resident 9MiB heap,
  actor geometry, fonts, textures and 16MiB Fast RAM preset remain unchanged.
- Loading credits use three lines: By FlyingFathead; the repository URL;
  Special thanks to: ChaosWhisperer.

## Source music finding

The owned base master's CharGen scripts contain no music-change commands. The
confirmed title file is `Music/Special/morrowind title.mp3`. Track 04 is the
established AmiWind choice, `Music/Explore/mx_explore_3.mp3`; it is not claimed as
proof of a fixed original ship/deck/Census soundtrack sequence. The original
engine's exact cue timing remains unverified. No speculative scene-change tracks
have been added.

## Validation

177 host tests pass. The 68040/FPU native build succeeds, and every file in the
final 128 MiB HDF is independently read back and hashed. Both hatch directions
passed native E activation in ordinary walking mode after diagnostic placement.
The actor-cache comparison and movie/menu captures are included in the private
checkpoint. Complete manual escort traversal and physical-hardware throughput
remain separate playtest gates. See the handoff and implementation journal.

## Packages and publication

The full public source is the recovery copy. The public incremental targets
exactly v0.0.18-dev3 and includes baseline hashes/deletions in its receipt.
The private playable contains owned game/ROM assets, emulator presets and
conversion/test evidence. Keep it private. The owner handles commits, tags,
pushes and releases; no git or gh commands are executed during development.
