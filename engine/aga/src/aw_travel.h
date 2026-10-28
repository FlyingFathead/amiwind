/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef AW_TRAVEL_H
#define AW_TRAVEL_H
/* The travel services (TRAVEL-SERVICES-CHIM-51): id1/travel.txt (tools/prepare_travel.py) holds every caravaner,
 * shipmaster, gondolier and guild guide of the game data with its destinations on this image's maps. The rules
 * (aw_travel_rules.c) are host-tested by tests/aga_travel_test.c; aw_scene.c opens the menu and makes the ride. */
#define AW_TRAVEL_ROWS 4          /* tools/prepare_travel.py ROWS_PER_PROVIDER: the most any provider of the three
                                     masters offers, and what the menu box holds with Cancel */
#define AW_TRAVEL_LABEL 48        /* tools/prepare_travel.py LABEL_BYTES + 1 */
#define AW_TRAVEL_MAP 16
typedef struct {
    char map[AW_TRAVEL_MAP];      /* the map to load (a town or region frame, a room) */
    float arrival[3],yaw;         /* where the player stands there, in that map's units */
    float source[3];              /* the destination in the original coordinates (the price and hours) */
    int price,hours;              /* the build's price and hours from the provider's own placement */
    char label[AW_TRAVEL_LABEL];  /* the destination's cell name (or region name outdoors) */
} aw_travel_row_t;
typedef struct {
    float mult,time_mult;         /* fTravelMult, fTravelTimeMult */
    int guild_price;              /* fMagesGuildTravel */
    int interior;                 /* the provider stands in an interior: the guild price, no time passes */
    int count;
    aw_travel_row_t rows[AW_TRAVEL_ROWS];
} aw_travel_t;
/* The rows of PROVIDER (an actor record id, compared without case) in TEXT, the whole table file. Returns the row
 * count (0: the provider offers no destination this image holds), -1 when TEXT is not a travel table. */
int AW_TravelParse(const char *text,const char *provider,aw_travel_t *out);
/* The price and hours of ROW: from PLAYER (the player's original coordinates; NULL when unknown) as OpenMW reckons
 * them, else the table's own. */
void AW_TravelCost(const aw_travel_t *t,int row,const float *player,int *price,int *hours);
#endif
