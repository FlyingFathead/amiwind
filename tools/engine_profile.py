# SPDX-License-Identifier: GPL-3.0-only
"""Engine profiles: which code paths the AGA engine is compiled with (docs/ENGINE_PROFILES.md).

c         AmiWind's C paths at -O1 everywhere: the default and the regression reference build.
upstream  the optimisations of TerribleFire's AmiQuake GCC port (Stephen Leary), including
          NovaCoder's original routines: upstream's 68k assembly linked instead of the C paths that
          upstream runs it for (the turbulent water/lava span loop and the chunky-to-planar
          conversion; the no-FPU build also its fixed-point library), compiled at -O1 as upstream's
          Makefile does (its README's "-O2 for most code" describes an older state).

--engine-asm and --engine-opt override either half; any other mix is recorded as "custom".
--engine-cpu 68060 is the experimental 68060-targeted build (docs/68060.md): the same profile compiled
with GCC's 68060 instruction selection (-m68060 -mhard-float: no FScc, no 64-bit MULS.L/DIVS.L, FINTRZ
in hardware), linked with the 68040 build's hard-float libraries; the binary runs on a 68060 only (FINTRZ
traps on a 68040). Default 68040, the baseline, whose make command stays unchanged.
--engine-opt o2 is the separate selective -O2 experiment (everything at -O2 except mathlib.c and
in_amiga.c at -O1, as upstream's README describes and its Makefile did before it went back to -O1).
The assembly units (engine/aga/src, upstream revision 9c62d90):
  spans  d_scan_68k.s D_DrawSpans8; the engine draws world spans with D_DrawSpans16 unless
         d_subdiv16 is 0, so this routine only runs then. Not in the upstream profile: see
         UNIT_NOTES['spans'].
  turb   d_scan_68k.s D_DrawTurbulent8Span (water and lava).
  maths  mathlib_68k.s AngleVectors through mathieeedoubtrans.library; not linked by upstream's
         game build either (its tests and benchmarks use it), and 68040 only.
  c2p    c2p8.s, NovaCoder's chunky-to-planar routine (falls back to the C conversion for padded
         plane rows).
  fixed  fixedpoint_asm.s: the 68020 (no-FPU) build's span routines call it; nothing in the 68040
         build does, so it is not linked there.
"""
from __future__ import annotations

UNITS = ('spans', 'turb', 'maths', 'c2p', 'fixed')
PROFILES = ('c', 'upstream')
OPT_LEVELS = ('o1', 'o2')
ENGINE_CPUS = ('68040', '68060')

# What each profile selects before overrides.
PROFILE_ASM = {'c': (), 'upstream': ('turb', 'c2p', 'fixed')}
PROFILE_OPT = {'c': 'o1', 'upstream': 'o1'}

CREDIT = ("the optimisations of TerribleFire's AmiQuake GCC port (Stephen Leary), including "
          "NovaCoder's original routines")
UPSTREAM_REVISION = '9c62d905151614af3e788ae3145a0d4ecc8a7bb8'

# The assembly objects a unit links into the 68040 / 68020 builds (engine/aga/Makefile).
UNIT_OBJECTS = {
    'spans': {'68040': 'd_scan_68k.o', '68020': 'd_scan_68k_nofpu.o'},
    'turb': {'68040': 'd_scan_68k.o', '68020': 'd_scan_68k_nofpu.o'},
    'maths': {'68040': 'mathlib_68k.o'},
    'c2p': {'68040': 'c2p8.o', '68020': 'c2p8.o'},
    'fixed': {'68020': 'fixedpoint_asm.o'},
}

UNIT_NOTES = {
    'spans': ("upstream's D_DrawSpans8 walks a 12-byte span array ended by count -128, z-tests and skips "
              "texel 255: the layout and checks of Quake's sprite span loop (D_SpriteDrawSpans), not the "
              "linked 16-byte world span list D_DrawSpans8 receives. Reached only with d_subdiv16 0; "
              "kept selectable for A/B, not part of the upstream profile."),
    'maths': ("calls mathieeedoubtrans.library for sine and cosine instead of Q_SinCosDeg and skips the "
              "AngleVectors FPU counter; not linked by upstream's game build."),
    'fixed': 'only the 68020 (no-FPU) build calls it; not linked into the 68040 build.',
}


