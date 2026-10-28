# The Halloween scene

_Last updated with AmiWind v0.0.54-dev1 (27 October 2026)._

For Halloween 2026 the animation stage gets a beat: the game's own skeletons, the dancers of Desele's House of
Earthly Delights in Suran and Dagoth Ur himself dance on a roof in Balmora, filmed by a small camera director. It is
a MiniWind scene, a test scene and a benchmark at once: every move is a group of the shared animation tables played
by name, nothing baked, so the scene shows the skeletal actors, a creature on the humanoid table and a creature on a
table of its own, and `dbg halloween bench` turns it into the standard frame-rate test.

## Building it

Every full-world build carries the cast, so `dbg halloween` and `aw bench halloween` work in the release images (since
v0.0.54). The cast is about 1 MB on the drive, and the game loads it only when the scene starts: it takes no memory
until then. `--halloween-cast off` leaves it out of a full-world image; that image then says it has no cast. The
cast is packed by the image step alone, so turning it on or off rebuilds the image and nothing else. A full build
carries no song: the custom OST slot (below) stays empty unless you fill it.

```
tools/build.py --miniwind-halloween [--custom-ost FILE] ...
```

`--miniwind-halloween` is the MiniWind preset ([MINIWIND.md](MINIWIND.md)): Balmora's exterior, as the animation
stage ([ANIMKIT.md](ANIMKIT.md)), with the scene's cast in the image (`--halloween`). On arrival it runs
`dbg halloween`. Other MiniWind builds take the cast only with `--halloween`. The cast is made from your own game
data, as everything else in the image:

| Cast member | Model | Animation table |
| --- | --- | --- |
| Skeleton (every skeleton record of the game uses one mesh, `r/skeleton.nif`) | one skeletal model | the shared humanoid table (`progs/humanoid.awsk`) |
| Desele's three dancers (Marelle, Caminda and Runa) | skeletal residents | the female view of the humanoid table |
| Dagoth Ur (`r/dagothr.nif`) | one skeletal model, his mask kept whole (457 of his 2,254 triangles for now: a larger model's skin does not fit the skeletal model's limits yet) | his own table (`progs/dagothur.awsk`: 22 groups, 29 bones, 70 KB), built from his own keyframes |

The first check before any of it: the skeleton creature's rig against the humanoid table. The skeleton is a two-legged
creature, so the original game plays the shared humanoid keyframes on it; every bone the table keeps is in its rig and
none of its bones is missing from the humanoid skeleton, so it rides the shared table and can play every humanoid
group (spellcasting, the hits, the deaths, swimming, sneaking). Dagoth Ur's rig is the biped too, with more finger
and toe bones and only his own groups (idles, `idlespell`, `spellcast`, three attacks, two hits, knockdown, knockout,
death, walk, run, turns), so he gets a small table of his own, made by the same tools. A cast member the builder
cannot make is left out with its reason in `halloween-cast.json`; without Dagoth Ur the scene plays the skeletons-only
version.

### Your own soundtrack: the custom OST slot

