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
typedef struct {
    unsigned char sky[4][3],fog[4][3]; /* day, sunrise, sunset, night (r_sky.c stop order) */
    int delta_milli;                   /* Transition Delta x 1000, per real second */
    int glare;                         /* Glare View x 100 */
} aw_weather_look_t;
typedef struct {
    int regions,hours;
    aw_weather_look_t look[AW_WEATHERS];
    unsigned char chances[AW_WEATHER_REGIONS][AW_WEATHERS];
} aw_weather_table_t;
/* The blended look the sky tables use: stops, strength 0..AW_WEATHER_STEPS of
 * the non-clear weather (0 = today's clear sky, unchanged) and glare 0..100. */
typedef struct {
    unsigned char sky[4][3],fog[4][3];
    int strength,glare;
} aw_weather_blend_t;

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
extern const char *const aw_weather_names[AW_WEATHERS];

/* Runtime (aw_weather.c). */
void AW_WeatherInit(void);
/* The look for this frame at the player's exterior position; returns a key that
 * changes whenever the look changes (0 = clear, nothing to blend). */
int AW_WeatherFrame(int days,int milliseconds,aw_weather_blend_t *out);
#endif
