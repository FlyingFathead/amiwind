"""Targeted, reversible visual clearance; never move authored collision."""
import json
from pathlib import Path
import numpy as np


def apply_visual_offsets(index, references, path=None):
    path = path or Path(__file__).resolve().parents[1]/'config/visual-offsets.json'
    config = json.loads(Path(path).read_text())
    for ref in references:
        ref.pop('_visual_offset', None)
    if not config.get('enabled', False):
        return
    for profile in config['profiles']:
        offset = np.asarray(profile['local_runtime_offset'], dtype=float)
        if offset.shape != (3,) or not np.isfinite(offset).all():
            raise ValueError('Visual offset must contain three finite values')
        for ref in references:
            model = index['models'][ref['model_index']]['source'].replace('\\', '/').lower()
            if model == profile['model'].lower() and ref['number'] in profile['references']:
                ref['_visual_offset'] = offset.tolist()


def visual_key(ref):
    return tuple(round(value, 5) for value in ref.get('_visual_offset', [0, 0, 0]))
