#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Fail when engine code can reach a 68040-unimplemented FPU instruction.

The 68040 executes only part of the 68881/68882 instruction set; the rest
(FSIN, FCOS, FSINCOS, FINT, FINTRZ, FMOVECR, FETOX, ... and every packed
decimal operand) take an F-line trap into an FPU support library, or crash a
machine without one (ENGINE-FPU-UNIMPL-31, ENGINE-FPSP-MISSING-31). The C
library the engine links contains such instructions, and the compiler can
route ordinary calls into them (a sin+cos pair becomes cexp).

Input: the linked engine and its linker map (the build writes
build/AmiQuakeGCC.map). The disassembly gives every instruction and every
reference to a function: a call, or the function address loaded into a
register for a later "jsr (aN)" (GCC does that for repeated calls), i.e. any
PC-relative operand, or absolute operand relocated against .text (objdump
-r; data and bss addresses overlap code addresses), equal to a function start; the map gives function start addresses
and the input object of each (static functions count as part of the
preceding global in the same object). A function is "bad" if it contains an
unimplemented instruction or references a bad function. Edges listed in the allowlist
(tools/fpu-unimplemented-allowlist.json: library function, the callers
allowed to use it, and why) are cut. The check fails if any engine function
(an input object outside the libraries) is bad, and names one call path.

Usage:
  check_fpu_unimplemented.py --binary B --map M [--objdump PATH] [--allowlist J] [--report OUT.json]
  check_fpu_unimplemented.py --disassembly D --map M ...   (pre-made objdump -d -r output)
