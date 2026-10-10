# AmiWind v0.0.35 - CHIMporting It All: Gathering Up The Loose Branches From The Seashore

Running on CHIM Engine v0.1.0. The boot checklist says it the short way:
"AmiWind v0.0.35 / CHIM v0.1.0".

Over the last releases a lot of work was finished but left on the shore: features, fixes and
builder improvements that sat on side branches while each release went out with the parts it
needed most. This release gathers all of it in. Every loose branch is either merged here or
shown to be in already; unfinished or experimental work ships behind a switch that is off by
default, so nothing is left behind and nothing changes the default game by accident.

The seashore is also where CHIMport began. Converting the open world to CHIM started from the
sea and the coastal regions and circles inward (the cells it works through include the empty
sea cells), so the title ties both together: gathering up the loose branches from the
seashore, where CHIMport began.

Previous release: [v0.0.34](RELEASE-v0.0.34.md).

## The builder

- **Resumable image step and unit caches**: a failed or changed build continues from the last
  finished unit (room, region, map pass), and every stage records hierarchical output hashes
  (units, segments, stage). See [BUILD_CACHE.md](BUILD_CACHE.md).
- **Shared storage pool**: identical outputs of builds, reused stages and prerendered entries
  are stored once; one garbage collector with one retention policy; leased workspaces.
- **Build preflight**: before any stage, an image build checks that the workspace cache is
  writable by the build user, that there is room for the build and that the game data is there,
  and prints the command that fixes each problem
  ([BUILD-CACHE-OWNER-FAILS-STAGE-34](bugs/BUILD-CACHE-OWNER-FAILS-STAGE-34.md)). A cache entry
  that still cannot be read or written later never stops a stage: the unit is built locally.
- **Tighter reuse keys**: a new row in the build scheduler's stage table no longer rebuilds
  stages that never read it ([BUILD-SCHEDULER-TABLE-KEY-35](bugs/BUILD-SCHEDULER-TABLE-KEY-35.md)).
- **Previous-release check**: release candidates and finals must contain the published
  previous release; the check runs first and prints the merge that fixes a missing one.

## What's new in v0.0.35

**In the game**

- **Walk and run:** companions and fighting NPCs walk and run by their real speed instead of sliding
  (the animation kit, on by default; [ANIMKIT.md](ANIMKIT.md)). `dbg animkit` in the console shows and
  plays an NPC's animation groups.
- **Combat:** NPCs hold their weapons and shields while they fight (also with the animation kit's walking
  and running models), swing strength and knockdowns work as in the original, and right-click picks a
  companion.
- **Guards with torches** keep holding them at night with the animation kit (while they stand).
- **A stuck companion** catches up only where you cannot see it; a hostile that cannot reach you
  keeps its distance instead of warping (owner decisions after a study of the original's behaviour).
- **The Vivec Arena Pit** has its interior; every interior got a new, stable save number, so **saves made
  inside an interior with an older version may not load** (saves made outdoors are not affected).
- **Lava** burns: Quake liquid with damage, a red tint, its sound and a glow at night.
- **Seyda Neen** is built from your own game data; the recorded v0.0.31 maps are no longer needed (still
  optional, not recommended).
- **Debug HUD:** the original Morrowind cell (`CELL x,y` outdoors, `INT n` indoors), and `NOCLIP: ON`
  (also `FLY: ON`, `GOD: ON`) while that mode is on.
- **CHIM lighting:** light styles for flickering and pulsing lights and more light sources at night
  (`--chim-lighting-type`; hybrid is the default and partial until the terrain light bake exists).
- **About 30 engine crash fixes** in map, model, sound and text handling, and a check that every map fits
  the engine's limits before the image is written.
- **Reading the game data:** fixes to how record strings, deleted records and archive paths are read.

**Testing and quick builds**

- **Direct start:** a development build can boot straight into a town, a room or a spot with a ready-made
  character.
- **MiniWind presets:** small test builds of one scene, built in minutes, that can set themselves up on
  arrival (for example a companion and fighting NPCs for the animation kit) ([MINIWIND.md](MINIWIND.md)).
- **CHIM converter fixes:** collision hulls, visibility and memory checks for the next CHIM towns (the
  routed hull method stays selectable; chain hulls remain the default).
- **CHIMport:** the island-wide conversion to CHIM, from the coast inward, with its tracker pages and a
  shared, hashed store for its results.

**The builder**

- Resumable image step and unit caches with hierarchical output hashes ([BUILD_CACHE.md](BUILD_CACHE.md)).
- A shared storage pool (outputs stored once by hash), a garbage collector and leased workspaces.
- A build preflight before any stage (cache ownership, free space, game data) and a reuse plan
  (`--reuse-plan`, `--accept-rebuild`); a refused cache entry never stops a stage.
- Every tool that reads an actor model's frames asks one place for its layout, and the payload preflight
  checks every actor layout and item tag table before the image work.
- A check that the builder runs its own source tree (`--check-entry`, developer mode) and run names that
  carry the version.
- Shared-pool inputs are named by their content in every stage key, and pool reads are checked.
- Tighter reuse keys that still cover every input (the CHIM world and its tracker data, the NPC models
  Balmora and the towns take from the shared storage pool), resuming a failed build from its last finished
  unit, and faster critical-path stages.
- Documentation edits no longer make a build start again: the progress report's key covers only the
  files it reads, and an advisory stage (a report) never stops a build.

**Experimental, off by default** ([EXPERIMENTAL_FLAGS.md](EXPERIMENTAL_FLAGS.md)): near and far NPC models,
original NPC heads, the quick character screen, NPC gallery models built from a shared parts library
(modular NPCs), CHIM
towns other than Seyda Neen built with no legacy region maps (`--chim-native-towns on`), and baked
night-lamp light on Balmora's streets and walls (`--night-lamp-lightmaps on`, an early prototype).

**Documentation:** the animation kit, MiniWind, the disk image size, the roadmap, the experimental switches.

Also in this release: the v0.0.34 fixes (silt strider hull, Bitter Coast mushrooms, seam and pick audits).

## Disk size

The image is still the two disk images of v0.0.34; the open-world region maps are most of it.
What fills it, file group by file group, and the roadmap horizon of one partition with CHIM (the
image stays as it is until the whole island runs on CHIM): [IMAGE_SIZE.md](IMAGE_SIZE.md).
On CHIM today: the towns (Seyda Neen's square, docks and census office courtyard, and Balmora); the open land outside them is still built the legacy way until CHIMport replaces it, coast first ([IMAGE_SIZE.md](IMAGE_SIZE.md#what-is-on-chim-today)).

## Known in this build

- [ANIMKIT-TORCH-STANDING-35](bugs/ANIMKIT-TORCH-STANDING-35.md): guards with the animation kit hold their torch only while standing.

- [TOWN-INTERIOR-SAVEID-ORDER-33](bugs/TOWN-INTERIOR-SAVEID-ORDER-33.md): saves made inside interiors with an older version may not load: every interior has a new save number.

See the [bug register](BUGS.md).
