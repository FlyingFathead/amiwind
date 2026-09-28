#!/usr/bin/env python3
"""Launch an owned local HDF with the documented FS-UAE playtest preset."""
import argparse
import hashlib
from pathlib import Path
import os
import shlex
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from mwad.paths import ensure_external
from mwad.progress import section
from project_version import VERSION

FS_UAE_URL = 'https://fs-uae.net/'
REFERENCE_ROM_SHA256 = '6d43840d4099a74170ea0f0425b6257c3891ebcaa39c4d1840075a9ab22b5707'


def local_path(value, label):
    path = ensure_external(value, label)
    if any(character in str(path) for character in '\r\n'):
        raise ValueError(f'{label} path must not contain a newline')
    return path


def rom_sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def select_rom(path):
    """Accept a file, or search one directory for the known ROM's exact bytes."""
    if path.is_file() and path.stat().st_size:
        return path
    if not path.is_dir():
        return None
    print(f'Looking for the reference Kickstart 3.1 A1200 ROM in: {path}', flush=True)
    print('Checking files directly in this directory; subdirectories are not searched.', flush=True)
    matches = []
    # The recorded A1200 ROM is exactly 512 KiB. Check by size and checksum,
    # not filename, so renamed ROM dumps are recognized without hashing huge files.
    for candidate in sorted(path.iterdir()):
        if candidate.is_symlink() or not candidate.is_file():
            continue
        try:
            if candidate.stat().st_size == 512 * 1024:
                print(f'Checking ROM checksum: {candidate.name}', flush=True)
                if rom_sha256(candidate) == REFERENCE_ROM_SHA256:
                    matches.append(candidate)
        except OSError as exc:
            print(f'[warning] Cannot read {candidate.name}: {exc}', flush=True)
    if matches:
        if len(matches)>1:
            print(f'Found {len(matches)} byte-identical reference copies; using {matches[0].name}.', flush=True)
        return local_path(matches[0], 'Kickstart ROM')
    print('No reference checksum matched here. Select a ROM file explicitly or another directory.', flush=True)
    return None


def prepare_launch(kickstart=None, *, interactive=False):
    """Read-only checks, performed before dependency setup or conversion."""
    section('FS-UAE autorun preflight')
    executable = shutil.which('fs-uae')
    if executable is None:
        raise ValueError('--autorun-fs-uae requires fs-uae on PATH. '
                         f'Install it from {FS_UAE_URL} or omit --autorun-fs-uae to build only. '
                         'No dependency setup or conversion has started.')
    executable = str(Path(executable).resolve())
    print(f'FS-UAE: {executable}', flush=True)
    location = local_path(kickstart if kickstart is not None else
                     Path.home() / '.roms/kickstart-3.1-a1200.rom', 'Kickstart ROM')
    if kickstart is None and not location.is_file() and location.parent.is_dir():
        location = location.parent
    rom = select_rom(location)
    while rom is None:
        guidance = (f'No Kickstart ROM selected from: {location}. '
                    'Supply your own Kickstart 3.1 A1200 ROM file or directory with --kickstart-file PATH. '
                    'ROMs are never downloaded or bundled. Licensed ROM information: '
                    'https://www.amigaforever.com/')
        if not interactive:
            raise ValueError(guidance)
        print(guidance, flush=True)
        answer = input('Directory or file containing your Kickstart 3.1 A1200 ROM (Enter to cancel): ').strip()
        if not answer:
            raise ValueError('No ROM selected; supply --kickstart-file PATH or omit --autorun-fs-uae to build only')
        if len(answer) >= 2 and answer[0] == answer[-1] and answer[0] in '\"\'':
            answer = answer[1:-1]
        location = local_path(answer, 'Kickstart ROM')
        rom = select_rom(location)
    digest = rom_sha256(rom)
    print(f'Kickstart ROM: {rom}\nSHA-256: {digest}', flush=True)
    if digest == REFERENCE_ROM_SHA256:
        print('[ok] SHA-256 matches the owner-tested Kickstart 3.1 A1200 ROM.', flush=True)
    else:
        print('[warning] ROM checksum differs from the owner-tested Kickstart 3.1 A1200 ROM. '
              'Continuing with your supplied file; compatibility is unverified.', flush=True)
    # Validate the same preset that the launcher will use, without writing files.
    configuration(Path('/placeholder/AmiWind.hdf'), rom)
    print('Preset: docs/FS-UAE-PLAYTESTING.md; A1200/AGA, 68040/FPU, JIT, '
          '2 MiB Chip + 16 MiB Zorro III RAM.', flush=True)
    return executable, rom


def configuration(image, rom):
    preset = ROOT / 'resources/emulators' / f'AmiWind-v{VERSION}-FS-UAE.fs-uae'
    text = preset.read_text(encoding='utf-8')
    for key, value in (('kickstart_file', rom), ('hard_drive_0', image)):
        lines = text.splitlines()
        matches = [i for i, line in enumerate(lines) if line.startswith(key + ' = ')]
        if len(matches) != 1:
            raise ValueError(f'Expected exactly one {key} entry in {preset}')
        lines[matches[0]] = f'{key} = {value}'
        text = '\n'.join(lines) + '\n'
    return text.replace('# Replace ROM and HDF placeholders with your owned local files.',
                        '# Local paths filled by the launcher; ROM and HDF are not bundled.')


def launch(image, executable, rom):
    image = local_path(image, 'HDF')
    rom = local_path(rom, 'Kickstart ROM')
    if not image.is_file() or image.stat().st_size == 0:
        raise ValueError(f'HDF missing or empty: {image}')
    config = image.with_suffix('.fs-uae')
    content = configuration(image, rom)
    if config.is_symlink():
        raise ValueError(f'Will not write through a configuration symlink: {config}')
    if config.exists():
        if config.read_text(encoding='utf-8') != content:
            raise ValueError(f'Existing configuration differs; preserved unchanged: {config}')
    else:
        with config.open('x', encoding='utf-8', newline='\n') as stream:
            stream.write(content)
    section('Launch AmiWind in FS-UAE')
    print(f'HDF: {image}\nConfiguration: {config}', flush=True)
    command = [executable, str(config)]
    print('Command: ' + shlex.join(command), flush=True)
    if not Path(executable).is_file() or not os.access(executable, os.X_OK):
        print(f'[warning] FS-UAE is no longer executable; launch skipped. Install: {FS_UAE_URL}', flush=True)
        return 1
    print('FS-UAE output follows. Close the emulator to return to the shell.', flush=True)
    try:
        result = subprocess.run(command, check=False)
    except OSError as exc:
        print(f'[warning] Could not start FS-UAE: {exc}', flush=True)
        return 1
    if result.returncode:
        print(f'[warning] FS-UAE exited with status {result.returncode}. HDF retained: {image}', flush=True)
    else:
        print('FS-UAE closed.', flush=True)
    return 0 if result.returncode == 0 else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', type=Path, required=True, help='Existing HDF; no rebuild')
    parser.add_argument('--kickstart-file', '--kickstart', dest='kickstart_file', type=Path,
                        help='Owned ROM file or directory to scan for the reference checksum (default: ~/.roms/; asks if missing interactively)')
    args = parser.parse_args(argv)
    try:
        executable, rom = prepare_launch(args.kickstart_file, interactive=sys.stdin.isatty())
        return launch(args.image, executable, rom)
    except (KeyboardInterrupt, EOFError):
        parser.exit(130, '\nFS-UAE launch interrupted; HDF retained.\n')
    except (OSError, ValueError) as exc:
        parser.exit(1, f'Error: {exc}\n')


if __name__ == '__main__':
    raise SystemExit(main())
