# SPDX-License-Identifier: GPL-3.0-only
"""Resolve host-side build options from config/build-defaults.json: CLI > selected JSON > shipped defaults.

bitmap_paper_ink: paper text ink for bitmap-derived fonts.
follow_original_stair_rules: collide stairs and slopes by Morrowind's own rules (step up 34 units = 8.5 at our
scale, walkable slope up to 46 degrees, authored collision instead of convex shells). TRUE by default (owner
decision 2026-10-08); the converters read it through resolve_font_options()["follow_original_stair_rules"]."""
import hashlib
import json
from pathlib import Path

DEFAULT_CONFIG = Path(__file__).resolve().parents[1] / "config/build-defaults.json"
INK_MODES = ("filled", "original")


def add_font_options(parser):
    parser.add_argument("--build-config", type=Path,
                        help="JSON build settings (bitmap_paper_ink, follow_original_stair_rules); CLI overrides this file")
    stairs = parser.add_mutually_exclusive_group()
    stairs.add_argument("--follow-original-stair-rules", dest="follow_original_stair_rules", action="store_true", default=None,
                        help="Stairs and slopes collide by Morrowind's rules (default: on, from config/build-defaults.json)")
    stairs.add_argument("--no-follow-original-stair-rules", dest="follow_original_stair_rules", action="store_false",
                        help="DEBUGGING ONLY: use the older convex stair collision")
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
    unknown = set(values) - {"bitmap_paper_ink", "follow_original_stair_rules"}
    if unknown:
        raise ValueError(f"Unknown build config keys in {path}: {', '.join(sorted(unknown))}")
    if "bitmap_paper_ink" in values and values["bitmap_paper_ink"] not in INK_MODES:
        raise ValueError(f"Invalid bitmap_paper_ink in {path}: expected filled or original")
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
    cli = getattr(args, "bitmap_paper_ink", None)
    if cli is not None:
        if cli not in INK_MODES:
            raise ValueError("Bitmap paper ink must be filled or original")
        mode, origin = cli, "CLI override"
    return {"bitmap_paper_ink": mode, "selected_by": origin, "config_files": records,
            "follow_original_stair_rules": stairs, "follow_original_stair_rules_selected_by": stairs_origin}
