#!/usr/bin/env python3
"""Inspect a TES3 installation and export experimental Amiga terrain packets.

Inputs are read-only. Outputs are private, locally generated game data.
This is an area auditor, not an OpenMW replacement or a playable runtime.
"""
import argparse
import hashlib
import json
import math
import struct
from collections import Counter
from pathlib import Path

from .esm import FormatError, is_deleted, records, require, string, subrecords  # noqa: F401  (re-exported)


def decode_heights(data):
    require(len(data) == 4232, "Expected 4232-byte VHGT")
    base = struct.unpack_from("<f", data)[0]
    require(math.isfinite(base), "Nonfinite terrain height")
    deltas = struct.unpack_from("<4225b", data, 4)
    heights = []
    for y in range(65):
        base += deltas[y * 65]
        value = base
        row = [value * 8]
        for x in range(1, 65):
            value += deltas[y * 65 + x]
            row.append(value * 8)
        heights.append(row)
    return heights


def decode_materials(data):
    require(len(data) == 512, "Expected 512-byte VTEX")
    src = struct.unpack("<256H", data)
    return [[src[((y // 4) * 4 + x // 4) * 16 + (y % 4) * 4 + x % 4]
             for x in range(16)] for y in range(16)]


def normpath(name):
    return name.replace("\\", "/").lower()


class BSA:
    """Read the uncompressed TES3 BSA directory without loading its assets."""
    def __init__(self, path):
        self.path = path
        size = path.stat().st_size
        with path.open("rb") as f:
            header = f.read(12)
            require(len(header) == 12, "Truncated BSA header")
            version, directory_size, count = struct.unpack("<III", header)
            require(version == 0x100, "Only TES3 BSA format is supported")
            start = 12 + directory_size + count * 8
            require(count * 12 <= directory_size and start <= size, "Invalid BSA directory")
            table = f.read(directory_size)
        names = table[count * 12:]
        self.entries = {}
        for i in range(count):
            length, offset = struct.unpack_from("<II", table, i * 8)
            name_offset = struct.unpack_from("<I", table, count * 8 + i * 4)[0]
            require(name_offset < len(names), "BSA filename offset out of range")
            end = names.find(b"\0", name_offset)
            require(end >= 0, "Unterminated BSA filename")
            name = normpath(string(names[name_offset:end], "BSA filename"))
            require(name not in self.entries, f"Duplicate BSA path: {name}")
            require(start + offset + length <= size, "BSA asset overruns archive")
            self.entries[name] = {"bytes": length, "offset": start + offset}


def cell_data(subs):
    header = {}
    refs = []
    ref = None
    for tag, data in subs:
        require(tag not in ("MVRF", "CNDT"), "Moved references require a full content loader")
        if tag == "FRMR":
            require(len(data) == 4, "Unsupported reference number")
            ref = {"number": struct.unpack("<I", data)[0], "scale": 1.0}
            refs.append(ref)
        elif ref is None:
            header[tag] = data
        elif tag == "NAME":
            ref["id"] = string(data, "reference NAME")
        elif tag == "DATA":
            require(len(data) == 24, "Invalid reference transform")
            values = struct.unpack("<6f", data)
            require(all(math.isfinite(x) for x in values), "Nonfinite reference transform")
            ref["position"] = list(values[:3])
            ref["rotation_radians"] = list(values[3:])
        elif tag == "XSCL":
            require(len(data) == 4, "Invalid reference scale")
            ref["scale"] = struct.unpack("<f", data)[0]
            require(math.isfinite(ref["scale"]), "Nonfinite reference scale")
        elif tag == "DELE":
            ref["deleted"] = True
        elif tag == "DODT":
            require(len(data) == 24, "Invalid door destination")
            values = struct.unpack("<6f", data)
            require(all(math.isfinite(x) for x in values), "Nonfinite door destination")
            ref["destination"] = {"position": list(values[:3]), "rotation_radians": list(values[3:])}
        elif tag == "DNAM":
            ref["destination_cell"] = string(data, "reference DNAM")
    require(len(header.get("DATA", b"")) == 12, "Invalid CELL header")
    flags, x, y = struct.unpack("<Iii", header["DATA"])
    return {"name": string(header.get("NAME", b""), "CELL NAME"), "flags": flags,
            "x": x, "y": y, "refs": refs, "region": string(header.get("RGNN", b""), "CELL RGNN")}


def load_esm(path, dialogue_search=""):
    data = path.read_bytes()
    counts = Counter()
    cells, lands, objects, textures, voice_matches = {}, {}, {}, {}, []
    topic = ""
    expected = None
    object_tags = set("STAT DOOR MISC WEAP CONT CREA LIGH NPC_ ARMO CLOT REPA ACTI APPA LOCK PROB INGR BOOK ALCH LEVI LEVC".split())
    for tag, flags, payload in records(data):
        counts[tag] += 1
        subs = list(subrecords(payload))
        s = dict(subs)
        if tag == "TES3":
            require(counts[tag] == 1 and sum(counts.values()) == 1, "Invalid TES3 header position")
            require(len(s.get("HEDR", b"")) == 300, "Invalid TES3 HEDR")
            require(not any(t == "MAST" for t, _ in subs), "Use a standalone base master, not a plugin")
            expected = struct.unpack_from("<I", s["HEDR"], 296)[0]
        elif tag == "CELL":
            cell = cell_data(subs)
            if not cell["flags"] & 1:
                key = (cell["x"], cell["y"])
                require(key not in cells, "Duplicate exterior cell")
                cells[key] = cell
        elif tag == "LAND":
            require(len(s.get("INTV", b"")) == 8, "Invalid LAND location")
            key = struct.unpack("<ii", s["INTV"])
            require(key not in lands, "Duplicate LAND record")
            if "VHGT" in s and not is_deleted(flags, s):
                lands[key] = {"heights": decode_heights(s["VHGT"]),
                              "materials": decode_materials(s["VTEX"]) if "VTEX" in s else [[0] * 16 for _ in range(16)]}
        elif tag == "LTEX" and not is_deleted(flags, s):
            index = struct.unpack("<I", s["INTV"])[0] + 1
            textures[index] = {"id": string(s["NAME"], "LTEX NAME"), "texture": string(s["DATA"], "LTEX DATA")}
        elif tag in object_tags and "NAME" in s and not is_deleted(flags, s):
            key = string(s["NAME"], tag + " NAME").casefold()
            require(key not in objects, f"Duplicate object ID: {key}")
            objects[key] = {"type": tag, "model": string(s.get("MODL", b""), tag + " MODL"),
                            "display_name": string(s.get("FNAM", b""), tag + " FNAM")}
        elif tag == "DIAL":
            topic = string(s.get("NAME", b""), "DIAL NAME")
        elif tag == "INFO" and dialogue_search and dialogue_search.casefold() in string(s.get("NAME", b""), "INFO NAME").casefold():
            voice_matches.append({"topic": topic, "id": string(s["INAM"], "INFO INAM"),
                                  "text": string(s["NAME"], "INFO NAME"), "sound": string(s.get("SNAM", b""), "INFO SNAM"),
                                  "race": string(s.get("RNAM", b""), "INFO RNAM"), "faction": string(s.get("FNAM", b""), "INFO FNAM")})
    require(counts["TES3"] == 1, "Missing TES3 header")
    require(expected == sum(counts.values()) - 1, "HEDR record count mismatch")
    return {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data), "counts": dict(counts),
            "cells": cells, "lands": lands, "objects": objects, "textures": textures,
            "voice_matches": voice_matches}


def terrain_packet(land, cx, cy, tx, ty, stride):
    """24-byte header, int16 heights, byte materials; pad to 32-byte boundary."""
    n = 16 // stride + 1
    values = [land["heights"][ty * 16 + y][tx * 16 + x] / 8
              for y in range(0, 17, stride) for x in range(0, 17, stride)]
    require(all(v == int(v) and -32768 <= v <= 32767 for v in values), "Height cannot fit int16 / 8")
    heights = struct.pack(">" + "h" * len(values), *(int(v) for v in values))
    mats = [land["materials"][(ty * 16 + y + stride // 2) // 4][(tx * 16 + x + stride // 2) // 4]
            for y in range(0, 16, stride) for x in range(0, 16, stride)]
    require(all(0 <= v <= 255 for v in mats), "Material index cannot fit uint8")
    payload = heights + bytes(mats)
    header = struct.pack(">4sHHiiHHI", b"MWT0", 1, n, cx * 4 + tx, cy * 4 + ty,
                         stride * 128, 8, len(payload))
    packet = header + payload
    return packet + bytes((-len(packet)) % 32)


def json_write(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


# Height of a cell without a LAND record (OpenMW's ESM::Land::DEFAULT_HEIGHT, world units): open sea
# cells of the base master hold wrecks, rocks and kelp over a flat seabed at this depth.
DEFAULT_LAND_HEIGHT = -2048


def default_land():
    """Flat land of a cell without a LAND record: DEFAULT_LAND_HEIGHT, default terrain material."""
    return {"heights": [[DEFAULT_LAND_HEIGHT] * 65 for _ in range(65)], "materials": [[0] * 16 for _ in range(16)],
            "default": True}


def audit(data_files, out, center, radius, stride, dialogue_search="", missing_land=None):
    """missing_land: None refuses a square with cells without land; 'flat' gives them default_land()."""
    from .paths import ensure_external, resolve_data_files, child_ci
    data_files = resolve_data_files(data_files)
    out = ensure_external(out, "output")
    require(stride in (1, 2, 4, 8), "Invalid terrain stride")
    require(not out.exists(), "Choose a new output directory; existing data is never overwritten")
    require(radius >= 0 and radius <= 8, "Radius must be between 0 and 8")
    esm = load_esm(child_ci(data_files, "Morrowind.esm"), dialogue_search)
    bsa = BSA(child_ci(data_files, "Morrowind.bsa"))
    selected = [(x, y) for y in range(center[1] - radius, center[1] + radius + 1)
                for x in range(center[0] - radius, center[0] + radius + 1)]
    require(missing_land in (None, "flat"), "missing_land must be None or 'flat'")
    defaulted = [p for p in selected if p not in esm["lands"]]
    if missing_land == "flat":
        for p in defaulted:
            esm["lands"][p] = default_land()
    else:
        require(not defaulted, "Selected square has missing terrain; choose a smaller region")
    placements, cells, models, missing, types, materials = [], [], set(), set(), Counter(), set()
    packets, index, grids = bytearray(), [], []
    seam_pairs, seam_max = 0, 0
    for cx, cy in selected:
        land = esm["lands"][(cx, cy)]
        cell = esm["cells"].get((cx, cy), {"name": "", "region": "", "refs": []})
        refs = [r for r in cell["refs"] if not r.get("deleted")]
        cells.append({"x": cx, "y": cy, "name": cell["name"], "region": cell["region"], "references": len(refs)})
        for ref in refs:
            require("id" in ref and "position" in ref, "Incomplete placed reference")
            obj = esm["objects"].get(ref["id"].casefold())
            if obj is None:
                missing.add(ref["id"])
            else:
                types[obj["type"]] += 1
                if obj["model"]:
                    models.add("meshes/" + normpath(obj["model"]))
            placements.append({"cell": [cx, cy], **ref, **(obj or {})})
        for tx, ty in ((x, y) for y in range(4) for x in range(4)):
            packet = terrain_packet(land, cx, cy, tx, ty, stride)
            index.append({"chunk": [cx * 4 + tx, cy * 4 + ty], "offset": len(packets), "bytes": len(packet)})
            packets.extend(packet)
        grids.append({"cell": [cx, cy], **{k: v for k, v in land.items() if k != "default"}})
        materials.update(v for row in land["materials"] for v in row)
        for neighbor, edge, other in [((cx + 1, cy), [r[-1] for r in land["heights"]], "west"),
                                     ((cx, cy + 1), land["heights"][-1], "south")]:
            if neighbor in selected:
                h = esm["lands"][neighbor]["heights"]
                seam = [r[0] for r in h] if other == "west" else h[0]
                seam_pairs += 1
                seam_max = max(seam_max, max(abs(a - b) for a, b in zip(edge, seam)))
    manifest = [{"path": m, **bsa.entries.get(m, {"missing": True})} for m in sorted(models)]
    profiles = []
    for step in (1, 2, 4, 8):
        n = 16 // step + 1
        packet_size = len(terrain_packet(esm["lands"][selected[0]], *selected[0], 0, 0, step))
        profiles.append({"source_grid_stride": step, "vertices_per_chunk": n * n,
                         "triangles_per_chunk": (n - 1) ** 2 * 2,
                         "bytes_per_chunk": packet_size, "region_bytes": len(index) * packet_size})
    summary = {
        "input": {"esm_bytes": esm["bytes"], "esm_sha256": esm["sha256"], "records": esm["counts"],
                  "bsa_bytes": bsa.path.stat().st_size, "bsa_entries": len(bsa.entries),
                  "bsa_folders": dict(Counter(p.split('/')[0] for p in bsa.entries))},
        "area": {"center": center, "radius_cells": radius, "cells": cells, "chunks": len(index),
                 "references": len(placements), "reference_types": dict(types), "missing_object_ids": sorted(missing),
                 "direct_unique_models": len(models), "direct_model_bytes": sum(m.get("bytes", 0) for m in manifest),
                 "missing_direct_models": [m["path"] for m in manifest if m.get("missing")],
                 "terrain_material_ids": sorted(materials),
                 "default_land_cells": [list(p) for p in defaulted] if missing_land == "flat" else []},
        "terrain": {"selected_stride": stride, "packet_stream_bytes": len(packets), "profiles": profiles,
                    "neighbor_seams_checked": seam_pairs, "max_seam_error_world_units": seam_max,
                    "note": "Height and material IDs only; no texture blending, meshes, sprites, collision structures or runtime memory included."},
        "dialogue_matches": esm["voice_matches"],
        "audio": {"bsa_audio_entries": sum(p.startswith(("sound/", "music/")) for p in bsa.entries),
                  "pcm_profiles": [{"sample_rate": rate, "channels": ch, "bytes_per_second": rate * ch,
                                    "buffer_16k_seconds": 16384 / (rate * ch)}
                                   for rate, ch in [(11025, 1), (22050, 1), (22050, 2)]]},
        "limitations": ["Standalone base master only; no plugin load order or moved-reference processing.",
                        "Direct MODL dependencies only; no NIF texture scan, body-part assembly, inventory, script or leveled-list dependency traversal.",
                        "Material IDs select one source terrain layer per quad; no baked appearance yet.",
                        "Dialogue lookup is evidence of assets, not implementation of its conditions.",
                        "No Amiga renderer, executable, disk driver, timings or RAM high-water measurement."]}
    out.mkdir(parents=True)
    (out / "terrain.mwt").write_bytes(packets)
    json_write(out / "terrain-index.json", index)
    json_write(out / "terrain-source.json", grids)
    json_write(out / "placements.json", placements)
    json_write(out / "direct-models.json", manifest)
    json_write(out / "materials.json", {i: esm["textures"].get(i, {"id": "default", "texture": None}) for i in sorted(materials)})
    json_write(out / "audit.json", summary)
    print(json.dumps({"output": str(out), "cells": len(cells), "references": len(placements),
                      "terrain_bytes": len(packets), "unique_models": len(models),
                      "direct_model_bytes": summary["area"]["direct_model_bytes"]}, indent=2))
