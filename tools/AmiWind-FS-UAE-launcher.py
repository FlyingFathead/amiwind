#!/usr/bin/env python3
"""Find a local AmiWind image, configure FS-UAE and launch it.

Python 3.8+ standard library only. Keep beside the versioned HDF and roms/.
Alternatively pass --directory to select the directory containing your HDFs.
"""
# SPDX-License-Identifier: GPL-3.0-only
import argparse
import configparser
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

REFERENCE_ROM_SHA256 = '6d43840d4099a74170ea0f0425b6257c3891ebcaa39c4d1840075a9ab22b5707'
SETTINGS_NAME = 'AmiWind-launcher.json'
DEFAULT_SETTINGS = {'format': 1, 'kickstart_rom': '', 'hdf': 'latest',
                    'fs_uae': 'fs-uae', 'confirm_launch': True}
VERSION = r'(\d+)\.(\d+)\.(\d+)(?:-([A-Za-z0-9][A-Za-z0-9._-]*))?'
IMAGE_NAME = re.compile(r'AmiWind-v(' + VERSION + r')\.hdf', re.IGNORECASE)
PROFILE_VALUES = {
    'amiga_model': 'A1200',
    'cpu': '68040-NOMMU',
    'fpu': '68040',
    'jit_compiler': '1',
    'uae_cpu_speed': 'max',
    'uae_cpu_24bit_addressing': 'false',
    'chip_memory': '2048',
    'slow_memory': '0',
    'fast_memory': '0',
    'zorro_iii_memory': '16384',
    'joystick_port_1': 'none',
    'middle_click_ungrab': '0',
    'keyboard_key_pageup': 'action_key_68',
    'keyboard_key_pagedown': 'action_key_69',
    'keyboard_key_home': 'action_key_6a',
    'keyboard_key_end': 'action_key_6c',
    'floppy_drive_volume': '0',
}
PROFILE_LABELS = (
    ('Amiga type', 'amiga_model', 'A1200'),
    ('CPU', 'cpu', '68040-NOMMU'),
    ('FPU', 'fpu', '68040 internal'),
    ('CPU speed', 'uae_cpu_speed', 'Fastest possible'),
    ('JIT', 'jit_compiler', 'ON'),
    ('24-bit addressing', 'uae_cpu_24bit_addressing', 'OFF'),
    ('Chip RAM', 'chip_memory', '2048 KiB'),
    ('Z3 Fast RAM', 'zorro_iii_memory', '16384 KiB'),
)
PRESET = '''# AmiWind v{version} accelerated Linux playtest preset.
# Local paths filled by AmiWind-FS-UAE-launcher.py.
# This is not a stock A1200 performance configuration.
[config]
amiga_model = A1200
cpu = 68040-NOMMU
fpu = 68040
jit_compiler = 1
uae_cpu_speed = max
uae_cpu_24bit_addressing = false
chip_memory = 2048
slow_memory = 0
fast_memory = 0
zorro_iii_memory = 16384
kickstart_file = {rom}
hard_drive_0 = {image}
hard_drive_0_type = hdf
joystick_port_1 = none
floppy_drive_volume = 0
fullscreen = 0
'''


def local_path(value, root):
    p = Path(value).expanduser()
    if not p.is_absolute():
        p = root / p
    p = p.resolve()
    if any(c in str(p) for c in '\r\n\0'):
        raise ValueError('File paths must not contain newline or NUL characters.')
    return p


def read_settings(root):
    path = root / SETTINGS_NAME
    if path.is_symlink():
        raise ValueError('Launcher settings are a symlink; preserved unchanged: ' + str(path))
    if not path.exists():
        return dict(DEFAULT_SETTINGS)
    def unique_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('Duplicate launcher setting: ' + key)
            result[key] = value
        return result
    saved = json.loads(path.read_text(encoding='utf-8-sig'), object_pairs_hook=unique_pairs)
    if not isinstance(saved, dict) or set(saved) - set(DEFAULT_SETTINGS):
        raise ValueError('Invalid or unknown launcher settings; settings preserved unchanged.')
    settings = dict(DEFAULT_SETTINGS, **saved)
    if type(settings['format']) is not int or settings['format'] != 1:
        raise ValueError('Unsupported launcher settings format; expected 1.')
    if type(settings['confirm_launch']) is not bool:
        raise ValueError('confirm_launch must be true or false.')
    for key in ('kickstart_rom', 'hdf', 'fs_uae'):
        if not isinstance(settings[key], str) or any(c in settings[key] for c in '\r\n\0'):
            raise ValueError('Invalid launcher setting: ' + key)
    if not settings['hdf'] or not settings['fs_uae']:
        raise ValueError('hdf and fs_uae settings must not be empty.')
    return settings


