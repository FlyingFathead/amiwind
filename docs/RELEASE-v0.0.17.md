# AmiWind v0.0.17 — easier building and demo startup

Build on Ubuntu/Debian Linux or Ubuntu under WSL with `./build.sh --autoinstall`.
The tool checks existing packages, proposes missing dependencies, downloads
verified native tools, creates an isolated Python environment, and continues
conversion and compilation with live progress and per-stage logs.

- Finds nested Morrowind Data Files directories and validates inputs.
- Uses root `VERSION` for tools, runtime, boot text and output filenames.
- Adds `--autorun-fs-uae` and `--kickstart-file PATH`. Supply an owned A1200
  Kickstart 3.1 ROM file or directory; missing selections prompt interactively.
  The launcher fills both ROM and HDF paths in the documented configuration.
- Enables `early_game_demo_start_1`: Seyda Neen town center, track 04
  (`Music/Explore/mx_explore_3.mp3`), then exploration shuffle.
- Updates README, Linux/WSL guides and FS-UAE/WinUAE setup links.
- Records future bounded build parallelism in the roadmap.

The owner completed the full game-data build and reported test-006 works on
Linux/FS-UAE. The final source adds host-side ROM-directory selection and docs;
the Amiga engine is unchanged from that tested candidate. Native compilation,
scene/music tests and 14 final launcher tests passed. Hosted CI will run on the
release push; this record does not claim that it has already passed. Windows/WSL
and physical Amiga behavior remain unverified. Compiler warnings remain open.
See [validation](VALIDATION-v0.0.17.md) for scope.

This is an early demo: bounded town and ship interior, idle NPCs, movement,
greetings and music. Full quests, conversations, NPC wandering and combat are
not implemented. Start with [Linux](LINUX_BUILD.md) or [Windows/WSL](WINDOWS_BUILD.md).

## Downloads

- `AmiWind-v0.0.17-public-source.zip`: complete source and documentation.
- `AmiWind-v0.0.17-public-source-incremental.zip`: cumulative source update from
  the recorded v0.0.16 owner snapshot; also applies over test-001 through test-006.
- Each ZIP has a same-name `.sha256` file.

All archives extract under `amiwind/`. Playable images and original/converted
game files stay private. No Morrowind or Quake game assets, Kickstart ROM or
Workbench files are included. The selected historical documentation screenshots
are retained. Supply your own installed Morrowind files and ROM to play.
