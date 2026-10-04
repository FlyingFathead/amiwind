# SPDX-License-Identifier: GPL-3.0-only
"""Convert owned night textures to a private, bounded shared indexed atlas."""
from pathlib import Path
import hashlib
import io
import json
import os
import struct
from PIL import Image, ImageChops

PHASES = ('full', 'three_wan', 'half_wan', 'one_wan', 'new',
          'one_wax', 'half_wax', 'three_wax')
NIGHT_SIZE = 128
MOON_SIZE = 24
ART_BYTES = NIGHT_SIZE ** 2 + 2 * len(PHASES) * MOON_SIZE ** 2
STAR_MASK_BYTES = NIGHT_SIZE ** 2 // 8
PAYLOAD_BYTES = ART_BYTES + STAR_MASK_BYTES
ATLAS_BYTES = 16 + PAYLOAD_BYTES
ASSET = 'gfx/aw_night_sky.lmp'
CONVERSION_REVISION = 'upper-diamond-original-alpha-v1'


def fnv1a(raw):
    value = 2166136261
    for byte in raw:
        value = ((value ^ byte) * 16777619) & 0xffffffff
    return value


def validate(raw, palette):
    if len(palette) != 768 or len(raw) not in (16 + ART_BYTES, ATLAS_BYTES):
        raise ValueError('Invalid night atlas or palette size')
    version = raw[:4]
    if (raw[4:8] != bytes((128, 128, 24, 8)) or version not in (b'AWN1', b'AWN2')
            or len(raw) != 16 + (ART_BYTES if version == b'AWN1' else PAYLOAD_BYTES)):
        raise ValueError('Invalid night atlas version/dimensions')
    if struct.unpack_from('<II', raw, 8) != (fnv1a(palette), fnv1a(raw[16:])):
        raise ValueError('Night atlas palette or payload checksum mismatch')
    return raw[16:]


def owned_images(data_files):
    """Resolve loose owned textures, then the owned BSA, case independently."""
    root = Path(data_files)
    entries = {p.name.casefold(): p for p in root.iterdir()}
    texture_dir = entries.get('textures')
    loose = {p.name.casefold(): p for p in texture_dir.iterdir() if p.is_file()} if texture_dir else {}
    archive = None
    result, receipts = {}, []
    names = ['tx_stars', 'tx_stars_nebula', 'tx_stars_nebula2', 'tx_stars_nebula3']
    names += ['tx_' + moon + '_' + phase for moon in ('masser', 'secunda') for phase in PHASES]
    for stem in names:
        raw = None
        name = None
        for suffix in ('.tga', '.dds'):
            path = loose.get(stem + suffix)
            if path:
                raw, name = path.read_bytes(), 'textures/' + path.name
                break
        if raw is None:
            from mwad.audit import BSA
            from npc_geometry import bsa_read
            if archive is None:
                path = entries.get('morrowind.bsa')
                if not path:
                    raise FileNotFoundError('Missing owned night texture: ' + stem)
                archive = BSA(path)
            for suffix in ('.dds', '.tga'):
                try:
                    name = 'textures/' + stem + suffix
                    raw = bsa_read(archive, name)
                    break
                except KeyError:
                    pass
        if raw is None:
            raise FileNotFoundError('Missing owned night texture: ' + stem)
        with Image.open(io.BytesIO(raw)) as opened:
            if 'A' not in opened.getbands():
                raise ValueError('Night texture requires explicit alpha: ' + name)
            result[stem] = opened.convert('RGBA')
        receipts.append({'name': name, 'sha256': hashlib.sha256(raw).hexdigest(),
                         'size': list(result[stem].size)})
    return result, receipts


