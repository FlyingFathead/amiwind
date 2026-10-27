/* SPDX-License-Identifier: GPL-2.0-or-later
 * The Halloween scene (dbg halloween, alias dbg halloweentest; docs/HALLOWEEN.md): the animation stage
 * (SKEL-ANIM-STAGE-52) with a beat clock. A cast from the image's halloween.txt (tools/halloween_cast.py: the
 * game's skeleton creature on the shared humanoid table, the dancers of Desele's House of Earthly Delights on the
 * female table, Dagoth Ur on his own table) stands before the camera and dances a choreography of the game's own
 * animation groups on the beat; a camera director changes shot on bar boundaries; the greeting box for the first
 * seconds is the only thing drawn in the middle of the screen; an FPS counter (off by default in the show) sits in
 * the bottom-left corner. dbg halloween bench is the standard benchmark: fixed frames, the same picture every run.
 *
 * Pure parts (aw_halloween_rules.c, host-tested): the command parser, the cast file reader, the choreography (the
 * step every role dances at a beat), a step's frame, the stage layout, the camera shots and the benchmark's
 * figures. Engine part: aw_halloween.c.
 */
#ifndef AW_HALLOWEEN_H
#define AW_HALLOWEEN_H

/* The beat in tenths of a beat a minute when the image has no soundtrack of its own (the tempo the choreography was
 * made to; tools/halloween_cast.py DEFAULT_BPM); a soundtrack's measured tempo comes in the cast file. */
#define AW_HALLOWEEN_BPM10		1320
#define AW_HALLOWEEN_BOX_SECONDS	5		/* the greeting alone on black, in silence, before the dance */
#define AW_HALLOWEEN_TEXT1		"HAPPY HALLOWEEN"
#define AW_HALLOWEEN_TEXT2		"FROM AMIWIND"
#define AW_HALLOWEEN_CAST_FILE	"halloween.txt"
#define AW_HALLOWEEN_MAX_ROWS	8		/* models in the cast file */
#define AW_HALLOWEEN_MAX		12		/* actors on the stage */
#define AW_HALLOWEEN_PATH		64
/* The benchmark: this many frames, the scene clock stepping a fixed time each frame (so every run draws the same
 * frames whatever the machine: 60 s of the scene), as Quake's timedemo plays a fixed recording. */
#define AW_HALLOWEEN_BENCH_FRAMES	600
#define AW_HALLOWEEN_BENCH_STEP		0.1f
/* A camera shot lasts this many bars of four beats; it changes only on a bar boundary. */
#define AW_HALLOWEEN_SHOT_BARS		4

enum {AW_HW_LEAD, AW_HW_DANCER, AW_HW_SKELETON, AW_HW_ROLES};
enum {AW_HW_HELP, AW_HW_START, AW_HW_STOP, AW_HW_STATUS, AW_HW_FPS, AW_HW_CAMERA};
enum {AW_HW_WITH_LEAD, AW_HW_SKELETONS};		/* the two versions */

/* kind; version; bench 1 for "bench"; value: fps 1/0, camera 1 = locked to the wide shot, 0 = the director */
typedef struct {int kind,version,bench,value;} aw_hw_cmd_t;
/* "dbg halloween [dagoth / skeletons / bench [skeletons] / fps on|off / camera wide|director / stop / status]": no
 * word starts the Dagoth Ur version (the skeletons-only one when the cast has no Dagoth Ur). 0 for anything else. */
int AW_HalloweenParse(int argc,const char **argv,aw_hw_cmd_t *out);

typedef struct {int role;char model[AW_HALLOWEEN_PATH];char name[32];} aw_hw_row_t;
typedef struct {int bpm10,soundtrack,rows;aw_hw_row_t row[AW_HALLOWEEN_MAX_ROWS];} aw_hw_cast_t;
/* The cast file's text (NUL-terminated): "AWHW1 <bpm x 10> <0/1>" then "<lead/dancer/skeleton> <model> <name>"
 * lines. 1 and *out filled, or 0 (a bad file: the scene says so and does not start). */
int AW_HalloweenReadCast(const char *text,aw_hw_cast_t *out);

/* One move of a choreography: a group of the dancer's table by its Morrowind name, how many beats it takes (0: its
 * own length at about the beat's pace, rounded up to whole pairs of beats), and how it plays: */
