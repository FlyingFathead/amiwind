# SPDX-License-Identifier: GPL-3.0-only
"""Resolve host-side paper font options: CLI > selected JSON > shipped defaults."""
import hashlib
import json
from pathlib import Path

DEFAULT_CONFIG = Path(__file__).resolve().parents[1] / "config/build-defaults.json"
INK_MODES = ("filled", "original")


def add_font_options(parser):
    parser.add_argument("--build-config", type=Path,
                        help="JSON build settings (currently bitmap_paper_ink); CLI overrides this file")
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
    unknown = set(values) - {"bitmap_paper_ink"}
    if unknown:
        raise ValueError(f"Unknown build config keys in {path}: {', '.join(sorted(unknown))}")
    if "bitmap_paper_ink" in values and values["bitmap_paper_ink"] not in INK_MODES:
        raise ValueError(f"Invalid bitmap_paper_ink in {path}: expected filled or original")
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
    cli = getattr(args, "bitmap_paper_ink", None)
    if cli is not None:
        if cli not in INK_MODES:
            raise ValueError("Bitmap paper ink must be filled or original")
        mode, origin = cli, "CLI override"
    return {"bitmap_paper_ink": mode, "selected_by": origin, "config_files": records}
