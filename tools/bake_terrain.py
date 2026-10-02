"""Bake coarse terrain colours from the owner's base-game texture pixels."""
import io
import json
from pathlib import Path, PurePosixPath

from mwad.audit import BSA, normpath
from mwad.paths import child_ci


def bake_colours(data_files, area, grids, heights, out):
    from PIL import Image
    bsa = BSA(child_ci(data_files, "Morrowind.bsa"))
    materials = json.loads((area / "materials.json").read_text())
    samples, records = {}, []
    with bsa.path.open("rb") as archive:
        for number, material in materials.items():
            texture = material.get("texture")
            if not texture:
                continue
            name = normpath("textures/" + texture)
            if ".." in Path(name).parts or Path(name).is_absolute():
                raise ValueError("Unsafe terrain texture path")
            candidates = [str(PurePosixPath(name).with_suffix(".dds")), name]
            chosen = next((p for p in candidates if p in bsa.entries), None)
            if chosen is None:
                raise ValueError(f"Missing base-game terrain texture: {texture}")
            record = bsa.entries[chosen]
            archive.seek(record["offset"])
            raw = archive.read(record["bytes"])
            with Image.open(io.BytesIO(raw)) as im:
                samples[int(number)] = im.convert("RGB").resize((2, 2), Image.Resampling.BOX)
            records.append({"material": int(number), "archive_path": chosen, "bytes": len(raw)})
    cells = {tuple(g["cell"]): g for g in grids}
    rgb, land_indices = [], []
    for y in range(97):
        for x in range(97):
            gx, gy = min(191, x * 2), min(191, y * 2)
            cell = cells[(gx // 64 - 3, gy // 64 - 10)]
            material = cell["materials"][(gy % 64) // 4][(gx % 64) // 4]
            if material not in samples:
                raise ValueError(f"No texture sample for terrain material {material}")
            colour = samples[material].getpixel(((gx % 4) // 2, (gy % 4) // 2))
            dx = heights[y * 2][min(192, x * 2 + 2)] - heights[y * 2][max(0, x * 2 - 2)]
            dy = heights[min(192, y * 2 + 2)][x * 2] - heights[max(0, y * 2 - 2)][x * 2]
            light = 1.6 * min(1.25, max(.70, 1 - (dx - dy) / 800))
            rgb.append(tuple(min(255, round(c * light)) for c in colour))
            if heights[y * 2][x * 2] > 0:
                land_indices.append(y * 97 + x)
    if not land_indices:
        raise ValueError("Terrain colour bake needs at least one land sample")
    strip = Image.new("RGB", (len(land_indices), 1))
    strip.putdata([rgb[i] for i in land_indices])
    quantized = strip.quantize(colors=3, method=Image.Quantize.MEDIANCUT)
    palette = quantized.getpalette()[:9]
    palette += [0] * (9 - len(palette))
    palette = [min(15, (c + 8) // 17) * 17 for c in palette]
    words = [0x678, 0x345, 0, 0, 0x677, 0, 0x678, 0xdc9]
    indexes = (2, 3, 5)
    for i, index in enumerate(indexes):
        r, g, b = palette[i*3:i*3+3]
        words[index] = (r // 17 << 8) | (g // 17 << 4) | b // 17
    result = [1] * (97 * 97)
    for index, colour in zip(land_indices, quantized.tobytes()):
        result[index] = indexes[colour]
    preview = Image.new("P", (97, 97))
    preview.putdata(result)
    colours = [component * 17 for word in words for component in (word >> 8 & 15, word >> 4 & 15, word & 15)]
    preview.putpalette(colours + [0] * (768 - len(colours)))
    preview.save(out / "converted/terrain-colour-bake.png")
    return result, words, {"textures": records, "sampling": "2x2 averaged texture samples per material tile",
                           "land_palette_colours": 3, "scope": "Prebaked coarse surface colours; no runtime UV texture mapping"}
