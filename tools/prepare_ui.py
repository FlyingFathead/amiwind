#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Bake an owned Morrowind bitmap font and draw host-side UI studies.

No game artwork is embedded in this script. The FNT layout/metric meanings were
checked against OpenMW's fontloader; this is an independent Python converter.
"""
import argparse
import hashlib
import json
import math
import struct
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rounded(n):
    return math.floor(n + 0.5)


class OriginalFont:
    def __init__(self, path):
        raw = path.read_bytes()
        if len(raw) != 296 + 256 * 56:
            raise ValueError('Unexpected FNT length')
        self.height, one, another = struct.unpack_from('<fII', raw)
        if (one, another) != (1, 1) or not 0 < self.height <= 128:
            raise ValueError('Invalid FNT header')
        name = raw[12:296].split(b'\0', 1)[0].decode('ascii')
        if Path(name).name != name:
            raise ValueError('Atlas name must be a basename')
        self.texture_path = next(p for p in path.parent.iterdir()
                                 if p.name.lower() == (name + '.tex').lower())
        tex = self.texture_path.read_bytes()
        w, h = struct.unpack_from('<II', tex)
        if not 0 < w <= 4096 or not 0 < h <= 4096 or len(tex) != 8 + w*h*4:
            raise ValueError('Invalid TEX dimensions or payload')
        self.atlas = Image.frombytes('RGBA', (w, h), tex[8:])
        self.glyphs = []
        for c in range(256):
            f = struct.unpack_from('<14f', raw, 296+c*56)
            if not all(math.isfinite(x) for x in f):
                raise ValueError('Non-finite glyph data')
            x, y, right, bottom = f[1]*w, f[2]*h, f[3]*w, f[6]*h
            box = tuple(rounded(v) for v in (x, y, right, bottom))
            if not (0 <= box[0] <= box[2] <= w and 0 <= box[1] <= box[3] <= h):
                raise ValueError('Glyph outside texture')
            width, height, left, extra, ascent = f[9:14]
            if width < 0 or height < 0:
                raise ValueError('Negative glyph dimensions')
            self.glyphs.append(dict(code=c, crop=box, width=width, height=height,
                                    advance=width+extra, left=left,
                                    top=self.height-ascent))

    def bake(self, size, levels=4, *, paper_ink="original"):
        if paper_ink not in ("original", "filled"):
            raise ValueError("Bitmap paper ink must be 'filled' or 'original'")
        scale = size/self.height
        baked = []
        for g in self.glyphs:
            width, height = rounded(g['width']*scale), rounded(g['height']*scale)
            mask = None
            if width and height:
                src = self.atlas.getchannel('A').crop(g['crop'])
                if not src.width or not src.height:
                    raise ValueError('Nonempty glyph has empty source crop')
                # Area resampling is done once on the host, never at runtime.
                src = src.resize((width, height), Image.Resampling.BOX)
                if paper_ink == "filled":
                    # Approved paper-only coverage correction, before quantization.
                    # No dilation, new pixels outside the glyph, or metric changes.
                    # Preserve the original transparent cutoff (43), while assigning
                    # medium/solid ink earlier. This matches the approved 2x preview.
                    src = src.point(lambda a: 0 if a < 43 else
                                    85 if a < 80 else 170 if a < 190 else 255)
                if levels == 2:
                    mask = src.point(lambda a: 255 if a >= 80 else 0)
                else:
                    mask = src.point(lambda a: rounded(a/255*(levels-1))*255//(levels-1))
            baked.append(dict(code=g['code'], width=width, height=height,
                              left=rounded(g['left']*scale), top=rounded(g['top']*scale),
                              advance=max(0, rounded(g['advance']*scale)), mask=mask))
        return baked



def pack_font(path, size, *, paper_ink="original"):
    glyphs = OriginalFont(path).bake(size, paper_ink=paper_ink)
    return pack_glyphs(glyphs, size)


def bake_family(item, sizes=(16, 14, 12)):
    """Prefer the loose TTF; fall back to Bethesda FNT+TEX as one family."""
    ttf_error = None
    if item["ttf_path"]:
        try:
            return ({size: pack_truetype(item["ttf_path"], size) for size in sizes},
                    "ttf", None)
        except (OSError, ValueError) as exc:
            ttf_error = str(exc)
    if item["bitmap_ready"]:
        return ({size: pack_font(item["bitmap_path"], size) for size in sizes},
                "bitmap-fallback" if item["ttf_path"] else "bitmap", ttf_error)
    if ttf_error:
        raise ValueError(f"{item['label']} TTF conversion failed and no bitmap fallback is available: {ttf_error}")
    raise ValueError(f"No usable source for {item['label']}")


def pack_truetype(path, size):
    """Rasterize a caller-supplied font to AWF1 on the host, never on Amiga."""
    if size not in (12, 14, 16):
        raise ValueError('Native font sizes are 12, 14 and 16')
    # Tiny hinted outlines can lose an entire hairline when reduced to the
    # native four ink levels (notably the top of Magic Cards o/s at 14px).
    # Sample the outline at 4x, then average coverage before quantization.
    # Keep native-size advances so existing menu wrapping does not change.
    oversample = 4
    encoding = 'unic'
    try:
        font = ImageFont.truetype(str(path), size, encoding=encoding, layout_engine=ImageFont.Layout.BASIC)
    except OSError:
        # Older Magic Cards TTFs expose a Windows symbol charmap. Selecting
        # FreeType's default map can silently rasterize .notdef for every letter.
        encoding = 'symb'
        font = ImageFont.truetype(str(path), size, encoding=encoding, layout_engine=ImageFont.Layout.BASIC)
    if len({bytes(font.getmask(c)) for c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'}) < 8:
        raise ValueError('Font charmap does not provide distinct Latin glyphs')
    outline = ImageFont.truetype(str(path), size*oversample, encoding=encoding,
                               layout_engine=ImageFont.Layout.BASIC)
    glyphs = []
    for code in range(256):
        char = bytes([code]).decode('cp1252', errors='replace')
        if code < 32 or code == 127 or char == '\ufffd':
            char = ' '
        left, top, right, bottom = outline.getbbox(char)
        left, top = math.floor(left/oversample), math.floor(top/oversample)
        right, bottom = math.ceil(right/oversample), math.ceil(bottom/oversample)
        width, height = right-left, bottom-top
        mask = Image.new('L', (max(1,width*oversample),max(1,height*oversample)))
        ImageDraw.Draw(mask).text((-left*oversample,-top*oversample),char,font=outline,fill=255)
        mask = mask.resize((max(1,width),max(1,height)), Image.Resampling.BOX)
        mask = mask.point(lambda a: rounded(a/85)*85)
        glyphs.append(dict(code=code,width=width,height=height,left=left,top=top,
                           advance=rounded(font.getlength(char)),mask=mask if width and height else None))
    return pack_glyphs(glyphs, size)


def pack_glyphs(glyphs, size):
    metrics = bytearray(); pixels = bytearray()
    for g in glyphs:
        offset = len(pixels)
        values = list(g['mask'].getdata()) if g['mask'] is not None else []
        for start in range(0, len(values), 4):
            byte = 0
            for i, value in enumerate(values[start:start+4]):
                byte |= (value // 85) << (6 - i*2)
            pixels.append(byte)
        if g['width'] > 32 or g['height'] > 32 or not 0 <= g['advance'] <= 32:
            raise ValueError('Glyph exceeds native limits')
        metrics.extend(struct.pack('<HBBbbBB', offset, g['width'], g['height'],
                                   g['left'], g['top'], g['advance'], 0))
    if len(pixels) > 24000:
        raise ValueError('Font exceeds native payload budget')
    return struct.pack('<4sBBH', b'AWF1', size, size+2, len(pixels)) + metrics + pixels


def background_packet(background,palette,protected):
    """Give artwork the free palette entries without changing UI/text colors."""
    free=[i for i in range(256) if i not in protected]
    if len(free)<16:raise ValueError('Insufficient background palette budget')
    colors=background.quantize(colors=len(free),dither=Image.Dither.NONE).getpalette()
    result=bytearray(palette)
    for n,i in enumerate(free):result[i*3:i*3+3]=bytes(colors[n*3:n*3+3])
    pal=Image.new('P',(1,1));pal.putpalette(result)
    indexed=background.quantize(palette=pal,dither=Image.Dither.NONE)
    return b'AWB2'+struct.pack('<HH',320,200)+result+indexed.tobytes()


def convert(data, palette_path, out):
    import sys, io
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
    from mwad.paths import ensure_external, child_ci, resolve_data_files
    from mwad.audit import BSA
    from mwad import font_sources
    from npc_geometry import Assets
    data = resolve_data_files(data); out = ensure_external(Path(out), 'private UI assets')
    out.mkdir(parents=True, exist_ok=True)
    fonts = font_sources.discover(data)
    palette = Path(palette_path).read_bytes()
    if len(palette) != 768: raise ValueError('Expected 256 RGB palette')
    assets = Assets(data, BSA(child_ci(data, 'Morrowind.bsa')))
    atlas = Image.new('RGBA', (64,64), (0,0,0,255)); sources = {}
    specs = [('top_left_corner',(0,0),(4,4)), ('top',(4,0),(16,4)),
             ('top_right_corner',(20,0),(4,4)), ('left',(0,4),(4,16)),
             ('right',(20,4),(4,16)), ('bottom_left_corner',(0,20),(4,4)),
             ('bottom',(4,20),(16,4)), ('bottom_right_corner',(20,20),(4,4))]
    for name, pos, size in specs:
        path = 'textures/menu_thick_border_'+name+'.dds'; raw = assets.read(path)
        image = Image.open(io.BytesIO(raw)).convert('RGBA')
        # Keep decorative edge detail; tile a source section, never smear it.
        image = image.crop((0,0,*size))
        atlas.paste(image, pos, image); sources[path] = hashlib.sha256(raw).hexdigest()
    for i, color in enumerate(('red','blue','green')):
        path = 'textures/menu_bar_'+color+'.dds'; raw = assets.read(path)
        image = Image.open(io.BytesIO(raw)).convert('RGBA').resize((16,16),Image.Resampling.BOX)
        atlas.paste(image, (16*i,32), image); sources[path] = hashlib.sha256(raw).hexdigest()
    pal = Image.new('P',(1,1)); pal.putpalette(palette)
    indexed = atlas.convert('RGB').quantize(palette=pal,dither=Image.Dither.NONE)
    (out/'ui.awu').write_bytes(b'AWU1'+struct.pack('<HH',64,64)+indexed.tobytes())
    path='textures/menu_morrowind.dds';raw=assets.read(path)
    background=Image.open(io.BytesIO(raw)).convert('RGB').resize((320,200),Image.Resampling.BOX)
    # Front-end artwork has its own palette; preserve every UI atlas/text color.
    protected=set(indexed.tobytes())|{254,255}
    for rgb in ((0,0,0),(76,67,46),(151,131,87),(223,199,144),(115,108,89),
                (22,20,18),(210,184,121),(114,114,114),(62,53,36)):
        protected.add(min(range(256),key=lambda i:sum((palette[i*3+c]-rgb[c])**2 for c in range(3))))
    (out/'menu.awb').write_bytes(background_packet(background,palette,protected))
    sources[path]=hashlib.sha256(raw).hexdigest()
    splash=next((p for p in data.iterdir() if p.name.casefold()=='splash' and p.is_dir()),None)
    screens=sorted((p for p in splash.iterdir() if p.suffix.casefold() in ('.tga','.dds','.bmp','.png')),
                   key=lambda p:p.name.casefold()) if splash else []
    loading=[]
    if not screens:print('Warning: Splash images not found; loading screens will use the original menu artwork.')
    for i,p in enumerate(screens[:32]):
        art=Image.open(p).convert('RGB').resize((320,200),Image.Resampling.LANCZOS)
        name=f'loading{i:02d}.awb';(out/name).write_bytes(background_packet(art,palette,protected))
        loading.append({'source':p.name,'sha256':sha(p),'output':name})
    font_report = {}
    for key, item in fonts.items():
        if not font_sources.usable(item):
            if key == 'magic':
                raise ValueError('Magic Cards font is required for the AmiWind UI')
            print(f"Warning: {item['label']} font unavailable; no TTF or complete FNT+TEX pair was found.")
            continue
        payloads, mode, ttf_error = bake_family(item)
        if ttf_error:
            print(f"Warning: preferred {item['ttf']} could not be converted safely ({ttf_error}); "
                  f"using Bethesda bitmap fallback {item['bitmap']}.")
        for size, payload in payloads.items():
            (out/f"{item['output']}{size}.awf").write_bytes(payload)
        selected = item['ttf_path'] if mode == 'ttf' else item['bitmap_path']
        font_report[key] = {
            'label': item['label'], 'mode': mode, 'source': selected.name,
            'source_sha256': sha(selected),
            'atlas_sha256': sha(item['atlas_path']) if mode != 'ttf' and item['atlas_path'] else None,
            'ttf_error': ttf_error,
            'outputs': [f"{item['output']}{size}.awf" for size in (16,14,12)],
        }
    magic = font_report['magic']
    report = {'format':'AmiWind private UI conversion 2','font_sha256':magic['source_sha256'],
              'atlas_sha256':magic['atlas_sha256'],'palette_sha256':sha(Path(palette_path)),
              'font_families':font_report, 'sources':sources,
              'encoding':'CP1252 game strings; preferred TTF or Bethesda bitmap fallback per family',
              'variants':[16,14,12], 'coverage':'three ink shades and transparent; packed 2-bit',
              'loading_screens':loading}
    (out/'ui-conversion.json').write_text(json.dumps(report,indent=2)+'\n')
    return report

if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data-files',type=Path,required=True)
    p.add_argument('--palette',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args(); print(json.dumps(convert(a.data_files,a.palette,a.out),indent=2))
