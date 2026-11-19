/* SPDX-License-Identifier: GPL-2.0-or-later
 * NET-VIVEC-ENTITY-PACKET-OVERFLOW-66: a frame's message from the game's server to its screen side, on the real server
 * code (sv_main.c SV_WriteEntitiesToClient, SV_SendClientDatagram, included here for its static parts) with the real
 * message writers and readers (common.c) and the game's own connection (net_loop.c). The datagram is filled far past
 * its size (600 things in sight, each with the largest update there is) and must never overflow: everything that goes
 * in reads back whole, the creatures and the nearest go first, nothing waits more than a few frames. On the game's own
 * connection the room comes from the settings (aw_net_frame), a frame that wants more than three quarters of it grows
 * the room and the buffers for the next frame (which then goes whole), a raised setting counts from the next frame,
 * the room keeps space for the reliable message, at aw_net_max the nearest go first with no overflow, and PACED keeps
 * to its budget (aw_net_send); a network packet stays at 1024 bytes. An overflow that still happens is caught, said
 * once and not sent. The old rule (16 bytes left before an update of up to 28) is shown to run past the buffer, as in
 * the maintainer's stop on the Bitter Coast. Sys_Error and Host_Error stop the test.
 */
#include "../engine/aga/src/sv_main.c"
#include <assert.h>
extern qsocket_t *loop_client;
double cl_net_parse_last, cl_net_parse_sum, cl_net_parse_max;	/* cl_main.c's, read by dbg netstat */
int cl_net_parse_frames;

/* common.c's byte order (COM_Init sets it in the game) */
extern short ShortNoSwap (short l);
extern int LongNoSwap (int l);
extern float FloatNoSwap (float f);
/* ---- what sv_main.c reaches outside itself, as small stand-ins ---- */
int pr_edict_size;
dprograms_t *progs;
char *pr_strings;
globalvars_t *pr_global_struct;
double realtime = 100;
client_t *host_client;
qboolean noclip_anglehack;
edict_t *EDICT_NUM (int n) {assert (n >= 0 && n < sv.max_edicts); return (edict_t *)((byte *)sv.edicts + n * pr_edict_size);}
int NUM_FOR_EDICT (edict_t *e) {return (int)(((byte *)e - (byte *)sv.edicts) / pr_edict_size);}
static ddef_t scale_field;
ddef_t *ED_FindField (char *name) {return strcmp (name, "aw_scale") ? NULL : &scale_field;}
eval_t *GetEdictFieldValue (edict_t *ed, char *field) {(void)ed; (void)field; return NULL;}
void SV_SetIdealPitch (void) {}
void SV_DropClient (qboolean crash) {(void)crash; fprintf (stderr, "SV_DropClient\n"); abort ();}
static byte all_visible[MAX_MAP_LEAFS / 8];
byte *Mod_LeafPVS (mleaf_t *leaf, model_t *model) {(void)leaf; (void)model; return all_visible;}
void Sys_Error (char *error, ...) {va_list a; va_start (a, error); vfprintf (stderr, error, a); va_end (a); fputc ('\n', stderr); abort ();}
void Host_Error (char *error, ...) {va_list a; va_start (a, error); vfprintf (stderr, error, a); va_end (a); fputc ('\n', stderr); abort ();}
static int printed;
void Con_Printf (char *fmt, ...) {(void)fmt; printed++;}
void Con_DPrintf (char *fmt, ...) {(void)fmt;}
static sizebuf_t sent;
static byte sent_data[262144];
static int sends;
int NET_SendUnreliableMessage (qsocket_t *sock, sizebuf_t *data)
{
    (void)sock;
    assert (!data->overflowed && data->cursize <= data->maxsize);
    memcpy (sent_data, data->data, data->cursize);
    sent.data = sent_data; sent.cursize = data->cursize; sent.maxsize = data->maxsize;
    sends++;
    return 1;
}

