/*
Copyright (C) 1996-1997 Id Software, Inc.

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.

See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.

*/
// sv_main.c -- server main program

#include "quakedef.h"
#include "aw_mappath.h"
#include "aw_anim.h"
#include "aw_animpick.h"
#include "amiwind_version.h"
#include "aw_spike.h"
#include "aw_ambient.h"
#include "aw_items.h"
#include "aw_tryalloc.h"	/* the frame buffer: an allocation that can say no (the Amiga's malloc traps instead) */
/* aw_actors.c: every server spawn is a new map for the actors, the same map's name too (ACTOR-TABLE-SAME-MAP-RELOAD-67).
 * Declared here, not in aw_actors.h: the CHIM world stage keys that header, and this fix must move no world stage key. */
void AW_ActorsServerReset (void);
/* aw_combat.c: the fights' edict pointers of the old server go (GAENOR-ATTACKS-AT-START-67). Declared here, not in
 * aw_combat.h, for the same reason: the CHIM world stage keys that header. */
void AW_CombatServerReset (void);
/* aw_mwhost.c: every server spawn attaches the map again for the scripts and the object state, the same map's too, so
 * the edicts of a disabled or taken reference are hidden at every load (PLAZA-FABRICANTS-LIVE-AT-START-67). Declared
 * here, not in a header a stage keys. */
void AW_MwscriptServerReset (void);

server_t		sv;
server_static_t	svs;
void (*aw_inspect_reset)(void);

char	localmodels[MAX_MODELS][5];			// inline model names for precache

//============================================================================

static void SV_NetStat_f (void);	/* dbg netstat (NET-VIVEC-ENTITY-PACKET-OVERFLOW-66) */
static cvar_t aw_net_method, aw_net_send, aw_net_frame, aw_net_buffer, aw_net_max;	/* the frame message's settings */

/*
===============
SV_Init
===============
*/
void SV_Init (void)
{
    int		i;
    extern	cvar_t	sv_maxvelocity;
    extern	cvar_t	sv_gravity;
    extern	cvar_t	sv_nostep;
    extern	cvar_t	sv_friction;
    extern	cvar_t	sv_edgefriction;
    extern	cvar_t	sv_stopspeed;
    extern	cvar_t	sv_maxspeed;
    extern	cvar_t	sv_accelerate;
    extern	cvar_t	sv_idealpitchscale;
    extern	cvar_t	sv_aim;

    Cvar_RegisterVariable (&sv_maxvelocity);
    Cvar_RegisterVariable (&sv_gravity);
    Cvar_RegisterVariable (&sv_friction);
    Cvar_RegisterVariable (&sv_edgefriction);
    Cvar_RegisterVariable (&sv_stopspeed);
    Cvar_RegisterVariable (&sv_maxspeed);
    Cvar_RegisterVariable (&sv_accelerate);
    Cvar_RegisterVariable (&sv_idealpitchscale);
    Cvar_RegisterVariable (&sv_aim);
    Cvar_RegisterVariable (&sv_nostep);
    Cvar_RegisterVariable (&aw_step_rules);	/* aw_walk.c, docs/STEP_MOVEMENT.md (default 0) */
    Cvar_RegisterVariable (&aw_body_overlap);	/* world.c, DOOR-ARRIVAL-INSIDE-ACTOR-66 (default 1) */
    Cmd_AddCommand ("aw_netstat", SV_NetStat_f);
    Cvar_RegisterVariable (&aw_net_method);	/* the frame message (NET-VIVEC-ENTITY-PACKET-OVERFLOW-66), saved */
    Cvar_RegisterVariable (&aw_net_send);
    Cvar_RegisterVariable (&aw_net_frame);
    Cvar_RegisterVariable (&aw_net_buffer);
    Cvar_RegisterVariable (&aw_net_max);

    for (i=0 ; i<MAX_MODELS ; i++)
        sprintf (localmodels[i], "*%ld", (long)i);
}

/*
=============================================================================

EVENT MESSAGES

=============================================================================
*/

/*
==================
SV_StartParticle

Make sure the event gets sent to all clients
==================
*/
void SV_StartParticle (vec3_t org, vec3_t dir, int color, int count)
{
    int		i, v;

    if (sv.datagram.cursize > MAX_DATAGRAM-16)
        return;
    MSG_WriteByte (&sv.datagram, svc_particle);
    MSG_WriteCoord (&sv.datagram, org[0]);
    MSG_WriteCoord (&sv.datagram, org[1]);
    MSG_WriteCoord (&sv.datagram, org[2]);
    for (i=0 ; i<3 ; i++)
    {
        v = dir[i]*16;
        if (v > 127)
            v = 127;
        else if (v < -128)
            v = -128;
        MSG_WriteChar (&sv.datagram, v);
    }
    MSG_WriteByte (&sv.datagram, count);
    MSG_WriteByte (&sv.datagram, color);
}

/*
==================
SV_StartSound

Each entity can have eight independant sound sources, like voice,
weapon, feet, etc.

Channel 0 is an auto-allocate channel, the others override anything
allready running on that entity/channel pair.

An attenuation of 0 will play full volume everywhere in the level.
Larger attenuations will drop off.  (max 4 attenuation)

==================
*/
void SV_StartSound (edict_t *entity, int channel, char *sample, int volume,
    float attenuation)
{
    int         sound_num;
    int field_mask;
    int			i;
    int			ent;

    if (volume < 0 || volume > 255)
        Sys_Error ("SV_StartSound: volume = %d", volume);

    if (attenuation < 0 || attenuation > 4)
        Sys_Error ("SV_StartSound: attenuation = %f", attenuation);

    if (channel < 0 || channel > 7)
        Sys_Error ("SV_StartSound: channel = %d", channel);

    if (sv.datagram.cursize > MAX_DATAGRAM-16)
        return;

// find precache number for sound
    for (sound_num=1 ; sound_num<MAX_SOUNDS
        && sv.sound_precache[sound_num] ; sound_num++)
        if (!strcmp(sample, sv.sound_precache[sound_num]))
            break;

    if ( sound_num == MAX_SOUNDS || !sv.sound_precache[sound_num] )
    {
        Con_Printf ("SV_StartSound: %s not precacheed\n", sample);
        return;
    }

    ent = NUM_FOR_EDICT(entity);

    channel = (ent<<3) | channel;

    field_mask = 0;
    if (volume != DEFAULT_SOUND_PACKET_VOLUME)
        field_mask |= SND_VOLUME;
    if (attenuation != DEFAULT_SOUND_PACKET_ATTENUATION)
        field_mask |= SND_ATTENUATION;

// directed messages go only to the entity the are targeted on
    MSG_WriteByte (&sv.datagram, svc_sound);
    MSG_WriteByte (&sv.datagram, field_mask);
    if (field_mask & SND_VOLUME)
        MSG_WriteByte (&sv.datagram, volume);
    if (field_mask & SND_ATTENUATION)
        MSG_WriteByte (&sv.datagram, attenuation*64);
    MSG_WriteShort (&sv.datagram, channel);
    MSG_WriteByte (&sv.datagram, sound_num);
    for (i=0 ; i<3 ; i++)
        MSG_WriteCoord (&sv.datagram, entity->v.origin[i]+0.5*(entity->v.mins[i]+entity->v.maxs[i]));
}

/*
==============================================================================

CLIENT SPAWNING

==============================================================================
*/

/*
================
SV_SendServerinfo

Sends the first message from the server to a connected client.
This will be sent on the initial connection and upon each server load.
================
*/
void SV_SendServerinfo (client_t *client)
{
    char			**s;
    char			message[2048];

    MSG_WriteByte (&client->message, svc_print);
    // AmiWind: the game and CHIM versions first, then the AmiQuake line and the help line
    sprintf (message, "%c\n" AMIWIND_TITLE "\n" AMIQUAKE_VERSION_LINE_OF (VERSION) " SERVER (%ld CRC)\n"
             AW_CONSOLE_HELP_LINE, 2, (long)pr_crc);
    MSG_WriteString (&client->message,message);

    MSG_WriteByte (&client->message, svc_serverinfo);
    MSG_WriteLong (&client->message, PROTOCOL_VERSION);
    MSG_WriteByte (&client->message, svs.maxclients);

    if (!coop.value && deathmatch.value)
        MSG_WriteByte (&client->message, GAME_DEATHMATCH);
    else
        MSG_WriteByte (&client->message, GAME_COOP);

    /* the map text is data, never a format (ENGINE-ENTITY-TEXT-UNBOUNDED-35) */
    Q_snprintf (message, sizeof(message), "%s", pr_strings+sv.edicts->v.message);

    MSG_WriteString (&client->message,message);

    for (s = sv.model_precache+1 ; *s ; s++)
        MSG_WriteString (&client->message, *s);
    MSG_WriteByte (&client->message, 0);

    for (s = sv.sound_precache+1 ; *s ; s++)
        MSG_WriteString (&client->message, *s);
    MSG_WriteByte (&client->message, 0);

// send music
    MSG_WriteByte (&client->message, svc_cdtrack);
    MSG_WriteByte (&client->message, sv.edicts->v.sounds);
    MSG_WriteByte (&client->message, sv.edicts->v.sounds);

// set view
    MSG_WriteByte (&client->message, svc_setview);
    MSG_WriteShort (&client->message, NUM_FOR_EDICT(client->edict));

    MSG_WriteByte (&client->message, svc_signonnum);
    MSG_WriteByte (&client->message, 1);

    client->sendsignon = true;
    client->spawned = false;		// need prespawn, spawn, etc
}

