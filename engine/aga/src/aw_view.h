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
#include "aw_anim.h"

enum {AW_VIEW_FIRST, AW_VIEW_THIRD, AW_VIEW_PREVIEW, AW_VIEW_VANITY, AW_VIEW_DEATH};

/* Player-only alias grids: five movement groups for draw/lower/punch.
 * No additions to the shared NPC layout or per-vertex renderer. */
#define AW_VIEW_LAYER_ROWS 15
typedef struct {
    short motion, base;
    unsigned char count, phases, action, grid_count;
    unsigned short hit_permille;
} aw_view_layer_t;
typedef struct {aw_view_layer_t rows[AW_VIEW_LAYER_ROWS];int count;} aw_view_layers_t;
/* Optional $action:motion_base:motion_count:grid_base:arm_phases[:grid_count[:hit_permille]] ANM words.
 * Five-field rows retain the original one-grid-pose-per-motion-frame rule.
 * Malformed or incomplete tables clear the entire table and return 0. */
int AW_ViewLayersParse(aw_view_layers_t *out,const char *text,int frames);
/* Bind each normal action row to normal motion, punch rows to ready motion. */
int AW_ViewLayersBind(const aw_view_layers_t *layers,const aw_anim_t *anim);
int AW_ViewLayerFrame(const aw_view_layers_t *layers,int action,int motion_frame,float fraction);

/* Original carried-torch emitter, one bounded point per companion alias frame. */
#define AW_VIEW_TORCH_FRAMES 256
typedef struct {int count;float point[AW_VIEW_TORCH_FRAMES][3];} aw_view_torch_t;
int AW_ViewTorchParse(aw_view_torch_t *out,const unsigned char *bytes,int size,int frames);
/* PLAYER-TORCH-THIRDPERSON-38: the held torch alias is optional and lives in the model
 * cache; a later load can evict it while the torch body stays (the renderer reloads the
 * body by itself, nothing reloaded the held torch). 1 = try to load it again now: it is
 * not cached, the last try is at least AW_VIEW_HELD_RETRY seconds ago, and the free hunk
 * meets the same AW_VIEW_HELD_FREE bytes as its first admission. */
#define AW_VIEW_HELD_RETRY 1.0
#define AW_VIEW_HELD_FREE (2*1024*1024)
int AW_ViewHeldRetry(int cached,int free_bytes,double now,double *next);

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
    int locked;           /* dbg setpov: the locked mode + 1 (0 not locked): no key, timer or script changes it */
} aw_view_t;
/* dbg setpov (FP-TORCH-HAND-REGRESSION-67, the maintainer 2026-11-18: a debug switch that forces the view and locks it
 * in with a message, for the test stills): MODE AW_VIEW_FIRST, AW_VIEW_THIRD or AW_VIEW_VANITY locks the view in it
 * (the idle timer, Toggle POV, the wheel and the view commands no longer change it); -1 unlocks. Pure. */
void AW_ViewLock(aw_view_t *v,int mode);
/* The locked mode, or -1. Pure. */
int AW_ViewLockedMode(const aw_view_t *v);
/* A race or sex swap (dbg race, FP-ARMS-NO-MODEL-SLOT-67): the body's and the first-person arms' part models of the old
 * one released at once (aw_view.c), both sets assembled again at the next frame that draws them; prints the model
 * table before and after. */
void AW_ViewPartsUnload(void);
/* 1 = RACE (a race id) and sex are a beast race by the body recipe, 0 not, -1 unknown (DBG-RACE-SWAP-67). */
int AW_ViewRaceBeast(const char *race,int female);

void AW_ViewRulesDefault(aw_view_rules_t *r);
void AW_ViewReset(aw_view_t *v,const aw_view_rules_t *r);
/* One frame of the Toggle POV key (camera.lua updatePOV): held = the key is down. */
void AW_ViewPOV(aw_view_t *v,const aw_view_rules_t *r,int held,float dt);
/* A Toggle POV press released before the next frame saw it: one short press (CAMERA-POV-TAP-LOST-36). */
void AW_ViewPOVTap(aw_view_t *v,const aw_view_rules_t *r);
/* One frame of the idle clock and the vanity orbit (camera.lua updateIdleTimer + updateVanity):
 * input = any key, mouse or movement this frame; allowed = vanity may start (alive, in game, enabled). */
