"""Discover preferred loose TrueType fonts and Bethesda bitmap fallbacks."""
from pathlib import Path

from .paths import child_ci, resolve_data_files

GOG_GOTY_URL = "https://www.gog.com/en/game/the_elder_scrolls_iii_morrowind_goty_edition"

# The GOG GOTY installer used for AmiWind development supplies these loose
# BookArt TTFs in addition to Bethesda's normal Fonts/*.fnt + *.tex data.
# GOTHIC.TTF identifies itself as Century Gothic and is therefore the preferred
# vector source for both regular and large Century Gothic variants.
FAMILIES = {
    "magic": {
        "label": "Magic Cards",
        "ttf": "Magic Cards.ttf",
        "bitmap": "Magic_Cards_Regular.fnt",
        "atlas": "Magic_Cards_Regular_0_Lod_A.tex",
        "output": "magic",
    },
    "gothic": {
        "label": "Century Gothic",
        "ttf": "GOTHIC.TTF",
        "bitmap": "century_gothic_font_regular.fnt",
        "atlas": "century_gothic_font_regular_0_Lod_A.tex",
        "output": "gothic",
    },
    "gothic_big": {
        "label": "Century Gothic Big",
        "ttf": "GOTHIC.TTF",
        "bitmap": "century_gothic_big.fnt",
        "atlas": "century_gothic_big_0_Lod_A.tex",
        "output": "gothicbig",
    },
    "daedric": {
        "label": "Daedric",
        "ttf": "daedric_runes.ttf",
        "bitmap": "daedric_font.fnt",
        "atlas": "daedric_font_0_Lod_A.tex",
        "output": "daedric",
    },
}

PREFERRED_TTFS = ("Magic Cards.ttf", "GOTHIC.TTF", "daedric_runes.ttf")


def _optional_nested(root, directory, filename):
    parent = child_ci(root, directory, required=False)
    if parent is None or not parent.is_dir():
        return None
    path = child_ci(parent, filename, required=False)
    return path if path is not None and path.is_file() else None


def discover(data_files):
    """Return actual source paths for every known Morrowind font family."""
    data = resolve_data_files(data_files)
    result = {}
    for key, spec in FAMILIES.items():
        ttf = _optional_nested(data, "BookArt", spec["ttf"])
        bitmap = _optional_nested(data, "Fonts", spec["bitmap"])
        atlas = _optional_nested(data, "Fonts", spec["atlas"])
        result[key] = {
            **spec,
            "ttf_path": ttf,
            "bitmap_path": bitmap,
            "atlas_path": atlas,
            "bitmap_ready": bool(bitmap and atlas),
        }
    return result


def preferred_ttf_inventory(fonts):
    """Report each distinct preferred GOG TTF once, even when families share it."""
    found = {}
    for key, item in fonts.items():
        name = item["ttf"]
        if name not in found:
            found[name] = item["ttf_path"]
    return found


def usable(item):
    return bool(item["ttf_path"] or item["bitmap_ready"])


def source_mode(item):
    if item["ttf_path"]:
        return "ttf"
    if item["bitmap_ready"]:
        return "bitmap"
    return None


def public_inventory(fonts):
    """JSON-safe diagnostic inventory without leaking absolute owner paths."""
    preferred = preferred_ttf_inventory(fonts)
    return {
        "preferred_ttf": {
            name: bool(path) for name, path in preferred.items()
        },
        "families": {
            key: {
                "label": item["label"],
                "preferred_ttf": f"BookArt/{item['ttf']}",
                "ttf_found": bool(item["ttf_path"]),
                "bitmap_fnt": f"Fonts/{item['bitmap']}",
                "bitmap_atlas": f"Fonts/{item['atlas']}",
                "bitmap_ready": item["bitmap_ready"],
                "selected": source_mode(item),
            }
            for key, item in fonts.items()
        },
    }


def fallback_warnings(fonts):
    """User-facing warning when the preferred GOG vector-font set is incomplete."""
    preferred = preferred_ttf_inventory(fonts)
    missing = [name for name, path in preferred.items() if path is None]
    if not missing:
        return []
    usable_fallbacks = sorted({item["bitmap"] for item in fonts.values()
                               if item["ttf_path"] is None and item["bitmap_ready"]})
    messages = [
        "Preferred loose TrueType font assets were not found: " +
        ", ".join("BookArt/" + name for name in missing) + ".",
        "The Steam GOTY release normally does not include the loose TTF fonts present in the GOG GOTY release. "
        "AmiWind recommends the GOG GOTY edition and has been developed/tested primarily against that layout: " + GOG_GOTY_URL,
    ]
    if usable_fallbacks:
        messages.append(
            "Falling back to Bethesda's Fonts/*.fnt + *.tex bitmap-font data for the affected families. "
            "The build can continue, but rasterized font appearance may vary and may be inferior to the preferred GOG TTF conversion, "
            "especially at scaled or non-native sizes."
        )
    return messages
