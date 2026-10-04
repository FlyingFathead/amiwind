/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef AW_BOOLEAN_H
#define AW_BOOLEAN_H
/* Explicit boolean registry. Never infer a type from the current value:
 * distance, font size and layout selectors may also happen to equal 0 or 1. */
static int AW_BooleanCvar(const char *name) {
    static const char *const names[]={"aw_daynightcycle","aw_daynight","aw_sun","aw_clouds","aw_starsky","aw_nightsky","guards_torch_cycle","aw_fog","aw_cull","aw_compass","aw_ui_hud","aw_ui_frame",
        "aw_intro_text_overlay","aw_show_speaker_name_during_voiceovers",
        "aw_allow_poly_budget_over","aw_input_trace","aw_door_sounds","aw_target_names","early_game_demo_start_1","_aw_debug_all",
        "_aw_debug_coords","_aw_debug_fps","_aw_debug_sealevel","showram",
        "r_drawentities","r_drawworld","r_fullbright","r_drawviewmodel",
        "cl_nolerp","lookspring","lookstrafe",NULL};
    int i;for(i=0;names[i];i++)if(!strcmp(name,names[i]))return 1;
    return 0;
}
static int AW_ParseBoolean(char *s) {
    if(!Q_strcasecmp(s,"true") || !Q_strcasecmp(s,"on") || !strcmp(s,"1"))return 1;
    if(!Q_strcasecmp(s,"false") || !Q_strcasecmp(s,"off") || !strcmp(s,"0"))return 0;
    return -1;
}
#endif
