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
/* World pose of an item: the actor's origin plus the tag origin turned by the
 * actor's yaw; the tag angles plus the actor's yaw (actors only turn about z), with
 * the pitch negated for the alias renderer (R_AliasSetUpTransform negates it back). */
void AW_ItemsPose(const float *tag6,const float origin[3],float yaw,float out_origin[3],float out_angles[3]);

#ifndef AW_ITEMS_HOST_TEST
struct edict_s;
/* At spawn (level loading): read the model's tag file and precache its items. */
void AW_ItemsPrep(struct edict_s *actor);
/* Show the actor's items (allocates up to two entities into out; 0 = none). */
int AW_ItemsShow(struct edict_s *actor,struct edict_s *out[AW_ITEMS_KINDS]);
/* Follow the actor's current frame. */
void AW_ItemsUpdate(struct edict_s *actor,struct edict_s *items[AW_ITEMS_KINDS]);
void AW_ItemsHide(struct edict_s *items[AW_ITEMS_KINDS]);
#endif
#endif
