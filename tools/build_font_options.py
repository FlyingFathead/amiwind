# SPDX-License-Identifier: GPL-3.0-only
"""Resolve build settings: CLI > selected JSON (--build-config) > shipped defaults.

The shipped defaults are config/build-defaults.json:
bitmap_paper_ink: paper text ink for bitmap-derived fonts.
follow_original_stair_rules: collide stairs and slopes by Morrowind's own rules (step up 34 units = 8.5 at our
scale, walkable slope up to 46 degrees, authored collision instead of convex shells). TRUE by default (owner
decision 2026-10-08); the converters read it through resolve_font_options()["follow_original_stair_rules"].
builder: legacy or chim, with chim_areas, the areas the CHIM builder writes.
chim_texture_effects: CHIM texture effects (.chimfx paths or shipped names, tools/chim/effects) the CHIM
builder applies, in order; none by default (docs/chim/TEXTURE_EFFECTS.md).
model_hull: how a placed model's standing hull is written when qbsp does not compile it (tools/routed_hull.py):
auto (default: routed above 16 convex pieces, INTERIOR-HULL-CHAIN-33 / CHIM-HULL-CHAIN-COST-33), chain (every piece
in one chain, the converters' earlier form), routed (every model) or balanced (the first routing, kept selectable).
heap_mb: the game heap (Quake's Hunk) in MiB, used exactly as asked like --jobs; not in the shipped defaults:
the engine source's AMIWIND_HEAP_MB is the default (tools/project_version.heap_plan)."""
import hashlib
import json
from pathlib import Path

DEFAULT_CONFIG = Path(__file__).resolve().parents[1] / "config/build-defaults.json"
INK_MODES = ("filled", "original")
BUILDERS = ("legacy", "chim")
MODEL_HULLS = ("auto", "chain", "routed", "balanced", "compiled")
KNOWN_KEYS = {"bitmap_paper_ink", "follow_original_stair_rules", "builder", "chim_areas", "chim_texture_effects",
              "heap_mb", "model_hull", "chim_stream_statics"}


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
    if "heap_mb" in values and (isinstance(values["heap_mb"], bool) or not isinstance(values["heap_mb"], int)):
        raise ValueError(f"Invalid heap_mb in {path}: expected a whole number of MiB")
    if "chim_stream_statics" in values and not isinstance(values["chim_stream_statics"], bool):
        raise ValueError(f"Invalid chim_stream_statics in {path}: expected true or false")
    if "model_hull" in values and values["model_hull"] not in MODEL_HULLS:
        raise ValueError(f"Invalid model_hull in {path}: expected auto, chain, routed, balanced or compiled")
    if "follow_original_stair_rules" in values and not isinstance(values["follow_original_stair_rules"], bool):
        raise ValueError(f"Invalid follow_original_stair_rules in {path}: expected true or false")
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
    stream, stream_origin = bool(defaults.get("chim_stream_statics", False)), "shipped default"
    if selected is not None and "chim_stream_statics" in values:
        stream, stream_origin = values["chim_stream_statics"], "build config"
    if getattr(args, "chim_stream_statics", None) is not None:
        stream, stream_origin = bool(args.chim_stream_statics), "CLI override"
    cli = getattr(args, "bitmap_paper_ink", None)
    if cli is not None:
        if cli not in INK_MODES:
            raise ValueError("Bitmap paper ink must be filled or original")
        mode, origin = cli, "CLI override"
    return {"bitmap_paper_ink": mode, "selected_by": origin, "config_files": records,
            "follow_original_stair_rules": stairs, "follow_original_stair_rules_selected_by": stairs_origin,
            "model_hull": hull, "model_hull_selected_by": hull_origin,
            "chim_stream_statics": stream, "chim_stream_statics_selected_by": stream_origin}


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


def add_builder_options(parser):
    parser.add_argument("--builder", choices=BUILDERS, default=None,
                        help="Exterior world pipeline: chim (default from v0.0.33, with the CHIM areas of "
                             "config/build-defaults.json: Balmora and Seyda Neen; the CHIM world streamer: every "
                             "asset stored once; docs/chim/WORLD_FORMAT.md) or legacy (overlapping region maps)")
    parser.add_argument("--chim-area", dest="chim_areas", action="append", default=None, metavar="TOWN",
                        help="With --builder chim: a town from config/towns.json the CHIM world holds "
                             "(repeatable; default from the build config)")
    parser.add_argument("--chim-texture-effect", dest="chim_texture_effects", action="append", default=None,
                        metavar="EFFECT",
                        help="With --builder chim: apply a CHIM texture effect (a .chimfx file or a shipped name such "
                             "as autumn_glitter_leaves; repeatable, in order). Off by default; replaces the build "
                             "config's list (docs/chim/TEXTURE_EFFECTS.md)")


def resolve_builder(args):
    """The builder type and, for chim, its areas and versions: CLI > --build-config > shipped defaults."""
    defaults, default_record = _read(DEFAULT_CONFIG)
    for key in ("builder", "chim_areas"):
        if key not in defaults:
            raise ValueError("Shipped build defaults must define " + key)
    builder, areas, origin = defaults["builder"], list(defaults["chim_areas"]), "shipped default"
    effects = list(defaults.get("chim_texture_effects", []))
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
    if getattr(args, "builder", None) is not None:
        builder, origin = args.builder, "CLI override"
    if getattr(args, "chim_areas", None):
        areas = list(dict.fromkeys(args.chim_areas))
    if getattr(args, "chim_texture_effects", None):
        effects = list(args.chim_texture_effects)
    record = {"builder": builder, "selected_by": origin, "config_files": records,
              "chim_version": None, "world_format": None, "chim_areas": [], "chim_texture_effects": []}
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
        record.update(chim_version=CHIM_VERSION, world_format="%d.%d" % FORMAT_VERSION, chim_areas=areas,
                      chim_texture_effects=loaded)
    return record
