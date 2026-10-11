/* SPDX-License-Identifier: GPL-2.0-or-later
 * The player's view: first or third person, the held-key orbit (preview),
 * the idle orbit (vanity), the wheel zoom, and the death scene
 * (docs/THIRD_PERSON.md).
 *
 * The rules are the original game's as OpenMW 0.51 reproduces them
 * (files/data/scripts/omw/camera/camera.lua, third_person.lua,
 * apps/openmw/mwrender/camera.cpp, mwmechanics/character.cpp,
 * mwmechanics/actors.cpp, mwstate/statemanagerimp.cpp) and the game's own
 * settings (fVanityDelay, sLoadLastSaveMsg, sYes, sNo), scaled 0.25 to game
 * units. Quake mechanism: the chase camera (chase.c chase_active: the client
 * draws the player's own entity, the first-person hands are not drawn).
 *
 * The pure part below has no engine dependencies (host-tested,
 * tests/aga_view_test.c).
 */
#ifndef AW_VIEW_H
#define AW_VIEW_H

enum {AW_VIEW_FIRST, AW_VIEW_THIRD, AW_VIEW_PREVIEW, AW_VIEW_VANITY, AW_VIEW_DEATH};

typedef struct {
    float switch_limit;   /* camera.lua updatePOV switchLimit: a shorter Toggle POV press switches, a longer one orbits */
    float vanity_delay;   /* GMST fVanityDelay (seconds idle before the vanity orbit) */
    float vanity_rate;    /* camera.lua updateVanity: degrees per second */
    float base_distance;  /* third_person.lua M.baseDistance x 0.25 */
    float min_distance;   /* camera.lua minDistance x 0.25 */
    float max_distance;   /* camera.lua maxDistance x 0.25 */
    float zoom_step;      /* actionbindings.lua Zoom3rdPerson: 10 per wheel click, x 0.25 */
    float height;         /* camera.cpp mHeight 124 above the feet, x 0.25 */
    float obstacle;       /* camera.cpp cameraObstacleLimit 5, x 0.25 */
} aw_view_rules_t;

typedef struct {
    int mode, primary;    /* the current mode; the primary mode (first or third) */
    float pov_held;       /* camera.lua previewTimer */
    float idle;           /* camera.lua idleTimer */
    float distance;       /* third_person.lua baseDistance (game units) */
    float orbit_yaw, orbit_pitch;   /* the camera's turn around the player (preview, vanity) */
} aw_view_t;

void AW_ViewRulesDefault(aw_view_rules_t *r);
void AW_ViewReset(aw_view_t *v,const aw_view_rules_t *r);
/* One frame of the Toggle POV key (camera.lua updatePOV): held = the key is down. */
void AW_ViewPOV(aw_view_t *v,const aw_view_rules_t *r,int held,float dt);
/* A Toggle POV press released before the next frame saw it: one short press (CAMERA-POV-TAP-LOST-36). */
void AW_ViewPOVTap(aw_view_t *v,const aw_view_rules_t *r);
/* One frame of the idle clock and the vanity orbit (camera.lua updateIdleTimer + updateVanity):
 * input = any key, mouse or movement this frame; allowed = vanity may start (alive, in game, enabled). */
void AW_ViewIdle(aw_view_t *v,const aw_view_rules_t *r,int input,int allowed,float dt);
/* The wheel (camera.lua zoom): delta > 0 zooms in (10 per click in the original, here r->zoom_step). */
void AW_ViewZoom(aw_view_t *v,const aw_view_rules_t *r,float delta);
/* The camera stands behind the player (every mode but first person). */
int AW_ViewBehind(const aw_view_t *v);
/* camera.cpp updatePosition: the distance after an obstacle at fraction (0..1) of the preferred
 * distance; the camera stays obstacle units in front of it. */
float AW_ViewObstacle(float preferred,float fraction,float obstacle);

/* ---- the death scene (PLAYER-DEATH-LIMBO-35, COMBAT-PLAYER-DEATH-FALL-33) ---- */
enum {AW_DEATH_NONE, AW_DEATH_FALLING, AW_DEATH_ASK, AW_DEATH_MAIN_MENU};
/* The choices: the original's Yes (load the most recent save) and No (main menu), and the
 * AmiWind quick retry of a lost fight (build-config switch, default on). */
enum {AW_DEATH_LOAD, AW_DEATH_MENU, AW_DEATH_RETRY, AW_DEATH_CHOICES};
typedef struct {
    int stage;
    float time, fall;     /* seconds since death; the death animation's length */
    int choice[AW_DEATH_CHOICES], count, selection;
} aw_death_t;
/* fall: the death animation's length. retry: the quick retry is offered. saved: a save exists.
 * OpenMW askLoadRecent: with no save and no retry the game goes straight to the main menu. */
void AW_DeathBegin(aw_death_t *d,float fall,int retry,int saved);
/* Advance; returns the stage. The prompt appears when the death animation has finished
 * (actors.cpp Result_DeathAnimJustFinished -> askLoadRecent). */
int AW_DeathStep(aw_death_t *d,float dt);
/* A key on the prompt: 1 left, 2 right, 3 accept, 4 yes, 5 no. Returns the chosen choice or -1. */
int AW_DeathKey(aw_death_t *d,int key);
void AW_DeathEnd(aw_death_t *d);

/* ---- engine part (aw_view.c) ---- */
#ifndef AW_VIEW_HOST_TEST
struct entity_s;
void AW_ViewInit(void);
void AW_ViewFrame(void);            /* once per client frame, before the view is set up */
int AW_ViewCamera(void);            /* replaces Chase_Update while the view is ours; 1 = done */
void AW_ViewRoll(void);             /* the third-person and death views keep the horizon level */
struct entity_s *AW_ViewBody(struct entity_s *ent);   /* the player's body for the drawn view entity, or NULL */
void AW_ViewInput(int key,int down);/* every key event: the idle clock, Toggle POV */
int AW_ViewKey(int key);            /* the death prompt's keys; 1 = used */
void AW_ViewDraw(void);             /* the death prompt */
int AW_ViewThirdPerson(void);       /* hands and torch model hidden */
int AW_ViewVanityFullscreen(void);   /* the vanity orbit draws the full-screen view, no HUD (aw_vanity_fullview) */
int AW_DeathLocked(void);           /* the player is dead: no talk, activate, attack or movement */
void AW_ViewSceneSpawn(void);       /* a new map: the death scene ends */
#endif
#endif