/* ---- a world of N things in sight, each with the largest update ---- */
#define THINGS 600
#define ACTORS 590	/* entities 590-599 are creatures (moving by steps), 3000 units away */
static model_t alias_model, brush_model;
static void world (int n, int scaled)
{
    int e;
    static byte edict_memory[THINGS * sizeof (edict_t)];
    static char strings[16] = "\0models/x.mdl";
    static mleaf_t leaf;
    static model_t worldmodel;
    static dprograms_t loaded;
    static globalvars_t globals;
    pr_global_struct = &globals;
    memset (&sv, 0, sizeof (sv));
    memset (edict_memory, 0, sizeof (edict_memory));
    progs = &loaded;	/* a loaded game program: SV_AliasScale looks its aw_scale field up */
    pr_edict_size = sizeof (edict_t);
    pr_strings = strings;
    sv.edicts = (edict_t *)edict_memory;
    sv.max_edicts = THINGS;
    sv.num_edicts = n;
    sv.active = true;
    strcpy (sv.name, "test");
    leaf.contents = CONTENTS_EMPTY;
    worldmodel.numleafs = 1;
    worldmodel.nodes = (mnode_t *)&leaf;
    sv.worldmodel = &worldmodel;
    alias_model.type = mod_alias;
    brush_model.type = mod_brush;
    sv.models[2] = &alias_model;
    sv.models[3] = &brush_model;
    sv.model_precache[2] = "progs/x.mdl";
    scale_field.type = ev_float;
    scale_field.ofs = (unsigned short)(offsetof (entvars_t, ltime) / sizeof (float));
    for (e = 1; e < n; e++)
    {
        edict_t *ent = EDICT_NUM (e);
        ent->num_leafs = MAX_ENT_LEAFS;	/* in too many leafs to list: always in sight */
        ent->v.model = 1;
        ent->v.modelindex = scaled ? 2 : 3;
        ent->baseline.modelindex = 1;
        /* far apart and each at its own distance from the player (edict 1, at the origin): 3-byte coordinates */
        ent->v.origin[0] = 5000 + e * 37.0f;
        ent->v.origin[1] = -3000 - e * 11.0f;
        ent->v.origin[2] = 100 + e;
        ent->v.angles[0] = 10; ent->v.angles[1] = 20; ent->v.angles[2] = 30;
        ent->v.frame = scaled ? 300 : 5;
        ent->v.colormap = 1; ent->v.skin = 2; ent->v.effects = 4;
        ent->v.ltime = scaled ? 2.0f : 1.0f;	/* the aw_scale field of this test */
        if (e >= ACTORS)
        {
            /* the creatures a town joins last: the highest entity numbers, the ones the old loop always left out */
            ent->v.movetype = MOVETYPE_STEP;
            ent->v.origin[0] = 3000 + e;
            ent->v.origin[1] = 0;
        }
    }
    EDICT_NUM (1)->v.origin[0] = EDICT_NUM (1)->v.origin[1] = EDICT_NUM (1)->v.origin[2] = 0;
    EDICT_NUM (1)->v.v_angle[1] = 0;	/* looking along +x: the things are in front */
    memset (sv_net_missed, 0, sizeof (sv_net_missed));
    memset (&sv_net, 0, sizeof (sv_net));
    memset (&sv_net_grown, 0, sizeof (sv_net_grown));
    sv_frame_room = sv_frame_grow = 0;	/* a new map: the room starts again from aw_net_frame */
}