/*
================
SV_ConnectClient

Initializes a client_t for a new net connection.  This will only be called
once for a player each game, not once for each level change.
================
*/
void SV_ConnectClient (int clientnum)
{
    edict_t			*ent;
    client_t		*client;
    int				edictnum;
    struct qsocket_s *netconnection;
    int				i;
    float			spawn_parms[NUM_SPAWN_PARMS];

    client = svs.clients + clientnum;

    Con_DPrintf ("Client %s connected\n", client->netconnection->address);

    edictnum = clientnum+1;

    ent = EDICT_NUM(edictnum);

// set up the client_t
    netconnection = client->netconnection;

    if (sv.loadgame)
        memcpy (spawn_parms, client->spawn_parms, sizeof(spawn_parms));
    memset (client, 0, sizeof(*client));
    client->netconnection = netconnection;

    strcpy (client->name, "unconnected");
    client->active = true;
    client->spawned = false;
    client->edict = ent;
    client->message.data = client->msgbuf;
    client->message.maxsize = sizeof(client->msgbuf);
    client->message.allowoverflow = true;		// we can catch it

#ifdef IDGODS
    client->privileged = IsID(&client->netconnection->addr);
#else
    client->privileged = false;
#endif

    if (sv.loadgame)
        memcpy (client->spawn_parms, spawn_parms, sizeof(spawn_parms));
    else
    {
    // call the progs to get default spawn parms for the new client
        PR_ExecuteProgram (pr_global_struct->SetNewParms);
        for (i=0 ; i<NUM_SPAWN_PARMS ; i++)
            client->spawn_parms[i] = (&pr_global_struct->parm1)[i];
    }

    SV_SendServerinfo (client);
}


/*
===================
SV_CheckForNewClients

===================
*/
void SV_CheckForNewClients (void)
{
    struct qsocket_s	*ret;
    int				i;

//
// check for new connections
//
    while (1)
    {
        ret = NET_CheckNewConnections ();
        if (!ret)
            break;

    //
    // init a new client structure
    //
        for (i=0 ; i<svs.maxclients ; i++)
            if (!svs.clients[i].active)
                break;
        if (i == svs.maxclients)
            Sys_Error ("Host_CheckForNewClients: no free clients");

        svs.clients[i].netconnection = ret;
        SV_ConnectClient (i);

        net_activeconnections++;
    }
}



/*
===============================================================================

FRAME UPDATES

===============================================================================
*/

/*
==================
SV_ClearDatagram

==================
*/
void SV_ClearDatagram (void)
{
    SZ_Clear (&sv.datagram);
    sv.datagram.overflowed = false;	/* a frame's overflow was dropped with that frame (NET-VIVEC-ENTITY-PACKET-OVERFLOW-66) */
}

/*
=============================================================================

The PVS must include a small area around the client to allow head bobbing
or other small motion on the client side.  Otherwise, a bob might cause an
entity that should be visible to not show up, especially when the bob
crosses a waterline.

=============================================================================
*/

int		fatbytes;
byte	fatpvs[MAX_MAP_LEAFS/8];

void SV_AddToFatPVS (vec3_t org, mnode_t *node)
{
    int		i;
    byte	*pvs;
    mplane_t	*plane;
    float	d;

    while (1)
    {
    // if this is a leaf, accumulate the pvs bits
        if (node->contents < 0)
        {
            if (node->contents != CONTENTS_SOLID)
            {
                pvs = Mod_LeafPVS ( (mleaf_t *)node, sv.worldmodel);
                for (i=0 ; i<fatbytes ; i++)
                    fatpvs[i] |= pvs[i];
            }
            return;
        }

        plane = node->plane;
        d = DotProduct (org, plane->normal) - plane->dist;
        if (d > 8)
            node = node->children[0];
        else if (d < -8)
            node = node->children[1];
        else
        {	// go down both
            SV_AddToFatPVS (org, node->children[0]);
            node = node->children[1];
        }
    }
}

/*
=============
SV_FatPVS

Calculates a PVS that is the inclusive or of all leafs within 8 pixels of the
given point.
=============
*/
byte *SV_FatPVS (vec3_t org)
{
    fatbytes = (sv.worldmodel->numleafs+31)>>3;
    Q_memset (fatpvs, 0, fatbytes);
    SV_AddToFatPVS (org, sv.worldmodel->nodes);
    return fatpvs;
}

//=============================================================================


/*
=============
SV_WriteEntitiesToClient

=============
*/
ddef_t *ED_FindField (char *name);

/* The instance scale of a live alias entity (its aw_scale field; 1 when the progs have no such field, the entity
 * is no alias model or the value is not a usable scale). The field's offset is looked up once per progs. */
static float SV_AliasScale (edict_t *ent)
{
    static dprograms_t *seen;
    static int ofs = -1;
    float s;
    model_t *m;
    if (progs != seen)
    {
        ddef_t *def = ED_FindField ("aw_scale");
        seen = progs;
        ofs = def && (def->type & ~DEF_SAVEGLOBAL) == ev_float ? def->ofs : -1;
    }
    if (ofs < 0)
        return 1;
    s = ((float *)&ent->v)[ofs];
    if (!(s > 0.01f && s < 64.0f) || s == 1.0f)
        return 1;
    m = (ent->v.modelindex > 0 && ent->v.modelindex < MAX_MODELS) ? sv.models[(int)ent->v.modelindex] : NULL;
    return m && m->type == mod_alias ? s : 1;
}

/* NET-VIVEC-ENTITY-PACKET-OVERFLOW-66 (critical; the maintainer's hang of 2026-11-17 on the Bitter Coast, and Vivec
 * since v0.0.66-dev7): the entity updates of a frame no longer fit the old 1024-byte message where many things are in
 * sight (harvestable plants, residents, creatures, items). The old loop stopped at "packet overflow" once fewer than
 * 16 bytes were left, but an update takes up to 28 since the 3-byte coordinates and the 2-byte model number; the last
 * one then ran past the buffer, whose overflow flag was never set on this stack buffer: the message was cleared and
 * written on from the middle of an update ("SZ_GetSpace: overflow"), and the screen side stopped on it
 * ("CL_ParseServerMessage: Illegible server message"). Now every update is sized before it goes in (aw_netsend.inc),
 * the nearest go first and the rest in the next frames, and the game's own connection (the loopback, which never
 * leaves the machine) takes a larger message. sv_net_reserve: the bytes the caller keeps free after the entities (the
 * frame's sounds and effects, sv.datagram). */
/* The largest update of one entity, from SV_WriteEntityUpdate's format (the maintainer, 2026-11-17: sure to be caught,
 * so computed from the format, never a literal): the bits and their second byte, the entity number as a short, the
 * model as a short (protocol.h MSG_WriteModel), frame, colormap, skin and effects a byte each, three coordinates of
 * AW_COORD_BYTES (aw_coord.h), three angles of a byte, and the AmiWind fields (their byte, the scale as a float, the
 * frame's high byte): 28 bytes with 3-byte coordinates. tests/aga_netsend_test.c writes the largest update and
 * checks it is exactly this. */