def portable_path(path, root):
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)


def version_key(version):
    m = re.fullmatch(VERSION, version, re.IGNORECASE)
    if not m:
        raise ValueError('Unsupported AmiWind version: ' + version)
    major, minor, patch, suffix = m.groups()
    rank, number = 5, 0  # A final release sorts after its prereleases.
    if suffix:
        known = re.fullmatch(r'(dev|test|alpha|beta|rc)[-._]?(\d*)', suffix, re.IGNORECASE)
        if known:
            rank = {'dev': 0, 'test': 1, 'alpha': 2, 'beta': 3, 'rc': 4}[known.group(1).lower()]
            number = int(known.group(2) or 0)
        else:
            # Arbitrary development labels have no reliable numeric order.
            # Modification time breaks this tie in select_image().
            rank, number = 0, -1
    return int(major), int(minor), int(patch), rank, number


def natural_key(name):
    return tuple((1, int(p)) if p.isdigit() else (0, p.casefold())
                 for p in re.split(r'(\d+)', name))


def select_image(root, requested=None, ask=False):
    if requested:
        path = local_path(requested, root)
        if re.search(r'-world-[0-9]+\.hdf$', path.name, re.IGNORECASE):
            raise ValueError('Select the boot HDF, not an additional world disk.')
        # An explicit working copy may use the optional -play suffix.
        match = IMAGE_NAME.fullmatch(re.sub(r'-play\.hdf$', '.hdf', path.name, flags=re.IGNORECASE))
        if not match:
            raise ValueError('Use an HDF named AmiWind-vVERSION.hdf (or -play.hdf).')
        choices = [(version_key(match.group(1)), path, match.group(1))]
    else:
        choices = []
        for path in root.iterdir():
            match = IMAGE_NAME.fullmatch(path.name)
            excluded = path.name.lower().endswith(('-play.hdf', '-backup.hdf', '-dry-run.hdf'))
            excluded = excluded or bool(re.search(r'-world-[0-9]+\.hdf$', path.name, re.IGNORECASE))
            if match and path.is_file() and not excluded:
                choices.append((version_key(match.group(1)), path, match.group(1)))
        if not choices:
            raise ValueError('No AmiWind-vVERSION.hdf found in the selected directory. Build or extract your playable image first.')
        choices.sort(key=lambda c: (c[0], c[1].stat().st_mtime_ns, natural_key(c[1].name), c[1].name), reverse=True)
    selected = 0
    if ask:
        print('Available AmiWind images (version order; modification date breaks ties):', flush=True)
        for i, (_, path, version) in enumerate(choices, 1):
            label = ' (suggested latest)' if i == 1 and not requested else ''
            date = datetime.fromtimestamp(path.stat().st_mtime).strftime('%Y-%m-%d %H:%M')
            print('  %d. v%s%s  [%s]  %s' % (i, version, label, date, path.name), flush=True)
        prompt = 'Run ' + ('latest ' if not requested else '') + 'AmiWind v' + choices[0][2]
        prompt += '? [Y/n' + (', or image number' if len(choices) > 1 else '') + ']: '
        while True:
            try:
                answer = input(prompt).strip().lower()
            except EOFError:
                return None
            if answer in ('n', 'no', 'q', 'quit'):
                return None
            if answer in ('', 'y', 'yes'):
                break
            if answer.isdigit() and 1 <= int(answer) <= len(choices):
                selected = int(answer) - 1
                break
            print('Enter Y, N' + (' or an image number from the list.' if len(choices) > 1 else '.'), flush=True)
    _, path, version = choices[selected]
    path = local_path(path, root)
    if not path.is_file() or path.stat().st_size == 0:
        raise ValueError('HDF missing or empty: ' + str(path))
    return path, version


def rom_hash(path):
    with path.open('rb') as stream:
        digest = hashlib.sha256()
        for block in iter(lambda: stream.read(65536), b''):
            digest.update(block)
    return digest.hexdigest()


