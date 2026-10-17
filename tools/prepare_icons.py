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

Pictures are AWI1 (w, h, palette indices), quantised to the installed game
palette without dithering, written ONCE under gfx/icon/<sha16>.awi
(content-addressed: identical pictures share one file). The table is
gfx/icons.awl: b'AWL1', u32 count, then count rows of 160 bytes, sorted by key
(ASCII case-insensitive, aw_icons.c binary-searches it):
  key[64]  source[64]  sha256[32]
Only the referenced closure is converted: the items the build stages inventory
resources for (tools/prepare_inventory.py) plus the fixed HUD keys. All outputs
are private game data (build output and pool only, never the repository).
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


def awi(rgb, palette):
    h, w = rgb.shape[:2]
    if not (0 < w <= LIMIT and 0 < h <= LIMIT): raise ValueError('Picture too large for a UI slot')
    return b'AWI1' + struct.pack('<HH', w, h) + quantise(rgb, palette)


def icon_picture(icon, palette, background=None):
    """An item/skill icon over black (the box interior) or the magic backdrop, ICON x ICON."""
    import numpy as np
    layer = premultiplied(icon.resize((32, 32)) if icon.size != (32, 32) else icon, (ICON, ICON))
    base = (np.zeros((ICON, ICON, 3)), np.ones((ICON, ICON)))
    if background is not None: base = over(premultiplied(background, (ICON, ICON)), base)
    rgb, _ = over(layer, base)
    return awi(rgb, palette)


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


def track(read, colour):
    """MW_BarTrack_Weapon/Magic: menu_bar_gray tinted by the ini colour, (BOX-2) x TRACK_H."""
    import numpy as np
    rgb = premultiplied(rgba(read(BAR_TEXTURE)), (BOX - 2 * BORDER, TRACK_H))[0]
    return rgb * (np.array(colour, dtype=np.float64) / 255.0)


def read_icon(assets, source):
    failures = []
    for candidate in (str(Path(source).with_suffix('.dds')), source):
        try:
            return candidate, rgba(assets.read(candidate))
        except (KeyError, OSError, ValueError) as error:
            failures.append(candidate + ': ' + str(error))
    raise ValueError('; '.join(failures))


def pack_table(rows):
    rows = sorted(rows, key=lambda r: key_bytes(r[0]))
    keys = [key_bytes(r[0]) for r in rows]
    if len(set(keys)) != len(keys): raise ValueError('Duplicate icon key')
    out = [b'AWL1', struct.pack('<I', len(rows))]
    for (key, source, digest), k in zip(rows, keys):
        src = source.replace('\\', '/').encode('cp1252')[:63]
        out += [k + b'\0' * (64 - len(k)), src + b'\0' * (64 - len(src)), bytes.fromhex(digest)]
    return b''.join(out)


def picture_path(digest):
    return 'gfx/icon/' + digest[:16] + '.awi'


def prepare(assets, id1, items, palette, colours):
    """items: {id: {'source_icon': ITEX, 'enchanted': bool}} - the referenced closure.
    colours: {'color_weapon_fill': [r,g,b], 'color_magic_fill': [r,g,b]}."""
    id1 = Path(id1)
    if len(palette) != 768: raise ValueError('Expected installed 256-colour game palette')
    report = {'rows': {}, 'pictures': {}, 'held': {}, 'format': 'AWL1 160-byte rows, AWI1 pictures',
              'sizes': {'box': BOX, 'border': BORDER, 'icon': ICON, 'bar_height': BAR_H, 'track_height': TRACK_H}}
    rows = []; stored = {}; backdrop = []

    def store(key, source, raw):
        digest = hashlib.sha256(raw).hexdigest(); path = picture_path(digest)
        if digest not in stored:
            (id1 / path).parent.mkdir(parents=True, exist_ok=True)
            (id1 / path).write_bytes(raw); stored[digest] = path
            report['pictures'][path] = {'sha256': digest, 'bytes': len(raw)}
        rows.append((key, source, digest))
        report['rows'][key] = {'source': source, 'sha256': digest, 'picture': path}

    def attempt(key, make):
        try: make()
        except (ValueError, KeyError, OSError) as error: report['held'][key] = str(error)

    attempt('hud:box', lambda: store('hud:box', THIN % '*', awi(thin_frame(assets.read, BOX, BOX), palette)))
    attempt('hud:bar', lambda: store('hud:bar', THIN % '*', awi(thin_frame(assets.read, BOX, BAR_H), palette)))
    for kind in ('weapon', 'magic'):
        name = 'color_%s_fill' % kind
        attempt('hud:track:' + kind, lambda kind=kind, name=name: store(
            'hud:track:' + kind, BAR_TEXTURE + ' * ' + name, awi(track(assets.read, colours[name]), palette)))

    def hand():
        source, image = read_icon(assets, HAND_TO_HAND[1]); store(HAND_TO_HAND[0], source, icon_picture(image, palette))
    attempt(HAND_TO_HAND[0], hand)
    for identifier, item in sorted(items.items()):
        if not item.get('source_icon'): continue
        key = 'item:' + identifier
        def one(identifier=identifier, item=item, key=key):
            source, image = read_icon(assets, 'icons/' + item['source_icon'].replace('\\', '/'))
            background = None
            if item.get('enchanted'):
                if not backdrop: backdrop.append(magic_background(assets.read(MAGIC_BACKGROUND)))
                background = backdrop[0]
            store(key, source, icon_picture(image, palette, background))
        attempt(key, one)
    table = pack_table(rows)
    (id1 / 'gfx').mkdir(parents=True, exist_ok=True)
    (id1 / 'gfx/icons.awl').write_bytes(table)
    report['table_sha256'] = hashlib.sha256(table).hexdigest()
    report['stored_pictures'] = len(stored); report['table_rows'] = len(rows)
    report['picture_bytes'] = sum(v['bytes'] for v in report['pictures'].values())
    print('Icon table: %d rows, %d pictures (%d bytes), %d held' % (len(rows), len(stored),
          report['picture_bytes'], len(report['held'])), flush=True)
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
    OpenMW mwmechanics/recharge.cpp rechargeItem)."""
    rate = settings.get('fmagicitemrechargepersecond')
    if rate is None or not (0 <= rate <= 1000): raise ValueError('Missing GMST fMagicItemRechargePerSecond')
    return 'fMagicItemRechargePerSecond %.6g\n' % rate, {'recharge_per_second': rate}
