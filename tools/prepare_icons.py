#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Icon and HUD-art import: one lookup table for the in-game UI pictures.

Every row maps a key to the original texture(s) the game data names and to one
converted picture:  key -> source path(s) -> picture SHA-256 -> picture file.

  item:<id>         an item record's ITEX (WEAP/ARMO/CLOT/...); an enchanted item
                    is composed over textures/menu_icon_magic.dds, as the
                    original item widget draws it
  skill:26          the hand-to-hand icon shown when unarmed
                    (icons/k/stealth_handtohand.dds)
  hud:box           the HUD weapon/magic box: black interior inside the thin
                    menu border (textures/menu_thin_border_*.dds)
  hud:bar           the frame of the small bar under a box (same thin border,
                    black client)
  hud:track:weapon  the bar fill: textures/menu_bar_gray.dds tinted with
  hud:track:magic   Morrowind.ini [FontColor] color_weapon_fill / color_magic_fill
  ui:head:block     the window title bar's head block (textures/menu_head_block_*.dds):
  ui:head:left      the tileable strip and its two edge columns
  ui:head:right
  mgef:<index>      a magic effect's ITEX (selected spell; none reachable yet:
                    the engine has no spell list)

Composition and proportions follow the original HUD as OpenMW 0.51 lays it out
(files/data/mygui/openmw_hud.layout WeapBox/SpellBox: a 36x36 box over a 36x6
bar beside three 65x12 stat bars; openmw_hud_box.skin.xml HUD_Box = BlackBG +
MW_Box; openmw_box.skin.xml MW_Box = 2-pixel menu_thin_border pieces;
openmw_hud_energybar.skin.xml MW_EnergyBar_Weapon/Magic: MW_Box around a black
client, a 2-pixel menu_bar_gray track; openmw_resources.xml
MW_ItemIconNoShadow: the 32x32 icon fills the box interior; itemwidget.cpp
ItemWidget::setItem: magic background only for enchanted items, its
44x44 texture corner drawn over the 42x42 widget at -5,-5). AmiWind's three
stat bars are 24 pixels tall where the original's are 42, so every HUD size is
scaled by 24/42: box 20x20 (1-pixel border, 18x18 icon), bar 20x4 (1-pixel
border, 18x2 track). Our own implementation; no OpenMW code is used.

  inv:<id>          an item's inventory cell, 16 x 16 (the original 42 x 42 cell with its
                    32 x 32 icon, scaled 16/42), on
  inv:<id>:equip    the magic backdrop when enchanted; :equip on menu_icon_equip.dds
                    (menu_icon_magic_equip.dds when enchanted), as the original item
                    widget's Equip state (UI-ICONS-INVENTORY-42)

Pictures are AWI1 (w, h, palette indices), quantised to the installed game
palette without dithering, each stored ONCE (by SHA-256) in one pack,
gfx/icons.awp: b'AWP1', u32 count, the pictures back to back (one file, not
thousands: classic FFS directories). The table is gfx/icons.awl: b'AWL2', u32
count, then count rows of 160 bytes, sorted by key (ASCII case-insensitive,
aw_icons.c binary-searches it):
  key[64]  source[56]  offset u32  size u32  sha256[32]