def select_rom(root, requested=None):
    location = local_path(requested, root) if requested else root / 'roms'
    if requested and not location.is_dir():
        rom = location
        if not rom.is_file() or rom.stat().st_size not in (262144, 524288, 1048576):
            raise ValueError('ROM must be an existing 256 KiB, 512 KiB or 1 MiB file: ' + str(rom))
        digest = rom_hash(rom)
    else:
        folder = location
        if not folder.is_dir():
            raise ValueError('ROM directory not found: ' + str(folder) + '. Supply a ROM file or directory with --rom PATH.')
        candidates = sorted((p for p in folder.iterdir() if p.is_file() and
                             p.stat().st_size in (262144, 524288, 1048576)), key=lambda p: p.name.casefold())
        hashes = [(p, rom_hash(p)) for p in candidates]
        matches = [(p, h) for p, h in hashes if h == REFERENCE_ROM_SHA256]
        if matches:
            rom, digest = matches[0]  # Multiple reference copies are byte-identical.
        elif len(hashes) == 1:
            rom, digest = hashes[0]
        elif not hashes:
            raise ValueError('No plausible Kickstart ROM found directly in ' + str(folder) + '. Use --rom FILE if needed.')
        else:
            raise ValueError('Several ROMs found; none matches the reference A1200 ROM. Select a file:\n  ' +
                             '\n  '.join(str(p) for p, _ in hashes))
        rom = local_path(rom, root)
    if digest != REFERENCE_ROM_SHA256:
        print('[warn] Kickstart ROM SHA-256 does not match the development Kickstart 3.1 A1200 ROM.\n'
              '       Compatibility is unverified; launch will continue.\n'
              '       Expected: ' + REFERENCE_ROM_SHA256 + '\n'
              '       Found:    ' + digest, flush=True)
    else:
        print('Kickstart ROM SHA-256 matches the development Kickstart 3.1 A1200 ROM.', flush=True)
    return rom


def image_disks(image):
    """Read a verified image layout; never silently drop required world drives."""
    image = Path(image).resolve()
    receipt = image.parent / 'build.json'
    if not receipt.is_file():
        if list(image.parent.glob(image.stem + '-world-*.hdf')):
            raise ValueError('Multi-HDF images require their build.json layout receipt.')
        return [image]
    record = json.loads(receipt.read_text(encoding='utf-8'))
    if record.get('hdf_file') != image.name:
        raise ValueError('Selected HDF does not match build.json.')
    entries = record.get('hdf_files')
    if entries is None:
        return [image]  # Legacy single-HDF receipt.
    if not isinstance(entries, list) or not 1 <= len(entries) <= 9:
        raise ValueError('Invalid HDF layout in build.json.')
    disks, names = [], set()
    for i, entry in enumerate(entries):
        name = entry.get('file', '')
        if not name or any(c in name for c in '/\\:\r\n\0') or not name.endswith('.hdf') or name.casefold() in names:
            raise ValueError('Unsafe or duplicate HDF filename in build.json.')
        disk = image.parent / name
        if disk.is_symlink() or not disk.is_file():
            raise ValueError('Required HDF missing or symlinked: ' + name)
        if entry.get('readback') != 'passed' or disk.stat().st_size != entry.get('bytes'):
            raise ValueError('Required HDF does not match its verified layout: ' + name)
        if bool(entry.get('bootable')) != (i == 0):
            raise ValueError('HDF layout must have one boot drive first.')
        disks.append(disk)
        names.add(name.casefold())
    if disks[0] != image:
        raise ValueError('Primary HDF must be first in build.json.')
    return disks


def configured_text(text, image, rom):
    parser = configparser.ConfigParser(interpolation=None, delimiters=('=',), strict=True)
    try:
        parser.read_string(text)
    except configparser.Error as error:
        raise ValueError('Existing FS-UAE configuration is invalid; preserved unchanged: ' + str(error)) from error
    sections = [s for s in parser.sections() if s.lower() == 'config']
    if len(sections) != 1 or parser.defaults():
        raise ValueError('Expected one [config] section and no DEFAULT settings; configuration preserved unchanged.')
    values = dict(PROFILE_VALUES)
    values.update({'kickstart_file': str(rom), 'hard_drive_0': str(image),
                   'hard_drive_0_type': 'hdf'})
    disks = image_disks(image)
    managed_layout = (Path(image).parent / 'build.json').is_file()
    for i, disk in enumerate(disks):
        values.update({f'hard_drive_{i}': str(disk), f'hard_drive_{i}_type': 'hdf'})
    # Preserve unrelated custom settings/comments. Core AmiWind machine-profile
    # values, paths and HDF type are managed so repeat playtests cannot silently
    # fall back to a slow or incompatible emulator profile.
    lines = text.splitlines(keepends=True)
    result = []
    found = set()
    inside = False
    def missing():
        for key, value in values.items():
            if key not in found:
                if result and not result[-1].endswith(('\n', '\r')):
                    result[-1] += '\n'
                result.append(key + ' = ' + value + '\n')
                found.add(key)
    for line in lines:
        section = re.match(r'^\s*\[([^]]+)\]\s*(?:[#;].*)?$', line.rstrip('\r\n'))
        if section:
            if inside:
                missing()
            inside = section.group(1).lower() == 'config'
        match = re.match(r'^\s*([^#;\s][^=]*?)\s*=\s*(.*?)\s*$', line.rstrip('\r\n')) if inside else None
        if match:
            key = match.group(1).lower()
            if managed_layout and re.fullmatch(r'hard_drive_[0-9]+(?:_.*)?', key) and key not in values:
                continue  # Remove stale drives/settings from the previous verified layout.
            if key == 'uae_address_space_24':
                if '\n' in parser[sections[0]].get(key, ''):
                    raise ValueError('Managed configuration entries must use a single line: ' + key)
                continue
            if key in values:
                if '\n' in parser[sections[0]].get(key, ''):
                    raise ValueError('Managed configuration entries must use a single line: ' + key)
                found.add(key)
                if match.group(2) != values[key]:
                    line = key + ' = ' + values[key] + '\n'
        result.append(line)
    if inside:
        missing()
    return ''.join(result)


