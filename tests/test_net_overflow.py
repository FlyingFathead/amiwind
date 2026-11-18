# SPDX-License-Identifier: GPL-3.0-only
"""A frame's message from the game's server to its screen side never runs past its buffer, and a message that still
does not read never ends the game (NET-VIVEC-ENTITY-PACKET-OVERFLOW-66, critical; the maintainer's stop on the Bitter
Coast in v0.0.66, "SZ_GetSpace: overflow" then "Illegible server message").

The server (tests/aga_netsend_test.c, on the real sv_main.c and common.c): 600 things in sight with the largest update
there is fill the message far past its size; every update is built whole first and goes in only where it fits, the
nearest first, the rest in the next frames; the game's own connection takes up to 8 KB and keeps room for the reliable
message; an overflow that still happens is caught and that message dropped whole. The old rule is shown to overflow.
The screen side (tests/aga_netparse_test.c, on the real cl_parse.c): a frame's update cut short or unreadable is dropped
with one console line; a reliable message that does not read still ends the session (Host_Error: the way back or the
place loaded again, aw_scene.c AW_SceneHostError). Here: the wiring the fixtures leave out."""
import os
import re
import shutil
import unittest
from pathlib import Path

import test_aga_native_source as native

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'engine' / 'aga' / 'src'
UBSAN = ['-fsanitize=undefined', '-fno-sanitize-recover=all']


def code(name):
    return (SRC / name).read_text(encoding='utf-8', errors='replace')


def strip_comments(text):
    return re.sub(r'/\*.*?\*/', '', text, flags=re.S)


def body(text, head):
    start = text.index(head)
    return text[start:text.index('\n}\n', start)]


@unittest.skipIf(os.name == 'nt', 'native fixtures run on Linux, including the Docker gate')
@unittest.skipUnless(shutil.which('cc'), 'a host C compiler is required')
class Native(unittest.TestCase):
    def test_the_server_never_runs_past_the_buffer(self):
        native.NativeSourceTests().compile_run('aga_netsend_test.c', [SRC / 'common.c', SRC / 'mathlib.c'],
                                               cflags=UBSAN)

    def test_the_screen_side_drops_a_frame_update_that_does_not_read(self):
        native.NativeSourceTests().compile_run('aga_netparse_test.c', [SRC / 'common.c', SRC / 'mathlib.c'],
                                               cflags=UBSAN)


class Wiring(unittest.TestCase):
    def test_the_largest_update_comes_from_the_format(self):
        server = code('sv_main.c')
        line = next(l for l in server.splitlines() if l.startswith('#define AW_NETSEND_RECORD_MAX'))
        self.assertIn('AW_COORD_BYTES', line)
        self.assertIn('sizeof(float)', line)
        self.assertIn('#error', code('aw_netsend.inc'))      # never a literal of its own
        write = strip_comments(body(server, 'void SV_WriteEntitiesToClient (edict_t'))
        # built whole first, then copied in only where it fits; no update is written into the message directly
        self.assertNotIn('SV_WriteEntityUpdate (', write)
        self.assertIn('bytes = SV_EntityUpdateRecord (ent, e, record);', write)
        self.assertIn('if (!over && used + bytes <= budget)', write)
        self.assertNotIn('Con_Printf ("packet overflow', server)

    def test_every_message_buffer_allows_its_overflow_explicitly_and_it_is_caught(self):
        for name, head in (('sv_main.c', 'qboolean SV_SendClientDatagram (client_t *client)'),
                           ('sv_main.c', 'void SV_SendNop (client_t *client)'),
                           ('sv_main.c', 'void SV_SendReconnect (void)'),
                           ('sv_main.c', 'static int SV_EntityUpdateRecord (edict_t *ent, int e, byte *out)'),
                           ('cl_input.c', 'void CL_SendMove (usercmd_t *cmd)'),
                           ('host.c', 'void Host_ShutdownServer(qboolean crash)')):
            text = strip_comments(body(code(name), head))
            self.assertRegex(text, r'\.allowoverflow = true;', head)
            self.assertRegex(text, r'memset \(&\w+, 0, sizeof\(\w+\)\);', head)
        spawn = strip_comments(code('sv_main.c'))
        self.assertIn('sv.datagram.allowoverflow = sv.reliable_datagram.allowoverflow = sv.signon.allowoverflow = true;',
                      spawn)
        self.assertIn('cls.message.allowoverflow = true;', code('cl_main.c'))
        # where each is sent, an overflowed one is never sent from its middle
        send = strip_comments(body(code('sv_main.c'), 'qboolean SV_SendClientDatagram (client_t *client)'))
        self.assertLess(send.index('if (msg.overflowed)'), send.index('NET_SendUnreliableMessage'))
        self.assertIn('if (!sv.datagram.overflowed && msg.cursize + sv.datagram.cursize < msg.maxsize)', send)
        reliable = strip_comments(body(code('sv_main.c'), 'void SV_UpdateToReliableMessages (void)'))
        self.assertIn('if (sv.reliable_datagram.overflowed)', reliable)
        self.assertIn('sv.datagram.overflowed = false;', body(code('sv_main.c'), 'void SV_ClearDatagram (void)'))
        self.assertIn('if (sv.signon.overflowed)', strip_comments(code('sv_main.c')))
        self.assertIn('if (cls.message.overflowed)', strip_comments(body(code('cl_main.c'), 'void CL_SendCmd (void)')))
        self.assertIn('if (buf.overflowed)', strip_comments(body(code('cl_input.c'), 'void CL_SendMove (usercmd_t *cmd)')))

    def test_nothing_of_this_kind_stops_the_game(self):
        # the game's own player is never dropped for an overflowed reliable message: Host_Error, the place again
        clients = strip_comments(body(code('sv_main.c'), 'void SV_SendClientMessages (void)'))
        local = clients.index('if (!Q_strcmp (host_client->netconnection->address, "LOCAL"))')
        self.assertLess(local, clients.index('Host_Error ("The reliable message to the screen side overflowed'))
        self.assertNotIn('Sys_Error', strip_comments(body(code('net_loop.c'), 'int Loop_SendMessage (qsocket_t *sock, sizebuf_t *data)')))
        self.assertNotIn('Sys_Error ("CL_ParseTEnt', code('cl_tent.c'))
        parse = strip_comments(code('cl_parse.c'))
        self.assertNotIn('Host_Error ("CL_ParseServerMessage: Illegible', parse)
        self.assertNotIn('Sys_Error ("i >= cl.maxclients")', parse)
        self.assertIn('cl_message_unreliable = ret == 2;', code('cl_main.c'))
        # Host_Error in play: the place loads again and the box says why (aw_scene.c)
        self.assertIn('AW_SceneHostError (string);', code('host.c'))
        self.assertIn('play_spot_take(p);', code('aw_scene.c'))

    def test_the_test_aid_and_its_documentation(self):
        self.assertIn('Cmd_AddCommand ("aw_netstat", SV_NetStat_f);', code('sv_main.c'))
        catalogue = (ROOT / 'config' / 'debug-commands.txt').read_text(encoding='utf-8')
        self.assertTrue(any(l.startswith('PLAYTESTING|netstat|aw_netstat|') for l in catalogue.splitlines()))
        page = (ROOT / 'docs' / 'NET_MESSAGES.md').read_text(encoding='utf-8')
        for word in ('MAX_DATAGRAM', '8192', 'dbg netstat', 'nearest', 'LF9'):
            self.assertIn(word, page)


if __name__ == '__main__':
    unittest.main()
