/* What the use key acts on (FOCUS-NPC-OVERRIDES-ITEM-62). As in OpenMW 0.51 the activation goes to the nearest object
 * along the view ray within the activation distance, never to the nearest actor by proximity: an item or plant the ray
 * meets before an actor, or inside the actor's box (the box is coarser than the drawn body: a standing actor's arms, a
 * body lying on the floor), is taken; an actor the ray meets wholly before the item is talked to or searched.
 * aw_activate_rules.c holds the rules as pure functions (host tested, tests/aga_activate_rules_test.c); aw_scene.c
 * applies them (AW_ActivateActor). */
#ifndef AW_ACTIVATE_H
#define AW_ACTIVATE_H

/* The ray ORIGIN + t*DIR (t from 0) against the box MINS..MAXS, all in the box's own frame: 1 when they meet, with the
 * entry *NEAR (0 when the ray starts inside) and the exit *FAR, in units of DIR's length. */
int AW_RayBox(const float origin[3],const float dir[3],const float mins[3],const float maxs[3],float *near_hit,
              float *far_hit);
/* 1 when the use goes to the item (or plant) at ITEM along the ray rather than to the actor whose box the ray enters
 * at ACTOR_NEAR and leaves at ACTOR_FAR; ITEM below 0: no item aimed at (the actor wins); ACTOR_FAR below 0: no actor
 * (the item wins). */
int AW_ActivateItemFirst(float item,float actor_near,float actor_far);
/* The nearest of two aim distances, each below 0 when nothing is aimed at that way; below 0 when neither. */
float AW_ActivateNearest(float a,float b);
/* DBG-CONTAINER-AIM-OUT-OF-REACH-67 (the check command aw_placed container aim, aw_inventory.c): the eye that looks at
 * the point AT from AW_AIM_EYE map units away, LIFT of them above it, on the floor direction DX DY (a unit vector from
 * AT towards the eye), and the Quake view angles of that look (*PITCH positive looks down). Half the 48-unit reach, so a
 * box round AT is met well within it; the helper stood 40 units out on the floor before, 46 to 60 from the point. */
#define AW_AIM_EYE 24.0f
void AW_AimEye(const float at[3],float dx,float dy,float lift,float eye[3],float *yaw,float *pitch);

/* FOCUS-NPC-OVERRIDES-ITEM-62: the box the use key's ray meets an actor by, in his own turned frame (map units, his
 * origin at 0 0 0, as aw_scene.c AW_NPCTargetReach turns the ray). A person's model holds ONE stored frame since
 * v0.0.52 (skeletal actors: the rest frame and an animation table) and that frame's box encloses every pose, about 60
 * units long around a body 15 wide, so it took the use from a door or an item beside him. OpenMW takes the faced object
 * by a ray against the drawn body (apps/openmw/mwworld/worldimp.cpp, castCameraToViewportRay); the nearest here without
 * posing on the server is the body's own box, world.qc aw_npc_floor's hull. */
#define AW_PERSON_HALF_X 7.32f      /* world.qc aw_npc_floor: setsize -7.32 -7.12 0 .. 7.32 7.12 33.25 */
#define AW_PERSON_HALF_Y 7.12f
#define AW_PERSON_TOP 33.25f
#define AW_BODY_TOP 8.0f            /* a body lies within 8 units of its floor (CORPSE-INVENTORY-NOT-OPENABLE-59) */
enum {AW_USEBOX_STORED,AW_USEBOX_BODY,AW_USEBOX_LYING};
/* A model that stores ONE frame, remembered for the use box while its frames are evicted from the cache (model_t
 * numframes of a skeletal model is its animation table's, not 1): a bit of model_t flags far above the EF_* bits the
 * client reads (model.h). aw_scene.c AW_NPCTargetReach sets or clears it whenever it finds the frames resident; a reload
 * starts from the file's flags (bit clear) until the next look. model.h and the alias loaders stay as they are: their
 * sources are pinned in the CHIM world stages' key (tools/engine_loader_policy.py) and model_t is at its 400 bytes. */
#define AW_MODEL_ONE_STORED_FRAME 0x01000000
/* 1 when MINS..MAXS is the person's hull above (every aw_npc once aw_npc_floor ran, creatures too; 0 0 0 before) */
int AW_ActorPersonHull(const float mins[3],const float maxs[3]);
/* The use box OUT_MINS..OUT_MAXS from the stored box MINS..MAXS (the drawn frame's, or the whole model's while its
 * frames are not resident; OUT may be MINS / MAXS) of an actor whose model stores FRAMES frames (0: not known). A
 * PERSON (the person's hull, not a creature) whose model stores ONE frame gets, alive, his body's box: x and y narrowed
 * to the half widths times SCALE, never wider than the stored box, the stored height kept (the head above the hull is
 * aimed at); DEAD (lying), the stored box with its top lowered to AW_BODY_TOP times SCALE over its floor (a body is
 * searched by looking down at it). Every other actor (more than one frame, a creature, frames not known) keeps the
 * stored box, as does a stored box that does not reach the body's middle. Returns the AW_USEBOX_* kind given. */