def parsed_config(path):
    parser = configparser.ConfigParser(interpolation=None, delimiters=('=',), strict=True)
    parser.read(path, encoding='utf-8-sig')
    sections = [section for section in parser.sections() if section.lower() == 'config']
    if len(sections) != 1 or parser.defaults():
        raise ValueError('Expected one [config] section and no DEFAULT settings: ' + str(path))
    return parser[sections[0]]


def print_host_preflight(version, image, rom, config):
    values = parsed_config(config)
    digest = rom_hash(rom)
    print('----------------------------------------------', flush=True)
    print('AmiWind v' + version + ' host preflight', flush=True)
    print('----------------------------------------------', flush=True)
    failed = False
    for label, key, display in PROFILE_LABELS:
        actual = values.get(key, '')
        expected = PROFILE_VALUES[key]
        ok = actual.strip().casefold() == expected.casefold()
        failed = failed or not ok
        shown = display if ok else (actual or '<missing>')
        print(('%-21s %-23s %s' % (label + ':', shown, '[x] OK' if ok else '[!] FAIL')), flush=True)
    speed_ok = values.get('uae_cpu_speed', '').strip().casefold() == 'max'
    failed = failed or not speed_ok
    print(('%-21s %-23s %s' % ('Cycle-exact speed:', 'OFF (cpu_speed=max)' if speed_ok else 'possible / unknown',
                                      '[x] OK' if speed_ok else '[!] FAIL')), flush=True)
    rom_ok = digest == REFERENCE_ROM_SHA256
    print(('%-21s %-23s %s' % ('Kickstart:', '3.1 A1200 40.68' if rom_ok else 'unrecognized ROM',
                                      '[x] OK' if rom_ok else '[!] WARN')), flush=True)
    print('ROM SHA-256:          ' + digest, flush=True)
    print('HDF:                  ' + image.name, flush=True)
    print('----------------------------------------------', flush=True)
    if failed:
        raise ValueError('Generated FS-UAE configuration failed the AmiWind accelerated-profile self-check.')


def write_config(root, version, image, rom):
    path = root / ('AmiWind-v' + version + '-FS-UAE.fs-uae')
    if path.is_symlink():
        raise ValueError('Configuration is a symlink; preserved unchanged: ' + str(path))
    existed = path.exists()
    before = path.read_bytes() if existed else None
    if existed:
        original = before.decode('utf-8-sig')
    else:
        template = root / 'resources' / 'emulators' / path.name
        original = template.read_text(encoding='utf-8-sig') if template.is_file() else PRESET.format(
            version=version, rom=rom, image=image)
    output = configured_text(original, image, rom).encode('utf-8')
    # Keep byte-identical configuration files completely untouched on reruns.
    if before == output:
        print('Existing configuration matches.', flush=True)
        return path
    backup = write_preserving(path, output, root, before)
    print(('Updated' if existed else 'Created') + ' configuration: ' + path.name, flush=True)
    if backup:
        print('Previous configuration kept in resources/emulators/backups/.', flush=True)
    return path


