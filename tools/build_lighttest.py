#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Build the light test corridor (LIGHTTEST-MAP-67, DBG-CYCLEITEMS-67; docs/ITEM_CYCLING.md): a long, dark procedural
corridor in every image (id1/maps/lighttest.bsp) with nothing in it but the player. dbg lighttest enters it (the game's
scripts paused, nothing drawn over the world but the held items' names), dbg lighttest 1 walks it for 20 seconds with a
look down at the hands, and dbg cycleitems puts every hand-holdable item of the game in the player's hands there in
turn. Built like the dark torch test room (tools/build_torchtest.py, which stays as it is): six brushes of the game
palette's grid, no source-game texture, no light entity, and valid lighting samples that are all zero, so only the held
light lights it."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess

from player_hull import lumps, pack_lumps, rebuild_world_hull, PROFILE
from vis_options import light_args

HALF_LENGTH = 2048      # along x: 20 s of walking or running from one end stays inside
HALF_WIDTH = 96
HEIGHT = 160
START = (-1984, 0, 17)  # at the west end, facing along the corridor (+x); the engine's AW_LIGHTTEST_START_X
ENTITIES = (b'worldspawn', b'info_player_start')


def validate(raw):
    data = lumps(raw)
    if not data[8] or any(data[8]):
        raise ValueError('Light test corridor must have nonempty all-zero lighting')
    if len(data[7]) < 6*20 or len(data[7]) % 20:
        raise ValueError('Light test corridor face table is invalid')
    for at in range(0, len(data[7]), 20):
        offset = struct.unpack_from('<i', data[7], at+16)[0]
        if data[7][at+12] == 255 or not 0 <= offset < len(data[8]):
            raise ValueError('Light test corridor face lacks valid light samples')
    entities = bytes(data[0])
    if b'"_aw_sky_mode" "interior"' not in entities or b'"aw_hull" "'+PROFILE.encode()+b'"' not in entities:
        raise ValueError('Light test corridor classification or standing hull missing')
    if b'sky' in bytes(data[2]).lower():
        raise ValueError('Light test corridor must have no sky texture')
    classes = tuple(part.split(b'"', 1)[0] for part in entities.split(b'"classname" "')[1:])
    if classes != ENTITIES:
        raise ValueError('Light test corridor must hold nothing but the player start: %r' % (classes,))
    return {'faces': len(data[7])//20, 'lighting_bytes': len(data[8]), 'zero_lighting': True,
            'standing_hull': PROFILE, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def build(palette, output, work, qbsp, vis, light):
    from PIL import Image
    from prepare_quake import box, miptex, wad
    output, work = Path(output), Path(work)
    work.mkdir(parents=True, exist_ok=False)
    palette = Path(palette).read_bytes()
    if len(palette) != 768:
        raise ValueError('Game palette must contain 256 RGB colours')
    colours = [min(range(224), key=lambda i: sum((palette[i*3+j]-v)**2 for j in range(3))) for v in (110, 190)]
    texture = Image.new('P', (32, 32))
    texture.putdata([colours[0 if x % 16 == 0 or y % 16 == 0 else 1] for y in range(32) for x in range(32)])
    (work/'lightcorridor.wad').write_bytes(wad([('lightwall', 68, miptex('lightwall', texture))]))
    x, y, h = HALF_LENGTH, HALF_WIDTH, HEIGHT
    walls = [((-x-16, -y-16, -16), (x+16, y+16, 0)), ((-x-16, -y-16, h), (x+16, y+16, h+16)),
             ((-x-16, -y-16, 0), (-x, y+16, h)), ((x, -y-16, 0), (x+16, y+16, h)),
             ((-x, -y-16, 0), (x, -y, h)), ((-x, y, 0), (x, y+16, h))]
    text = ['{', '"classname" "worldspawn"', '"wad" "lightcorridor.wad"', '"message" "Light test corridor"',
            '"_aw_sky_mode" "interior"', '"_minlight" "16"']
    text += [box(lo, hi, 'lightwall') for lo, hi in walls]
    text += ['}', '{', '"classname" "info_player_start"', '"origin" "%d %d %d"' % START, '"angle" "0"', '}']
    map_path = work/'lighttest.map'
    map_path.write_text('\n'.join(text)+'\n', encoding='ascii', newline='\n')
    # as the torch room: compiled at minlight 16 only so every face gets its sample range, then every byte zeroed
    commands = [[str(Path(qbsp).resolve()), '-nopercent', map_path.name],
                [str(Path(vis).resolve()), '-threads', '1', 'lighttest.bsp'],
                [str(Path(light).resolve()), *light_args('-minlight', '16', 'lighttest.bsp')]]
    with (work/'compile.log').open('w', encoding='utf-8', newline='\n') as log:
        for command in commands:
            subprocess.run(command, cwd=work, stdout=log, stderr=subprocess.STDOUT, check=True)
    bsp = work/'lighttest.bsp'
    rebuild_world_hull(bsp, map_path, qbsp)
    data = lumps(bsp.read_bytes())
    if not data[8]:
        raise ValueError('Light compiler produced no samples; refuse a fullbright corridor')
    data[0] = data[0].replace(b'"_minlight" "16"', b'"_minlight" "0"')
    data[8] = bytearray(len(data[8]))
    raw = pack_lumps(data)
    report = validate(raw)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(raw)
    if output.read_bytes() != raw:
        raise ValueError('Light test corridor readback differs')
    report.update(format='AmiWind procedural light test corridor 1', commands=commands,
                  room_bounds=[[-x, -y, 0], [x, y, h]], start=list(START),
                  palette_sha256=hashlib.sha256(palette).hexdigest(),
                  source='Procedural six-brush corridor and grid artwork; no source-game textures')
    (work/'receipt.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8', newline='\n')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('palette', 'output', 'work', 'qbsp', 'vis', 'light'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.palette, args.output, args.work, args.qbsp, args.vis, args.light), indent=2))


if __name__ == '__main__':
    main()
