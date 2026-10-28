# SPDX-License-Identifier: GPL-3.0-only
"""Option groups of the builder's command line (tools/build.py parser()), split out of build.py to keep it well
under the release text size limit (BUILD-PY-AT-TEXT-LIMIT-49). parser() calls each group in its place, so the
options, their order and the help text are exactly as before. Options a test reads in build.py's text stay there."""
from pathlib import Path

import retired_flags


# Legacy recorded Seyda Neen maps (project decision 10 October 2026): optional and NOT RECOMMENDED since v0.0.31.
SEYDA_RECORDED_HELP = ("optional, NOT RECOMMENDED since v0.0.31: legacy recorded v0.0.31 Seyda Neen maps; the "
                       "default converts Seyda Neen from your data. DIR/id1 holds them (from your own v0.0.31 "
                       "image), checked against config/seyda-recorded-v0.0.31.json and kept byte for byte "
                       "(BUILD-SEYDA-REGEN-30, tools/recorded_stage.py)")
SEYDA_RECORDED_WARNING = ("WARNING: --seyda-recorded is NOT RECOMMENDED since v0.0.31: legacy recorded v0.0.31 "
                          "Seyda Neen maps; the default converts Seyda Neen from your data.")


# --room-batches not given: every batch (the maintainer's decision of 23 October 2026). The default is a str subclass
# so room_batch_selection tells it from an explicit value: not given, a MiniWind and --interior-format bsp build no
# batch room (never an error); given, a MiniWind takes numbers only and bsp refuses it.
ROOM_BATCHES_DEFAULT = 'all'


class RoomBatchesDefault(str):
    """The --room-batches value when the option is not given (equal to its text)."""


def add_stage_group(p):
    """--stage .. --install-sdk (7 options)."""
    p.add_argument("--stage", choices=("terrain", "aga"), default="aga",
                   help="terrain: host packets only; aga: full experimental HDF")
    p.add_argument("--check", action="store_true", help="Check prerequisites without conversion; optional interactive SDK setup requires confirmation")
    p.add_argument("--plan", action="store_true", help="Check prerequisites and print commands without running")
    p.add_argument("--install-dependencies", action="store_true", help="Preview and confirm Ubuntu/Debian host packages and an external Python environment")
    p.add_argument("--autoinstall", action="store_true", help="Quickest setup: confirm missing host/Python/native dependencies, install them, then continue the build")
    p.add_argument("--yes", action="store_true", help="With --autoinstall, accept the displayed dependency proposal and APT installation (for CI)")
    p.add_argument("--install-sdk", action="store_true", help="Fetch the pinned Linux x86_64 Amiga SDK after confirmation; works alone or with --install-dependencies")


def add_versions_group(p):
    """--versions .. --no-entity-baseline (18 options)."""
    p.add_argument("--versions", action="store_true", help="Compare available tools/packages with the recorded build reference, then exit")
    p.add_argument("--host-plan", action="store_true", help="Read-only OS-specific tool inventory; no installation, tool execution or game data required")
    p.add_argument("--fallback-font", type=Path, help="DejaVuSansMono.ttf for generated console graphics (default: tools/fonts or Linux system font)")
    p.add_argument("--palette", type=Path, help="Optional exact 768-byte conversion RGB palette for the scene; default derives scene colours")
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
    p.add_argument("--workbench-icon", choices=("off", "requester", "launch"), default=None,
                   help="Icon on the boot volume for someone who opens it from Workbench (docs/WORKBENCH_ICON.md): "
                        "launch (the default when not given: the icon starts the game from Workbench), requester (a requester "
                        "says AmiWind starts by booting from its disk) or off (no icon)")
    p.add_argument("--seyda-recorded", type=Path, metavar="DIR",
                   help=retired_flags.help_text(SEYDA_RECORDED_HELP))
    p.add_argument("--seyda-scene-source", choices=("auto", "carrier", "compiled"), default="auto",
                   help="how the bsp stage makes Seyda Neen's scene map: auto (the default: the source-only "
                        "entity/model-box carrier for a CHIM-native Seyda Neen, no BSP29 compile of its cell-aligned "
                        "frame; the compiled town otherwise), carrier, or " + retired_flags.HELP_PREFIX
                        + ": compiled for a CHIM-native Seyda Neen (the complete town compiled to BSP29, which exceeds the "
                        "BSP29 node limit since the frame is cell-aligned, BUILD-SEYDA-HULL2-32; --override "
                        "seyda-scene-compiled)")
    p.add_argument("--skip-dressing", action="store_true",
                   help="DEBUGGING ONLY: the earlier interior rule, leaving out lantern hooks, ropes, ferns and other "
                        "dressing in the Seyda Neen interiors (receipted); by default they are kept (BUILD-DRESSING-EXCLUDED-32)")
    p.add_argument("--no-entity-baseline", action="store_true",
                   help="DEBUGGING ONLY: do not compare the image's entity tracker with the release baseline "
                        "(config/entity-baseline.json); by default a placement lost against it stops the build")


