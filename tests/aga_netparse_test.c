/* SPDX-License-Identifier: GPL-2.0-or-later
 * NET-VIVEC-ENTITY-PACKET-OVERFLOW-66: the screen side's reading of a server message (the real cl_parse.c, included
 * for its static parts, with common.c's readers). A frame's update (an unreliable message) that is cut short in the
 * middle of an entity's update, or that holds a byte no command starts with (the maintainer's "Illegible server
 * message"), is dropped with one console line and the game goes on: no Host_Error, and the next frame's update reads
 * as usual. A reliable message that does not read still ends the session (Host_Error: in the game the way back or the
 * place loaded again, aw_scene.c).
 */
#include "../engine/aga/src/cl_parse.c"
#include <assert.h>

extern short ShortNoSwap (short l);
extern int LongNoSwap (int l);
extern float FloatNoSwap (float f);

/* ---- the client state and what parsing reaches, as small stand-ins ---- */
client_static_t cls;
client_state_t cl;
entity_t cl_entities[MAX_EDICTS], cl_static_entities[MAX_STATIC_ENTITIES];
lightstyle_t cl_lightstyle[MAX_LIGHTSTYLES];
efrag_t cl_efrags[MAX_EFRAGS];
dlight_t cl_dlights[MAX_DLIGHTS];
viddef_t vid;
sizebuf_t net_message;
double realtime = 50;
cvar_t cl_shownet = {"cl_shownet", "0"};
static jmp_buf host_error;
static int host_errors, dropped_lines;
void Host_Error (char *error, ...) {(void)error; host_errors++; longjmp (host_error, 1);}
void Sys_Error (char *error, ...) {va_list a; va_start (a, error); vfprintf (stderr, error, a); va_end (a); abort ();}
void Host_EndGame (char *message, ...) {(void)message; abort ();}
void Con_Printf (char *fmt, ...) {if (strstr (fmt, "Frame update dropped")) dropped_lines++;}
void Con_DPrintf (char *fmt, ...) {(void)fmt;}
/* the rest of what the parser reaches: never called by these messages */
#define NEVER {abort ();}
server_t sv;
qboolean noclip_anglehack;
int cl_message_unreliable;	/* cl_main.c's, set per message there */
int AW_AnimLazy (const char *name) {(void)name; NEVER return 0;}
void CDAudio_Play (byte track, qboolean looping) {(void)track; (void)looping; NEVER}
void CDAudio_Pause (void) NEVER
void CDAudio_Resume (void) NEVER
void CL_ClearState (void) NEVER
int CL_GetMessage (void) {NEVER return 0;}
void CL_ParseTEnt (void) NEVER
void CL_SignonReply (void) NEVER
void Cbuf_AddText (char *text) {(void)text; NEVER}
void Cmd_ExecuteString (char *text, cmd_source_t src) {(void)text; (void)src; NEVER}
void *Hunk_AllocName (int size, char *name) {(void)size; (void)name; NEVER return NULL;}
void Hunk_Check (void) NEVER
struct model_s *Mod_FindName (char *name) {(void)name; NEVER return NULL;}
model_t *Mod_ForName (char *name, qboolean crash) {(void)name; (void)crash; NEVER return NULL;}
void Mod_TouchModel (char *name) {(void)name; NEVER}
int NET_SendMessage (struct qsocket_s *sock, sizebuf_t *d) {(void)sock; (void)d; NEVER return 0;}
void R_AddEfrags (entity_t *ent) {(void)ent; NEVER}
void R_NewMap (void) NEVER
void R_ParseParticleEffect (void) NEVER
void SCR_CenterPrint (char *str) {(void)str; NEVER}
void S_BeginPrecaching (void) NEVER
void S_EndPrecaching (void) NEVER
sfx_t *S_PrecacheSound (char *sample) {(void)sample; NEVER return NULL;}
void S_StartSound (int n, int c, sfx_t *s, vec3_t o, float v, float a) {(void)n; (void)c; (void)s; (void)o; (void)v; (void)a; NEVER}
void S_StaticSound (sfx_t *s, vec3_t o, float v, float a) {(void)s; (void)o; (void)v; (void)a; NEVER}
void S_StopSound (int n, int c) {(void)n; (void)c; NEVER}
void S_TouchSound (char *sample) {(void)sample; NEVER}
void Sbar_Changed (void) NEVER
void V_ParseDamage (void) NEVER