int AW_ActorUseBox(int frames,int dead,int person,float scale,const float mins[3],const float maxs[3],float out_mins[3],
                   float out_maxs[3]);

/* The last choice of aw_scene.c AW_ActivateActor (map units from the eye; -1 when none), for `aw_placed aim`. */
typedef struct {float actor_near,actor_far,item,plant;int item_first;} aw_activate_aim_t;
extern aw_activate_aim_t aw_activate_last;

/* HUD-TEXTS-OVERLAP-67: ONE focus a frame. What the view ray meets within the activation distance, by kind: a person or
 * creature (where the ray enters and leaves his box), an item, container or plant (the nearer of them), a load door, a
 * hinged door; map units from the eye, -1 when the ray meets none of that kind. The kind AW_FocusChoose returns alone
 * gets the title, the action line and the use key (aw_scene.c), so a person's box never reaches past a nearer door and a
 * door behind him is not aimed at. */
enum {AW_FOCUS_NONE,AW_FOCUS_ACTOR,AW_FOCUS_THING,AW_FOCUS_DOOR,AW_FOCUS_HINGED,AW_FOCUS_KINDS};
typedef struct {float actor_near,actor_far,thing,door,hinged;} aw_focus_aim_t;
/* A kind the frame before had keeps the focus while the new nearest is less than this much nearer (map units): an
 * animated actor's box no longer flips the focus between him and the door beside him from frame to frame. */
#define AW_FOCUS_HOLD 4.0f
/* The seconds an actor stays aimed after the ray slipped out of his drawn frame's box while it still meets his whole
 * model's box (aw_scene.c focus_kind). */
#define AW_FOCUS_HOLD_SECONDS 0.25
/* The kind that takes the focus: the nearest along the ray; an item or plant inside an actor's box counts as before him
 * (AW_ActivateItemFirst); on a tie the actor, then the thing, the hinged door, the load door. PREVIOUS (the kind of the
 * frame before, AW_FOCUS_NONE at first) is kept under AW_FOCUS_HOLD. */
int AW_FocusChoose(const aw_focus_aim_t *aim,int previous);
/* The distance along the ray of KIND in AIM (the entry into the actor's box for an actor), -1 when absent. */
float AW_FocusDistance(const aw_focus_aim_t *aim,int kind);
/* aw_scene.c: the kind that has the focus this frame and the numbers it was chosen by (`aw_placed aim` prints them) */
int AW_SceneFocusKind(void);
extern aw_focus_aim_t aw_focus_last;

/* PLANT-BOX-AIM-69: a container aimed by its measured box (tools/prepare_focus.py CONTAINER_BOXES: the visible vertex
 * box of its whole model; since FARGOTH-STASH-STUMP-69 every plant that opens as a container has one, and a plant's box
 * is far coarser than its leaves and stems: a bush's reaches past the mushroom, the sign, the person or the smaller
 * plant standing in it). The original's activation ray meets the drawn shapes (OpenMW 0.51 World::getFacedObject), so
 * what stands inside such a box is met where it is, not behind the box. */
/* 1 when POINT lies inside the box CENTRE +- the half axes AXIS (aw_inventory.c focus_board_axis: three half axes,
 * turned as drawn); a degenerate axis holds nothing. */
int AW_BoxHolds(const float centre[3],const float axis[3][3],const float point[3]);
/* 1 when what the view ray meets at T takes the aim from the best so far, met at NEAREST (HAVE_BEST 0: none yet): the
 * nearer, except that what the ray meets inside a container's measured box stands in it and wins over that container:
 * BEST_BOX_HOLDS_T (T lies inside the best's box: the candidate wins although farther) and OWN_BOX_HOLDS_NEAREST (the
 * best's point lies inside the candidate's own box: the candidate yields although nearer). Never past REACH, never
 * below 0. */
int AW_AimTakes(float t,float nearest,float reach,int have_best,int best_box_holds_t,int own_box_holds_nearest);
/* 1 when the use goes to the plant to pick at PLANT along the ray (aw_harvest_runtime.c) rather than to the item or
 * container at ITEM (each below 0 when none): the nearer of the two, and a plant met inside the container's measured
 * box (ITEM_BOX_HOLDS_PLANT). Before, an item or container always went first, also from behind the plant. */
int AW_PlantFirst(float item,float plant,int item_box_holds_plant);

#endif
