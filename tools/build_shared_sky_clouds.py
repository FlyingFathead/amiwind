# SPDX-License-Identifier: GPL-3.0-only
"""Convert a user-provided RGBA cloud image to AmiWind's two-layer sky.

The output is private generated artwork, never a source-distribution asset.
The 128x128 left layer uses zero for holes and neutral indexed cloud tones.
The right layer uses atmosphere index 224 and optional secondary tones 2/4/5.
V2/V3 read these distinct roles. Alpha is baked into coverage and tonal contrast,
not retained as RGBA. No original artwork is bundled with this tool.
"""
from pathlib import Path
import argparse
import hashlib
import json
from PIL import Image

SKY_BANK = (222, 133, 95, 156, 140, 83, 221)
SECONDARY_TONES = (2, 4, 5)
FORBIDDEN = frozenset((0, 224, 255, *SECONDARY_TONES, *SKY_BANK, *range(225, 254)))


def build_cloud_sky(image, palette, *, alpha_cutoff=16, contrast=2.0,
                    secondary=None, secondary_cutoff=192):
    if len(palette) != 768:
        raise ValueError('Palette must contain 256 RGB triples')
    if not 0 <= alpha_cutoff < 255 or not 0 < contrast <= 4:
        raise ValueError('Invalid alpha cutoff or contrast')
    if not 0 <= secondary_cutoff < 255:
        raise ValueError('Invalid secondary alpha cutoff')
    image = image.convert('RGBA').resize((128, 128), Image.Resampling.LANCZOS)
    if secondary is not None:
        secondary = secondary.convert('RGBA').resize((128, 128), Image.Resampling.LANCZOS)
    tones = [tuple(palette[i:i + 3]) for i in range(0, 768, 3)]
    candidates = [i for i in range(256) if i not in FORBIDDEN]
    ramp = [min(candidates, key=lambda i: sum((v - target) ** 2 for v in tones[i]))
            for target in range(256)]
    output = bytearray(32768)
    cloud_count = 0
    secondary_count = 0
    for y in range(128):
        for x in range(128):
            alpha = image.getpixel((x, y))[3]
            output[y * 256 + x] = ramp[min(255, round(alpha * contrast))] if alpha and alpha >= alpha_cutoff else 0
            output[y * 256 + x + 128] = 224
            if secondary is not None:
                alpha2 = secondary.getpixel((x, y))[3]
                if alpha2 and alpha2 >= secondary_cutoff:
                    tone = min(2, (alpha2 - secondary_cutoff) * 3 // (256 - secondary_cutoff))
                    output[y * 256 + x + 128] = SECONDARY_TONES[tone]
                    secondary_count += 1
            cloud_count += bool(output[y * 256 + x])
    left = {output[y * 256 + x] for y in range(128) for x in range(128)}
    assert not (left - {0}) & FORBIDDEN
    return bytes(output), {'width': 256, 'height': 128, 'bytes': len(output),
        'cloud_pixels': cloud_count, 'transparent_pixels': 16384 - cloud_count,
        'left_indices': sorted(left),
        'right_indices': sorted({output[y * 256 + x + 128] for y in range(128) for x in range(128)}),
        'secondary_cloud_pixels': secondary_count, 'secondary_alpha_cutoff': secondary_cutoff,
        'alpha_cutoff': alpha_cutoff, 'alpha_contrast': contrast,
        'alpha_preserved': False, 'source_rgb_preserved': False,
        'interpretation': 'original cloud shape; neutral source tones colored by runtime sky profiles'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cloud-image', type=Path, required=True)
    parser.add_argument('--palette', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--secondary-image', type=Path)
    parser.add_argument('--secondary-cutoff', type=int, default=192)
    parser.add_argument('--alpha-cutoff', type=int, default=16)
    parser.add_argument('--contrast', type=float, default=2.0)
    args = parser.parse_args()
    if args.output.exists() or args.output.with_suffix('.json').exists():
        raise SystemExit('Refusing to replace an existing sky or receipt')
    raw = args.cloud_image.read_bytes()
    palette = args.palette.read_bytes()
    secondary = None
    secondary_hash = None
    if args.secondary_image:
        secondary_hash = hashlib.sha256(args.secondary_image.read_bytes()).hexdigest()
        with Image.open(args.secondary_image) as opened:
            if 'A' not in opened.getbands():
                raise ValueError('Secondary cloud input needs an explicit alpha channel')
            secondary = opened.convert('RGBA')
    with Image.open(args.cloud_image) as image:
        if 'A' not in image.getbands():
            raise ValueError('Cloud input needs an explicit alpha channel')
        sky, report = build_cloud_sky(image, palette, alpha_cutoff=args.alpha_cutoff,
                                      contrast=args.contrast, secondary=secondary,
                                      secondary_cutoff=args.secondary_cutoff)
        report['source_size'] = list(image.size)
    report.update(source_sha256=hashlib.sha256(raw).hexdigest(),
                  palette_sha256=hashlib.sha256(palette).hexdigest(),
                  secondary_source_sha256=secondary_hash,
                  output_sha256=hashlib.sha256(sky).hexdigest())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(sky)
    args.output.with_suffix('.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
