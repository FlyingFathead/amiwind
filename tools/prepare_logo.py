#!/usr/bin/env python3
"""Convert the project wordmark and readable native-pixel startup typography."""
from pathlib import Path
import struct
from PIL import Image, ImageEnhance, ImageDraw, ImageFont
from prepare_video import HEADER, WIDTH, HEIGHT, FPS, RATE, validate

# Two lines under the AmiWind name on the startup screen. A build type may
# select other lines (tools/build_aga.py startup_lines, tools/miniwind.py).
STARTUP_LINES = ('An open-source RPG engine', 'for the Commodore Amiga')
# CHIM builds (from v0.0.33, the first CHIM Engine release) show one line
# instead; legacy-engine builds keep STARTUP_LINES (never "powered by CHIM" on
# a legacy build). "CHIM" is drawn in the console font like MiniWind's version
# line: the game font's capital H is an uncial h.
CHIM_STARTUP_LINES = ((('RPG engine powered by ', 'game'), ('CHIM', 'console')),)
# Widest text line on the startup screen: 8-pixel margins on both sides.
TEXT_WIDTH = WIDTH - 16
# Logo box, gap under it and line height without a converted game font.
LOGO_BOX = (304, 80)
LOGO_GAP = 8
FALLBACK_LINE_HEIGHT = 14
# Free rows kept between the last text line and an engine-drawn prompt line.
PROMPT_GAP = 4
# Startup stream timing in frames (10 fps): fade in, fully visible, fade out.
FADE_IN, VISIBLE, FADE_OUT = 20, 50, 10
# A held screen (an engine prompt waits under it) ends fully visible: fade in,
# then one second visible; the engine keeps showing the last frame.
HELD_VISIBLE = 10
# A line is a string (all in the game font) or a sequence of (text, font)
# segments, font GAME_FONT or CONSOLE_FONT. The console font is the engine's own
# 8x8 conchars atlas (tools/debug_font.py, staged by tools/prepare_quake.py), the
# font of the engine-drawn MiniWind prompt. Magic Cards' capital H is an uncial
# h, so MiniWind draws "CHIM v<CHIM_VERSION>" in the console font (tools/miniwind.py).
GAME_FONT, CONSOLE_FONT = 'game', 'console'
CONSOLE_CELL = 8
# Console glyphs have ink on rows 0-6: capitals and digits end on row 6.
CONSOLE_BASELINE = 7
TEXT_RGB = (223, 199, 144)


