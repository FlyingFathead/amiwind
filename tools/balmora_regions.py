# SPDX-License-Identifier: GPL-3.0-only
"""Balmora's sub-cell layout: the generic town layout with the Balmora config.

Kept for existing callers; the implementation lives in town_regions.py.
"""
from town_regions import (visual_profile, intersects, local_bounds, regions, validate_partition,
                          owner, select_references, audit_coverage, collision_coverage)
from town_config import load_settings

__all__ = ['config', 'visual_profile', 'intersects', 'local_bounds', 'regions', 'validate_partition',
           'owner', 'select_references', 'audit_coverage', 'collision_coverage']


def config():
    return load_settings('balmora')
