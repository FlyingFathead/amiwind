#!/usr/bin/env python3
"""Convert the project wordmark and readable native-pixel startup typography."""
from pathlib import Path
import struct
from PIL import Image, ImageEnhance, ImageDraw, ImageFont
from prepare_video import HEADER, WIDTH, HEIGHT, FPS, RATE, validate


def text_width(font, text):
    return sum(font[8 + c * 8 + 6] for c in text.encode('cp1252'))


def draw_font(image, font, text, x, y, rgb=(223, 199, 144)):
    """Use the same privately converted AWF1 pixels as the native UI."""
    for c in text.encode('cp1252'):
        off, w, h, left, top, advance, _ = struct.unpack_from('<HBBbbBB', font, 8 + c * 8)
        for yy in range(h):
            for xx in range(w):
                k = yy * w + xx
                shade = (font[2056 + off + k // 4] >> (6 - 2 * (k % 4))) & 3
                px, py = x + left + xx, y + top + yy
                if shade and 0 <= px < image.width and 0 <= py < image.height:
                    image.putpixel((px, py), tuple(v * shade // 3 for v in rgb))
        x += advance


def load_font(path):
    font = Path(path).read_bytes()
    if len(font) < 2056 or font[:4] != b'AWF1' or font[4] not in (12, 14, 16):
        raise ValueError('Expected an owned converted AWF1 font')
    if len(font) != 2056 + struct.unpack_from('<H', font, 6)[0]:
        raise ValueError('Truncated AWF1 font')
    for c in range(256):
        off, w, h, left, top, advance, unused = struct.unpack_from('<HBBbbBB', font, 8 + c * 8)
        if w > 32 or h > 32 or advance > 32 or unused or 2056 + off + (w * h + 3) // 4 > len(font):
            raise ValueError('Invalid AWF1 glyph')
    return font


def draw_text_card(image, text, font_path):
    """Private, supplied movie text replaces unreadable burned-in title cards."""
    font = load_font(font_path)
    lines = []
    for paragraph in text.split('\n'):
        line = ''
        for word in paragraph.split():
            trial = (line + ' ' + word).strip()
            if text_width(font, trial) > 288 and line:
                lines.append(line); line = word
            else:
                line = trial
        lines.append(line)
    height = len(lines) * font[5]
    if height > 176 or any(text_width(font, line) > 288 for line in lines):
        raise ValueError('Title card exceeds native screen; split its text')
    # An opaque card avoids doubled text while the original audio continues.
    result = Image.new('RGB', image.size, (0, 0, 0))
    for i, line in enumerate(lines):
        draw_font(result, font, line, (320 - text_width(font, line)) // 2,
                  (200 - height) // 2 + i * font[5])
    return result


def wordmark(source, size):
    image = Image.open(source).convert('RGBA')
    bounds = image.getchannel('A').getbbox()
    if not bounds:
        raise ValueError('Empty project logo')
    image = image.crop(bounds)
    image.thumbnail(size, Image.Resampling.LANCZOS)
    return image


def prepare_menu_logo(source, palette_path, target):
    image = wordmark(source, (200, 40))
    full = Image.new('RGBA', (200, 40), (0, 0, 0, 255))
    full.alpha_composite(image, ((200 - image.width) // 2, (40 - image.height) // 2))
    palette = Path(palette_path).read_bytes()
    if len(palette) != 768:
        raise ValueError('Expected a 256-colour game palette')
    pal = Image.new('P', (1, 1)); pal.putpalette(palette)
    result = full.convert('RGB').quantize(palette=pal, dither=Image.Dither.NONE)
    Path(target).write_bytes(b'AWI1' + struct.pack('<HH', 200, 40) + result.tobytes())


def prepare_logo(source, target, font_path=None):
    target = Path(target)
    image = wordmark(source, (304, 80))
    full = Image.new('RGBA', (WIDTH, HEIGHT), (0, 0, 0, 255))
    full.alpha_composite(image, ((WIDTH-image.width)//2, 53 + (80-image.height)//2))
    full = full.convert('RGB')
    lines = ['A Commodore Amiga', 'demake of Morrowind']
    if font_path and Path(font_path).is_file():
        font = load_font(font_path)
        for i, line in enumerate(lines):
            draw_font(full, font, line, (WIDTH-text_width(font, line))//2, 141+i*font[5])
    else:
        draw = ImageDraw.Draw(full)
        for i, line in enumerate(lines):
            draw.text((WIDTH//2, 141+i*14), line, anchor='mt', fill=(223,199,144), font=ImageFont.load_default())
    gains = [i/10 for i in range(11)] + [1]*14 + [i/5 for i in range(4, -1, -1)] + [0]
    frames = [ImageEnhance.Brightness(full).enhance(gain) for gain in gains]
    contact = Image.new('RGB', (WIDTH, HEIGHT*len(frames)))
    for i, frame in enumerate(frames): contact.paste(frame, (0, HEIGHT*i))
    palette = contact.quantize(colors=256)
    samples = (len(frames)*RATE+FPS-1)//FPS
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('xb') as stream:
        stream.write(HEADER.pack(b'AWV1', WIDTH, HEIGHT, FPS, RATE, len(frames), samples))
        stream.write(bytes(palette.getpalette()).ljust(768, b'\0')[:768])
        for frame in frames:
            stream.write(frame.quantize(palette=palette, dither=Image.Dither.NONE).tobytes())
        stream.write(bytes(samples))
    return validate(target)
