#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Build the small procedural dark torch room without source-game assets.

The game's palette supplies indices, not texture artwork. Retain nonempty,
valid all-zero lightmaps so renderer fallback/fullbright cannot fake darkness.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess

from player_hull import lumps, pack_lumps, rebuild_world_hull, PROFILE


def validate(raw):
    data = lumps(raw)
    if not data[8] or any(data[8]):
        raise ValueError('Torch room must have nonempty all-zero lighting')
    if len(data[7]) < 6*20 or len(data[7]) % 20:
        raise ValueError('Torch room face table is invalid')
    for at in range(0, len(data[7]), 20):
        offset = struct.unpack_from('<i', data[7], at+16)[0]
        if data[7][at+12] == 255 or not 0 <= offset < len(data[8]):
            raise ValueError('Torch room face lacks valid light samples')
    entities = bytes(data[0])
    if b'"_aw_sky_mode" "interior"' not in entities or b'"aw_hull" "'+PROFILE.encode()+b'"' not in entities:
        raise ValueError('Torch room classification or standing hull missing')
    if b'"classname" "light"' in entities or b'sky' in bytes(data[2]).lower():
        raise ValueError('Torch room must have no lights or sky texture')
    return {'faces': len(data[7])//20, 'lighting_bytes': len(data[8]),
            'zero_lighting': True, 'standing_hull': PROFILE,
            'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def build(palette, output, work, qbsp, vis, light):
    from PIL import Image
    from prepare_quake import box, miptex, wad
    output, work = Path(output), Path(work)
    work.mkdir(parents=True, exist_ok=False)
    palette = Path(palette).read_bytes()
    if len(palette) != 768:
        raise ValueError('Game palette must contain 256 RGB colours')
    colours = [min(range(224), key=lambda i: sum((palette[i*3+j]-v)**2 for j in range(3))) for v in (110, 190)]
    texture = Image.new('P', (32,32))
    texture.putdata([colours[0 if x%16==0 or y%16==0 else 1] for y in range(32) for x in range(32)])
    (work/'torchroom.wad').write_bytes(wad([('torchwall', 68, miptex('torchwall', texture))]))
    walls = [((-144,-112,-16),(144,112,0)), ((-144,-112,128),(144,112,144)),
             ((-144,-112,0),(-128,112,128)), ((128,-112,0),(144,112,128)),
             ((-128,-112,0),(128,-96,128)), ((-128,96,0),(128,112,128))]
    text = ['{', '"classname" "worldspawn"', '"wad" "torchroom.wad"',
            '"message" "Dark torch test"', '"_aw_sky_mode" "interior"', '"_minlight" "16"']
    text += [box(lo, hi, 'torchwall') for lo, hi in walls]
    text += ['}', '{', '"classname" "info_player_start"', '"origin" "64 0 17"', '"angle" "180"', '}']
    map_path = work/'torchtest.map';map_path.write_text('\n'.join(text)+'\n', encoding='ascii')
    # ericw 0.18.1 discards a uniform minlight-1 map as empty. Compile at 16
    # solely to allocate valid sample ranges; zero every byte before staging.
    commands = [[str(Path(qbsp).resolve()), '-nopercent', map_path.name],
                [str(Path(vis).resolve()), '-threads', '1', 'torchtest.bsp'],
                [str(Path(light).resolve()), '-threads', '1', '-minlight', '16', 'torchtest.bsp']]
    with (work/'compile.log').open('w') as log:
        for command in commands:
            subprocess.run(command, cwd=work, stdout=log, stderr=subprocess.STDOUT, check=True)
    bsp = work/'torchtest.bsp'
    rebuild_world_hull(bsp, map_path, qbsp)
    data = lumps(bsp.read_bytes())
    if not data[8]:
        raise ValueError('Light compiler produced no samples; refuse fullbright room')
    data[0] = data[0].replace(b'"_minlight" "16"', b'"_minlight" "0"')
    data[8] = bytearray(len(data[8]))
    raw = pack_lumps(data);report = validate(raw)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(raw)
    if output.read_bytes() != raw:
        raise ValueError('Torch room readback differs')
    report.update(format='AmiWind procedural dark torch room 1', commands=commands,
                  room_bounds=[[-128,-96,0],[128,96,128]], palette_sha256=hashlib.sha256(palette).hexdigest(),
                  source='Procedural six-brush room and grid artwork; no source-game textures',
                  native_acceptance='pending target playtest')
    (work/'receipt.json').write_text(json.dumps(report, indent=2)+'\n')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('palette','output','work','qbsp','vis','light'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.palette,args.output,args.work,args.qbsp,args.vis,args.light),indent=2))


if __name__ == '__main__':
    main()
