/* SPDX-License-Identifier: GPL-2.0-or-later
 * Region weather (SKY-REDMOUNTAIN-BLUE-44, docs/DAY_NIGHT_AND_SKY.md "Region weather"): every
 * exterior region draws the weather its REGN record's chances give it, with the
 * sky and fog colours of that weather (world/region-weather.aww, written by the
 * builder from the game's records and Morrowind.ini). Rules from OpenMW file
 * apps/openmw/mwworld/weather.cpp (read, not copied): a roll 1..100 against the
 * running sum of the chances picks the weather, a chance list that does not
 * reach the roll gives Clear; a region's weather is chosen again every "Hours
 * Between Weather Changes" game hours; walking into another region moves to its
 * weather at that weather's Transition Delta (per real second); arriving by
 * teleport or a load switches at once. AmiWind's own choices: the roll is a
 * hash of the region and the game-hour period, so it needs no save field, and a
 * transition is drawn in AW_WEATHER_STEPS steps so the sky tables are rebuilt
 * at most that often.
 */
#ifndef AW_WEATHER_H
#define AW_WEATHER_H
#define AW_WEATHERS 10
#define AW_WEATHER_CLEAR 0
#define AW_WEATHER_BLIGHT 7
#define AW_WEATHER_REGIONS 256
#define AW_WEATHER_STEPS 16
#define AW_WEATHER_PATH "world/region-weather.aww"
/* Two table versions: AWW1 (sky and fog stops, 32 bytes per weather) and AWW2
 * (WEATHER-AMBIENT-SUN-UNUSED-51: also the Ambient and Sun colour stops of
 * Morrowind.ini, 56 bytes per weather). An AWW1 table lights the land as before. */
#define AW_WEATHER_LOOK_V1 32
#define AW_WEATHER_LOOK_V2 56
typedef struct {
    unsigned char sky[4][3],fog[4][3]; /* day, sunrise, sunset, night (r_sky.c stop order) */
    unsigned char ambient[4][3],sun[4][3]; /* AWW2 only: Ambient / Sun Day, Sunrise, Sunset, Night Color */
    int delta_milli;                   /* Transition Delta x 1000, per real second */
    int glare;                         /* Glare View x 100 */
} aw_weather_look_t;
typedef struct {
    int regions,hours,light;           /* light: the table carries ambient and sun stops (AWW2) */
    aw_weather_look_t look[AW_WEATHERS];
    unsigned char chances[AW_WEATHER_REGIONS][AW_WEATHERS];
} aw_weather_table_t;
/* The blended look the sky tables use: stops, strength 0..AW_WEATHER_STEPS of
 * the non-clear weather (0 = today's clear sky, unchanged) and glare 0..100;
 * the blended ambient and sun stops with the clear weather's beside them, so
 * the land's light can follow the weather relative to the clear look the
 * engine's own day/night light already draws (light 0: no light stops). */
typedef struct {
    unsigned char sky[4][3],fog[4][3];
    unsigned char ambient[4][3],sun[4][3],clear_ambient[4][3],clear_sun[4][3];
    int strength,glare,light;
} aw_weather_blend_t;
/* The land's light under a weather (WEATHER-AMBIENT-SUN-UNUSED-51): rule from
 * OpenMW file apps/openmw/mwworld/weather.cpp (read, not copied): exteriors are
 * lit by the weather's ambient colour plus its sun colour, each blended between
 * the time-of-day stops. The engine's baked light already holds the clear
 * weather, so the land takes the RATIO of the weather's light to the clear
 * weather's: per channel (ambient + sun x AW_WEATHER_SUN_SHARE/256) against the
 * same sum of Clear, in 1/256 (256 = unchanged), clamped. The sun counts at its
 * average share on lit ground (half). */
#define AW_WEATHER_SUN_SHARE 128
#define AW_WEATHER_TONE_MIN 32
#define AW_WEATHER_TONE_MAX 384
void AW_WeatherLightTone(const aw_weather_blend_t *blend,int a,int b,int mix,int *tone);

/* The weather in effect at the player (SKY-REDMOUNTAIN-BLUE-44, 46): rules from OpenMW file
 * apps/openmw/mwworld/weather.cpp (read, not copied). A new weather (another region walked into, a
 * new period) starts a transition when none runs; while one runs it is queued and starts when the
 * running one ends (addWeatherTransition), never a jump back. A cell without a region keeps the
 * weather it had (updateWeatherRegion ignores an empty region). Only an arrival (the first frame, a
 * jump of over half a cell: travel, a door to elsewhere, a load; or a wait, rest or travel of an hour
 * or more of game time) puts the weather there at once (playerTeleported / advanceTime); a walked
 * crossing into another frame map, however long its load, is not an arrival. */
