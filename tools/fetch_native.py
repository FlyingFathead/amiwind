#!/usr/bin/env python3
"""Fetch public, pinned map tools or build the reference QuakeC compiler."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import shlex
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from mwad.paths import ensure_external
from mwad.progress import Progress

ERICW = {
    'release': 'v0.18.1',
    'url': 'https://github.com/ericwa/ericw-tools/releases/download/v0.18.1/ericw-tools-v0.18.1-Linux.zip',
    'bytes': 14594502,
    'sha256': '986531ff66d692fa732b7f75a6c871dcbd152b98721d1c2475b76d3367f040e2',
    'directory': 'ericw-tools-v0.18.1-Linux',
}
QCC_COMMIT = 'c0d1b91c74eb654365ac7755bc837e497caaca73'
QCC_URL = 'https://api.github.com/repos/id-Software/Quake-Tools/tarball/' + QCC_COMMIT
# Source hashes from the reference revision, independent of gzip repackaging.
QCC_FILES = {
    'COPYING': (17992, '32b1062f7da84967e7019d01ab805935caa7ab7321a7ced0e30ebe75e5df1670'),
    'cmdlib.c': (9086, '453c7420942ee875405484a481a0bad4b050f6d61207e14aed76553566f709bb'),
    'cmdlib.h': (2524, '200f170215e2bddb66cb2cbe5e39720a06cdeaaf9eadadbc86cec5901f1a632d'),
    'pr_comp.c': (22559, '2daa81bbb038383219a9b0aa0011b00c083fa70410602a775ccd44d70e524d79'),
    'pr_comp.h': (3146, '5bb00ba926012e83e53a8c7e107a91aace3b7b39815d7deab21dc42a91b980f8'),
    'pr_lex.c': (12720, '8bfcf395bc027918a8c421370318d99e8611c7a531503df95b7d068afc5db987'),
    'progdefs.h': (3263, '112dd897987d265980a564a9e4773de33b0cc4a96d85658ed3a495ff891f3932'),
    'qcc.c': (24396, '75274defe1a5012b6b86d3d8a3dee933beba070382d992362ec2ab4293f0612c'),
    'qcc.h': (13885, '4764368c9d4c0bfaa152772508c919893af7215a35adbcdddcad1c678638a836'),
}


def download(url, path, limit):
    request = urllib.request.Request(url, headers={'User-Agent': 'AmiWind-build'})
    size = 0
    with Progress('Downloading ' + url, interval=5) as progress:
        with urllib.request.urlopen(request, timeout=60) as source, path.open('wb') as target:
            for block in iter(lambda: source.read(1024 * 1024), b''):
                size += len(block)
                if size > limit:
                    raise ValueError('Download exceeds expected size limit')
                target.write(block)
                progress.bytes(size, ERICW['bytes'] if url == ERICW['url'] else None)


def _fetch(component, destination):
    destination = ensure_external(destination, component + ' tools directory')
    if destination.exists() or destination.is_symlink():
        raise ValueError(f'Destination exists and will not be overwritten: {destination}')
    if component == 'ericw' and (sys.platform != 'linux' or platform.machine().lower() not in ('x86_64', 'amd64')):
        raise ValueError('The pinned ericw-tools binary is for Linux x86_64, including x86_64 WSL')
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='amiwind-' + component + '-', dir=destination.parent) as temp:
        work = Path(temp); archive = work/'download'; staged = work/'ready'; staged.mkdir()
        print('Source URL: ' + (ERICW['url'] if component == 'ericw' else QCC_URL), flush=True)
        print(f'Temporary archive: {archive}\nInstall destination: {destination}', flush=True)
        if component == 'ericw':
            print(f"Expected: {ERICW['bytes']:,} bytes; SHA-256 {ERICW['sha256']}", flush=True)
        else:
            print(f'Expected QuakeC revision: {QCC_COMMIT}; {len(QCC_FILES)} source files checked by size/SHA-256.', flush=True)
        if component == 'ericw':
            download(ERICW['url'], archive, ERICW['bytes'])
            if archive.stat().st_size != ERICW['bytes'] or hashlib.sha256(archive.read_bytes()).hexdigest() != ERICW['sha256']:
                raise ValueError('ericw-tools download does not match pinned size/SHA-256')
            print('ericw-tools size and SHA-256 verified.', flush=True)
            with Progress('Extracting ericw-tools'), zipfile.ZipFile(archive) as bundle:
                for item in bundle.infolist():
                    parts = PurePosixPath(item.filename).parts
                    mode = item.external_attr >> 16
                    if not parts or parts[0] != ERICW['directory'] or '..' in parts or '\\' in item.filename or stat.S_ISLNK(mode):
                        raise ValueError('Unsafe path in ericw-tools archive')
                    target = staged.joinpath(*parts[1:])
                    if item.is_dir():
                        target.mkdir(parents=True, exist_ok=True)
                    else:
                        target.parent.mkdir(parents=True, exist_ok=True)
                        with bundle.open(item) as source, target.open('xb') as output:
                            shutil.copyfileobj(source, output)
                        target.chmod(0o755 if mode & 0o111 else 0o644)
            for name in ('qbsp', 'vis', 'light'):
                if not os.access(staged/'bin'/name, os.X_OK):
                    raise ValueError('ericw-tools missing executable ' + name)
            receipt = ERICW
        elif component == 'qcc':
            download(QCC_URL, archive, 4 * 1024 * 1024)
            qc = staged/'qcc'; qc.mkdir()
            seen = set()
            with Progress('Extracting and verifying pinned QuakeC source'), tarfile.open(archive) as bundle:
                for item in bundle:
                    parts = PurePosixPath(item.name).parts
                    if len(parts) != 3 or parts[1] != 'qcc' or parts[2] not in QCC_FILES:
                        continue
                    name = parts[2]; size, digest = QCC_FILES[name]
                    if name in seen or not item.isfile() or item.size != size:
                        raise ValueError('Invalid qcc source entry: ' + name)
                    source = bundle.extractfile(item)
                    raw = source.read(size + 1)
                    if len(raw) != size or hashlib.sha256(raw).hexdigest() != digest:
                        raise ValueError('qcc source SHA-256 mismatch: ' + name)
                    (qc/name).write_bytes(raw); seen.add(name)
            if seen != QCC_FILES.keys():
                raise ValueError('Missing pinned qcc source files')
            command = ['cc', '-std=gnu89', '-include', 'unistd.h', '-O2', '-fcommon', '-o', '../qcc-host',
                       'qcc.c', 'pr_comp.c', 'pr_lex.c', 'cmdlib.c']
            with Progress('Compiling reference QuakeC compiler'):
                subprocess.run(command, cwd=qc, check=True)
            from build_aga import check_quakec
            with Progress('Testing QuakeC compiler with AmiWind sources'):
                check_quakec(staged/'qcc-host')
            receipt = {'commit': QCC_COMMIT, 'url': QCC_URL, 'source_sha256': QCC_FILES,
                       'build_command': command, 'binary_sha256': hashlib.sha256((staged/'qcc-host').read_bytes()).hexdigest()}
        else:
            raise ValueError('Unknown native tool component: ' + component)
        (staged/'amiwind-download.json').write_text(json.dumps(receipt, indent=2) + '\n')
        staged.rename(destination)
    print(f'{component} ready: {destination}')


def manual_help(component, destination):
    print(f'Manual {component} setup:', file=sys.stderr)
    if component == 'ericw':
        print('  Release page: https://github.com/ericwa/ericw-tools/releases/tag/v0.18.1', file=sys.stderr)
        print('  Download: ' + ERICW['url'], file=sys.stderr)
        print(f"  Required size: {ERICW['bytes']} bytes; SHA-256: {ERICW['sha256']}", file=sys.stderr)
        print('  Verify the ZIP and extract the complete folder, including its shared libraries.', file=sys.stderr)
        print('  Continue with ./build.sh --autoinstall --quake-tools /absolute/path/to/ericw-tools-v0.18.1-Linux/bin', file=sys.stderr)
    else:
        print('  Source page: https://github.com/id-Software/Quake-Tools/tree/' + QCC_COMMIT, file=sys.stderr)
        print('  Source archive: ' + QCC_URL, file=sys.stderr)
        print('  Or obtain the source and build it with:', file=sys.stderr)
        print('    ' + shlex.join(['git', 'clone', 'https://github.com/id-Software/Quake-Tools.git', str(destination)]), file=sys.stderr)
        print('    ' + shlex.join(['git', '-C', str(destination), 'checkout', '--detach', QCC_COMMIT]), file=sys.stderr)
        print('    cd ' + shlex.quote(str(Path(destination)/'qcc')), file=sys.stderr)
        print('    cc -std=gnu89 -include unistd.h -O2 -fcommon -o ../qcc-host qcc.c pr_comp.c pr_lex.c cmdlib.c', file=sys.stderr)
        print('  From the AmiWind checkout, continue with ./build.sh --autoinstall --qcc ' + shlex.quote(str(Path(destination)/'qcc-host')), file=sys.stderr)
    print('  Existing tool directories are never overwritten.', file=sys.stderr)


def fetch(component, destination):
    try:
        return _fetch(component, destination)
    except (OSError, ValueError, subprocess.SubprocessError, tarfile.TarError, zipfile.BadZipFile):
        manual_help(component, destination)
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('component', choices=('ericw', 'qcc'))
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    try:
        fetch(args.component, args.out)
    except (KeyboardInterrupt, EOFError):
        parser.exit(130, '\nCancelled.\n')
    except (OSError, ValueError, subprocess.SubprocessError, tarfile.TarError, zipfile.BadZipFile) as exc:
        parser.exit(1, f'{exc}\n')
