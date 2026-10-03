#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Generate local FS-UAE and WinUAE configurations for every verified HDF."""
import argparse
import importlib.util
import json
from pathlib import Path
import re
import sys
from project_version import ROOT, VERSION
sys.path.insert(0, str(ROOT / 'src'))


def launcher():
    spec = importlib.util.spec_from_file_location('amiwind_config_launcher', ROOT / 'tools/AmiWind-FS-UAE-launcher.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_configs(image, rom=None, config_suffix=''):
    image = Path(image).resolve()
    if not image.is_file() or image.stat().st_size == 0:
        raise ValueError('Primary HDF missing or empty.')
    portable = launcher()
    disks = portable.image_disks(image)
    receipt = image.parent / 'build.json'
    if not receipt.is_file():
        receipt = image.parent / 'dry-run-build.json'
    record = json.loads(receipt.read_text(encoding='utf-8'))
    version = record['version']
    if version != VERSION:
        raise ValueError('Image version differs from the source configuration presets.')
    if rom and (not Path(rom).is_file() or Path(rom).stat().st_size == 0):
        raise ValueError('Owned Kickstart ROM missing or empty.')
    rom = str(Path(rom).resolve()) if rom else ''
    if any(c in rom for c in '\r\n'):
        raise ValueError('ROM path contains a newline.')
    fs_template = (ROOT / f'resources/emulators/AmiWind-v{version}-FS-UAE.fs-uae').read_text(encoding='utf-8')
    fs = portable.configured_text(fs_template, image, rom)
    win_template = (ROOT / f'resources/emulators/AmiWind-v{version}-WinUAE.uae').read_text(encoding='utf-8')
    lines = [line for line in win_template.splitlines() if not re.match(r'(?:hardfile2|uaehf[0-9]+)=', line)]
    lines = [f'kickstart_rom_file={rom}' if line.startswith('kickstart_rom_file=') else line for line in lines]
    for i, disk in enumerate(disks):
        if any(c in str(disk) for c in ',\r\n'):
            raise ValueError('WinUAE HDF path contains an unsupported delimiter.')
        lines.append(f'hardfile2=rw,DH{i}:{disk},0,0,0,512,0,,uae{i}')
    outputs = {image.with_name(image.stem + config_suffix + '-FS-UAE.fs-uae'): fs,
               image.with_name(image.stem + config_suffix + '-WinUAE.uae'): '\n'.join(lines) + '\n'}
    # Preflight both files before writing; preserve any user-edited configuration.
    for path, content in outputs.items():
        if path.is_symlink() or (path.exists() and path.read_text(encoding='utf-8') != content):
            raise ValueError('Existing emulator configuration differs; preserved: ' + str(path))
    for path, content in outputs.items():
        if not path.exists():
            with path.open('x', encoding='utf-8', newline='\n') as stream:
                stream.write(content)
    return [path.name for path in outputs]


def output_paths(image):
    image = Path(image).resolve()
    disks = launcher().image_disks(image)
    receipt = image.parent / 'build.json'
    if not receipt.is_file(): receipt = image.parent / 'dry-run-build.json'
    record = json.loads(receipt.read_text(encoding='utf-8'))
    configs = []
    for name in record.get('emulator_configs', []):
        if not isinstance(name, str) or any(c in name for c in '/\\:\r\n\0'):
            raise ValueError('Unsafe emulator configuration filename in receipt.')
        path = image.parent / name
        if path.is_symlink() or not path.is_file():
            raise ValueError('Emulator configuration missing: ' + str(path))
        if path.suffix not in ('.fs-uae', '.uae'):
            raise ValueError('Unknown emulator configuration format.')
        configs.append(dict(emulator='FS-UAE' if path.suffix == '.fs-uae' else 'WinUAE', path=str(path)))
    return dict(hdf_files=[str(path) for path in disks], emulator_configs=configs)


def print_outputs(image):
    from mwad.progress import section
    paths = output_paths(image)
    lines = ['Your .hdf file(s):', '']
    lines.extend(f'{i}. {path}' for i, path in enumerate(paths['hdf_files'], 1))
    lines.extend(['', 'FS-UAE and WinUAE runners:', ''])
    lines.extend(f"{i}. {entry['emulator']}: {entry['path']}" for i, entry in enumerate(paths['emulator_configs'], 1))
    section('\n'.join(lines))
    return paths


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', type=Path, required=True)
    parser.add_argument('--kickstart-file', type=Path)
    args = parser.parse_args()
    names = write_configs(args.image, args.kickstart_file)
    receipt = args.image.resolve().parent / 'build.json'
    if not receipt.is_file(): receipt = args.image.resolve().parent / 'dry-run-build.json'
    record = json.loads(receipt.read_text(encoding='utf-8'))
    record['emulator_configs'] = names
    receipt.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8',newline='\n')
    print_outputs(args.image)


if __name__ == '__main__':
    main()
