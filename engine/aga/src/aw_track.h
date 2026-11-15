/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef AW_TRACK_H
#define AW_TRACK_H
/* Object tracks (ENDGAME-CHAMBER-COLLAPSE-63, the track mode beside DOOR-MOVERS-56's hinge and slide): the movers of
 * an animated world object (the Heart Chamber's collapse) and each one's world transform per frame, as the builder
 * writes them (tools/object_movers.py, record 'AWTK' version 1, big-endian). A group of the object plays its movers
 * along their tracks from its start, holding the last frame (OpenMW holds an object's last pose when a group ends).
 * No quakedef.h: plain C on the record's bytes, so the host's native test builds it alone. */

#define AW_TRACK_MAGIC "AWTK"
#define AW_TRACK_VERSION 1
#define AW_TRACK_HEAD 20      /* magic, version, movers, frames, rate x 16, f32 unit, sounds, 0 */
#define AW_TRACK_MOVER 36     /* u16 node, u16 0, 32-byte name */
#define AW_TRACK_NAME 32
#define AW_TRACK_SOUND 32     /* u16 frame, 30-byte sound id */
#define AW_TRACK_SOUND_NAME 30
#define AW_TRACK_FRAME 14     /* 7 x s16: x, y, z in units, quaternion w, x, y, z x 32767 */
#define AW_TRACK_MAX_MOVERS 64

typedef struct {
    const unsigned char *data;  /* the record (kept by the caller while the track is used) */
    int bytes;
    int movers,frames,sounds;
    float rate,unit;            /* frames a second; game units per position step */
    int names_at,sounds_at,frames_at;
} aw_track_t;

/* Read a record: 1 when it is whole and consistent, 0 refused (wrong magic or version, sizes that do not fit). */
int AW_TrackParse(const unsigned char *data,int bytes,aw_track_t *t);
/* The seconds a group plays: (frames - 1) / rate. */
float AW_TrackSeconds(const aw_track_t *t);
/* Mover M's node number and name (NUL-terminated, at most AW_TRACK_NAME - 1 characters); -1 for no such mover. */
int AW_TrackMover(const aw_track_t *t,int m,char *name,int size);
/* Mover M at SECONDS since the group started: position (game units, the object's own space) and unit quaternion
 * (w, x, y, z), linear between frames, the quaternions by normalised lerp on the shorter arc; before 0 the first
 * frame, past the end the last (held). 0 for no such mover. */
int AW_TrackSample(const aw_track_t *t,int m,float seconds,float pos[3],float quat[4]);
/* The sound keys whose frame lies in (FROM, TO] seconds (the first frame when FROM < 0): each one's id copied to
 * out[k] (AW_TRACK_SOUND_NAME bytes each), at most MAX; returns how many. */
int AW_TrackSoundsBetween(const aw_track_t *t,float from,float to,char (*out)[AW_TRACK_SOUND_NAME],int max);
/* A unit quaternion as a row-vector 3x3 rotation (p' = p * m), the layout tools/object_movers.quaternion reads. */
void AW_TrackMatrix(const float quat[4],float m[3][3]);
#endif