#define AW_NETSEND_RECORD_MAX (1 + 1 + 2 + 2 + 4 + 3 * AW_COORD_BYTES + 3 + 1 + (int)sizeof(float) + 1)
#include "aw_netsend.inc"
static int sv_net_reserve;
static int sv_net_limit;	/* the bytes this frame's message may hold (PACED: aw_net_send; 0: the whole room) */
static unsigned char sv_net_missed[MAX_EDICTS];   /* frames each entity's update waited (cleared with a new server) */
static aw_netsend_t sv_net_cand[MAX_EDICTS];
static unsigned char sv_net_send[MAX_EDICTS];
/* dbg netstat: the last frame, and since the map started or dbg netstat reset: the fullest frame, the waits */
static struct {
    int candidates,wanted,budget,sent,sent_bytes,deferred,frames,frames_deferred,frames_over_1024,dropped;
    int worst_wanted,worst_candidates,worst_budget,worst_deferred,worst_need;
    int wait_max,waited;	/* the longest wait of an update that went out after waiting, in frames; how many did */
    double wait_sum,said;
    double frame_sum,frame_max;	/* the time from one frame message to the next, in seconds */
    int frame_n;
} sv_net;
/* an update that goes out after waiting: its wait counted for dbg netstat, then none */
static void SV_NetSent (int e)
{
    if (e >= MAX_EDICTS || !sv_net_missed[e])
        return;
    sv_net.waited++;
    sv_net.wait_sum += sv_net_missed[e];
    if (sv_net_missed[e] > sv_net.wait_max)
        sv_net.wait_max = sv_net_missed[e];
    sv_net_missed[e] = 0;
}
static void SV_WriteEntityUpdate (edict_t *ent, int e, sizebuf_t *msg);
/* One entity's update, built whole in OUT (AW_NETSEND_RECORD_MAX bytes) before it goes anywhere: its size in bytes, or
 * -1 when it would not fit there (a format that grew past the computed largest update: never written, said once). */
static int SV_EntityUpdateRecord (edict_t *ent, int e, byte *out)
{
    static qboolean said;
    sizebuf_t	scratch;
    memset (&scratch, 0, sizeof(scratch));
    scratch.data = out;
    scratch.maxsize = AW_NETSEND_RECORD_MAX;
    scratch.allowoverflow = true;	/* caught here, never Sys_Error: an overflow marks it and clears it */
    SV_WriteEntityUpdate (ent, e, &scratch);
    if (scratch.overflowed)
    {
        if (!said)
            Con_Printf ("Entity %ld: its update is larger than %ld bytes; not sent\n", (long)e, (long)AW_NETSEND_RECORD_MAX);
        said = true;
        return -1;
    }
    return scratch.cursize;
}
static int SV_EntityUpdateBytes (edict_t *ent, int e)
{
    byte record[AW_NETSEND_RECORD_MAX];
    return SV_EntityUpdateRecord (ent, e, record);
}

void SV_WriteEntitiesToClient (edict_t	*clent, sizebuf_t *msg)
{
    int		e, i, n, mark, budget, over, bytes, used;
    byte	*pvs, record[AW_NETSEND_RECORD_MAX];
    vec3_t	org, forward, right, up, dir;
    float	dist;
    edict_t	*ent;

// find the client's PVS
    VectorAdd (clent->v.origin, clent->v.view_ofs, org);
    pvs = SV_FatPVS (org);
    AngleVectors (clent->v.v_angle, forward, right, up);
    mark = msg->cursize;
    budget = (sv_net_limit > 0 && sv_net_limit < msg->maxsize ? sv_net_limit : msg->maxsize) - msg->cursize -
             sv_net_reserve;
    if (budget < 0)
        budget = 0;
    used = over = n = 0;

// send over all entities (excpet the client) that touch the pvs
    ent = NEXT_EDICT(sv.edicts);
    for (e=1 ; e<sv.num_edicts ; e++, ent = NEXT_EDICT(ent))
    {
#ifdef QUAKE2
        // don't send if flagged for NODRAW and there are no lighting effects
        if (ent->v.effects == EF_NODRAW)
            continue;
#endif

// ignore if not touching a PV leaf
        if (ent != clent)	// clent is ALLWAYS sent
        {
// ignore ents without visible models
            if (!ent->v.modelindex || !pr_strings[ent->v.model])
                continue;

            for (i=0 ; i < ent->num_leafs ; i++)
                if (pvs[ent->leafnums[i] >> 3] & (1 << (ent->leafnums[i]&7) ))
                    break;

            if (i == ent->num_leafs && ent->num_leafs < MAX_ENT_LEAFS)
                continue;		// not visible
        }

        /* built whole first: its exact size and its place in the order; copied in at once while everything so far
         * fits, never once the room left is smaller than the update */
        bytes = SV_EntityUpdateRecord (ent, e, record);
        if (bytes < 0)
            continue;
        VectorSubtract (ent->v.origin, org, dir);
        dist = Length (dir);
        sv_net_cand[n].e = (short)e;
        sv_net_cand[n].bytes = (short)bytes;
        /* an actor: one that moves by steps or flies (residents, creatures, guards) or is marked a monster */
        sv_net_cand[n].key = ent == clent ? AW_NETSEND_FIRST :
            AW_NetSendKey (dist, DotProduct (dir, forward) < 0,
                           !(ent->v.movetype == MOVETYPE_STEP || ent->v.movetype == MOVETYPE_FLY ||
                             ((int)ent->v.flags & FL_MONSTER)),
                           e < MAX_EDICTS ? sv_net_missed[e] : 0);
        n++;
        if (!over && used + bytes <= budget)
        {
            SZ_Write (msg, record, bytes);
            used += bytes;
        }
        else
            over = 1;
    }

    sv_net.candidates = n;
    sv_net.budget = budget;
    for (i = 0, sv_net.wanted = 0; i < n; i++)
        sv_net.wanted += sv_net_cand[i].bytes;
    sv_net.deferred = 0;
    if (over)
    {
        /* not everything fits: the nearest, in front first, the waiting ones forward; the rest in the next frames */
        msg->cursize = mark;
        used = AW_NetSendChoose (sv_net_cand, n, budget, sv_net_send);
        for (i = 0; i < n; i++)
        {
            e = sv_net_cand[i].e;
            if (sv_net_send[i] && SV_EntityUpdateRecord (EDICT_NUM(e), e, record) == sv_net_cand[i].bytes)
            {
                SZ_Write (msg, record, sv_net_cand[i].bytes);
                SV_NetSent (e);
            }
            else
            {
                sv_net.deferred++;
                if (e < MAX_EDICTS && sv_net_missed[e] < 255)
                    sv_net_missed[e]++;
            }
        }
        sv_net.frames_deferred++;
        /* the room ran short (PACED waits by design and says nothing) */
        if (!sv_net_limit && (realtime - sv_net.said > 30 || sv_net.said > realtime))
        {
            sv_net.said = realtime;
            Con_Printf ("Entity updates: %ld of %ld wait for the next frames (%ld of %ld bytes; dbg netstat)\n",
                        (long)sv_net.deferred, (long)n, (long)sv_net.wanted, (long)budget);
        }
    }
    else
        for (i = 0; i < n; i++)
            SV_NetSent (sv_net_cand[i].e);
    sv_net.sent = n - sv_net.deferred;
    sv_net.sent_bytes = used;
    sv_net.frames++;
    if (sv_net.wanted + mark > MAX_DATAGRAM)
        sv_net.frames_over_1024++;
    if (sv_net.wanted > sv_net.worst_wanted)
    {
        sv_net.worst_wanted = sv_net.wanted;
        sv_net.worst_candidates = n;
        sv_net.worst_budget = budget;
        sv_net.worst_deferred = sv_net.deferred;
    }
}

/* One entity's update (NET-VIVEC-ENTITY-PACKET-OVERFLOW-66: sized first by SV_EntityUpdateBytes, then written where it
 * fits; at most AW_NETSEND_RECORD_MAX bytes). */
