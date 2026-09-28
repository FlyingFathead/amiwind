"""Read-only preflight of an installed game tree and TES3 containers."""
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import struct

from .audit import BSA
from .paths import child_ci, ensure_external, installed_game_path, resolve_data_files

REFERENCE_DIR = Path(__file__).resolve().parents[2] / "config/input-reference"


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def reference_files():
    manifest = json.loads((REFERENCE_DIR / "reference.json").read_text())
    files = {}
    for shard in manifest["shards"]:
        files.update(json.loads((REFERENCE_DIR / shard).read_text()))
    return files


def matches_core(data):
    """A detected installation is offered only if both core files match."""
    records = json.loads((REFERENCE_DIR / "reference.json").read_text())["core"]
    for name, reference in records.items():
        path = child_ci(data, name)
        if path.stat().st_size != reference["bytes"] or digest(path) != reference["sha256"]:
            return False
    return True


def fingerprints(loose, stage, reference=None):
    reference = reference_files() if reference is None else reference
    result = {"matching": 0, "different": [], "missing": [], "optional_differences": [], "extra": 0}
    for name, expected in reference.items():
        core = name in ("morrowind.esm", "morrowind.bsa")
        if stage == "terrain" and not core:
            continue
        required = core or name.startswith(("sound/", "music/"))
        item = loose.get(name)
        if item is None:
            if required:
                result["missing"].append(name)
            continue
        if item["bytes"] == expected["bytes"] and digest(item["path"]) == expected["sha256"]:
            result["matching"] += 1
        else:
            result["different" if required else "optional_differences"].append(name)
    result["extra"] = sum(name not in reference for name in loose)
    return result


def master_structure(path):
    """Walk every record and subrecord boundary without decoding game assets."""
    size = path.stat().st_size
    count = 0
    expected = None
    with path.open("rb") as stream:
        while stream.tell() < size:
            header = stream.read(16)
            if len(header) != 16:
                raise ValueError("Truncated ESM record header")
            tag, length, _, _ = struct.unpack("<4sIII", header)
            end = stream.tell() + length
            if end > size or (count == 0 and tag != b"TES3") or (count and tag == b"TES3"):
                raise ValueError("Invalid ESM record boundary/header")
            while stream.tell() < end:
                if stream.tell() + 8 > end:
                    raise ValueError("Truncated ESM subrecord header")
                sub, length = struct.unpack("<4sI", stream.read(8))
                if stream.tell() + length > end:
                    raise ValueError("ESM subrecord overruns its record")
                if count == 0 and sub == b"HEDR":
                    if length != 300 or expected is not None:
                        raise ValueError("Invalid ESM HEDR")
                    expected = struct.unpack_from("<I", stream.read(length), 296)[0]
                elif count == 0 and sub == b"MAST":
                    raise ValueError("Expected the standalone base master, not a plugin")
                else:
                    stream.seek(length, 1)
            count += 1
    if expected is None or expected != count - 1:
        raise ValueError("ESM record count does not match its header")
    return count


def locate_data_files(selected, notify=None, choose=None, max_depth=4, max_dirs=2000):
    """Find a core-file pair before inventory; never hash an arbitrary parent."""
    say = notify or (lambda message: None)
    try:
        return resolve_data_files(selected)
    except ValueError:
        pass
    say(f"Core game files not found directly in {selected} or its Data Files folder.")
    say(f"Looking in subdirectories (up to {max_depth} levels; directory symlinks are not followed)...")
    candidates = []
    visited = 0
    def walk_error(exc):
        raise exc
    for parent, dirs, files in os.walk(selected, onerror=walk_error, followlinks=False):
        visited += 1
        if visited > max_dirs:
            raise ValueError(f"Game-directory search reached {max_dirs} folders; select a more specific installation directory")
        parent = Path(parent)
        names = {name.casefold() for name in files}
        if {'morrowind.esm', 'morrowind.bsa'} <= names:
            # The strict resolver also rejects ambiguous case and unsafe paths.
            candidates.append(resolve_data_files(parent))
            dirs[:] = []
        elif len(parent.relative_to(selected).parts) >= max_depth:
            dirs[:] = []
        else:
            dirs[:] = sorted(name for name in dirs if not (parent / name).is_symlink())
    candidates = sorted(set(candidates))
    if not candidates:
        raise ValueError(f"No folder containing Morrowind.esm and Morrowind.bsa found within {max_depth} levels of {selected}. Select your installation root or Data Files directory")
    if len(candidates) > 1:
        if choose is None:
            raise ValueError("Multiple Morrowind installations found; select one explicitly with --data-files:\n  - " + "\n  - ".join(map(str, candidates)))
        data = choose(candidates)
        if data not in candidates:
            raise ValueError("No discovered Morrowind installation was selected")
    else:
        data = candidates[0]
    say(f"Found candidate: {data}")
    say("Checking this folder's containers, required assets, file sizes and reference SHA-256 hashes next.")
    return data