#define AW_HW_FIT		0	/* the whole group squeezed or stretched into its beats */
#define AW_HW_LOOP		1	/* a cycle (walk, sneak, swim) looping at its own pace x 1.25 for its beats */
#define AW_HW_BACK		2	/* the whole group backwards (a death played back: getting up) */
#define AW_HW_DANCE		3	/* an actor's own dance looping at its own pace (Desele's dancers' d:idle9) */
typedef struct {const char *group;unsigned char beats,play;} aw_hw_step_t;
/* A role's line: its steps, repeated. */
int AW_HalloweenLine(int role,const aw_hw_step_t **steps);
/* The beats a step takes for a group of SECONDS (its own length) at beat BEAT seconds. */
int AW_HalloweenBeats(const aw_hw_step_t *s,float seconds,float beat);
/* A step's table frame SECONDS into it: group frames first..last at RATE frames a second, the step SPAN seconds
 * long; a fraction, so the engine blends between frames. */
float AW_HalloweenFrame(unsigned first,unsigned last,float rate,float into,float span,int play);
/* A side-step's mirror for a dancer on the left: "swimwalkleft" <-> "swimwalkright" (sneak, walk, run, turn too);
 * other names unchanged. out holds 32 bytes. */
void AW_HalloweenMirror(const char *group,char *out);

/* A place on the stage: the role, which of that role's models (wrapping), and where, in map units from the player
 * (right of the view, ahead of it). */
typedef struct {int role,model;float right,ahead;} aw_hw_slot_t;
/* The stage of a version for a cast with LEADS, DANCERS and SKELETONS models: the Dagoth Ur version puts him in the
 * centre, the dancers around him (the same number on each side), the skeletons behind them, the same number on
 * each side; the skeletons-only version two rows of skeletons. Returns the slot count (<= AW_HALLOWEEN_MAX), 0
 * when the cast cannot fill it (no skeleton). */
int AW_HalloweenLayout(int version,int leads,int dancers,int skeletons,aw_hw_slot_t *out);

/* The camera director: the wide establishing shot (the stage's own framing), a slow dolly-in toward the centre, a
 * tracking shot along the line, a crane rising over the group, an orbit around the centre, a close-up on a dancer;
 * each AW_HALLOWEEN_SHOT_BARS bars, in that order, the motion eased (slow in, slow out). */
enum {AW_HW_SHOT_WIDE, AW_HW_SHOT_DOLLY, AW_HW_SHOT_TRACK, AW_HW_SHOT_CRANE, AW_HW_SHOT_ORBIT, AW_HW_SHOT_CLOSE,
      AW_HW_SHOTS};
/* The shot SECONDS into the scene at beat BEAT, and *u its eased progress 0..1 (locked: always the wide shot). */
int AW_HalloweenShot(float seconds,float beat,int locked,float *u);
/* The shot's eye and the point it looks at, every shot at least at its subject's fitting distance (head to feet in
 * frame): FORWARD the view's level direction (the cast faces back along it); CENTRE the cast's middle, about
 * mid-body, FIT the distance that frames the whole cast (AW_HalloweenFrameCast); CLOSE the close-up's dancer at
 * mid-body, CLOSE_FIT the distance that frames her alone. */
void AW_HalloweenShotPose(int shot,float u,const float forward[3],const float centre[3],float fit,
                          const float close[3],float close_fit,float eye[3],float look[3]);
/* The framing of the whole cast (the wide shot and the first frame after the greeting): the eye looking along
 * FORWARD (level, unit) and down from AW_HALLOWEEN_FRAME_PITCH degrees at CENTRE (the cast's middle, about mid-body),
 * as far back as the cast's half width and half height need to fit the field of view (FOV_X, FOV_Y degrees) with
 * AW_HALLOWEEN_FRAME_MARGIN to spare. */
#define AW_HALLOWEEN_FRAME_PITCH	22.f
#define AW_HALLOWEEN_FRAME_MARGIN	1.35f
void AW_HalloweenFrameCast(const float centre[3],float half_width,float half_height,const float forward[3],
                           float fov_x,float fov_y,float eye[3]);
/* Quake view angles (pitch down positive, yaw) looking from EYE at LOOK. */
void AW_HalloweenAim(const float eye[3],const float look[3],float angles[3]);

/* The benchmark's figures from N frame times (seconds): average fps (frames over their time), the slowest frame's
 * fps, the 1 % low (fps of the mean of the slowest 1 % of frames, at least one), the seconds. */
typedef struct {float average,minimum,low1,seconds;int frames;} aw_hw_bench_t;
void AW_HalloweenBenchFigures(const float *times,int n,aw_hw_bench_t *out);

void AW_HalloweenInit(void);
void AW_HalloweenTick(void);
void AW_HalloweenDraw(void);
/* The director's view (view.c, before the world is drawn): 1 when it set r_refdef's eye and angles. */
int AW_HalloweenCamera(float origin[3],float angles[3]);
#endif
