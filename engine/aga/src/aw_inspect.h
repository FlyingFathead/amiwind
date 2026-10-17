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
extern void (*aw_inspect_draw)(void);
extern void (*aw_inspect_reset)(void);
#endif
