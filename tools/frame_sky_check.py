#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""The shared-sky check of the CHIM frame maps: every open-world frame map names the shared exterior sky in its
worldspawn, as open_world_worldspawn (tools/chim/frame_map.py) writes it: "_aw_sky_mode" "exterior" and
"_aw_sky_asset" "gfx/aw_shared_sky.lmp". Over a map without them the engine draws the interior black instead of the
sky (R_SetSkyBackground reads _aw_sky_mode). The image step's own check (tools/build_exclusions.py
check_always_included) only asks that the sky asset a map names exists, so a frame map that names none passed it.
New exterior frames (the expansions' cells, CHIM-SOL-FLORA-PATH-65) are where such a map would first appear.

- frame_maps_without_sky(maps_dir): the frame maps of a maps folder (tools/map_files.py frame_maps: by their
  worldspawn key "_chim_frame", whatever the extension) whose worldspawn lacks either key or names another value.
  It reads only each map's header and entity lump.
- frame_map_sky_after (phase after:image, tools/build_preflight.py EARLY_CHECKS): the image step's frame maps
  (RUN/image/boot/id1/maps), the moment the image step has passed, before the build is called passed and before any
  kit is made from it. The frame maps are made in the image step itself (chim.frame_map.build_regions), so no stage
  before it holds one.

A module of its own rather than a function in tools/chim/frame_map.py: that file counts whole in the key of a stage
that reaches its region pass cache (PassCache.open with its __file__; BUILD-KEY-KEYED-REACH-WHOLE-51), so a new
function there could re-key such a stage. The keys and values checked are read from open_world_worldspawn itself
(wanted_keys), so the check follows any change made there.

    python3 tools/frame_sky_check.py MAPS_DIR     (lists the frame maps without the shared sky; exit 1 if any)
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _path in (ROOT / 'tools', ROOT / 'src'):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

IMAGE_MAPS = Path('image', 'boot', 'id1', 'maps')   # the image step's own maps folder in a build run
SHOWN = 8


def wanted_keys():
    """{sky key: value} every open-world frame map carries: the shared-sky keys (tools/build_exclusions.py SKY_KEYS)
    as open_world_worldspawn gives them."""
    from build_exclusions import SKY_KEYS
    from chim.frame_map import open_world_worldspawn
    row = open_world_worldspawn({})
    return {key: row[key] for key in SKY_KEYS}


def frame_maps_without_sky(maps_dir, wanted=None):
    """[(map file name, [what is wrong])] of the CHIM frame maps in MAPS_DIR whose worldspawn lacks one of WANTED's
    keys (default wanted_keys()) or holds another value; [] when every frame map carries them. Maps that are not
    frame maps (no "_chim_frame": the legacy maps, the rooms) are not read past their header."""
    from map_files import frame_maps, head_bytes, worldspawn
    wanted = wanted_keys() if wanted is None else dict(wanted)
    out = []
    for path in frame_maps(maps_dir):
        keys = worldspawn(head_bytes(path))
        wrong = [('%s missing' % key) if key not in keys else ('%s is "%s", not "%s"' % (key, keys[key], value))
                 for key, value in wanted.items() if keys.get(key) != value]
        if wrong:
            out.append((path.name, wrong))
    return out


def problem_text(found, where):
    """The one problem line for FOUND (frame_maps_without_sky's list) in the maps folder WHERE."""
    shown = '; '.join('%s (%s)' % (name, ', '.join(wrong)) for name, wrong in found[:SHOWN])
    more = '; and %d more' % (len(found) - SHOWN) if len(found) > SHOWN else ''
    return ('%d CHIM frame map%s in %s do%s not name the shared exterior sky as open_world_worldspawn '
            '(tools/chim/frame_map.py) writes it, so the engine would draw the interior black over %s: %s%s'
            % (len(found), '' if len(found) == 1 else 's', where, 'es' if len(found) == 1 else '',
               'it' if len(found) == 1 else 'them', shown, more))


def frame_map_sky_after(context):
    """Phase after:image: the frame maps the image step has just written, in the run folder."""
    maps = Path(context.run) / IMAGE_MAPS
    if not maps.is_dir():
        context.log('  %s: no maps folder, no frame map to check' % IMAGE_MAPS.as_posix())
        return []
    found = frame_maps_without_sky(maps)
    if found:
        return [problem_text(found, IMAGE_MAPS.as_posix())]
    context.log('  every frame map in %s names the shared exterior sky' % IMAGE_MAPS.as_posix())
    return []


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print(__doc__.strip().splitlines()[-1].strip())
        return 2
    found = frame_maps_without_sky(argv[0])
    for name, wrong in found:
        print('%s: %s' % (name, ', '.join(wrong)))
    from map_files import frame_maps
    print('%d frame maps, %d without the shared sky' % (len(frame_maps(argv[0])), len(found)))
    return 1 if found else 0


if __name__ == '__main__':
    sys.exit(main())
