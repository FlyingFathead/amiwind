#!/usr/bin/env python3
"""Convert an owner's intro movie to bounded native AWV1 video/PCM streaming."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from mwad.paths import ensure_external

WIDTH, HEIGHT, FPS, RATE = 320, 200, 10, 11025
HEADER = struct.Struct(">4sHHHHII12x")
PIXELS = WIDTH * HEIGHT
MAX_FRAMES = 18000


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def validate(path):
    """Validate dimensions, reserved fields, exact sizes and all payload bytes."""
    with Path(path).open("rb") as stream:
        header = stream.read(32)
        if len(header) != 32:
            raise ValueError("Truncated video header")
        magic, w, h, fps, rate, frames, samples = HEADER.unpack(header)
        if ((magic, fps, rate) != (b"AWV1", FPS, RATE)
                or (w, h) not in ((160, 100), (320, 200))
                or any(header[20:]) or not 1 <= frames <= MAX_FRAMES
                or samples != (frames * RATE + FPS - 1) // FPS):
            raise ValueError("Unsupported video header")
        remaining = 768 + frames * w * h + samples
        while remaining:
            chunk = stream.read(min(65536, remaining))
            if not chunk:
                raise ValueError("Truncated video payload")
            remaining -= len(chunk)
        if stream.read(1):
            raise ValueError("Trailing video payload")
    return {"frames": frames, "samples": samples, "seconds": frames / FPS,
            "width": w, "height": h}


def prepare_video(source, output, ffmpeg="ffmpeg", size=(320, 200), captions=None, font=None):
    source = Path(source).resolve()
    if not source.is_file():
        raise ValueError("Supply the owned Data Files/Video/mw_intro.bik file")
    output = ensure_external(output, "movie conversion")
    output.mkdir(parents=True, exist_ok=False)
    target = output / "mw_intro.awv"
    width, height = size
    if size not in ((160, 100), (320, 200)):
        raise ValueError("Choose 320x200 or the retained 160x100 conversion")
    pixels = width * height
    cards = json.loads(Path(captions).read_text()) if captions else []
    if cards and (size != (320, 200) or font is None):
        raise ValueError("Readable title cards require 320x200 and a converted font")
    if cards:
        from prepare_logo import draw_text_card
        for card in cards:
            if not (0 <= card["start"] < card["end"] <= 1800 and
                    isinstance(card["text"], str) and len(card["text"]) <= 1024):
                raise ValueError("Invalid title-card timing or text")
    with tempfile.TemporaryDirectory(prefix="amiwind-video-") as tmp:
        raw, pcm = Path(tmp) / "rgb.raw", Path(tmp) / "audio.raw"
        # Fit the source display aspect ratio, then letterbox; never crop titles.
        filters = (f"fps={FPS},scale={width}:{height}:flags=lanczos:force_original_aspect_ratio=decrease:"
                   "force_divisible_by=2,setsar=1,"
                   f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black")
        subprocess.run([ffmpeg, "-v", "error", "-nostdin", "-i", str(source), "-an",
                        "-t", "1800.1", "-vf", filters, "-pix_fmt", "rgb24",
                        "-f", "rawvideo", str(raw)], check=True)
        size = raw.stat().st_size
        frames, tail = divmod(size, pixels * 3)
        if tail or not 1 <= frames <= MAX_FRAMES:
            raise ValueError("Expected a nonempty movie no longer than 30 minutes")
        samples = (frames * RATE + FPS - 1) // FPS
        subprocess.run([ffmpeg, "-v", "error", "-nostdin", "-i", str(source), "-vn",
                        "-t", str(frames / FPS), "-ac", "1", "-ar", str(RATE),
                        "-af", "aresample=osf=u8:dither_method=triangular",
                        "-f", "s8", str(pcm)], check=True)
        # A fixed palette avoids flashing between frames. Sample the whole movie
        # at bounded cost instead of building it from the opening black frame.
        picks = sorted({i * (frames - 1) // 255 for i in range(256)})
        contact = Image.new("RGB", (40, 25 * len(picks)))
        with raw.open("rb") as stream:
            for row, frame in enumerate(picks):
                stream.seek(frame * pixels * 3)
                image = Image.frombytes("RGB", (width, height), stream.read(pixels * 3))
                for card in cards:
                    if card["start"] <= frame / FPS < card["end"]:
                        image = draw_text_card(image, card["text"], font)
                contact.paste(image.resize((40, 25)), (0, row * 25))
        sampled = contact.quantize(colors=252 if cards else 256)
        palette_bytes = bytes(sampled.getpalette()).ljust(768, b"\0")[:768]
        if cards:
            # Tiny palette-study thumbnails dilute narrow font strokes. Reserve
            # exact ink shades so bright gold text cannot become a blue moon color.
            palette_bytes=palette_bytes[:756]+bytes((74,66,48,148,132,96,223,199,144,0,0,0))
        palette=Image.new('P',(1,1));palette.putpalette(palette_bytes)
        with target.open("xb") as dst, raw.open("rb") as src:
            dst.write(HEADER.pack(b"AWV1", width, height, FPS, RATE, frames, samples))
            dst.write(palette_bytes)
            for frame in range(frames):
                image = Image.frombytes("RGB", (width, height), src.read(pixels * 3))
                for card in cards:
                    if card["start"] <= frame / FPS < card["end"]:
                        image = draw_text_card(image, card["text"], font)
                dst.write(image.quantize(palette=palette, dither=Image.Dither.NONE).tobytes())
            with pcm.open("rb") as audio:
                remaining = samples
                while remaining:
                    take = min(65536, remaining)
                    dst.write(audio.read(take).ljust(take, b"\0"))
                    remaining -= take
    result = validate(target)
    result.update(format="AWV1", source=source.name, width=width, height=height, fps=FPS,
                  rate=RATE, channels=1, bits=8, palette="fixed 256 colours",
                  bytes=target.stat().st_size, sha256=digest(target),
                  source_sha256=digest(source))
    if captions:
        result.update(title_cards=cards, title_cards_sha256=digest(captions), font_sha256=digest(font))
    (output / "video-conversion.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--ffmpeg", default="ffmpeg")
    parser.add_argument("--low-res", action="store_true", help="Retain the 160x100 low-bandwidth option")
    parser.add_argument("--captions", type=Path, help="Private JSON title cards: start/end seconds and text")
    parser.add_argument("--font", type=Path, help="Owned converted AWF1 font for native-pixel title cards")
    args = parser.parse_args()
    print(json.dumps(prepare_video(args.source, args.out, args.ffmpeg,
        (160, 100) if args.low_res else (320, 200), args.captions, args.font), indent=2))
