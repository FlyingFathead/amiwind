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

/* Pure rules (aw_weather_rules.c, host-tested). */
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
