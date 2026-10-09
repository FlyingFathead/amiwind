#!/usr/bin/env python3
"""Check each exported vertex/material against the decoded source grids."""
import argparse
import json
import struct
from pathlib import Path


def verify(area):
    from .paths import ensure_external
    area = ensure_external(area, "area data")
    data = (area / "terrain.mwt").read_bytes()
    index = json.loads((area / "terrain-index.json").read_text())
    grids = {tuple(g["cell"]): g for g in json.loads((area / "terrain-source.json").read_text())}
    position = checked_heights = checked_materials = 0
    for entry in index:
        if entry["offset"] != position:
            raise ValueError("Noncontiguous packet index")
        packet = data[position:position + entry["bytes"]]
        magic, version, n, x, y, spacing, scale, length = struct.unpack_from(">4sHHiiHHI", packet)
        if (magic, version, scale) != (b"MWT0", 1, 8) or [x, y] != entry["chunk"]:
            raise ValueError("Packet header mismatch")
        if n not in (3, 5, 9, 17) or spacing * (n-1) != 2048:
            raise ValueError("Invalid packet dimensions")
        if length != 2*n*n + (n-1)**2 or len(packet) != ((24+length+31)//32)*32:
            raise ValueError("Invalid packet size")
        if any(packet[24+length:]):
            raise ValueError("Nonzero packet padding")
        cx, tx = divmod(x, 4)
        cy, ty = divmod(y, 4)
        source = grids[(cx, cy)]
        stride = spacing // 128
        heights = struct.unpack_from(">"+"h"*(n*n), packet, 24)
        for vy in range(n):
            for vx in range(n):
                expected = source["heights"][ty*16+vy*stride][tx*16+vx*stride]
                if heights[vy*n+vx]*scale != expected:
                    raise ValueError("Packed height differs from source")
                checked_heights += 1
        materials = packet[24+2*n*n:24+length]
        for qy in range(n-1):
            for qx in range(n-1):
                expected = source["materials"][(ty*16+qy*stride+stride//2)//4][(tx*16+qx*stride+stride//2)//4]
                if materials[qy*(n-1)+qx] != expected:
                    raise ValueError("Packed material differs from source")
                checked_materials += 1
        position += len(packet)
    if position != len(data):
        raise ValueError("Trailing unindexed packet bytes")
    result = {"packets_checked": len(index), "heights_checked": checked_heights,
              "materials_checked": checked_materials, "bytes_checked": position, "status": "passed"}
    print(json.dumps(result, indent=2))
    return result