/* a frame's update as the server writes it: the time, then entity updates */
static byte data[256];
static void message (const byte *bytes, int n, int unreliable)
{
    memcpy (data, bytes, n);
    net_message.data = data;
    net_message.cursize = n;
    net_message.maxsize = sizeof (data);
    cl_message_unreliable = unreliable;
}

int main (void)
{
    int i, before;
    float t = 12.5f;
    byte update[64], n;

    LittleLong = LongNoSwap; LittleShort = ShortNoSwap; LittleFloat = FloatNoSwap;
    cls.state = ca_connected;
    cls.signon = SIGNONS;
    cl.num_entities = 1;
    cl.maxclients = 1;
    vid.colormap = (pixel_t *)data;

    /* a whole update: svc_time, then entity 5 with its x coordinate */
    n = 0;
    update[n++] = svc_time; memcpy (update + n, &t, 4); n += 4;
    update[n++] = U_SIGNAL | U_ORIGIN1;
    update[n++] = 5;
    update[n++] = 0x00; update[n++] = 0x10; update[n++] = 0x00;	/* 3-byte coordinate (aw_coord.h): 16.0 */
    message (update, n, 1);
    if (!setjmp (host_error))
        CL_ParseServerMessage ();
    assert (!host_errors && !dropped_lines && cl.mtime[0] == 12.5f && cl_entities[5].msgtime == 12.5f);

    /* the same update cut in the middle of the coordinate: dropped, one line, no Host_Error */
    message (update, n - 2, 1);
    if (!setjmp (host_error))
        CL_ParseServerMessage ();
    assert (!host_errors && dropped_lines == 1);

    /* a byte no command starts with (what an overflowed message began with): dropped, said at most every 10 s */
    update[5] = 60;
    message (update, n, 1);
    if (!setjmp (host_error))
        CL_ParseServerMessage ();
    assert (!host_errors && dropped_lines == 1 && cl_parse_dropped == 2);
    realtime += 11;
    message (update, n, 1);
    if (!setjmp (host_error))
        CL_ParseServerMessage ();
    assert (!host_errors && dropped_lines == 2 && cl_parse_dropped == 3);

    /* an entity number past the table, and a model past it: dropped */
    update[5] = U_SIGNAL | U_MOREBITS;
    update[6] = U_LONGENTITY >> 8;
    update[7] = 0xff; update[8] = 0x7f;
    message (update, 9, 1);
    if (!setjmp (host_error))
        CL_ParseServerMessage ();
    assert (!host_errors && cl_parse_dropped == 4);

    /* the next whole update reads as usual */
    update[5] = U_SIGNAL | U_ORIGIN1;
    update[6] = 5;
    before = cl_parse_dropped;
    t = 13.0f; memcpy (update + 1, &t, 4);
    message (update, n, 1);
    if (!setjmp (host_error))
        CL_ParseServerMessage ();
    assert (!host_errors && cl_parse_dropped == before && cl_entities[5].msgtime == 13.0f);

    /* a reliable message that does not read still ends the session (Host_Error) */
    update[5] = 60;
    message (update, n, 0);
    if (!setjmp (host_error))
        CL_ParseServerMessage ();
    assert (host_errors == 1);
    /* and a reliable message after a frame update that was dropped is never caught by the frame's catch */
    message (update, n - 2, 1);
    if (!setjmp (host_error))
        CL_ParseServerMessage ();
    message (update, n, 0);
    if (!setjmp (host_error))
        CL_ParseServerMessage ();
    assert (host_errors == 2);
    for (i = 0; i < 1; i++)
        printf ("frame updates dropped: %d, console lines: %d, sessions ended for a reliable message: %d\n",
                cl_parse_dropped, dropped_lines, host_errors);
    return 0;
}