def write_preserving(path, output, root, before):
    """Replace only the expected bytes, retaining an existing file as a backup."""
    if path.is_symlink():
        raise ValueError('Refusing to replace a configuration symlink: ' + str(path))
    existed = before is not None
    temporary = None
    backup = None
    try:
        with tempfile.NamedTemporaryFile(prefix='.amiwind-config-', suffix='.tmp', dir=root, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(output)
            stream.flush()
            os.fsync(stream.fileno())
        if existed:
            if path.read_bytes() != before:
                raise ValueError('Configuration changed while preparing it; retry the launcher.')
            folder = root / 'resources' / 'emulators' / 'backups'
            folder.mkdir(parents=True, exist_ok=True)
            number = 1
            while True:
                backup = folder / (path.name + '.%04d.bak' % number)
                try:
                    with backup.open('xb') as stream:
                        stream.write(before)
                        stream.flush()
                        os.fsync(stream.fileno())
                    break
                except FileExistsError:
                    number += 1
            os.chmod(temporary, path.stat().st_mode & 0o777)
        # Exclusive creation avoids overwriting a config that appeared mid-run.
        if not existed:
            # Exclusive file creation also works on filesystems without hard links.
            with path.open('xb') as stream:
                try:
                    stream.write(output)
                    stream.flush()
                    os.fsync(stream.fileno())
                except BaseException:
                    path.unlink()
                    raise
            temporary.unlink()
        else:
            os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return backup


def save_settings(root, settings):
    path = root / SETTINGS_NAME
    before = path.read_bytes() if path.exists() else None
    if before is not None and json.loads(before.decode('utf-8-sig')) == settings:
        return
    output = (json.dumps(settings, indent=2, ensure_ascii=False) + '\n').encode('utf-8')
    write_preserving(path, output, root, before)
    print('Saved launcher settings: ' + path.name, flush=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, help='Playable directory; defaults to the folder containing this script')
    parser.add_argument('--hdf', help='Select an HDF for this run, or use latest (the default)')
    parser.add_argument('--rom', help='Select and remember a ROM file (or search a ROM directory)')
    parser.add_argument('--fs-uae', metavar='EXECUTABLE', help='Select and remember FS-UAE executable (default: fs-uae on PATH)')
    parser.add_argument('-y', '--yes', action='store_true', help='Run the newest image without the selection prompt')
    parser.add_argument('--configure-only', action='store_true', help='Validate files and create/reuse the preset without launching')
    args = parser.parse_args(argv)
    try:
        root = local_path(args.directory or Path(__file__).resolve().parent, Path.cwd())
        if not root.is_dir():
            raise ValueError('Playable directory not found: ' + str(root))
        settings = read_settings(root)
        requested = args.hdf or settings['hdf']
        interactive = not args.yes and not args.configure_only
        selected = select_image(root, None if requested == 'latest' else requested,
                                ask=settings['confirm_launch'] and interactive)
        if selected is None:
            print('Cancelled. No files changed.', flush=True)
            return 0
        image, version = selected
        rom_location = args.rom or settings['kickstart_rom'] or None
        while True:
            try:
                rom = select_rom(root, rom_location)
                break
            except (ValueError, OSError) as error:
                if not interactive:
                    raise
                print(str(error), flush=True)
                try:
                    rom_location = input('Kickstart ROM file or directory (Enter to cancel): ').strip()
                except EOFError:
                    rom_location = ''
                if not rom_location:
                    print('Cancelled. No files changed.', flush=True)
                    return 0
                if len(rom_location) >= 2 and rom_location[0] == rom_location[-1] and rom_location[0] in '\"\'':
                    rom_location = rom_location[1:-1]
        command = args.fs_uae or settings['fs_uae']
        if '/' in command or '\\' in command:
            command = str(local_path(command, root))
        executable = shutil.which(command)
        if not args.configure_only and executable is None:
            raise ValueError('FS-UAE was not found. Install fs-uae or select it with --fs-uae /path/to/fs-uae. No configuration was changed.')
        config = write_config(root, version, image, rom)
        settings['kickstart_rom'] = portable_path(rom, root)
        if args.fs_uae:
            if Path(command).is_absolute():
                remembered = portable_path(Path(command), root)
                settings['fs_uae'] = remembered if Path(remembered).is_absolute() else './' + remembered
            else:
                settings['fs_uae'] = command
        save_settings(root, settings)
        print_host_preflight(version, image, rom, config)
        print('AmiWind v' + version + '\nHDF: ' + str(image) + '\nROM: ' + str(rom), flush=True)
        if args.configure_only:
            print('Files matched. Configuration ready.', flush=True)
            return 0
        print("Files matched. We're off to Morrowind!", flush=True)
        return subprocess.run([executable, str(config)], cwd=root, check=False).returncode
    except (OSError, ValueError, UnicodeError) as error:
        print('AmiWind launcher: ' + str(error), file=sys.stderr, flush=True)
        return 1
    except KeyboardInterrupt:
        return 130


if __name__ == '__main__':
    sys.exit(main())