def add_accept_entity_loss_group(p):
    """--accept-entity-loss .. --npc-root-rule (31 options)."""
    p.add_argument("--accept-entity-loss", metavar="REASON",
                   help="Recorded reason that lets an intended loss against the entity baseline pass; name the "
                        "loss's tracker ID in it (release readiness)")
    p.add_argument("--readiness-id", action="append", default=[], metavar="KEY=ID[,ID]",
                   help="Release readiness (tools/release_readiness.py): the tracker ID of an item a release "
                        "candidate or final would refuse (KEY = the option without its dashes, as the readiness "
                        "block prints it, e.g. no-npc-gallery=ID); a full development build stops before any stage "
                        "while an item has no registered ID. Repeatable")
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
                                  "(tools/run_name.py); an explicit name must contain the source version in developer mode; elsewhere a loud warning")
    p.add_argument("--recipe", type=Path, metavar="FILE",
                   help="Build from a recipe (schema build-recipe-1): the build's options as named fields, its input "
                        "files by SHA-256 and the build that checked it. Options given on the command line win; each "
                        "difference is printed and recorded. See docs/BUILD_RECIPES.md")
    p.add_argument("--save-recipe", type=Path, metavar="FILE",
                   help="Write the exact recipe of this build (every option after defaults and overrides, the input "
                        "SHA-256s) to FILE when the build ends; unverified until the master builder checks it in "
                        "(docs/BUILD_RECIPES.md)")
    p.add_argument("--recipe-input", dest="recipe_inputs", action="append", default=[], metavar="ROLE=PATH",
                   help="With --recipe: read the recipe's input ROLE from PATH (its SHA-256 must still match)")
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
    p.add_argument("--npc-anim-type", type=int, choices=(1, 2), default=2,
                   help="Actor motion (docs/ANIMKIT.md): 2 (default) = skeletal, one rest frame on its skeleton's shared table, no movers, no baked frames; 1 = the baked kit as before")
    p.add_argument("--npc-anim", choices=("idle", "react", "move", "full", "react+full"), default=None,
                   help="NPC animation groups per resident model (config/npc-anim-kit.json, docs/ANIMATION.md); default from --anim-kit (on: react+full, off: idle): idle = the previous 8 idle frames; react adds hit and death; move adds walk and run; full adds swim, knockdown and a hand-to-hand attack; react+full (project decision for the next release) = react standing models plus a full model each actor wears only while it moves")
    p.add_argument("--npc-gallery-method", choices=("v2", "baked"), default=None,
                   help="The NPC gallery: v2 (default; NPC Gallery v2.0, tools/gallery_v2.py: the actors the build has "
                        "made, spawned in the gallery from their own rows; nothing baked, no npc-gallery stage) or baked "
                        "(the previous gallery: the npc-gallery stage bakes its own copy of every NPC and creature "
                        "record). A MiniWind leaves the gallery out unless this is given")
    p.add_argument("--no-npc-gallery", action="store_true", help="DEBUGGING ONLY: omit inspection gallery, never required game NPCs; gallery included by default. The image says so in game: dbg npcgallery and the other gallery commands print a built-without-the-NPC-gallery notice. Same as --exclude npc-gallery")
    p.add_argument("--npc-root-rule", choices=("morrowind", "legacy"), default="legacy", help="NIF root node rule for NPC body parts and equipment: legacy (default; the full root transform, verified correct for rigid body parts) or morrowind (the root rotation is ignored exactly as for scenery; measured to break 35 rigid NPC part meshes). Part of every NPC stage's cache key (AMIWIND_NPC_ROOT_RULE)")


def add_with_video_group(p):
    """--with-video .. --no-cell-progress (8 options)."""
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


def add_no_harvest_group(p):
    """--no-harvest .. --map-budget-policy (4 options)."""
    p.add_argument('--no-harvest', action='store_true',
                   help='DEBUGGING ONLY: omit harvestable mushrooms (shipped since v0.0.29); the harvest step is built '
                        'by default and such an image does not match a release (mushrooms stay baked, not pickable)')
    p.add_argument('--harvest-interiors', choices=('on', 'off'), default='on',
                   help='Harvestable mushrooms inside the shipped interiors (default on since v0.0.47: picked = gone '
                        'and remembered in the save, one pick state with the outdoors, HARVEST-INTERIOR-PICK-47); '
                        'off: the earlier exterior-only harvest, interior mushrooms stay baked scenery')
    p.add_argument('--tree-sprites', action='store_true',
                   help='No effect, kept for old command lines: world flora is built by default (BUILD-FLORA-OPTIN-32)')
    p.add_argument('--map-budget-policy', choices=('strict', 'warning'), default='strict',
                   help='Private playtest only: warning permits modeled reserve allowance excess; actual allocation limits and other checks remain enforced')