static void SV_WriteEntityUpdate (edict_t *ent, int e, sizebuf_t *msg)
{
    int		i;
    int		bits, frame, aw;
    float	scale;
    float	miss;

        scale = SV_AliasScale (ent);
        frame = (int)ent->v.frame;
        aw = (scale != 1 ? AWU_SCALE : 0) | (frame > 255 ? AWU_FRAME2 : 0);

// send an update
        bits = 0;

        for (i=0 ; i<3 ; i++)
        {
            miss = ent->v.origin[i] - ent->baseline.origin[i];
            if ( miss < -0.1 || miss > 0.1 )
                bits |= U_ORIGIN1<<i;
        }

        if ( ent->v.angles[0] != ent->baseline.angles[0] )
            bits |= U_ANGLE1;

        if ( ent->v.angles[1] != ent->baseline.angles[1] )
            bits |= U_ANGLE2;

        if ( ent->v.angles[2] != ent->baseline.angles[2] )
            bits |= U_ANGLE3;

        if (ent->v.movetype == MOVETYPE_STEP)
            bits |= U_NOLERP;	// don't mess up the step animation

        if (aw)
            bits |= U_AW_EXT;

        if (ent->baseline.colormap != ent->v.colormap)
            bits |= U_COLORMAP;

        if (ent->baseline.skin != ent->v.skin)
            bits |= U_SKIN;

        /* a frame over 255 is always sent whole: the client's baseline holds one byte of it */
        if (ent->baseline.frame != ent->v.frame || frame > 255)
            bits |= U_FRAME;

        if (ent->baseline.effects != ent->v.effects)
            bits |= U_EFFECTS;

        if (ent->baseline.modelindex != ent->v.modelindex)
            bits |= U_MODEL;

        if (e >= 256)
            bits |= U_LONGENTITY;

        if (bits >= 256)
            bits |= U_MOREBITS;

    //
    // write the message
    //
        MSG_WriteByte (msg,bits | U_SIGNAL);

        if (bits & U_MOREBITS)
            MSG_WriteByte (msg, bits>>8);
        if (bits & U_LONGENTITY)
            MSG_WriteShort (msg,e);
        else
            MSG_WriteByte (msg,e);

        if (bits & U_MODEL)
            MSG_WriteModel (msg, (int)ent->v.modelindex);
        if (bits & U_FRAME)
            MSG_WriteByte (msg, frame & 255);
        if (bits & U_COLORMAP)
            MSG_WriteByte (msg, ent->v.colormap);
        if (bits & U_SKIN)
            MSG_WriteByte (msg, ent->v.skin);
        if (bits & U_EFFECTS)
            MSG_WriteByte (msg, ent->v.effects);
        if (bits & U_ORIGIN1)
            MSG_WriteCoord (msg, ent->v.origin[0]);
        if (bits & U_ANGLE1)
            MSG_WriteAngle(msg, ent->v.angles[0]);
        if (bits & U_ORIGIN2)
            MSG_WriteCoord (msg, ent->v.origin[1]);
        if (bits & U_ANGLE2)
            MSG_WriteAngle(msg, ent->v.angles[1]);
        if (bits & U_ORIGIN3)
            MSG_WriteCoord (msg, ent->v.origin[2]);
        if (bits & U_ANGLE3)
            MSG_WriteAngle(msg, ent->v.angles[2]);
        if (bits & U_AW_EXT)
        {
            MSG_WriteByte (msg, aw);
            if (aw & AWU_SCALE)
                MSG_WriteFloat (msg, scale);
            if (aw & AWU_FRAME2)
                MSG_WriteByte (msg, (frame >> 8) & 255);
        }
}

/*
=============
SV_CleanupEnts

=============
*/
void SV_CleanupEnts (void)
{
    int		e;
    edict_t	*ent;

    ent = NEXT_EDICT(sv.edicts);
    for (e=1 ; e<sv.num_edicts ; e++, ent = NEXT_EDICT(ent))
    {
        ent->v.effects = (int)ent->v.effects & ~EF_MUZZLEFLASH;
    }

}

/*
==================
SV_WriteClientdataToMessage

==================
*/
void SV_WriteClientdataToMessage (edict_t *ent, sizebuf_t *msg)
{
    int		bits;
    int		i;
    edict_t	*other;
    int		items;
#ifndef QUAKE2
    eval_t	*val;
#endif

//
// send a damage message
//
    if (ent->v.dmg_take || ent->v.dmg_save)
    {
        other = PROG_TO_EDICT(ent->v.dmg_inflictor);
        MSG_WriteByte (msg, svc_damage);
        MSG_WriteByte (msg, ent->v.dmg_save);
        MSG_WriteByte (msg, ent->v.dmg_take);
        for (i=0 ; i<3 ; i++)
            MSG_WriteCoord (msg, other->v.origin[i] + 0.5*(other->v.mins[i] + other->v.maxs[i]));

        ent->v.dmg_take = 0;
        ent->v.dmg_save = 0;
    }

//
// send the current viewpos offset from the view entity
//
    SV_SetIdealPitch ();		// how much to look up / down ideally

// a fixangle might get lost in a dropped packet.  Oh well.
    if ( ent->v.fixangle )
    {
        MSG_WriteByte (msg, svc_setangle);
        for (i=0 ; i < 3 ; i++)
            MSG_WriteAngle (msg, ent->v.angles[i] );
        ent->v.fixangle = 0;
    }

    bits = 0;

    if (ent->v.view_ofs[2] != DEFAULT_VIEWHEIGHT)
        bits |= SU_VIEWHEIGHT;

    if (ent->v.idealpitch)
        bits |= SU_IDEALPITCH;

// stuff the sigil bits into the high bits of items for sbar, or else
// mix in items2
#ifdef QUAKE2
    items = (int)ent->v.items | ((int)ent->v.items2 << 23);
#else
    val = GetEdictFieldValue(ent, "items2");

    if (val)
        items = (int)ent->v.items | ((int)val->_float << 23);
    else
        items = (int)ent->v.items | ((int)pr_global_struct->serverflags << 28);
#endif

    bits |= SU_ITEMS;

    if ( (int)ent->v.flags & FL_ONGROUND)
        bits |= SU_ONGROUND;

    if ( ent->v.waterlevel >= 2)
        bits |= SU_INWATER;

    for (i=0 ; i<3 ; i++)
    {
        if (ent->v.punchangle[i])
            bits |= (SU_PUNCH1<<i);
        if (ent->v.velocity[i])
            bits |= (SU_VELOCITY1<<i);
    }

    if (ent->v.weaponframe)
        bits |= SU_WEAPONFRAME;

    if (ent->v.armorvalue)
        bits |= SU_ARMOR;

//	if (ent->v.weapon)
        bits |= SU_WEAPON;

// send the data

    MSG_WriteByte (msg, svc_clientdata);
    MSG_WriteShort (msg, bits);

    if (bits & SU_VIEWHEIGHT)
        MSG_WriteChar (msg, ent->v.view_ofs[2]);

    if (bits & SU_IDEALPITCH)
        MSG_WriteChar (msg, ent->v.idealpitch);

    for (i=0 ; i<3 ; i++)
    {
        if (bits & (SU_PUNCH1<<i))
            MSG_WriteChar (msg, ent->v.punchangle[i]);
        if (bits & (SU_VELOCITY1<<i))
            MSG_WriteChar (msg, ent->v.velocity[i]/16);
    }

// [always sent]	if (bits & SU_ITEMS)
    MSG_WriteLong (msg, items);

    if (bits & SU_WEAPONFRAME)
        MSG_WriteByte (msg, ent->v.weaponframe);
    if (bits & SU_ARMOR)
        MSG_WriteByte (msg, ent->v.armorvalue);
    if (bits & SU_WEAPON)
        MSG_WriteModel (msg, SV_ModelIndex(pr_strings+ent->v.weaponmodel));

    MSG_WriteShort (msg, ent->v.health);
    MSG_WriteByte (msg, ent->v.currentammo);
    MSG_WriteByte (msg, ent->v.ammo_shells);
    MSG_WriteByte (msg, ent->v.ammo_nails);
    MSG_WriteByte (msg, ent->v.ammo_rockets);
    MSG_WriteByte (msg, ent->v.ammo_cells);

    if (standard_quake)
    {
        MSG_WriteByte (msg, ent->v.weapon);
    }
    else
    {
        for(i=0;i<32;i++)
        {
            if ( ((int)ent->v.weapon) & (1<<i) )
            {
                MSG_WriteByte (msg, i);
                break;
            }
        }
    }
}

/*
=======================
SV_SendClientDatagram
=======================
*/
/* NET-VIVEC-ENTITY-PACKET-OVERFLOW-66: the game's own connection (the loopback, net_loop.c: both sides in this
 * program) carries a frame's message far larger than the 1024 bytes a network packet holds, with room to spare that
 * grows when a frame needs it, and a separate budget for what one frame may send (the maintainer, 2026-11-17: room to
 * spare, grown when needed, the sizes settings; what is sent each frame is what costs time on the 68k). All saved:
 * - aw_net_method and aw_net_send (below): FULL sends everything in sight; PACED at most aw_net_send bytes a frame,
 *   past it the nearest first and the rest in the next frames. The defaults come from the in-game measurement
 *   (docs/performance/NET_FRAME.md).
 * - aw_net_frame (32768): the frame message's room at the start of each map; aw_net_buffer (65536): the client's
 *   receive buffer at the first frame of a game; aw_net_max (262144): the room never grows past it.
 * - A frame that wants more than three quarters of its room (up to its send budget) doubles the room, and the receive
 *   buffer with it, for the next frame: never in the middle of a message, never past aw_net_max, one console line.
 *   Nothing shrinks during a map; the room starts again from aw_net_frame at the next map.
 * - The receive buffer also takes this frame's reliable message after it and whatever the client has not read: the
 *   frame's room keeps that free, so the reliable one always fits.
 * The fullest frame the engine can make today is about 18 KB (MAX_EDICTS 600 updates of at most 28 bytes, the player's
 * data, the frame's sounds and effects), under the starting room: the growth is for a larger entity table or format.
 * Memory, allocated once at the first frame and only grown: the frame buffer (the room) and the receive buffer and
 * net_message (net_loop.c): 128 KB at the start sizes, about 0.8 MB at aw_net_max. */
