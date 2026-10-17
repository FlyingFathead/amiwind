#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Generate local FS-UAE and WinUAE configurations for every verified HDF."""
import argparse
import importlib.util
import json
from pathlib import Path
import os
import re
import shutil
import sys
from project_version import ROOT, VERSION
sys.path.insert(0, str(ROOT / 'src'))


def launcher():
    spec = importlib.util.spec_from_file_location('amiwind_config_launcher', ROOT / 'tools/AmiWind-FS-UAE-launcher.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ROM_PLACEHOLDER = '/path/to/your/kickstart-3.1-a1200.rom'
LAUNCHER_NAME = 'AmiWind-FS-UAE-launcher.py'
FS_JIT_NOTE = '# JIT is on for speed (jit_compiler = 1). If the game misbehaves, set it to 0 (much slower).'
WIN_JIT_NOTE = '; JIT is on for speed (cachesize=8192). If the game misbehaves, set cachesize=0 (much slower).'


def backup_name(path):
    """First free <name>.bak, <name>.bak2, ... beside the file."""
    candidate = path.with_name(path.name + '.bak')
    number = 1
    while candidate.exists() or candidate.is_symlink():
        number += 1
        candidate = path.with_name(path.name + '.bak%d' % number)
    return candidate


def write_text_with_backup(path, content):
    """Write an LF file; an existing different file is first kept as .bak (never silently overwritten)."""
    if path.is_symlink():
        raise ValueError('Existing emulator configuration is a symlink; preserved: ' + str(path))
    if path.exists():
        if path.read_bytes() == content.encode('utf-8'):
            return False
        backup = backup_name(path)
        shutil.copy2(path, backup)
        print('Kept your previous configuration as ' + backup.name, flush=True)
    with path.open('w', encoding='utf-8', newline='\n') as stream:
        stream.write(content)
    return True


def write_launcher(folder):
    """Put the portable Python launcher beside the image (existing different copy kept as .bak)."""
    source = ROOT / 'tools' / LAUNCHER_NAME
    if not source.is_file():
        print('WARNING: ' + LAUNCHER_NAME + ' not found in the source tree; no launcher written.', flush=True)
        return None
    target = Path(folder) / LAUNCHER_NAME
    data = source.read_bytes()
    if target.is_symlink():
        raise ValueError('Existing launcher is a symlink; preserved: ' + str(target))
    if target.exists():
        if target.read_bytes() == data:
            return target
        shutil.copy2(target, backup_name(target))
    target.write_bytes(data)
    try:
        os.chmod(target, 0o755)
    except OSError:
        pass
    return target


def write_configs(image, rom=None, config_suffix='', fast_ram_mib=None):
    image = Path(image).resolve()
    if not image.is_file() or image.stat().st_size == 0:
        raise ValueError('Primary HDF missing or empty.')
    portable = launcher()
    fast_ram_mib = portable.FAST_RAM_DEFAULT_MIB if fast_ram_mib is None else portable.parse_fast_ram(fast_ram_mib)
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
    if not rom:
        print('WARNING: no Kickstart ROM given. The emulator configurations carry a placeholder: set '
              'kickstart_file (FS-UAE) / kickstart_rom_file (WinUAE) to your own A1200 Kickstart 3.1 ROM '
              '(none is shipped), or run the Python launcher, which asks for it.', flush=True)
    if any(c in rom for c in '\r\n'):
        raise ValueError('ROM path contains a newline.')
    fs_template = (ROOT / f'resources/emulators/AmiWind-v{version}-FS-UAE.fs-uae').read_text(encoding='utf-8')
    fs = portable.configured_text(fs_template, image, rom or ROM_PLACEHOLDER, fast_ram_mib)
    # Relative HDF names: the config sits beside its HDFs, so the folder can be moved or copied.
    fs = re.sub(r'(?m)^(hard_drive_[0-9]+ *= *).*[/\\]([^/\\\r\n]+\.hdf)[ \t]*$', r'\g<1>\g<2>', fs)
    fs = re.sub(r'(?m)^(jit_compiler *=)', lambda m: FS_JIT_NOTE + '\n' + m.group(1), fs, count=1)
    win_template = (ROOT / f'resources/emulators/AmiWind-v{version}-WinUAE.uae').read_text(encoding='utf-8')
    win_template = portable.fast_ram_winuae_text(win_template, fast_ram_mib)
    lines = [line for line in win_template.splitlines() if not re.match(r'(?:hardfile2|uaehf[0-9]+)=', line)]
    lines = [f'kickstart_rom_file={rom}' if line.startswith('kickstart_rom_file=') else line for line in lines]
    for i, disk in enumerate(disks):
        if any(c in str(disk) for c in ',\r\n'):
            raise ValueError('WinUAE HDF path contains an unsupported delimiter.')
        lines.append(f'hardfile2=rw,DH{i}:{disk},0,0,0,512,0,,uae{i}')
    lines = [WIN_JIT_NOTE + '\ncachesize=8192' if line.startswith('cachesize=') else line for line in lines]
    lines.insert(0, '; HDF paths below are absolute: edit them if you move this folder.')
    if not rom:
        lines.insert(1, '; SET kickstart_rom_file below to your own A1200 Kickstart 3.1 ROM (none is shipped).')
    outputs = {image.with_name(image.stem + config_suffix + '-FS-UAE.fs-uae'): fs,
               image.with_name(image.stem + config_suffix + '-WinUAE.uae'): '\n'.join(lines) + '\n'}
    for path in outputs:
        if path.is_symlink():
            raise ValueError('Existing emulator configuration is a symlink; preserved: ' + str(path))
    for path, content in outputs.items():
        write_text_with_backup(path, content)
    write_launcher(image.parent)
    try:
        from playtest_readmes import write_readmes      # private playtest packaging only (not in the public source)
    except ImportError:
        write_readmes = None
    if write_readmes:
        write_readmes(image.parent, version)
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
    launcher_file = Path(image).resolve().parent / LAUNCHER_NAME
    if launcher_file.is_file():
        lines.extend(['', 'Python launcher (asks for your ROM, then starts FS-UAE):', '', str(launcher_file)])
    section('\n'.join(lines))
    return paths


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', type=Path, required=True)
    parser.add_argument('--kickstart-file', type=Path)
    parser.add_argument('--fast-ram', metavar='MIB', help='Fast RAM in MiB for both profiles (default: the profile 16 MiB); '
                        'the same sizes as the launcher: 128, 256, 512, 1024, 1536 or another size the emulator can make')
    args = parser.parse_args()
    names = write_configs(args.image, args.kickstart_file, fast_ram_mib=args.fast_ram)
    receipt = args.image.resolve().parent / 'build.json'
    if not receipt.is_file(): receipt = args.image.resolve().parent / 'dry-run-build.json'
    record = json.loads(receipt.read_text(encoding='utf-8'))
    record['emulator_configs'] = names
    receipt.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8',newline='\n')
    print_outputs(args.image)


if __name__ == '__main__':
    main()