def add_media_catalogue_group(p):
    """--media-catalogue .. --chim-regions-status (7 options)."""
    p.add_argument('--media-catalogue', choices=('on', 'off'), default='off',
                   help='DEBUGGING ONLY: on also puts the media catalogue (the media coverage report, about 64 MB) on '
                        'the boot disk as id1/media/catalogue.json; off (the default after v0.0.46) leaves it beside the '
                        'image as image/media-coverage.json, since nothing in the game reads it '
                        '(IMAGE-MEDIA-CATALOGUE-ON-DISK-46, docs/MEDIA_IMPORT.md)')
    p.add_argument('--file-aliases', choices=('on', 'off'), default='on',
                   help='on (the default since v0.0.47): byte-identical models, sounds, sprites and tags of the boot '
                        'disk are stored once, their other names listed in id1/file-aliases.txt that the engine reads '
                        '(tools/payload_share.py, IMAGE-DUPLICATE-FILES-46, docs/PAYLOAD_SHARING.md; about 21 MB less '
                        'on the v0.0.46 payload); off stores every copy (the method before)')
    p.add_argument('--shared-skins', choices=('on', 'off'), default='on',
                   help='on (the default since v0.0.47): an actor skin that several actor models repeat (a model and '
                        'its mover model) is stored once in progs/skins/ and the models point to it '
                        '(tools/payload_share.py, IMAGE-ACTOR-SKIN-REPEATS-46, docs/PAYLOAD_SHARING.md; about 65 MB '
                        'less on the v0.0.46 payload); off keeps a skin in every model (the method before)')
    p.add_argument('--night-lamp-lightmaps', choices=('on', 'off'), default='off',
                   help='EXPERIMENTAL (off by default): legacy Balmora cores get baked night-lamp lightmaps on '
                        'lightstyle 32 (prototype, tools/lamp_lightmaps.py; docs/EXPERIMENTAL_FLAGS.md); off keeps '
                        'the night lamps as engine lights only')
    p.add_argument('--chim-native-towns', choices=('on', 'off'), default='on',
                   help='CHIM towns built from the game data with no legacy region-map chain (tools/chim_town.py, '
                        'CHIM-LEGACY-CHAIN-33; Seyda Neen since v0.0.36-dev5: its frame maps from the scene stage\'s '
                        'complete town, no region maps): on (default since v0.0.36: every CHIM area prepared through the CHIM pipeline). '
                        + retired_flags.HELP_PREFIX + ': off (the legacy chains; retired since '
                        + retired_flags.RETIRED_SINCE + ', refused in developer mode without --override '
                        'chim-native-towns-off; docs/EXPERIMENTAL_FLAGS.md "Retired flags")')
    p.add_argument('--chim-regions', action='append', default=[], metavar='SET',
                   help='Exterior cells on CHIM, one CHIM frame per cell replacing that cell\'s open-world map '
                        '(docs/chim/CHIM_REGIONS.md). Default for a full --builder chim build (since v0.0.47): '
                        '@config/chim-cells.json, the release cell list in the source tree. Values: seabed, coast, '
                        'sea-ring, a region name, @FILE (CSV with x,y, aw-chim-cells-1 JSON, Toolkit World Map '
                        'state export), or none (no CHIM region cells: the earlier default, kept selectable); '
                        'repeatable; needs --builder chim')
    p.add_argument('--chim-regions-status', type=Path, metavar='FILE',
                   help='The CHIM progress tracker file (cell-progress.json) --chim-regions is checked against: '
                        'every cell finished in CHIMport (or empty sea), no legacy pocket, no town frame; default '
                        'the public reference docs/chim/cell-progress-reference.json')


