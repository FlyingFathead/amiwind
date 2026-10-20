# SPDX-License-Identifier: GPL-3.0-only
"""Stand-in assets never ship behind a warning line (SKY-FLAT-PALETTE-DRIFT-41).

v0.0.40 and v0.0.41 shipped a one-colour placeholder sky because the shared cloud sky could not be
prepared, and the build said so in one warning line. Every place where the builder would put a stand-in
(or nothing) where the game's own asset belongs goes through check(): with the game's own data files
that stops the build, naming the placeholder, the unit, each input with its SHA-256 and the reason. A test
build may let a named placeholder through with --allow-placeholder NAME (loud, recorded in the image
receipt; a private-test waiver, so a release candidate or final refuses it and release readiness lists
it).

KNOWN_GAPS: a stand-in that every build ships today because of an OPEN bug in the register is not
refused (that would stop every build) and not hidden either: it prints a [PLACEHOLDER KNOWN GAP] line
naming the bug and is recorded in the image receipt with that bug ID. When the bug is fixed its entry
goes, and the stand-in stops the build again (tests/test_placeholder_policy.py keeps every entry tied
to an open bug).
Standard library only.
"""
import hashlib
from pathlib import Path

OPTION = '--allow-placeholder'

# name: what the image ships instead
NAMES = {
    'shared-sky': 'the converted maps\' one-colour placeholder as the exterior sky (no clouds)',
    'night-sky': 'no night atlas (no stars, nebula or moon artwork) or the legacy atlas',
    'night-windows': 'an empty night-windows table (no window glows at night)',
    'ui-font': 'the readable fallback interface font instead of the converted original fonts',
    'logo-font': "the startup screen lines in Pillow's built-in font instead of the game font",
    'intro-video': 'no intro video',
}


# name: the open bug that makes every build ship this stand-in today
KNOWN_GAPS = {
    'night-windows': 'NIGHT-WINDOWS-LOST-CHIM-36',
}


class PlaceholderRefused(ValueError):
    """A stand-in would ship; the message names it, the unit, the inputs and the opt-out."""


def parse(values):
    """The set of allowed names from repeated --allow-placeholder values (comma lists allowed)."""
    allowed = set()
    for value in values or ():
        for name in str(value).split(','):
            name = name.strip()
            if not name:
                continue
            if name not in NAMES:
                raise ValueError(f'{OPTION} {name!r}: unknown placeholder (known: {", ".join(sorted(NAMES))})')
            allowed.add(name)
    return allowed


def describe_inputs(inputs):
    """'path sha256 X' or 'path missing' for each input path."""
    parts = []
    for path in inputs or ():
        path = Path(path)
        if path.is_file():
            parts.append(f'{path} sha256 {hashlib.sha256(path.read_bytes()).hexdigest()}')
        else:
            parts.append(f'{path} missing')
    return '; '.join(parts) or 'none'


def check(name, reason, allowed=(), unit=None, inputs=(), records=None):
    """Refuse the placeholder NAME (PlaceholderRefused) unless it is allowed or a known gap (KNOWN_GAPS);
    then print it loudly and return (and append to RECORDS) its record."""
    if name not in NAMES:
        raise ValueError('Unknown placeholder ' + repr(name))
    record = {'placeholder': name, 'ships': NAMES[name], 'reason': str(reason), 'unit': unit,
              'inputs': describe_inputs(inputs)}
    if name in KNOWN_GAPS and name not in set(allowed or ()):
        record['known_gap'] = KNOWN_GAPS[name]
        print(f'[PLACEHOLDER KNOWN GAP] {name}: this image ships {NAMES[name]} ({reason}; unit {unit or "-"}; '
              f'open bug {KNOWN_GAPS[name]})', flush=True)
        if records is not None:
            records.append(record)
        return record
    if name not in set(allowed or ()):
        raise PlaceholderRefused(
            f'Placeholder refused: {name} (the image would ship {NAMES[name]}): {reason}; unit {unit or "-"}; '
            f'inputs {record["inputs"]}. Test builds only: {OPTION} {name} (refused for release candidates '
            'and finals).')
    print(f'[PLACEHOLDER ALLOWED] {name}: this image ships {NAMES[name]} ({reason}; unit {unit or "-"}; '
          f'{OPTION} {name})', flush=True)
    if records is not None:
        records.append(record)
    return record