#define AW_WEATHER_NONE (-1)
#define AW_WEATHER_ARRIVAL_UNITS 4096.0  /* half a cell (8,192 original units) */
#define AW_WEATHER_ARRIVAL_HOURS 1
typedef struct {
    int current,next,queued;   /* next/queued AW_WEATHER_NONE when no transition runs or waits */
    double progress;           /* 0..1 of current -> next */
    int region;                /* the last region with a name, -1 none yet */
} aw_weather_state_t;

/* Pure rules (aw_weather_rules.c, host-tested). */
void AW_WeatherForce(aw_weather_state_t *s,int weather);
void AW_WeatherAddTransition(aw_weather_state_t *s,int weather);
void AW_WeatherAdvance(aw_weather_state_t *s,const aw_weather_table_t *table,double seconds);
int AW_WeatherRegionKeep(aw_weather_state_t *s,int region);
int AW_WeatherIsArrival(int have_last,double dx,double dy,long hours_passed);
int AW_WeatherChoose(const unsigned char *chances,int count,int roll);
int AW_WeatherRoll(int region,int period);
int AW_WeatherPeriod(int days,int milliseconds,int hours);
int AW_WeatherParse(const unsigned char *raw,long size,aw_weather_table_t *out);
int AW_WeatherOfRegion(const aw_weather_table_t *table,int region,int days,int milliseconds);
void AW_WeatherBlend(const aw_weather_table_t *table,int from,int to,int step,aw_weather_blend_t *out);
int AW_WeatherIndex(const char *name);
/* Storms (ACTOR-STORM-POSE-51): rules from OpenMW files apps/openmw/mwworld/weather.cpp and
 * apps/openmw/mwmechanics/character.cpp (read, not copied). An ash or blight storm blows outward from Red Mountain
 * (original units 25000, 70000) at the player's position; during a transition the weather being left counts until
 * half way, then the one arriving. An actor shields its eyes (idlestorm, torso and right arm) when it faces into the
 * wind: its forward direction against the storm's below -0.5. */
#define AW_WEATHER_ASH 6
#define AW_WEATHER_RED_MOUNTAIN_X 25000.0f
#define AW_WEATHER_RED_MOUNTAIN_Y 70000.0f
int AW_WeatherIsStorm(int current,int next,double progress);
/* Falling weather (WEATHER-RAIN): what falls in a weather (AW_PRECIP_*) and how strongly 0..AW_WEATHER_STEPS
 * during a transition: the leaving weather's fades out over the first half, the arriving weather's comes in over
 * the second (OpenMW mwworld/weather.cpp starts the rain once a transition passes its Rain Threshold, 0.6 as
 * Morrowind.ini ships it; read, not copied). */
#define AW_PRECIP_NONE 0
#define AW_PRECIP_RAIN 1
#define AW_PRECIP_HEAVY_RAIN 2
#define AW_PRECIP_ASH 3
#define AW_PRECIP_SNOW 4
#define AW_PRECIP_BLIZZARD 5
int AW_WeatherPrecipOf(int weather);
int AW_WeatherPrecip(int current,int next,double progress,int *strength);
/* the storm's direction at an original-world position (unit, x y); 0 at Red Mountain itself */
int AW_WeatherStormDirection(const float *source,float dir[2]);
/* 1 when an actor at yaw degrees (Quake: 0 = +x, 90 = +y; the original world's axes) faces into the storm */
int AW_WeatherFacesStorm(float yaw,const float dir[2]);
extern const char *const aw_weather_names[AW_WEATHERS];

/* Runtime (aw_weather.c). */
void AW_WeatherInit(void);
/* The look for this frame at the player's exterior position; returns a key that
 * changes whenever the look changes (0 = clear, nothing to blend). */
int AW_WeatherFrame(int days,int milliseconds,aw_weather_blend_t *out);
/* 1 when the weather lights the land too (aw_weather 1, the default); 0 for aw_weather 2 (sky and fog only). */
int AW_WeatherLightOn(void);
/* 1 with the storm's direction while an ash or blight storm blows at the player this frame (exteriors, region
 * weather on; set by AW_WeatherFrame, so it follows the sky). */
int AW_WeatherStorm(float dir[2]);
/* What falls at the player this frame (AW_PRECIP_*, strength 0..AW_WEATHER_STEPS); AW_PRECIP_NONE indoors. */
int AW_WeatherFalling(int *strength);
/* aw_atmos.c: the falling weather and the mesh smoke (WEATHER-RAIN, MESH-PARTICLE-EMITTERS); the update runs each
 * client frame after CL_UpdateTEnts (cl_main.c), the init with the weather's (r_sky.c). */
void AW_AtmosInit(void);
void AW_AtmosUpdate(void);
#endif
