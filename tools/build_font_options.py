# SPDX-License-Identifier: GPL-3.0-only
"""Resolve build settings: CLI > selected JSON (--build-config) > shipped defaults.

The shipped defaults are config/build-defaults.json:
bitmap_paper_ink: paper text ink for bitmap-derived fonts.
follow_original_stair_rules: collide stairs and slopes by Morrowind's own rules (step up 34 units = 8.5 at our
scale, walkable slope up to 46 degrees, authored collision instead of convex shells). TRUE by default (maintainer
decision 2026-10-08); the converters read it through resolve_font_options()["follow_original_stair_rules"].
builder: legacy or chim, with chim_areas, the areas the CHIM builder writes.
chim_texture_effects: CHIM texture effects (.chimfx paths or shipped names, tools/chim/effects) the CHIM
builder applies, in order; none by default (docs/chim/TEXTURE_EFFECTS.md).
chim_lighting_type: how a CHIM world is lit (tools/chim/light_types.py): none, lamps or hybrid (the default, maintainer
decision 2026-10-09); baked-e and full are reserved for an increased-memory version (docs/chim/LIGHTING.md).
model_hull: how a placed model's standing hull is written when qbsp does not compile it (tools/routed_hull.py):
auto (default: routed above 16 convex pieces, INTERIOR-HULL-CHAIN-33 / CHIM-HULL-CHAIN-COST-33), chain (every piece
in one chain, the converters' earlier form), routed (every model) or balanced (the first routing, kept selectable).
lava: how Morrowind's lava pools are converted (tools/lava.py, docs/LAVA.md): quake (default: Quake liquid brushes
with a "*lava" warp texture, lava contents, embers and glow) or static (the earlier rule: interior rooms leave the pool
activator out, exterior frames place the pool mesh as a solid model).
world_map: the in-game world map file (tools/prepare_world_ui.py, docs/WORLD_MAP_AND_JOURNAL.md): v2 (default: AWM2,
the terrain map plus the molten lava pools of the exterior cells) or v1 (AWM1: terrain and settlements only, kept selectable).
npc_head_detail: humanoid heads in whole-model NPC bakes (tools/npc_geometry.py head_plan): original (the head
keeps every original triangle, the body its silhouette, NPC-HEAD-DECIMATION-33), budget (the previous 480-triangle
split that decimated heads) or auto (shipped default: budget; original heads are EXPERIMENTAL, off by default in v0.0.35 and
chosen only with --npc-head-detail original; docs/EXPERIMENTAL_FLAGS.md).
npc_head_reducer: how the budget-head bake reduces head and hair: locked (default from v0.0.43-dev3, decided for
the project 18 October 2026: the boundary-locked reducer, no new holes, NPC-HEAD-DECIMATION-33) or default (the
previous reducer, byte for byte).
heap_mb: the game heap (Quake's Hunk) in MiB, used exactly as asked like --jobs; not in the shipped defaults:
the engine source's AMIWIND_HEAP_MB is the default (tools/project_version.heap_plan).
storage_pool_dir: the shared storage pool folder (tools/storage_pool.resolve_dir; --storage-pool-dir overrides it,
relative paths are relative to the config file); not in the shipped defaults: WORKSPACE/cache/asset-pool-v1."""
import hashlib
import json
from pathlib import Path

DEFAULT_CONFIG = Path(__file__).resolve().parents[1] / "config/build-defaults.json"
INK_MODES = ("filled", "original")
BUILDERS = ("legacy", "chim")
MODEL_HULLS = ("auto", "chain", "routed", "balanced", "compiled")
LAVA_MODES = ("quake", "static")
WORLD_MAPS = ("v1", "v2")
WORLD_MAP_VARIABLE = "AMIWIND_WORLD_MAP"   # read by tools/prepare_world_ui.py (same name, test-checked)


