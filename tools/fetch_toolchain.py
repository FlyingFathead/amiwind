#!/usr/bin/env python3
"""Fetch the pinned public Linux SDK into a new external directory."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import shlex
import sys
import tarfile
import tempfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from mwad.paths import ensure_external
from mwad.progress import Progress

SPEC = {
    'release': 'v16.2-rc11',
    'url': 'https://github.com/AmigaPorts/m68k-amigaos-gcc/releases/download/v16.2-rc11/m68k-amigaos-gcc-16.2-rc11-x86_64-linux.tar.xz',
    'sha256': '96409aa7dd91a4cd1d8c5dadf12ceccebc505fc82a1dff42a05dfec061527cd1',
    'bytes': 63450712,
    'directory': 'm68k-amigaos-gcc-16.2',
}


def _fetch(destination):
    destination = ensure_external(destination, 'SDK download directory')
    if sys.platform != 'linux' or platform.machine().lower() not in ('x86_64', 'amd64'):
        raise ValueError('This pinned SDK download is for Linux x86_64, including x86_64 WSL')
    if not hasattr(tarfile, 'data_filter'):
        raise ValueError('SDK extraction requires a Python with tarfile.data_filter (use Python 3.12+)')
    if destination.exists():
        raise ValueError('SDK destination already exists; reuse it with --sdk or choose a new location')
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='amiwind-sdk-', dir=destination.parent) as temp:
        archive = Path(temp) / 'sdk.tar.xz'
        print('Source URL: ' + SPEC['url'], flush=True)
        print(f'Temporary archive: {archive}\nInstall destination: {destination}', flush=True)
        print(f"Expected: {SPEC['bytes']:,} bytes; SHA-256 {SPEC['sha256']}", flush=True)
        h = hashlib.sha256()
        size = 0
        with Progress('Downloading Amiga SDK', interval=5) as progress:
            with urllib.request.urlopen(SPEC['url'], timeout=60) as stream, archive.open('wb') as output:
                for block in iter(lambda: stream.read(1024*1024), b''):
                    size += len(block)
                    if size > SPEC['bytes']:
                        raise ValueError('SDK download exceeds pinned size')
                    h.update(block)
                    output.write(block)
                    progress.bytes(size, SPEC['bytes'])
        if size != SPEC['bytes'] or h.hexdigest() != SPEC['sha256']:
            raise ValueError('SDK archive does not match the pinned size/SHA-256')
        print('SDK size and SHA-256 verified.', flush=True)
        extracted = Path(temp) / 'extracted'
        extracted.mkdir()
        with Progress('Extracting SDK'), tarfile.open(archive) as bundle:
            bundle.extractall(extracted, filter='data')
        sdk = extracted / SPEC['directory']
        for name in ('bin/m68k-amigaos-gcc', 'bin/vasmm68k_mot', 'm68k-amigaos/ndk-include/exec/exec_lib.i'):
            if not (sdk / name).is_file():
                raise ValueError('SDK missing ' + name)
        sdk.rename(destination)
    (destination / 'amiwind-download.json').write_text(json.dumps(SPEC, indent=2) + '\n')
    print(destination)


def manual_help(destination):
    print('Manual SDK setup:', file=sys.stderr)
    print('  Releases: https://github.com/AmigaPorts/m68k-amigaos-gcc/releases/tag/' + SPEC['release'], file=sys.stderr)
    print('  Download: ' + SPEC['url'], file=sys.stderr)
    print(f"  Required size: {SPEC['bytes']} bytes; SHA-256: {SPEC['sha256']}", file=sys.stderr)
    print(f"  Verify the archive, extract it, then select the {SPEC['directory']} folder containing bin/ and m68k-amigaos/.", file=sys.stderr)
    print('  Continue with ./build.sh --autoinstall --sdk /absolute/path/to/' + SPEC['directory'], file=sys.stderr)
    print('  Automatic destination (not overwritten): ' + shlex.quote(str(destination)), file=sys.stderr)


def fetch(destination):
    try:
        return _fetch(destination)
    except (OSError, ValueError, tarfile.TarError):
        manual_help(destination)
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    try:
        fetch(parser.parse_args().out)
    except (KeyboardInterrupt, EOFError):
        parser.exit(130, '\nCancelled.\n')
    except (OSError, ValueError, tarfile.TarError) as exc:
        parser.exit(1, str(exc) + '\n')
