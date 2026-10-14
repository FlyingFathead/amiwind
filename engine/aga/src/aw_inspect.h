/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef AW_INSPECT_H
#define AW_INSPECT_H
void AW_InspectInit(void);
/* Optional hooks keep the ordinary input/render/server paths independent. */
extern int (*aw_inspect_buttons)(int bits);
extern int (*aw_inspect_crosshair)(void);
extern void (*aw_inspect_draw)(void);
extern void (*aw_inspect_reset)(void);
#endif