def add_legacy_area_group(p):
    """--legacy-area .. --chim-draw-distance (31 options)."""
    p.add_argument('--legacy-area', dest='legacy_areas', action='append', default=[], metavar='TOWN',
                   help=retired_flags.help_text(
                       'build TOWN with the legacy region-map chain (tools/import_town.py; Seyda Neen: its 64 region '
                       'maps and special scenes cut in the image step) although the CHIM builder '
                       'holds it; refused in developer mode without --override legacy-area; default: a CHIM town has '
                       'no legacy maps (docs/EXPERIMENTAL_FLAGS.md "Retired flags")'))
    p.add_argument('--override', action='append', default=[], metavar='NAME', choices=retired_flags.NAMES,
                   help='Let one retired flag through in developer mode, only if sure / for historical regression '
                        'tests (repeatable): ' + ', '.join(retired_flags.NAMES) + '; recorded in every receipt')
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
                        'table row but seyda, e.g. vivec_city): its exterior on CHIM, its residents and, in the '
                        'full scope, its interiors.' + ' ' + retired_flags.vivec_help())
    p.add_argument('--miniwind-map-inspection', action='store_true',
                   help='With --miniwind: skip startup/character screens; enable god, noclip and debug HUD on arrival')
    p.add_argument('--miniwind-debug', action='store_true',
                   help='With --miniwind: a DEBUG ONLY sandbox, not a playtest (notice, startup screen, marker, '
                        'HDF and run names say so); the only build type that takes --chim-draw-distance')
    p.add_argument('--chim-detail-budget', metavar='NAME',
                   help='CHIM builder: a named per-mesh visual triangle budget (config/chim-detail-budgets.json); '
                        'default none')
    p.add_argument('--coord-range', choices=('wide', 'narrow'), default='wide',
                   help='How the engine sends positions (tools/coord_range.py, CHIM-FRAME-COORD-RANGE-33): wide (default '
                        'since v0.0.36) = 24 bits of 1/256 units, +/-32,768 (all of Vivec in one CHIM frame); narrow = '
                        "Quake's 1/8-unit shorts, +/-4,096 (the method before v0.0.36; refuses areas wider than +/-4,000)")
    p.add_argument('--engine-experiment', action='append', choices=('widecoord',), metavar='NAME',
                   help='Engine compile switch of the v0.0.36 spike (docs/EXPERIMENTAL_FLAGS.md): widecoord = wide '
                        'coordinates, the default since v0.0.36 (--coord-range wide); kept so older commands still run')
    p.add_argument('--chim-cut-models-over', type=float, metavar='UNITS',
                   help='CHIM builder: cut models wider than UNITS into tiles shared by their placements '
                        '(tools/chim/cut.py); default none')
    p.add_argument('--chim-terrain-shoreline', choices=('on', 'off'), default='on',
                   help='CHIM builder: town frames triangulate the shoreline tiles as the legacy region maps do '
                        '(on, default: the CHIM/legacy border meets without steps, CHIM-STITCH-SHORELINE-36) or '
                        'keep the plain 128-unit tile grid (off: the method before v0.0.36)')
    p.add_argument('--chim-terrain-resident-detail', choices=('on', 'off'), default='on',
                   help='CHIM builder: town frames keep the original LAND samples on the terrain tiles under '
                        'residents who stand on the ground (on, default, CHIM-VIVEC-FRAME-WIDE-41) or the plain '
                        '128-unit tile grid there (off: the method before v0.0.41)')
    p.add_argument('--chim-terrain-hull', choices=('auto', 'routed', 'compiled'), default='compiled',
                   help='CHIM builder: standing hull of chunk terrain: compiled for every chunk (default from v0.0.36, '
                        'project decision: a fraction of the bytes; CHIM-REGION-MARGIN-STORAGE-36, CHIM-BALMORA-RING-GROWTH-36), '
                        'auto (the earlier default: compiled by qbsp for irregular ground, routed chains for the regular '
                        'grid) or routed')
    p.add_argument('--chim-terrain-refs', choices=('off', 'on'), default='on',
                   help='CHIM builder: terrain references (world format 0.7, default from v0.0.36, project decision): '
                        'chunk terrain stored once per content and placed at an offset by every chunk with it, so '
                        'neighbouring CHIM region frames share their margins (CHIM-REGION-MARGIN-STORAGE-36); off keeps '
                        'a copy per chunk (format 0.5, the earlier default)')
    p.add_argument('--chim-model-hull-patch', choices=('off', 'on'), default='on',
                   help='CHIM builder: add the pieces a compiled model hull lost under a walkable surface (on, '
                        'default), or keep the compiled hull as it is and record the check (off: the previous '
                        'method; CHIM-COMPILED-HULL-SHORT-36)')
    p.add_argument('--chim-model-bevels', default=None,
                   help='CHIM builder: edge bevels of the model standing hulls (EXPERIMENTAL; '
                        'CHIM-COMPILED-HULL-OVERFILL-46): exact, or tol:N; not given or profile = only the meshes whose '
                        'profile asks for them (the method before)')
    p.add_argument('--interior-format', choices=('chim', 'bsp'), default='chim',
                   help='CHIM builder: the form of the interiors (EXPERIMENTAL; docs/chim/INTERIOR_STORE.md): chim = CHIM '
                        'rooms on one interior store, each mesh and texture once, loaded whole at the door (the '
                        'default, maintainer 22 October 2026); bsp = a Quake map per room (the method before)')
    p.add_argument('--room-batches', default=RoomBatchesDefault(ROOM_BATCHES_DEFAULT), metavar='none|all|N|N-M[,...]',
                   help='CHIM builder: convert the interior rooms of these batches of the room list of the repo '
                        '(config/room-batches.json; EXPERIMENTAL, docs/chim/DOOR_GRAPH.md "Rooms by batch in the builder") as '
                        'CHIM rooms, each door linked both ways; a room another room stage of the plan converts is left to '
                        'it. Not given = all (the maintainer\'s decision of 23 October 2026: every base-game interior); '
                        'none = no batch rooms. A MiniWind takes batch numbers only (e.g. --miniwind-balmora '
                        '--room-batches 1): not given, it builds none; so does --interior-format bsp, which refuses '
                        'an explicit selection')
    p.add_argument('--chim-placement-format', choices=('0.7', '0.8'), default=None,
                   help='CHIM builder: world format of the placements (EXPERIMENTAL; CHIM-TILT-VARIANTS-SPLIT-33): 0.8 = '
                        'one model per mesh + scale, the full rotation in the record, collision from the placed pieces; '
                        'not given or 0.7 = scale and tilt baked per variant (the method before)')
    p.add_argument('--chim-reach-index', choices=('copies', 'refs'), default=None,
                   help='CHIM builder: placements a chunk reaches but does not own (EXPERIMENTAL; '
                        'CHIM-PLACEMENT-MARGIN-COPIES-46): refs = world format 0.9, a 4-byte reference to the '
                        'owner record in the same frame (needs --chim-placement-format 0.8); not given or copies = '
                        'a whole record in every chunk the drawn box touches (the method before)')
    p.add_argument('--chim-terrain-pack', choices=('bsp29', 'compact', 'generate'), default='generate',
                   help='CHIM builder: how terrain records are stored: generate (the default since v0.0.47) = world '
                        'format 0.11, regular-path terrain generated by the engine from its heights, the rest compact '
                        '(needs --chim-terrain-refs on; with --chim-terrain-refs off the builder falls back to bsp29); '
                        'compact = world format 0.10, a lossless repack the engine expands to the same bytes; bsp29 = '
                        'the BSP29 brush image (the method before)')
    p.add_argument('--chim-actor-table', choices=('off', 'on'), default='on',
                   help='CHIM builder: the actor table (CHIM-EXTERIOR-ACTORS-MISSING-46): on (the default since '
                        'v0.0.47) = every exterior NPC and creature reference of the game data in maps/chim-actors.cca, '
                        'read by the type 1 window with "chim actors table 1", and the actor library stage; off = none '
                        '(only the frame maps place actors; the method before)')
    p.add_argument('--chim-region-actors', choices=('off', 'on'), default='on',
                   help='CHIM builder (CHIM-EXTERIOR-ACTORS-MISSING-46; on by default, the maintainer, 23 October 2026): on = every CHIM region frame '
                        'map places the exterior NPC and creature references of its cells at their authored spots, '
                        'grounded on the frame collision as the towns\' residents (tools/chim/region_actors.py; the '
                        'actor library stage gives the models; levelled creature lists are listed as deferred); off '
                        '(the default) = region frames place no actors (the method before)')
    p.add_argument('--chim-mesh-method', choices=('table', 'converter', 'merge', 'meshopt+merge'), default=None,
                   help='CHIM builder: how meshes become faces: table (default: config/mesh-methods.json), or one method '
                        'for every mesh: converter (the method before v0.0.36-dev3), merge, meshopt+merge '
                        '(docs/chim/MESH_METHODS.md)')
    p.add_argument('--chim-model-weld', choices=('base', 'placed'), default=None,
                   help='CHIM builder: how a model variant shares its vertices: base (default: as its base, so every '
                        'scale and tilt has the same vertices and edges; CHIM-STRIDER-SCALED-SEAMS-36) or placed '
                        '(by the placed position, the method before v0.0.36-dev3)')
    p.add_argument('--chim-uv-scroll', choices=('off', 'turbulent'), default='turbulent',
                   help='CHIM builder: shapes whose texture scrolls in the original (the Ghostfence curtain, '
                        'waterfalls, the ash mire; not lava): turbulent (default since v0.0.47) a Quake turbulent '
                        'texture that ripples over time, unlit (in game: dbg ghostfence on/off); off a still texture, '
                        'the method before v0.0.47 (GHOSTFENCE-NO-ANIMATION-46)')
    p.add_argument('--chim-fire-light', choices=('on', 'off'), default='on',
                   help='CHIM builder (CHIM-EXTERIOR-FLAMES-MISSING-48; on by default, the maintainer 2026-10-23: '
                        '"set it on by default but add some dbg command like dbg campfires on|off"): on = each fire '
                        'outdoors (campfire, brazier, fire pit, torch, flame lamp) carries its light record in its '
                        'frame map flame row, and the engine lights the placed models around it (in game: dbg '
                        'campfires on/off); off = flames without light (the frame maps of before this option)')
    p.add_argument('--chim-placement-light', choices=('off', 'sources'), default=None,
                   help='CHIM builder, EXPERIMENTAL (CHIM-MESHLESS-LIGHTS-33): sources = every exterior light source '
                        'that adds light (the lights without a mesh among them) gives the placed models it reaches a '
                        'light level (world format 0.12; hybrid lighting only; tools/chim/placement_light.py); off '
                        '(the default until its in-game frame cost is measured) = none, the world as before')
    p.add_argument('--chim-draw-distance', type=int, metavar='UNITS',
                   help='DEBUG ONLY (--miniwind --miniwind-debug): a stated closer view; the CHIM world is built '
                        'and heap-gated for this draw distance and the image starts with it (default 540)')