def inspect(path, stage="aga", allow_differences=False, reference=None, notify=None, choose=None):
    selected = ensure_external(installed_game_path(path), "game installation")
    if not selected.is_dir():
        raise ValueError(f"Game installation is not a directory: {selected}")
    data = locate_data_files(selected, notify=notify, choose=choose)
    errors, warnings, checks = [], [], []
    loose = {}
    # os.walk gives explicit errors, unlike silently skipped unreadable folders.
    def walk_error(exc):
        raise exc
    for parent, dirs, files in os.walk(data, onerror=walk_error, followlinks=False):
        for name in dirs:
            if (Path(parent) / name).is_symlink():
                errors.append("Directory symlink is not scanned: " + str(Path(parent) / name))
        for name in files:
            candidate = Path(parent) / name
            key = candidate.relative_to(data).as_posix().casefold()
            checked = ensure_external(candidate, "game input")
            if key in loose:
                errors.append("Ambiguous case-insensitive input path: " + key)
            if not checked.is_file():
                errors.append("Expected a regular input file: " + key)
                continue
            loose[key] = {"path": checked, "bytes": checked.stat().st_size}
    archive = {}
    for name in ("Morrowind.esm", "Morrowind.bsa"):
        item = loose.get(name.casefold())
        if not item or not item["bytes"]:
            errors.append("Missing or empty required input: " + name)
            continue
        try:
            if name.endswith(".esm"):
                checks.append(f"{name}: {master_structure(item['path'])} record boundaries checked")
            else:
                archive = BSA(item["path"]).entries
                checks.append(f"{name}: {len(archive)} archive entries and byte ranges checked")
        except (OSError, ValueError, UnicodeError, struct.error) as exc:
            errors.append(f"{name}: {exc}")
    categories = Counter(key.split('/')[0] for key in loose)
    packed = Counter(key.split('/')[0] for key in archive)
    if stage == "aga":
        for group in ("meshes", "textures"):
            if not any(key.startswith(group + "/") and info["bytes"] for key, info in archive.items()):
                errors.append(f"Morrowind.bsa has no nonempty {group}/ assets required by the static scene converter")
        music = [key for key in loose if key.startswith("music/") and key.endswith(".mp3")]
        if not 1 <= len(music) <= 99:
            errors.append("Music/: current converter requires 1–99 MP3 files")
        if not any(key.startswith("music/explore/") and loose[key]["bytes"] for key in music):
            errors.append("Music/Explore/: no nonempty exploration MP3 files")
        for key in music:
            if not loose[key]["bytes"]:
                errors.append("Empty required music input: " + key)
        combined = {**archive, **loose}
        if not any(key.startswith("sound/vo/") and info["bytes"] for key, info in combined.items()):
            errors.append("Sound/Vo/: no nonempty voice assets in loose files or Morrowind.bsa")
    if not categories["fonts"]:
        warnings.append("Fonts/ absent: optional for the current build; needed for future original-font conversion")
    empty = sum(not item["bytes"] for item in loose.values())
    if empty:
        warnings.append(f"{empty} empty loose files found; required inputs are checked separately")
    known = fingerprints(loose, stage, reference)
    differences = known["missing"] + known["different"]
    if differences:
        message = (f"Reference comparison: {len(known['missing'])} known files missing, "
                   f"{len(known['different'])} size/SHA-256 differences; " + ", ".join(differences[:6]))
        if len(differences) > 6:
            message += f" (and {len(differences)-6} more)"
        if allow_differences:
            warnings.append(message + "; continuing with explicitly allowed unverified data differences")
        else:
            errors.append(message + ". This may be another edition/language. Use --allow-data-differences only if intentional; structural errors still block the build")
    if known["optional_differences"]:
        warnings.append(f"{len(known['optional_differences'])} optional files differ from the reference")
    return {"data_files": str(data), "selected_root": str(selected), "loose_files": len(loose),
            "loose_bytes": sum(item["bytes"] for item in loose.values()),
            "loose_categories": dict(categories), "archive_categories": dict(packed),
            "checks": checks, "warnings": warnings, "errors": errors, "fingerprints": known}


def display(report):
    print("Game inputs: " + report["data_files"])
    print(f"  Scanned {report['loose_files']} loose files ({report['loose_bytes']:,} bytes)")
    known = report["fingerprints"]
    print(f"  [matching] {known['matching']} reference files: size and SHA-256")
    if known["extra"]:
        print(f"  [unrecognized] {known['extra']} additional files: no reference checksum")
    for message in report["checks"]:
        print("  [ok] " + message)
    for category in ("meshes", "textures", "sound", "music", "fonts"):
        print(f"  {category}/: {report['loose_categories'].get(category, 0)} loose, "
              f"{report['archive_categories'].get(category, 0)} archived")
    for kind in ("warnings", "errors"):
        for message in report[kind]:
            print(f"  [{'warning' if kind == 'warnings' else 'missing/invalid'}] {message}")
    print("Container structure and required asset groups checked; conversion validates individual referenced assets.")
    print("No game files changed. Executables, GOG extras and expansion/mod load orders are not build inputs.")