/* Two methods to compare (methods as switches), live from the console, saved: 1 FULL, every update in sight each
 * frame, the room growing as needed; 2 PACED, at most aw_net_send bytes a frame, the nearest first, the rest in the
 * next frames. The default is the one that measured better (docs/performance/NET_FRAME.md). */
static cvar_t aw_net_method = {"aw_net_method", "1", true};
static cvar_t aw_net_send = {"aw_net_send", "4096", true};
static cvar_t aw_net_frame = {"aw_net_frame", "32768", true};
static cvar_t aw_net_buffer = {"aw_net_buffer", "65536", true};
static cvar_t aw_net_max = {"aw_net_max", "262144", true};
#define AW_NET_LIMIT 4194304	/* the settings' own bound: a message's length fits three bytes (net_loop.c) */
extern int Loop_ReceiveSize (void);
extern int Loop_Unread (void);
extern int Loop_Grow (int receive, int message);
static byte *sv_frame_data;	/* the frame buffer: allocated, the size of the room or more */
static int sv_frame_size;
static int sv_frame_room;	/* the room now; 0 until the first frame of a map */
static int sv_frame_grow;	/* the room the last frame asked for (0 none) */
static struct {
    int count, from, to, wanted, at_max;
} sv_net_grown;
static int SV_NetSetting (cvar_t *v, int low, int high)
{
    int n = (int)v->value;
    return n < low ? low : n > high ? high : n;
}
/* An overflow that still happens (every message buffer allows it explicitly, so it marks the buffer instead of
 * stopping the game): that message is dropped whole and the console says so, at most once every 30 s. */
int aw_net_dropped;	/* the messages dropped so, for the state file (aw_remote.c net_dropped: the engine smoke fails on it) */
static void SV_NetOverflowSaid (const char *what, int size)
{
    static double said = -1000;
    aw_net_dropped++;
    if (realtime - said >= 30 || realtime < said)
    {
        said = realtime;
        Con_Printf ("Message overflow caught (%ld so far): %s, %ld bytes; not sent\n", (long)aw_net_dropped, what, (long)size);
    }
}
/* Before a frame is written: the room from the setting (raised settings count from the next frame on) and what the
 * last frame asked for, the frame buffer and the connection's buffers grown to it; never past aw_net_max. */
static void SV_NetRoomPrepare (void)
{
    static qboolean short_said;
    int max = SV_NetSetting (&aw_net_max, MAX_DATAGRAM, AW_NET_LIMIT);
    int start = SV_NetSetting (&aw_net_frame, MAX_DATAGRAM, max);
    int want = sv_frame_room > start ? sv_frame_room : start, receive;
    byte *data;
    if (sv_frame_grow > want)
        want = sv_frame_grow;
    if (want > max)
        want = max;
    sv_frame_grow = 0;
    receive = SV_NetSetting (&aw_net_buffer, NET_MAXMESSAGE, AW_NET_LIMIT);
    if (receive < want + MAX_MSGLEN + 64)
        receive = want + MAX_MSGLEN + 64;
    if (want > sv_frame_size)
    {
        if ((data = AW_TryMalloc (want)) != NULL)
        {
            if (sv_frame_data)
                free (sv_frame_data);
            sv_frame_data = data;
            sv_frame_size = want;
        }
    }
    if ((want > sv_frame_size || !Loop_Grow (receive, want > MAX_MSGLEN ? want : MAX_MSGLEN)) && !short_said)
    {
        short_said = true;
        Con_Printf ("Frame message: not enough memory for %ld bytes of room; it stays at %ld\n", (long)want,
                    (long)sv_frame_size);
    }
    sv_frame_room = want < sv_frame_size ? want : sv_frame_size;
}
/* The room of this frame's message to CLIENT: on the game's own connection the room (what is free in the client's
 * receive buffer after its unread messages and this frame's reliable one at most); -1 for a network client (a packet,
 * MAX_DATAGRAM). */
static int SV_LoopDatagramRoom (client_t *client)
{
    int room;
    if (!client->netconnection || Q_strcmp (client->netconnection->address, "LOCAL") || !client->netconnection->driverdata)
        return -1;
    SV_NetRoomPrepare ();
    if (!sv_frame_data)
        return -1;		/* no memory for a larger one: a network packet's size */
    room = Loop_ReceiveSize () - Loop_Unread () - ((client->message.cursize + 4 + 3) & ~3) - 16;
    if (room > sv_frame_room)
        room = sv_frame_room;
    return room < 16 ? 16 : room;	/* a nearly full buffer: a message that does not fit is not sent */
}

/* dbg netstat [reset] (NET-VIVEC-ENTITY-PACKET-OVERFLOW-66): the method and its budget, the room and its growth, the
 * last frame's entity updates, and since the map started or the last reset the fullest frame, how close it came to the
 * room, the waits, the frame time and the client's reading time per frame; the models that filled the last frame.
 * reset: a new measuring window (to compare the two methods in one session). */
extern double cl_net_parse_last, cl_net_parse_sum, cl_net_parse_max;
extern int cl_net_parse_frames;
static void SV_NetStat_f (void)
{
    static int model_bytes[MAX_MODELS], model_count[MAX_MODELS];
    int i, k, best, shown, paced = (int)aw_net_method.value == 2;
    if (Cmd_Argc () >= 2 && !Q_strcasecmp (Cmd_Argv (1), "reset"))
    {
        memset (&sv_net, 0, sizeof(sv_net));
        cl_net_parse_last = cl_net_parse_sum = cl_net_parse_max = 0;
        cl_net_parse_frames = 0;
        Con_Printf ("dbg netstat: a new measuring window starts.\n");
        return;
    }
    if (!sv.active)
    {
        Con_Printf ("dbg netstat: no map is running.\n");
        return;
    }
    Con_Printf ("Method %s (aw_net_method %ld)%s%ld; room %ld bytes (aw_net_frame %ld, up to aw_net_max %ld), "
                "receive buffer %ld; grown %ld times (last %ld to %ld for a frame of %ld bytes)\n",
                paced ? "PACED" : "FULL", (long)(paced ? 2 : 1), paced ? ", budget aw_net_send " : ", budget the room ",
                (long)(paced ? SV_NetSetting (&aw_net_send, MAX_DATAGRAM, AW_NET_LIMIT) : sv_frame_room),
                (long)sv_frame_room, (long)aw_net_frame.value, (long)aw_net_max.value, (long)Loop_ReceiveSize (),
                (long)sv_net_grown.count, (long)sv_net_grown.from, (long)sv_net_grown.to, (long)sv_net_grown.wanted);
    Con_Printf ("Last frame on %s: %ld entities in sight want %ld bytes, budget %ld; %ld sent in %ld bytes, %ld wait\n",
                sv.name, (long)sv_net.candidates, (long)sv_net.wanted, (long)sv_net.budget, (long)sv_net.sent,
                (long)sv_net.sent_bytes, (long)sv_net.deferred);
    Con_Printf ("Since then: %ld frames, %ld with updates waiting, %ld over %ld bytes; the fullest frame %ld bytes (%ld%% "
                "of the room, %ld entities, %ld waited); longest wait %ld frames, %ld updates waited %ld.%ld frames on "
                "average; %ld frame messages not sent\n",
                (long)sv_net.frames, (long)sv_net.frames_deferred, (long)sv_net.frames_over_1024, (long)MAX_DATAGRAM,
                (long)sv_net.worst_need, sv_frame_room ? (long)(sv_net.worst_need * 100L / sv_frame_room) : 0L,
                (long)sv_net.worst_candidates, (long)sv_net.worst_deferred, (long)sv_net.wait_max, (long)sv_net.waited,
                sv_net.waited ? (long)(sv_net.wait_sum / sv_net.waited) : 0L,
                sv_net.waited ? (long)(sv_net.wait_sum * 10 / sv_net.waited) % 10 : 0L, (long)sv_net.dropped);
    Con_Printf ("Frame time %ld.%ld ms average, %ld ms longest (%ld frames); the client reads %ld us a frame on average, "
                "%ld us longest, %ld us the last frame\n",
                sv_net.frame_n ? (long)(sv_net.frame_sum * 1000 / sv_net.frame_n) : 0L,
                sv_net.frame_n ? (long)(sv_net.frame_sum * 10000 / sv_net.frame_n) % 10 : 0L,
                (long)(sv_net.frame_max * 1000), (long)sv_net.frame_n,
                cl_net_parse_frames ? (long)(cl_net_parse_sum * 1e6 / cl_net_parse_frames) : 0L,
                (long)(cl_net_parse_max * 1e6), (long)(cl_net_parse_last * 1e6));
    memset (model_bytes, 0, sizeof(model_bytes));
    memset (model_count, 0, sizeof(model_count));
    for (i = 0; i < sv_net.candidates; i++)
    {
        edict_t *ent = EDICT_NUM(sv_net_cand[i].e);
        k = (int)ent->v.modelindex;
        if (k > 0 && k < MAX_MODELS)
        {
            model_bytes[k] += sv_net_cand[i].bytes;
            model_count[k]++;
        }
    }
    for (shown = 0; shown < 8; shown++)
    {
        for (best = 0, k = 1; k < MAX_MODELS; k++)
            if (model_bytes[k] > model_bytes[best])
                best = k;
        if (!best || !model_bytes[best])
            break;
        Con_Printf ("  %ld bytes: %ld x %s\n", (long)model_bytes[best], (long)model_count[best],
                    sv.model_precache[best] ? sv.model_precache[best] : "?");
        model_bytes[best] = 0;
    }
}

