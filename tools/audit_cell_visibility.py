#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Write a private source-script visibility audit from an owner-supplied master."""
import argparse
import json
import math
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from mwad.script_visibility import audit_cell


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('master', type=Path)
    p.add_argument('--cell', nargs=2, type=int, required=True)
    p.add_argument('--state', action='append', default=[], metavar='GLOBAL=VALUE')
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    state = {}
    for entry in a.state:
        name, sep, value = entry.partition('=')
        if not sep or not name or name.casefold() in state:
            p.error('Each state must be a unique GLOBAL=VALUE')
        try:
            state[name.casefold()] = float(value)
        except ValueError:
            p.error('State value must be numeric')
        if not math.isfinite(state[name.casefold()]):
            p.error('State value must be finite')
    report = audit_cell(a.master.read_bytes(), a.cell, state)
    serialized = json.dumps(report, indent=2, allow_nan=False) + '\n'
    with a.out.open('x', encoding='utf-8', newline='\n') as out:
        out.write(serialized)
    print(json.dumps(report['counts']))


if __name__ == '__main__':
    main()
