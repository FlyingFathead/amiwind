# SPDX-License-Identifier: GPL-3.0-only
"""The image step's last part, call by call: which of its checks a build tries in its first minutes.

tools/build_aga.py finalize_image runs after every stage: a check that fails there fails an hour or more into a
build. A build with Mournhold's districts stopped there, in the door check, 1 h 34 min after it started
(DOOR-CHECK-MODULE-FRAME-MAPS-67). The rule since then: a check of the image's last part is tried early, on what
the plan already knows (the map names a build will write, the stage outputs it reuses), or this table says why it
cannot be yet.

Every function finalize_image calls (one it imports inside itself, or one of build_aga's own) is in exactly one
table here:

- CHECKS: it can refuse the image. 'early': the name of the first-minute or after-stage check that tries it before
  the image step (tools/build_preflight.py EARLY_CHECKS), or None with 'why': what it needs that no earlier point of
  the build has. A row with None is open work, named: the list of such rows is the list of failures a build can still
  meet only at its end.
- WORK: it installs, writes, reads or counts; it is not a check.

tests/test_finalize_checks.py reads finalize_image's source and fails when a call is in neither table, in both, or
no longer made; when a name that reads as a check (require_, check_, verify_, validate_, audit_, _gate) is listed
as work; and when an 'early' name is not a registered early check. So a new check of the image's last part cannot
be added without deciding, here, how a build learns of its failure early.

Builder bookkeeping only: no stage reads this module.
"""

BUILT_MAPS = 'needs the maps and tables this image has just written; no dry run from the plan yet'
STAGE_OUTPUTS = 'needs the stage outputs staged into this image; no dry run on the stored outputs yet'

CHECKS = {
    # the doors
    'write_door_check': {'early': 'module-frame-maps',
                         'why': 'the job table is tried on a module\'s frame map names; the walk through the '
                                'engine\'s door code needs the image\'s banks and maps'},
    'write_world_doors': {'early': None, 'why': BUILT_MAPS},
    'write_room_batch_links': {'early': None, 'why': BUILT_MAPS},
    # the maps against the engine's tables and memory
    'check_engine_map_limits': {'early': 'module-store-maps',
                                'why': 'tried right after a module\'s world stage on its own frame maps; the island\'s '
                                       'maps and the rooms need the image'},
    'require_frame_map_heap': {'early': None, 'why': BUILT_MAPS},
    'require_room_map_heap': {'early': None, 'why': BUILT_MAPS},
    'audit_world_map_heap_with_receipt': {'early': None, 'why': BUILT_MAPS},
    'apply_map_budget_policy': {'early': None, 'why': BUILT_MAPS},
    'verify_optimized_maps': {'early': None, 'why': BUILT_MAPS},
    'verify_heap_loader_source_receipt': {'early': None, 'why': STAGE_OUTPUTS},
    'require_stairs': {'early': None, 'why': BUILT_MAPS + ' (off by default: the stair walk)'},
    'known_stair_findings': {'early': None, 'why': 'reads the accepted findings given on the command line only'},
    # the actors
    'require_fitted': {'early': None, 'why': BUILT_MAPS},
    'require_actor_ground': {'early': None, 'why': BUILT_MAPS},
    'creature_census_stage': {'early': None, 'why': BUILT_MAPS},
    'actor_spec_stage': {'early': None, 'why': BUILT_MAPS},
    'entity_gate': {'early': None, 'why': BUILT_MAPS},
    'require_arrivals': {'early': None, 'why': BUILT_MAPS},
    # lights, plants, legacy maps
    'check_image': {'early': None, 'why': BUILT_MAPS},
    'require_chim_coverage': {'early': None, 'why': BUILT_MAPS},
    'require_no_legacy_areas': {'early': None, 'why': BUILT_MAPS},
    'legacy_layout_findings': {'early': None, 'why': BUILT_MAPS},
    # the staged content
    'payload_preflight': {'early': None, 'why': STAGE_OUTPUTS},
    'validate_world_ui': {'early': None, 'why': STAGE_OUTPUTS},
    'ready_hands_check': {'early': None, 'why': STAGE_OUTPUTS},
    'check_recorded': {'early': None, 'why': STAGE_OUTPUTS},
    'check_always_included': {'early': None, 'why': BUILT_MAPS},
    'require_complete_media_outputs': {'early': None, 'why': STAGE_OUTPUTS},
}

WORK = frozenset('''
    excluded_groups image_jobs Background region_actors_on prepare_staged_sky placeholder install_mwscript
    install_focus stage install_books install_chargen install_hand_catalog configure_staged_maps worldspawn_sky_keys
    cull_staged_maps staged_exterior_map_names enabled_value write_hand_table stamp_staged_hands stamp_staged_cells
    staged_interior_map_names install_chim_interiors bake_room_ground frozen_maps optimize_maps harvest_image_step
    chim_town_grounding empty_miniwind_actor_evidence chim_world_once master_path chim_town_placements
    chim_region_placements voice_table_step dialogue_table_step ambient_table_step tp_places_step
    installed_actor_library install_actor_library write_coverage write_actor_table world_progress_step runtime_towns
    chim_native_towns stage_direct_start miniwind_options stage_night_lighting image_sources chim_town_specials
    chim_frame_maps chim_town_rows region_actor_inputs region_actor_summary remove_legacy_areas staged_extra_towns
    remove_towns_not_on_chim prune_world_payload native_towns _frame_heap_cache install_chim_sol install_layer_stores
    layer_actor_inputs sol_test_module_record
    stage_effect_links effect_link_layers presented_places rebind_chim_maps prepare_guard_torches catalogue_step creature_census_partial world_allowances
    stair_rules_enabled rebind_marked_maps bind_heap_report heap_watcher_summary add_heap image_start
    image_content_fingerprint write_catalogue stage_catalogue legacy_maps_summary share_payload miniwind_hdf_tag
    disk_layout_settings pack_world_volumes add_chim_volume planned_mib plan_drives planned_partition
    write_boot_partition compact_layout hash_files assemble_drives combat_summary miniwind_start digest
    stage_excluded_content miniwind_receipt write_configs print_outputs write_world_coverage
'''.split())

CHECK_WORDS = ('require_', 'check_', 'verify_', 'validate_', 'audit_')
CHECK_ENDS = ('_gate', '_check')


def reads_as_check(name):
    """True when NAME reads as a check by the code's own naming."""
    return name.startswith(CHECK_WORDS) or name.endswith(CHECK_ENDS)


def finalize_calls(source):
    """The names finalize_image calls that it imports inside itself or that build_aga defines, from build_aga.py's
    SOURCE text (the name used at the call: an import's alias)."""
    import ast
    tree = ast.parse(source)
    own = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}
    function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'finalize_image')
    imported = {alias.asname or alias.name for node in ast.walk(function) if isinstance(node, ast.ImportFrom)
                for alias in node.names}
    return {node.func.id for node in ast.walk(function)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
            and (node.func.id in imported or node.func.id in own)}


def not_tried_early():
    """[(check, why)] of the checks a build can still meet only in the image's last part, by name."""
    return sorted((name, row['why']) for name, row in CHECKS.items() if not row['early'])
