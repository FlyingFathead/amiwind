/* SPDX-License-Identifier: GPL-2.0-or-later */
/* The room record reader (chim_format.c ChimFormat_Room, docs/chim/INTERIOR_STORE.md):
 * header, room block, model list and 56-byte placed records with the light
 * byte, and the refusal of short, wrong-kind and out-of-range files. */
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <string.h>
#include "chim/chim_format.h"

static unsigned char buf[4096];

static void U16 (unsigned char *p, unsigned v) { p[0] = (unsigned char)(v >> 8); p[1] = (unsigned char)v; }
static void U32 (unsigned char *p, unsigned long v)
{
    p[0] = (unsigned char)(v >> 24); p[1] = (unsigned char)(v >> 16); p[2] = (unsigned char)(v >> 8); p[3] = (unsigned char)v;
}
static void F32 (unsigned char *p, float f) { unsigned long v; unsigned int u; memcpy (&u, &f, 4); v = u; U32 (p, v); }

/* A room of PLACEMENTS records over MODELS store models; returns its bytes. */
static long Room (int minor, const char *kind, int models, int placements)
{
    long dir = 64, data = 64 + 4L*models, bytes = data + 56L*placements;
    int i;
    memset (buf, 0, sizeof buf);
    memcpy (buf, "CHIM", 4); memcpy (buf + 4, kind, 4);
    U16 (buf + 8, 0); U16 (buf + 10, (unsigned)minor); U32 (buf + 12, 32); U32 (buf + 16, (unsigned long)placements);
    U32 (buf + 20, (unsigned long)dir); U32 (buf + 24, (unsigned long)data); U32 (buf + 28, (unsigned long)bytes);
    F32 (buf + 32, -100); F32 (buf + 36, -80); F32 (buf + 40, -16); F32 (buf + 44, 120); F32 (buf + 48, 90); F32 (buf + 52, 128);
    U32 (buf + 56, (unsigned long)models); U32 (buf + 60, 0);
    for (i = 0; i < models; i++)
        U32 (buf + 64 + 4*i, 300u + (unsigned)i);
    for (i = 0; i < placements; i++)
    {
        unsigned char *r = buf + data + 56L*i;
        U32 (r, (unsigned long)i); U32 (r + 4, 9000u + (unsigned)i); U32 (r + 8, 300u + (unsigned)(i % models));
        F32 (r + 12, 10.0f*i); F32 (r + 16, -5); F32 (r + 20, 2); F32 (r + 24, 45);
        U16 (r + 28, 0); r[30] = r[31] = 0;
        U16 (r + 32, (unsigned)(-8 & 0xffff)); U16 (r + 34, (unsigned)(-8 & 0xffff)); U16 (r + 36, 0);
        U16 (r + 38, 8); U16 (r + 40, 8); U16 (r + 42, 16);
        U16 (r + 44, 1); U16 (r + 46, (unsigned)((i == 1 ? 0x60 : 0) << 8 | (i == 2 ? 2 : 0)));
        F32 (r + 48, i == 1 ? 90.0f : 0.0f); F32 (r + 52, 0);
    }
    return bytes;
}

int main (void)
{
    chim_header_t h;
    chim_room_t room;
    chim_record_t rec;
    long n;

    /* A valid room: 3 placements over 2 models */
    n = Room (12, "ROOM", 2, 3);
    assert (ChimFormat_Room (buf, n, &h, &room));
    assert (h.count == 3 && h.minor == 12 && h.directory == 64 && h.data == 72 && room.models == 2);
    assert (room.mins[0] == -100 && room.maxs[2] == 128);
    assert (ChimFormat_U32 (buf + h.directory + 4) == 301);
    assert (ChimFormat_RecordPlaced (buf + h.data + 56, &rec));
    assert (rec.model == 301 && rec.pitch == 90 && rec.yaw == 45 && rec.mins[0] == -8 && rec.maxs[2] == 16);
    assert (ChimFormat_RecordLight (h.minor, rec.flags) == 0x60);
    assert (ChimFormat_RecordPlaced (buf + h.data + 112, &rec) && ChimFormat_RecordLight (h.minor, rec.flags) == 0 &&
            (rec.flags & CHIM_RECORD_STORY_HIDDEN));
    /* an empty room: no placements, no models */
    n = Room (12, "ROOM", 0, 0);
    assert (ChimFormat_Room (buf, n, &h, &room) && h.count == 0);
    /* refusals */
    n = Room (12, "ROOM", 2, 3);
    assert (!ChimFormat_Room (buf, n - 1, &h, &room));             /* short: the header's size is the file's */
    assert (!ChimFormat_Room (buf, 40, &h, &room));                /* shorter than header and block */
    n = Room (12, "FRAM", 2, 3);
    assert (!ChimFormat_Room (buf, n, &h, &room));                 /* another kind */
    n = Room (12, "XXXX", 2, 3);
    assert (!ChimFormat_Room (buf, n, &h, &room));                 /* no kind at all */
    n = Room (7, "ROOM", 2, 3);
    assert (!ChimFormat_Room (buf, n, &h, &room));                 /* before placed records (0.8) */
    n = Room (CHIM_FORMAT_MINOR + 1, "ROOM", 2, 3);
    assert (!ChimFormat_Room (buf, n, &h, &room));                 /* newer than this engine */
    n = Room (13, "ROOM", 2, 3);
    assert (ChimFormat_Room (buf, n, &h, &room) && h.minor == 13); /* 0.13: light tints */
    n = Room (12, "ROOM", 2, 3);
    U32 (buf + 20, 68);
    assert (!ChimFormat_Room (buf, n, &h, &room));                 /* the model list is not at 64 */
    n = Room (12, "ROOM", 2, 3);
    U32 (buf + 24, 76);
    assert (!ChimFormat_Room (buf, n, &h, &room));                 /* placements not after the model list */
    n = Room (12, "ROOM", 2, 3);
    U32 (buf + 56, 3);
    assert (!ChimFormat_Room (buf, n, &h, &room));                 /* model count against the offsets */
    n = Room (12, "ROOM", 2, 3);
    U32 (buf + 60, 1);
    assert (!ChimFormat_Room (buf, n, &h, &room));                 /* the reserved word */
    n = Room (12, "ROOM", 2, 3);
    F32 (buf + 32, 200);
    assert (!ChimFormat_Room (buf, n, &h, &room));                 /* mins over maxs */
    n = Room (12, "ROOM", 2, 3);
    F32 (buf + 44, (float)NAN);
    assert (!ChimFormat_Room (buf, n, &h, &room));                 /* not a number */
    n = Room (12, "ROOM", 0, 0);
    U32 (buf + 16, 1); U32 (buf + 28, (unsigned long)(n + 56));
    assert (!ChimFormat_Room (buf, n + 56, &h, &room));            /* placements with no models */
    /* room names */
    assert (ChimFormat_RoomNameValid ("bmclagius") && ChimFormat_RoomNameValid ("vivec_hlaalu-1"));
    assert (ChimFormat_RoomNameValid ("abcdefghijklmnopqrstuv"));
    assert (!ChimFormat_RoomNameValid ("abcdefghijklmnopqrstuvw") && !ChimFormat_RoomNameValid (""));
    assert (!ChimFormat_RoomNameValid ("Room") && !ChimFormat_RoomNameValid ("a/b") && !ChimFormat_RoomNameValid ("a.b"));
    puts ("room record: header, block, model list, placed records with the light byte, 13 refusals and room names passed");
    return 0;
}