"""
import argparse
import json
import re
import subprocess
import sys
from collections import deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALLOWLIST = ROOT / 'tools' / 'fpu-unimplemented-allowlist.json'
# 68040 User's Manual, "Unimplemented floating-point instructions": emulated
# by the FPSP. Plus packed decimal operands (size .p) on any instruction.
UNIMPLEMENTED = frozenset('''facos fasin fatan fatanh fcos fcosh fetox fetoxm1 fgetexp fgetman
    fint fintrz flog10 flog2 flogn flognp1 fmod frem fscale fsin fsincos fsinh ftan ftanh
    ftentox ftwotox fmovecr'''.split())
IMPLEMENTED = frozenset('''fabs fadd fsadd fdadd fbeq fbne fbgt fbge fblt fble fbgl fbgle fbngle fbngl
    fbnle fbnlt fbnge fbngt fbsf fbst fbseq fbsne fbogt fboge fbolt fbole fbogl fbor fbun fbueq
    fbugt fbuge fbult fbule fbf fbt fcmp fdbcc fdiv fsdiv fddiv fmove fsmove fdmove fmovem fmul
    fsmul fdmul fneg fsneg fdneg fnop frestore fsave fscc fsgldiv fsglmul fsqrt fssqrt fdsqrt fsub
    fssub fdsub ftrapcc ftst fabs fsabs fdabs'''.split())
INSTRUCTION = re.compile(r'^\s*([0-9a-f]+):\s+(?:[0-9a-f]{4} )+\s*(\S+)\s*(.*)$')
ABSOLUTE = re.compile(r'(?<![#\w@(])0x([0-9a-f]+)|(?:^|\s)([0-9a-f]{3,8})(?= <)')
PCREL = re.compile(r'%pc@\(0x([0-9a-f]+)\)')
RELOC = re.compile(r'^\s*[0-9a-f]+:\s+RELOC\S*\s+(\S+)')
MAP_SYMBOL = re.compile(r'^\s+0x([0-9a-f]+)\s+([A-Za-z_.$][\w.$]*)\s*$')
MAP_SECTION = re.compile(r'^ \.text\s+0x([0-9a-f]+)\s+0x([0-9a-f]+)\s+(\S+)')


def unimplemented(mnemonic):
    """True for a 68040-unimplemented FPU mnemonic (objdump spelling, size suffix optional)."""
    m = mnemonic.lower()
    if not m.startswith('f'):
        return False
    if m in UNIMPLEMENTED:
        return True
    base, size = m[:-1], m[-1:]
    if size in 'bwlsdxp' and (base in UNIMPLEMENTED or base in IMPLEMENTED):
        return base in UNIMPLEMENTED or size == 'p'
    return False


def read_map(text):
    """[(start, name, object)] for every .text section and global in it, sorted."""
    sections, symbols = [], []
    current = None
    for line in text.splitlines():
        m = MAP_SECTION.match(line)
        if m:
            start, size = int(m.group(1), 16), int(m.group(2), 16)
            current = (start, start + size, m.group(3))
            if size:
                sections.append(current)
            continue
        if line.startswith(' .') or line.startswith('.'):
            current = None
            continue
        m = MAP_SYMBOL.match(line)
        if m and current and current[0] <= int(m.group(1), 16) < current[1]:
            symbols.append((int(m.group(1), 16), m.group(2), current[2]))
    functions = []
    for start, end, obj in sections:
        inside = sorted(s for s in symbols if start <= s[0] < end)
        if not inside or inside[0][0] != start:
            inside.insert(0, (start, '%s@%x' % (Path(obj).name, start), obj))
        functions.extend(inside)
    functions.sort()
    return functions


def is_library(obj):
    return '.a(' in obj or obj.endswith('.a') or '/lib/' in obj or obj.endswith('crt0.o')


def analyse(disassembly, functions):
    starts = [f[0] for f in functions]
    by_start = {f[0]: f[1] for f in functions}

    def owner(address):
        lo, hi = 0, len(starts) - 1
        if not starts or address < starts[0]:
            return None
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if starts[mid] <= address:
                lo = mid
            else:
                hi = mid - 1
        return functions[lo][1]

    sites, calls = {}, {}
    pending = None      # (function, absolute operands) waiting for their RELOC lines

    def refer(function, address):
        target = by_start.get(address)
        if target and target != function:
            calls.setdefault(function, set()).add(target)

    for line in disassembly.splitlines():
        r = RELOC.match(line)
        if r:
            # objdump -r: an absolute operand is a code address only when it
            # is relocated against .text (data and bss addresses overlap).
            if pending and r.group(1) == '.text':
                for address in pending[1]:
                    refer(pending[0], address)
                pending = None
            continue
        m = INSTRUCTION.match(line)
        if not m:
            continue
        pending = None
        address, mnemonic, operands = int(m.group(1), 16), m.group(2), m.group(3)
        function = owner(address)
        if function is None:
            continue
        if unimplemented(mnemonic):
            sites.setdefault(function, []).append('%x %s %s' % (address, mnemonic, operands.strip()))
        for value in PCREL.findall(operands):
            refer(function, int(value, 16))
        absolute = [int(a or b, 16) for a, b in ABSOLUTE.findall(PCREL.sub('', operands))]
        if absolute:
            pending = (function, absolute)
    return sites, calls


def check(disassembly, map_text, allowlist):
    functions = read_map(map_text)
    objects = {name: obj for _, name, obj in functions}
    sites, calls = analyse(disassembly, functions)
    allowed = {}
    for row in allowlist.get('allowed', []):
        allowed[row['function']] = set(row['callers']) if row['callers'] != '*' else '*'
    cut = lambda caller, callee: callee in allowed and (allowed[callee] == '*' or caller in allowed[callee])
    callers = {}
    for caller, targets in calls.items():
        for callee in targets:
            if not cut(caller, callee):
                callers.setdefault(callee, set()).add(caller)
    # Reverse breadth-first search from every function with an unimplemented
    # instruction; next[] remembers one step of a path towards it.
    nxt, queue = {}, deque()
    for function in sites:
        nxt[function] = None
        queue.append(function)
    while queue:
        callee = queue.popleft()
        for caller in callers.get(callee, ()):
            if caller not in nxt:
                nxt[caller] = callee
                queue.append(caller)

    def path(function):
        out = [function]
        while nxt[out[-1]] is not None:
            out.append(nxt[out[-1]])
        return out

    failures = [dict(function=f, object=objects.get(f, '?'), path=path(f),
                     instructions=sites.get(path(f)[-1], [])[:3])
                for f in sorted(nxt) if not is_library(objects.get(f, ''))]
    used = {callee for caller, targets in calls.items() for callee in targets if cut(caller, callee)}
    unused = sorted(set(allowed) - used)
    total = sum(len(v) for v in sites.values())
    return dict(passed=not failures, unimplemented_instructions=total,
                functions_with_unimplemented={f: dict(object=objects.get(f, '?'), count=len(v))
                                              for f, v in sorted(sites.items())},
                engine_failures=failures, allowlist_unused=unused)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument('--binary', type=Path)
    src.add_argument('--disassembly', type=Path)
    p.add_argument('--map', type=Path, required=True)
    p.add_argument('--objdump', default='m68k-amigaos-objdump')
    p.add_argument('--allowlist', type=Path, default=ALLOWLIST)
    p.add_argument('--report', type=Path)
    args = p.parse_args(argv)
    if args.binary:
        disassembly = subprocess.run([args.objdump, '-d', '-r', '-m', 'm68k:68040', str(args.binary)],
                                     check=True, capture_output=True, text=True).stdout
    else:
        disassembly = args.disassembly.read_text(encoding='utf-8', errors='replace')
    allowlist = json.loads(args.allowlist.read_text(encoding='utf-8'))
    result = check(disassembly, args.map.read_text(encoding='utf-8', errors='replace'), allowlist)
    if args.report:
        args.report.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8', newline='\n')
    print('68040-unimplemented FPU instructions in the binary: %d in %d functions'
          % (result['unimplemented_instructions'], len(result['functions_with_unimplemented'])))
    for name, row in result['functions_with_unimplemented'].items():
        print('  %-28s %3d  %s' % (name, row['count'], Path(row['object']).name))
    for name in result['allowlist_unused']:
        print('allowlist entry not used by this build: ' + name)
    for row in result['engine_failures']:
        print('FAIL engine function %s (%s) reaches %s: %s'
              % (row['function'], Path(row['object']).name, ' -> '.join(row['path']), '; '.join(row['instructions'])))
    if not result['passed']:
        print('Engine code reaches 68040-unimplemented FPU instructions (see ENGINE-FPU-UNIMPL-31).')
        return 1
    print('No engine function reaches a 68040-unimplemented FPU instruction outside the allowlist.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
