/* SPDX-License-Identifier: GPL-2.0-or-later */
/* Real sprite projection/rasterization, with an independent ray/plane oracle. */
#include "quakedef.h"
#include "r_local.h"
#include "d_local.h"
#include <assert.h>

#define SIZE 128
#define TW 16
#define TH 32
#define CLEAR 240
#define BACK -1
client_state_t cl;
entity_t *currententity;
vec3_t r_entorigin, r_origin, modelorg, vup, vpn, vright;
clipplane_t view_clipplanes[4];
refdef_t r_refdef;
float xcenter = 64, ycenter = 64, xscale = 64, yscale = 64;
float xscaleinv = 1.0f / 64, yscaleinv = 1.0f / 64;
float d_sdivzstepu, d_tdivzstepu, d_zistepu;
float d_sdivzstepv, d_tdivzstepv, d_zistepv;
float d_sdivzorigin, d_tdivzorigin, d_ziorigin;
fixed16_t sadjust, tadjust, bbextents, bbextentt;
unsigned int d_zwidth = SIZE;
int screenwidth = SIZE, cachewidth;
byte *cacheblock, *d_viewbuffer;
short *d_pzbuffer;
static byte colors[SIZE * SIZE + 2];
static short depths[SIZE * SIZE + 2];

void TransformVector(vec3_t in, vec3_t out)
{
    out[0] = DotProduct(in, vright);
    out[1] = DotProduct(in, vup);
    out[2] = DotProduct(in, vpn);
}
void Q_memcpy(void *out, void *in, int count) { memcpy(out, in, count); }
void D_SetupFixedPointGradients(void) { }
void Con_Printf(char *fmt, ...) { assert(0 && "unexpected sprite warning"); }
void Sys_Error(char *fmt, ...) { assert(0 && "unexpected sprite error"); }

static int oracle(mspriteframe_t *frame, float scale, int x, int y,
                  int *pixel, int *zvalue)
{
    vec3_t ray, offset, hit;
    float distance, denom, s, t, sf, tf;
    int axis;
    for (axis = 0; axis < 3; ++axis)
    {
        ray[axis] = vpn[axis] + vright[axis] * (x - xcenter) / xscale +
                    vup[axis] * (ycenter - y) / yscale;
        offset[axis] = r_entorigin[axis] - r_origin[axis];
    }
    denom = DotProduct(ray, r_spritedesc.vpn);
    if (denom <= 0) return 0;
    distance = DotProduct(offset, r_spritedesc.vpn) / denom;
    for (axis = 0; axis < 3; ++axis)
        hit[axis] = r_origin[axis] + ray[axis] * distance - r_entorigin[axis];
    s = DotProduct(hit, r_spritedesc.vright) / scale - frame->left;
    t = frame->up - DotProduct(hit, r_spritedesc.vup) / scale;
    /* Avoid polygon edges and integer-texel boundaries: the span drawer uses
       fixed point and eight-pixel perspective steps, unlike this exact oracle. */
    if (s < 1 || s >= TW - 1 || t < 1 || t >= TH - 1) return 0;
    sf = s - floor(s); tf = t - floor(t);
    if (sf < .2f || sf > .8f || tf < .2f || tf > .8f) return 0;
    *pixel = frame->pixels[(int)t * TW + (int)s];
    *zvalue = (int)(32768.0f / distance);
    return 1;
}

