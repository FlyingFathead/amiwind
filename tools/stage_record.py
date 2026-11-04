# SPDX-License-Identifier: GPL-3.0-only
"""What a stage's record of what it used (tools/build_cache.py used_record, the narrowed reuse key) must also hold.

BUILD-MWSCRIPT-STAGE-REUSED-COMPILER-CHANGED-59: every v0.0.59 build, the release included, reused the mwscript stage
from v0.0.58 although its compiler changed. The record held only the compiler functions that ran:
- a literal table (build_cache.lazy_tables: functions.HOST) is a unit of its own, and reading it is no call the trace
  can see, so the v0.0.59 additions to HOST (RaiseRank, LowerRank, ShowRestMenu, GetPCSleep) left it unchanged;
- the stage hashes the compiler's files whole (tools/mwscript/ident.py compiler_identity), but the trace saw them only
  as imports.
recorded_tables adds the tables the recorded code names; whole_read_missing refuses a record that lacks a .py file the
stage's code reads whole, so the records written before this fix fall back to the full stage key."""


def recorded_tables(index, units):
    """{module: {table}} of the literal tables (module_symbols 'tables') that UNITS ({module: {unit}}, the code a
    stage ran) name: in their own module, through `from M import TABLE` and through `M.TABLE` / `pkg.M.TABLE`.
    Scheduling units (build_cache.SCHEDULING_UNITS) and output-neutral modules key no stage."""
    from build_cache import OUTPUT_NEUTRAL, SCHEDULING_UNITS
    found = {}

    def resolve(module, level, path):
        if level:
            base = path.rsplit('/', 1)[0] if '/' in path else ''
            for _ in range(level - 1):
                base = base.rsplit('/', 1)[0] if '/' in base else ''
            return index._exact_module(module or '__init__', base)
        return index._exact_module(module) if module else []

    def add(targets, name):
        for target in targets:
            if target in OUTPUT_NEUTRAL or not target.endswith('.py'):
                continue
            if name in (index._module_symbols(target).get('tables') or ()) and (target, name) not in SCHEDULING_UNITS:
                found.setdefault(target, set()).add(name)

    for path, wanted in sorted(units.items()):
        symbols = index._module_symbols(path)
        facts_by_unit = symbols.get('units') or {}
        own = set(symbols.get('tables') or ())
        for unit in sorted(wanted):
            facts = facts_by_unit.get(unit)
            if not facts:
                continue

            def binding(name):
                return (facts.get('bindings') or {}).get(name) or (symbols.get('bindings') or {}).get(name) \
                    or (symbols.get('fallback') or {}).get(name)
            for name in sorted(facts.get('names') or ()):
                if name in own and (path, name) not in SCHEDULING_UNITS:
                    found.setdefault(path, set()).add(name)
                bound = binding(name)
                if bound and bound[0] == 'from':
                    add(resolve(bound[1], bound[2], path), bound[3])
            for value, chain in sorted(facts.get('attributes') or ()):
                bound = binding(value)
                if not bound:
                    continue
                if bound[0] == 'module':
                    module, level = bound[1], bound[2]
                elif bound[0] == 'from':
                    module, level = ('%s.%s' % (bound[1], bound[3]) if bound[1] else bound[3]), bound[2]
                else:
                    continue
                for depth in range(len(chain)):
                    add(resolve('.'.join([module, *chain[:depth]]), level, path), chain[depth])
    return found


def whole_code_reads(index, script):
    """The repository .py files the stage SCRIPT's code reads whole as data (FOLDER.glob('*.py'), a literal path to a
    .py file), from INDEX's static closure; set() for no script or dynamic code; None when it cannot be worked out."""
    if script is None:
        return set()
    try:
        _, data, uncertain = index.closure(script)
    except Exception:  # noqa: BLE001 - a closure that cannot be worked out narrows nothing
        return None
    if uncertain:
        return set()      # dynamic code: its record's own completeness check decides, as before
    return {path for path in data if path.endswith('.py')}


def whole_read_missing(record, index, script):
    """Why RECORD cannot narrow the key of the stage SCRIPT (a .py file its code reads whole that the record keys only
    by the code that ran), or None."""
    whole = whole_code_reads(index, script)
    if whole is None:
        return 'its code reach cannot be worked out'
    missing = sorted(path for path in whole if path not in (record.get('data') or {}))
    if missing:
        return 'its code reads %s whole, which its record keys only by the code that ran' % missing[0]
    return None
