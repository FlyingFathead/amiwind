/* Carried items (weapon, shield) drawn as separate models on a hand bone's
 * per-frame tag (tools/npc_items.py writes <model>.tag beside a resident model and
 * the item models once). The original engine attaches the wielded weapon to
 * "Weapon Bone" and the shield to "Shield Bone"; an alias model cannot hide parts,
 * so a resident shows its items only while fighting (NPC-WEAPON-MESH-33). */
#ifndef AW_ITEMS_H
#define AW_ITEMS_H

#define AW_ITEMS_KINDS 2            /* weapon, shield */
#define AW_ITEMS_MAX_FRAMES 256
#define AW_ITEMS_ROW 12             /* per kind: origin x y z, pitch yaw roll */
#define AW_ITEMS_PATH 64

/* Parse a tag file: returns the frame count (must equal numframes) and fills rows
 * (frames x AW_ITEMS_ROW floats, caller-sized for maxframes) and the item paths
 * ("" for none); 0 = invalid. */
int AW_ItemsParse(const char *text,int numframes,float *rows,int maxframes,char paths[AW_ITEMS_KINDS][AW_ITEMS_PATH]);
/* A skeletal model's tag file (SKEL-ITEM-TAGS-52; the builder's AWTS1 form): no rows, the item bones'
 * indices in the shared table (-1 none) and the actor's own scale; the row of a frame is made from the table's
 * pose at that frame (aw_skel.h AW_SkelBoneTag). Two optional last lines "light <path>" and "emitter x y z" are a
 * carried light (a guard's torch) on the shield bone and its flame point in that bone's space: light, emitter and
 * *has_emitter (any may be NULL). Returns the frame count (must equal numframes, the table's), or 0 = invalid. */
#define AW_ITEMS_MAX_SKEL_FRAMES 65535
#define AW_ITEMS_MAX_BONES 64
int AW_ItemsParseSkel(const char *text,int numframes,char paths[AW_ITEMS_KINDS][AW_ITEMS_PATH],int bones[AW_ITEMS_KINDS],
                      float scale[3],char light[AW_ITEMS_PATH],float emitter[3],int *has_emitter);
/* World pose of an item: the actor's origin plus the tag origin turned by the
 * actor's yaw; the tag angles plus the actor's yaw (actors only turn about z), with
 * the pitch negated for the alias renderer (R_AliasSetUpTransform negates it back). */
void AW_ItemsPose(const float *tag6,const float origin[3],float yaw,float out_origin[3],float out_angles[3]);

#ifndef AW_ITEMS_HOST_TEST
struct edict_s;
struct model_s;
/* Same AWTG1 rows, dynamically selected player weapon/shield paths. */
int AW_ItemsAliasTag(struct model_s *model,int frame,int kind,float tag[6]);
void AW_ItemsAliasClear(void);
/* At spawn (level loading): read the model's tag file and precache its items. */
void AW_ItemsPrep(struct edict_s *actor);
/* Show the actor's items (allocates up to two entities into out; 0 = none). */
int AW_ItemsShow(struct edict_s *actor,struct edict_s *out[AW_ITEMS_KINDS]);
/* Follow the actor's current frame. */
void AW_ItemsUpdate(struct edict_s *actor,struct edict_s *items[AW_ITEMS_KINDS]);
void AW_ItemsHide(struct edict_s *items[AW_ITEMS_KINDS]);
/* What an actor carries: bit 0 a weapon, bit 1 a shield, AW_ITEMS_LIGHT a carried light (a guard's torch); the
 * animation stage picks its cast with it (dbg animkit stage, SKEL-ANIM-STAGE-52). */
#define AW_ITEMS_LIGHT 4
int AW_ItemsKinds(struct edict_s *actor);
/* Carried lights of skeletal actors (a guard's torch): moved with their actors every server frame (SV_Physics).
 * At most AW_ITEMS_CARRIERS per map, each one entity while torches are carried (the map gate reserves them:
 * tools/map_engine_limits.py runtime_edicts; as many as the guard torch drawer shows, GUARD_VISIBLE). */
#define AW_ITEMS_CARRIERS 32
void AW_ItemsCarriedUpdate(void);
/* A carried light's flame point in its item model's space, 1 when the model is one (the guard torch flame and
 * light, aw_guard_torch.c). */
int AW_ItemsLightEmitter(const struct model_s *item,float out[3]);
/* A skeletal model that carries a light while torches are shown holds it up: 1 with its left arm's root bone and
 * the table frame of the "torch" group that arm takes (aw_skel.h AW_SkelPoseLayer; SKEL-ITEM-TAGS-52); 0 otherwise.
 * The renderer, the cull box and the item rows all pose it so (r_alias.c, skel_rows). */
int AW_ItemsTorchLayer(const struct model_s *m,const void *skel_table,int frame,float *layer_frame,int *root);
/* r_alias.c's hook to it (set with the level's item tables; NULL: no torch pose, as in the renderer's native tests) */
extern int (*R_AliasTorchLayer)(const struct model_s *m,const void *skel_table,int frame,float *layer_frame,int *root);
/* An actor (of an item table: its arm bones are known) facing into an ash or blight storm while idle, walking,
 * running, turning or sneaking shields its eyes: 1 with its right arm's root and the table frame of the "idlestorm"
 * group (ACTOR-STORM-POSE-51; aw_weather.h). yaw: the drawn entity's. The torso part of the original pose is left
 * out (one arm layer). */
int AW_ItemsStormLayer(const struct model_s *m,const void *skel_table,int frame,float yaw,float *layer_frame,int *root);
extern int (*R_AliasStormLayer)(const struct model_s *m,const void *skel_table,int frame,float yaw,float *layer_frame,
    int *root);
#endif
#endif
