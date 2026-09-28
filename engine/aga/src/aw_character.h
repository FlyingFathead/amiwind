/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef AW_CHARACTER_H
#define AW_CHARACTER_H
typedef struct {
    char id[64],name[48];
    unsigned char attributes[16],skills[27];
    short modifiers[8];
    unsigned short magicka;
    int power_count;
    char powers[16][64];
} aw_race_t;
typedef struct {char id[64],name[48];unsigned char attributes[2],special,skills[10];} aw_class_t;
typedef struct {
    char id[64],name[48];short modifiers[8];unsigned short magicka;
    int power_count;char powers[16][64];
} aw_birth_t;
typedef struct {char id[64];unsigned char race,female,kind;} aw_part_t;
typedef struct {
    int valid,race,female,head,hair,clas,birth,level;
    short attributes[8],modifiers[8],damage[8],skills[27];
    float current[3],maximum[3];
} aw_character_t;
extern aw_character_t aw_character;
extern aw_race_t aw_races[16];
extern aw_class_t aw_classes[32];
extern aw_birth_t aw_births[16];
extern aw_part_t aw_parts[384];
extern int aw_race_count,aw_class_count,aw_birth_count,aw_part_count;
extern unsigned char aw_character_source[32];
int AW_CharacterDecode(const unsigned char *data,int size);
int AW_CharacterLoad(void);
int AW_CharacterRebuild(aw_character_t *c);
void AW_CharacterReset(void);
int AW_CharacterOpen(int kind);
int AW_CharacterActive(void);
int AW_CharacterDone(void);
int AW_CharacterKey(int key);
void AW_CharacterMouse(int dx,int dy);
void AW_CharacterDraw(void);
int AW_HeadDecode(int slot,const unsigned char *raw,int size);
int AW_HeadLoad(int head,int hair);
void AW_HeadDraw(int x,int y,int width,int height,float angle);
void AW_HeadClear(void);
#endif