def export_world_map(value):
    """Export the resolved world map format for the world-ui stage and the image step (stdlib only: the
    builder's bootstrap imports no third-party module)."""
    import os
    if value not in WORLD_MAPS:
        raise ValueError("world_map must be v1 or v2")
    os.environ[WORLD_MAP_VARIABLE] = value
NPC_HEAD_DETAILS = ("auto", "original", "budget")
NPC_HEAD_REDUCERS = ("locked", "default")
KNOWN_KEYS = {"bitmap_paper_ink", "follow_original_stair_rules", "builder", "chim_areas", "chim_texture_effects",
              "heap_mb", "model_hull", "chim_stream_statics", "lava", "world_map", "chim_lighting_type",
              "storage_pool_dir", "npc_head_detail", "npc_head_reducer",
              # NPC model levels of detail: validated and resolved by tools/npc_lod.py.
              "npc_lod", "npc_lod_levels", "npc_face_lod", "npc_lod_disk_mib",
              # The image's disk layout: validated and resolved by tools/layout_plan.py.
              "disk_layout", "partition_headroom_mib", "boot_partition_headroom_mib",
              # The free space a build needs (tools/disk_need.py): machine settings, in no stage key.
              "min_free_gib", "disk_margin_percent"}


def add_disk_layout_options(parser):
    """The image's disk layout options (tools/layout_plan.py; tools/build.py passes them to the image step)."""
    parser.add_argument("--disk-layout", choices=("compact", "legacy"), default=None,
                        help="Disk image layout: compact (default, config disk_layout: the fewest partitions the payload "
                             "needs, each sized from its payload + headroom; tools/layout_plan.py) or legacy (the earlier "
                             "layout: open-world maps on volumes of their own, partitions payload + 20 %% + 16 MiB)")
    parser.add_argument("--partition-headroom-mib", type=int, default=None, metavar="MIB",
                        help="Free space every partition keeps (default 100, config partition_headroom_mib)")
    parser.add_argument("--boot-partition-headroom-mib", type=int, default=None, metavar="MIB",
                        help="Free space the boot partition keeps for saves and settings (default: the partition "
                             "headroom, config boot_partition_headroom_mib)")
    # The free space a build needs (tools/disk_need.py, BUILD-DISK-NEED-UNKNOWN-52): machine settings, in no stage
    # key and no recipe; they set AMIWIND_MIN_FREE_GIB / AMIWIND_DISK_MARGIN_PERCENT for the checks.
    parser.add_argument("--min-free-gib", type=float, default=None, metavar="GIB",
                        help="The least free space a build asks for on its workspace's file system (default 35, "
                             "config min_free_gib); the need is the last known good build's figure plus the margin")
    parser.add_argument("--disk-margin-percent", type=float, default=None, metavar="PERCENT",
                        help="The margin over the last known good build's disk figure (default 30, config "
                             "disk_margin_percent)")