static void run_case(float entity_scale, int type, float pitch, float side,
                     float left, float up, int check_occlusion)
{
    model_t model;
    entity_t entity;
    msprite_t sprite;
    mspriteframe_t *frame;
    float scale, c = cos(pitch), s = sin(pitch);
    int x, y, axis, i, expected, zvalue, checked = 0, mismatched = 0;
    int opaque = 0, transparent = 0, hidden = 0;
    memset(&model, 0, sizeof(model));
    memset(&entity, 0, sizeof(entity));
    memset(&sprite, 0, sizeof(sprite));
    frame = calloc(1, sizeof(*frame) + TW * TH);
    assert(frame);
    frame->width = TW; frame->height = TH;
    frame->left = left; frame->right = left + TW;
    frame->up = up; frame->down = up - TH;
    for (y = 0; y < TH; ++y)
        for (x = 0; x < TW; ++x)
            frame->pixels[y * TW + x] =
                (x < 3 || x > 12 || (y > 26 && x < 7)) ? 255 :
                10 + y * 4 + x / 4;
    sprite.type = type; sprite.numframes = 1;
    sprite.frames[0].type = SPR_SINGLE; sprite.frames[0].frameptr = frame;
    model.type = mod_sprite; model.cache.data = &sprite;
    entity.model = &model; entity.aw_sprite_scale = entity_scale;
    currententity = &entity;
    scale = entity_scale > 0 ? entity_scale : 1;
    r_entorigin[0] = 81; r_entorigin[1] = side; r_entorigin[2] = -3;
    r_origin[0] = 5; r_origin[1] = 7.3f; r_origin[2] = 11.1f;
    VectorSubtract(r_origin, r_entorigin, modelorg);
    vpn[0] = c; vpn[1] = 0; vpn[2] = s;
    vup[0] = -s; vup[1] = 0; vup[2] = c;
    vright[0] = 0; vright[1] = -1; vright[2] = 0;
    for (axis = 0; axis < 3; ++axis)
    {
        view_clipplanes[0].normal[axis] = vpn[axis] + vright[axis];
        view_clipplanes[1].normal[axis] = vpn[axis] * 63 / 64 - vright[axis];
        view_clipplanes[2].normal[axis] = vpn[axis] + vup[axis];
        view_clipplanes[3].normal[axis] = vpn[axis] * 63 / 64 - vup[axis];
    }
    for (i = 0; i < 4; ++i)
        view_clipplanes[i].dist = DotProduct(r_origin, view_clipplanes[i].normal);
    memset(&r_refdef, 0, sizeof(r_refdef));
    r_refdef.fvrectright_adj = SIZE - 1;
    r_refdef.fvrectbottom_adj = SIZE - 1;
    memset(colors, CLEAR, sizeof(colors));
    for (i = 0; i < SIZE * SIZE + 2; ++i) depths[i] = BACK;
    d_viewbuffer = colors + 1; d_pzbuffer = depths + 1;
    if (check_occlusion)
        for (y = 0; y < SIZE; ++y)
            for (x = 0; x < SIZE; ++x)
                if ((x / 5) % 2) d_pzbuffer[y * SIZE + x] = 32000;
    R_DrawSprite();
    assert(colors[0] == CLEAR && colors[SIZE * SIZE + 1] == CLEAR);
    assert(depths[0] == BACK && depths[SIZE * SIZE + 1] == BACK);
    for (y = 1; y < SIZE - 1; ++y)
        for (x = 1; x < SIZE - 1; ++x)
        {
            if (!oracle(frame, scale, x, y, &expected, &zvalue)) continue;
            ++checked;
            i = y * SIZE + x;
            if (check_occlusion && (x / 5) % 2)
            {
                ++hidden;
                if (d_viewbuffer[i] != CLEAR || d_pzbuffer[i] != 32000) ++mismatched;
            }
            else if (expected == 255)
            {
                ++transparent;
                if (d_viewbuffer[i] != CLEAR || d_pzbuffer[i] != BACK) ++mismatched;
            }
            else
            {
                ++opaque;
                if (d_viewbuffer[i] != expected || abs(d_pzbuffer[i] - zvalue) > 1) ++mismatched;
            }
        }
    printf("scale=%g type=%d pitch=%g side=%g origin=(%g,%g) checked=%d opaque=%d transparent=%d hidden=%d mismatched=%d\n",
           entity_scale, type, pitch, side, left, up, checked, opaque,
           transparent, hidden, mismatched);
    fflush(stdout);
    assert(checked >= 10 && opaque > 0 && transparent > 0);
    assert(!check_occlusion || hidden > 0);
    assert(mismatched == 0);
    free(frame);
}

int main(int argc, char **argv)
{
    if (argc > 1 && !strcmp(argv[1], "scale-only"))
    {
        run_case(2, SPR_VP_PARALLEL, 0, 0, -8, 16, 0);
        return 0;
    }
    /* Centered legacy art, authored base anchors, fractional/large instance
       scales, pitch, clipped posters, transparent roots and foreground slopes. */
    run_case(0, SPR_VP_PARALLEL, 0, 0, -8, 16, 0);
    run_case(1, SPR_VP_PARALLEL, 0, 0, -5, 29, 0);
    run_case(.5f, SPR_VP_PARALLEL, 0, 0, -5, 29, 0);
    run_case(1.75f, SPR_VP_PARALLEL, 0, 0, -5, 29, 0);
    run_case(3, SPR_VP_PARALLEL, .23f, 0, -5, 29, 1);
    run_case(3, SPR_VP_PARALLEL_UPRIGHT, -.17f, 0, -5, 29, 1);
    run_case(3, SPR_FACING_UPRIGHT, .1f, 70, -5, 29, 1);
    puts("sprite mapping: all cases passed");
    return 0;
}
