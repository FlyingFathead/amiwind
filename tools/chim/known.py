# SPDX-License-Identifier: GPL-3.0-only
"""Known stair findings a private -devN test may accept (light: no numpy; tools/build.py checks them
before setup)."""


KNOWN_STAIR_FINDINGS = 'config/known-stair-findings.json'


def known_stair_findings(ids, root=None):
    """{placement reference: finding ID} for the accepted known stair findings (by tracker ID, from
    config/known-stair-findings.json); an unknown ID is refused."""
    import json
    from pathlib import Path
    root = Path(root) if root else Path(__file__).resolve().parents[2]
    table = json.loads((root / KNOWN_STAIR_FINDINGS).read_text(encoding='utf-8'))['findings']
    unknown = sorted(set(ids) - set(table))
    if unknown:
        raise ValueError('Unknown stair finding: %s (known: %s)' % (', '.join(unknown), ', '.join(sorted(table))))
    return {ref: fid for fid in ids for ref in table[fid]['refs']}