/* After a frame was written on the game's own connection: a frame that wanted more than three quarters of the room
 * (FULL: everything in sight; PACED: up to its budget) doubles the room for the next frame (SV_NetRoomPrepare grows
 * the buffers then), never past aw_net_max; one console line. NEED: the bytes the whole frame wanted. */
static void SV_NetRoomAsk (int need)
{
    int max = SV_NetSetting (&aw_net_max, MAX_DATAGRAM, AW_NET_LIMIT), to = sv_frame_room;
    if (need > sv_net.worst_need)
        sv_net.worst_need = need;
    if (need * 4 <= sv_frame_room * 3)
        return;
    if (sv_frame_room >= max)
    {
        if (!sv_net_grown.at_max)
            Con_Printf ("Frame message: at its largest room, %ld bytes (aw_net_max), a frame on %s wanted %ld; the "
                        "nearest go first\n", (long)sv_frame_room, sv.name, (long)need);
        sv_net_grown.at_max = 1;
        return;
    }
    while (need * 4 > to * 3 && to < max)
        to *= 2;
    if (to > max)
        to = max;
    sv_frame_grow = to;
    sv_net_grown.count++;
    sv_net_grown.from = sv_frame_room;
    sv_net_grown.to = to;
    sv_net_grown.wanted = need;
    Con_Printf ("Frame message: the room grows from %ld to %ld bytes for the next frame (a frame on %s wanted %ld)\n",
                (long)sv_frame_room, (long)to, sv.name, (long)need);
}

qboolean SV_SendClientDatagram (client_t *client)
{
    byte		buf[MAX_DATAGRAM];
    sizebuf_t	msg;
    int			room, head, paced;

    room = SV_LoopDatagramRoom (client);
    paced = (int)aw_net_method.value == 2;
    {
        /* dbg netstat: the frame time, one frame message to the next (a pause or a load is not a frame) */
        static double last;
        double dt = realtime - last;
        last = realtime;
        if (dt > 0 && dt < 2)
        {
            sv_net.frame_sum += dt;
            if (dt > sv_net.frame_max)
                sv_net.frame_max = dt;
            sv_net.frame_n++;
        }
    }
    memset (&msg, 0, sizeof(msg));
    msg.data = room > 0 ? sv_frame_data : buf;
    msg.maxsize = room > 0 ? room : (int)sizeof(buf);
    msg.cursize = 0;
    /* never sent overflowed: a full buffer clears and is marked, and such a message is dropped below */
    msg.allowoverflow = true;

    MSG_WriteByte (&msg, svc_time);
    MSG_WriteFloat (&msg, sv.time);

// add the client specific data to the datagram
    SV_WriteClientdataToMessage (client->edict, &msg);
    head = msg.cursize;

    /* the frame's sounds and effects keep their room after the entities; PACED: at most aw_net_send bytes a frame */
    sv_net_reserve = sv.datagram.cursize + 1 < msg.maxsize / 2 ? sv.datagram.cursize + 1 : 0;
    sv_net_limit = room > 0 && paced ? SV_NetSetting (&aw_net_send, MAX_DATAGRAM, AW_NET_LIMIT) : 0;
    SV_WriteEntitiesToClient (client->edict, &msg);
    if (room > 0)
    {
        int need = head + sv_net.wanted + sv.datagram.cursize;
        SV_NetRoomAsk (paced && need > sv_net_limit ? sv_net_limit : need);
    }
    sv_net_reserve = sv_net_limit = 0;

// copy the server datagram if there is space
    /* (its own overflow, from a game script's writes, cleared it partway: not copied, SV_NetOverflowSaid) */
    if (!sv.datagram.overflowed && msg.cursize + sv.datagram.cursize < msg.maxsize)
        SZ_Write (&msg, sv.datagram.data, sv.datagram.cursize);
    else if (sv.datagram.overflowed)
        SV_NetOverflowSaid ("the frame's sounds and effects (sv.datagram)", sv.datagram.maxsize);

    if (msg.overflowed)
    {
        /* cannot happen with every update sized first; if it does, the frame's update is not sent (the screen side
         * keeps the last one), never a message that starts in the middle of an update */
        sv_net.dropped++;
        SV_NetOverflowSaid ("a frame update", msg.maxsize);
        return true;
    }

// send the datagram
    if (NET_SendUnreliableMessage (client->netconnection, &msg) == -1)
    {
        SV_DropClient (true);// if the message couldn't send, kick off
        return false;
    }

    return true;
}

/*
=======================
SV_UpdateToReliableMessages
=======================
*/
void SV_UpdateToReliableMessages (void)
{
    int			i, j;
    client_t *client;

// check for changes to be sent over the reliable streams
    for (i=0, host_client = svs.clients ; i<svs.maxclients ; i++, host_client++)
    {
        if (host_client->old_frags != host_client->edict->v.frags)
        {
            for (j=0, client = svs.clients ; j<svs.maxclients ; j++, client++)
            {
                if (!client->active)
                    continue;
                MSG_WriteByte (&client->message, svc_updatefrags);
                MSG_WriteByte (&client->message, i);
                MSG_WriteShort (&client->message, host_client->edict->v.frags);
            }

            host_client->old_frags = host_client->edict->v.frags;
        }
    }

    /* NET-VIVEC-ENTITY-PACKET-OVERFLOW-66: a broadcast that overflowed (a game script's writes) was cleared partway:
     * dropped whole, never sent from the middle */
    if (sv.reliable_datagram.overflowed)
        SV_NetOverflowSaid ("a broadcast to every client (sv.reliable_datagram)", sv.reliable_datagram.maxsize);
    else
        for (j=0, client = svs.clients ; j<svs.maxclients ; j++, client++)
        {
            if (!client->active)
                continue;
            SZ_Write (&client->message, sv.reliable_datagram.data, sv.reliable_datagram.cursize);
        }

    SZ_Clear (&sv.reliable_datagram);
    sv.reliable_datagram.overflowed = false;
}


/*
=======================
SV_SendNop

Send a nop message without trashing or sending the accumulated client
message buffer
=======================
*/
void SV_SendNop (client_t *client)
{
    sizebuf_t	msg;
    byte		buf[4];

    memset (&msg, 0, sizeof(msg));
    msg.data = buf;
    msg.maxsize = sizeof(buf);
    msg.cursize = 0;
    msg.allowoverflow = true;	/* every message buffer says it (NET-VIVEC-ENTITY-PACKET-OVERFLOW-66) */

    MSG_WriteChar (&msg, svc_nop);

    if (NET_SendUnreliableMessage (client->netconnection, &msg) == -1)
        SV_DropClient (true);	// if the message couldn't send, kick off
    client->last_message = realtime;
}

/*
=======================
SV_SendClientMessages
=======================
*/
void SV_SendClientMessages (void)
{
    int			i;
    void		AW_ItemsPreSend (void);		/* aw_items.c (declared here: a build stage reads aw_items.h) */

// every humanoid group by its state (aw_animkit.c): the picked frames go out, the drivers' come back below
    AW_AnimPickPreSend ();
// held items and carried lights on the hand of the frame that goes out (NPC-WEAPON-GRIP-WRONG-69): after the pick
    AW_ItemsPreSend ();
// update frags, names, etc
    SV_UpdateToReliableMessages ();

// build individual updates
    for (i=0, host_client = svs.clients ; i<svs.maxclients ; i++, host_client++)
    {
        if (!host_client->active)
            continue;

        if (host_client->spawned)
        {
            if (!SV_SendClientDatagram (host_client))
                continue;
        }
        else
        {
        // the player isn't totally in the game yet
        // send small keepalive messages if too much time has passed
        // send a full message when the next signon stage has been requested
        // some other message data (name changes, etc) may accumulate
        // between signon stages
            if (!host_client->sendsignon)
            {
                if (realtime - host_client->last_message > 5)
                    SV_SendNop (host_client);
                continue;	// don't send out non-signon messages
            }
        }

        // check for an overflowed message.  Should only happen
        // on a severely congested connection that backs up a lot, then
        // changes level
        if (host_client->message.overflowed)
        {
            /* NET-VIVEC-ENTITY-PACKET-OVERFLOW-66: the reliable message was cleared partway, so it is never sent.
             * The game's own player is not dropped (that ended the game): the session ends through Host_Error, so
             * the place he is in loads again (aw_scene.c AW_SceneHostError) and the box says why; a network
             * client is dropped as before */
            host_client->message.overflowed = false;
            if (!Q_strcmp (host_client->netconnection->address, "LOCAL"))
            {
                SZ_Clear (&host_client->message);
                Host_Error ("The reliable message to the screen side overflowed (%ld bytes)",
                            (long)host_client->message.maxsize);
            }
            SV_DropClient (true);
            continue;
        }

        if (host_client->message.cursize || host_client->dropasap)
        {
            if (!NET_CanSendMessage (host_client->netconnection))
            {
//				I_Printf ("can't write\n");
                continue;
            }

            if (host_client->dropasap)
                SV_DropClient (false);	// went to another level
            else
            {
                if (NET_SendMessage (host_client->netconnection
                , &host_client->message) == -1)
                    SV_DropClient (true);	// if the message couldn't send, kick off
                SZ_Clear (&host_client->message);
                host_client->last_message = realtime;
                host_client->sendsignon = false;
            }
        }
    }

    AW_AnimPickPostSend ();

// clear muzzle flashes
    SV_CleanupEnts ();
}