def add_direct_to_game_map_group(p):
    """--direct-to-game-map .. --miniwind-boot (2 options)."""
    p.add_argument('--direct-to-game-map', dest='direct_to_game_map', metavar='START',
                   help='Quick test build (-devN only): boot straight into START with a ready-made character, no '
                        'intro, ship or character creation. START: an area (balmora, seyda_neen, vivec_arena), '
                        '"interior:<cell id>", cell:X,Y or pos:X,Y,Z[@HEADING] (the debug HUD\'s GLOBAL XYZ). '
                        'See docs/chim/build_guide/DIRECT_START.md')
    p.add_argument('--miniwind-boot', metavar='CMD[;CMD]',
                   help='With --miniwind: dbg console commands the sandbox runs once on arrival, separated by ";" '
                        '(a preset row\'s boot_commands; docs/MINIWIND.md)')


def add_quick_character_group(p):
    """--quick-character .. --no-skip-census (4 options)."""
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


def add_serial_stages_group(p):
    """--serial-stages .. --resource-check (44 options)."""
    p.add_argument('--serial-stages', action='store_true',
                   help='Run stages in order while retaining each stage job limit (diagnostics)')
    p.add_argument('--live-logs', action='store_true',
                   help='BENCHMARK/DIAGNOSTIC IMAGES: the engine writes its diagnostic logs as they happen '
                        '(aw_logs_live 1; tools/profile_aga.py reads them); default: in memory until Exit game '
                        'or dbg savelogs, so play keeps the boot volume quiet (BOOT-VOLUME-NOT-VALIDATED-33)')
    p.add_argument('--log-level', choices=('quiet', 'normal', 'verbose'), default=None,
                   help='How much the stages print (default: normal, or AMIWIND_LOG_LEVEL): quiet drops only the '
                        'per-unit progress lines; phase start/end lines with their time, the heartbeat of a silent '
                        'stage, warnings and errors always print. Recorded in the receipt; outputs are the same. '
                        'See docs/BUILD_PROFILE.md')
    p.add_argument('--quiet', action='store_true', help='Same as --log-level quiet')
    p.add_argument('--perf-guard', choices=('fail', 'warn', 'off'), default='fail',
                   help='Perf guard at the end of the build (tools/perf_guard.py, docs/BUILD_PROFILE.md "Perf guard"): '
                        'every stage section is judged against earlier runs of the same work (cores, time) and for '
                        'long sections on a fraction of the cores; fail (default) ends the build with exit 3 when it '
                        'fails (outputs stay valid and reusable), warn only prints, off is for DEBUGGING ONLY')
    p.add_argument('--perf-guard-baselines', type=Path, metavar='FILE',
                   help='Perf guard baselines ledger (default: AMIWIND_PERF_GUARD_BASELINES, else '
                        '<workspace>/cache/perf-guard/baselines.jsonl); a passed build adds its sections to it')
    p.add_argument('--size-guard', choices=('auto', 'fail', 'warn', 'off'), default='auto',
                   help='Size guard at the end of an image build (tools/size_ledger.py, docs/BUILD_OUTPUT.md "Size '
                        'ledger"): a payload folder that grew more than --size-growth-margin against a like-for-like '
                        'record (the previous release, tools/size-baseline.json, and --size-baseline) fails the '
                        'build with exit 4 unless --size-growth-reason names it; auto (default) = warn for -devN '
                        'versions, fail for rc and final; off is for DEBUGGING ONLY')
    p.add_argument('--size-baseline', type=Path, metavar='FILE',
                   help='A previous build\'s size-ledger.json to compare with, besides the previous release')
    p.add_argument('--size-growth-margin', type=float, default=0.05, metavar='GIB',
                   help='Growth per payload folder the size guard allows without a reason (GiB, default 0.05)')
    p.add_argument('--size-growth-reason', metavar='TEXT',
                   help='Names why the payload grew (recorded in size-ledger.json and the build summary)')
    p.add_argument('--no-profile', action='store_true',
                   help='DEBUGGING ONLY: run stages without the build profiler and output manifests '
                        '(build-profile.json); outputs are the same, and a later --reuse-from cannot use such a run. '
                        'See docs/BUILD_PROFILE.md')
    # A first-time user's build and the release's from-scratch check (tools/clean_build.py, docs/BUILD_CACHE.md
    # "Before a release"): off by default; neither changes a stage command or key, the receipt records them.
    p.add_argument('--clean', action='store_true',
                   help='Build as a first-time user would: no --reuse-from, --rebuild-stage, prerendered store or '
                        'cache and pool outside the workspace, and the workspace cache (WORKSPACE/cache) must be '
                        'empty or absent (a filled one is refused, never emptied: give a new --workspace). '
                        'Recorded in the build receipt (clean). See docs/BUILD_CACHE.md')
    p.add_argument('--public-defaults', action='store_true',
                   help='Refuse what a public user would not have: --override and retired flags, every --allow-* '
                        'and --accept-* waiver, --chim-regions @FILE or --chim-regions-status outside the source '
                        'tree, and the switches of docs/EXPERIMENTAL_FLAGS.md at a non-default value; every refusal '
                        'is listed. Recorded in the build receipt (public_defaults). With --clean: the release\'s '
                        'from-scratch check')
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
    p.add_argument('--stair-walk', choices=('auto', 'off', 'all', 'flights'), default='auto',
                   help='OFF BY DEFAULT (decided by the maintainer 20 October 2026, BUILD-STAIR-WALK-OFF-46: auto = off, no build walks stairs unless asked). When asked, what the stair walk covers: flights (only the steps of flights, which gate the build), all '
                        '(every step and ramp, the advisory findings too: a nightly or beta run on request) or auto '
                        '(default: flights for every build since v0.0.46; before, all for development builds). This '
                        'is WHAT is walked; with the walk cache (--stair-walk-cache cached, the default with '
                        '--developer-mode) a map or frame whose walk inputs are unchanged is not walked again')
    p.add_argument('--stair-walk-key', choices=('reach', 'frame'), default=None,
                   help='How the walk of a CHIM frame is keyed: reach (default with --stair-walk-cache cached: per core, '
                        'its steps and ramps and the collision within reach of their walks, so collision far from '
                        'every stair does not walk a frame again) or frame (the key before v0.0.46: every chunk and '
                        'placement of the frame; the default with --stair-walk-cache records, whose shipped stair '
                        'records are keyed by it); sets AMIWIND_STAIR_WALK_KEY')
    p.add_argument('--stair-walk-places', metavar='FILE|ID,...', default=None,
                   help='DEVELOPMENT BUILDS ONLY: a targeted stair walk of the named places and nothing else (a '
                        'redundancy check of individual problem places on request): a watch-list file, or a comma '
                        'list of IDs of config/stair-watch.json, cells x:y, frame paths frames/..., maps map:NAME and source '
                        'references ref:N; the rows are reported, never stored; sets AMIWIND_STAIR_WALK_PLACES')
    p.add_argument('--stair-watch', metavar='FILE|off', default=None,
                   help='The stair watch list: the frames holding its places are walked again on every build, even '
                        'when their walk is reused, and a difference from the record stops the build (default '
                        'config/stair-watch.json; a bug page that reports a stair or walkway problem adds its place '
                        'there); off: none; sets AMIWIND_STAIR_WATCH')
    p.add_argument('--stair-walk-cache', choices=('records', 'cached', 'full'), default=None,
                   help='records (the default without --developer-mode): a CHIM frame whose collision matches the '
                        'known-good stair records shipped with the source (config/stair-records, by SHA-256) or a '
                        'walk stored in this workspace is not walked; a frame in neither (another converter or other '
                        'game data) is reported by name and walked only on request (cached); legacy maps as cached. '
                        'cached (the default with --developer-mode): a legacy map or CHIM frame is stair-walked once '
                        'and its result reused while what the walk reads (its collision, by SHA-256) is unchanged; a '
                        'few reused ones are walked again on every build to check the cache (--stair-walk-sample). '
                        'full: REGRESSION AND BETA-TEST RUNS ONLY (the from-scratch reference build before a release, '
                        'a nightly check): walks every map and frame again, ignoring every stored and shipped walk')
    p.add_argument('--stair-walk-area', choices=('owned', 'frame'), default=None,
                   help='Where a CHIM region frame\'s stair walk walks: owned (default: the cell the frame owns plus '
                        'the map-switch margin; its border copies of other cells are walked where they are owned) '
                        'or frame (the method before v0.0.42: the whole frame with its border copies)')
    p.add_argument('--stair-collision-method', choices=('0', '1'), default=None,
                   help='How a flight of stairs gets its collision: 1 (default since v0.0.48-dev2) a stairway collision mesh (one ramp, or one block per tread) for every flight whose collision fails the geometric stair check (tools/stair_mesh.py; a mesh without a flight keeps its collision and unit key); 0 the convex proxies with the stair rules (the method before, kept for A/B); sets AMIWIND_STAIR_COLLISION_METHOD')
    p.add_argument('--collision-source', choices=('authored', 'profile'), default=None,
                   help='Which triangles of a model collide: authored (default since v0.0.48-dev2) one rule for every mesh converter: the root RootCollisionNode, else the drawn triangles; NC* and NCC models nonsolid, AvoidNode subtrees left out (tools/collision_source.py, COLLISION-RCN-SCOPE-32); profile the rule before (each converter profile opts in, the drawn triangles otherwise; kept for A/B); sets AMIWIND_COLLISION_SOURCE')
    p.add_argument('--collision-underside', choices=('rule', 'split', 'whole', 'names'), default=None,
                   help='How a CHIM model keeps collision that a convex piece closes under an authored ceiling '
                        '(CHIM-VOS-TEMPLE-WALKWAY-41): names (default): a list of mesh names (the Velothi temples) '
                        'keeps its authored collision surfaces. EXPERIMENTAL general rules, for every mesh: rule (a '
                        'piece filling more than a unit under an authored downward-facing surface becomes authored '
                        'plates), split (such a piece is split first) or whole (such a mesh keeps all its authored '
                        'surfaces; much more collision memory)')
    p.add_argument('--scale-snap', choices=('on', 'off'), default=None,
                   help='CHIM placements of a mesh without collision (kelp, grass) scaled to the nearest 0.1 so its '
                        'scaled copies share one model (chim.build.SCALE_SNAP; at most 5 %% of the size at scale 1; '
                        'CHIM-HULL-SURFACE-HEAP-46): on (default) or off (every scale as placed); sets '
                        'AMIWIND_SCALE_SNAP')
    p.add_argument('--stair-walk-sample', type=int, default=None, metavar='N',
                   help='Reused maps or frames the stair walk walks again and compares on every build (default 2; '
                        '0 = none, development builds only): a difference stops the build (the cache key missed an '
                        'input)')
    # Release reuse by default (build_cache.resolve_release_reuse)
    p.add_argument('--allow-release-reuse', action='store_true', default=None,
                   help='The default since v0.0.49: an rc or final takes --reuse-from and the per-file caches')
    p.add_argument('--release-from-scratch', dest='allow_release_reuse', action='store_false',
                   help='Build an rc or final from scratch (the reproducibility gate; --clean implies it)')
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
    # Resource plan (tools/resource_plan.py, docs/BUILD_PROFILE.md "Resource plan"): memory and threads per stage
    # against what the build gets, before the first stage of every build; WILL NOT FIT refuses the build at once.
    p.add_argument('--resource-plan', action='store_true',
                   help='Print the resource plan of this build (memory and threads per stage that will run, against '
                        'what the build gets) and exit; read only, nothing is built. With --check: after the checks')
    p.add_argument('--resource-plan-json', type=Path, metavar='FILE',
                   help='With --resource-plan: also write the plan (schema resource-plan-1) to FILE')
    p.add_argument('--resource-memory-gb', type=float, metavar='GB',
                   help="The memory the build will run with (e.g. its lease), instead of this container's own limit")
    p.add_argument('--resource-threads', type=int, metavar='N',
                   help="The threads the build will run with (e.g. its lease), instead of this container's CPU quota")
    p.add_argument('--resource-from', action='append', default=[], type=Path, metavar='RUN',
                   help='Also measure stages from this earlier run (and the runs it reused from); repeatable. '
                        'Default: the --reuse-from run and the workspace history only')
    p.add_argument('--resource-check', choices=('fail', 'warn', 'off'), default='fail',
                   help='fail (default): a stage whose single unit cannot fit the memory refuses the build before '
                        'any stage; warn: print it and build anyway; off: no resource plan')