def add_font_options(parser):
    parser.add_argument("--build-config", type=Path,
                        help="JSON build settings (bitmap_paper_ink, follow_original_stair_rules, builder, chim_areas); CLI overrides this file")
    stairs = parser.add_mutually_exclusive_group()
    stairs.add_argument("--follow-original-stair-rules", dest="follow_original_stair_rules", action="store_true", default=None,
                        help="Stairs and slopes collide by Morrowind's rules (default: on, from config/build-defaults.json)")
    stairs.add_argument("--no-follow-original-stair-rules", dest="follow_original_stair_rules", action="store_false",
                        help="DEBUGGING ONLY: use the older convex stair collision")
    parser.add_argument("--model-hull", choices=MODEL_HULLS, default=None,
                        help="Standing hull of large placed models: chain (default in v0.0.33: one chain per model), "
                             "auto (routed above 16 convex pieces; CHIM: above 256), routed (every model) or balanced "
                             "(the first routing: parts by piece counts, xy cuts)")
    parser.add_argument("--lava", choices=LAVA_MODES, default=None,
                        help="Lava pools: quake (default: Quake liquid with the warp, lava contents, damage and tint) "
                             "or static (the earlier rule: rooms leave the pool out, exterior frames place it as a model)")
    parser.add_argument("--world-map", choices=WORLD_MAPS, default=None,
                        help="In-game world map file: v2 (default: terrain map plus the molten lava pools) or v1 "
                             "(the earlier map: terrain and settlements only)")
    parser.add_argument("--npc-head-detail", choices=NPC_HEAD_DETAILS, default=None,
                        help="Humanoid NPC heads in baked models: auto (default: budget, the previous bake), original (EXPERIMENTAL, original (head keeps "
                             "every original triangle, body and clothing keep their silhouette) or budget (the "
                             "previous 480-triangle bake that decimated heads)")
    parser.add_argument("--npc-head-reducer", choices=NPC_HEAD_REDUCERS, default=None,
                        help="How the budget-head bake reduces NPC head and hair shapes: locked (default: the "
                             "boundary-locked reducer, no new holes in a face) or default (the previous reducer)")
    stream = parser.add_mutually_exclusive_group()
    stream.add_argument("--chim-stream-statics", dest="chim_stream_statics", action="store_true", default=None,
                        help="CHIM frame maps tag their sprite and model statics to stream with their chunks (default on, "
                             "from config/build-defaults.json; the engine reads the tags)")
    stream.add_argument("--no-chim-stream-statics", dest="chim_stream_statics", action="store_false",
                        help="DEBUGGING ONLY: CHIM frame maps keep every static loaded with the map")
    parser.add_argument("--bitmap-paper-ink", choices=INK_MODES, default=None,
                        help="Bitmap-derived paper text only: filled (default) or original; TTF and UI fonts unchanged")


def _read(path):
    path = Path(path).expanduser()
    try:
        raw = path.read_bytes()
        values = json.loads(raw)
    except (OSError, ValueError, UnicodeError) as exc:
        raise ValueError(f"Cannot read build config {path}: {exc}") from exc
    if not isinstance(values, dict):
        raise ValueError(f"Build config {path} must be a JSON object")
    unknown = set(values) - KNOWN_KEYS
    if unknown:
        raise ValueError(f"Unknown build config keys in {path}: {', '.join(sorted(unknown))}")
    if "bitmap_paper_ink" in values and values["bitmap_paper_ink"] not in INK_MODES:
        raise ValueError(f"Invalid bitmap_paper_ink in {path}: expected filled or original")
    if "builder" in values and values["builder"] not in BUILDERS:
        raise ValueError(f"Invalid builder in {path}: expected legacy or chim")
    if "chim_areas" in values and (not isinstance(values["chim_areas"], list) or not values["chim_areas"]
                                   or not all(isinstance(a, str) and a for a in values["chim_areas"])):
        raise ValueError(f"Invalid chim_areas in {path}: expected a non-empty list of town ids")
    if "chim_texture_effects" in values and (not isinstance(values["chim_texture_effects"], list)
                                             or not all(isinstance(e, str) and e for e in values["chim_texture_effects"])):
        raise ValueError(f"Invalid chim_texture_effects in {path}: expected a list of effect files or names")
    if "chim_lighting_type" in values:
        from chim.light_types import TYPES
        if values["chim_lighting_type"] not in TYPES:
            raise ValueError(f"Invalid chim_lighting_type in {path}: expected one of {', '.join(TYPES)}")
    if "heap_mb" in values and (isinstance(values["heap_mb"], bool) or not isinstance(values["heap_mb"], int)):
        raise ValueError(f"Invalid heap_mb in {path}: expected a whole number of MiB")
    if "chim_stream_statics" in values and not isinstance(values["chim_stream_statics"], bool):
        raise ValueError(f"Invalid chim_stream_statics in {path}: expected true or false")
    if "model_hull" in values and values["model_hull"] not in MODEL_HULLS:
        raise ValueError(f"Invalid model_hull in {path}: expected auto, chain, routed, balanced or compiled")
    if "lava" in values and values["lava"] not in LAVA_MODES:
        raise ValueError(f"Invalid lava in {path}: expected quake or static")
    if "world_map" in values and values["world_map"] not in WORLD_MAPS:
        raise ValueError(f"Invalid world_map in {path}: expected v1 or v2")
    if "npc_head_detail" in values and values["npc_head_detail"] not in NPC_HEAD_DETAILS:
        raise ValueError(f"Invalid npc_head_detail in {path}: expected auto, original or budget")
    if "npc_head_reducer" in values and values["npc_head_reducer"] not in NPC_HEAD_REDUCERS:
        raise ValueError(f"Invalid npc_head_reducer in {path}: expected locked or default")
    if "follow_original_stair_rules" in values and not isinstance(values["follow_original_stair_rules"], bool):
        raise ValueError(f"Invalid follow_original_stair_rules in {path}: expected true or false")
    if "disk_layout" in values and values["disk_layout"] not in ("compact", "legacy"):
        raise ValueError(f"Invalid disk_layout in {path}: expected compact or legacy")
    for name in ("partition_headroom_mib", "boot_partition_headroom_mib"):
        value = values.get(name)
        if name in values and not (value is None and name == "boot_partition_headroom_mib") and (
                isinstance(value, bool) or not isinstance(value, int) or value < 0):
            raise ValueError(f"Invalid {name} in {path}: expected a whole number of MiB (0 or more)")
    if "storage_pool_dir" in values and not (isinstance(values["storage_pool_dir"], str) and values["storage_pool_dir"]):
        raise ValueError(f"Invalid storage_pool_dir in {path}: expected a folder path")
    return values, {"path": str(path.resolve()), "sha256": hashlib.sha256(raw).hexdigest()}