/*
==============================================================================

SERVER SPAWNING

==============================================================================
*/

/*
================
SV_ModelIndex

================
*/
int SV_ModelIndex (char *name)
{
    int		i;

    if (!name || !name[0])
        return 0;

    for (i=0 ; i<MAX_MODELS && sv.model_precache[i] ; i++)
        if (!strcmp(sv.model_precache[i], name))
            return i;
    if (i==MAX_MODELS || !sv.model_precache[i])
        Sys_Error ("SV_ModelIndex: model %s not precached", name);
    return i;
}

/*
================
SV_CreateBaseline

================
*/
void SV_CreateBaseline (void)
{
    int			i;
    edict_t			*svent;
    int				entnum;

    for (entnum = 0; entnum < sv.num_edicts ; entnum++)
    {
    // get the current server version
        svent = EDICT_NUM(entnum);
        if (svent->free)
            continue;
        if (entnum > svs.maxclients && !svent->v.modelindex)
            continue;

    //
    // create entity baseline
    //
        VectorCopy (svent->v.origin, svent->baseline.origin);
        VectorCopy (svent->v.angles, svent->baseline.angles);
        svent->baseline.frame = svent->v.frame;
        svent->baseline.skin = svent->v.skin;
        if (entnum > 0 && entnum <= svs.maxclients)
        {
            svent->baseline.colormap = entnum;
            svent->baseline.modelindex = SV_ModelIndex("progs/player.mdl");
        }
        else
        {
            svent->baseline.colormap = 0;
            svent->baseline.modelindex =
                SV_ModelIndex(pr_strings + svent->v.model);
        }

    //
    // add to the message
    //
        MSG_WriteByte (&sv.signon,svc_spawnbaseline);
        MSG_WriteShort (&sv.signon,entnum);

        MSG_WriteModel (&sv.signon, svent->baseline.modelindex);
        MSG_WriteByte (&sv.signon, svent->baseline.frame);
        MSG_WriteByte (&sv.signon, svent->baseline.colormap);
        MSG_WriteByte (&sv.signon, svent->baseline.skin);
        for (i=0 ; i<3 ; i++)
        {
            MSG_WriteCoord(&sv.signon, svent->baseline.origin[i]);
            MSG_WriteAngle(&sv.signon, svent->baseline.angles[i]);
        }
    }
}


/*
================
SV_SendReconnect

Tell all the clients that the server is changing levels
================
*/
void SV_SendReconnect (void)
{
    char	data[128];
    sizebuf_t	msg;

    memset (&msg, 0, sizeof(msg));
    msg.data = (byte *)data;
    msg.cursize = 0;
    msg.maxsize = sizeof(data);
    msg.allowoverflow = true;	/* every message buffer says it (NET-VIVEC-ENTITY-PACKET-OVERFLOW-66) */

    MSG_WriteChar (&msg, svc_stufftext);
    MSG_WriteString (&msg, "reconnect\n");
    NET_SendToAll (&msg, 5);

    if (cls.state != ca_dedicated)
#ifdef QUAKE2
        Cbuf_InsertText ("reconnect\n");
#else
        Cmd_ExecuteString ("reconnect\n", src_command);
#endif
}


/*
================
SV_SaveSpawnparms

Grabs the current state of each client for saving across the
transition to another level
================
*/
void SV_SaveSpawnparms (void)
{
    int		i, j;

    svs.serverflags = pr_global_struct->serverflags;

    for (i=0, host_client = svs.clients ; i<svs.maxclients ; i++, host_client++)
    {
        if (!host_client->active)
            continue;

    // call the progs to get default spawn parms for the new client
        pr_global_struct->self = EDICT_TO_PROG(host_client->edict);
        PR_ExecuteProgram (pr_global_struct->SetChangeParms);
        for (j=0 ; j<NUM_SPAWN_PARMS ; j++)
            host_client->spawn_parms[j] = (&pr_global_struct->parm1)[j];
    }
}


/*
================
SV_SpawnServer

This is called at the start of each level
================
*/
extern float		scr_centertime_off;

/* Why the last SV_SpawnServer did not spawn its map, "" when it did or has not run (SCENE-LOAD-FAIL-FALLBACK-67:
 * Host_Map_f names it in the failed load's box and console block). */
char aw_spawn_why[160];

qboolean SV_MapNameFits (const char *name)
{
    if (name && strlen (name) <= SV_MAPNAME_MAX)
        return true;
    Con_Printf ("Map name too long (at most %d characters).\n", SV_MAPNAME_MAX);
    return false;
}

