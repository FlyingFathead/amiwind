# SPDX-License-Identifier: GPL-3.0-only
"""The build module bloodmoon-solstheim in the build plan: which cells it builds, and its two stages.

tools/build.py calls resolve() with its other cell preflights and commands() where the plan is made, and nothing
else of the builder knows the module (the module rule, tools/build.py "THE EXPANSIONS AS BUILD MODULES"): its stages
are in the plan only when Bloodmoon.esm is selected and the tracker reference calls at least one of Solstheim's cells
finished; they are keyed only by their own inputs (tools/build_cache.py MODULE_STAGE_LAYERS); no base stage reads
their output or takes an option from them. Without the module the plan is the one before, command for command.

- bloodmoon-solstheim-data: the data folder of the base master and Bloodmoon.esm (tools/presented_data.py);
- bloodmoon-solstheim: the cells' CHIM world (tools/bloodmoon_solstheim.py: tools/chim_build.py on that folder, the
  module's own cells, its own unit cache), installed by the image as the store chimsol with the frame maps slNNNN
  and the rows file world/regions-sl.awr (tools/chim/layer_stores.py MODULE_STAGES).

Both functions take what they need of the builder as arguments (this file never imports tools/build.py).
"""
MASTER = 'Bloodmoon.esm'
DATA_STAGE = 'bloodmoon-solstheim-data'
STAGE = 'bloodmoon-solstheim'
MASTERS = 'Morrowind.esm,Bloodmoon.esm'
UNIT_CACHE = 'cache/bloodmoon-solstheim-units'
CELLS_OPTION = 'bloodmoon_solstheim_cells'        # the build option value that holds the module's cells
# The stages that take something of the module after their unchanged base command. The image installs the world by
# its own rule (tools/chim/layer_stores.py image_options: every module stage in the plan); the tracker data counts the
# module's world as the build's own cells.
TRACKER_STAGE = 'cell-progress'


def resolve(args, masters, builder, status, log=print):
    """The module's cells: Solstheim's cells that the tracker file STATUS calls finished (the named set of
    Bloodmoon.esm, tools/chim/regions.py layer_sets), set as args.bloodmoon_solstheim_cells; None when the module
    is not built: Bloodmoon not among MASTERS (the build's selection in load order: --no-dlc, --dlc tribunal), a
    MiniWind sandbox, a cell list of the caller's own (--chim-regions: a test of named cells builds those and nothing
    else), no CHIM builder (BUILDER: tools/build.py resolve_builder's record, or a call that gives it), or no finished
    cell. A test image of named Solstheim cells (--chim-sol-test) does not build it either, and says so: one plan line
    and the record {'built': False, 'reason'}, which the build writes into build-state.json (tools/build.py
    chim_sol_test_module_record). The base world's cell list never holds these cells. Returns the record for the
    build log."""
    from chim import regions as chim_regions
    setattr(args, CELLS_OPTION, None)
    if MASTER not in masters or getattr(args, 'miniwind', False) or getattr(args, 'chim_regions', None):
        return None
    if getattr(args, 'chim_sol_test', None):
        # a test image of named Solstheim cells (--chim-sol-test, tools/build.py chim_sol_test_commands): its own test
        # world is the image's Solstheim store chimsol, the store this module installs, so the module is not built,
        # as for a cell list of the caller's own (the glacier comparison's image stopped in its image step on two
        # chimsol stores, 21 November 2026)
        reason = ('--chim-sol-test names Solstheim\'s cells for this image: a test image, Solstheim is only those '
                  'cells (the store chimsol is the test world)')
        log('Module bloodmoon-solstheim: NOT BUILT: %s' % reason)
        return {'built': False, 'reason': reason}
    builder = builder() if callable(builder) else builder
    if builder['builder'] != 'chim':
        return None
    table, problems = chim_regions.plan([chim_regions.layer_sets()[MASTER]], status, towns=())
    kinds = chim_regions.table_kinds(table)
    if not kinds:
        # no finished cell yet (the plan says so as "holds no cell"): the module is not built, and a build with
        # Bloodmoon selected is the build without it; the first-minute check 'expansion-module-cells' says how many
        # cells the tracker file calls finished
        for problem in problems:
            log('Module bloodmoon-solstheim: not built: %s' % problem)
        return None
    problems += chim_regions.owned_land_problems(kinds, getattr(args, 'data_files', None))
    if problems:
        raise ValueError('The module bloodmoon-solstheim (Solstheim\'s outdoor cells) failed its cell preflight before '
                         'any stage (--no-dlc or --dlc tribunal builds without it):' + (chr(10) + '  ')
                         + (chr(10) + '  ').join(problems))
    setattr(args, CELLS_OPTION, chim_regions.encode_cells(kinds))
    c = table['counts']
    log('Module bloodmoon-solstheim: %d Solstheim cells in %d frames, a world of their own (the stages '
        'bloodmoon-solstheim-data and bloodmoon-solstheim); %d dropped' % (c['cells'], c['frames'],
                                                                         len(table['dropped'])))
    return {'selection': table['selection'], 'counts': c, 'dropped': table['dropped']}


