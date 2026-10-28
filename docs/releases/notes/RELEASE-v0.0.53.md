# AmiWind v0.0.53: Super Freak Halloween Update

Released 27 October 2026. Running on CHIM Engine v0.2.2. Previous release: [v0.0.52](RELEASE-v0.0.52.md); development
snapshots [v0.0.53-dev1](RELEASE-v0.0.53-dev1.md), [v0.0.53-dev2](RELEASE-v0.0.53-dev2.md) and
[v0.0.53-dev3](RELEASE-v0.0.53-dev3.md).

The doors of the region frames work after a walk across a frame border, and every build now proves it: the engine's own
door code is run over all 1,102 exterior entrances of the base game. The four characters of the base game with a dance
of their own, Desele's dancers in Suran among them, dance it. A Halloween scene on the animation stage, with the game's
skeletons, the Suran dancers and Dagoth Ur dancing to a beat, is also the standard benchmark for real Amigas.

## What changed since v0.0.52

- **Doors after a walk across a frame border.** The engine read only the door table of the frame the game started in,
  so 830 of the 1,102 exterior entrances were dead once you had walked into their frame: no prompt, no use. It now reads
  the table of the frame you are in, and a script's Activate on a load door does the same
  ([DOOR-BANK-STREAMED-FRAME-51](../../bugs/DOOR-BANK-STREAMED-FRAME-51.md),
  [CHIM-REGION-DOORS-NO-PROMPT-42](../../bugs/CHIM-REGION-DOORS-NO-PROMPT-42.md)). Checked in game on the maintainer's five
  entrances (a Red Mountain cavern, two Velothi tombs, an Imperial guard tower, an Azura's Coast stronghold) and four
  more. The hinged doors were checked and needed no change; a test keeps them so.
- **The door check in every build.** The image step of a whole-world build runs the door audit (a checklist of every
  door, its entrance, its interior, the way back and its lock) and the engine's own door code compiled for the host
  over the finished image: for each of the 1,102 exterior entrances the crossing into its frame, the prompt, the use
  key and a script's Activate into the room, the way back out, and, for region-frame doors, the wall between the player
  and the door in the world's own collision. 1,102 of 1,102 work after a walk over a frame border (272 through the
  v0.0.52 scene code). The count of usable entrances is kept in the repository and may only go up; a build whose image
  uses fewer stops ([DOOR-ENTRANCE-AUDIT-51](../../BUGS.md)). `dbg door roulette [SEED]` loads one random room at its own
  start, with its name, map and the seed printed; the same seed loads the same room.
- **The doorway slack.** The stricter part of the check traces the wall between the player and the door: it found 50
  region-frame entrances the use ray could not reach from where a player can stand, mostly because an entrance's own
  doorway collision closes the doorway a few units in front of the door's use box. The use ray may now meet a surface
  up to 16 units before the door (a wall farther out still refuses it), and the check stands the player only on a
  walkable floor. All 1,102 entrances are usable after walking in and both ways; with the wall traced 1,067 are, 31
  more than before. The Sadrith Mora Gateway Inn's north wing and Arkngthand now prompt and enter in game
  ([DOOR-USE-BLOCKED-53](../../BUGS.md)).
- **The Suran dancers dance.** The base game ships a dancing animation, and four characters in the master files name it
  as their own. Our skeletal characters ignored an animation file of a character's own, so Desele's dancers only
  idled. Those files now join the shared humanoid table as their own groups, and the dancers loop their dance
  ([DANCER-OWN-ANIM-IGNORED-53](../../BUGS.md)). The 432 creatures that play their own files keep their baked frames; tables
  of their own follow in v0.0.54.
- **The Halloween scene.** `dbg halloween` starts it on the animation stage's roof in Balmora: after a greeting on a
  black screen (five seconds, in silence), the game's skeletons, Desele's dancers and Dagoth Ur dance to a beat, filmed
  by a small camera director (wide, dolly, tracking, crane, orbit and close-up shots, each keeping its subject whole),
  at sunset. Two versions: Dagoth Ur in the centre with the dancers and skeletons around him, or the skeletons alone
  (`dbg halloween skeletons`). Built with `--miniwind-halloween`; every move is a group of the shared animation tables
  played by name. Dagoth Ur gets a small animation table of his own, the first creature on one
  ([HALLOWEEN-SCENE-53](../../BUGS.md), [the scene](../../HALLOWEEN.md)).