/* ---- the entity updates read back with the real readers; returns how many, fills SEEN ---- */
extern sizebuf_t net_message;
sizebuf_t net_message;
static int read_back (const sizebuf_t *msg, int start, unsigned char *seen)
{
    int count = 0;
    net_message.data = msg->data;
    net_message.cursize = msg->cursize;
    net_message.maxsize = msg->maxsize;
    MSG_BeginReading ();
    msg_readcount = start;
    while (msg_readcount < net_message.cursize)
    {
        int bits = MSG_ReadByte (), num, aw;
        assert (bits & U_SIGNAL);
        bits &= 127;
        if (bits & U_MOREBITS)
            bits |= MSG_ReadByte () << 8;
        num = bits & U_LONGENTITY ? MSG_ReadShort () : MSG_ReadByte ();
        assert (num > 0 && num < THINGS && !seen[num]);
        seen[num] = 1;
        if (bits & U_MODEL) assert (MSG_ReadModel () == (int)EDICT_NUM (num)->v.modelindex);
        if (bits & U_FRAME) MSG_ReadByte ();
        if (bits & U_COLORMAP) assert (MSG_ReadByte () == 1);
        if (bits & U_SKIN) assert (MSG_ReadByte () == 2);
        if (bits & U_EFFECTS) assert (MSG_ReadByte () == 4);
        if (bits & U_ORIGIN1) assert (fabs (MSG_ReadCoord () - EDICT_NUM (num)->v.origin[0]) < 1);
        if (bits & U_ANGLE1) MSG_ReadAngle ();
        if (bits & U_ORIGIN2) assert (fabs (MSG_ReadCoord () - EDICT_NUM (num)->v.origin[1]) < 1);
        else assert (EDICT_NUM (num)->v.origin[1] == 0);
        if (bits & U_ANGLE2) MSG_ReadAngle ();
        if (bits & U_ORIGIN3) assert (fabs (MSG_ReadCoord () - EDICT_NUM (num)->v.origin[2]) < 1);
        if (bits & U_ANGLE3) MSG_ReadAngle ();
        if (bits & U_AW_EXT)
        {
            aw = MSG_ReadByte ();
            if (aw & AWU_SCALE) assert (MSG_ReadFloat () == 2.0f);
            if (aw & AWU_FRAME2) assert (MSG_ReadByte () == 1);
        }
        assert (!msg_badread);
        count++;
    }
    assert (msg_readcount == net_message.cursize);
    return count;
}

/* the rules alone (aw_netsend.inc) */
static void rules (void)
{
    aw_netsend_t c[4];
    unsigned char send[4];
    /* nearer first; actors before scenery within 8192 units; behind after everything in front within 16384 units;
     * a waiting one moves forward */
    assert (AW_NetSendKey (100, 0, 0, 0) < AW_NetSendKey (200, 0, 0, 0));
    assert (AW_NetSendKey (5000, 0, 0, 0) < AW_NetSendKey (100, 0, 1, 0));
    assert (AW_NetSendKey (5000, 0, 0, 0) < AW_NetSendKey (100, 1, 0, 0));
    assert (AW_NetSendKey (100, 1, 0, 5) < AW_NetSendKey (100, 0, 0, 0));
    assert (AW_NetSendKey (-5, 0, 0, 0) == 0 && AW_NetSendKey (1e9f, 0, 0, 0) == 60000);
    assert (AW_NetSendKey (0, 0, 0, 1000) == AW_NetSendKey (0, 0, 0, AW_NETSEND_MISSED_MAX));
    assert (AW_NetSendKey (60000, 1, 1, 21) < AW_NetSendKey (0, 0, 0, 0));	/* the farthest after 21 frames: first */
    /* all fit: none moved, all sent */
    c[0].e = 3; c[0].bytes = 10; c[0].key = 50; c[1].e = 4; c[1].bytes = 10; c[1].key = 10;
    assert (AW_NetSendChoose (c, 2, 20, send) == 20 && send[0] && send[1] && c[0].e == 3);
    /* over: by key; a larger one left out, a smaller later one still in; never past the budget */
    c[0].e = 1; c[0].bytes = 6; c[0].key = AW_NETSEND_FIRST;
    c[1].e = 9; c[1].bytes = 28; c[1].key = 900;
    c[2].e = 5; c[2].bytes = 20; c[2].key = 100;
    c[3].e = 7; c[3].bytes = 8; c[3].key = 950;
    assert (AW_NetSendChoose (c, 4, 40, send) == 34);
    assert (c[0].e == 1 && send[0] && c[1].e == 5 && send[1] && c[2].e == 9 && !send[2] && c[3].e == 7 && send[3]);
}