#ifdef QUAKE2
void SV_SpawnServer (char *server, char *startspot)
#else
void SV_SpawnServer (char *server)
#endif
{
    double aw_load_start,aw_world_start,aw_world_time,aw_actors_start,aw_actors_time;
    edict_t		*ent;
    int			i;

    /* Every caller (map, changelevel, restart, load) passes through here:
     * a name that does not fit is refused before anything changes. */
    aw_spawn_why[0] = 0;
    if (!SV_MapNameFits (server))
    {
        Q_snprintf (aw_spawn_why, sizeof(aw_spawn_why), "the map name is too long");
        return;
    }
    // let's not have any servers with no name
    if (hostname.string[0] == 0)
        Cvar_Set ("hostname", "UNNAMED");
    scr_centertime_off = 0;

    Con_DPrintf ("SpawnServer: %s\n",server);
    aw_load_start=Sys_FloatTime();
    /* Also cover restart/changelevel, which do not pass through Host_Map_f. */
    SCR_BeginLoadingPlaque();
    svs.changelevel_issued = false;		// now safe to issue another

//
// tell all connected clients that we are going to a new level
//
    if (sv.active)
    {
        SV_SendReconnect ();
    }

//
// make cvars consistant
//
    if (coop.value)
        Cvar_SetValue ("deathmatch", 0);
    current_skill = (int)(skill.value + 0.5);
    if (current_skill < 0)
        current_skill = 0;
    if (current_skill > 3)
        current_skill = 3;

    Cvar_SetValue ("skill", (float)current_skill);

//
// set up the new server
//
    AW_HeapAuditPhase(sv.worldmodel?sv.worldmodel->name:sv.name,"outgoing");
    Host_ClearMemory ();
    AW_HeapAuditBegin();
    AW_HeapAuditPhase(server,"after-unload");

    memset (&sv, 0, sizeof(sv));
    AW_AnimSceneReset();   /* same-map reloads also need fresh mover precaches */
    AW_ItemsSceneReset();  /* and fresh held-item precache indices (HELD-WEAPON-WRONG-MODEL-62) */
    AW_HalloweenServerReset();   /* and drop every edict pointer kept from the old server (HORS-AFTER-HALLOWEEN-CRASH-58) */
    AW_CombatServerReset();      /* the fights' too: a kept slot became a fight of the new map's actor at its edict number
                                    (GAENOR-ATTACKS-AT-START-67) */
    AW_AmbientServerReset();
    AW_ActorsServerReset();   /* the same map spawned again joins its cells again (ACTOR-TABLE-SAME-MAP-RELOAD-67) */
    AW_MwscriptServerReset();   /* and attaches its scripts and object state again (PLAZA-FABRICANTS-LIVE-AT-START-67) */
    {   /* the solid boxes of the new map chosen again (aw_barrier.c; OPENING-BARRIERS-PER-BOX-68); declared here, not in
         * a header the CHIM stages key */
        void AW_BarrierServerReset(void);
        AW_BarrierServerReset();
    }
    {   /* the use key's focus table read again for the new map, also when its world model gets the last world's model
         * slot (aw_inventory.c; ROOM-AIM-ROWS-OUTDOORS-AFTER-COURTYARD-68); declared here, not in a header the CHIM
         * stages key */
        void AW_FocusServerReset(void);
        AW_FocusServerReset();
    }
    if(aw_inspect_reset)aw_inspect_reset();
    /* the waits of the entity updates and dbg netstat start again with the map (NET-VIVEC-ENTITY-PACKET-OVERFLOW-66) */
    memset (sv_net_missed, 0, sizeof(sv_net_missed));
    memset (&sv_net, 0, sizeof(sv_net));
    memset (&sv_net_grown, 0, sizeof(sv_net_grown));
    sv_frame_room = 0;	/* the room starts again from aw_net_frame; the buffers keep their size */

    COM_FormatPath (sv.name, sizeof(sv.name), "%s", server);	/* fits: SV_MapNameFits */
#ifdef QUAKE2
    if (startspot)
        COM_FormatPath (sv.startspot, sizeof(sv.startspot), "%s", startspot);
#endif

// load progs to get entity field count
    aw_load_phase = "server: progs";
    PR_LoadProgs ();

// allocate server memory
    sv.max_edicts = MAX_EDICTS;

    sv.edicts = Hunk_AllocName (sv.max_edicts*pr_edict_size, "edicts");

    sv.datagram.maxsize = sizeof(sv.datagram_buf);
    sv.datagram.cursize = 0;
    sv.datagram.data = sv.datagram_buf;

    sv.reliable_datagram.maxsize = sizeof(sv.reliable_datagram_buf);
    sv.reliable_datagram.cursize = 0;
    sv.reliable_datagram.data = sv.reliable_datagram_buf;

    sv.signon.maxsize = sizeof(sv.signon_buf);
    sv.signon.cursize = 0;
    sv.signon.data = sv.signon_buf;
    /* NET-VIVEC-ENTITY-PACKET-OVERFLOW-66: every message buffer allows its overflow explicitly: it is marked, caught
     * where the buffer is sent (the frame's sounds, a broadcast: dropped whole; the sign-on: this load ends, the
     * way back), never Sys_Error */
    sv.datagram.allowoverflow = sv.reliable_datagram.allowoverflow = sv.signon.allowoverflow = true;

// leave slots at start for clients only
    sv.num_edicts = svs.maxclients+1;
    for (i=0 ; i<svs.maxclients ; i++)
    {
        ent = EDICT_NUM(i+1);
        svs.clients[i].edict = ent;
    }

    sv.state = ss_loading;
    sv.paused = false;

    sv.time = 1.0;

    COM_FormatPath (sv.name, sizeof(sv.name), "%s", server);
    /* The one map path resolver (aw_mappath.c): maps/<name>.chim for a CHIM
     * frame map, else maps/<name>.bsp. */
    AW_MapPath (server, sv.modelname, sizeof(sv.modelname));
    {
        const char *variant=AW_SceneWorldModel(server);
        if(variant && !COM_FormatPath(sv.modelname,sizeof(sv.modelname),"%s",variant))
            AW_MapPath (server, sv.modelname, sizeof(sv.modelname));
    }
    AW_HeapAuditPhase(sv.modelname,"before-bsp");
    aw_load_phase = "server: world model";
    AW_StreamLoadBegin(sv.modelname);aw_world_start=Sys_FloatTime();
    {
        double spike_t0;
        AW_SPIKE_BEGIN (spike_t0);
        sv.worldmodel = Mod_ForName (sv.modelname, false);
        AW_SPIKE_END (AW_SP_MAPFILE, spike_t0, 0);
    }
    aw_world_time=Sys_FloatTime()-aw_world_start;
    if (!sv.worldmodel)
    {
        char why[160];
        if (AW_MapChimOrphan (server, why, sizeof(why)))
        {
            Con_Printf ("Map %s unavailable: %s\n", server, why);
            Q_snprintf (aw_spawn_why, sizeof(aw_spawn_why), "%s", why);
        }
        else
            Q_snprintf (aw_spawn_why, sizeof(aw_spawn_why), "its world model %s did not load", sv.modelname);
        Con_Printf ("Couldn't spawn server %s\n", sv.modelname);
        sv.active = false;
        SCR_EndLoadingPlaque();
        return;
    }
    /* The world and its inline models *1..*N take precache slots 1..N+1 of
     * MAX_MODELS (ENGINE-SUBMODEL-LIMIT-32): a map with more is refused as
     * unavailable, as a missing map is; the builder's map gate
     * (tools/map_engine_limits.py) keeps shipped maps far below. */
    if (sv.worldmodel->numsubmodels > MAX_MODELS - 1)
    {
        Con_Printf ("Map %s unavailable: %ld models, the engine holds %ld\n", sv.modelname,
                    (long)sv.worldmodel->numsubmodels, (long)(MAX_MODELS - 1));
        Q_snprintf (aw_spawn_why, sizeof(aw_spawn_why), "%ld models, the engine holds %ld",
                    (long)sv.worldmodel->numsubmodels, (long)(MAX_MODELS - 1));
        sv.active = false;
        SCR_EndLoadingPlaque();
        return;
    }
    /* A CHIM frame map is a BSP29 file but not a playable map without its
     * CHIM world: refused loudly, as a missing map is, never loaded as a void. */
    {
        char why[160];
        if (AW_MapRefused (sv.modelname, sv.worldmodel->entities, why, sizeof(why)))
        {
            Con_Printf ("Map %s unavailable: %s\n", sv.modelname, why);
            Q_snprintf (aw_spawn_why, sizeof(aw_spawn_why), "%s", why);
            sv.active = false;
            SCR_EndLoadingPlaque();
            return;
        }
    }
    sv.models[1] = sv.worldmodel;
    AW_HeapAuditPhase(sv.modelname,"after-bsp");

//
// clear world interaction links
//
    aw_load_phase = "server: inline models";
    SV_ClearWorld ();

    sv.sound_precache[0] = pr_strings;

    sv.model_precache[0] = pr_strings;
    sv.model_precache[1] = sv.modelname;
    for (i=1 ; i<sv.worldmodel->numsubmodels ; i++)
    {
        sv.model_precache[1+i] = localmodels[i];
        sv.models[i+1] = Mod_ForName (localmodels[i], false);
    }

//
// load the rest of the entities
//
    ent = EDICT_NUM(0);
    memset (&ent->v, 0, progs->entityfields * 4);
    ent->free = false;
    ent->v.model = sv.worldmodel->name - pr_strings;
    ent->v.modelindex = 1;		// world model
    ent->v.solid = SOLID_BSP;
    ent->v.movetype = MOVETYPE_PUSH;

    if (coop.value)
        pr_global_struct->coop = coop.value;
    else
        pr_global_struct->deathmatch = deathmatch.value;

    pr_global_struct->mapname = sv.name - pr_strings;
#ifdef QUAKE2
    pr_global_struct->startspot = sv.startspot - pr_strings;
#endif

// serverflags are for cross level information (sigils)
    pr_global_struct->serverflags = svs.serverflags;

    aw_load_phase = "server: entities";
    AW_SceneryBegin(sv.worldmodel->entities);
    aw_actors_start=Sys_FloatTime();
    ED_LoadFromFile (sv.worldmodel->entities);
    AW_GalleryEntities();
    aw_actors_time=Sys_FloatTime()-aw_actors_start;
    AW_HeapAuditPhase(sv.modelname,"after-actors");

    sv.active = true;

// all setup is completed, any further precache statements are errors
    sv.state = ss_active;

// run two frames to allow everything to settle
    host_frametime = 0.1;
    aw_load_phase = "server: settle frame 1";
    SV_Physics ();
    aw_load_phase = "server: settle frame 2";
    SV_Physics ();

// create a baseline for more efficient communications
    aw_load_phase = "server: baseline";
    SV_CreateBaseline ();
    /* a sign-on (the map's statics and baselines) past its buffer was cleared partway: this load ends (the way back
     * and the box), never a client that reads a sign-on from its middle (NET-VIVEC-ENTITY-PACKET-OVERFLOW-66) */
    if (sv.signon.overflowed)
        Host_Error ("The map's sign-on message is larger than %ld bytes", (long)sv.signon.maxsize);

// send serverinfo to all connected clients
    for (i=0,host_client = svs.clients ; i<svs.maxclients ; i++, host_client++)
        if (host_client->active)
            SV_SendServerinfo (host_client);

    Con_DPrintf ("Server spawned.\n");
    AW_StreamLoadEnd(sv.modelname,aw_world_time,aw_actors_time,Sys_FloatTime()-aw_load_start);
    aw_load_phase = "after the server spawn";
}