- **The standard benchmark.** `aw bench halloween` (aliases `aw halloweenbench` and `dbg halloween bench`) plays the
  scene as 600 frames with the scene clock stepping a tenth of a second each frame, so every machine draws the same
  frames, and prints one line to copy: the average, minimum and 1 % low frame rates, the frames, the seconds, the Fast
  RAM, the CPU and the build. `aw bench NAME` takes more scenes later. The hardware page names it the standard test
  ([BENCH-NO-STANDARD-DEMO-48](../../BUGS.md), [AmiWind on real hardware](../../REAL_HARDWARE.md)).
- **The custom OST slot.** A build can carry one track of your own (`--custom-ost FILE`): the builder converts its audio
  into the game's music stream and packs it into your image only, so no other stage is rebuilt. `aw music custom play`
  plays it alone while the game's playlist waits and `aw music custom stop` gives the playlist back; the scene and the
  benchmark use only this player, and are silent without a track. The repository and the public builds carry no
  song ([CUSTOM-OST-SLOT-53](../../BUGS.md)).
- **The disk check.** Every build checks, before anything else (before the builder image and before the game data is
  copied into a Docker volume) and again before each stage, that the disk holds the last known good build's measured
  footprint plus 30 %, never less than 35 GiB. Every passing build records its own footprint and the release ships the
  last figure. The settings are in the build defaults and rebuild nothing when changed
  ([BUILD-DISK-NEED-UNKNOWN-52](../../BUGS.md), [Linux build guide](../../LINUX_BUILD.md)).
- **Faster GitHub checks.** The public tools are kept between runs, the test suite runs in six shards side by side, and
  the dry-run image is built after the tests, each job with its own time limit; the v0.0.52 run had been cancelled at
  its single job's limit ([CI-SOURCE-JOB-TIMEOUT-52](../../BUGS.md), [CI_DRY_RUN.md](../../CI_DRY_RUN.md)).
- **The fingerprint fix.** A cache hit now names only code the stage key counts, so the records of the CHIM world, the
  room stages, area and character are no longer refused after a development build: a version-only change rebuilds only
  the engine and the image (40 of 43 stages reused in the proving build)
  ([BUILD-STAGE-READS-UNFINGERPRINTED-48](../../BUGS.md)).
- **The deferral expiry.** A maintainer's deferral that names a version counts only until that version; at it, the bug
  fails the persisting check and is triaged again, so deferrals no longer carry bugs through the release they name
  ([REGISTER-DEFERRAL-EXPIRES-53](../../BUGS.md)).

## Known in this build

- 35 entrances still keep the use key out of reach, because their converted collision fills the space the player needs:
  24 Daedric shrines whose steps the player slides off, 7 raised trapdoors, 2 Dwemer doors, a Redoran hut door and the
  Unmarked Shipwreck's upper trapdoor ([DOOR-USE-COLLISION-FILLED-53](../../bugs/DOOR-USE-COLLISION-FILLED-53.md)); the fix changes the CHIM world's
  collision and comes in v0.0.54.
- The inspect pin at an exterior load door names the building shell around it, not the door
  ([INSPECT-PIN-LOAD-DOOR-51](../../bugs/INSPECT-PIN-LOAD-DOOR-51.md)).
- The Halloween scene and `aw bench halloween` need an image built with the cast (`--miniwind-halloween`); the release
  images do not carry it, so there both say the image has no cast. The cast joins the default build in a
  follow-up.
- Characters idle in place without wandering, nobody attacks on sight, and Dagoth Ur does not fight or speak (v0.0.54).
- Some large interiors, in Vivec above all, are still loading in when you are already there
  ([CHIM-ROOM-POPIN-51](../../bugs/CHIM-ROOM-POPIN-51.md)).
- The first measured disk figure with per-stage numbers is still to be written by a build
  ([BUILD-DISK-NEED-UNKNOWN-52](../../bugs/BUILD-DISK-NEED-UNKNOWN-52.md)); the shipped figure is the one measured on the v0.0.52 final.
- The GitHub checks' job times for this release are recorded after its first run
  ([CI-SOURCE-JOB-TIMEOUT-52](../../bugs/CI-SOURCE-JOB-TIMEOUT-52.md)).
- The v0.0.51 playtest findings still open (silt striders, the crosshair, the night speckle, loose fire sprites) are in
  the [bug register](../../BUGS.md) for v0.0.54.