def resolve_font_options(args):
    defaults, default_record = _read(DEFAULT_CONFIG)
    if "bitmap_paper_ink" not in defaults:
        raise ValueError("Shipped build defaults must define bitmap_paper_ink")
    mode = defaults["bitmap_paper_ink"]
    origin = "shipped default"
    records = [default_record]
    selected = getattr(args, "build_config", None)
    if selected is not None:
        values, record = _read(selected)
        records.append(record)
        if "bitmap_paper_ink" in values:
            mode = values["bitmap_paper_ink"]
            origin = "build config"
    if "follow_original_stair_rules" not in defaults:
        raise ValueError("Shipped build defaults must define follow_original_stair_rules")
    stairs, stairs_origin = defaults["follow_original_stair_rules"], "shipped default"
    if selected is not None and "follow_original_stair_rules" in values:
        stairs, stairs_origin = values["follow_original_stair_rules"], "build config"
    cli_stairs = getattr(args, "follow_original_stair_rules", None)
    if cli_stairs is not None:
        stairs, stairs_origin = bool(cli_stairs), "CLI override"
    if "model_hull" not in defaults:
        raise ValueError("Shipped build defaults must define model_hull")
    hull, hull_origin = defaults["model_hull"], "shipped default"
    if selected is not None and "model_hull" in values:
        hull, hull_origin = values["model_hull"], "build config"
    if getattr(args, "model_hull", None) is not None:
        hull, hull_origin = args.model_hull, "CLI override"
    if "lava" not in defaults:
        raise ValueError("Shipped build defaults must define lava")
    lava, lava_origin = defaults["lava"], "shipped default"
    if selected is not None and "lava" in values:
        lava, lava_origin = values["lava"], "build config"
    if getattr(args, "lava", None) is not None:
        lava, lava_origin = args.lava, "CLI override"
    if "world_map" not in defaults:
        raise ValueError("Shipped build defaults must define world_map")
    world_map, world_map_origin = defaults["world_map"], "shipped default"
    if selected is not None and "world_map" in values:
        world_map, world_map_origin = values["world_map"], "build config"
    if getattr(args, "world_map", None) is not None:
        world_map, world_map_origin = args.world_map, "CLI override"
    stream, stream_origin = bool(defaults.get("chim_stream_statics", False)), "shipped default"
    if selected is not None and "chim_stream_statics" in values:
        stream, stream_origin = values["chim_stream_statics"], "build config"
    if getattr(args, "chim_stream_statics", None) is not None:
        stream, stream_origin = bool(args.chim_stream_statics), "CLI override"
    heads, heads_origin = defaults.get("npc_head_detail", "auto"), "shipped default"
    if selected is not None and "npc_head_detail" in values:
        heads, heads_origin = values["npc_head_detail"], "build config"
    if getattr(args, "npc_head_detail", None) is not None:
        heads, heads_origin = args.npc_head_detail, "CLI override"
    reducer, reducer_origin = defaults.get("npc_head_reducer", "locked"), "shipped default"
    if selected is not None and "npc_head_reducer" in values:
        reducer, reducer_origin = values["npc_head_reducer"], "build config"
    if getattr(args, "npc_head_reducer", None) is not None:
        reducer, reducer_origin = args.npc_head_reducer, "CLI override"
    heads_setting = heads
    if heads == "auto":
        # v0.0.35: original heads are EXPERIMENTAL and off by default (project decision 2026-10-10).
        heads, heads_origin = "budget", heads_origin + ", auto: budget (original heads are experimental)"
    cli = getattr(args, "bitmap_paper_ink", None)
    if cli is not None:
        if cli not in INK_MODES:
            raise ValueError("Bitmap paper ink must be filled or original")
        mode, origin = cli, "CLI override"
    return {"bitmap_paper_ink": mode, "selected_by": origin, "config_files": records,
            "follow_original_stair_rules": stairs, "follow_original_stair_rules_selected_by": stairs_origin,
            "model_hull": hull, "model_hull_selected_by": hull_origin,
            "lava": lava, "lava_selected_by": lava_origin,
            "world_map": world_map, "world_map_selected_by": world_map_origin,
            "chim_stream_statics": stream, "chim_stream_statics_selected_by": stream_origin,
            "npc_head_detail": heads, "npc_head_detail_selected_by": heads_origin,
            "npc_head_detail_setting": heads_setting,
            "npc_head_reducer": reducer, "npc_head_reducer_selected_by": reducer_origin}