def parse_asm(text):
    """--engine-asm: a comma list of UNITS, 'none' or 'all'; None = the profile's set."""
    if text is None:
        return None
    words = [part.strip() for part in str(text).replace(' ', ',').split(',') if part.strip()]
    if words == ['none']:
        return ()
    if words == ['all']:
        return UNITS
    unknown = [word for word in words if word not in UNITS]
    if unknown or not words:
        raise ValueError('--engine-asm takes a comma list of %s, or none, or all (not %r)'
                         % (', '.join(UNITS), text))
    return tuple(unit for unit in UNITS if unit in words)


def parse_opt(text):
    """--engine-opt: o1, o2 (the selective -O2 experiment) or 'upstream' (= o1, what upstream's Makefile
    builds with); None = the profile's level."""
    if text is None:
        return None
    value = {'upstream': 'o1'}.get(str(text), str(text))
    if value not in OPT_LEVELS:
        raise ValueError('--engine-opt takes o1, o2 or upstream (not %r)' % (text,))
    return value


def resolve(profile='c', asm=None, opt=None, cpu='68040', engine_cpu='68040'):
    """The engine profile record: what the engine build compiles and links.

    profile: c|upstream; asm: --engine-asm text (or None); opt: --engine-opt text (or None);
    engine_cpu: --engine-cpu 68040 (the baseline) or 68060 (the experimental 68060-targeted build)."""
    if profile not in PROFILES:
        raise ValueError('--engine-profile takes c or upstream (not %r)' % (profile,))
    engine_cpu = str(engine_cpu or '68040')
    if engine_cpu not in ENGINE_CPUS:
        raise ValueError('--engine-cpu takes 68040 or 68060 (not %r)' % (engine_cpu,))
    if engine_cpu == '68060' and cpu != '68040':
        raise ValueError('--engine-cpu 68060 needs the FPU build (--cpu 68040), not --cpu %s' % (cpu,))
    units = parse_asm(asm)
    level = parse_opt(opt)
    selected = tuple(PROFILE_ASM[profile]) if units is None else units
    level = PROFILE_OPT[profile] if level is None else level
    if cpu == '68020':
        if 'maths' in selected:
            raise ValueError('--engine-asm maths needs the 68040 build (mathlib_68k.s uses the FPU)')
        if {'spans', 'turb'} & set(selected) and 'fixed' not in selected:
            raise ValueError("--engine-asm spans/turb in the 68020 build needs 'fixed' "
                             '(d_scan_68k_nofpu.s calls fixedpoint_asm.s)')
    linked = sorted({UNIT_OBJECTS[unit][cpu] for unit in selected if cpu in UNIT_OBJECTS[unit]})
    effective = tuple(unit for unit in selected if cpu in UNIT_OBJECTS[unit])
    label = next((name for name in PROFILES
                  if {unit for unit in PROFILE_ASM[name] if cpu in UNIT_OBJECTS[unit]} == set(effective)
                  and PROFILE_OPT[name] == level), 'custom')
    # (the 68060 build links the same objects as the 68040 build: the same make target, other -m flags)
    return {'profile': profile, 'label': label, 'cpu': cpu, 'engine_cpu': engine_cpu,
            'engine_cpu_flags': ('-m68060 -mhard-float (libraries of the 68040 build)' if engine_cpu == '68060'
                                 else ('-m68040 -m68881' if cpu == '68040' else None)),
            'asm': list(selected), 'asm_linked': list(effective), 'asm_objects': linked,
            'opt': level,
            'opt_flags': ('-O1 everywhere' if level == 'o1'
                          else '-O2, mathlib.c and in_amiga.c -O1'),
            'd_sprite': '-O0',
            'overrides': {'asm': asm, 'opt': opt},
            'notes': {unit: UNIT_NOTES[unit] for unit in selected if unit in UNIT_NOTES},
            'upstream_revision': UPSTREAM_REVISION if (selected or level != 'o1') else None,
            'credit': CREDIT if (selected or level != 'o1') else None}


def engine_cpu(record):
    """The record's --engine-cpu (68040 for records written before the option existed)."""
    return record.get('engine_cpu') or '68040'


def is_default(record):
    """True for the c profile with nothing linked, -O1 and the 68040 baseline: the build's commands stay
    unchanged."""
    return not record['asm'] and record['opt'] == 'o1' and engine_cpu(record) == '68040'


def make_variables(record):
    """engine/aga/Makefile variables; none for the c profile (its make command stays unchanged)."""
    if is_default(record):
        return []
    out = ['ENGINE_ASM=' + ' '.join(record['asm']), 'ENGINE_OPT=' + record['opt']]
    if engine_cpu(record) != '68040':
        out.append('ENGINE_CPU=' + engine_cpu(record))
    return out


