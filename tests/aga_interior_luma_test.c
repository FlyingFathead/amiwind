/* SPDX-License-Identifier: GPL-2.0-or-later */
/* Reuse synthetic real renderer pixels; exercise the real archived cvar too. */
#define main exterior_regression_main
#define AW_TEST_REAL_COMMON
#define Con_Printf Exterior_Con_Printf
#include "aga_exterior_light_fallback_test.c"
#undef main
#undef Con_Printf
server_t sv;
static int torchtest,argument_count=1;
static char *argument="";
static char printed[512];
static void (*luma_command)(void),(*exterior_command)(void);
static int cache_flushes;
void __real_D_FlushCaches(void);
void __wrap_D_FlushCaches(void){cache_flushes++;__real_D_FlushCaches();}
void Con_Printf(char *format,...){va_list ap;va_start(ap,format);vsnprintf(printed,sizeof printed,format,ap);va_end(ap);}
int AW_TorchTestActive(void){return torchtest;}
int Cmd_Argc(void){return argument_count;}
char *Cmd_Argv(int n){return n==1?argument:"aw_interiorluma_set";}
void Cmd_AddCommand(char *name,void (*fn)(void)){if(!strcmp(name,"aw_interiorluma_set"))luma_command=fn;else {assert(!strcmp(name,"aw_exteriorluma_set"));exterior_command=fn;}}
qboolean Cmd_Exists(char *name){return false;}
void *Z_Malloc(int size){return calloc(1,size);}
void Z_Free(void *p){free(p);}
void SV_BroadcastPrintf(char *format,...){assert(0);}
extern unsigned blocklights[18*18];
static void set(char *value){argument_count=value?2:1;argument=value?value:"";luma_command();}
static void factor(float value){assert(fabs(R_InteriorLumaFactor()-value)<.00001f);}
int main(int argc,char **argv)
{
    static const char *const baseline[]={"seyda","balmora","sn031","vf0846",
        "torchtest","charplane","newhouse","bmtemple_unknown"};
    static char *const settings[]={"1.0","1.1","1.2","1.3"};
    static const int expected[]={50,55,60,65};
    /* The original alias path truncates float-to-int: float 1.3 * 50 is
     * just under 65. Surface fixed-point conversion retains more precision. */
    static const int alias_expected[]={50,55,60,64};
    vec3_t point={8,8,24};cvar_t *setting;FILE *f;char saved[256];
    int i,flushes;unsigned static1,dynamic1,static12,dynamic12;byte old_pixel;
    exterior_regression_main();
    R_InteriorLumaInit();setting=Cvar_FindVar("aw_interiorluma");
    assert(setting && setting->archive && luma_command);assert(fabs(setting->value-1.2f)<.00001f);
    sv.active=1;strcpy(sv.name,"census");exterior=0;r_refdef.ambientlight=0;
    surface.samples=samples;surface.styles[0]=0;memset(samples,50,sizeof samples);
    R_InteriorLumaUpdate();factor(1.2f);assert(R_LightPoint(point)==60);
    flushes=cache_flushes;R_InteriorLumaUpdate();R_InteriorLumaUpdate();
    assert(cache_flushes==flushes);
    set("1.2");factor(1.2f);assert(R_LightPoint(point)==60);
    /* Exercise the real classifier before other controls, including caves. */
    assert(argc>1);
    for(i=1;i<argc;i++){
        strcpy(sv.name,argv[i]);assert(AW_Interior());R_InteriorLumaUpdate();factor(1.2f);
        assert(R_LightPoint(point)==60);render(0,0,0,0);
        assert(blocklights[0]==(unsigned)((255-60)<<VID_CBITS));
    }
    set("1");factor(1);assert(R_LightPoint(point)==50);render(0,0,0,0);old_pixel=pixels[0][0];
    /* Query preserves the saved setting; changed gain must invalidate caches. */
    set(NULL);factor(1);set("1.2");factor(1.2f);
    assert(D_CacheSurface(&surface,0)->data[0]>old_pixel);
    set("0");factor(0);assert(R_LightPoint(point)==0);render(0,0,0,0);render(1,0,0,1);
    assert(pixels[1][0]>pixels[0][0]);
    set("1");render(0,0,0,0);static1=blocklights[0];render(1,0,0,1);dynamic1=blocklights[0];
    set("1.2");render(0,0,0,0);static12=blocklights[0];render(1,0,0,1);dynamic12=blocklights[0];
    assert(static1-dynamic1==static12-dynamic12);
    /* Check the real surface's inverted fixed-point light and alias sample:
     * one gain only, not compounded on the previous setting or update. */
    for(i=0;i<4;i++){
        set(settings[i]);R_InteriorLumaUpdate();R_InteriorLumaUpdate();
        assert(R_LightPoint(point)==alias_expected[i]);render(0,0,0,0);
        assert(blocklights[0]==(unsigned)((255-expected[i])<<(VID_CBITS)));
        flushes=cache_flushes;R_InteriorLumaUpdate();R_InteriorLumaUpdate();
        assert(cache_flushes==flushes);
    }
    set("-3");factor(0);set("8");factor(4);set("1.2");
    set("nan");factor(1.2f);set("inf");factor(1.2f);set("oops");factor(1.2f);set("1x");factor(1.2f);
    Cvar_Set("aw_interiorluma","nan");R_InteriorLumaUpdate();factor(1.2f);assert(isfinite(setting->value));
    Cvar_Set("aw_interiorluma","inf");R_InteriorLumaUpdate();factor(1.2f);
    Cvar_Set("aw_interiorluma","oops");R_InteriorLumaUpdate();factor(1.2f);
    setting->value=NAN;R_InteriorLumaUpdate();factor(1.2f);assert(isfinite(setting->value));
    Cvar_Set("aw_interiorluma","-8");R_InteriorLumaUpdate();factor(0);
    Cvar_Set("aw_interiorluma","9");R_InteriorLumaUpdate();factor(4);set("1.2");
    set(NULL);assert(strstr(printed,"1.200") && strstr(printed,"gameplay interior"));
    for(i=0;i<sizeof baseline/sizeof baseline[0];i++){
        strcpy(sv.name,baseline[i]);R_InteriorLumaUpdate();factor(1);
        assert(R_LightPoint(point)==50);render(0,0,0,0);
        assert(blocklights[0]==(unsigned)((255-50)<<VID_CBITS));
    }
    /* Raw torchtest entry is exempt even when the explicit mode is inactive. */
    strcpy(sv.name,"torchtest");assert(AW_Interior());set(NULL);factor(1);
    assert(strstr(printed,"effective 1.000") && strstr(printed,"baseline/excluded"));
    strcpy(sv.name,"bmtemple");R_InteriorLumaUpdate();factor(1.2f);
    torchtest=1;R_InteriorLumaUpdate();factor(1);torchtest=0;
    sv.active=0;R_InteriorLumaUpdate();factor(1);sv.active=1;
    /* The actual config writer archives the chosen override, not the default. */
    set("1.7");f=tmpfile();assert(f);Cvar_WriteVariables(f);rewind(f);
    {size_t n=fread(saved,1,sizeof saved-1,f);saved[n]=0;}fclose(f);assert(strstr(saved,"aw_interiorluma \"1.700000\""));
    Cvar_Set("aw_interiorluma","1.0");Cvar_Set("aw_interiorluma","1.700000");R_InteriorLumaUpdate();factor(1.7f);
    /* The player slider is six exact tenths and archives the actual setting. */
    for(i=10;i<=15;i++){
        R_InteriorBrightnessSetStep(i);assert(R_InteriorBrightnessStep()==i);
        assert(fabs(setting->value-i*.1f)<.00001f);
        flushes=cache_flushes;R_InteriorBrightnessSetStep(i);assert(cache_flushes==flushes);
    }
    R_InteriorBrightnessSetStep(-100);factor(1);assert(R_InteriorBrightnessStep()==10);
    R_InteriorBrightnessSetStep(999);factor(1.5f);assert(R_InteriorBrightnessStep()==15);
    /* The exterior knob is independent and follows validated scene lighting. */
    assert(exterior_command && Cvar_FindVar("aw_exteriorluma")->archive);
    strcpy(sv.name,"seyda");exterior=1;R_InteriorLumaUpdate();factor(1);
    R_BrightnessSetStep(1,13);factor(1.3f);assert(R_BrightnessStep(0)==15);
    set("1.2");factor(1.3f); /* Interior changes cannot change exterior gain. */
    strcpy(sv.name,"census");exterior=0;R_InteriorLumaUpdate();factor(1.2f);
    R_BrightnessSetStep(1,15);factor(1.2f);
    strcpy(sv.name,"seyda");exterior=1;R_InteriorLumaUpdate();factor(1.5f);
    Cvar_Set("aw_exteriorluma","nan");R_InteriorLumaUpdate();factor(1);
    assert(isfinite(Cvar_FindVar("aw_exteriorluma")->value));
    strcpy(sv.name,"torchtest");R_InteriorLumaUpdate();factor(1);
    puts("all authored interiors: real scene classification, static pixels/alias, single 1.0/1.1/1.2/1.3 gain, cache refresh, dynamic independence, bounds/nonfinite, exclusions and archived override passed");
    return 0;
}