void AW_ViewIdle(aw_view_t *v,const aw_view_rules_t *r,int input,int allowed,float dt);
/* One frame of an orbit's hold on the view (the preview and vanity orbits: the mouse turns the camera, not the
 * player): VIEW (pitch, yaw, roll: the client's view angles) stays at ANCHOR, the player's heading, and what VIEW moved
 * from it this frame turns the camera (orbit_yaw, orbit_pitch). ENTERED: the orbit began this frame, its anchor is the
 * view now. FORCED: the game turned the player this frame (a script's SetAngle on the player, an arrival's facing,
 * aw_view, aw_aim: the server's set-angle message): that is the player's new heading, so it becomes the anchor and the
 * camera starts again from it (VIEW-VANITY-UNDOES-SET-VIEW-67; OpenMW apps/openmw/mwrender/camera.cpp Camera::setMode,
 * instantTransition: leaving an orbit the camera takes the player's own rotation, which a script's turn has set). */
void AW_ViewOrbitHold(aw_view_t *v,float view[3],float anchor[3],int entered,int forced);
/* May the vanity orbit run: switched on (or started by hand), a player body, and no combat playground or Arena
 * fight: the orbit's full view skips the playground's drawing, which also runs its clock (the sounds mode went
 * silent after 30 s without input, CREATURE-SOUNDS-CLIFFRACER-SILENT-58). */
int AW_ViewVanityAllowed(int enabled,int body,int arena);
/* PLAYER-VANITY-WALK-STUCK-67: what the player body's animation state lives through besides the body itself: the view
 * mode (first, third, the Toggle POV orbit, the vanity orbit, death), the movement type (walking, noclip), swimming,
 * whether play has the keys (a menu, the dialogue window or the console over it), whether the body is drawn. After
 * an idle vanity orbit the walk and run stayed stuck until a map load re-made the state; now a change of any of these
 * restarts it as a load does (AW_ViewBodyRestart). SIG with valid 0 (a new map) always counts as a change. 1 when NOW
 * differs from LAST; LAST becomes NOW. */
typedef struct {int valid,mode,movetype,swimming,playing,drawn;} aw_view_body_sig_t;
int AW_ViewBodySigChanged(aw_view_body_sig_t *last,const aw_view_body_sig_t *now);
/* The body's animation clocks back to their start, as a new map leaves them: the move group (no group, the next frame
 * picks it), the jump and landing state (none). */
void AW_ViewBodyRestart(aw_anim_play_t *play,aw_anim_air_t *air);
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
/* the race's height scale of the player's assembled body (aw_player_parts.h), 1 without one (MAGIC-SHELL-EGG-STYLE-67:
 * the shell on the player at the actor's own scale, as OpenMW's Npc::adjustScale scales the whole actor) */
float AW_ViewRaceHeight(void);
void AW_ViewInput(int key,int down);/* every key event: the idle clock, Toggle POV */
int AW_ViewKey(int key);            /* the death prompt's keys; 1 = used */
void AW_ViewDraw(void);             /* the death prompt */
int AW_ViewThirdPerson(void);       /* hands and torch model hidden */
int AW_ViewVanityFullscreen(void);   /* the vanity orbit draws the full-screen view, no HUD (aw_vanity_fullview) */
int AW_DeathLocked(void);           /* the player is dead: no talk, activate, attack or movement */
void AW_ViewSceneSpawn(void);       /* a new map: the death scene ends */
/* dbg cam orbit (aw_cam.c): around EDICT (0: the point) at FOCAL, RATE degrees a second; PHOTO: no HUD */
int AW_ViewOrbitStart(int edict,const float *focal,int photo,float rate);
void AW_ViewOrbitPending(int photo,float rate);   /* start on the crosshair target once a recall has arrived */
void AW_ViewOrbitEnd(int say);                    /* restores everything the orbit changed */
void AW_ViewOrbitSpeed(float rate);
int AW_ViewOrbitActive(void);
#endif
#endif