def fallback_width(text):
    """Pixel width of a line in Pillow's default font (no converted game font)."""
    font = ImageFont.load_default()
    if hasattr(font, 'getlength'):
        return int(-(-font.getlength(text) // 1))
    return font.getsize(text)[0]


def startup_layout(lines, line_height, prompt_top=None):
    """(logo top, first text line top) on the 320x200 startup screen. The normal
    two lines keep their fixed places; other lines centre logo and text together,
    above prompt_top (the row where the engine draws a prompt line) when given."""
    if tuple(lines) == STARTUP_LINES and prompt_top is None:
        return 53, 141
    area = HEIGHT if prompt_top is None else prompt_top - PROMPT_GAP
    block = LOGO_BOX[1] + LOGO_GAP + len(lines) * line_height
    if not lines or block > area - (16 if prompt_top is None else 0):
        raise ValueError('Startup screen lines do not fit under the logo: %d lines' % len(lines))
    top = (area - block) // 2
    return top, top + LOGO_BOX[1] + LOGO_GAP


def startup_gains(held=False):
    """Brightness of each startup stream frame: fade in, visible, fade out; a
    held screen (held=True) ends on a fully visible frame instead."""
    gains = [i / FADE_IN for i in range(FADE_IN)]
    if held:
        return gains + [1] * HELD_VISIBLE
    return gains + [1] * VISIBLE + [i / FADE_OUT for i in range(FADE_OUT - 1, -1, -1)]


def text_width(font, text):
    return sum(font[8 + c * 8 + 6] for c in text.encode('cp1252'))


def line_segments(line):
    """[(text, font)] of a startup screen line: a string is one game-font segment."""
    if isinstance(line, str):
        return [(line, GAME_FONT)]
    segments = [tuple(segment) for segment in line]
    if not segments or any(len(segment) != 2 or not isinstance(segment[0], str) or not segment[0]
                           or segment[1] not in (GAME_FONT, CONSOLE_FONT) for segment in segments):
        raise ValueError('Startup screen line segments must be (text, %r or %r): %r'
                         % (GAME_FONT, CONSOLE_FONT, line))
    return segments


def line_text(line):
    """The plain text of a startup screen line (receipts, checks)."""
    return ''.join(text for text, _ in line_segments(line))


def console_atlas():
    """The engine's console font: the 128x128 conchars atlas, 8x8 cells, 0 = no ink."""
    from debug_font import readable_atlas
    return readable_atlas()


def console_missing(text, atlas=None):
    """Characters of text the console font draws nothing for (space excepted)."""
    atlas = console_atlas() if atlas is None else atlas

    def inked(c):
        x, y = (c % 16) * CONSOLE_CELL, (c // 16) * CONSOLE_CELL
        return any(atlas[(y + yy) * 128 + x + xx] for yy in range(CONSOLE_CELL) for xx in range(CONSOLE_CELL))
    return sorted({ch for ch in text if ch != ' ' and not (' ' <= ch <= '~' and inked(ord(ch)))})


def draw_console(image, text, x, y, rgb=TEXT_RGB, atlas=None):
    """Draw text in the console font with its cells' top row at y, as the engine
    draws its prompt (aw_movie.c draw_prompt: 8-pixel cells, every inked pixel)."""
    atlas = console_atlas() if atlas is None else atlas
    for i, c in enumerate(text.encode('ascii')):
        cx, cy = (c % 16) * CONSOLE_CELL, (c // 16) * CONSOLE_CELL
        for yy in range(CONSOLE_CELL):
            for xx in range(CONSOLE_CELL):
                px, py = x + i * CONSOLE_CELL + xx, y + yy
                if atlas[(cy + yy) * 128 + cx + xx] and 0 <= px < image.width and 0 <= py < image.height:
                    image.putpixel((px, py), rgb)


def game_baseline(font):
    """Row under the game font's capitals, from the line top: the most common
    glyph bottom of A-Z (the lower one on a tie)."""
    bottoms = {}
    for c in range(ord('A'), ord('Z') + 1):
        _, w, h, _, top, _, _ = struct.unpack_from('<HBBbbBB', font, 8 + c * 8)
        if w and h:
            bottoms[top + h] = bottoms.get(top + h, 0) + 1
    if not bottoms:
        return font[5]
    return max(bottoms, key=lambda bottom: (bottoms[bottom], bottom))


def segment_layout(line, measure, baseline):
    """([(text, font, x offset, y offset)], width) of a line's segments: game-font
    text measured by measure(text), console text 8 pixels a character; a console
    segment sits on the game font's baseline (row `baseline` under the line top)."""
    out, x = [], 0
    for text, kind in line_segments(line):
        if kind == CONSOLE_FONT:
            out.append((text, kind, x, baseline - CONSOLE_BASELINE))
            x += len(text) * CONSOLE_CELL
        else:
            out.append((text, kind, x, 0))
            x += measure(text)
    return out, x


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


MENU_LOGO_SIZE = (200, 40)
# The palette's own gold ramp (UI-MENU-LOGO-32): hue in degrees, minimum
# saturation and brightness (0..1) of the entries the menu logo may use.
GOLD_HUE = (30.0, 60.0)
GOLD_MIN_SATURATION = 0.25
GOLD_MIN_VALUE = 0.08


def menu_logo_excluded():
    """Entries the menu logo never uses: the reserved UI slots (status-bar
    colours), the sky bank repainted after the logo is made, transparent 255."""
    from ui_palette import RESERVED
    from sky_palette_overlay import BANK
    return set(RESERVED) | set(BANK) | {255}


def gold_ramp(palette):
    """Indices of the palette's gold entries and of its black, both outside
    the excluded entries."""
    import colorsys
    if len(palette) != 768:
        raise ValueError('Expected a 256-colour game palette')
    excluded = menu_logo_excluded()
    allowed = [i for i in range(256) if i not in excluded]
    ramp = []
    for i in allowed:
        h, s, v = colorsys.rgb_to_hsv(*(c / 255 for c in palette[i * 3:i * 3 + 3]))
        if GOLD_HUE[0] <= h * 360 <= GOLD_HUE[1] and s >= GOLD_MIN_SATURATION and v >= GOLD_MIN_VALUE:
            ramp.append(i)
    if len(ramp) < 4:
        raise ValueError('Game palette has no usable gold ramp for the menu logo')
    black = min(allowed, key=lambda i: (sum(palette[i * 3:i * 3 + 3]), i))
    return ramp, black


def luma(rgb):
    return .299 * rgb[0] + .587 * rgb[1] + .114 * rgb[2]


def prepare_menu_logo(source, palette_path, target, style='gold', rule=None):
    """Write the 200x40 AWI1 menu logo.

    style 'gold' (default): the name-only source mapped onto the palette's
    gold ramp, brightness first, no dither. style 'legacy': the previous
    method, kept for comparison: whole-palette nearest colours of the source
    as given (the old wordmark with its rule above the name).
    rule None (default) or 'below': an optional gold rule under the name;
    a rule is never drawn above it."""
    width, height = MENU_LOGO_SIZE
    palette = Path(palette_path).read_bytes()
    if len(palette) != 768:
        raise ValueError('Expected a 256-colour game palette')
    if style == 'legacy':
        if rule is not None:
            raise ValueError('The legacy menu logo takes its rule from the source')
        image = wordmark(source, MENU_LOGO_SIZE)
        full = Image.new('RGBA', MENU_LOGO_SIZE, (0, 0, 0, 255))
        full.alpha_composite(image, ((width - image.width) // 2, (height - image.height) // 2))
        pal = Image.new('P', (1, 1)); pal.putpalette(palette)
        result = full.convert('RGB').quantize(palette=pal, dither=Image.Dither.NONE)
        Path(target).write_bytes(b'AWI1' + struct.pack('<HH', width, height) + result.tobytes())
        return
    if style != 'gold':
        raise ValueError('Unknown menu logo style: ' + str(style))
    if rule not in (None, 'below'):
        raise ValueError('A menu logo rule can only go below the name')
    ramp, black = gold_ramp(palette)
    gap = 3 if rule else 0
    image = wordmark(source, (width, height - gap))
    top = (height - gap - image.height) // 2
    full = Image.new('RGBA', MENU_LOGO_SIZE, (0, 0, 0, 255))
    full.alpha_composite(image, ((width - image.width) // 2, top))
    colours = [tuple(palette[i * 3:i * 3 + 3]) for i in ramp]
    lumas = [luma(c) for c in colours]
    cache = {}

    def nearest(rgb):
        if rgb not in cache:
            y = luma(rgb)
            cache[rgb] = min(range(len(ramp)), key=lambda k: (
                4 * (lumas[k] - y) ** 2 + .25 * sum((a - b) ** 2 for a, b in zip(colours[k], rgb)), k))
        return cache[rgb]

    pixels = bytearray()
    for rgb in full.convert('RGB').getdata():
        # Composited near-black background and glow stay the palette's black.
        pixels.append(black if luma(rgb) < 12 else ramp[nearest(rgb)])
    if rule:
        bright = ramp[max(range(len(ramp)), key=lambda k: (lumas[k], -k))]
        row = top + image.height + gap - 2
        left = (width - image.width) // 2
        for x in range(left, left + image.width):
            pixels[row * width + x] = bright
    Path(target).write_bytes(b'AWI1' + struct.pack('<HH', width, height) + bytes(pixels))


def draw_segment_lines(image, lines, font, measure, text_top, line_height):
    """Draw lines of mixed fonts, each centred as a whole, its segments side by side."""
    if font:
        baseline = game_baseline(font)
    else:
        draw, default = ImageDraw.Draw(image), ImageFont.load_default()
        baseline = draw.textbbox((0, 0), 'H', font=default)[3]
    atlas = console_atlas()
    for i, line in enumerate(lines):
        top = text_top + i * line_height
        segments, width = segment_layout(line, measure, baseline)
        left = (WIDTH - width) // 2
        for text, kind, dx, dy in segments:
            if kind == CONSOLE_FONT:
                draw_console(image, text, left + dx, top + dy, atlas=atlas)
            elif font:
                draw_font(image, font, text, left + dx, top + dy)
            else:
                draw.text((left + dx, top + dy), text, fill=TEXT_RGB, font=default)


def prepare_logo(source, target, font_path=None, lines=None, prompt_top=None):
    """The startup logo stream: the wordmark and `lines` (default STARTUP_LINES)
    in the converted game font, centred, under it. A line given as (text, font)
    segments draws its CONSOLE_FONT segments in the engine's console font, the
    line still centred as a whole.

    prompt_top: the row where the engine draws a prompt line and waits (the
    MiniWind "Press ENTER to start", engine/aga/src/aw_movie.c): the text stays
    above it, the rows from it down stay black, and the stream ends on the fully
    visible screen (no fade out) for the engine to hold."""
    target = Path(target)
    lines = list(STARTUP_LINES if lines is None else lines)
    font = load_font(font_path) if font_path and Path(font_path).is_file() else None
    line_height = font[5] if font else FALLBACK_LINE_HEIGHT
    logo_top, text_top = startup_layout(lines, line_height, prompt_top)
    measure = (lambda text: text_width(font, text)) if font else fallback_width
    if tuple(lines) != STARTUP_LINES:
        for line in lines:
            text = line_text(line)
            if not text or any(not (' ' <= c <= '~') for c in text):
                raise ValueError('Startup screen line is not printable: %r' % text)
            if segment_layout(line, measure, 0)[1] > TEXT_WIDTH:
                raise ValueError('Startup screen line does not fit: %r' % text)
            game = ''.join(part for part, kind in line_segments(line) if kind == GAME_FONT)
            console = ''.join(part for part, kind in line_segments(line) if kind == CONSOLE_FONT)
            # Every character must be one its font has (a glyph that advances, an inked cell).
            missing = sorted({c for c in game if font and not font[8 + ord(c) * 8 + 6]})
            if missing:
                raise ValueError('The game font has no glyph for %s in startup screen line %r'
                                 % (', '.join(repr(c) for c in missing), text))
            missing = console_missing(console) if console else []
            if missing:
                raise ValueError('The console font has no glyph for %s in startup screen line %r'
                                 % (', '.join(repr(c) for c in missing), text))
    image = wordmark(source, LOGO_BOX)
    full = Image.new('RGBA', (WIDTH, HEIGHT), (0, 0, 0, 255))
    full.alpha_composite(image, ((WIDTH-image.width)//2, logo_top + (LOGO_BOX[1]-image.height)//2))
    full = full.convert('RGB')
    if all(isinstance(line, str) for line in lines):
        if font:
            for i, line in enumerate(lines):
                draw_font(full, font, line, (WIDTH-text_width(font, line))//2, text_top+i*font[5])
        else:
            draw = ImageDraw.Draw(full)
            for i, line in enumerate(lines):
                draw.text((WIDTH//2, text_top+i*FALLBACK_LINE_HEIGHT), line, anchor='mt', fill=(223,199,144), font=ImageFont.load_default())
    else:
        draw_segment_lines(full, lines, font, measure, text_top, line_height)
    if prompt_top is not None:
        # The prompt's rows stay black: nothing the stream draws reaches them.
        full.paste((0, 0, 0), (0, prompt_top - PROMPT_GAP, WIDTH, HEIGHT))
    # Two-second fade, five seconds fully visible, one-second fade to black (a
    # held screen: the fade in, then one second fully visible).
    gains = startup_gains(prompt_top is not None)
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


def prepare_opening_card(captions, font_path, target, movie_frames):
    """A runtime-switchable first quote; leave the original AWV audio/video intact."""
    import json
    cards = json.loads(Path(captions).read_text())
    if not isinstance(cards, list) or not cards or not isinstance(cards[0], dict):
        raise ValueError('Expected a nonempty private title-card list')
    card = cards[0]
    start, end, text = card.get('start'), card.get('end'), card.get('text')
    if (not isinstance(start, (int, float)) or not isinstance(end, (int, float))
            or not 0 <= start < end <= movie_frames / FPS
            or not isinstance(text, str) or not text.strip()):
        raise ValueError('Invalid opening-card time or text')
    first, last = int(start * FPS), int(end * FPS)
    if last <= first:
        raise ValueError('Opening card must last at least one frame')
    result = draw_text_card(Image.new('RGB', (WIDTH, HEIGHT)), text, font_path)
    indexed = result.quantize(colors=256, dither=Image.Dither.NONE)
    raw = (struct.pack('>4sIII', b'AWT1', first, last, 0)
           + bytes(indexed.getpalette()).ljust(768, b'\0')[:768] + indexed.tobytes())
    Path(target).write_bytes(raw)
    return {'first_frame': first, 'end_frame': last, 'bytes': len(raw)}