Only the referenced closure is converted: the HUD items the build stages
resources for, every catalogue item the player can own (inventory icons) and
the fixed UI keys; the item pictures are converted in a process pool. All
outputs are private game data (build output and pool only, never the
repository).
"""
import hashlib, io, struct
from pathlib import Path

ROW = 160
BOX = 20            # 36 * 24/42, rounded
BORDER = 1          # 2 * 24/42, rounded
ICON = BOX - 2 * BORDER          # 18: the 32x32 icon area inside the box
BAR_H = 4           # 6 * 24/42, rounded: 1-pixel border, 2-pixel track
TRACK_H = BAR_H - 2 * BORDER
HAND_TO_HAND = ('skill:26', 'icons/k/stealth_handtohand.dds')
MAGIC_BACKGROUND = 'textures/menu_icon_magic.dds'
THIN = 'textures/menu_thin_border_%s.dds'
BAR_TEXTURE = 'textures/menu_bar_gray.dds'
LIMIT = 32          # the engine's slot holds at most 32x32 pixels
STRIP = (320, 16)   # a wide UI strip slot: at most 320x16 pixels
# The window title bar (UI-WINDOW-TITLE-BAR-42): openmw_windows.skin.xml MW_Caption = a head block
# (HB_ALL: menu_head_block_middle tiled inside 2-pixel menu_head_block edges, 20 pixels tall) left
# and right of the title, the title on the window's black between them (WindowCaption::align: the
# text width + 24). AmiWind's title band is 12 pixels: everything scaled by 12/20.
HEAD = 'textures/menu_head_block_%s.dds'
HEAD_H = 12
HEAD_EDGE = 1       # 2 * 12/20, rounded


def key_bytes(key):
    raw = key.encode('cp1252').lower()   # ASCII-only lowering, as AW_InventoryCompare
    if len(raw) >= 64 or any(c < 32 for c in raw): raise ValueError('Invalid icon key ' + key)
    return raw


def rgba(raw):
    from PIL import Image
    return Image.open(io.BytesIO(raw)).convert('RGBA')


def premultiplied(image, size):
    """Box-filter an RGBA image to size in premultiplied alpha: (rgb*a, a) arrays."""
    import numpy as np
    from PIL import Image
    a = np.asarray(image.convert('RGBA'), dtype=np.float64) / 255.0
    rgb = a[..., :3] * a[..., 3:4]
    w, h = size
    out_rgb = np.stack([np.asarray(Image.fromarray(np.uint8(np.clip(rgb[..., c] * 255 + .5, 0, 255)), 'L')
                                   .resize((w, h), Image.Resampling.BOX), dtype=np.float64) / 255 for c in range(3)], -1)
    alpha = np.asarray(Image.fromarray(np.uint8(np.clip(a[..., 3] * 255 + .5, 0, 255)), 'L')
                       .resize((w, h), Image.Resampling.BOX), dtype=np.float64) / 255
    return out_rgb, alpha


def over(top, bottom):
    """Premultiplied 'over'."""
    trgb, ta = top; brgb, ba = bottom
    return trgb + brgb * (1 - ta[..., None]), ta + ba * (1 - ta)


def quantise(rgb, palette):
    import numpy as np
    colours = np.frombuffer(bytes(palette), dtype=np.uint8).reshape(256, 3).astype(np.float64)[:255]
    pixels = (np.clip(rgb, 0, 1) * 255.0).reshape(-1, 1, 3)
    return np.argmin(((pixels - colours[None]) ** 2).sum(2), axis=1).astype(np.uint8).tobytes()


def awi(rgb, palette, limit=(LIMIT, LIMIT)):
    h, w = rgb.shape[:2]
    if not (0 < w <= limit[0] and 0 < h <= limit[1]): raise ValueError('Picture too large for a UI slot')
    return b'AWI1' + struct.pack('<HH', w, h) + quantise(rgb, palette)


def icon_picture(icon, palette, background=None, size=None):
    """An item/skill icon over black or a backdrop (magic, equipped), size x size (default ICON)."""
    import numpy as np
    size = size or ICON
    layer = premultiplied(icon.resize((32, 32)) if icon.size != (32, 32) else icon, (size, size))
    base = (np.zeros((size, size, 3)), np.ones((size, size)))
    if background is not None: base = over(premultiplied(background, (size, size)), base)
    rgb, _ = over(layer, base)
    return awi(rgb, palette)


def cell_picture(icon, palette, background=None, cell=None):
    """An inventory cell as the original item widget draws it (openmw_resources.xml MW_ItemIcon:
    a 42 x 42 cell, the backdrop texture's 44 x 44 corner stretched over it, the 32 x 32 icon at
    5,5), scaled to cell x cell: the icon becomes 32*cell/42 pixels at 5*cell/42."""
    import numpy as np
    cell = cell or INV
    side = int(round(32 * cell / 42.0)); at = int(round(5 * cell / 42.0))
    base = (np.zeros((cell, cell, 3)), np.ones((cell, cell)))
    if background is not None: base = over(premultiplied(background, (cell, cell)), base)
    rgb, alpha = premultiplied(icon.resize((32, 32)) if icon.size != (32, 32) else icon, (side, side))
    layer = (np.zeros((cell, cell, 3)), np.zeros((cell, cell)))
    layer[0][at:at + side, at:at + side] = rgb; layer[1][at:at + side, at:at + side] = alpha
    out, _ = over(layer, base)
    return awi(out, palette)


def cell_background(raw):
    """The item widget's backdrop: the texture's 44 x 44 corner (scaled with the texture)."""
    from PIL import Image
    image = rgba(raw); scale = image.size[1] / 64.0
    return image.resize((44, 44), Image.Resampling.BOX, box=(0, 0, 44 * scale, 44 * scale))


def _convert(job):
    """Worker: (icon bytes, backdrop or None, palette, size, cell) -> AWI1 bytes (process pool)."""
    raw, background, palette, size, cell = job
    if cell: return cell_picture(rgba(raw), palette, background, size)
    return icon_picture(rgba(raw), palette, background, size)


INV = 16            # inventory icons: the 32x32 originals 2:1 (the inventory row's 16-pixel slot)
EQUIP_BACKGROUND = 'textures/menu_icon_equip.dds'
MAGIC_EQUIP_BACKGROUND = 'textures/menu_icon_magic_equip.dds'


def magic_background(raw):
    """The magic backdrop under a 32x32 icon: the item widget shows the texture's
    44x44 corner (scaled with the texture: height/64) on a 42x42 frame placed at
    -5,-5 of the icon area, so the icon area sees texture pixels 5*44/42 ..
    37*44/42."""
    from PIL import Image
    image = rgba(raw); scale = image.size[1] / 64.0
    lo, hi = 5 * 44 / 42 * scale, 37 * 44 / 42 * scale
    return image.resize((32, 32), Image.Resampling.BOX, box=(lo, lo, hi, hi))


def thin_frame(read, w, h):
    """BlackBG + MW_Box at w x h with a BORDER-pixel border made of the original
    thin border pieces (each 2 pixels thick, box-filtered to BORDER)."""
    import numpy as np
    from PIL import Image
    out = np.zeros((h, w, 3))
    def piece(name, size):
        return premultiplied(rgba(read(THIN % name)), size)[0]     # premultiplied = over black
    b = BORDER
    out[0:b, b:w - b] = piece('top', (w - 2 * b, b)); out[h - b:h, b:w - b] = piece('bottom', (w - 2 * b, b))
    out[b:h - b, 0:b] = piece('left', (b, h - 2 * b)); out[b:h - b, w - b:w] = piece('right', (b, h - 2 * b))
    out[0:b, 0:b] = piece('top_left_corner', (b, b)); out[0:b, w - b:w] = piece('top_right_corner', (b, b))
    out[h - b:h, 0:b] = piece('bottom_left_corner', (b, b)); out[h - b:h, w - b:w] = piece('bottom_right_corner', (b, b))
    return out


def head_pieces(read):
    """The title-bar head block at HEAD_H pixels: the tileable strip (top edge, tiled middle,
    bottom edge; the middle texture's own width scaled by the same factor) and the left and right
    edge columns (corner, side, corner)."""
    import numpy as np
    scale = HEAD_H / 20.0; e = HEAD_EDGE; mid_h = HEAD_H - 2 * e
    middle = rgba(read(HEAD % 'middle')); w = max(1, int(round(middle.size[0] * scale)))
    def piece(name, size):
        return premultiplied(rgba(read(HEAD % name)), size)[0]
    strip = np.zeros((HEAD_H, w, 3))
    strip[0:e] = piece('top', (w, e)); strip[e:HEAD_H - e] = premultiplied(middle, (w, mid_h))[0]
    strip[HEAD_H - e:] = piece('bottom', (w, e))
    left = np.zeros((HEAD_H, e, 3)); right = np.zeros((HEAD_H, e, 3))
    left[0:e] = piece('top_left_corner', (e, e)); left[e:HEAD_H - e] = piece('left', (e, mid_h))
    left[HEAD_H - e:] = piece('bottom_left_corner', (e, e))
    right[0:e] = piece('top_right_corner', (e, e)); right[e:HEAD_H - e] = piece('right', (e, mid_h))
    right[HEAD_H - e:] = piece('bottom_right_corner', (e, e))
    return strip, left, right


def track(read, colour):
    """MW_BarTrack_Weapon/Magic: menu_bar_gray tinted by the ini colour, (BOX-2) x TRACK_H."""
    import numpy as np
    rgb = premultiplied(rgba(read(BAR_TEXTURE)), (BOX - 2 * BORDER, TRACK_H))[0]
    return rgb * (np.array(colour, dtype=np.float64) / 255.0)


def read_icon_raw(assets, source):
    """The original icon's bytes (.dds first, then the record's own name)."""
    failures = []
    for candidate in (str(Path(source).with_suffix('.dds')), source):
        try:
            return candidate, assets.read(candidate)
        except (KeyError, OSError, ValueError) as error:
            failures.append(candidate + ': ' + str(error))
    raise ValueError('; '.join(failures))


def read_icon(assets, source):
    failures = []
    for candidate in (str(Path(source).with_suffix('.dds')), source):
        try:
            return candidate, rgba(assets.read(candidate))
        except (KeyError, OSError, ValueError) as error:
            failures.append(candidate + ': ' + str(error))
    raise ValueError('; '.join(failures))


def pack_table(rows, offsets):
    """AWL2: key[64] source[56] offset u32 size u32 sha256[32], sorted by key; offsets: digest -> (offset, size)
    in gfx/icons.awp (one file instead of thousands: the classic FFS directory rule)."""
    rows = sorted(rows, key=lambda r: key_bytes(r[0]))
    keys = [key_bytes(r[0]) for r in rows]
    if len(set(keys)) != len(keys): raise ValueError('Duplicate icon key')
    out = [b'AWL2', struct.pack('<I', len(rows))]
    for (key, source, digest), k in zip(rows, keys):
        src = source.replace('\\', '/').encode('cp1252')[:55]
        offset, size = offsets[digest]
        out += [k + b'\0' * (64 - len(k)), src + b'\0' * (56 - len(src)), struct.pack('<II', offset, size),
                bytes.fromhex(digest)]
    return b''.join(out)


def prepare(assets, id1, items, palette, colours, inventory=None, jobs=1):
    """items: {id: {'source_icon': ITEX, 'enchanted': bool}} - the HUD closure (item:<id>, 18 x 18).
    inventory: {id: {'source_icon', 'enchanted', 'equippable'}} - every item the player can own
    (inv:<id>, 16 x 16; inv:<id>:equip on the equipped backdrop for equippable items).
    colours: {'color_weapon_fill': [r,g,b], 'color_magic_fill': [r,g,b]}."""
    import time
    from concurrent.futures import ProcessPoolExecutor
    id1 = Path(id1); inventory = inventory or {}
    if len(palette) != 768: raise ValueError('Expected installed 256-colour game palette')
    report = {'rows': {}, 'held': {}, 'format': 'AWL2 160-byte rows into gfx/icons.awp (AWP1 of AWI1 pictures)',
              'sizes': {'box': BOX, 'border': BORDER, 'icon': ICON, 'inventory_icon': INV, 'bar_height': BAR_H,
                        'track_height': TRACK_H}}
    rows = []; pictures = {}; backdrops = {}

    def store(key, source, raw):
        digest = hashlib.sha256(raw).hexdigest()
        pictures.setdefault(digest, raw)
        rows.append((key, source, digest)); report['rows'][key] = {'source': source, 'sha256': digest}

    def attempt(key, make):
        try: make()
        except (ValueError, KeyError, OSError) as error: report['held'][key] = str(error)

    def backdrop(name, cell):
        key = (name, bool(cell))
        if key not in backdrops:
            raw = assets.read(name)
            backdrops[key] = cell_background(raw) if cell else magic_background(raw)
        return backdrops[key]

    attempt('hud:box', lambda: store('hud:box', THIN % '*', awi(thin_frame(assets.read, BOX, BOX), palette)))
    attempt('hud:bar', lambda: store('hud:bar', THIN % '*', awi(thin_frame(assets.read, BOX, BAR_H), palette)))
    for kind in ('weapon', 'magic'):
        name = 'color_%s_fill' % kind
        attempt('hud:track:' + kind, lambda kind=kind, name=name: store(
            'hud:track:' + kind, BAR_TEXTURE + ' * ' + name, awi(track(assets.read, colours[name]), palette)))

    def head():
        strip, left, right = head_pieces(assets.read)
        store('ui:head:block', HEAD % 'middle', awi(strip, palette, STRIP))
        store('ui:head:left', HEAD % 'left', awi(left, palette)); store('ui:head:right', HEAD % 'right', awi(right, palette))
    attempt('ui:head:block', head)

    def hand():
        source, image = read_icon(assets, HAND_TO_HAND[1]); store(HAND_TO_HAND[0], source, icon_picture(image, palette))
    attempt(HAND_TO_HAND[0], hand)

    # Item icons: read the originals here (one archive reader), convert in a process pool.
    jobs_list = []
    def queue(key, source_icon, background_name, size, cell=False):
        try:
            source, image = read_icon_raw(assets, 'icons/' + source_icon.replace('\\', '/'))
            background = backdrop(background_name, cell) if background_name else None
            jobs_list.append((key, source, (image, background, bytes(palette), size, cell)))
        except (ValueError, KeyError, OSError) as error:
            report['held'][key] = str(error)
    for identifier, item in sorted(items.items()):
        if item.get('source_icon'):
            queue('item:' + identifier, item['source_icon'], MAGIC_BACKGROUND if item.get('enchanted') else None, ICON)
    for identifier, item in sorted(inventory.items()):
        if not item.get('source_icon'): continue
        queue('inv:' + identifier, item['source_icon'], MAGIC_BACKGROUND if item.get('enchanted') else None, INV, True)
        if item.get('equippable'):
            queue('inv:' + identifier + ':equip', item['source_icon'],
                  MAGIC_EQUIP_BACKGROUND if item.get('enchanted') else EQUIP_BACKGROUND, INV, True)
    workers = max(1, min(int(jobs or 1), len(jobs_list) // 64 + 1))
    start = time.time()
    print('Icon import: %d item pictures on %d workers (asked %s)' % (len(jobs_list), workers, jobs), flush=True)
    if workers > 1:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            results = list(pool.map(_convert, [j[2] for j in jobs_list], chunksize=32))
    else:
        results = [_convert(j[2]) for j in jobs_list]
    for (key, source, _), raw in zip(jobs_list, results): store(key, source, raw)

    pack = [b'AWP1', struct.pack('<I', len(pictures))]; offsets = {}; at = 8
    for digest in sorted(pictures):
        raw = pictures[digest]; offsets[digest] = (at, len(raw)); pack.append(raw); at += len(raw)
    pack = b''.join(pack); table = pack_table(rows, offsets)
    (id1 / 'gfx').mkdir(parents=True, exist_ok=True)
    (id1 / 'gfx/icons.awp').write_bytes(pack); (id1 / 'gfx/icons.awl').write_bytes(table)
    report['table_sha256'] = hashlib.sha256(table).hexdigest(); report['pack_sha256'] = hashlib.sha256(pack).hexdigest()
    report['stored_pictures'] = len(pictures); report['table_rows'] = len(rows)
    report['picture_bytes'] = sum(len(v) for v in pictures.values()); report['pack_bytes'] = len(pack)
    report['table_bytes'] = len(table)
    print('Icon table: %d rows, %d pictures (%d bytes in the pack), %d held; took %.1f s, %d workers' % (
          len(rows), len(pictures), len(pack), len(report['held']), time.time() - start, workers), flush=True)
    return report


def ini_colours(data_files):
    """Morrowind.ini [FontColor] color_weapon_fill / color_magic_fill (the HUD bar fills)."""
    colours = {'color_weapon_fill': None, 'color_magic_fill': None}; notes = []; ini = None
    for parent in (Path(data_files), Path(data_files).parent):
        for p in parent.iterdir() if parent.is_dir() else ():
            if p.name.casefold() == 'morrowind.ini': ini = p
        if ini: break
    if ini:
        section = ''
        for line in ini.read_bytes().decode('cp1252', 'replace').splitlines():
            line = line.strip()
            if line.startswith('['): section = line.casefold(); continue
            if section == '[fontcolor]' and '=' in line:
                name, value = line.split('=', 1); name = name.strip().casefold()
                if name in colours:
                    try: parts = [int(v) for v in value.split(',')]
                    except ValueError: continue
                    if len(parts) == 3 and all(0 <= v <= 255 for v in parts): colours[name] = parts
    for name in colours:
        if colours[name] is None:
            # The value Morrowind.ini ships with (OpenMW files/openmw.cfg carries the same fallback).
            colours[name] = [200, 60, 30]; notes.append(name + ' not in Morrowind.ini; shipped value 200,60,30')
    return colours, {'ini': ini.name if ini else None, 'notes': notes}


def hud_settings(settings):
    """gfx/hud-settings.txt: the enchantment recharge rate (GMST fMagicItemRechargePerSecond;
    OpenMW mwmechanics/recharge.cpp rechargeItem) and the hand-to-hand name (GMST sSkillHandtohand:
    the inventory window's title when unarmed, OpenMW mwgui/hud.cpp unsetSelectedWeapon)."""
    rate = settings.get('fmagicitemrechargepersecond')
    if rate is None or not (0 <= rate <= 1000): raise ValueError('Missing GMST fMagicItemRechargePerSecond')
    text = 'fMagicItemRechargePerSecond %.6g\n' % rate; info = {'recharge_per_second': rate}
    name = settings.get('sskillhandtohand')
    if isinstance(name, str) and name and len(name) < 64 and all(32 <= ord(c) < 127 for c in name):
        text += 'sSkillHandtohand %s\n' % name; info['hand_to_hand'] = name
    return text, info