Any build can carry one track of your own. Point `--custom-ost FILE` (or the machine setting `AMIWIND_CUSTOM_OST`)
at any audio or video file you own; the builder takes its audio track with ffmpeg, converts it into the game's music
stream (11,015 Hz, stereo, signed 8-bit, the same path as the game's own music) and puts it into your image as the
custom track. Only the image step packs it, so it never makes the builder redo any other stage. In the game the
custom OST player plays it: `aw music custom play` plays your track alone while the game's own playlist waits, and
`aw music custom stop` gives the playlist back. The Halloween scene and `aw bench halloween` use the same player:
your track starts with the first beat, and with the cast in the image the builder also measures its tempo so the
dance follows your music's beat. Without a custom track the scene is silent: the game's own music never plays in it.
The file goes into your image only; the repository carries no audio, only the option, the conversion and the
scene's default beat (132 beats a minute). (`--halloween-soundtrack` is the same option under its first name.)

## In the game

| Command | What it does |
| --- | --- |
| `dbg halloween` | The Dagoth Ur version: he stands in the centre, the dancers around him (two on each side), the skeletons behind and beside them (three on each side). |
| `dbg halloween skeletons` | The skeletons alone, two rows of four, dancing in unison. |
| `dbg halloweentest [skeletons]` | The same with the FPS counter on. |
| `dbg halloween fps on` / `off` | The FPS counter, small, in the bottom-left corner (off in the show). |
| `dbg halloween camera wide` / `director` | Lock the camera to the wide shot, or give it back to the director. |
| `aw bench halloween [skeletons]` (also `aw halloweenbench`, `dbg halloween bench`) | The standard benchmark (below). |
| `dbg halloween status` | The actors, the time, the beat and the shot. |
| `dbg halloween stop` | Ends the scene; the cast leaves. |

The show opens on a black screen: for 5 seconds, in silence, a box in the exact centre says, on two centred lines,
HAPPY HALLOWEEN and FROM AMIWIND (the game's own message box, only as large as its two lines). Then the rooftop
appears, the dance begins and your soundtrack, when the image has one, starts with the first beat. Most tracks begin
with a moment of silence: the builder measures it on the converted track (10 ms windows under -40 dB) and writes it
into the cast file, and the scene starts your track that much earlier, under the greeting, together with the player's
own start delay (0.16 seconds, measured in the emulator), so the first beat is heard as the
rooftop appears. The greeting never
draws over the scene. Every readout keeps to a corner: the FPS counter, when it is on, sits small in the bottom-left
corner. Photo mode hides the HUD while the scene runs, with its own notice box and hints switched off
(`dbg photomode ui off` does that for photo mode at any time; the scene puts the setting back when it ends). The
residents' own voice lines around the roof keep playing with the music.

The cast stands on the stage floor in front of you, on one line as the animation stage's cast does: the floor
under the centre's spot is found first, then every dancer and skeleton takes the free spot nearest its place whose
floor is that same level (never another roof level, the air or a wall), and is settled on it as the game settles its
residents. The console line at the start says how many feet the ground check found on the stage floor. Stand on the
stage roof and face the open side.

Every cast move sounds as it plays: when an actor's spellcast group reaches its release keys (the table's own text
keys, where the hand lets go), the game's spell cast sound plays, one school after another, the bolt sound for a cast
on target. The sounds are converted from your game data when the image is built (`sound/aw/cast/`). The animation
stage's casts sound the same way.

## The choreography

A beat clock picks the moves. Each role dances its own line of steps, every step a whole number of beats, so the
actors of a role move together and every move starts on a beat; a move longer than a beat or two (a cast, a fall)
takes its own length at about its own pace, rounded up to whole pairs of beats.

- The skeletons: the hits in quick succession (`hit2` to `hit5`), the swimming side-steps (`swimwalkleft`,
  `swimwalkright`) one beat each, spellcasting, knockdown and knockout with the getting up, the deaths played forward
  and then backwards so they rise again, sneaks and walks; an idle only as a two-beat rest between moves.
- The dancers do most of the dancing around Dagoth Ur: the spellcasting postures as dance arms, the hits, the side-steps,
  sneaks and walks. Around him the left side mirrors the right.
- Dagoth Ur poses more than he dances: his spellcasting on the strong beats, `idlespell` and his idles between, a
  spell turn to each side and one great swing of his arm.

The steps are our own, made only of the game's animation groups by their Morrowind names; the lines are in
`engine/aga/src/aw_halloween_rules.c`.

## The camera

A small director changes the shot every four bars (16 beats), always on a bar boundary, and moves the camera with
eased motion (slow in, slow out) within a shot:

1. the wide establishing shot: the whole cast, head to feet with a margin, looking down at its middle (also the very
   first frame after the greeting);
2. a slow dolly-in from wider than that to the wide framing;
3. a tracking shot sliding across the front of the line;
4. a crane shot rising from low to high over the group;
5. an orbit across the front, around the centre;
6. a close-up on one dancer, head to feet, picked when the shot begins from the ones in a big move (a cast, a fall).

Every shot keeps its subject whole: the camera stays at least as far away as the cast's (or the one dancer's) box
needs to fit the field of view. When a wall or roof stands between the eye and the cast, the eye first rises over
it, and only then comes in front of it, as the orbit camera does ([camera marks](CAMERA_MARKS.md)).
`dbg halloween camera wide` keeps the wide shot only.

## The benchmark

`aw bench halloween` (or `aw bench halloween skeletons`; `aw halloweenbench` and `dbg halloween bench` are the same;
`aw bench NAME` takes more benchmark scenes later) plays the scene as a benchmark: no greeting and no music, the FPS
counter on, and 600 frames with the scene clock stepping a tenth of a second each frame (60 seconds of the dance and
every camera shot), so every run on every machine draws exactly the same frames, as Quake's timedemo plays a fixed
recording. At the end the console shows one line to copy: the average, minimum and 1 % low frame rates, the frame
count, the seconds, the Fast RAM, the CPU and the build. How to send it: [REAL_HARDWARE.md](REAL_HARDWARE.md).
The residents of Balmora around the roof keep their own idle timing, so the picture away from the stage can differ
a little between runs.

## Known limits

- The cast stands where it is put: no footwork across the roof yet (the walks and side-steps play in place, as the
  shared table holds the moving groups in place).
- No spell effects on the casts yet; the cast animations alone.
- The scene starts the beat when it starts; it does not look for the first downbeat of a soundtrack.
- The scene and the benchmark need an image with the cast: every full-world build from v0.0.54 on (unless built with
  `--halloween-cast off`) and `--miniwind-halloween`. The v0.0.53 release images do not carry it, so in them
  `dbg halloween` and `aw bench halloween` say the image has no cast.
- The scene plays in front of you, where you stand. The Halloween MiniWind build starts you on the stage roof in
  Balmora; in a full image, stand on open, level ground and face the open side. For numbers to compare with other
  machines, run the benchmark at the same place.
