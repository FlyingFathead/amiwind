#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""TEST BUILDS ONLY: the --chim-sol-test world stage (chim-sol) through a runner of its own, for comparison images
of Solstheim's glacier corner (SOL-GLACIER-METHODS-AB-COMPARE-68):

    tools/solstheim_test_world.py [--unit-pool DIR] [--mesh-method-set NAME] [--look-only] <tools/chim_build.py arguments>

It runs tools/chim_build.py in this process, as tools/bloodmoon_solstheim.py does for the module's world stage, with
three options of its own that never reach the converter:
- --unit-pool DIR: the converter's unit cache backed by the shared storage pool (bloodmoon_solstheim.pooled_units),
  so the stage takes the units the CHIMport runs of the same cells and set stored;
- --mesh-method-set NAME: the named set of config/mesh-method-sets.json for the meshes it lists (chim.method_sets);
- --look-only: the CHIM heap gate and the zone walk gate REPORT instead of stopping, for this process only: each
  gate's full report is still written, and the stage's receipt (OUT/chim-receipt.json) says "does not fit 32 MB:
  look only" with the gates' own lines. Such frames are for look-only sessions with more Fast RAM; the builder
  refuses the option for release candidates and finals (tools/build.py, project_version).
tools/chim_build.py and the converters are unchanged; the builder names this runner only when one of the options is
given (tools/build.py chim_sol_test_commands), so the test route's command without them is the one before.
"""
import json
from pathlib import Path
import sys

LOOK_ONLY = '--look-only'
LOOK_ONLY_TEXT = 'does not fit 32 MB: look only'


def take_flag(argv, flag):
    """(whether FLAG was given, ARGV without it)."""
    argv = list(argv)
    if flag not in argv:
        return False, argv
    argv.remove(flag)
    return True, argv


def out_of(argv):
    """The converter's --out folder from its arguments, or None."""
    for i, part in enumerate(argv):
        if part == '--out' and i + 1 < len(argv):
            return Path(argv[i + 1])
        if part.startswith('--out='):
            return Path(part.split('=', 1)[1])
    return None


def look_only_gates():
    """(failures, restore): chim.heap.require_heap and chim.zone_sim.require_zone_walk made to report a budget
    failure instead of raising it, for this process; FAILURES collects each gate's own line. A failure that is not
    the budget (a world that does not read back) still stops the stage."""
    import chim.heap
    import chim.zone_sim
    heap, walk = chim.heap.require_heap, chim.zone_sim.require_zone_walk
    failures = []

    def require_heap(out, *args, **kw):
        try:
            return heap(out, *args, **kw)
        except ValueError as exc:
            if not str(exc).startswith('CHIM heap gate failed'):
                raise
            failures.append(str(exc))
            print('LOOK ONLY: %s' % exc, flush=True)
            path = Path(kw.get('report_path') or Path(out) / 'chim-heap.json')
            report = json.loads(path.read_text(encoding='utf-8')) if path.is_file() else {'frames': []}
            return dict(report, status='failed (look only)')

    def require_zone_walk(out, *args, **kw):
        try:
            return walk(out, *args, **kw)
        except ValueError as exc:
            if not str(exc).startswith('CHIM zone walk gate failed'):
                raise
            failures.append(str(exc))
            print('LOOK ONLY: %s' % exc, flush=True)
            return {'status': 'failed (look only)', 'walks': []}

    chim.heap.require_heap, chim.zone_sim.require_zone_walk = require_heap, require_zone_walk

    def restore():
        chim.heap.require_heap, chim.zone_sim.require_zone_walk = heap, walk
    return failures, restore


def mark_receipt(out, failures):
    """OUT/chim-receipt.json says the frames do not fit, with the gates' own lines (the image's record takes it)."""
    path = Path(out) / 'chim-receipt.json'
    receipt = json.loads(path.read_text(encoding='utf-8')) if path.is_file() else {}
    receipt['look_only'] = {'text': LOOK_ONLY_TEXT, 'gates': list(failures)}
    path.write_text(json.dumps(receipt, indent=1, sort_keys=True) + '\n', encoding='utf-8', newline='\n')


