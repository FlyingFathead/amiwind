#!/usr/bin/env python3
"""Package only the verified asset-free image and its corresponding source."""
import argparse
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from mwad.paths import ensure_external
from build_aga import VERSION
from build_dry_run import digest
from release import create_candidate, validate_candidate, version


def package(image_dir, output):
    image_dir = ensure_external(image_dir, 'dry-run image directory')
    output = ensure_external(output, 'artifact output')
    output.mkdir(parents=True, exist_ok=True)
    stem = f'AmiWind-v{VERSION}-dry-run'
    image = image_dir / (stem + '.hdf')
    receipt = image_dir / 'dry-run-build.json'
    record = json.loads(receipt.read_text())
    if (record.get('kind') != 'asset-free test compile' or record.get('game_assets') is not False
            or record.get('rom_included') is not False or record.get('version') != VERSION
            or record.get('hdf_sha256') != digest(image)):
        raise ValueError('Image does not match an asset-free build receipt')
    source = output / f'AmiWind-v{version(ROOT)}-public-source.zip'
    result = output / (stem + '.zip')
    checksum = result.with_suffix('.zip.sha256')
    if any(p.exists() for p in (source, result, checksum)):
        raise ValueError('Artifact already exists; use a new output directory')
    create_candidate(ROOT, source)
    validate_candidate(ROOT, source)
    readme = (f'{stem}\n\nAsset-free test compile; not a playable demo.\n'
              'Attach the HDF as an RDB hard drive in your Amiga emulator.\n'
              'Supply your own licensed Kickstart 3.1 ROM. No ROM is included.\n'
              'The normal runtime reference is A1200/AGA, 68040/FPU, 2 MiB Chip + 16 MiB Fast.\n'
              'Booting displays the test-build notice. Stop the emulator to exit.\n\n'
              'To play, rebuild from your own Morrowind installation; see docs/LINUX_BUILD.md.\n'
              'The included source ZIP extracts into amiwind/ and contains corresponding source,\n'
              'build instructions and component licences. The native engine uses GPL-2.0-or-later.\n'
              'https://github.com/FlyingFathead/amiwind\n')
    with zipfile.ZipFile(result, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in (image, receipt, source):
            archive.write(path, stem + '/' + path.name)
        archive.write(ROOT / 'engine/aga/COPYING', stem + '/COPYING')
        archive.writestr(stem + '/README.txt', readme)
    with zipfile.ZipFile(result) as archive:
        if archive.testzip() is not None:
            raise ValueError('Dry-run archive CRC failure')
    checksum.write_text(digest(result) + '  ' + result.name + '\n')
    source.with_suffix('.zip.sha256').write_text(digest(source) + '  ' + source.name + '\n')
    print(result)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--image-dir', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    try:
        args = p.parse_args()
        package(args.image_dir, args.out)
    except (OSError, ValueError) as exc:
        p.exit(1, str(exc) + '\n')
