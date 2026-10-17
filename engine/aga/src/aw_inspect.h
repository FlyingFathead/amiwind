/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef AW_INSPECT_H
#define AW_INSPECT_H
void AW_InspectInit(void);
/* dbg cam orbit: the target under the rendered crosshair (aw_inspect.c). */
int AW_InspectTarget(int *edict,float *focal);
struct entity_s;
int AW_InspectFrameCentre(struct entity_s *candidate,float *out);
/* Optional hooks keep the ordinary input/render/server paths independent. */
extern int (*aw_inspect_buttons)(int bits);
extern int (*aw_inspect_crosshair)(void);
extern void (*aw_inspect_reset)(void);
/* The CHIM placement a view ray hits (INSPECT-CHIM-PLACEMENT-UNNAMED-42): a placed
 * model in a CHIM frame collides as the world, so the pin asks the frame which
 * placement record it was. Set by Chim_Init; NULL without a CHIM map. */
typedef struct {
    float fraction;               /* along start->end, as SV_Move reports it */
    unsigned pid,ref,model;       /* placement id, Morrowind reference (FRMR), model id */
    int cell_x,cell_y;            /* original exterior cell of the reference */
    float origin[3],yaw;          /* local units, degrees */
    char name[64];                /* the model's name in the CHIM index, "" if unread */
} aw_chim_pick_t;
extern int (*aw_chim_pick)(const float *start,const float *end,aw_chim_pick_t *out);
/* INSPECT-OVER-VIEWPORT-42: nothing is drawn over the 3D view, the stat bars or the weapon/magic
 * boxes. While inspect is on, aw_hud.c draws the hint and up to three lines of the pinned snapshot
 * underneath the health/magic/fatigue bars, at the bottom of the screen ("underneath the player
 * stats HUD", the maintainer); the bars, the boxes and the coordinate rows move up by
 * AW_INSPECT_LIFT pixels to make room, and screen.c grows the strip under the view to
 * AW_INSPECT_SB_LINES lines (the normal 48 + the lift). */
#define AW_INSPECT_LINE 128
#define AW_INSPECT_BOTTOM_LINES 4
#define AW_INSPECT_LINE_STEP 9
#define AW_INSPECT_LIFT (AW_INSPECT_BOTTOM_LINES*AW_INSPECT_LINE_STEP)
#define AW_INSPECT_SB_LINES (48+AW_INSPECT_LIFT)
/* aw_hud.c: AW_INSPECT_LIFT while the inspect lines are shown under the bars, else 0. */
int AW_InspectHudLift(void);
extern const char *(*aw_inspect_hint)(void);
extern int (*aw_inspect_strip)(char lines[][AW_INSPECT_LINE],int max,int width);
int AW_InspectEnabled(void);
/* keys.c: the right (and middle) mouse button leaves inspect mode. */
extern int (*aw_inspect_key)(int key);
#endif
