#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Classic Workbench icons (.info files) from indexed PNG pictures.

A classic icon is an AmigaOS "DiskObject" (icon.library, Workbench 1.x-3.1): a
fixed 78-byte header (magic 0xE310, version 1, an Intuition Gadget whose size is
the picture's, the icon type, pointers that only say "present" when non-zero,
the position and the stack size), an optional DrawerData (disk and drawer
icons: the window the icon opens), one or two Image structures with their bit
planes (normal, and the picture shown while the icon is selected), then the
default tool and the tool types as length-prefixed strings. Everything is
big-endian. The icon holds palette INDICES only: the colours are those of the
Workbench screen (a stock Workbench 3.1 has 4: grey, black, white, blue).

The writer is deterministic: the same pictures and fields give the same bytes.
The reader parses a file field by field and refuses anything it does not know
(trailing bytes, unknown magic, truncated parts); the tests use it on the
writer's output.

Usage:
  amiga_icon.py write --png P [--selected-png P2] --type tool|project|disk|drawer
                      [--default-tool T] [--tool-type K=V ...] [--stack N] --out FILE.info
  amiga_icon.py dump FILE.info
  amiga_icon.py to-png FILE.info --out P [--selected-out P2]
"""
import argparse
import json
import struct
import sys
from pathlib import Path

MAGIC = 0xE310
VERSION = 1
TYPES = {'disk': 1, 'drawer': 2, 'tool': 3, 'project': 4, 'garbage': 5}
TYPE_NAMES = {v: k for k, v in TYPES.items()}
NO_ICON_POSITION = 0x80000000
# Gadget flags: GFLG_GADGIMAGE (the render is an Image) and GFLG_GADGHIMAGE (the select render is a second Image);
# without a second Image the selected icon is drawn complemented (GFLG_GADGHCOMP = 0).
GADGIMAGE = 0x0004
GADGHIMAGE = 0x0002
ACTIVATION = 0x0003      # GACT_RELVERIFY | GACT_IMMEDIATE, as Workbench writes them
BOOLGADGET = 0x0001
REVISION = 1             # gadget UserData: 1 = a Workbench 2.x+ icon (DrawerData2 follows for disk/drawer icons)
PRESENT = 1              # a "pointer" field only says whether its part follows
HEADER = struct.Struct('>HH IhhhhHHH IIIiIHI BB IIiiIIi')     # 78 bytes
IMAGE = struct.Struct('>hhhhhIBBI')                          # 20 bytes
NEWWINDOW = struct.Struct('>hhhhBBIIIIIIIhhHHH')             # 48 bytes
DRAWER2 = struct.Struct('>IH')                               # 6 bytes
# Stock Workbench 3.1 colours 0-3 (what the pictures are drawn for; the screen decides the real colours).
WB31_PALETTE = ((0xAA, 0xAA, 0xAA), (0x00, 0x00, 0x00), (0xFF, 0xFF, 0xFF), (0x66, 0x88, 0xBB))
assert HEADER.size == 78 and IMAGE.size == 20 and NEWWINDOW.size == 48


def row_bytes(width):
    return ((width + 15) // 16) * 2


def to_planes(pixels, width, height, depth):
    """Pixel indices (row-major list) -> bit planes: plane 0 first, each row padded to 16 bits."""
    if len(pixels) != width * height:
        raise ValueError('picture has %d pixels, not %d x %d' % (len(pixels), width, height))
    limit = 1 << depth
    bad = [p for p in pixels if not 0 <= p < limit]
    if bad:
        raise ValueError('pixel index %d does not fit %d bit planes (%d colours)' % (bad[0], depth, limit))
    stride = row_bytes(width)
    out = bytearray(depth * height * stride)
    for plane in range(depth):
        base = plane * height * stride
        for y in range(height):
            row = pixels[y * width:(y + 1) * width]
            for x, value in enumerate(row):
                if value >> plane & 1:
                    out[base + y * stride + (x >> 3)] |= 0x80 >> (x & 7)
    return bytes(out)


def from_planes(data, width, height, depth):
    stride = row_bytes(width)
    if len(data) != depth * height * stride:
        raise ValueError('plane data is %d bytes, not %d' % (len(data), depth * height * stride))
    pixels = [0] * (width * height)
    for plane in range(depth):
        base = plane * height * stride
        for y in range(height):
            for x in range(width):
                if data[base + y * stride + (x >> 3)] & (0x80 >> (x & 7)):
                    pixels[y * width + x] |= 1 << plane
    return pixels


def _string(text):
    raw = text.encode('latin-1') + b'\0'
    return struct.pack('>I', len(raw)) + raw


def _picture(picture, depth):
    width, height, pixels = picture
    if not (0 < width <= 1024 and 0 < height <= 1024):
        raise ValueError('picture size %dx%d is out of range' % (width, height))
    planes = to_planes(list(pixels), width, height, depth)
    return IMAGE.pack(0, 0, width, height, depth, PRESENT, (1 << depth) - 1, 0, 0) + planes


def disk_object(kind, normal, selected=None, default_tool=None, tool_types=(), stack=4096, depth=2,
                window=(50, 50, 400, 100)):
    """The .info bytes. normal/selected = (width, height, pixel indices); kind = a TYPES name."""
    if kind not in TYPES:
        raise ValueError('unknown icon type %r (one of %s)' % (kind, ', '.join(TYPES)))
    if not 1 <= depth <= 8:
        raise ValueError('depth must be 1-8')
    if not 0 <= stack <= 0x7FFFFFFF:
        raise ValueError('stack %d is out of range' % stack)
    width, height = normal[0], normal[1]
    if selected is not None and (selected[0], selected[1]) != (width, height):
        raise ValueError('the selected picture must be the size of the normal one')
    for text in ([default_tool] if default_tool else []) + list(tool_types):
        if '\0' in text or '\n' in text:
            raise ValueError('icon strings cannot hold NUL or line breaks: %r' % text)
        text.encode('latin-1')
    drawer = TYPES[kind] in (TYPES['disk'], TYPES['drawer'])
    flags = GADGIMAGE | (GADGHIMAGE if selected is not None else 0)
    out = bytearray(HEADER.pack(
        MAGIC, VERSION,
        0, 0, 0, width, height, flags, ACTIVATION, BOOLGADGET,
        PRESENT, PRESENT if selected is not None else 0, 0, 0, 0, 0, REVISION,
        TYPES[kind], 0,
        PRESENT if default_tool else 0, PRESENT if tool_types else 0,
        -0x80000000, -0x80000000,                     # NO_ICON_POSITION: Workbench places it
        PRESENT if drawer else 0, 0, stack))
    if drawer:
        left, top, w, h = window
        out += NEWWINDOW.pack(left, top, w, h, 255, 255, 0, 0, 0, 0, 0, 0, 0, 90, 40, 0xFFFF, 0xFFFF, 1)
        out += struct.pack('>ii', 0, 0)
    out += _picture(normal, depth)
    if selected is not None:
        out += _picture(selected, depth)
    if default_tool:
        out += _string(default_tool)
    if tool_types:
        out += struct.pack('>I', (len(tool_types) + 1) * 4)
        for text in tool_types:
            out += _string(text)
    if drawer:
        out += DRAWER2.pack(0, 0)                     # show icons, view by default
    return bytes(out)


class _Reader:
    def __init__(self, data):
        self.data, self.pos = data, 0

    def take(self, n, what):
        if self.pos + n > len(self.data):
            raise ValueError('icon is truncated in %s (needs %d bytes at offset %d, file has %d)'
                             % (what, n, self.pos, len(self.data)))
        chunk = self.data[self.pos:self.pos + n]
        self.pos += n
        return chunk

    def string(self, what):
        (length,) = struct.unpack('>I', self.take(4, what))
        raw = self.take(length, what)
        if not length or raw[-1:] != b'\0':
            raise ValueError('%s is not NUL-terminated' % what)
        return raw[:-1].decode('latin-1')

    def image(self, what):
        left, top, width, height, depth, data_ptr, pick, onoff, nxt = IMAGE.unpack(self.take(IMAGE.size, what))
        planes = bin(pick).count('1')
        stride = row_bytes(width)
        raw = self.take(planes * height * stride, what + ' planes')
        return dict(left=left, top=top, width=width, height=height, depth=depth, plane_pick=pick,
                    plane_on_off=onoff, pixels=from_planes(raw, width, height, planes))


def parse(data):
    """Field-by-field reading of a classic DiskObject; refuses unknown magic, truncation and trailing bytes."""
    r = _Reader(bytes(data))
    f = HEADER.unpack(r.take(HEADER.size, 'header'))
    (magic, version, next_gadget, left, top, width, height, flags, activation, gtype, render, select, text,
     mutex, special, gid, userdata, kind, pad, tool_ptr, types_ptr, cur_x, cur_y, drawer_ptr, toolwin_ptr,
     stack) = f
    if magic != MAGIC:
        raise ValueError('not an icon: magic 0x%04X' % magic)
    if version != VERSION:
        raise ValueError('unknown icon version %d' % version)
    if kind not in TYPE_NAMES:
        raise ValueError('unknown icon type %d' % kind)
    out = dict(magic=magic, version=version, type=TYPE_NAMES[kind], gadget=dict(
        left=left, top=top, width=width, height=height, flags=flags, activation=activation, type=gtype,
        render=render, select=select, text=text, user_data=userdata), stack=stack,
        current_x=cur_x & 0xFFFFFFFF, current_y=cur_y & 0xFFFFFFFF, default_tool=None, tool_types=[],
        drawer=None, selected=None)
    if drawer_ptr:
        nw = NEWWINDOW.unpack(r.take(NEWWINDOW.size, 'drawer window'))
        cx, cy = struct.unpack('>ii', r.take(8, 'drawer position'))
        out['drawer'] = dict(left=nw[0], top=nw[1], width=nw[2], height=nw[3], current_x=cx, current_y=cy)
    if not render:
        raise ValueError('icon has no picture')
    out['normal'] = r.image('normal picture')
    if select:
        if not flags & GADGHIMAGE:
            raise ValueError('a second picture without GFLG_GADGHIMAGE')
        out['selected'] = r.image('selected picture')
    if tool_ptr:
        out['default_tool'] = r.string('default tool')
    if types_ptr:
        (count,) = struct.unpack('>I', r.take(4, 'tool types'))
        if count < 4 or count % 4:
            raise ValueError('tool type count field %d is not (n+1)*4' % count)
        out['tool_types'] = [r.string('tool type %d' % i) for i in range(count // 4 - 1)]
    if toolwin_ptr:
        out['tool_window'] = r.string('tool window')
    if drawer_ptr and userdata == REVISION:
        flags2, modes = DRAWER2.unpack(r.take(DRAWER2.size, 'drawer data 2'))
        out['drawer'].update(flags=flags2, view_modes=modes)
    if r.pos != len(r.data):
        raise ValueError('%d trailing bytes after the icon' % (len(r.data) - r.pos))
    return out


def load_png(path, depth=2):
    """An indexed (palette) PNG -> (width, height, indices); every index must fit the icon's colours."""
    from PIL import Image
    with Image.open(path) as im:
        if im.mode != 'P':
            raise ValueError('%s must be an indexed (palette) PNG, not %s' % (path, im.mode))
        width, height = im.size
        pixels = list(im.getdata())
    top = max(pixels)
    if top >= 1 << depth:
        raise ValueError('%s uses colour index %d; a %d-plane icon has %d colours' % (path, top, depth, 1 << depth))
    return width, height, pixels


