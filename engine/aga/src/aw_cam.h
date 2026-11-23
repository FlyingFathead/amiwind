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

/* ---- camera shots: dbg cam pan and dbg cam track (docs/CAMERA_MARKS.md "Pan" and "Track") ----
 * A shot as a film camera makes it: the opening frame held, the move with an eased start and stop (the speed rises
 * and falls along aw_ease.h's curve, the Halloween director's) and a constant speed between, the closing frame held.
 * The distance covered is a function of the shot's own clock alone, so any frame times that add up to the same
 * clock give the same frame, and a slow frame moves further, never a fixed step (tests/aga_cam_test.c). */
#define AW_CAM_SHOT_EASE 1.25f     /* seconds of eased speed at each end of the move (less for a very short move) */
#define AW_CAM_SHOT_HOLD 3.0f      /* the default seconds held on the opening and on the closing frame */
#define AW_CAM_SHOT_HOLD_MAX 60.0f
#define AW_CAM_SHOT_MAX_DT .25f    /* a longer frame (a load) counts as this, as the view's own clock: no jump */
/* The pan's default speed: the frame's width in AW_CAM_PAN_CROSS seconds (film's rule of thumb: a thing should take
 * 5 to 7 s to cross the frame, or the pan judders), so the field of view over 6 s: 15 degrees a second at the
 * game's field of view of 90 degrees (the fov setting, screen.c). */
#define AW_CAM_PAN_CROSS 6.0f
#define AW_CAM_PAN_SPEED_MAX 90.0f
#define AW_CAM_PAN_DEGREES_MAX 3600.0f
/* The tracking glide's default speed in map units a second: a slow walk (128 of the original's units a second, under
 * its walking speeds; the map is a quarter of the original's scale, aw_move.h AW_MOVE_UNIT_SCALE). */
#define AW_CAM_TRACK_SPEED 32.0f
#define AW_CAM_TRACK_SPEED_MAX 1024.0f
#define AW_CAM_TRACK_MAX 8192.0f   /* the longest glide, map units */
typedef struct {
    float distance;     /* > 0: degrees (a pan) or map units (a track) */
    float speed;        /* > 0: the constant speed between the eased ends, a second */
    float hold;         /* >= 0: seconds held on the opening and on the closing frame */
    float ease;         /* seconds of eased speed at each end: AW_CAM_SHOT_EASE, or distance/speed when shorter */
    float clock;        /* seconds since the shot began (AW_CamShotStep) */
} aw_cam_shot_t;
/* 1 = SHOT set up for DISTANCE at SPEED with HOLD at each end, its clock at 0; 0 = refused (nothing changed). */
int AW_CamShotBegin(aw_cam_shot_t *shot,float distance,float speed,float hold);
/* The move alone (both eased ends and the constant middle) and the whole shot (two holds and the move), seconds. */
float AW_CamShotMoveSeconds(const aw_cam_shot_t *shot);
float AW_CamShotSeconds(const aw_cam_shot_t *shot);
/* The shot's clock on by DT seconds (negative or not a number: 0; over AW_CAM_SHOT_MAX_DT: that). */
void AW_CamShotStep(aw_cam_shot_t *shot,float dt);
/* The distance covered at the shot's clock, 0..distance (0 through the opening hold, distance from the closing). */
float AW_CamShotTravel(const aw_cam_shot_t *shot);
int AW_CamShotDone(const aw_cam_shot_t *shot);
/* The pan's default speed for the horizontal field of view FOV_X (degrees; out of range: 90). */
float AW_CamPanSpeed(float fov_x);
/* The shortest turn from yaw FROM to yaw TO in degrees: -180 < turn <= 180. */
float AW_CamTurn(float from,float to);
#endif
