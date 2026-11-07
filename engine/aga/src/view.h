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
// view.h

extern	cvar_t		v_gamma;

extern	byte		gammatable[256];	// palette is sent through this
extern	byte		ramps[3][256];
extern float v_blend[4];

extern cvar_t lcd_x;


void V_Init (void);
void V_RenderView (void);
float V_CalcRoll (vec3_t angles, vec3_t velocity);
/* FP-FOREARMS-BELOW-VIEW-61: the first-person model's own view (view.c aw_fp_view): OpenMW 0.51's first-person field
 * of view (degrees, vertical) and the share of the view's pitch its first-person neck turns the arms by */
extern cvar_t aw_fp_view;
#define V_FP_FOV 60.0f
#define V_FP_NECK .75f
float V_FirstPersonScale (float tan_half, float half, float yscale);
float V_FirstPersonPitch (float pitch, float factor);
/* r_main.c: 1 = the first-person model's projection from here on, 0 = the world's back */
void R_FirstPersonProjection (int on);
void V_UpdatePalette (void);
/* A script's FadeOut / FadeIn / FadeTo: the screen's black to TARGET (0 none .. 1 black) over SECONDS (view.c). */
void V_ScreenFade (float target, float seconds);
float V_ScreenFadeLevel (void);
float V_ScreenFadeTarget (void);