def build_atlas(images, palette):
    if len(palette) != 768:
        raise ValueError('Expected indexed RGB palette')
    tones = [tuple(palette[i:i+3]) for i in range(0, 765, 3)]
    cache = {}
    def nearest(rgb):
        if rgb not in cache:
            cache[rgb] = min(range(255), key=lambda i: sum((tones[i][k]-rgb[k])**2 for k in range(3)))
        return cache[rgb]
    # Preserve original nebula alpha. Artificially lifting three overlaid
    # layers fills the dark gaps that should reveal the distant source stars.
    background = Image.new('RGBA', (128, 128), (9, 10, 16, 255))
    for index, stem in enumerate(('tx_stars_nebula', 'tx_stars_nebula2', 'tx_stars_nebula3')):
        layer = images[stem].resize((128, 128), Image.Resampling.LANCZOS)
        layer = ImageChops.offset(layer, index*43, index*29)
        background = Image.alpha_composite(background, layer)
    # Runtime L1 projection reads only the upper diamond. Rotate/compress the
    # entire source square into it, rather than discarding its outer half.
    # Inverse of sx=u+v-1, sy=v-u; invalid/below-horizon cells stay transparent.
    payload = bytearray([255]) * NIGHT_SIZE ** 2
    for y in range(128):
        for x in range(128):
            if abs(x-63)+abs(y-63) >= 63:
                continue
            dx, dy = (x-63)/63.0, (63-y)/63.0
            u, v = (dx-dy+1)/2, (dx+dy+1)/2
            pixel = background.getpixel((min(127, int(u*128)), min(127, int(v*128))))
            if max(pixel[:3]) > 16:
                payload[y*128+x] = nearest(tuple(pixel[:3]))
    star_mask = bytearray(STAR_MASK_BYTES)
    stars = images['tx_stars'].convert('RGBA')
    brightest = {}
    for y in range(stars.height):
        for x in range(stars.width):
            pixel = stars.getpixel((x, y))
            rgb = tuple(c*pixel[3]//255 for c in pixel[:3])
            if max(rgb) < 48:
                continue
            u, v = (x+.5)/stars.width, (y+.5)/stars.height
            ix, iy = round(63+63*(u+v-1)), round(63-63*(v-u))
            # Rounding an edge source texel can land on z=0. Keep it in the
            # nearest valid cell, so source-square corners are not discarded.
            while abs(ix-63)+abs(iy-63) >= 63:
                if abs(ix-63) >= abs(iy-63):
                    ix += 1 if ix < 63 else -1
                else:
                    iy += 1 if iy < 63 else -1
            index = iy*128+ix
            if payload[index] != 255:
                continue  # stars are behind the original nebula's dark gaps
            if index not in brightest or max(rgb) > max(brightest[index]):
                brightest[index] = rgb
    for index, rgb in brightest.items():
        payload[index] = nearest(rgb)
        star_mask[index//8] |= 1 << (index & 7)
    for moon in ('masser', 'secunda'):
        for phase in PHASES:
            image = images['tx_' + moon + '_' + phase].resize((24, 24), Image.Resampling.LANCZOS)
            # Transparent index preserves both the disc edge and original phase.
            for r, g, b, a in image.getdata():
                payload.append(255 if a < 32 else nearest((r*a//255, g*a//255, b*a//255)))
    assert len(payload) == ART_BYTES
    payload.extend(star_mask)
    assert len(payload) == PAYLOAD_BYTES
    raw = b'AWN2' + bytes((128, 128, 24, 8)) + struct.pack('<II', fnv1a(palette), fnv1a(payload)) + payload
    validate(raw, palette)
    return bytes(raw)


def prepare_night_sky(id1, data_files, work_dir):
    """Prepare even when the independent cloud/palette marker already exists."""
    id1, work = Path(id1), Path(work_dir)
    target, marker = id1/ASSET, id1/'gfx/night-sky.json'
    palette = (id1/'gfx/palette.lmp').read_bytes()
    upgrade = False
    previous_version = None
    if marker.exists():
        report = json.loads(marker.read_text())
        raw = target.read_bytes()
        validate(raw, palette)
        if (report.get('sha256') != hashlib.sha256(raw).hexdigest()
                or report.get('palette_sha256') != hashlib.sha256(palette).hexdigest()
                or report.get('path') != ASSET or report.get('bytes') != len(raw)):
            raise ValueError('Stale night sky marker')
        if raw[:4] == b'AWN2' and report.get('conversion_revision') == CONVERSION_REVISION:
            return dict(report, status='verified_reuse')
        if not data_files:
            warning = 'Legacy night atlas projection retained; provide owned inputs to rebuild the full upper hemisphere with original alpha.'
            print('[warning] ' + warning, flush=True)
            return dict(report, status='legacy_fallback_warning', warning=warning, legacy_atlas=True, stale_conversion=True)
        upgrade = True
        previous_version = raw[:4].decode('ascii')
    if target.exists() and not upgrade:
        raise ValueError('Untracked night sky exists without its receipt')
    try:
        if not data_files:
            raise FileNotFoundError('No owned night textures supplied')
        images, inputs = owned_images(data_files)
    except (FileNotFoundError, KeyError, OSError, ValueError) as exc:
        report = {'status': 'fallback_warning', 'warning': str(exc), 'night_sky': False}
        print('[warning] Original night atlas unavailable: ' + str(exc), flush=True)
        return report
    raw = build_atlas(images, palette)
    report = {'status': 'prepared_owned_night', 'night_sky': True, 'path': ASSET,
              'bytes': len(raw), 'payload_bytes': PAYLOAD_BYTES, 'atlas_version': 2,
              'conversion_revision': CONVERSION_REVISION,
              'projection': 'full-source-square-to-upper-L1-diamond', 'nebula_alpha_multiplier': 1,
              'star_point_cells': sum(value.bit_count() for value in raw[16+ART_BYTES:]),
              'black_background_key_max_rgb': 16, 'star_points_behind_nebula': True,
              'sha256': hashlib.sha256(raw).hexdigest(), 'palette_sha256': hashlib.sha256(palette).hexdigest(),
              'sources': inputs, 'phases': list(PHASES), 'native_acceptance': False,
              'scope': 'Original bitmap shapes in a reduced shared atlas; approximate dome/orbits, not original sky mesh/weather parity.'}
    if upgrade:
        report['upgraded_legacy_atlas'] = True
        report['upgraded_from_atlas_version'] = previous_version
    work.mkdir(parents=True, exist_ok=True)
    receipt = work/'night-sky-preparation.json'
    if receipt.exists():
        raise ValueError('Existing night preparation receipt: use a fresh work directory')
    target.parent.mkdir(parents=True, exist_ok=True)
    if upgrade:
        backup = work/'before-legacy'
        backup.mkdir(exist_ok=False)
        (backup/'aw_night_sky.lmp').write_bytes(target.read_bytes())
        (backup/'night-sky.json').write_bytes(marker.read_bytes())
    staged_target = target.with_name(target.name+'.night-tmp') if upgrade else target
    with staged_target.open('xb') as stream:
        stream.write(raw)
    if upgrade:
        os.replace(staged_target, target)
    marker.write_text(json.dumps(report, indent=2)+'\n')
    receipt.write_text(json.dumps(report, indent=2)+'\n')
    return report