LAYER_DATA_FORMAT = 'aw-chim-layer-data-1'       # tools/chim_layer_data.py's record in its folder


def data_files_of(argv):
    """The converter's --data-files folder from its arguments, or None."""
    for i, part in enumerate(argv):
        if part == '--data-files' and i + 1 < len(argv):
            return Path(argv[i + 1])
        if part.startswith('--data-files='):
            return Path(part.split('=', 1)[1])
    return None


def own_masters(argv):
    """The master list the stage's data folder holds: 'Morrowind.esm' alone for the layered test folder of
    tools/chim_layer_data.py (its Morrowind.esm is the base master with the layer's records appended, a standalone
    master; no other master file is in it), else None (the build's selection stands). The build exports its own
    selection (all three masters by default since the expansions are selected), which that folder does not hold:
    the glacier comparison's first test image stopped on 'Missing Tribunal.esm' (21 November 2026)."""
    data = data_files_of(argv)
    record = data / 'layer-data.json' if data is not None else None
    if record is None or not record.is_file():
        return None
    try:
        layered = json.loads(record.read_text(encoding='utf-8')).get('format') == LAYER_DATA_FORMAT
    except (OSError, ValueError):
        return None
    return 'Morrowind.esm' if layered else None


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    root = Path(__file__).resolve().parents[1]
    # src/ before tools/: the src/mwad package, not tools/mwad.py (as tools/chim_build.py orders them)
    for path in (root / 'tools', root / 'src'):
        while str(path) in sys.path:
            sys.path.remove(str(path))
        sys.path.insert(0, str(path))
    import bloodmoon_solstheim
    from chim import method_sets
    pool, argv = bloodmoon_solstheim.take_pool(argv)
    name, argv = method_sets.take(argv)
    look, argv = take_flag(argv, LOOK_ONLY)
    restores = []
    masters = own_masters(argv)
    if masters is not None:
        # the stage reads its own folder's master alone, for this process and the workers it starts (they inherit
        # the environment); put back after
        import os
        from mwad.masters import MASTERS_ENV
        before = os.environ.get(MASTERS_ENV)
        os.environ[MASTERS_ENV] = masters
        print('SOLSTHEIM TEST: the layered test data folder: masters %s (the build selects %s)'
              % (masters, before or 'the base game alone'), flush=True)

        def put_back(before=before):
            if before is None:
                os.environ.pop(MASTERS_ENV, None)
            else:
                os.environ[MASTERS_ENV] = before
        restores.append(put_back)
    import chim_build
    made = bloodmoon_solstheim.pooled_units(pool) if pool is not None else None
    if name:
        # the set's report (method C's figures per unit) goes into the converter's output folder
        record, restore = method_sets.install(name, report=out_of(argv))
        restores.append(restore)
        print('SOLSTHEIM TEST: %s' % method_sets.line(record), flush=True)
    failures = []
    if look:
        failures, restore = look_only_gates()
        restores.append(restore)
        print('SOLSTHEIM TEST: look only: the heap and zone walk gates report instead of stopping', flush=True)
    sys.argv = [str(Path(__file__).resolve().parent / 'chim_build.py'), *argv]
    try:
        result = chim_build.main()
    finally:
        while restores:
            restores.pop()()
        if made is not None:
            print(bloodmoon_solstheim.pool_line(made).replace('MODULE bloodmoon-solstheim', 'SOLSTHEIM TEST'),
                  flush=True)
    if look and failures and out_of(argv) is not None:
        mark_receipt(out_of(argv), failures)
        print('SOLSTHEIM TEST: %s (%d gate(s)); the receipt says so' % (LOOK_ONLY_TEXT, len(failures)), flush=True)
    return result


if __name__ == '__main__':
    sys.exit(main())