def short(record):
    """One line for logs, summaries and the boot check: e.g. 'upstream (asm turb,c2p; -O1)'."""
    asm = ','.join(record['asm_linked']) or 'none'
    level = '-O1' if record['opt'] == 'o1' else '-O2'
    cpu = '; 68060' if engine_cpu(record) == '68060' else ''
    if record['label'] == 'c':
        return 'c (C paths, -O1%s)' % cpu
    return '%s (asm %s; %s%s)' % (record['label'], asm, level, cpu)


def boot_line(record):
    """The boot check row (engine/aga/boot/bootcheck.asm includes amiwind_engine.i)."""
    if record['label'] == 'c':
        value = 'c: C paths, -O1'
    elif record['label'] == 'upstream':
        value = 'upstream: 68k asm, -O1'
    else:
        value = 'custom: asm %d, -O%s' % (len(record['asm_linked']), record['opt'][1])
    if engine_cpu(record) == '68060':
        value += ', 68060'
    return ('Engine profile:       ' + value).ljust(49) + ' [i] INFO'


def write_boot_include(directory, record):
    """amiwind_engine.i for the boot check: the engine profile row."""
    from pathlib import Path
    path = Path(directory) / 'amiwind_engine.i'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("; Generated from the engine profile (--engine-profile); do not edit.\n"
                    'engine_note:    dc.b "%s",10,0\n' % boot_line(record), encoding='utf-8', newline='\n')
    return path


def check_link_map(map_text, record):
    """Every selected assembly object is in the link map, and no assembly object is linked when none
    is selected (the c profile links no upstream assembly). Returns the problems (empty = fine)."""
    problems = []
    every = {name for unit in UNIT_OBJECTS.values() for name in unit.values()}
    for name in sorted(every):
        present = ('/' + name) in map_text or ('\\' + name) in map_text
        wanted = name in record['asm_objects']
        if wanted and not present:
            problems.append('selected assembly object %s is not in the link map' % name)
        if present and not wanted:
            problems.append('assembly object %s is linked but not selected' % name)
    return problems


def add_options(parser):
    parser.add_argument('--engine-profile', choices=PROFILES, default='c',
                        help='Engine code paths (docs/ENGINE_PROFILES.md): c = AmiWind C paths at -O1 (default, the '
                             'regression reference); upstream = ' + CREDIT + ': upstream 68k assembly (turbulent span, '
                             'chunky-to-planar) at -O1 as upstream builds. EXPERIMENTAL')
    parser.add_argument('--engine-asm', metavar='UNITS', default=None,
                        help='Override the profile\'s assembly units: a comma list of %s, or none, or all '
                             '(EXPERIMENTAL; docs/ENGINE_PROFILES.md)' % ','.join(UNITS))
    parser.add_argument('--engine-opt', choices=('o1', 'o2', 'upstream'), default=None,
                        help="Override the profile's optimisation: o1 (-O1 everywhere; upstream = o1, as upstream's Makefile) "
                             'or o2 (the selective -O2 experiment: mathlib.c and in_amiga.c at -O1). EXPERIMENTAL')
    parser.add_argument('--engine-cpu', choices=ENGINE_CPUS, default='68040',
                        help='Target CPU of the engine code: 68040 (default, the baseline) or 68060 (GCC 68060 '
                             'instruction selection, -m68060 -mhard-float; runs on a 68060 only; docs/68060.md). '
                             'EXPERIMENTAL')


def from_args(args, cpu='68040'):
    return resolve(getattr(args, 'engine_profile', 'c') or 'c', getattr(args, 'engine_asm', None),
                   getattr(args, 'engine_opt', None), cpu, getattr(args, 'engine_cpu', None) or '68040')


def cli_arguments(args):
    """The build_aga.py engine options for a build.py run: none for the default c profile."""
    out = []
    if (getattr(args, 'engine_profile', 'c') or 'c') != 'c':
        out += ['--engine-profile', args.engine_profile]
    if getattr(args, 'engine_asm', None) is not None:
        out += ['--engine-asm', args.engine_asm]
    if getattr(args, 'engine_opt', None) is not None:
        out += ['--engine-opt', args.engine_opt]
    if (getattr(args, 'engine_cpu', None) or '68040') != '68040':
        out += ['--engine-cpu', args.engine_cpu]
    return out