def add_heap_options(parser):
    parser.add_argument("--heap-mb", type=int, default=None, metavar="N",
                        help="Game heap (Quake's Hunk) in MiB, used exactly as asked like --jobs (default: the engine's "
                             "11). Above the size measured to run the whole game on 16 MiB Fast RAM, the build, the "
                             "boot check and the engine print one warning and go on (docs/chim/build_guide/MEMORY.md)")


def resolve_heap(args):
    """The game heap: CLI > --build-config heap_mb > the engine source's default. Never refused for
    being large: above the measured safe size the record carries the warning the build prints."""
    from project_version import heap_plan
    asked, origin = None, "engine default"
    selected = getattr(args, "build_config", None)
    if selected is not None:
        values, _ = _read(selected)
        if "heap_mb" in values:
            asked, origin = values["heap_mb"], "build config"
    if getattr(args, "heap_mb", None) is not None:
        asked, origin = args.heap_mb, "CLI override"
    plan = heap_plan(asked)
    plan["selected_by"] = origin
    return plan


def configured_storage_pool_dir(args):
    """(value, folder of the config file) of the build config's storage_pool_dir, or (None, None)."""
    selected = getattr(args, "build_config", None)
    if selected is None:
        return None, None
    values, _ = _read(selected)
    return values.get("storage_pool_dir"), Path(selected).expanduser().absolute().parent