/* the old rule: stop once fewer than 16 bytes are left; the largest update then runs past a 1024-byte buffer */
static void old_rule (void)
{
    byte data[MAX_DATAGRAM];
    sizebuf_t msg;
    int e, start, overflowed = 0;
    world (THINGS, 1);
    /* the frame's time and the player's data come first and take a few dozen bytes, a different number each frame */
    for (start = 0; start < 40; start++)
    {
        memset (&msg, 0, sizeof (msg));
        msg.data = data; msg.maxsize = sizeof (data); msg.allowoverflow = true;
        msg.cursize = start;
        for (e = 1; e < THINGS; e++)
        {
            if (msg.maxsize - msg.cursize < 16 + 1 + 4 + 1)	/* the old reserve with the AmiWind fields */
                break;
            SV_WriteEntityUpdate (EDICT_NUM (e), e, &msg);
            if (msg.overflowed)
                break;
        }
        overflowed += msg.overflowed;
    }
    /* "SZ_GetSpace: overflow": the message was cleared and written on from the middle of an update */
    printf ("the old rule ran past the 1024 bytes for %d of 40 starting sizes\n", overflowed);
    assert (overflowed > 0);
}

#define LOOP_ROOM 8192
int main (void)
{
    byte data[LOOP_ROOM];
    sizebuf_t msg;
    unsigned char seen[THINGS];
    int frame, e, n, wait[THINGS], longest;
    qsocket_t local, peer, remote;
    client_t client;

    LittleLong = LongNoSwap; LittleShort = ShortNoSwap; LittleFloat = FloatNoSwap;	/* as COM_Init on this host */
    rules ();
    old_rule ();
    assert (SV_EntityUpdateBytes (EDICT_NUM (2), 300) == AW_NETSEND_RECORD_MAX);	/* the largest update there is */

    /* a 1024-byte packet and an 8 KB one, 600 things with the largest update: never past the buffer, all legible,
     * the nearest first, the player always */
    for (n = 0; n < 2; n++)
    {
        world (THINGS, 1);
        memset (&msg, 0, sizeof (msg));
        msg.data = data; msg.maxsize = n ? LOOP_ROOM : MAX_DATAGRAM;	/* allowoverflow off: Sys_Error */
        SV_WriteEntitiesToClient (EDICT_NUM (1), &msg);
        assert (msg.cursize <= msg.maxsize && !msg.overflowed);
        memset (seen, 0, sizeof (seen));
        e = read_back (&msg, 0, seen);
        assert (seen[1] && e == sv_net.sent && sv_net.deferred == THINGS - 1 - e && sv_net.deferred > 0);
        assert (sv_net.wanted > msg.maxsize && sv_net.sent_bytes == msg.cursize);
        /* the creatures first, though they are the highest numbers (OUTDOOR-CREATURES-REGRESSION-66) */
        for (e = ACTORS; e < THINGS; e++)
            assert (seen[e]);
        /* then the nearest scenery: every one sent is nearer than every one left (farther with its number) */
        for (frame = 0, e = 2; e < ACTORS; e++)
        {
            if (!seen[e]) frame = 1;
            assert (!(frame && seen[e]));
        }
        printf ("%s: %d of %d updates in %d of %d bytes (all of them want %d)\n", n ? "loopback" : "packet",
                sv_net.sent, sv_net.candidates, msg.cursize, msg.maxsize, sv_net.wanted);
    }

    /* frame after frame on a 1024-byte packet: every update goes out within a few frames */
    world (THINGS, 1);
    memset (wait, 0, sizeof (wait));
    for (longest = 0, frame = 0; frame < 120; frame++)
    {
        memset (&msg, 0, sizeof (msg));
        msg.data = data; msg.maxsize = MAX_DATAGRAM;
        SV_WriteEntitiesToClient (EDICT_NUM (1), &msg);
        memset (seen, 0, sizeof (seen));
        read_back (&msg, 0, seen);
        for (e = 1; e < THINGS; e++)
        {
            wait[e] = seen[e] ? 0 : wait[e] + 1;
            if (wait[e] > longest) longest = wait[e];
        }
    }
    /* about 36 of the 599 largest updates fit a packet: 17 frames send each one once; the nearest go more often */
    printf ("the longest wait over 120 frames: %d frames\n", longest);
    assert (longest <= 17 + 8);

    /* the whole frame message on the game's own connection (FULL): the room from aw_net_frame (8192 here); a frame of
     * about 13 KB wants more than three quarters of it, so the room and the buffers grow for the next frame, which
     * goes whole */
    world (THINGS, 0);
    memset (&client, 0, sizeof (client));
    memset (&local, 0, sizeof (local)); memset (&peer, 0, sizeof (peer)); memset (&remote, 0, sizeof (remote));
    strcpy (local.address, "LOCAL");
    local.driverdata = &peer;
    loop_client = &peer;
    client.netconnection = &local;
    client.edict = EDICT_NUM (1);
    client.message.data = data; client.message.maxsize = 1;	/* only its size is read */
    aw_net_method.value = 1; aw_net_send.value = 4096;
    aw_net_frame.value = 8192; aw_net_buffer.value = 16384; aw_net_max.value = 262144;
    e = printed;
    assert (SV_SendClientDatagram (&client) && sends == 1);
    assert (sent.cursize > MAX_DATAGRAM && sent.cursize <= 8192 && sv_net.deferred > 0);
    assert (sv_net_grown.count == 1 && sv_net_grown.from == 8192 && sv_net_grown.to == 32768 && printed == e + 2);
    assert (SV_SendClientDatagram (&client) && sends == 2);
    assert (sv_frame_room == 32768 && sv_net.deferred == 0 && sent.cursize > 8192);	/* the whole frame */
    assert (Loop_ReceiveSize () >= 32768 + MAX_MSGLEN && net_message.maxsize >= 32768 && sv_net_grown.count == 1);
    printf ("FULL: a frame of %d bytes grew the room from 8192 to %d and went whole the next frame\n", sent.cursize,
            sv_frame_room);
    /* a raised setting counts from the next frame; nothing shrinks during a map */
    aw_net_frame.value = 65536;
    assert (SV_SendClientDatagram (&client) && sv_frame_room == 65536 && sv_frame_size >= 65536);
    aw_net_frame.value = 8192;
    assert (SV_SendClientDatagram (&client) && sv_frame_room == 65536);
    /* the room keeps space for what the client has not read and this frame's reliable message */
    peer.receiveMessageLength = Loop_ReceiveSize () - 3000;
    client.message.cursize = 1000;
    assert (SV_SendClientDatagram (&client) && sent.cursize <= 3000 - 1004 - 16);
    /* full: the frame message overflows its 16 bytes; caught, said once, dropped whole (never sent from its middle) */
    peer.receiveMessageLength = Loop_ReceiveSize ();
    client.message.cursize = 0;
    n = sends; e = printed;
    assert (SV_SendClientDatagram (&client));
    printf ("full buffer: sends %d, dropped %d, console lines %d\n", sends - n, sv_net.dropped, printed - e);
    assert (sends == n && sv_net.dropped == 1 && printed == e + 1);
    assert (SV_SendClientDatagram (&client) && sends == n && sv_net.dropped == 2 && printed == e + 1);
    peer.receiveMessageLength = 0;

    /* at aw_net_max the room does not grow: the nearest go first, nothing past the buffer, said once */
    world (THINGS, 0);
    aw_net_frame.value = 8192; aw_net_max.value = 8192;
    e = printed;
    assert (SV_SendClientDatagram (&client) && SV_SendClientDatagram (&client));
    assert (sv_frame_room == 8192 && sent.cursize <= 8192 && sv_net.deferred > 0 && sv_net_grown.count == 0);
    assert (sv_net_grown.at_max && printed == e + 2);	/* the room ran short once (FULL), the largest room once */
    aw_net_max.value = 262144;

    /* PACED keeps to its budget, the nearest first; it never grows the room for what it would not send */
    world (THINGS, 0);
    aw_net_method.value = 2; aw_net_send.value = 4096; aw_net_frame.value = 32768;
    assert (SV_SendClientDatagram (&client) && sent.cursize <= 4096 + 64 && sv_net.deferred > 0);
    assert (sv_net_grown.count == 0 && sv_frame_room == 32768);
    for (e = ACTORS; e < THINGS; e++)
        assert (!sv_net_missed[e]);	/* the creatures went */
    printf ("PACED: %d of %d updates in %d bytes, budget 4096\n", sv_net.sent, sv_net.candidates, sent.cursize);
    aw_net_method.value = 1;

    /* a network client keeps a packet's size */
    strcpy (remote.address, "192.168.1.2");
    client.netconnection = &remote;
    assert (SV_SendClientDatagram (&client) && sent.cursize <= MAX_DATAGRAM);
    return 0;
}
