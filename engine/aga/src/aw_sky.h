/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef AW_SKY_H
#define AW_SKY_H
/* Reserved semantic depth for sky-filled background spans only. */
#define AW_SKY_BACKGROUND_DEPTH (-32768)
#define AW_SHARED_SKY_PATH "gfx/aw_shared_sky.lmp"
#define AW_SHARED_SKY_BYTES (256*128)
#define AW_NIGHT_SKY_PATH "gfx/aw_night_sky.lmp"
#define AW_NIGHT_SKY_ART_BYTES (128*128+2*8*24*24)
#define AW_NIGHT_SKY_STAR_MASK_BYTES (128*128/8)
#define AW_NIGHT_SKY_PAYLOAD (AW_NIGHT_SKY_ART_BYTES+AW_NIGHT_SKY_STAR_MASK_BYTES)
#define AW_NIGHT_SKY_BYTES (16+AW_NIGHT_SKY_PAYLOAD)
void R_InitDayNight(void);
int R_SkyExterior(void);
/* Current exterior fog ramp; NULL preserves the legacy presentation. */
const unsigned char *R_DayNightFogColours(void);
/* Background-only presentation after depth occlusion. Unnormalised world ray. */
unsigned char R_DayNightSkyPixel(unsigned char colour,float x,float y,float z,int fog);
const float *R_DayNightSunDirection(void);
/* Pure saved-date orbit, independent of renderer caches/assets/settings.
 * Masser=0, Secunda=1. Returns above-horizon; phase is optional (0..7). */
int R_NightMoonOrbit(int moon,int milliseconds,int days,float direction[3],int *phase);
/* Masser=0, Secunda=1; NULL when hidden or no valid owned atlas. */
const float *R_DayNightMoonDirection(int moon);
/* Procedural legacy colors follow the versioned private asset palette remap. */
unsigned char R_SkyLegacyColour(unsigned char index);
/* Validated shared cloud roles use a broader texture projection. */
extern float r_sky_texture_scale;
#endif