def add_builder_options(parser):
    parser.add_argument("--builder", choices=BUILDERS, default=None,
                        help="Exterior world pipeline: chim (default from v0.0.33, with the CHIM areas of "
                             "config/build-defaults.json: Balmora, Seyda Neen and all of Vivec; the CHIM world streamer: every "
                             "asset stored once; docs/chim/WORLD_FORMAT.md) or legacy (overlapping region maps)")
    from retired_flags import vivec_help as retired_vivec_help   # the retired Vivec district areas
    parser.add_argument("--chim-area", dest="chim_areas", action="append", default=None, metavar="TOWN",
                        help="With --builder chim: a town from config/towns.json the CHIM world holds "
                             "(repeatable; default from the build config)" + ' ' + retired_vivec_help())
    parser.add_argument("--chim-texture-effect", dest="chim_texture_effects", action="append", default=None,
                        metavar="EFFECT",
                        help="With --builder chim: apply a CHIM texture effect (a .chimfx file or a shipped name such "
                             "as autumn_glitter_leaves; repeatable, in order). Off by default; replaces the build "
                             "config's list (docs/chim/TEXTURE_EFFECTS.md)")
    from chim.light_types import TYPES, help_text
    parser.add_argument("--chim-lighting-type", dest="chim_lighting_type", choices=list(TYPES), default=None,
                        help="With --builder chim: " + help_text())


def resolve_builder(args):
    """The builder type and, for chim, its areas and versions: CLI > --build-config > shipped defaults."""
    defaults, default_record = _read(DEFAULT_CONFIG)
    for key in ("builder", "chim_areas"):
        if key not in defaults:
            raise ValueError("Shipped build defaults must define " + key)
    builder, areas, origin = defaults["builder"], list(defaults["chim_areas"]), "shipped default"
    effects = list(defaults.get("chim_texture_effects", []))
    from chim.light_types import DEFAULT as LIGHTING_DEFAULT
    lighting, lighting_origin = defaults.get("chim_lighting_type", LIGHTING_DEFAULT), "shipped default"
    records = [default_record]
    selected = getattr(args, "build_config", None)
    if selected is not None:
        values, record = _read(selected)
        records.append(record)
        if "builder" in values:
            builder, origin = values["builder"], "build config"
        if "chim_areas" in values:
            areas = list(values["chim_areas"])
        if "chim_texture_effects" in values:
            effects = list(values["chim_texture_effects"])
        if "chim_lighting_type" in values:
            lighting, lighting_origin = values["chim_lighting_type"], "build config"
    if getattr(args, "chim_lighting_type", None) is not None:
        lighting, lighting_origin = args.chim_lighting_type, "CLI override"
    if getattr(args, "builder", None) is not None:
        builder, origin = args.builder, "CLI override"
    if getattr(args, "chim_areas", None):
        areas = list(dict.fromkeys(args.chim_areas))
    if getattr(args, "chim_texture_effects", None):
        effects = list(args.chim_texture_effects)
    record = {"builder": builder, "selected_by": origin, "config_files": records,
              "chim_version": None, "world_format": None, "chim_areas": [], "chim_texture_effects": [],
              "chim_lighting_type": None}
    if builder == "chim":
        from chim import CHIM_VERSION, FORMAT_VERSION
        from chim.areas import area_problems
        problems = area_problems(areas)
        if problems:
            raise ValueError("; ".join(problems))
        loaded = []
        if effects:  # numpy: only when an effect is asked for (setup modes run before the tools exist)
            from chim.texfx import effect_path, load_effect
        for value in effects:
            effect = load_effect(effect_path(value))
            loaded.append({"effect": value, "name": effect["name"], "sha256": effect["sha256"],
                           "path": str(effect_path(value))})
        from chim.light_types import check as check_lighting
        record.update(chim_version=CHIM_VERSION, world_format="%d.%d" % FORMAT_VERSION, chim_areas=areas,
                      chim_texture_effects=loaded, chim_lighting_type=check_lighting(lighting),
                      chim_lighting_type_selected_by=lighting_origin)
    return record
