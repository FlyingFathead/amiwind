# SPDX-License-Identifier: GPL-3.0-only
"""The compiler's identity: the SHA-256 of its source files, whole (the mwscript stage's unit key and its receipt's
'compiler'), and the image step's check that the compiled scripts it installs were made by this source's compiler.

Origin BUILD-MWSCRIPT-STAGE-REUSED-COMPILER-CHANGED-59: every v0.0.59 build reused the stage from v0.0.58. Its record
of what it used held only the compiler functions that ran, not the table functions.HOST (RaiseRank, LowerRank,
ShowRestMenu, GetPCSleep were added) nor these files hashed whole, so v0.0.59 shipped the older bytecode."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def compiler_files():
    """tools/mwscript/*.py, the stage (tools/prepare_mwscript.py), and tools/prepare_combat.py, whose autocalculation
    and equipment rules the actor table uses (actors.py); tools/room_batches.py and tools/town_interiors.py, whose
    door arrival rule the player's PositionCell uses (rooms.py)."""
    return sorted((ROOT / 'tools' / 'mwscript').glob('*.py')) + [ROOT / 'tools' / 'prepare_mwscript.py',
                                                                   ROOT / 'tools' / 'prepare_combat.py',
                                                                   ROOT / 'tools' / 'room_batches.py',
                                                                   ROOT / 'tools' / 'town_interiors.py']


def compiler_identity():
    h = hashlib.sha256()
    for path in compiler_files():
        h.update(path.name.encode() + b'\0' + path.read_bytes())
    return h.hexdigest()


def note_read():
    """Tell the stage trace that the stage keys the compiler's files whole ('=' lines, pass_cache.note_covered): the
    trace sees them only as imports, so the stage's record held only the functions that ran."""
    from pass_cache import note_covered
    lines = []
    for path in compiler_files():
        try:
            lines.append('=' + Path(path).resolve().relative_to(ROOT).as_posix())
        except ValueError:
            continue
    note_covered(lines)


def check(stage):
    """Refuse compiled game scripts that another compiler made: the stage receipt's 'compiler' must be this source's
    (tools/build_aga.py install_mwscript). Returns {'compiler': the receipt's, 'source_compiler': this source's}."""
    receipt = json.loads((Path(stage) / 'mwscript-receipt.json').read_text(encoding='utf-8'))
    made = (receipt.get('inputs') or {}).get('compiler')
    source = compiler_identity()
    if made != source:
        raise ValueError('Compiled scripts in %s were made by another compiler: receipt compiler %s, this source %s. '
                         'Rebuild the mwscript stage (--rebuild-stage mwscript) and register the reuse that kept them '
                         '(BUILD-MWSCRIPT-STAGE-REUSED-COMPILER-CHANGED-59)' % (stage, made, source))
    return {'compiler': made, 'source_compiler': source}
