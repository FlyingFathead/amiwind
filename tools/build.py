#!/usr/bin/env python3
"""Guided local build; outputs stay in a private workspace.

CAPACITY FIRST: before starting the build, verify enough usable storage for ALL
required content, conversion intermediates, staging copies, temporary images,
readback verification and a margin. Include filesystem/quota limits and shared
RAM limits for memory-backed scratch. If capacity is insufficient, arrange it
before expensive work; never omit NPC models or the gallery to make a build fit.

All NPCs must be included and loadable by the engine for the game to be complete.
NPC gallery creation MUST NOT be skipped except for exceptional, explicitly
requested debugging purposes. Build time and disk usage are not reasons to omit it.

Normal builds and recovery MUST include the gallery; missing input/model/catalogue
content is an error, never an automatic opt-out. Only the owner's explicit
--no-npc-gallery permits debugging-only omission of inspection assets. It must
never remove required game NPC content or change the normal default.

Skipping NPC model creation together with the gallery is pointless and
counterproductive for a complete build: all character models are still required
in the final product. Exceptional debugging may temporarily isolate the gallery;
it cannot reduce the final game's required content.

BOTH GALLERIES REQUIRE OUTSIDE APPROVAL FOR EXCEPTIONS: the NPC gallery and
upcoming static-asset gallery, including their model generation, catalogues,
coverage, quality and validation, must not be disabled, reduced or bypassed
without a specific documented case/scenario and explicit approval from the
project owner. The builder or contributor cannot approve its own exception.
Time pressure, storage pressure and convenience are not approval. Existing
--no-npc-gallery support is only a mechanism for an owner-approved exceptional
debugging case; its availability does not grant permission to use it.

A complete game requires all of its NPC and other game assets intact, packaged
and loadable by the engine. Skipping model/asset creation with either gallery is
pointless and counterproductive: those assets are required in the final product
anyway. A debugging exception cannot redefine a complete build. Loadable does not
mean all assets must be resident in memory simultaneously. The static-asset
gallery remains planned; this contract does not claim it is implemented.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tarfile
import time

ROOT = Path(__file__).resolve().parents[1]
# Release entity baseline (tools/entity_tracker.py baseline): counts and placement digests.
ENTITY_BASELINE = ROOT / "config/entity-baseline.json"
sys.path.insert(0, str(ROOT / "src"))
from mwad.paths import child_ci, ensure_external, inside, resolve_data_files, installed_game_path, is_wsl, is_game_input
from mwad import input_check
from mwad.progress import Progress, live_log, section
import build_versions
from build_jobs import add_jobs, jobs_warning, resolve_jobs
from build_host import executable_path, find_executable, fallback_font, host_name, setup_plan
from build_summary import BuildSummary
from build_font_options import (add_builder_options, add_font_options, add_heap_options, resolve_builder,
                                resolve_font_options, resolve_heap)
from build_aga import UPSTREAM_SHA256, RUNTIME_BUILD_DIR, VERSION, runtime_sources, check_quakec


# Legacy recorded Seyda Neen maps (owner decision 10 October 2026): optional and NOT RECOMMENDED since v0.0.31.
SEYDA_RECORDED_HELP = ("optional, NOT RECOMMENDED since v0.0.31: legacy recorded v0.0.31 Seyda Neen maps; the "
                       "default converts Seyda Neen from your data. DIR/id1 holds them (from your own v0.0.31 "
                       "image), checked against config/seyda-recorded-v0.0.31.json and kept byte for byte "
                       "(BUILD-SEYDA-REGEN-30, tools/recorded_stage.py)")
SEYDA_RECORDED_WARNING = ("WARNING: --seyda-recorded is NOT RECOMMENDED since v0.0.31: legacy recorded v0.0.31 "
                          "Seyda Neen maps; the default converts Seyda Neen from your data.")


# --anim-kit on|off: the resident animation profile each value selects (tools/npc_anim.py, config/npc-anim-kit.json).
ANIM_KIT_PROFILES = {"on": "react+full", "off": "idle"}


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--data-files", type=Path, help=r"Morrowind installation root or Data Files; e.g. C:\GOG Games\Morrowind (Windows/WSL). Guided mode offers a detected GOG install")
    p.add_argument("--workspace", type=Path, default=ROOT / "out",
                   help="Build output parent (default: ignored out/ in this checkout)")
    p.add_argument("--stage", choices=("terrain", "aga"), default="aga",
                   help="terrain: host packets only; aga: full experimental HDF")
    p.add_argument("--check", action="store_true", help="Check prerequisites without conversion; optional interactive SDK setup requires confirmation")
    p.add_argument("--plan", action="store_true", help="Check prerequisites and print commands without running")
    p.add_argument("--install-dependencies", action="store_true", help="Preview and confirm Ubuntu/Debian host packages and an external Python environment")
    p.add_argument("--autoinstall", action="store_true", help="Quickest setup: confirm missing host/Python/native dependencies, install them, then continue the build")
    p.add_argument("--yes", action="store_true", help="With --autoinstall, accept the displayed dependency proposal and APT installation (for CI)")
    p.add_argument("--install-sdk", action="store_true", help="Fetch the pinned Linux x86_64 Amiga SDK after confirmation; works alone or with --install-dependencies")
    p.add_argument("--tools-dir", type=Path, default=ROOT.parent / "amiwind-tools", help="External dependency environment parent (default: ../amiwind-tools)")
    p.add_argument("--versions", action="store_true", help="Compare available tools/packages with the recorded build reference, then exit")
    p.add_argument("--host-plan", action="store_true", help="Read-only OS-specific tool inventory; no installation, tool execution or game data required")
    p.add_argument("--fallback-font", type=Path, help="DejaVuSansMono.ttf for generated console graphics (default: tools/fonts or Linux system font)")
    p.add_argument("--check-inputs", action="store_true", help="Check the game installation without requiring build tools, then exit")
    p.add_argument("--layout-selftest", action="store_true",
                   help="Prove the disk-layout gate refuses every Amiga disk limit through the image step's packing "
                        "code (sparse dummy files, seconds, always cleaned up), then exit; no game data needed")
    p.add_argument("--dry-run", action="store_true", help="Actually compile the engine and create an asset-free boot-notice HDF; --plan only previews commands")
    p.add_argument('--recover-image-from', type=Path, help='Recover an rc3 image-stage failure into a new run, reusing completed conversion; rebuild engine, gallery and image')
    p.add_argument('--accept-known-stair-findings', action='append', default=[], metavar='ID',
                   help='PRIVATE -devN TESTS ONLY: the stair gates (CHIM stage and image step) accept the failures of this '
                        'known finding (tracker ID, config/known-stair-findings.json); recorded; refused for rc and final')
    p.add_argument('--allow-known-actor-ground-findings', type=Path,
                   help='PRIVATE TEST ONLY: accept an exact reviewed actor-contact report; does not pass the production gate')
    p.add_argument("--autorun-fs-uae", action="store_true", help="Check FS-UAE and your ROM before setup, then launch the completed HDF using the documented preset")
    p.add_argument("--kickstart-file", "--kickstart", dest="kickstart_file", type=Path,
                   help="Owned ROM file or directory for --autorun-fs-uae (default: ~/.roms/; asks if missing interactively)")
    p.add_argument("--amiga-libs", type=Path, metavar="DIR",
                   help="Optional: a folder from your own Workbench/accelerator installation (or its LIBS: drawer). "
                        "68040.library/68060.library found there are copied to LIBS: on the boot disk and opened at boot; "
                        "without one the build continues and reports no FPU support library. See docs/FPU_SUPPORT_LIBRARY.md")
    p.add_argument("--seyda-recorded", type=Path, metavar="DIR",
                   help=SEYDA_RECORDED_HELP)
    p.add_argument("--skip-dressing", action="store_true",
                   help="DEBUGGING ONLY: the earlier interior rule, leaving out lantern hooks, ropes, ferns and other "
                        "dressing in the Seyda Neen interiors (receipted); by default they are kept (BUILD-DRESSING-EXCLUDED-32)")
    p.add_argument("--no-entity-baseline", action="store_true",
                   help="DEBUGGING ONLY: do not compare the image's entity tracker with the release baseline "
                        "(config/entity-baseline.json); by default a placement lost against it stops the build")
    p.add_argument("--accept-entity-loss", metavar="REASON",
                   help="Recorded reason that lets an intended loss against the entity baseline pass")
    p.add_argument("--amiga-libs-policy", choices=("warn", "fail", "require-known"), default="warn",
                   help="Known-inputs policy for --amiga-libs: warn (default; unknown builds used with a warning, "
                        "invalid files not used), fail (an invalid file stops the build), require-known. See docs/KNOWN_INPUTS.md")
    p.add_argument("--game-data-policy", choices=("warn", "fail", "require-known"), default="warn",
                   help="Known-inputs policy for Morrowind/Tribunal/Bloodmoon .esm/.bsa: warn (default; unknown versions "
                        "used with a warning), fail (any invalid file stops), require-known. See docs/KNOWN_INPUTS.md")
    p.add_argument("--check-hashes", choices=("core", "full", "auto", "off"), default="core",
                   help="Input hashing with the workspace lock amiwind-inputs.lock: core (default; the masters, archives, "
                        "Amiga libraries and ROM are hashed every build, other inputs only when size or times changed), "
                        "full (every input; use for releases), auto (every input only when changed), off (no checks; loud warning)")
    p.add_argument("--allow-data-differences", action="store_true", help="Explicitly allow unverified edition/file checksum differences; container and required-group errors still block")
    p.add_argument("--name", help="New immutable run name; default YYYY_MM_DD_vX.Y.Z[-suffix]_<purpose>[-tryN]_<gitshort> "
                                  "(tools/run_name.py); an explicit name must contain the source version")
    p.add_argument("--any-run-name", action="store_true",
                   help="Allow a --name without the source version (loud warning)")
    p.add_argument("--developer-mode", "--devmode", dest="developer_mode", action="store_true",
                   help="Before any stage, check and print the working version (refused when the source VERSION "
                        "differs), that every builder module comes from this source tree, the integration head, the "
                        "storage pool (writable, hard links), the run name and a reuse preflight; recorded in "
                        "build-state.json (tools/entry_check.py, docs/BUILD_CACHE.md \"Developer mode\")")
    p.add_argument("--working-version", type=Path, metavar="FILE",
                   help="Working-version record (JSON with working_version, optional integration_head); default "
                        "AMIWIND_WORKING_VERSION, then WORKSPACE/../WORKING_VERSION.json, then the storage pool's")
    p.add_argument("--accept-version-mismatch", metavar="REASON",
                   help="Developer mode: build although the source VERSION differs from the working version (say why)")
    p.add_argument("--source-commit", metavar="HASH",
                   help="The source commit for the run name when the source is not a git checkout "
                        "(also AMIWIND_SOURCE_COMMIT; else 'nogit')")
    p.add_argument("--sdk", type=Path, help="AmigaPorts GCC SDK root")
    p.add_argument("--vasm", type=Path, help="Separate vasmm68k_mot executable (default: SDK bin directory)")
    p.add_argument("--upstream-archive", type=Path, help="Optional legacy provenance check; the runtime source is included")
    p.add_argument("--quake-tools", type=Path, help="ericw-tools directory containing qbsp, vis, light")
    p.add_argument("--qcc", help="QuakeC compiler path or command (qcc-host, qcc or fteqcc)")
    p.add_argument("--intro-captions", type=Path, help="Private opening quote JSON; runtime aw_intro_text_overlay 0/1 selects original/readable text")
    p.add_argument("--ffmpeg", default="ffmpeg")
    p.add_argument("--xdftool", default="xdftool")
    p.add_argument("--rdbtool", default="rdbtool")
    p.add_argument('--gallery-cache', type=Path, help='Persistent NPC model cache (default: WORKSPACE/cache/npc-gallery-v1); gallery coverage remains mandatory')
    p.add_argument('--gallery-seed-run', type=Path, help='Import completed compatible model pairs from a stopped rc9 build run')
    p.add_argument("--anim-kit", choices=("on", "off"), default="on",
                   help="The animation kit (docs/ANIMKIT.md): on (default) = residents get the react+full kit, so companions and fighters walk and run by speed; off = the previous 8 idle frames (--npc-anim idle). --npc-anim picks a profile directly and wins over this switch")
    p.add_argument("--npc-anim", choices=("idle", "react", "move", "full", "react+full"), default=None,
                   help="NPC animation groups per resident model (config/npc-anim-kit.json, docs/ANIMATION.md); default from --anim-kit (on: react+full, off: idle): idle = the previous 8 idle frames; react adds hit and death; move adds walk and run; full adds swim, knockdown and a hand-to-hand attack; react+full (owner decision for the next release) = react standing models plus a full model each actor wears only while it moves")
    p.add_argument("--no-npc-gallery", action="store_true", help="DEBUGGING ONLY: omit inspection gallery, never required game NPCs; gallery included by default. The image says so in game: dbg npcgallery and the other gallery commands print a built-without-the-NPC-gallery notice. Same as --exclude npc-gallery")
    p.add_argument("--npc-root-rule", choices=("morrowind", "legacy"), default="legacy", help="NIF root node rule for NPC body parts and equipment: legacy (default; the full root transform, verified correct for rigid body parts) or morrowind (the root rotation is ignored exactly as for scenery; measured to break 35 rigid NPC part meshes). Part of every NPC stage's cache key (AMIWIND_NPC_ROOT_RULE)")
    from build_exclusions import add_options as add_exclusion_options
    add_exclusion_options(p)
    p.add_argument('--with-video', action='store_true',
                   help='MiniWind: keep the videos (a MiniWind build leaves them out by default, '
                        'like --exclude video)')
    p.add_argument('--npc-models', choices=('whole', 'parts'), default='whole',
                   help='NPC gallery humanoid models: whole (each appearance baked whole; default) or parts '
                        '(each body part converted once, appearances composed; docs/MODULAR_NPCS.md)')
    p.add_argument('--parts-cache', type=Path, help='Persistent NPC parts library for --npc-models parts '
                   '(default: WORKSPACE/cache/npc-parts-v1)')
    p.add_argument('--npc-parts-policy', default='exact', metavar='exact|levelsN',
                   help='Part quota policy for --npc-models parts: exact (default) or levelsN (N 1-16 levels per part)')
    p.add_argument('--npc-parts-face-cap', type=int, default=666, metavar='FACES',
                   help='Per-actor face cap for levelsN recipes (64-666); an outfit over it uses its exact recipe')
    p.add_argument("--hands", choices=("3d","sprites"), default="3d", help="First-person runtime build: Nord first-person hands and original carried torch")
    p.add_argument('--no-tree-sprites', action='store_true',
                   help='DEBUGGING ONLY: omit world flora (original trees, grass and reeds as sprites with collision, '
                        'shipped since v0.0.28); flora is built by default and such an image does not match a release')
    p.add_argument('--no-cell-progress', action='store_true',
                   help='DEBUGGING ONLY: skip writing the cell progress data of a CHIM build (BUILD/toolkit/cell-progress.json for the '
                        'Toolkit World Map; on by default, never fails the build)')
    p.add_argument('--live-tracker', nargs='?', const='file', choices=('file', 'server'), default=None,
                   help='Follow a CHIM build on the Toolkit map while it runs. file (default when no value is given): no server, a '
                        'static page in BUILD/toolkit/live that refreshes itself; server: a small local web server on 127.0.0.1 '
                        'only, read-only, stopped with the build. Guided builds ask once; other builds are off unless given')
    p.add_argument('--no-live-tracker', dest='tracker_declined', action='store_true', help='Do not offer or start the live build tracker')
    p.add_argument('--keep-tracker', action='store_true',
                   help='Keep the live tracker server running after the build until you press Enter (never left running unattended)')
    p.add_argument('--no-harvest', action='store_true',
                   help='DEBUGGING ONLY: omit harvestable mushrooms (shipped since v0.0.29); the harvest step is built '
                        'by default and such an image does not match a release (mushrooms stay baked, not pickable)')
    p.add_argument('--tree-sprites', action='store_true',
                   help='No effect, kept for old command lines: world flora is built by default (BUILD-FLORA-OPTIN-32)')
    p.add_argument('--map-budget-policy', choices=('strict', 'warning'), default='strict',
                   help='Private playtest only: warning permits modeled reserve allowance excess; actual allocation limits and other checks remain enforced')
    from vis_options import VIS_MODES, DEFAULT_VIS_MODE
    p.add_argument('--vis', '--vis-mode', dest='vis_mode', choices=VIS_MODES, default=DEFAULT_VIS_MODE,
                   help='Map compiler vis pass for every converted map: fast (default; portal flood only, '
                        'outputs unchanged) or full (full portal flow, slower). vis threads follow --jobs. '
                        'See docs/performance/TOWN-VISIBILITY.md')
    from town_config import extra_towns as offered_towns, shipped_extra_towns
    # A registry row with "blocked": reason is configured but fails a limit; it
    # stays in the table (stable save IDs) and is not offered here. A row with
    # "shipped_since" is part of the release and built by default
    # (BUILD-EXTRA-TOWN-OPTIN-32); --extra-town adds the others.
    # A shipped row with "withdrawn": reason is left out of default builds (owner
    # decision) and offered here again like a town not shipped yet.
    extra_towns, shipped_towns = offered_towns(), shipped_extra_towns()
    p.add_argument('--extra-town', action='append', default=[], choices=extra_towns, metavar='TOWN',
                   help='Also import this town from config/towns.json (towns not shipped yet: '
                        + (', '.join(t for t in extra_towns if t not in shipped_towns) or 'none')
                        + '; shipped towns, ' + (', '.join(shipped_towns) or 'none')
                        + ', are built by default and need no option). See docs/TOWN_IMPORT.md')
    p.add_argument('--no-extra-town', action='append', default=[], choices=shipped_towns, metavar='TOWN',
                   help='DEBUGGING ONLY: leave out this shipped town (' + (', '.join(shipped_towns) or 'none')
                        + '), which every default build makes; such an image does not match a release')
    p.add_argument('--only-core-towns', action='store_true',
                   help='DEBUGGING ONLY: build Seyda Neen and Balmora only, without the shipped towns ('
                        + (', '.join(shipped_towns) or 'none') + ') or any --extra-town; such an image does '
                        'not match a release')
    p.add_argument('--night-lamp-lightmaps', choices=('on', 'off'), default='off',
                   help='EXPERIMENTAL (off by default): legacy Balmora cores get baked night-lamp lightmaps on '
                        'lightstyle 32 (prototype, tools/lamp_lightmaps.py; docs/EXPERIMENTAL_FLAGS.md); off keeps '
                        'the night lamps as engine lights only')
    p.add_argument('--chim-native-towns', choices=('on', 'off'), default='off',
                   help='EXPERIMENTAL (off by default in v0.0.35): build CHIM towns other than Seyda Neen from the '
                        'game data with no legacy region-map chain (tools/chim_town.py, CHIM-LEGACY-CHAIN-33); '
                        'off keeps their legacy chains (docs/EXPERIMENTAL_FLAGS.md)')
    p.add_argument('--legacy-area', dest='legacy_areas', action='append', default=[], metavar='TOWN',
                   help='DEBUGGING ONLY (legacy): build TOWN with the legacy region-map chain (tools/import_town.py) '
                        'although the CHIM builder holds it; default: a CHIM town has no legacy maps '
                        '(docs/chim/build_guide/BUILDER_TYPES.md)')
    p.add_argument('--miniwind', action='store_true',
                   help='Build type AmiWind "MiniWind" Playtester Build: a quick PARTIAL-AREA test of Balmora only '
                        '(Balmora exterior on CHIM, Balmora interiors, engine, menus, UI, audio, fonts and music); '
                        'no Seyda Neen, open world or extra towns; boots straight into Balmora. Private -devN '
                        'versions only, never a release. See docs/MINIWIND_PLAYTESTER.md')
    p.add_argument('--miniwind-description', metavar='TEXT',
                   help='With --miniwind: optional "Scene: TEXT" line on the startup screen (printable ASCII, '
                        'at most two lines; recorded in the build receipt)')
    p.add_argument('--miniwind-scope', metavar='SCOPE',
                   help='With --miniwind: full (default: the Balmora exterior on CHIM and the Balmora interiors) or '
                        'exterior (the leanest test build: the Balmora exterior on CHIM only, no interiors, no NPC '
                        'gallery; every door says "Area unavailable"; labelled "quick playtest, no NPC gallery")')
    p.add_argument('--miniwind-town', metavar='TOWN',
                   help='With --miniwind: the town the sandbox holds and boots into (default balmora; any town '
                        'table row but seyda, e.g. vivec_temple): its exterior on CHIM, its residents and, in the '
                        'full scope, its interiors')
    p.add_argument('--miniwind-debug', action='store_true',
                   help='With --miniwind: a DEBUG ONLY sandbox, not a playtest (notice, startup screen, marker, '
                        'HDF and run names say so); the only build type that takes --chim-draw-distance')
    p.add_argument('--chim-detail-budget', metavar='NAME',
                   help='CHIM builder: a named per-mesh visual triangle budget (config/chim-detail-budgets.json); '
                        'default none')
    p.add_argument('--chim-cut-models-over', type=float, metavar='UNITS',
                   help='CHIM builder: cut models wider than UNITS into tiles shared by their placements '
                        '(tools/chim/cut.py); default none')
    p.add_argument('--chim-draw-distance', type=int, metavar='UNITS',
                   help='DEBUG ONLY (--miniwind --miniwind-debug): a stated closer view; the CHIM world is built '
                        'and heap-gated for this draw distance and the image starts with it (default 540)')
    from miniwind_presets import add_options as add_miniwind_preset_options
    add_miniwind_preset_options(p)
    p.add_argument('--direct-to-game-map', dest='direct_to_game_map', metavar='START',
                   help='Quick test build (-devN only): boot straight into START with a ready-made character, no '
                        'intro, ship or character creation. START: an area (balmora, seyda_neen, vivec_arena), '
                        '"interior:<cell id>", cell:X,Y or pos:X,Y,Z[@HEADING] (the debug HUD\'s GLOBAL XYZ). '
                        'See docs/chim/build_guide/DIRECT_START.md')
    p.add_argument('--miniwind-boot', metavar='CMD[;CMD]',
                   help='With --miniwind: dbg console commands the sandbox runs once on arrival, separated by ";" '
                        '(a preset row\'s boot_commands; docs/MINIWIND.md)')
    p.add_argument('--quick-character', metavar='RACE,CLASS[,NAME]',
                   help='The ready-made character of a direct start or MiniWind build (default: the Hors preset, '
                        'Nord Barbarian); RACE and CLASS must be playable in your game files')
    census = p.add_mutually_exclusive_group()
    census.add_argument('--skip-census', dest='skip_census', action='store_const', const=True, default=None,
                        help='New Game makes the character on the quick character screen (name, race and head, '
                             'class, birthsign, attributes and skills: the census office menus) and goes straight to the '
                             'scene, without the ship and the census office walk. Default: on for MiniWind and other '
                             'direct-start builds (unless --quick-character gives the character), off for every other '
                             'build. -devN only. See docs/chim/build_guide/DIRECT_START.md')
    census.add_argument('--no-skip-census', dest='skip_census', action='store_const', const=False,
                        help='Keep the previous start: a MiniWind or direct-start build starts with its ready-made '
                             'character (Hors or --quick-character), a normal build with the ship and the census')
    from hidden_surface_build import add_options as add_hidden_surface_options
    add_hidden_surface_options(p)
    from exterior_sky_build import add_options as add_exterior_sky_options
    add_exterior_sky_options(p)
    p.add_argument('--estimate-world', type=Path, metavar='OUT',
                   help='Estimate every world map (heap, BSP limits, entities) from --data-files into OUT, '
                        'without converting; then exit. See docs/WORLD_ESTIMATE.md')
    p.add_argument('--estimate-sample', type=int, default=0, metavar='N',
                   help='With --estimate-world: also convert N stratified maps and report the estimate error '
                        '(uses --quake-tools and --sdk)')
    from scenery_reduce import add_options as add_scenery_reduce_options
    add_scenery_reduce_options(p)
    add_jobs(p)
    p.add_argument('--serial-stages', action='store_true',
                   help='Run stages in order while retaining each stage job limit (diagnostics)')
    p.add_argument('--live-logs', action='store_true',
                   help='BENCHMARK/DIAGNOSTIC IMAGES: the engine writes its diagnostic logs as they happen '
                        '(aw_logs_live 1; tools/profile_aga.py reads them); default: in memory until Exit game '
                        'or dbg savelogs, so play keeps the boot volume quiet (BOOT-VOLUME-NOT-VALIDATED-33)')
    p.add_argument('--no-profile', action='store_true',
                   help='DEBUGGING ONLY: run stages without the build profiler and output manifests '
                        '(build-profile.json); outputs are the same, and a later --reuse-from cannot use such a run. '
                        'See docs/BUILD_PROFILE.md')
    p.add_argument('--reuse-from', type=Path, metavar='RUN',
                   help='Development builds: copy the verified outputs of stages whose input fingerprint is unchanged '
                        'from this earlier run instead of running them; refused for release candidates and finals. '
                        'See docs/BUILD_PROFILE.md')
    p.add_argument('--rebuild-stage', metavar='NAME[,NAME]', default='',
                   help='With --reuse-from: run these stages again although they could be reused; every stage after '
                        'them is still decided by its key (reused only if the forced stages write the same outputs). '
                        'Same release rules as --reuse-from. See docs/BUILD_CACHE.md')
    p.add_argument('--rebuild-unit', metavar='UNIT:NAME[,UNIT:NAME]', default='',
                   help='Build these stage units again although they are cached (interior-room:bmtemple, '
                        'town-region:bm003, world-scenery-region:vf0123, UNIT:* for all); list them with '
                        'python tools/pass_cache.py list WORKSPACE/cache/image-passes. See docs/BUILD_CACHE.md')
    p.add_argument('--accept-rebuild', action='store_true',
                   help='With --reuse-from: build even when the reuse preflight finds stages rebuilt for no reason the '
                        'source diff or their inputs explain (a key too broad); without it the build stops before any '
                        'stage runs. See docs/BUILD_CACHE.md "Reuse preflight"')
    p.add_argument('--reuse-mode', choices=('copy', 'hardlink', 'pool'), default='copy',
                   help='With --reuse-from: copy (default), hard-link reused files, or link them from the shared '
                        'storage pool (WORKSPACE/cache/asset-pool-v1; the old file is pooled by a hard link, never '
                        'copied). Linked files are made read-only in every run sharing them; never as root')
    p.add_argument('--storage-pool', choices=('auto', 'on', 'off'), default='auto',
                   help='Store the outputs of a passed build once in the shared storage pool '
                        '(WORKSPACE/cache/asset-pool-v1, by SHA-256) and replace them in the run by read-only hard '
                        'links, so identical files of other runs, reused stages and prerendered entries take no '
                        'extra space (docs/BUILD_CACHE.md). auto (default): development builds; on: every build; '
                        'off: DEBUGGING ONLY')
    p.add_argument('--storage-pool-dir', type=Path, metavar='DIR',
                   help='The shared storage pool folder (default WORKSPACE/cache/asset-pool-v1; also the build config '
                        'key storage_pool_dir or the environment variable AMIWIND_STORAGE_POOL, in that order after '
                        'this option). Name one folder in several workspaces and in tools/chimport.py to share ONE '
                        'pool. Hard links need it on the same file system and mount as the run: otherwise files are '
                        'copied, with one warning recorded in the build state (docs/BUILD_CACHE.md)')
    p.add_argument('--stair-walk', choices=('auto', 'all', 'flights'), default='auto',
                   help='What the image step\'s stair walk covers: all (every step and ramp; the advisory '
                        'findings), flights (only the steps of flights, which gate the build) or auto (default: '
                        'all for development builds, flights for release candidates and finals; a nightly full '
                        'report uses all)')
    p.add_argument('--allow-release-reuse', action='store_true',
                   help='With --reuse-from on a release candidate or final VERSION, and for the per-file caches '
                        '(world terrain, media, the per-map passes of the image step, whose receipts count their hits): '
                        'only while the from-scratch gate runs separately on the same commit and its payload is '
                        'compared file by file with the release payload')
    p.add_argument('--prerendered', nargs='+', metavar='DIR',
                   help='Prerendered store (docs/chim/build_guide/SPEED.md): --prerendered DIR uses stored stage outputs '
                        'with the same fingerprint and stores the chosen stages of this build once the whole build passed; '
                        '--prerendered list DIR, --prerendered verify DIR and --prerendered prune DIR inspect it '
                        '(prune only reports candidates)')
    p.add_argument('--prerendered-stages', default='default', metavar='STAGES',
                   help='With --prerendered DIR: stages to store: default (CHIM worlds, interiors, Balmora, area, '
                        'towns), all, or a comma list of stage names')
    p.add_argument('--no-unit-cache', action='store_true',
                   help='DEBUGGING ONLY: convert every world terrain map even when a verified copy is in the '
                        'per-map cache (WORKSPACE/cache/world-terrain-v1; development builds only)')
    p.add_argument('--no-media-cache', action='store_true',
                   help='DEBUGGING ONLY: convert every sound and movie even when a verified copy is in the '
                        'asset pool (WORKSPACE/cache/asset-pool-v1; development builds only)')
    p.add_argument('--fingerprint-scope', choices=('units', 'symbols', 'modules'), default='units',
                   help='Stage fingerprint sources: units (default; the code each stage can reach, hashed per '
                        'reached function), symbols (the same code, whole files hashed) or modules (the first, '
                        'wider method: every import of every imported module)')
    add_font_options(p)
    import npc_lod
    npc_lod.add_options(p)
    add_builder_options(p)
    add_heap_options(p)
    return p


def ask(value, prompt, interactive):
    if value is not None:
        return value
    if interactive:
        return input(prompt + ": ").strip() or None
    return None


def detected_sdk(args):
    """Find the SDK installed by our setup command, without writing anything."""
    candidate = ensure_external(args.tools_dir / "sdk", "SDK")
    assembler = executable_path(args.vasm or candidate / "bin/vasmm68k_mot")
    required = (executable_path(candidate / "bin/m68k-amigaos-gcc"), assembler,
                candidate / "m68k-amigaos/ndk-include/exec/exec_lib.i")
    return candidate if all(path.is_file() for path in required) else None


def select_sdk(args, interactive=False, game_data=None, install_requested=False):
    """Downloads require explicit selection and consent; plans never fetch."""
    if args.sdk:
        return ensure_external(args.sdk, "SDK")
    found = detected_sdk(args)
    if found:
        print(f"Using installed Amiga SDK: {found}")
        return found

    if host_name() == 'windows':
        raise ValueError('Windows SDK download is not implemented. Select an installed Windows SDK '
                         'with --sdk; use --host-plan and docs/WINDOWS_BUILD_ROADMAP.md.')

    from fetch_toolchain import SPEC, fetch
    destination = ensure_external(args.tools_dir / "sdk", "SDK download directory")
    command = [sys.executable, str(ROOT / "tools/fetch_toolchain.py"),
               "--out", str(destination)]
    print("Amiga SDK not configured. It provides the Amiga cross-compiler and assembler.")
    print(f"Pinned download: {SPEC['release']}, {SPEC['bytes']:,} bytes; size and SHA-256 checked before extraction.")
    print("SDK release page: https://github.com/AmigaPorts/m68k-amigaos-gcc/releases/tag/" + SPEC['release'])
    print("Source: " + SPEC['url'])
    print(f"Destination: {destination}")
    available = not destination.exists() and not destination.is_symlink()
    if available:
        print("Standalone SDK download command (no APT or pip installation):")
        print("  " + shlex.join(command))
    else:
        print("This destination already exists but is not a complete SDK; it will not be overwritten.")
        print("Select an existing SDK with --sdk, or choose a new --tools-dir for setup.")
    if install_requested and (args.plan or args.check):
        print("SDK setup preview only. No download or directory creation performed.")
        return None
    if args.plan:
        print("Plan mode never downloads; use the standalone command separately.")
    elif args.check:
        print("This is a prerequisite check. Only choosing 'install' and confirming will write SDK files; no build will run.")
    prompt = "SDK root, 'install' to download" if available and not args.plan else "Existing AmigaPorts SDK root"
    raw = 'install' if install_requested else ask(None, prompt + " (Enter to report missing)", interactive)
    if not raw:
        return None
    if raw.casefold() != 'install':
        return ensure_external(raw, "SDK")
    if args.plan or not available:
        print("SDK download unavailable in this mode or destination. Use the setup guidance above.")
        return None
    if game_data and (inside(destination, game_data) or inside(game_data, destination)):
        raise ValueError("Keep the SDK download directory separate from the game installation")
    if input("Download and extract this SDK now? [y/N] ").strip().casefold() in ("y", "yes"):
        try:
            fetch(destination)
        except tarfile.TarError as exc:
            raise ValueError(f"SDK extraction failed: {exc}") from exc
        return destination
    print("SDK download declined. No SDK files created.")
    return None


def gog_installation():
    if not (sys.platform == "win32" or is_wsl()):
        return None
    try:
        root = installed_game_path(r"C:\GOG Games\Morrowind")
        data = resolve_data_files(root)
        if input_check.matches_core(data):
            return root
    except (OSError, ValueError):
        pass
    return None


def game_input(value, interactive):
    if value is not None:
        return value
    if not interactive:
        return None
    print("Use your installed Morrowind files. Store pages:")
    print("  GOG: https://www.gog.com/en/game/the_elder_scrolls_iii_morrowind_goty_edition")
    print("  Steam: https://store.steampowered.com/app/22320/The_Elder_Scrolls_III_Morrowind_Game_of_the_Year_Edition/")
    print("Host: " + ("WSL" if is_wsl() else sys.platform))
    if sys.platform == "win32" or is_wsl():
        print(r"Checking C:\GOG Games\Morrowind for the reference core file sizes and SHA-256 hashes...", flush=True)
    candidate = gog_installation()
    if candidate:
        print(f"Found a matching GOG installation: {candidate}")
        print("Morrowind.esm and Morrowind.bsa match reference sizes and SHA-256 hashes; full input checks follow.")
        if input("Use this installation? [Y/n] ").strip().casefold() in ("", "y", "yes"):
            return candidate
    else:
        print("No matching default GOG installation detected. Select your installed game folder; another edition/location may still be usable.")
    return input("Morrowind installation root (or Data Files directory): ").strip() or None


def choose_installation(candidates):
    print("Multiple candidate installations found; choose the one to validate:")
    for number, path in enumerate(candidates, 1):
        print(f"  {number}. {path}")
    while True:
        answer = input("Installation number (Enter to cancel): ").strip()
        if not answer:
            raise ValueError("No installation selected; rerun with --data-files pointing to the desired folder")
        if answer.isdigit() and 1 <= int(answer) <= len(candidates):
            return candidates[int(answer)-1]
        print(f"Enter a number from 1 to {len(candidates)}.")


def executable(value, label, errors):
    found = find_executable(value)
    if not found:
        errors.append(f"{label}: executable not found ({value or 'not supplied'})")
        return None
    return str(Path(found).resolve())


def prepare_dependencies(args, interactive):
    if args.autoinstall or (interactive and sys.platform == 'linux' and not args.plan):
        from setup_build import setup
        if not args.sdk:
            args.sdk = detected_sdk(args)
        if not setup(args, getattr(args, '_argv', []), interactive=interactive):
            raise ValueError('Dependency setup was not accepted; build stopped before conversion')
        if not args.sdk:
            args.sdk = detected_sdk(args)


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def prerequisites(args, interactive=False):
    errors, tools = [], {}
    args.workspace = ensure_external(args.workspace, "build workspace")
    raw = game_input(args.data_files, interactive)
    data = None
    if raw:
        try:
            print("Checking the installed file tree, containers and reference SHA-256 hashes...", flush=True)
            with Progress("Verifying game files, containers and reference hashes"):
                args.input_report = input_check.inspect(raw, args.stage, args.allow_data_differences,
                                                       notify=print, choose=choose_installation if interactive else None,
                                                       hasher=input_lock(args))
            input_check.display(args.input_report)
            errors.extend(args.input_report["errors"])
            data = Path(args.input_report["data_files"])
            args.known_game_data = check_known_game_data(args, data)
            if inside(args.workspace, data) or inside(data, args.workspace):
                errors.append("Use an output workspace separate from the game installation, not its parent or child")
        except (OSError, ValueError) as exc:
            errors.append(str(exc))
    else:
        errors.append("Supply --data-files '/path/to/Morrowind/Data Files'")
    if errors:
        raise ValueError("Game inputs need attention before tool setup:\n  - " + "\n  - ".join(errors))
    args.data_files = data
    if args.stage == "aga":
        prepare_dependencies(args, interactive)
        for module, package in (("setuptools", "setuptools>=68 (provides distutils for PyFFI)"),
                                ("PIL", "Pillow"), ("numpy", "numpy"),
                                ("scipy", "scipy"), ("pyffi", "PyFFI==2.2.3"),
                                ("fast_simplification", "fast-simplification==0.2.0")):
            if importlib.util.find_spec(module) is None:
                errors.append(f"Python dependency missing: {package}; use this Python environment's pip")
        if not errors and not args.plan:
            try:
                with Progress('Checking the PyFFI TES3 reader'):
                    from prepare_scenery import check_nif_reader
                    check_nif_reader()
            except (ImportError, AttributeError, ValueError, OSError) as exc:
                errors.append(f'PyFFI reader check failed: {exc}. Run --autoinstall to install required Python dependencies, including setuptools; see docs/BUILD_DEPENDENCIES.md')
        if errors:
            raise ValueError('Python conversion dependencies need attention:\n  - ' + '\n  - '.join(errors))
        for name in ("make",):
            tools[name] = executable(name, name, errors)
        for name in ("ffmpeg", "xdftool", "rdbtool"):
            tools[name] = executable(getattr(args, name), name, errors)
        sdk = select_sdk(args, interactive, game_data=data)
        if sdk:
            args.sdk = ensure_external(sdk, "SDK")
            tools["m68k-amigaos-gcc"] = executable(args.sdk / "bin/m68k-amigaos-gcc", "m68k-amigaos-gcc", errors)
            tools["vasmm68k_mot"] = executable(args.vasm or args.sdk / "bin/vasmm68k_mot", "vasmm68k_mot", errors)
            if not (args.sdk / "m68k-amigaos/ndk-include/exec/exec_lib.i").is_file():
                errors.append("SDK NDK includes missing: m68k-amigaos/ndk-include/exec/exec_lib.i")
        else:
            errors.append("Amiga SDK missing: use the download command above or supply --sdk /path/to/sdk")
        try:
            runtime_sources()
        except (OSError, ValueError) as exc:
            errors.append(str(exc))
        archive = args.upstream_archive
        if archive:
            args.upstream_archive = ensure_external(archive, "upstream source archive")
            if not args.upstream_archive.is_file() or sha256(args.upstream_archive) != UPSTREAM_SHA256:
                errors.append(f"AmiQuake archive must match SHA-256 {UPSTREAM_SHA256}")
        if interactive:
            print("Map tools: https://github.com/ericwa/ericw-tools/releases/tag/v0.18.1")
        tool_dir = build_versions.find_quake_tools(args)
        if not tool_dir and not all(shutil.which(name) for name in ('qbsp', 'vis', 'light')):
            tool_dir = ask(args.quake_tools, "ericw-tools bin directory (blank to use PATH)", interactive)
        for name in ("qbsp", "vis", "light"):
            value = Path(tool_dir).expanduser() / name if tool_dir else name
            tools[name] = executable(value, name, errors)
        qcc = build_versions.find_qcc(args)
        if not qcc:
            print("QuakeC compiler missing. Ubuntu/Debian package: sudo apt-get install fteqcc")
            print("FTEQCC: https://fte.triptohell.info/ | Reference compiler: https://github.com/id-Software/Quake-Tools")
            qcc = ask(args.qcc, "QuakeC compiler path (qcc-host, qcc or fteqcc)", interactive)
        tools["qcc"] = executable(qcc, "QuakeC compiler", errors)
        if tools["qcc"] and not args.plan:
            print(f"Checking QuakeC compilation with {tools['qcc']} (temporary files only)...", flush=True)
            try:
                check_quakec(tools['qcc'], args.hands)
                print("  [ok] AmiWind QuakeC compiled; program version and system-variable CRC match the engine.")
            except (OSError, ValueError, subprocess.SubprocessError) as exc:
                errors.append(f"QuakeC compile check failed: {exc}")
        try:
            args.fallback_font = fallback_font(args.fallback_font, args.tools_dir)
            tools['console-font'] = str(args.fallback_font)
        except ValueError as exc:
            errors.append(str(exc))
    args.version_report = build_versions.report(args, tools) if args.stage == "aga" else []
    if errors:
        raise ValueError("Prerequisites need attention:\n  - " + "\n  - ".join(errors) + "\nSee docs/LINUX_BUILD.md.")
    args.data_files = data
    return tools


def dry_run_prerequisites(args, interactive=False):
    errors, tools = [], {}
    args.workspace = ensure_external(args.workspace, "build workspace")
    if args.data_files:
        raise ValueError("The asset-free --dry-run does not accept --data-files")
    prepare_dependencies(args, interactive)
    sdk = select_sdk(args, interactive)
    if not sdk:
        raise ValueError("Amiga SDK missing: use the download command above or supply --sdk for the asset-free native compile")
    args.sdk = ensure_external(sdk, "SDK")
    for name, value in (("make", "make"), ("m68k-amigaos-gcc", args.sdk / "bin/m68k-amigaos-gcc"),
                        ("vasmm68k_mot", args.vasm or args.sdk / "bin/vasmm68k_mot")):
        tools[name] = executable(value, name, errors)
    if importlib.util.find_spec("amitools") is None:
        errors.append("Python dependency missing: amitools==0.8.1")
    if not (args.sdk / "m68k-amigaos/ndk-include/exec/exec_lib.i").is_file():
        errors.append("SDK NDK includes are missing")
    runtime_sources()
    args.version_report = build_versions.report(args, tools)
    if errors:
        raise ValueError("Dry-run prerequisites need attention:\n  - " + "\n  - ".join(errors))
    return tools


def dry_run_commands(args, run):
    common = ["--sdk", str(args.sdk)] + (["--vasm", str(args.vasm)] if args.vasm else [])
    binary = run / "engine" / RUNTIME_BUILD_DIR / "build/AmiQuakeGCC"
    return [
        ("engine", [sys.executable, str(ROOT / "tools/build_aga.py"), "engine", *common,
                    "--out", str(run / "engine"), "--hands", args.hands, "--jobs", str(resolve_jobs(args.jobs))]),
        ("dry-run-image", [sys.executable, str(ROOT / "tools/build_dry_run.py"), *common,
                           "--engine", str(binary), "--out", str(run / "image"),
                           *(["--kickstart-file", str(args.kickstart_file)] if getattr(args,"kickstart_file",None) else []),
                           *(["--amiga-libs", str(args.amiga_libs), "--amiga-libs-policy", getattr(args, "amiga_libs_policy", "warn")]
                             if getattr(args,"amiga_libs",None) else [])]),
    ]


def world_layout_ceiling():
    """Fixed survey ceiling of the recorded world layout (BUILD-WORLD-LAYOUT-DRIFT-32)."""
    layout = json.loads((ROOT / "config/world-region-refinements.json").read_text(encoding="utf-8"))
    return layout["survey_source_triangle_limit"]


def world_flora_status(args):
    """World flora (trees and grass) in this build: (built, status).

    Built by default in every real AGA image build, like the NPC gallery: every
    release since v0.0.28 ships it (BUILD-FLORA-OPTIN-32). Only explicit
    --no-tree-sprites (debugging only) removes it. Asset-free dry runs,
    terrain-only builds and the rc3 image recovery (which predates flora)
    make no image with flora.
    """
    if getattr(args, 'dry_run', False):
        return False, 'asset-free'
    if getattr(args, 'stage', 'aga') != 'aga':
        return False, 'not applicable (terrain stage)'
    if getattr(args, 'recover_image_from', None):
        return False, 'not part of the rc3 image recovery'
    if getattr(args, 'no_tree_sprites', False):
        return False, 'disabled by --no-tree-sprites'
    if getattr(args, 'miniwind', False):
        return False, 'not built (--miniwind: world flora needs the open-world terrain)'
    return True, 'enabled'


def hand_catalog_status(args):
    """Per-race first-person hands in this build: (built, status).

    Every release since v0.0.29 ships the catalogue (progs/hands/*.mdl,
    gfx/hand-models.awh, gfx/hand-torch.awt); it was made outside the builder
    until BUILD-HANDS-NOT-BUILT-32. Built in every real AGA image build with
    3D hands; sprite hands, asset-free dry runs, terrain-only builds and the
    rc3 image recovery (which predates it) make none.
    """
    if getattr(args, 'dry_run', False):
        return False, 'asset-free'
    if getattr(args, 'stage', 'aga') != 'aga':
        return False, 'not applicable (terrain stage)'
    if getattr(args, 'recover_image_from', None):
        return False, 'not part of the rc3 image recovery'
    if getattr(args, 'hands', '3d') != '3d':
        return False, 'not applicable (sprite hands)'
    return True, 'enabled'


def hand_catalog_steps(args, tool, run, jobs=None):
    """The catalogue step and its image option (BUILD-HANDS-NOT-BUILT-32).

    Converted against the runtime palette the image step derives from the
    scene palette (UI bank reserved), with the authored source topology:
    byte-identical to what v0.0.31 shipped.
    """
    step = ('hand-catalog', tool('prepare_hand_catalog.py', '--data-files', args.data_files,
            '--palette', run / 'intro-scene/id1/gfx/palette.lmp', '--runtime-palette',
            '--topology', 'source', '--out', run / 'hand-catalog', '--jobs', resolve_jobs(args.jobs if jobs is None else jobs)))
    return step, ['--hand-catalog', str(run / 'hand-catalog')]


def harvest_status(args):
    """Harvestable mushrooms in this build: (built, status).

    Every release since v0.0.29 ships them (id1/harvest-*.txt,
    progs/harvest/*.mdl); they were made outside the builder until
    BUILD-HARVEST-NOT-BUILT-32. Built in every real AGA image build; only
    explicit --no-harvest (debugging only) removes them. Asset-free dry runs,
    terrain-only builds and the rc3 image recovery (which predates it) make none.
    """
    if getattr(args, 'dry_run', False):
        return False, 'asset-free'
    if getattr(args, 'stage', 'aga') != 'aga':
        return False, 'not applicable (terrain stage)'
    if getattr(args, 'recover_image_from', None):
        return False, 'not part of the rc3 image recovery'
    if getattr(args, 'no_harvest', False):
        return False, 'disabled by --no-harvest'
    return True, 'enabled'


def harvest_steps(args, tool, run, jobs):
    """The harvest step and its image option (BUILD-HARVEST-NOT-BUILT-32).

    Shared mushroom models against the runtime palette (the scene palette after
    the census) and every original exterior placement; the image step derives
    the per-map plan from the maps it ships, gates and admits them.
    """
    step = ('harvest', tool('harvest_build.py', 'prepare', '--data-files', args.data_files,
            '--palette', run / 'intro-scene/id1/gfx/palette.lmp', '--out', run / 'harvest',
            '--jobs', jobs))
    return step, ['--harvest', str(run / 'harvest')]


def town_selection(args):
    """The towns after Seyda and Balmora this build imports (BUILD-EXTRA-TOWN-OPTIN-32).

    Every town config/towns.json marks "shipped_since" is part of the release
    and imported by every real AGA build (the Vivec Arena since v0.0.32), in
    table order; --extra-town adds towns not shipped yet, in command order.
    Only the debugging opt-outs --no-extra-town TOWN and --only-core-towns
    leave a shipped town out. Asset-free dry runs, terrain-only builds and the
    rc3 image recovery (which predates extra towns) import none.

    Returns {'towns': [...], 'shipped': [...], 'left_out': [...], 'status': text};
    contradictory options raise ValueError.
    """
    from town_config import shipped_extra_towns
    shipped = shipped_extra_towns()
    requested = list(dict.fromkeys(getattr(args, 'extra_town', None) or []))
    dropped = list(dict.fromkeys(getattr(args, 'no_extra_town', None) or []))
    only_core = getattr(args, 'only_core_towns', False)
    both = [town for town in requested if town in dropped]
    if both:
        raise ValueError('--extra-town and --no-extra-town both name ' + ', '.join(both) + '; use one')
    if only_core and (requested or dropped):
        raise ValueError('--only-core-towns already leaves out every extra town; drop --extra-town/--no-extra-town')
    record = {'shipped': shipped}
    if getattr(args, 'miniwind', False):
        if requested or dropped or only_core:
            raise ValueError('--miniwind builds one town (--miniwind-town); drop --extra-town/--no-extra-town/'
                             '--only-core-towns')
        town = getattr(args, 'miniwind_town', None) or 'balmora'
        if town == 'balmora':
            return dict(record, towns=[], left_out=list(shipped),
                        status='none; left out: ' + (', '.join(shipped) or 'none') + ' (--miniwind: Balmora only)')
        left = [t for t in shipped if t != town]
        return dict(record, towns=[town], left_out=left,
                    status=town + '; left out: ' + (', '.join(left) or 'none') + ' (--miniwind-town ' + town + ')')
    if getattr(args, 'dry_run', False):
        return dict(record, towns=[], left_out=[], status='asset-free')
    if getattr(args, 'stage', 'aga') != 'aga':
        return dict(record, towns=[], left_out=[], status='not applicable (terrain stage)')
    if getattr(args, 'recover_image_from', None):
        return dict(record, towns=[], left_out=[], status='not part of the rc3 image recovery')
    left_out = list(shipped) if only_core else [town for town in shipped if town in dropped]
    towns = [town for town in shipped if town not in left_out]
    towns += [town for town in requested if town not in towns]
    parts = [', '.join(towns) or 'none']
    if left_out:
        parts.append('left out for debugging: ' + ', '.join(left_out)
                     + (' (--only-core-towns)' if only_core else ' (--no-extra-town)'))
    status = '; '.join(parts) + (' (shipped by default)' if towns and towns == shipped and not left_out else '')
    return dict(record, towns=towns, left_out=left_out, status=status)


# Legacy region-map stage of each town (tools/import_town.py): balmora, else town-<id>.
def legacy_town_stage(town):
    return 'balmora' if town == 'balmora' else 'town-' + town


def chim_native_towns(args, builder=None):
    """CHIM areas built without their legacy region-map chain (CHIM-LEGACY-CHAIN-33): every CHIM
    area except Seyda Neen (its frame takes the recorded legacy stage) and towns named with
    --legacy-area (debugging/legacy only)."""
    builder = builder or getattr(args, 'builder_options', None) or resolve_builder(args)
    if builder['builder'] != 'chim' or getattr(args, 'chim_native_towns', 'off') != 'on':
        return []  # v0.0.35: EXPERIMENTAL, off by default (--chim-native-towns on)
    legacy = set(getattr(args, 'legacy_areas', None) or [])
    return [town for town in builder['chim_areas'] if town != 'seyda' and town not in legacy]


def chim_town_commands(args, builder, steps, tool, run, tools, jobs):
    """Replace each CHIM-native town's legacy chain stage by its chim-town stage (tools/chim_town.py,
    after the CHIM world): residents, frame entities, region table and door bank from the game data.
    The image takes them (--chim-town) and drops the legacy-map-only options for that town (the
    Balmora layout repair and its night-window scenery: the town has no legacy maps)."""
    towns = chim_native_towns(args, builder)
    # Extra towns not on CHIM ship nothing in a CHIM image (the image step leaves them out whole,
    # chim.frame_map.remove_towns_not_on_chim): their import is not run either (CHIM-LEGACY-CHAIN-33).
    if getattr(args, 'chim_native_towns', 'off') != 'on':
        return steps  # the legacy chains, as before (--chim-native-towns off, the v0.0.35 default)
    not_on_chim = {name for name, _ in steps if name.startswith('town-') and name[5:] not in builder['chim_areas']}
    steps = [(name, command) for name, command in steps if name not in not_on_chim]
    if not towns:
        return steps
    dropped = {legacy_town_stage(town) for town in towns}
    steps = [(name, command) for name, command in steps if name not in dropped]
    index = next(i for i, (name, _) in enumerate(steps) if name == 'chim') + 1
    steps[index:index] = [('chim-town-' + town, tool(
        'chim_town.py', '--town', town, '--data-files', args.data_files, '--scene', run / 'intro-scene',
        '--chim-world', run / 'chim-world', '--out', run / ('chim-town-' + town), '--ffmpeg', tools['ffmpeg'],
        '--jobs', jobs)) for town in towns]

    def image(command):
        command = [str(part) for part in command]
        if 'balmora' in towns:
            for option in ('--balmora-cache', '--balmora-scenery'):
                while option in command:
                    at = command.index(option)
                    del command[at:at + 2]
        for town in towns:
            command += ['--chim-town', str(run / ('chim-town-' + town))]
        return command
    return [(name, image(command) if name == 'image' else command) for name, command in steps]


def world_terrain_cache(args):
    """The per-map world terrain cache (development builds only; docs/BUILD_PROFILE.md).

    Release candidates and finals convert every map, like the from-scratch gate, unless
    --allow-release-reuse says that gate runs separately on the same commit.
    """
    if getattr(args, 'no_unit_cache', False):
        return []
    if not (re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+-dev[0-9]+', VERSION) or getattr(args, 'allow_release_reuse', False)):
        return []
    return ['--cache', args.workspace / 'cache/world-terrain-v1']


def stair_walk_scope(version, choice='auto'):
    """'all' or 'flights' for the image step's stair walk: --stair-walk all|flights as given;
    auto = 'all' for development (-devN) versions, 'flights' for release candidates and finals
    (owner decision 9 October 2026; a nightly full report builds with --stair-walk all)."""
    if choice in ('all', 'flights'):
        return choice
    if choice != 'auto':
        raise ValueError('--stair-walk must be auto, all or flights')
    return 'all' if re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+-dev[0-9]+', version) else 'flights'


def reuse_cache_fallback(reuse_from, workspace):
    """The cache folder of the --reuse-from run's workspace (RUN is WORKSPACE/build/NAME), or None when
    there is no such run, it has no cache folder, or it is this build's own workspace."""
    if not reuse_from:
        return None
    try:
        other = Path(reuse_from).expanduser().resolve().parent.parent / 'cache'
        own = (Path(workspace).expanduser().resolve() / 'cache')
        if not other.is_dir() or other == own:
            return None
    except OSError:
        return None
    return other


def media_file_cache(args, run, stage):
    """The per-file sound and movie cache of the media and intro stages (development builds only).

    Same rule as the world terrain cache: release candidates and finals convert every file,
    unless --allow-release-reuse says the from-scratch gate runs separately on the same commit.
    The hit and miss counts go to the run's profile folder for the build summary.
    """
    if getattr(args, 'no_media_cache', False):
        return []
    if not (re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+-dev[0-9]+', VERSION) or getattr(args, 'allow_release_reuse', False)):
        return []
    return ['--cache', storage_pool_dir(args), '--cache-report', run / 'profile' / 'file-cache' / f'{stage}.json']


def npc_lod_arguments(args, run, stage):
    """Near/far NPC model options (tools/npc_lod.py) for the stages that bake residents: only
    non-default choices, so default command lines stay unchanged, plus the asset pool on
    development builds (the media cache's rule, media_file_cache)."""
    if stage not in ('area', 'balmora', 'balmora-interiors') and not stage.startswith('town-'):
        return []
    import npc_lod
    options = npc_lod.resolve_options(args)
    pool = media_file_cache(args, run, stage)
    # Strings only: the commands go into build-state.json (BUILD-NPCLOD-PATH-ARG-34).
    return [str(item) for item in npc_lod.option_arguments(options) + (['--npc-model-pool', pool[1]] if pool else [])]


# Setup and report modes that check no build input: they print a note instead of stopping on a missing
# one (--check, --plan and --check-inputs still stop: they check what the build needs).
NO_CONVERSION_MODES = ('install_sdk', 'install_dependencies', 'versions', 'layout_selftest', 'estimate_world')


def seyda_source(args):
    """Where a CHIM build's Seyda Neen region maps come from: 'converted', 'recorded' or None (no Seyda
    frame maps: legacy builder, Seyda Neen not a CHIM area, other stages, asset-free dry runs)."""
    builder = getattr(args, 'builder_options', None) or resolve_builder(args)
    if (builder['builder'] != 'chim' or 'seyda' not in builder['chim_areas'] or getattr(args, 'stage', 'aga') != 'aga'
            or getattr(args, 'dry_run', False)):
        return None
    return 'recorded' if getattr(args, 'seyda_recorded', None) is not None else 'converted'


def seyda_terrain_cull_options(args):
    """['--seyda-terrain-cull', 'off'] when a CHIM build converts Seyda Neen from the data files: those
    region maps are only the frame maps' check reference and leave the image, and the canonical terrain
    cull cannot complete from scratch (BUILD-SEYDA-CULL-STABLE-32). Otherwise nothing (legacy unchanged)."""
    return ['--seyda-terrain-cull', 'off'] if seyda_source(args) == 'converted' else []


def chim_seyda_input(args):
    """Where a CHIM build's Seyda Neen comes from (seyda_source), with one line for a converted one.

    From v0.0.34 a CHIM build with Seyda Neen (the shipped default) needs no recorded input: the image step
    converts the Seyda Neen region maps from your own data (prepare_seyda_regions.convert_builder_scene,
    without the terrain visual cull) and the CHIM frame maps are checked against them (chim.frame_map:
    statics both ways, origin, harvest, actor contact) before they leave the image. `--seyda-recorded DIR`
    still installs the recorded v0.0.31 maps instead and checks them byte for byte (tools/recorded_stage.py;
    BUILD-SEYDA-REGEN-30)."""
    source = seyda_source(args)
    if source == 'converted' and not any(getattr(args, mode, False) for mode in NO_CONVERSION_MODES):
        print('Seyda Neen: converted from your data; the CHIM frame maps are checked against the converted '
              'region maps (no recorded input; --seyda-recorded DIR is optional)', flush=True)
    return source


def npc_model_arguments(args):
    """build_gallery.py options of the NPC model method; none for the default (whole)."""
    method = getattr(args, 'npc_models', 'whole') or 'whole'
    if method == 'whole':
        return []
    policy = getattr(args, 'npc_parts_policy', 'exact') or 'exact'
    cap = getattr(args, 'npc_parts_face_cap', 666) or 666
    if not (policy == 'exact' or (policy.startswith('levels') and policy[6:].isdigit() and 1 <= int(policy[6:]) <= 16)):
        raise ValueError('--npc-parts-policy must be exact or levelsN (N 1-16)')
    if not 64 <= cap <= 666:
        raise ValueError('--npc-parts-face-cap must be 64-666')
    cache = getattr(args, 'parts_cache', None) or args.workspace / 'cache/npc-parts-v1'
    return ['--npc-models', method, '--parts-cache', cache, '--npc-parts-policy', policy,
            '--npc-parts-face-cap', cap]


def commands(args, tools, run):
    """Include the NPC gallery and world flora in normal AGA builds.

    Only explicit --no-npc-gallery removes the gallery and only explicit
    --no-tree-sprites removes world flora; absence is never inferred from
    old scene contents. Both opt-outs are debugging-only: required game NPCs
    must never be removed by them. Asset-free dry runs use their separate recipe.
    """
    # One worker count for the whole plan: an explicit --jobs N exactly, auto
    # resolved once (BUILD-JOBS-RESOLVE-PER-STAGE-32).
    jobs = resolve_jobs(args.jobs)
    # --exclude and the older switches (--no-npc-gallery, --no-harvest) as one group list.
    from build_exclusions import fold as fold_exclusions
    groups = fold_exclusions(args)
    font_options = getattr(args, "font_options", None) or resolve_font_options(args)
    heap = getattr(args, "heap_options", None) or resolve_heap(args)
    py = sys.executable
    def tool(name, *items):
        return [py, str(ROOT / "tools" / name), *map(str, items)]
    work = run / "work"
    steps = [
        ("setup", tool("mwad.py", "setup", "--data-files", args.data_files, "--workspace", work, "--target", "a1200" if args.stage == "aga" else "a500")),
        ("terrain", tool("mwad.py", "convert", "--workspace", work)),
    ]
    if args.stage == "aga":
        binary = run / "engine" / RUNTIME_BUILD_DIR / "build/AmiQuakeGCC"
        steps += [
            ("scenery", tool("prepare_scenery.py", "--workspace", work, "--out", run / "scenery", "--jobs", jobs)),
            ("scene", tool("prepare_quake.py", "--workspace", work, "--scene", run / "scenery", "--out", run / "alias-scene", "--jobs", jobs,
                           *(['--fallback-font', args.fallback_font] if args.fallback_font else []))),
            ("bsp", tool("prepare_mesh_bsp.py", "--scene", run / "alias-scene", "--scenery", run / "scenery", "--out", run / "bsp-scene", "--jobs", jobs,
                *[part for name in ("qbsp", "vis", "light") for part in ("--" + name, tools[name])])),
            ("npcs", tool("prepare_npcs.py", "--data-files", args.data_files, "--scene", run / "bsp-scene", "--out", run / "npc-scene", "--ffmpeg", tools["ffmpeg"])),
            ("hands", tool("prepare_hands.py", "--data-files", args.data_files, "--scene", run / "npc-scene", "--out", run / "hands-scene", "--jobs", jobs)),
            ("interior", tool("prepare_interior.py", "--data-files", args.data_files, "--scene", run / "hands-scene", "--out", run / "interior-scene", "--jobs", jobs,
                *[part for name in ("qbsp", "vis", "light") for part in ("--" + name, tools[name])])),
            ("dialogue-lookup", tool("prepare_dialogue_lookup.py", "--data-files", args.data_files, "--out", run / "voice-lookup.json")),
            ("intro", tool("prepare_intro.py", "--jobs", jobs, "--data-files", args.data_files, "--scene", run / "interior-scene", "--out", run / "intro-scene", "--ffmpeg", tools["ffmpeg"], *media_file_cache(args, run, "intro"))),
            ("census", tool("prepare_census.py", "--data-files", args.data_files, "--scene", run / "intro-scene",
                "--jobs", jobs,
                *[part for name in ("qbsp", "vis", "light") for part in ("--" + name, tools[name])])),
            ("npc-gallery", tool("build_gallery.py", "--data-files", args.data_files,
                "--palette", run / "intro-scene/id1/gfx/palette.lmp", "--out", run / "npc-gallery",
                "--cache", getattr(args, "gallery_cache", None) or args.workspace / "cache/npc-gallery-v1",
                *(["--seed-run", args.gallery_seed_run] if getattr(args, "gallery_seed_run", None) else []),
                *npc_model_arguments(args),
                "--jobs", jobs,
                *[part for name in ("qbsp", "vis", "light") for part in ("--" + name, tools[name])])),
            ("area", tool("prepare_area.py", "--data-files", args.data_files, "--scene", run / "intro-scene",
                "--jobs", jobs, "--ffmpeg", tools["ffmpeg"],
                "--qbsp", tools["qbsp"], "--vis", tools["vis"], "--light", tools["light"])),
            ("balmora", tool("prepare_balmora.py", "--data-files", args.data_files, "--scene", run / "intro-scene",
                "--out", run / "balmora-work", "--jobs", jobs, "--ffmpeg", tools["ffmpeg"],
                "--qbsp", tools["qbsp"], "--vis", tools["vis"], "--light", tools["light"])),
            ("balmora-interiors", tool("prepare_balmora_interiors.py", "--data-files", args.data_files,
                "--scene", run / "intro-scene", "--jobs", jobs, "--ffmpeg", tools["ffmpeg"],
                "--qbsp", tools["qbsp"], "--vis", tools["vis"], "--light", tools["light"])),
            ("door-audio", tool("prepare_door_audio.py", "--data-files", args.data_files, "--scene", run / "intro-scene", "--ffmpeg", tools["ffmpeg"])),
            ("character", tool("prepare_character.py", "--jobs", jobs, "--data-files", args.data_files, "--scene", run / "intro-scene")),
            ("reading", tool("prepare_reading.py", "--data-files", args.data_files, "--scene", run / "intro-scene",
                "--bitmap-paper-ink", font_options["bitmap_paper_ink"])),
            ("opening-references", tool("prepare_opening_refs.py", "--data-files", args.data_files, "--scene", run / "intro-scene")),
            ("world-survey", tool("survey_vvardenfell.py", "--data-files", args.data_files,
                "--out", run / "world-survey", "--jobs", jobs,
                "--triangle-limit", world_layout_ceiling())),
            ("world-ui", tool("prepare_world_ui.py", "--data-files", args.data_files,
                "--survey", run / "world-survey", "--scene", run / "intro-scene")),
            ("actor-contact", tool("check_scene_actors.py", "--scene", run / "intro-scene", "--jobs", jobs,
                "--data-files", args.data_files, "--out", run / "actor-contact",
                "--ericw-bin", Path(tools['qbsp']).parent,
                "--canonical-land-source", run / "world-survey/terrain-source.npz",
                *(["--allow-known-actor-ground-findings", args.allow_known_actor_ground_findings]
                  if getattr(args, "allow_known_actor_ground_findings", None) else []),
                *(["--seyda-recorded", args.seyda_recorded] if getattr(args, "seyda_recorded", None) else []),
                *seyda_terrain_cull_options(args))),
            ("world-terrain", tool("prepare_world_regions.py", "--survey", run / "world-survey",
                "--data-files", args.data_files, "--scene", run / "intro-scene",
                "--out", run / "world-terrain", "--bindir", Path(tools['qbsp']).parent,
                "--jobs", jobs, *world_terrain_cache(args))),
            ("seam-audit", tool("seam_audit.py", "gate", "--data-files", args.data_files,
                "--out", run / "seam-audit.json", "--jobs", jobs)),
            ("world-scenery-assets", tool("world_scenery.py", "--data-files", args.data_files,
                "--out", run / "world-scenery-source", "--export-meshes",
                "--jobs", jobs)),
            ("world-scenery", tool("prepare_world_scenery.py", "--terrain", run / "world-terrain",
                "--scenery", run / "world-scenery-source/scenery",
                "--palette", run / "intro-scene/id1/gfx/palette.lmp",
                "--out", run / "world-scenery", "--jobs", jobs)),
            ("media", tool("prepare_media_assets.py", "--data-files", args.data_files, "--ffmpeg", tools["ffmpeg"], "--out", run / "media", "--jobs", jobs, *media_file_cache(args, run, "media"))),
            ("music", tool("prepare_music.py", "--data-files", args.data_files, "--ffmpeg", tools["ffmpeg"], "--out", run / "music", "--jobs", jobs)),
            ("engine", tool("build_aga.py", "engine", "--sdk", args.sdk, "--out", run / "engine", "--hands", args.hands, "--jobs", jobs,
                            *(["--vasm", args.vasm] if args.vasm else []),
                            # Only an asked heap adds an option: the default command line stays unchanged.
                            *(["--heap-mb", heap["heap_mb"]] if heap["selected_by"] != "engine default" else []))),
            ("image", tool("build_aga.py", "image", "--jobs", jobs, *(["--kickstart-file", args.kickstart_file] if getattr(args,"kickstart_file",None) else []), *(["--allow-known-actor-ground-findings", args.allow_known_actor_ground_findings] if getattr(args,"allow_known_actor_ground_findings",None) else []), *[part for fid in (getattr(args, "accept_known_stair_findings", None) or []) for part in ("--accept-known-stair-findings", fid)], *(["--intro-captions", args.intro_captions] if getattr(args,"intro_captions",None) else []), "--sdk", args.sdk, "--data-files", args.data_files, "--hands", args.hands, *(["--no-npc-gallery"] if args.no_npc_gallery else ["--gallery", run / "npc-gallery"]), "--scene", run / "intro-scene", "--world-scenery", run / "world-scenery", "--music", run / "music", "--media", run / "media", "--engine", binary, "--out", run / "image",
                *[part for name in ("qcc", "qbsp", "vis", "light", "xdftool", "rdbtool") for part in ("--" + name, tools[name])])),
        ]
        # Shipped towns (by default) and --extra-town towns convert in the same
        # scene chain, right after Balmora's interiors (BUILD-EXTRA-TOWN-OPTIN-32).
        towns = [(f'town-{town}', tool('import_town.py', '--town', town, '--data-files', args.data_files,
                  '--scene', run / 'intro-scene', '--out', run / f'{town}-work', '--jobs', jobs,
                  '--ffmpeg', tools['ffmpeg'], '--qbsp', tools['qbsp'], '--vis', tools['vis'], '--light', tools['light']))
                 for town in town_selection(args)['towns']]
        index = next(i for i, (name, _) in enumerate(steps) if name == 'balmora-interiors') + 1
        steps[index:index] = towns
        # Only a non-default vis mode adds an option: default command lines stay unchanged.
        vis_mode = getattr(args, 'vis_mode', 'fast')
        if vis_mode != 'fast':
            vis_steps = {'bsp', 'interior', 'census', 'area', 'balmora', 'balmora-interiors', 'actor-contact', 'world-terrain', 'image',
                         *(name for name, _ in towns)}
            steps = [(name, command + ['--vis-mode', vis_mode] if name in vis_steps else command)
                     for name, command in steps]
    if world_flora_status(args)[0]:
        image_index = next(i for i, (name, _) in enumerate(steps) if name == 'image')
        flora_steps = [
            ('world-flora-assets', tool('prepare_tree_sprites.py', '--data-files', args.data_files,
                '--palette', run / 'intro-scene/id1/gfx/palette.lmp',
                '--out', run / 'world-flora-assets', '--jobs', jobs)),
            ('world-flora', tool('prepare_world_flora.py', '--terrain', run / 'world-terrain',
                '--base', run / 'world-scenery', '--flora', run / 'world-flora-assets',
                '--palette', run / 'intro-scene/id1/gfx/palette.lmp',
                '--out', run / 'world-flora', '--jobs', jobs, '--collision-packing', 'adaptive')),
        ]
        steps[image_index:image_index] = flora_steps
        steps = [(name, command + ['--world-flora', str(run / 'world-flora'),
                      '--town-flora-source-index', str(run / 'scenery/scenery-index.json'),
                      '--town-flora-scene-report', str(run / 'alias-scene/scene-report.json')] if name == 'image' else command)
                 for name, command in steps]
    if harvest_status(args)[0]:
        step, options = harvest_steps(args, tool, run, jobs)
        image_index = next(i for i, (name, _) in enumerate(steps) if name == 'image')
        steps.insert(image_index, step)
        steps = [(name, command + options if name == 'image' else command) for name, command in steps]
    if hand_catalog_status(args)[0]:
        step, options = hand_catalog_steps(args, tool, run, jobs)
        image_index = next(i for i, (name, _) in enumerate(steps) if name == 'image')
        steps.insert(image_index, step)
        steps = [(name, command + options if name == 'image' else command) for name, command in steps]
    if args.stage == 'aga':
        image_options = ['--hidden-surface-cull', getattr(args, 'hidden_surface_cull', 'true'),
                         '--local-skybox', getattr(args, 'local_skybox', 'false'),
                         '--map-budget-policy', getattr(args, 'map_budget_policy', 'strict'),
                         # Seyda region conversion: same canonical LAND as actor-contact.
                         '--canonical-land-source', str(run / 'world-survey/terrain-source.npz'),
                         # Night window table sources: the scenery the towns came from.
                         '--town-scenery', str(run / 'scenery'),
                         '--balmora-scenery', str(run / 'balmora-work/scenery')]
        if not getattr(args, 'recover_image_from', None):
            # Measured bounded Balmora layout repair (since v0.0.27; the rc3 image
            # recovery predates it). Independent of world flora, which it used
            # to depend on (BUILD-FLORA-OPTIN-32).
            image_options += ['--balmora-cache', str(run / 'balmora-work')]
            if getattr(args, 'night_lamp_lightmaps', 'off') == 'on':
                image_options += ['--night-lamp-lightmaps']  # EXPERIMENTAL, off by default
        if getattr(args, 'shared_sky_source', None) is not None:
            image_options += ['--shared-sky-source', str(args.shared_sky_source.resolve())]
        if getattr(args, 'seyda_recorded', None) is not None:
            image_options += ['--seyda-recorded', str(args.seyda_recorded)]
        image_options += seyda_terrain_cull_options(args)
        # Entity tracker against the last release (BUILD-DRESSING-EXCLUDED-32): a placement the
        # release had and this image lacks stops the image step unless the loss is accepted.
        if not getattr(args, 'no_entity_baseline', False) and ENTITY_BASELINE.is_file():
            image_options += ['--entity-baseline', str(ENTITY_BASELINE)]
        if getattr(args, 'accept_entity_loss', None):
            image_options += ['--accept-entity-loss', args.accept_entity_loss]
        if getattr(args, 'live_logs', False):
            image_options += ['--live-logs']
        if getattr(args, 'amiga_libs', None) is not None:
            image_options += ['--amiga-libs', str(args.amiga_libs),
                              '--amiga-libs-policy', getattr(args, 'amiga_libs_policy', 'warn')]
        steps = [(name, command + image_options if name == 'image' else command)
                 for name, command in steps]
    if getattr(args, 'skip_dressing', False):
        steps = [(name, command + ['--skip-dressing'] if name in ('interior', 'census', 'area') else command)
                 for name, command in steps]
    if args.stage == 'aga':
        steps = [(name, command + npc_lod_arguments(args, run, name)) for name, command in steps]
    if args.stage == 'aga':
        builder = getattr(args, 'builder_options', None) or resolve_builder(args)
        if builder['builder'] == 'chim':
            # The CHIM world (docs/chim/WORLD_FORMAT.md) of the selected areas, validated, with
            # its statistics (docs/chim/STATS.md). The palette is census's (BUILD-PALETTE-RACE-32).
            image_index = next(i for i, (name, _) in enumerate(steps) if name == 'image')
            steps.insert(image_index, ('chim', tool(
                'chim_build.py', *[part for area in builder['chim_areas'] for part in ('--area', area)],
                '--data-files', args.data_files, '--palette', run / 'intro-scene/id1/gfx/palette.lmp',
                '--out', run / 'chim-world', '--qbsp', tools['qbsp'],
                # opt-in CHIM texture effects (none by default; docs/chim/TEXTURE_EFFECTS.md)
                *[part for e in builder.get('chim_texture_effects', []) for part in ('--texture-effect', e['path'])],
                # opt-in CHIM settings (none by default): detail budget, large-model cut, a debug closer view
                *chim_stage_options(args),
                # how the CHIM world is lit (docs/chim/LIGHTING.md; default hybrid)
                '--lighting-type', builder.get('chim_lighting_type') or 'hybrid',
                '--unit-cache', args.workspace / 'cache/chim-units', '--jobs', jobs, '--validate', '--stats',
                # Seyda Neen's frame reads the legacy scene chain of the same run (chim.seyda).
                '--legacy-run', run,
                # the CHIM heap gate probes the engine's target ABI sizes (chim.heap)
                '--sdk', args.sdk,
                # private -devN tests only: accepted known stair findings (checked in main)
                *[part for fid in (getattr(args, 'accept_known_stair_findings', None) or [])
                  for part in ('--accept-known-stair-findings', fid)],
                # Payload parity: the image's harvest removal and town flora (CHIM-PAYLOAD-PARITY-33).
                *(['--harvest', run / 'harvest'] if any(n == 'harvest' for n, _ in steps) else []),
                *(['--flora', run / 'world-flora-assets'] if any(n == 'world-flora-assets' for n, _ in steps)
                  else []))))
            # The tracker data of this build's own CHIM world (tools/cell_progress_build.py), default on, in its own
            # stage with its own key: run inside the CHIM stage, its code (and the docs it can read) keyed the whole CHIM
            # world, or, left out, under-declared it (BUILD-CHIM-KEY-UNDERDECLARED-35). It never fails the build.
            if not getattr(args, 'no_cell_progress', False):
                steps.insert(image_index + 1, ('cell-progress', tool(
                    'cell_progress_build.py', '--out', run / 'toolkit', '--chim-world', run / 'chim-world',
                    '--data-files', args.data_files, '--never-fail')))
            # The image adds it as one more world volume, gated for classic FFS (tools/chim/disk.py).
            steps = [(name, command + ['--chim-world', str(run / 'chim-world'), '--chim-lighting-type',
                                       builder.get('chim_lighting_type') or 'hybrid'] if name == 'image' else command)
                     for name, command in steps]
            steps = chim_town_commands(args, builder, steps, tool, run, tools, jobs)
    if args.no_npc_gallery:
        steps = [(name, command) for name, command in steps if name != "npc-gallery"]
    if getattr(args, 'miniwind', False) and args.stage == 'aga':
        steps = miniwind_commands(args, steps)
    # Quick test builds (--exclude): one table says what each group skips (tools/build_exclusions.py).
    if groups and args.stage == 'aga' and not getattr(args, 'dry_run', False):
        import build_exclusions
        if 'music' in groups:
            # The image takes no soundtrack: drop --music DIR (the stage does not run).
            steps = [(name, _drop_option(command, '--music') if name == 'image' else command) for name, command in steps]
        lost = build_exclusions.removes_placements(groups)
        if lost and not getattr(args, 'accept_entity_loss', None):
            # Placements the group removes are recorded against the release baseline with this reason.
            reason = build_exclusions.summary(lost)
            steps = [(name, command + ['--accept-entity-loss', reason] if name == 'image' and '--entity-baseline' in command
                      else command) for name, command in steps]
        steps = build_exclusions.apply(steps, groups, run=run, area_cells=getattr(args, 'closure_cells', None),
                                       data_files=args.data_files,
                                       closure_groups=getattr(args, 'unreferenced_groups', None))
    # A direct start (tools/direct_start.py): the image resolves the start against its final maps.
    start = getattr(args, 'direct_start', None)
    character = getattr(args, 'quick_character_record', None)
    if args.stage == 'aga' and not getattr(args, 'dry_run', False) and (start or getattr(args, 'quick_character', None)):
        extra = (['--direct-start', start.text] if start else []) + \
            (['--quick-character', ','.join([character['race'], character['class'], character['name']])]
             if getattr(args, 'quick_character', None) else [])
        steps = [(name, command + extra if name == 'image' else command) for name, command in steps]
    # --skip-census (configure_skip_census): the image writes aw_skip_census 1 into the game's defaults.
    if args.stage == 'aga' and not getattr(args, 'dry_run', False) and \
            (getattr(args, 'skip_census_record', None) or {}).get('on'):
        steps = [(name, command + ['--skip-census'] if name == 'image' else command) for name, command in steps]
    return steps


PRERENDERED_ACTIONS = ('list', 'verify', 'prune')


def storage_pool_dir(args):
    """The storage pool folder: --storage-pool-dir > build config storage_pool_dir > AMIWIND_STORAGE_POOL >
    WORKSPACE/cache/asset-pool-v1 (tools/storage_pool.resolve_dir)."""
    import storage_pool
    from build_font_options import configured_storage_pool_dir
    config, base = configured_storage_pool_dir(args)
    return storage_pool.resolve_dir(args.workspace, getattr(args, 'storage_pool_dir', None), config, base)[0]


def storage_pool_record(args, run, log=print):
    """Check once per build that the pool can be hard-linked with RUN (tools/storage_pool.setting); cached on ARGS.
    No links: one loud warning, and the callers copy instead (never a failed build, BUILD TIME RULE 5)."""
    record = getattr(args, '_storage_pool_record', None)
    if record is None:
        import storage_pool
        from build_font_options import configured_storage_pool_dir
        config, base = configured_storage_pool_dir(args)
        pool, origin = storage_pool.resolve_dir(args.workspace, getattr(args, 'storage_pool_dir', None), config, base)
        record = storage_pool.setting(pool, origin, run, log=log)
        args._storage_pool_record = record
    return record


def storage_pool_enabled(args, version=None):
    setting = getattr(args, 'storage_pool', 'auto')
    if setting == 'auto':
        return bool(re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+-dev[0-9]+', version or VERSION))
    return setting == 'on'


def pool_outputs(args, run, played=False):
    """After a passed build: store the run's outputs (and this build's new prerendered entries) once in the
    storage pool and link them back read-only (tools/storage_pool.py). Never fails the build."""
    if not storage_pool_enabled(args) or getattr(args, 'dry_run', False):
        return None
    import storage_pool
    record = storage_pool_record(args, run, log=lambda line: print(line, flush=True))
    if not record['links'] and storage_pool._can_protect():
        # Pooling across file systems or mounts would add a copy, never save one.
        summary = {'schema': storage_pool.SCHEMA, 'apply': False, 'skipped_reason': record['warning'], 'pool': record}
        try:
            (Path(run) / 'profile').mkdir(parents=True, exist_ok=True)
            (Path(run) / 'profile' / 'storage-pool.json').write_bytes(
                (json.dumps(summary, indent=1, sort_keys=True) + chr(10)).encode('utf-8'))
        except OSError:
            pass
        return summary
    folders = [path for path in sorted(Path(run).iterdir())
               if path.name not in ('logs', 'profile', 'scratch') and not (played and path.name == 'image')]
    try:
        stored = json.loads((Path(run) / 'profile' / 'prerendered.json').read_text())
        folders += [Path(stored['dir']) / relative / 'files' for relative in (stored.get('stored') or {}).values()]
    except (OSError, ValueError, KeyError, TypeError):
        pass
    try:
        summary = storage_pool.adopt(storage_pool_dir(args), folders, apply=True,
                                     log=lambda line: print(line, flush=True))
        report = json.dumps(summary, indent=1, sort_keys=True) + chr(10)
        (Path(run) / 'profile' / 'storage-pool.json').write_text(report)
        return summary
    except OSError as exc:
        print(f'[warning] Storage pool not updated ({exc}); the build passed and its files are unchanged.', flush=True)
        return None


def prerendered_action(values):
    """--prerendered list|verify|prune DIR (tools/prerendered.py); nothing is built."""
    if len(values) != 2:
        raise ValueError(f'--prerendered {values[0]} takes the store folder: --prerendered {values[0]} DIR')
    import prerendered
    return prerendered.main([values[0], values[1]])


def without_option(command, flag):
    """command without `flag VALUE` (every occurrence)."""
    out, skip = [], False
    for part in command:
        if skip:
            skip = False
        elif str(part) == flag:
            skip = True
        else:
            out.append(part)
    return out


def miniwind_commands(args, steps):
    """The AmiWind "MiniWind" Playtester Build plan (tools/miniwind.py): the
    normal CHIM plan without the stages it leaves out, and an image step that
    ships Balmora only, with the boot notice and logo lines generated from the
    stages that remain. Recorded on args for the build receipt."""
    import miniwind
    scope = getattr(args, 'miniwind_scope', None) or miniwind.DEFAULT_SCOPE
    town = getattr(args, 'miniwind_town', None) or miniwind.TOWN
    debug = getattr(args, 'miniwind_debug', False)
    steps, left_out = miniwind.plan(steps, scope, town)
    # Stages the build type never generates: world flora, the extra towns and the
    # NPC gallery (the exterior scope sets --no-npc-gallery, which drops it earlier).
    for name in ('world-flora-assets', 'world-flora', 'npc-gallery',
                 *('town-' + t for t in town_selection(args)['left_out'])):
        left_out.setdefault(name, miniwind.omitted(name, scope, town))
    names = [name for name, _ in steps]
    if 'chim' not in names:
        raise ValueError('--miniwind needs the CHIM builder stage')
    if town != miniwind.TOWN and not {'town-' + town, 'chim-town-' + town} & set(names):
        raise ValueError('--miniwind-town %s: the plan has no stage for it (chim-town-%s or town-%s)' % (town, town, town))
    feature_line = miniwind.features_line(names, scope, town)
    miniwind.data_file(feature_line, town, debug=debug)  # the engine's limits, before any stage runs
    description = getattr(args, 'miniwind_description', None)
    image = []
    for name, command in steps:
        if name == 'image':
            # Seyda Neen's region conversion and the open world are not built; the
            # release entity baseline would count every Seyda placement as lost.
            for flag in ('--world-scenery', '--canonical-land-source', '--entity-baseline', '--gallery'):
                command = without_option(command, flag)
            if town != miniwind.TOWN:
                # no Balmora in another town's sandbox: no layout repair, no Balmora night-window scenery
                for flag in ('--balmora-cache', '--balmora-scenery'):
                    command = without_option(command, flag)
            command = [*command, *([] if '--no-npc-gallery' in command else ['--no-npc-gallery']),
                       '--miniwind', '--miniwind-features', feature_line,
                       *(['--miniwind-description', description] if description else []),
                       *(['--miniwind-boot', args.miniwind_boot] if getattr(args, 'miniwind_boot', None) else []),
                       # only a non-default scope adds an option: the full scope's command stays as it was
                       *([miniwind.SCOPE_OPTION, scope] if scope != miniwind.DEFAULT_SCOPE else []),
                       *([miniwind.TOWN_OPTION, town] if town != miniwind.TOWN else []),
                       *([miniwind.DEBUG_OPTION] if debug else []),
                       *(['--default-draw-distance', str(args.chim_draw_distance)]
                         if getattr(args, 'chim_draw_distance', None) else [])]
        image.append((name, command))
    args.miniwind_record = miniwind.record(names, left_out, description, scope, town, debug,
                                           debug_settings(args))
    return image


def chim_stage_options(args):
    """chim_build.py options of the opt-in CHIM settings (--chim-detail-budget, --chim-cut-models-over,
    --chim-draw-distance); none by default, so a default command line stays unchanged."""
    out = []
    if getattr(args, 'chim_detail_budget', None):
        out += ['--detail-budget', args.chim_detail_budget]
    if getattr(args, 'chim_cut_models_over', None) is not None:
        out += ['--cut-models-over', str(args.chim_cut_models_over)]
    if getattr(args, 'chim_draw_distance', None):
        out += ['--draw-distance', str(args.chim_draw_distance)]
    return out


def debug_settings(args):
    """What a DEBUG ONLY MiniWind build changes from a playtest (recorded in its receipts)."""
    out = {}
    if getattr(args, 'chim_draw_distance', None):
        out['draw_distance'] = args.chim_draw_distance
    if getattr(args, 'chim_detail_budget', None):
        out['detail_budget'] = args.chim_detail_budget
    if getattr(args, 'chim_cut_models_over', None) is not None:
        out['cut_models_over'] = args.chim_cut_models_over
    if getattr(args, 'accept_known_stair_findings', None):
        out['accepted_stair_findings'] = list(args.accept_known_stair_findings)
    return out


def _drop_option(command, flag):
    if flag not in command:
        return command
    index = command.index(flag)
    return command[:index] + command[index + 2:]


def execute(steps, run, metadata):
    if metadata.get('compiler_jobs', 1) > 1 and not metadata.get('serial_stages', False):
        from build_parallel import execute_parallel
        return execute_parallel(steps, run, metadata, ROOT)
    run.mkdir(parents=True, exist_ok=False)
    (run / "logs").mkdir()
    receipt = {**metadata, "status": "running", "steps": []}
    def save():
        temporary = run / "build-state.tmp"
        temporary.write_text(json.dumps(receipt, indent=2) + "\n")
        temporary.replace(run / "build-state.json")
    save()
    import build_profile
    profile = build_profile.start(run, steps, metadata)
    for number, (name, command) in enumerate(steps, 1):
        log = run / "logs" / f"{number:02}-{name}.log"
        title = name + " (pre-baking in-game character models...)" if name == "npc-gallery" else name
        section(f"Build [{number}/{len(steps)}]: {title}")
        print(f"Log: {log}", flush=True)
        entry = {"name": name, "command": command, "status": "running", "log": str(log),
                 "jobs": metadata.get("compiler_jobs", 1)}
        receipt["steps"].append(entry)
        save()
        start = time.monotonic()
        try:
            with log.open("w") as output:
                with Progress(f"[{number}/{len(steps)}] {name}"), live_log(log):
                    from build_parallel import THREAD_LIMITS
                    from build_scratch import stage_environment
                    subprocess.run(profile.command(number, name, command, metadata.get('compiler_jobs', 1)),
                                   cwd=ROOT, stdout=output, stderr=subprocess.STDOUT, check=True,
                                   env=dict(os.environ, **THREAD_LIMITS, **stage_environment(run), PYTHONUNBUFFERED='1',
                                            AMIWIND_BUILD_JOBS=str(metadata.get('compiler_jobs', 1))))
        except (OSError, subprocess.CalledProcessError, KeyboardInterrupt) as exc:
            status = "cancelled" if isinstance(exc, KeyboardInterrupt) else "failed"
            entry.update(status=status, elapsed_seconds=round(time.monotonic() - start, 3))
            profile.finished(name, entry)
            receipt["status"] = status
            save()
            profile.close(receipt)
            if isinstance(exc, KeyboardInterrupt):
                print(f"Build cancelled. Earlier results and logs retained in {run}", flush=True)
                raise
            raise RuntimeError(f"{name} failed. Earlier results are retained. Read {log}; use a new --name after fixing the problem.") from exc
        entry.update(status="passed", elapsed_seconds=round(time.monotonic() - start, 3))
        profile.finished(name, entry)
        save()
    receipt["status"] = "passed"
    save()
    profile.close(receipt)


def provenance(args, tools):
    """Capture inputs and build choices once, before any conversion stage runs."""
    def hashes(base, accept):
        return {str(path.relative_to(base)): sha256(path)
                for path in sorted(base.rglob("*")) if path.is_file() and accept(path)}
    builder = getattr(args, "builder_options", None) or resolve_builder(args)
    miniwind = getattr(args, "miniwind", False) and not args.dry_run and args.stage == "aga"
    extra = {"build_type": getattr(args, "miniwind_record", None)} if miniwind else {}
    exterior = miniwind and getattr(args, "miniwind_scope", None) == "exterior"
    mw_town = (getattr(args, "miniwind_town", None) or "balmora") if miniwind else "balmora"
    return {
        "schema": "amiwind-build-receipt-v1", "runtime_version": VERSION,
        **extra,
        "npc_gallery": "asset-free" if args.dry_run else
            "omitted (--miniwind-scope exterior: quick playtest, no NPC gallery)" if exterior else
            "omitted (--miniwind PARTIAL-AREA test)" if miniwind else
            ("disabled by --no-npc-gallery" if args.no_npc_gallery else "enabled"),
        "recipe": "asset-free-test-compile-v1" if args.dry_run else f"miniwind-{mw_town}-exterior-chim-v1" if exterior
            else f"miniwind-{mw_town}-chim-v1" if miniwind
            else "seyda-neen-prison-v1" if args.stage == "aga" else "seyda-neen-terrain-v1",
        "excluded_content": __import__('build_exclusions').record(getattr(args, 'exclude_groups', None) or []),
        "direct_start": ({**args.direct_start.record(), 'summary': __import__('direct_start').summary(args.direct_start)}
                         if getattr(args, 'direct_start', None) is not None else None),
        "quick_character": getattr(args, 'quick_character_record', None),
        "skip_census": getattr(args, 'skip_census_record', None),
        "miniwind_preset": getattr(args, 'miniwind_preset_record', None),
        "reference_closure": ({'groups': getattr(args, 'unreferenced_groups', []),
                               'cells': getattr(args, 'closure_cells', None)}
                              if 'unreferenced' in (getattr(args, 'exclude_groups', None) or []) else None),
        "npc_anim": getattr(args, "npc_anim", "idle"),
        "npc_models": getattr(args, "npc_models", "whole"),
        "stage": args.stage, "hands": args.hands if args.stage == "aga" else None,
        "python": sys.version, "data_files": str(args.data_files), "tools": tools,
        "version_comparison": getattr(args, "version_report", []),
        "hidden_surface_cull": {"enabled": getattr(args, "hidden_surface_cull", "true") == "true",
                                "stage": "final serialized static exterior surfaces",
                                "scope": "certified hidden surfaces; not all-interior acceptance"},
        "exterior_sky": {"local_skybox": getattr(args, "local_skybox", "false") == "true",
                         "shared_sky_source": str(args.shared_sky_source.resolve()) if getattr(args, "shared_sky_source", None) else None,
                         "stage": "final serialized exterior sky before hidden surfaces and compaction",
                         "unknown_maps": "preserved and recorded"},
        "mesh_reduction": {"texinfo_snap_texels": getattr(args, "texinfo_snap", None),
                           "scenery_reduce_error": getattr(args, "scenery_reduce", None),
                           "scenery_reduce_texels": getattr(args, "scenery_reduce_texels", None),
                           "default": "both off; see docs/MESH_TIPS_AND_TRICKS.md"},
        "compiler_jobs": resolve_jobs(args.jobs),
        "jobs_requested": getattr(args, "jobs_requested", args.jobs),
        "vis_mode": getattr(args, "vis_mode", "fast"),
        "amiga_libs": str(args.amiga_libs) if getattr(args, "amiga_libs", None) else None,
        "seyda_recorded": str(args.seyda_recorded) if getattr(args, "seyda_recorded", None) else None,
        "seyda_recorded_not_recommended": getattr(args, "seyda_recorded", None) is not None,
        "extra_towns": town_selection(args)['towns'],
        "extra_town_selection": town_selection(args),
        "serial_stages": args.serial_stages,
        'world_flora': {'requested': world_flora_status(args)[0],
                        'status': world_flora_status(args)[1],
                        'policy_sha256': sha256(ROOT / 'config/world-flora.json') if world_flora_status(args)[0] else None},
        'hand_catalog': {'requested': hand_catalog_status(args)[0], 'status': hand_catalog_status(args)[1]},
        'harvest': {'requested': harvest_status(args)[0], 'status': harvest_status(args)[1]},
        "font_options": getattr(args, "font_options", None) or resolve_font_options(args),
        # The game heap (--heap-mb / build config heap_mb), with its warning when above the safe size.
        "heap": getattr(args, "heap_options", None) or resolve_heap(args),
        # The exterior world pipeline (legacy region maps or the CHIM world) and, for CHIM,
        # its own version and the world format it writes.
        "builder": builder["builder"], "chim_version": builder["chim_version"],
        "world_format": builder["world_format"], "builder_options": builder,
        "input_check": getattr(args, "input_report", None),
        "npc_root_rule": getattr(args, "npc_root_rule", "legacy"),
        "tool_sha256": {name: sha256(path) for name, path in tools.items()},
        "input_sha256": {} if args.dry_run else input_hashes(args),
        "known_inputs": known_inputs_record(args),
        "source_sha256": hashes(ROOT, lambda path:
            (path.suffix in (".py", ".c", ".h", ".patch", ".qc", ".asm", ".sh", ".cfg")
             or path.name in ("Makefile", "VERSION", "CHIM_VERSION", "pyproject.toml"))
            and path.relative_to(ROOT).parts[0] != "out"
            and "__pycache__" not in path.parts),
    }


def input_lock(args):
    """The build's one input lock: amiwind-inputs.lock in the workspace (private)."""
    lock = getattr(args, '_input_lock', None)
    if lock is None:
        import known_inputs
        workspace = ensure_external(args.workspace, "build workspace")
        lock = known_inputs.InputLock(None if getattr(args, 'plan', False) else workspace / known_inputs.LOCK_NAME,
                                      getattr(args, 'check_hashes', 'core'))
        args._input_lock = lock
        if lock.mode == 'off':
            print('[WARNING] --check-hashes off: input files are NOT verified against known versions or the reference.', flush=True)
    return lock


def check_known_game_data(args, data):
    """Known-inputs verdicts of the masters and archives, at the start of the build."""
    import known_inputs
    report = known_inputs.check_game_data(data, input_lock(args), getattr(args, 'game_data_policy', 'warn'),
                                          input_report=getattr(args, 'input_report', None))
    for text in known_inputs.report_lines(report):
        print(text, flush=True)
    if report['warnings']:
        print(f"[warning] {len(report['warnings'])} game data file(s) not known (listed above); "
              'they are used (--game-data-policy warn). See docs/KNOWN_INPUTS.md', flush=True)
    args.known_game_data = report
    return report


def input_hashes(args):
    """SHA-256 of every game input, from the build's input lock (one hashing path)."""
    lock = input_lock(args)
    paths = [path for path in sorted(args.data_files.rglob("*"))
             if path.is_file() and is_game_input(path.relative_to(args.data_files))]
    lock.prepare(paths)
    return {str(path.relative_to(args.data_files)): lock.sha256(path) for path in paths}


def check_known_kickstart(args):
    """Verdict of --kickstart-file (informational: the launcher checks the ROM too)."""
    rom = getattr(args, 'kickstart_file', None)
    if not rom or not Path(rom).is_file():
        return None
    import known_inputs
    lock = input_lock(args)
    lock.prepare([rom], core=True)
    record = known_inputs.classify('kickstart-rom', Path(rom).name, rom, lock.sha256(rom), lock.table)
    lock.note_verdict(rom, record)
    print('Kickstart ROM: ' + known_inputs.line(record), flush=True)
    return record


def known_inputs_record(args):
    """The known-inputs block of the build receipt and summary."""
    if getattr(args, '_input_lock', None) is None and not getattr(args, 'kickstart_file', None):
        return None
    kickstart = check_known_kickstart(args)
    lock = input_lock(args)
    return {'check_hashes': lock.summary(), 'game_data': getattr(args, 'known_game_data', None),
            'amiga_libs': getattr(args, 'known_amiga_libs', None), 'kickstart': kickstart}


def estimate_world(args):
    """--estimate-world: the builder's whole-world estimate (tools/world_estimate.py)."""
    import world_estimate
    raw = game_input(args.data_files, sys.stdin.isatty())
    if raw is None:
        raise ValueError("Supply --data-files with your Morrowind installation root")
    if args.estimate_sample and not args.quake_tools:
        raise ValueError('--estimate-sample needs --quake-tools (ericw-tools directory with qbsp, vis, light)')
    options = ['estimate', '--data-files', str(installed_game_path(raw)), '--out', str(args.estimate_world)]
    if args.jobs:
        options += ['--jobs', str(resolve_jobs(args.jobs))]
    if args.estimate_sample:
        options += ['--sample-convert', str(args.estimate_sample), '--quake-tools', str(args.quake_tools)]
        if args.sdk:
            options += ['--sdk', str(args.sdk)]
    return world_estimate.main(options)


def miniwind_mode(scope=None, town=None, debug=False):
    """The build summary's mode line of a MiniWind build."""
    import miniwind
    scope = scope or miniwind.DEFAULT_SCOPE
    tag = miniwind.label(scope)
    return (miniwind.NAME + ' (' + ('DEBUG ONLY, not a playtest; ' if debug else '')
            + miniwind.partial_area(scope, town or miniwind.TOWN) + (', ' + tag if tag else '') + ')')


def configure_area_closure(args):
    """The cells an area build's reference closure covers (--exclude-unreferenced): a MiniWind
    build's Balmora (its exterior grid and, in the full scope, its rooms). Sets args.closure_cells."""
    args.closure_cells = None
    if 'unreferenced' not in (getattr(args, 'exclude_groups', None) or []):
        return None
    from content_closure import area_cells
    cells = area_cells(getattr(args, 'miniwind_town', None) or 'balmora')
    if getattr(args, 'miniwind_scope', None) == 'exterior':
        cells = [cell for cell in cells if cell.startswith('cell:')]
    args.closure_cells = cells
    return cells


def configure_direct_start(args):
    """--direct-to-game-map / --quick-character (tools/direct_start.py), checked before any work:
    -devN only, a real AGA image, the start point in the build. Sets args.direct_start,
    args.quick_character_record and, for an area build's reference closure, args.closure_cells."""
    import direct_start
    from project_version import require_private_test_version
    used = [flag for flag, value in ((direct_start.OPTION, getattr(args, 'direct_to_game_map', None)),
                                     (direct_start.CHARACTER_OPTION, getattr(args, 'quick_character', None)))
            if value is not None]
    args.direct_start = None
    args.quick_character_record = direct_start.parse_character(None)
    if used:
        require_private_test_version(VERSION, used)
        if args.stage != 'aga' or args.dry_run:
            raise ValueError(' and '.join(used) + ' need a real AGA image build')
        if getattr(args, 'quick_character', None) is not None:
            if getattr(args, 'direct_to_game_map', None) is None and not args.miniwind:
                raise ValueError(direct_start.CHARACTER_OPTION + ' needs ' + direct_start.OPTION + ' or a MiniWind build')
            args.quick_character_record = direct_start.parse_character(args.quick_character)
    if getattr(args, 'direct_to_game_map', None) is not None:
        start = direct_start.parse(args.direct_to_game_map)
        if args.miniwind:
            towns, world = ['balmora'], False
        else:
            towns, world = ['seyda', 'balmora', *town_selection(args)['towns']], True
        scope = direct_start.build_scope(towns, world, 'interiors' in (getattr(args, 'exclude_groups', None) or []),
                                         args.miniwind_scope if args.miniwind else None)
        args.direct_start = direct_start.check(start, scope)
        if args.miniwind and getattr(args, 'miniwind_description', None) is None:
            # The startup screen's "Scene:" line names the start point unless a description is given.
            import miniwind
            args.miniwind_description = miniwind.check_description(start.describe())
        print('Direct start: ' + direct_start.summary(start), flush=True)
    if args.direct_start is not None and 'unreferenced' in (getattr(args, 'exclude_groups', None) or []):
        # A direct start's closure covers the start area, room or cell.
        args.closure_cells = direct_start.closure_cells(args.direct_start)
    return args.direct_start


def configure_skip_census(args):
    """--skip-census / --no-skip-census, resolved before any work: default on for MiniWind and other
    direct-start builds without --quick-character, off otherwise; on for a normal build is -devN only.
    Sets args.skip_census_record ({'on', 'source'}) for the image step and the receipt."""
    quick = bool(getattr(args, 'miniwind', False)) or getattr(args, 'direct_start', None) is not None
    explicit = getattr(args, 'skip_census', None)
    if explicit is None:
        on = quick and getattr(args, 'quick_character', None) is None
        source = ('default: quick test build' if on else
                  'default: --quick-character gives the character' if quick else 'default: normal build')
    else:
        on, source = bool(explicit), '--skip-census' if explicit else '--no-skip-census'
    if on and not quick:
        from project_version import require_private_test_version
        require_private_test_version(VERSION, ['--skip-census'])
        if args.stage != 'aga' or args.dry_run:
            raise ValueError('--skip-census needs a real AGA image build')
    args.skip_census_record = {'on': on, 'source': source}
    if on:
        print('Quick character screen: New Game skips the ship and the census (%s)' % source, flush=True)
    return args.skip_census_record


def configure_miniwind(args):
    """--miniwind: the AmiWind "MiniWind" Playtester Build (tools/miniwind.py).

    A private -devN test only (refused for release candidates and finals, as
    the private-test waivers are); an AGA image build with the CHIM builder and
    Balmora as its only CHIM area. Options that contradict a Balmora-only
    build stop here, before any work."""
    import miniwind
    from project_version import require_private_test_version
    if not args.miniwind:
        raise ValueError(miniwind.DESCRIPTION_OPTION + '/' + miniwind.SCOPE_OPTION + '/' + miniwind.TOWN_OPTION
                         + '/' + miniwind.DEBUG_OPTION + ' require ' + miniwind.OPTION)
    town = miniwind.check_town(getattr(args, 'miniwind_town', None) or miniwind.TOWN)
    debug = bool(getattr(args, 'miniwind_debug', False))
    scope = getattr(args, 'miniwind_scope', None)
    scope = miniwind.check_scope(miniwind.DEFAULT_SCOPE if scope is None else scope)
    require_private_test_version(VERSION, [miniwind.OPTION])
    if args.stage != 'aga' or args.dry_run or args.recover_image_from or args.estimate_world:
        raise ValueError('--miniwind is a real AGA image build (not --stage terrain, --dry-run, '
                         '--recover-image-from or --estimate-world)')
    if getattr(args, 'seyda_recorded', None) is not None:
        raise ValueError('--miniwind builds no Seyda Neen; drop --seyda-recorded')
    if getattr(args, 'builder', None) == 'legacy':
        raise ValueError('--miniwind is a pure CHIM build; drop --builder legacy')
    areas = list(dict.fromkeys(getattr(args, 'chim_areas', None) or []))
    if areas and areas != [town]:
        raise ValueError('--miniwind holds %s only; drop --chim-area %s' % (
            town, ', '.join(a for a in areas if a != town)))
    args.builder, args.chim_areas = 'chim', [town]
    args.miniwind_scope, args.miniwind_town, args.miniwind_debug = scope, town, debug
    if getattr(args, 'chim_draw_distance', None) is not None:
        # a stated closer view: debugging only, never in a playtest
        if not debug:
            raise ValueError('--chim-draw-distance is DEBUG ONLY: add ' + miniwind.DEBUG_OPTION)
        if not 128 <= args.chim_draw_distance <= 540:
            raise ValueError('--chim-draw-distance must be 128..540 (a closer view than the default 540)')
    if miniwind.label(scope):
        # The exterior scope implies --no-npc-gallery (every MiniWind plan leaves the gallery out).
        args.no_npc_gallery = True
    args.miniwind_description = miniwind.check_description(args.miniwind_description)
    print('Build type: ' + miniwind.NAME + ' | ' + ('DEBUG ONLY, not a playtest | ' if debug else '')
          + miniwind.partial_area(scope, town), flush=True)
    print('MiniWind scope: ' + scope + (' (' + miniwind.label(scope) + ')' if miniwind.label(scope) else ''),
          flush=True)
    if args.miniwind_description:
        print('Startup screen: ' + miniwind.SCENE_PREFIX + args.miniwind_description, flush=True)


def check_payload(argv):
    """--check-payload RUN: the image step's payload preflight alone (read only) on RUN's staged payload,
    with the image command recorded in RUN/build-state.json (tools/payload_preflight.py)."""
    if len(argv) != 1:
        print('Usage: build.py --check-payload RUN', file=sys.stderr)
        return 2
    run = Path(argv[0])
    state = json.loads((run / 'build-state.json').read_text(encoding='utf-8'))
    step = next((s for s in state.get('steps', []) if s.get('name') == 'image'), None)
    command = step and step.get('command') or []
    script = next((i for i, part in enumerate(command) if Path(part).name == 'build_aga.py'), None)
    if script is None or command[script + 1:script + 2] != ['image']:
        print('No image step command in ' + str(run / 'build-state.json'), file=sys.stderr)
        return 2
    return subprocess.call([sys.executable, str(Path(__file__).resolve().parent / 'build_aga.py'),
                            *command[script + 1:], '--payload-preflight-only'])


def main(argv=None):
    # Also cover direct Python invocations and subsequent environment re-exec.
    os.environ['PYTHONUNBUFFERED'] = '1'
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(line_buffering=True)
    argv = list(sys.argv[1:] if argv is None else argv)
    # Read-only commands on run folders (docs/BUILD_PROFILE.md): live progress and the profiler.
    if argv[:1] == ['status']:
        import build_progress
        return build_progress.main(argv[1:])
    if argv[:1] == ['--check-payload']:
        return check_payload(argv[1:])
    if argv[:1] == ['--reuse-report']:
        # Read only: every stage a --reuse-from run did not reuse, EXPECTED or UNEXPECTED (tools/reuse_report.py).
        import reuse_report
        return reuse_report.main(argv[1:])
    if argv[:1] == ['--reuse-plan']:
        # Read only, seconds: the reuse preflight of a run against this checkout (tools/reuse_report.py).
        import reuse_report
        return reuse_report.plan_main(argv[1:])
    if argv[:1] == ['profile']:
        import build_profile
        return build_profile.main(argv[1:], prog='build.py profile')
    if argv[:1] == ['--check-entry']:
        # Read only, seconds: the worker entry check (tools/entry_check.py, docs/BUILD_CACHE.md "Entry check").
        import entry_check
        return entry_check.main(argv[1:], workspace_default=ROOT / 'out', pool_for=storage_pool_dir)
    p = parser()
    args = p.parse_args(argv)
    args._argv = argv
    # Import guard on every build (BUILD-IMAGE-STALE-PYTHONPATH-35): builder code only from this source tree;
    # other builder trees on PYTHONPATH (an old copy in a container image) are dropped before any stage runs.
    import entry_check
    refused = entry_check.guard_imports(ROOT)
    if refused:
        p.exit(1, 'Error: ' + refused + '\n')
    # The animation kit (docs/ANIMKIT.md): --anim-kit on (default) = the react+full profile unless --npc-anim names one.
    if getattr(args, "npc_anim", None) is None:
        args.npc_anim = ANIM_KIT_PROFILES[getattr(args, "anim_kit", "on")]
    if args.layout_selftest:
        # Asset-free and read-only for the checkout: dummy payloads in an always-removed scratch folder.
        import layout_selftest
        found = [(name, find_executable(getattr(args, name))) for name in ('xdftool', 'rdbtool')]
        return layout_selftest.main([part for name, path in found if path for part in ('--' + name, path)])
    # One worker count per build (BUILD-JOBS-RESOLVE-PER-STAGE-32): an explicit
    # --jobs N exactly, automatic resolved here once; provenance, the scheduler
    # and every stage share it.
    args.jobs_requested = args.jobs
    if args.jobs is None:
        args.jobs = resolve_jobs(None)
    # NPC root-node rule: stage code names AMIWIND_NPC_ROOT_RULE, so it is part of every NPC stage's key.
    os.environ['AMIWIND_NPC_ROOT_RULE'] = args.npc_root_rule
    # Resident animation kit profile (tools/npc_anim.py reads AMIWIND_NPC_ANIM; part of the stage cache identity).
    if getattr(args, 'npc_anim', 'idle') != 'idle':
        os.environ['AMIWIND_NPC_ANIM'] = args.npc_anim
        if not getattr(args, 'host_plan', False):  # a host plan prints JSON only
            print(f'NPC animation kit: {args.npc_anim} (docs/ANIMATION.md)', flush=True)
    else:
        os.environ.pop('AMIWIND_NPC_ANIM', None)
    # Converter workers read these from the environment (off unless given).
    from scenery_reduce import apply_options as apply_scenery_reduce_options
    apply_scenery_reduce_options(args)
    # Item cost history for longest-first pools (tools/build_costs.py): scheduling only.
    from build_costs import ENV as COST_HISTORY_ENV
    os.environ.setdefault(COST_HISTORY_ENV, str(Path(args.workspace).resolve() / 'cache' / 'item-costs'))
    # Image-step per-map pass results by content (tools/pass_cache.py): development builds, and release
    # candidates and finals with --allow-release-reuse (the from-scratch gate runs separately), so a late
    # image-step failure resumes from the finished maps (BUILD-IMAGE-NO-RESUME-33); otherwise every pass
    # runs on every map.
    from pass_cache import ENV as PASS_CACHE_ENV, setting as pass_cache_setting
    pass_cache_value = pass_cache_setting(VERSION, args.workspace, getattr(args, 'allow_release_reuse', False))
    if getattr(args, 'rebuild_unit', ''):
        from pass_cache import REBUILD_ENV
        os.environ[REBUILD_ENV] = args.rebuild_unit  # stage workers read it (pass_cache.forced)
    if pass_cache_value == 'off':
        os.environ[PASS_CACHE_ENV] = 'off'
    else:
        os.environ.setdefault(PASS_CACHE_ENV, pass_cache_value)
    # What the image step's stair walk covers (owner decision 9 October 2026): every step and
    # ramp in development builds and nightly full reports, only the steps of flights (the rows
    # that can fail the gate) in release candidates and finals.
    STAIR_WALK_ENV = 'AMIWIND_STAIR_WALK'  # tools/stair_walk.py SCOPE_ENV
    stair_scope = stair_walk_scope(VERSION, getattr(args, 'stair_walk', 'auto'))
    os.environ[STAIR_WALK_ENV] = stair_scope
    if not getattr(args, 'host_plan', False):  # a host plan prints JSON only
        print('Stair walk: ' + ('every step and ramp' if stair_scope == 'all' else 'flight steps only (release build)')
              + ' (--stair-walk ' + getattr(args, 'stair_walk', 'auto') + ')', flush=True)
    if getattr(args, 'legacy_areas', None):
        print('WARNING: --legacy-area ' + ', '.join(args.legacy_areas) + ': legacy region maps are built for a CHIM '
              'town (legacy/debugging only; default builds have one Balmora, on CHIM).', flush=True)
    try:
        from chim_town import NATIVE_ENV
        native = chim_native_towns(args) if getattr(args, 'stage', 'aga') == 'aga' and not args.dry_run else []
        os.environ[NATIVE_ENV] = ','.join(native)
    except ValueError:
        pass  # contradictory builder options are reported by the plan itself
    # Per-file caches of the --reuse-from run's workspace, read-only, when it is another workspace
    # (a new volume starts with an empty pool: BUILD-CACHE-PER-WORKSPACE-33).
    from file_cache import FALLBACK_ENV
    fallback = reuse_cache_fallback(getattr(args, 'reuse_from', None), args.workspace)
    if fallback:
        os.environ.setdefault(FALLBACK_ENV, str(fallback))
        print(f'Per-file caches: also reading the --reuse-from workspace cache {fallback} (read-only).', flush=True)
    if args.no_npc_gallery:
        print("WARNING: --no-npc-gallery is for debugging builds only. All NPC assets required by the game remain required; this flag omits only the inspection gallery.", flush=True)
    if args.no_tree_sprites:
        print("WARNING: --no-tree-sprites is for debugging builds only. World flora (trees, grass and reeds, "
              "shipped in every release since v0.0.28) is left out, so this image does not match a release; "
              "maps that place flora (such as reused Seyda Neen maps) stop the image step.", flush=True)
    elif args.tree_sprites:
        print("Note: --tree-sprites has no effect; world flora is built by default.", flush=True)
    if args.no_harvest:
        print("WARNING: --no-harvest is for debugging builds only. Harvestable mushrooms (shipped in every "
              "release since v0.0.29) are left out, so this image does not match a release.", flush=True)
    if args.no_extra_town or args.only_core_towns:
        print("WARNING: " + ("--only-core-towns" if args.only_core_towns else "--no-extra-town") + " is for "
              "debugging builds only. Towns the release ships (config/towns.json shipped_since) are left out, "
              "so this image does not match a release.", flush=True)
    from town_config import shipped_extra_towns
    for town in dict.fromkeys(args.extra_town):
        if town in shipped_extra_towns():
            print(f"Note: --extra-town {town} has no effect; {town} is shipped and built by default.", flush=True)
    summary = None
    try:
        if args.prerendered and args.prerendered[0] in PRERENDERED_ACTIONS:
            return prerendered_action(args.prerendered)
        if args.prerendered and len(args.prerendered) != 1:
            raise ValueError('--prerendered takes one store folder (or list|verify|prune DIR)')
        if args.tree_sprites and args.no_tree_sprites:
            raise ValueError('--tree-sprites (no effect, flora is the default) contradicts --no-tree-sprites; use one')
        # MiniWind test spots (config/miniwind-presets.json): --miniwind-preset NAME|list, --miniwind-NAME.
        import miniwind_presets
        if getattr(args, 'miniwind_preset', None) == 'list':
            print(miniwind_presets.listing())
            return 0
        if getattr(args, 'miniwind_preset', None) is not None:
            from project_version import require_private_test_version
            require_private_test_version(VERSION, ['--miniwind-preset ' + args.miniwind_preset])
            miniwind_presets.apply(args)
        if (args.miniwind or args.miniwind_description is not None or args.miniwind_scope is not None
                or args.miniwind_town is not None or args.miniwind_debug):
            configure_miniwind(args)  # refused for rc/final and contradictory options, before any work
        if args.chim_draw_distance is not None and not args.miniwind:
            raise ValueError('--chim-draw-distance is DEBUG ONLY: a --miniwind --miniwind-debug build')
        town_selection(args)  # contradictory town options stop here, before any work
        # Quick test builds: unknown/refused groups and rc/final versions stop here, before any work.
        import build_exclusions
        added = build_exclusions.miniwind_defaults(args)
        if added:
            print('MiniWind quick test defaults: ' + ', '.join(added) + ' (music and the shared sky stay; '
                  '--with-video / --exclude-unreferenced none turn them off)', flush=True)
        groups = build_exclusions.resolve(args, VERSION, area_build=bool(getattr(args, 'miniwind', False)))
        configure_area_closure(args)
        configure_direct_start(args)
        configure_skip_census(args)
        if groups:
            if args.stage != 'aga' or args.dry_run:
                raise ValueError('--exclude needs a real AGA image build')
            print('WARNING: quick test build (--exclude): ' + build_exclusions.summary(groups)
                  + '. Such an image does not match a release; the game and receipts say so.', flush=True)
        if args.host_plan:
            if args.autoinstall or args.install_dependencies or args.install_sdk or args.autorun_fs_uae:
                raise ValueError('--host-plan cannot be combined with installation or launch modes')
            print(json.dumps(setup_plan(args), indent=2))
            return 0
        if args.stage == 'aga' and not args.dry_run:
            # rc/final images contain the previous release (RELEASE-PREVIOUS-FIXES-MISSING-33)
            from previous_release import require_previous_release
            note = require_previous_release(ROOT, VERSION)
            if note:
                print(note, flush=True)
            # Seconds-long checks before any stage: cache ownership, free space, game data (build_preflight.py).
            import build_preflight
            from previous_release import is_release_version
            problems = build_preflight.run(args.workspace, getattr(args, 'data_files', None), space=False)
            space = build_preflight.free_space_problems(args.workspace)
            if is_release_version(VERSION):
                problems += space  # release builds stop; development builds only warn
            for warning in ([] if is_release_version(VERSION) else space):
                print('WARNING: build preflight: ' + warning, flush=True)
            if problems:
                raise ValueError('Build preflight failed before any stage:\n  ' + '\n  '.join(problems))
        if getattr(args, 'accept_known_stair_findings', None):
            from project_version import require_private_test_version
            require_private_test_version(VERSION, ['--accept-known-stair-findings'])
            from chim.known import known_stair_findings
            known_stair_findings(args.accept_known_stair_findings)
        if args.allow_known_actor_ground_findings:
            from project_version import require_private_test_version
            require_private_test_version(VERSION, ['--allow-known-actor-ground-findings'])
            if args.stage != 'aga' or args.dry_run:
                raise ValueError('--allow-known-actor-ground-findings requires a real AGA image build')
            from check_actor_ground import load_approved_report
            args.allow_known_actor_ground_findings = args.allow_known_actor_ground_findings.expanduser().resolve()
            load_approved_report(args.allow_known_actor_ground_findings)
        if getattr(args, 'seyda_recorded', None) is not None:
            if args.stage != 'aga':
                raise ValueError('--seyda-recorded requires an AGA image build')
            from recorded_stage import check_source
            args.seyda_recorded = args.seyda_recorded.expanduser().resolve()
            check_source(args.seyda_recorded)  # before any conversion: the pinned set or nothing
            print(SEYDA_RECORDED_WARNING, flush=True)
            print('Recorded-stage exception BUILD-SEYDA-REGEN-30: Seyda Neen from ' + str(args.seyda_recorded), flush=True)
        if args.amiga_libs is not None:
            if args.stage != 'aga':
                raise ValueError('--amiga-libs requires an AGA image build')
            import fpu_support
            args.amiga_libs = args.amiga_libs.expanduser().resolve()
            if not fpu_support.find(args.amiga_libs):
                print('FPU support library: none found in ' + str(args.amiga_libs) + ' (the build continues without one)', flush=True)
            else:
                # Verdicts at the start of the build; the image step applies the same policy.
                verdicts, warnings = fpu_support.inspect(args.amiga_libs, args.amiga_libs_policy, input_lock(args))
                args.known_amiga_libs = {'policy': args.amiga_libs_policy, 'files': verdicts, 'warnings': warnings}
                print(f'Amiga libraries (policy {args.amiga_libs_policy}):', flush=True)
                from known_inputs import line as known_line
                for row in verdicts:
                    print('  ' + known_line(row), flush=True)
        args.font_options = resolve_font_options(args)
        args.builder_options = resolve_builder(args)
        args.heap_options = resolve_heap(args)
        if args.heap_options["heap_warning"]:
            print("=" * 72 + "\nWARNING: " + args.heap_options["heap_warning"] + "\n" + "=" * 72, flush=True)
        if args.recover_image_from and args.builder_options['builder'] != 'legacy':
            # The rc3 image recovery restores a legacy-builder run; it predates CHIM (the default from v0.0.33).
            raise ValueError('--recover-image-from restores a legacy-builder run: add --builder legacy')
        chim_seyda_input(args)
        # Converter and image workers read the stair rule from the environment
        # (mesh_geometry.stair_mitigation_mode, stair_walk gate).
        from mesh_geometry_env import (export_chim_stream_statics, export_model_hull, export_npc_head_detail,
                                       export_stair_rules)
        export_stair_rules(args.font_options["follow_original_stair_rules"])
        export_model_hull(args.font_options["model_hull"])
        from lava import export_lava
        export_lava(args.font_options["lava"])
        export_chim_stream_statics(args.font_options["chim_stream_statics"])
        export_npc_head_detail(args.font_options["npc_head_detail"])
        if args.recover_image_from and (args.stage != 'aga' or args.dry_run or args.host_plan or args.check_inputs or args.versions or args.install_dependencies or args.install_sdk):
            raise ValueError('--recover-image-from requires an AGA build/check/plan, with a new run name')
        if args.reuse_from is not None:
            if args.no_profile or args.recover_image_from or args.dry_run:
                raise ValueError('--reuse-from needs a profiled AGA or terrain build (not --no-profile, '
                                 '--recover-image-from or --dry-run)')
            from build_cache import require_reuse_allowed
            require_reuse_allowed(VERSION, args.allow_release_reuse)
            args.reuse_from = args.reuse_from.expanduser().resolve()
        if args.prerendered:
            if args.no_profile or args.recover_image_from or args.dry_run:
                raise ValueError('--prerendered needs a profiled AGA or terrain build (not --no-profile, '
                                 '--recover-image-from or --dry-run)')
            from prerendered import parse_stages
            parse_stages(args.prerendered_stages)
        if sys.version_info < (3, 10):
            raise ValueError("Python 3.10 or newer is required")
        if args.yes and not args.autoinstall:
            raise ValueError('--yes requires --autoinstall')
        if args.estimate_sample and not args.estimate_world:
            raise ValueError('--estimate-sample requires --estimate-world')
        if args.estimate_world and (args.install_dependencies or args.install_sdk or args.versions or args.check_inputs
                                    or args.dry_run or args.autorun_fs_uae or args.recover_image_from):
            raise ValueError('--estimate-world runs alone; use it separately from setup, inventory and build modes')
        if args.autoinstall and (args.install_sdk or args.versions or args.check_inputs or args.stage != 'aga'):
            raise ValueError('--autoinstall is for AGA builds/checks; use it separately from setup-only or inventory modes')
        if sum((args.install_dependencies or args.install_sdk, args.versions, args.check_inputs)) > 1:
            raise ValueError("Use dependency/SDK setup, --versions or --check-inputs separately")
        emulator = None
        if args.kickstart_file and args.stage != 'aga':
            raise ValueError('--kickstart-file requires an AGA image build')
        if args.autorun_fs_uae:
            if args.stage != 'aga' or args.install_dependencies or args.install_sdk or args.versions or args.check_inputs:
                raise ValueError('--autorun-fs-uae requires an AGA build; setup-only and inventory modes do not create an HDF')
            from run_fs_uae import prepare_launch
            emulator = prepare_launch(args.kickstart_file, interactive=sys.stdin.isatty() and not args.yes)
            args.kickstart_file = emulator[1]
            # Keep an interactively selected/relative ROM across managed-venv re-exec.
            argv.extend(['--kickstart-file', str(emulator[1])])
            if args.check or args.plan:
                print('Check/plan mode: FS-UAE will not launch and no emulator configuration will be written.')
        if args.install_dependencies:
            if args.autoinstall:
                from setup_build import setup, use_environment
                use_environment(args, argv)
                args.sdk = args.sdk or detected_sdk(args)
                if args.data_files:
                    args.data_files = installed_game_path(args.data_files).expanduser().resolve()
                accepted = setup(args, argv, interactive=sys.stdin.isatty(), preview=args.plan or args.check)
                return 0 if accepted or args.plan or args.check else 1
            from install_dependencies import install
            return install(args)
        if args.install_sdk:
            if args.sdk:
                raise ValueError("--install-sdk installs into --tools-dir/sdk; use --sdk only to select an existing SDK for checks/builds")
            game = installed_game_path(args.data_files).expanduser().resolve() if args.data_files else None
            select_sdk(args, interactive=sys.stdin.isatty(), game_data=game, install_requested=True)
            return 0
        if not args.check_inputs and args.stage == 'aga':
            from setup_build import use_environment
            use_environment(args, argv)
        if args.autoinstall and args.plan:
            from setup_build import setup
            args.sdk = args.sdk or detected_sdk(args)
            if args.data_files:
                args.data_files = installed_game_path(args.data_files).expanduser().resolve()
            setup(args, argv, preview=True)
            return 0
        if args.estimate_world:
            return estimate_world(args)
        if args.versions:
            if not args.sdk:
                args.sdk = detected_sdk(args)
            build_versions.report(args)
            return 0
        if args.check_inputs:
            raw = game_input(args.data_files, sys.stdin.isatty())
            if raw is None:
                raise ValueError("Supply --data-files with your Morrowind installation root")
            print("Checking the installed file tree, containers and reference SHA-256 hashes...", flush=True)
            with Progress("Verifying game files, containers and reference hashes"):
                report = input_check.inspect(raw, args.stage, args.allow_data_differences,
                                             notify=print, choose=choose_installation if sys.stdin.isatty() else None,
                                             hasher=input_lock(args))
            input_check.display(report)
            args.input_report = report
            check_known_game_data(args, Path(report["data_files"]))
            for line in input_lock(args).summary_lines():
                print(line)
            input_lock(args).save()
            return 1 if report["errors"] else 0
        # Run names carry date, version, purpose and commit (tools/run_name.py, docs/BUILD_CACHE.md "Run names").
        import run_name
        commit, commit_origin = run_name.source_commit(ROOT, getattr(args, "source_commit", None))
        label = None
        if getattr(args, "miniwind", False) and not args.dry_run:
            # The town, DEBUG-ONLY and the exterior scope's label (tools/miniwind.py run_name).
            import miniwind
            label = miniwind.run_name("-" + args.miniwind_town if args.miniwind_town == miniwind.TOWN else "",
                                      args.miniwind_scope, args.miniwind_town, args.miniwind_debug)
        what = run_name.purpose(args.stage, args.dry_run, label)
        if getattr(args, 'direct_start', None) is not None:
            # The direct-start area in the purpose (tools/direct_start.py area_label).
            import direct_start
            what = (what + '-' + direct_start.area_label(args.direct_start))[:48].rstrip('-.')
        explicit = bool(args.name)
        if explicit:
            warning = run_name.check_explicit(args.name, VERSION, getattr(args, "any_run_name", False))
            if warning:
                print(warning, flush=True)
        else:
            args.name = run_name.default_name(VERSION, what, commit,
                                              exists=lambda name: (args.workspace / "build" / name).exists())
        if not run_name.NAME.fullmatch(args.name):
            raise ValueError("--name must be 1-100 letters, digits, dots, hyphens or underscores")
        args.run_name_record = run_name.record(args.name, VERSION, commit, commit_origin, what, explicit)
        print(f"Run name: {args.name}", flush=True)
        if getattr(args, 'developer_mode', False):
            # Developer mode (tools/entry_check.py): version, source, integration head, pool, run name, reuse.
            args.developer_mode_record = entry_check.check(
                ROOT, args.working_version, args.workspace, storage_pool_dir(args),
                getattr(args, 'source_commit', None), args.name, args.reuse_from,
                getattr(args, 'fingerprint_scope', 'units'), probe_pool=not (args.plan or args.check),
                accept_mismatch=args.accept_version_mismatch)
            print('\n'.join(entry_check.lines(args.developer_mode_record)), flush=True)
            if not args.developer_mode_record['ok']:
                raise ValueError('developer mode refused the build: '
                                 + '; '.join(args.developer_mode_record['refusals']))
        elif args.working_version or args.accept_version_mismatch:
            raise ValueError('--working-version and --accept-version-mismatch need --developer-mode '
                             '(or use build.py --check-entry)')
        if args.stage == "aga" and not args.dry_run:
            print("Original stair rules: " + ("on" if args.font_options["follow_original_stair_rules"] else "OFF (debugging)") +
                  " (" + args.font_options["follow_original_stair_rules_selected_by"] + ")", flush=True)
            print("Model hulls: " + args.font_options["model_hull"] +
                  " (" + args.font_options["model_hull_selected_by"] + ")", flush=True)
            print("Lava: " + args.font_options["lava"] +
                  " (" + args.font_options["lava_selected_by"] + ")", flush=True)
            print("NPC heads: " + args.font_options["npc_head_detail"] +
                  " (" + args.font_options["npc_head_detail_selected_by"] + ")", flush=True)
            print("Bitmap paper ink: " + args.font_options["bitmap_paper_ink"] +
                  " (" + args.font_options["selected_by"] +
                  "); preferred TTF conversion and dialogue/menu fonts unchanged.")
            print("World flora (trees and grass): " + world_flora_status(args)[1])
            print("Per-race first-person hands: " + hand_catalog_status(args)[1])
            print("Harvestable mushrooms: " + harvest_status(args)[1])
            print("Extra towns: " + town_selection(args)['status'])
            print("Content: " + __import__('build_exclusions').summary(args.exclude_groups))
        tools =(dry_run_prerequisites if args.dry_run else prerequisites)(args, interactive=sys.stdin.isatty())
        if not args.dry_run and args.stage == 'aga':
            # The direct start against the owner's masters: the cell exists, the character is playable.
            import direct_start
            if getattr(args, 'direct_start', None) is not None:
                direct_start.check_cell_exists(args.direct_start, args.data_files)
            if getattr(args, 'quick_character', None) is not None:
                args.quick_character_record = direct_start.parse_character(args.quick_character, args.data_files)
        recovery = None
        if args.recover_image_from:
            from recover_image import inspect_run
            with Progress('Checking retained rc3 conversion for image recovery'):
                recovery = inspect_run(args, ROOT)
        run = ensure_external(args.workspace / "build" / args.name, "build run")
        print(f"Prerequisites passed. Scope: {'asset-free test compile' if args.dry_run else args.stage}; data: {args.data_files}")
        if args.check:
            print("Checks completed. No build outputs created. Individual assets are validated during conversion; target performance is not tested here.")
            return 0
        if run.exists():
            raise ValueError(f"Build already exists: {run}; choose a new --name")
        steps = dry_run_commands(args, run) if args.dry_run else commands(args, tools, run)
        if recovery:
            from recover_image import recovery_commands
            steps = recovery_commands(steps, args.recover_image_from.resolve(), run)
            args.serial_stages = True  # Two dependent stages; engine retains its job budget.
        if args.plan:
            for name, command in steps:
                print(name + ": " + shlex.join(command))
            if getattr(args, 'miniwind_record', None):
                record = args.miniwind_record
                print(record['name'] + ': ' + record['partial_area'])
                print('Left out: ' + '; '.join(name + ' (' + why + ')' for name, why in record['left_out'].items()))
                print('Boot notice: ' + ' / '.join(record['notice']))
                print('MiniWind scope: ' + record['scope'] + (' (' + record['label'] + ')' if record['label'] else ''))
            return 0
        mode = 'AGA image recovery (retained rc3 conversion)' if recovery else 'asset-free dry run (not playable)' if args.dry_run else miniwind_mode(args.miniwind_scope, args.miniwind_town, args.miniwind_debug) if args.miniwind else 'AGA conversion and image' if args.stage == 'aga' else 'terrain conversion'
        summary = BuildSummary(run, VERSION, mode)
        with Progress("Recording input, tool and source checksums"):
            metadata = provenance(args, tools)
        metadata['build_started_at'] = summary.started_at
        metadata["jobs_warning"] = jobs_warning(getattr(args, "jobs_requested", args.jobs))
        if metadata["jobs_warning"]:
            print(metadata["jobs_warning"], flush=True)  # once per build; recorded in build-state and summary
        summary.record_environment(metadata)
        summary.known_inputs = metadata.get('known_inputs')
        lock = getattr(args, '_input_lock', None)
        lock_path = lock.save() if lock is not None else None
        if lock_path:
            # Later stages take input hashes from the lock (known_inputs.input_sha256).
            os.environ['AMIWIND_INPUTS_LOCK'] = str(lock_path)
        if recovery:
            if metadata['input_sha256'] != recovery.pop('input_sha256'):
                raise ValueError('Game inputs changed since rc3; refusing mixed-input recovery')
            metadata['recovery'] = recovery
        metadata['profile'] = not args.no_profile
        if getattr(args, 'developer_mode_record', None) is not None:
            metadata['developer_mode'] = args.developer_mode_record  # tools/entry_check.py
        metadata['run_name'] = args.run_name_record  # date, version, suffix, purpose, commit (tools/run_name.py)
        if args.builder_options['builder'] == 'chim' and args.stage == 'aga' and not args.dry_run:
            # Which legacy exterior stages a CHIM plan still runs, and who reads them (tools/chim/plan.py).
            from chim.plan import record as chim_plan_record
            metadata['chim_plan'] = chim_plan_record([name for name, _ in steps], args.builder_options['chim_areas'])
        # Stage fingerprints always; reuse only with an explicit --reuse-from (docs/BUILD_PROFILE.md).
        import build_cache
        store = None
        if getattr(args, 'prerendered', None):
            from prerendered import configure
            store = configure(args.prerendered[0], VERSION, args.allow_release_reuse, args.prerendered_stages)
        forced = [name for name in (getattr(args, 'rebuild_stage', '') or '').split(',') if name]
        if forced:
            unknown = sorted(set(forced) - {name for name, _ in steps})
            if unknown or not args.reuse_from:
                raise ValueError('--rebuild-stage needs --reuse-from and stage names of this plan'
                                 + (': unknown ' + ', '.join(unknown) if unknown else ''))
        metadata['storage_pool_dir'] = str(storage_pool_dir(args))
        reuse_mode = args.reuse_mode
        if not args.dry_run and (reuse_mode in ('hardlink', 'pool') or storage_pool_enabled(args)):
            pool_record = storage_pool_record(args, run, log=lambda line: print(line, flush=True))
            metadata['storage_pool'] = dict(pool_record, reuse_mode_asked=reuse_mode)
            if reuse_mode in ('hardlink', 'pool') and not pool_record['links']:
                reuse_mode = 'copy'
            metadata['storage_pool']['reuse_mode'] = reuse_mode
        steps = build_cache.prepare(steps, run, metadata, args.reuse_from, reuse_mode,
                                    scope=getattr(args, 'fingerprint_scope', 'units'), prerendered=store,
                                    pool=storage_pool_dir(args), forced=forced,
                                    accept_rebuild=getattr(args, 'accept_rebuild', False))
        if args.reuse_from and args.allow_release_reuse:
            metadata['stage_cache']['release_reuse'] = 'allowed: the from-scratch gate runs separately'
        print(f"Build run: {run}\nLive tool output follows; per-stage logs are saved in {run / 'logs'}.", flush=True)
        live = None
        if args.builder_options['builder'] == 'chim' and args.stage == 'aga' and not args.dry_run and not args.no_cell_progress:
            import live_tracker
            mode = live_tracker.choose(args.live_tracker, args.tracker_declined, sys.stdin.isatty() and not args.yes)
            if mode:
                live = live_tracker.LiveTracker(run, mode, len(steps), data_files=args.data_files).start()
        try:
            execute(steps, run, metadata)
        except BaseException:
            if live:
                live.stop()
            raise
        if args.dry_run:
            result = run / "image" / f"AmiWind-v{VERSION}-dry-run.hdf"
            print('No game assets or ROMs were used. This is not a playable demo.')
        else:
            result = run / "image" / f"AmiWind-v{VERSION}.hdf" if args.stage == "aga" else run / "work/generated/seyda-neen"
            print('Private generated content: do not include it in the public source package.')
        acceptance = None
        if args.stage == 'aga' and not args.dry_run:
            image_receipt = run/'image/build.json'
            if image_receipt.is_file():
                record = json.loads(image_receipt.read_text())
                acceptance = record.get('actor_ground_audit')
                name = record.get('hdf_file', result.name)
                if Path(name).name != name:
                    raise ValueError('Image receipt contains an unsafe HDF filename')
                result = run/'image'/name
            if args.allow_known_actor_ground_findings and acceptance is None:
                raise ValueError('Private-test build is missing its actor acceptance receipt')
        summary.finish('passed', result, actor_acceptance=acceptance)
        if live:
            import live_tracker
            if args.keep_tracker:
                live_tracker.wait_for_enter(live)
            live.stop()
            if live.final_line():
                print(live.final_line(), flush=True)
        if emulator:
            from run_fs_uae import launch
            try:
                if launch(result, *emulator):
                    print('[warning] Build succeeded, but FS-UAE launch/playtest did not complete successfully. HDF retained.')
            except (OSError, ValueError) as exc:
                print(f'[warning] Build succeeded; FS-UAE launch skipped: {exc}. HDF retained: {result}')
        pool_outputs(args, run, played=bool(emulator))
        return 0
    except (KeyboardInterrupt, EOFError):
        if summary and not summary.finished:
            summary.finish('cancelled')
        p.exit(130, "\nCancelled.\n")
    except (OSError, ValueError, RuntimeError) as exc:
        if summary and not summary.finished:
            summary.finish('failed')
        p.exit(1, f"Error: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