def save_png(path, picture, palette=WB31_PALETTE):
    from PIL import Image
    width, height, pixels = picture
    im = Image.new('P', (width, height))
    flat = [c for rgb in palette for c in rgb]
    im.putpalette(flat + [0] * (768 - len(flat)))
    im.putdata(list(pixels))
    im.save(path, optimize=False)


def write_icon(out, png, kind, selected_png=None, default_tool=None, tool_types=(), stack=4096, depth=2):
    data = disk_object(kind, load_png(png, depth), load_png(selected_png, depth) if selected_png else None,
                       default_tool=default_tool, tool_types=tool_types, stack=stack, depth=depth)
    parse(data)
    Path(out).write_bytes(data)
    return data


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    w = sub.add_parser('write')
    w.add_argument('--png', required=True, type=Path)
    w.add_argument('--selected-png', type=Path)
    w.add_argument('--type', required=True, choices=sorted(TYPES))
    w.add_argument('--default-tool')
    w.add_argument('--tool-type', action='append', default=[])
    w.add_argument('--stack', type=int, default=4096)
    w.add_argument('--out', required=True, type=Path)
    d = sub.add_parser('dump')
    d.add_argument('info', type=Path)
    p = sub.add_parser('to-png')
    p.add_argument('info', type=Path)
    p.add_argument('--out', required=True, type=Path)
    p.add_argument('--selected-out', type=Path)
    a = ap.parse_args(argv)
    if a.cmd == 'write':
        data = write_icon(a.out, a.png, a.type, a.selected_png, a.default_tool, a.tool_type, a.stack)
        print('Icon %s: %s, %d bytes' % (a.out, a.type, len(data)))
    elif a.cmd == 'dump':
        info = parse(a.info.read_bytes())
        for key in ('normal', 'selected'):
            if info.get(key):
                info[key] = {k: v for k, v in info[key].items() if k != 'pixels'}
        print(json.dumps(info, indent=2))
    else:
        info = parse(a.info.read_bytes())
        n = info['normal']
        save_png(a.out, (n['width'], n['height'], n['pixels']))
        if a.selected_out and info['selected']:
            s = info['selected']
            save_png(a.selected_out, (s['width'], s['height'], s['pixels']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
