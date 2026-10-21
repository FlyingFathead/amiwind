# SPDX-License-Identifier: GPL-3.0-only
"""The cell crossing method an image starts with (docs/chim/CELL_CROSSINGS.md).

The engine selects the method with the console command "chim crossing 0|1" (engine/aga/src/chim/chim_world.c,
Subcommand; chim_chunks.c ChimChunks_WindowOn): 0, the default, is type 0 (a level change at every frame border);
1 is type 1 (the region frames around the player held as one window, a crossing streams). The command takes effect
at the next map start and is not saved (a stored setting never switches the method), so a build that wants type 1
from the start puts it in the game's default settings: id1/default-game.cfg runs at start-up, before any map
(quake.rc: exec default.cfg, exec default-game.cfg, ...), after the "chim" command is registered (Host_Init:
Host_InitCommands -> AW_DebugInit -> Chim_Init, then exec quake.rc). The command needs no loaded world.

Builder option --chim-crossing 0|1, default 1 since v0.0.47 (decided for the project, 2026-10-21; v0.0.47-dev2 was
built with it). 1 adds the image step's --chim-crossing 1, which ends default-game.cfg with a commented block and
"chim crossing 1" (tools/build_aga.py stage_chim_crossing). 0 writes nothing: the image step's command and the image
are the same as before the option existed (type 0 everywhere, the method before, kept selectable). Towns never join
a type 1 window: their crossings stay type 0 in either case (the engine decides, docs/chim/CELL_CROSSINGS.md). The
image step only: no other stage sees the option.
"""

DEFAULT = '1'           # type 1 by default since v0.0.47 (decided for the project, 2026-10-21); 0 = type 0, the method before
OPTION = '--chim-crossing'
LINE = 'chim crossing 1'


def add_option(parser):
    parser.add_argument(OPTION, choices=('0', '1'), default=DEFAULT,
                        help='The cell crossing method the image starts with (docs/chim/CELL_CROSSINGS.md): 1 (the '
                             'default since v0.0.47) type 1, the region frames around the player as one window '
                             '("chim crossing 1" at the end of default-game.cfg; "chim crossing 0" in the console '
                             'before a map starts gives the old crossing back; towns stay type 0); 0 type 0, a level '
                             'change at every frame border, nothing written (the method before). Image step only.')


def configure(args, builder=None):
    """{'type', 'source'}: --chim-crossing, resolved before any work (the builder's receipt keeps it). BUILDER: the
    resolved builder type; a legacy-builder image has no CHIM world, so it gets type 0 and nothing written (its
    image step as before)."""
    if builder is not None and builder != 'chim':
        return {'type': 0, 'source': 'no CHIM world (builder %s)' % builder}
    value = getattr(args, 'chim_crossing', None)
    if not value or value == DEFAULT:
        return {'type': int(DEFAULT), 'source': 'default'}
    return {'type': int(value), 'source': OPTION + ' ' + value}


def image_arguments(record):
    """The image step's extra arguments: --chim-crossing 1 for type 1, nothing for type 0 (a type 0 build's image
    step and game settings are the same as before the option existed)."""
    return [OPTION, '1'] if record and record.get('type') == 1 else []
