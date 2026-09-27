#!/usr/bin/env python3
"""Reject desktop-library dependencies in the standalone Amiga executable."""
import argparse
from pathlib import Path

FORBIDDEN_LIBRARIES = (b'icon.library', b'workbench.library')

def check_binary(data):
    if data[:4] != bytes.fromhex('000003f3'):
        raise ValueError('Expected an Amiga Hunk executable')
    lower = data.lower()
    found = [name.decode('ascii') for name in FORBIDDEN_LIBRARIES if name in lower]
    if found:
        raise ValueError('Unwanted desktop library dependency: ' + ', '.join(found))
    return {'desktop_library_check': 'passed', 'bytes': len(data)}

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('binary', type=Path)
    args = parser.parse_args()
    try:
        print(check_binary(args.binary.read_bytes()))
    except (OSError, ValueError) as exc:
        parser.exit(1, str(exc) + '\n')
