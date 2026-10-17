/* SPDX-License-Identifier: GPL-2.0-or-later
 * Named camera marks (dbg cam mark / recall / list, docs/CAMERA_MARKS.md).
 * aw_cam_rules.c: the marks file line format, no engine dependencies
 * (host-tested, tests/aga_cam_test.c); aw_cam.c: the console command. */
#ifndef AW_CAM_H
#define AW_CAM_H

#define AW_CAM_MAGIC "AWCM1"
#define AW_CAM_NAME 32          /* name: 1..31 of A-Z a-z 0-9 _ - . (matched without case) */
#define AW_CAM_MAP 16           /* a map name: 1..15 of a-z 0-9 _ */
#define AW_CAM_NOTE 160
#define AW_CAM_LINE 384         /* one line, without its line end */
#define AW_CAM_FILE_BYTES 16384 /* each marks file */
#define AW_CAM_GLOBAL_BOUND 2000000.0  /* as dbg tp X Y [Z] */
#define AW_CAM_LOCAL_BOUND 32768.0     /* as aw_view; the engine also applies its own range */

typedef struct {
    char name[AW_CAM_NAME];
    int global;               /* 1: original Morrowind coordinates (the map is chosen as dbg tp does) */
    char map[AW_CAM_MAP];     /* global 0: the map, coordinates in its local units */
    float point[3];
    int has_z;                /* global: 0 = X Y (on the ground there), 1 = X Y Z (first floor at or below Z) */
    float yaw,pitch;          /* yaw 0..<360, pitch -80..80 (as aw_aim / aw_view) */
    int time;                 /* HHMM 0000..2359, -1 = left as it is */
    int headlamp;             /* 0 off, 1 on, -1 left as it is */
    int fog;                  /* fog/draw distance 100..4096, -1 left as it is */
    char note[AW_CAM_NOTE];
} aw_cam_mark_t;

int AW_CamValidName(const char *name);
int AW_CamSameName(const char *a,const char *b);
/* 1 = a mark, 0 = a comment or an empty line, -1 = invalid. LINE has no line end. */
int AW_CamParse(const char *line,aw_cam_mark_t *mark);
/* The line for MARK without its line end; 0 when it does not fit or is invalid. */
int AW_CamFormat(const aw_cam_mark_t *mark,char *out,int size);
#endif
