"""The image's boot configs against the engine's command buffer (CFG-OVER-COMMAND-BUFFER-68).

Every .cfg the game execs is read whole into the engine's command buffer (engine/aga/src/cmd.c, Cbuf_Init). A file
that does not fit is dropped WHOLE by Cbuf_AddText ("Cbuf_AddText: overflow"), so every setting in it is lost without
a stop. The v0.0.68-dev8 image's default-game.cfg had grown to 8511 bytes against the 8192 of Quake's buffer: none of
the game's defaults ran, the actor table among them, so no outdoor creature was placed. The engine's buffer is now
32768 bytes, and the image step calls check() after it has written its last default line: each boot .cfg must stay
under half of the buffer, the other half for what is queued beside it (the saved settings, a console line).
tests/test_boot_cfg_fits.py keeps ENGINE_CMD_BUFFER equal to cmd.c's value.
"""
import re
from pathlib import Path

ENGINE_CMD_BUFFER = 32768
CMD_C = Path(__file__).resolve().parents[1] / 'engine/aga/src/cmd.c'


def engine_buffer(path=CMD_C):
    """The command buffer size cmd.c's Cbuf_Init allocates (SZ_Alloc (&cmd_text, N))."""
    found = re.search(r'SZ_Alloc\s*\(\s*&cmd_text\s*,\s*(\d+)\s*\)', Path(path).read_text(encoding='utf-8'))
    if not found:
        raise ValueError('%s: no SZ_Alloc (&cmd_text, N) in Cbuf_Init' % path)
    return int(found.group(1))


def check(id1, buffer=ENGINE_CMD_BUFFER):
    """Refuse an image whose boot .cfg files would not fit the command buffer with room to spare (each under half of
    it). Prints one line and returns {name: bytes} of the files checked."""
    sizes = {p.name: p.stat().st_size for p in sorted(Path(id1).glob('*.cfg'))}
    over = {name: size for name, size in sizes.items() if size >= buffer // 2}
    if over:
        raise ValueError('boot config over half of the engine command buffer (%d bytes; a file that does not fit is '
                         'dropped whole, CFG-OVER-COMMAND-BUFFER-68): %s' % (
                             buffer, ', '.join('%s %d bytes' % item for item in sorted(over.items()))))
    print('Boot configs: %s; each under half of the engine command buffer (%d bytes)' % (
        ', '.join('%s %d bytes' % item for item in sorted(sizes.items())) or 'none', buffer), flush=True)
    return sizes