def commands(args, steps, tool, run, tools, jobs, chim_options):
    """STEPS with the module's two stages before the base CHIM world stage, which they neither read nor change, and
    the tracker stage counting the module's world. TOOL, RUN, TOOLS, JOBS: as tools/build.py gives its own command
    makers; CHIM_OPTIONS(args, cells): the build's opt-in CHIM settings with the module's cells in place of the base
    list (tools/build.py module_chim_options). Without the module's cells: STEPS unchanged, every command as before."""
    cells = getattr(args, CELLS_OPTION, None)
    if not cells:
        return steps
    folder, world = run / DATA_STAGE, run / STAGE
    lighting = next((command[command.index('--lighting-type') + 1] for name, command in steps
                     if name == 'chim' and '--lighting-type' in command), 'hybrid')
    index = next(i for i, (name, _) in enumerate(steps) if name == 'chim')
    steps = list(steps)
    # the shared storage pool of the build (tools/storage_pool.py: --storage-pool-dir, the environment, else the
    # workspace's own): the world stage takes the units a CHIMport run of the same cells stored there and stores its
    # own (tools/bloodmoon_solstheim.py pooled_units; CHIMPORT-UNITS-NOT-SHARED-WITH-BUILD-68). The pool is
    # content-addressed in every stage key (tools/build_cache.py POOL_TOKEN), so what it holds re-keys nothing.
    import storage_pool
    pool = storage_pool.resolve_dir(args.workspace, getattr(args, 'storage_pool_dir', None))[0]
    steps[index:index] = [
        (DATA_STAGE, tool('presented_data.py', '--data-files', args.data_files, '--out', folder,
                          '--masters', MASTERS)),
        (STAGE, tool('bloodmoon_solstheim.py', '--data-files', folder,
                     '--palette', run / 'intro-scene/id1/gfx/palette.lmp', '--out', world,
                     '--qbsp', tools['qbsp'], *chim_options(args, cells),
                     '--lighting-type', lighting,
                     '--unit-cache', args.workspace / UNIT_CACHE, '--unit-pool', pool,
                     # the mesh method set (--chim-mesh-method-set, config/mesh-method-sets.json): the runner's own
                     # option, only when given (SOL-GLACIER-METHODS-AB-COMPARE-68)
                     *(('--mesh-method-set', args.chim_mesh_method_set)
                       if getattr(args, 'chim_mesh_method_set', None) else ()),
                     '--jobs', jobs, '--validate', '--stats', '--sdk', args.sdk))]
    # strings only: the commands go into build-state.json (BUILD-NPCLOD-PATH-ARG-34)
    tracker = ['--module-chim-world', str(world)]
    return [(name, list(command) + tracker if name == TRACKER_STAGE else command) for name, command in steps]
