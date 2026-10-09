/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef AW_HORIZON_H
#define AW_HORIZON_H
/* Bounded, exact resident LAND background. No asset allocation or collision. */
void AW_HorizonDraw(byte colour, int distance);
void AW_HorizonReport(void);
/* CHIM far terrain: a regular heightfield drawn beyond the fog plane in the
 * fog colour with the same rasterizer (chim/chim_far.c). */
#define AW_HORIZON_GRID_MAX_BLOCK 16
typedef struct aw_horizon_grid_s {
    const short *heights;   /* ny rows (by y) of nx heights, local units */
    const short *bounds;    /* per block (rows by y): lowest, highest height; NULL: computed */
    int nx, ny, block;      /* samples across and along; quads per block side (1..16) */
    float x0, y0, step;     /* local position of sample (0, 0); spacing in local units */
    float reach;            /* forward depth beyond which nothing is drawn; 0: no limit */
} aw_horizon_grid_t;
void AW_HorizonGrid(const aw_horizon_grid_t *grid, byte colour, int distance, int cull);
/* Last AW_HorizonGrid: blocks, culled near/far/side, drawn, triangles, back
 * faces, polygons, pixels (9 values). */
void AW_HorizonGridCounts(long *out);
#endif
