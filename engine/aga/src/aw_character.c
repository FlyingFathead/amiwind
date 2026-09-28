/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include "aw_story.h"
#include "aw_character.h"

aw_character_t aw_character;
aw_race_t aw_races[16];
aw_class_t aw_classes[32];
aw_birth_t aw_births[16];
aw_part_t aw_parts[384];
int aw_race_count,aw_class_count,aw_birth_count,aw_part_count;
byte aw_character_source[32];
static byte specialization[27];
static const byte *cursor,*limit;
static int decode_error;
static int menu,accepted,row,review_return,page;
static int mouse_x=160,mouse_y=90,mouse_visible;
static aw_character_t choice;
static float rotation;
static const char *attributes[]={"Strength","Intelligence","Willpower","Agility","Speed","Endurance","Personality","Luck"};
static const char *skills[]={"Block","Armorer","Medium armor","Heavy armor","Blunt weapon","Long blade","Axe","Spear","Athletics","Enchant","Destruction","Alteration","Illusion","Conjuration","Mysticism","Restoration","Alchemy","Unarmored","Security","Sneak","Acrobatics","Light armor","Short blade","Marksman","Mercantile","Speechcraft","Hand to hand"};

static int take(void *out,int count)
{
    if(count<0 || count>limit-cursor){decode_error=1;return 0;}
    memcpy(out,cursor,count);cursor+=count;return 1;
}
static int number(void){byte b[2]={0,0};take(b,2);return b[0]+(b[1]<<8);}
static void name(char *out,int size)
{
    int i;
    if(!take(out,size))return;
    if(!out[0] || !memchr(out,0,size)){decode_error=1;return;}
    for(i=0;out[i];i++)if((unsigned char)out[i]<32)decode_error=1;
}
static int powers(char out[16][64])
{
    byte n=0;int i;take(&n,1);
    if(n>16){decode_error=1;return 0;}
    for(i=0;i<n;i++)name(out[i],64);
    return n;
}

int AW_CharacterDecode(const byte *data,int size)
{
    int nr,nc,nb,np,i,j;byte pad=0;
    aw_race_t *r;aw_class_t *c;aw_birth_t *b;aw_part_t *p;
    aw_race_count=aw_class_count=aw_birth_count=aw_part_count=0;
    if(size<72 || size>98304 || memcmp(data,"AWC1",4))return 0;
    cursor=data+4;limit=data+size;decode_error=0;
    nr=number();nc=number();nb=number();np=number();
    if(nr<1 || nr>16 || nc<1 || nc>32 || nb<1 || nb>16 || np<1 || np>384)return 0;
    take(specialization,27);take(&pad,1);take(aw_character_source,32);
    if(pad)return 0;
    for(i=0;i<27;i++)if(specialization[i]>2)return 0;
    for(i=0;i<nr && !decode_error;i++){
        r=&aw_races[i];name(r->id,64);name(r->name,48);
        take(r->attributes,16);take(r->skills,27);
        for(j=0;j<8;j++){r->modifiers[j]=(short)number();
        if(abs(r->modifiers[j])>1000)decode_error=1;}
        r->magicka=number();
        if(r->magicka>1000)decode_error=1;
        r->power_count=powers(r->powers);
    }
    for(i=0;i<nc && !decode_error;i++){
        c=&aw_classes[i];name(c->id,64);name(c->name,48);
        take(c->attributes,2);take(&c->special,1);take(c->skills,10);
        if(c->attributes[0]>7 || c->attributes[1]>7 || c->special>2)decode_error=1;
        for(j=0;j<10;j++)if(c->skills[j]>26)decode_error=1;
    }
    for(i=0;i<nb && !decode_error;i++){
        b=&aw_births[i];name(b->id,64);name(b->name,48);
        for(j=0;j<8;j++){b->modifiers[j]=(short)number();
        if(abs(b->modifiers[j])>1000)decode_error=1;}
        b->magicka=number();
        if(b->magicka>1000)decode_error=1;
        b->power_count=powers(b->powers);
    }
    for(i=0;i<np && !decode_error;i++){
        p=&aw_parts[i];name(p->id,64);take(&p->race,1);take(&p->female,1);take(&p->kind,1);take(&pad,1);
        if(pad || p->race>=nr || p->female>1 || p->kind>1)decode_error=1;
    }
    if(decode_error || cursor!=limit)return 0;
    /* Reject duplicate IDs and missing race/sex choices before selectors use it. */
    for(i=0;i<np;i++)for(j=0;j<i;j++)if(!strcmp(aw_parts[i].id,aw_parts[j].id))return 0;
    for(i=0;i<nr*4;i++){
        for(j=0;j<np;j++)if(aw_parts[j].race==i/4 && aw_parts[j].female==(i/2)%2 && aw_parts[j].kind==i%2)break;
        if(j==np)return 0;
    }
    aw_race_count=nr;aw_class_count=nc;aw_birth_count=nb;aw_part_count=np;
    return 1;
}

int AW_CharacterLoad(void)
{
    FILE *f=NULL;byte *raw;int size,ok;
    if(aw_race_count)return 1;
    size=COM_FOpenFile("character/catalog.awc",&f);
    if(!f)return 0;
    if(size<72 || size>98304){fclose(f);return 0;}
    raw=malloc(size);
    if(!raw){fclose(f);return 0;}
    ok=fread(raw,1,size,f)==(size_t)size;fclose(f);
    if(ok)ok=AW_CharacterDecode(raw,size);
    free(raw);return ok;
}

static int part_next(int current,int race,int sex,int kind,int direction)
{
    int i,index=current;
    for(i=0;i<aw_part_count;i++){
        index=(index+direction+aw_part_count)%aw_part_count;
        if(aw_parts[index].race==race && aw_parts[index].female==sex && aw_parts[index].kind==kind)return index;
    }
    return -1;
}
static int part_valid(int index,aw_character_t *c,int kind)
{
    return index>=0 && index<aw_part_count && aw_parts[index].race==c->race &&
        aw_parts[index].female==c->female && aw_parts[index].kind==kind;
}
int AW_CharacterRebuild(aw_character_t *c)
{
    int i;aw_race_t *r;aw_class_t *k;aw_birth_t *b;
    if(c->race<0 || c->race>=aw_race_count || c->female<0 || c->female>1 ||
       c->clas<0 || c->clas>=aw_class_count || c->birth<0 || c->birth>=aw_birth_count ||
       !part_valid(c->head,c,0) || !part_valid(c->hair,c,1))return 0;
    r=&aw_races[c->race];k=&aw_classes[c->clas];b=&aw_births[c->birth];
    for(i=0;i<8;i++){
        c->attributes[i]=r->attributes[i*2+c->female];
        c->modifiers[i]=r->modifiers[i]+b->modifiers[i];c->damage[i]=0;
    }
    for(i=0;i<2;i++)c->attributes[k->attributes[i]]+=10;
    for(i=0;i<27;i++)c->skills[i]=5+r->skills[i]+(specialization[i]==k->special?5:0);
    for(i=0;i<10;i++)c->skills[k->skills[i]]+=(i&1)?25:10;
    /* Starting health uses base Strength/Endurance; permanent Fortify Attribute
     * effects modify fatigue/magicka, without granting retroactive health. */
    c->maximum[0]=(c->attributes[0]+c->attributes[5])*.5f;
    c->maximum[1]=(c->attributes[1]+c->modifiers[1])*(1+(r->magicka+b->magicka)*.1f);
    c->maximum[2]=0;
    for(i=0;i<6;i++)if(i!=1 && i!=4)c->maximum[2]+=c->attributes[i]+c->modifiers[i];
    for(i=0;i<3;i++)c->current[i]=c->maximum[i];
    c->level=1;c->valid=1;return 1;
}

void AW_CharacterReset(void)
{
    memset(&aw_character,0,sizeof(aw_character));menu=accepted=review_return=0;
    AW_HeadClear();
    if(!AW_CharacterLoad())return;
    aw_character.head=part_next(-1,0,0,0,1);aw_character.hair=part_next(-1,0,0,1,1);
    AW_CharacterRebuild(&aw_character);
}

int AW_CharacterOpen(int kind)
{
    if(kind<1 || kind>4 || !AW_CharacterLoad() || !aw_character.valid)return 0;
    choice=aw_character;menu=kind;row=page=accepted=review_return=mouse_visible=0;rotation=0;
    IN_AWClearButtons();
    if(kind==1 && !AW_HeadLoad(choice.head,choice.hair)){menu=0;return 0;}
    return 1;
}
int AW_CharacterActive(void){return menu!=0;}
int AW_CharacterDone(void){int result=accepted;accepted=0;return result;}

static void change(int direction)
{
    if(menu==1){
        if(row==0)choice.race=(choice.race+direction+aw_race_count)%aw_race_count;
        if(row==1)choice.female=1-choice.female;
        if(row<2){choice.head=part_next(-1,choice.race,choice.female,0,1);choice.hair=part_next(-1,choice.race,choice.female,1,1);}
        if(row==2)choice.head=part_next(choice.head,choice.race,choice.female,0,direction);
        if(row==3)choice.hair=part_next(choice.hair,choice.race,choice.female,1,direction);
        if(row<4 && !AW_HeadLoad(choice.head,choice.hair))Con_Printf("Head preview missing or invalid.\n");
    }else if(menu==2)choice.clas=(choice.clas+direction+aw_class_count)%aw_class_count;
    else if(menu==3)choice.birth=(choice.birth+direction+aw_birth_count)%aw_birth_count;
    else page=(page+direction+5)%5;
    AW_CharacterRebuild(&choice);
}
void AW_CharacterMouse(int dx,int dy)
{
    if(!menu)return;
    mouse_visible=1;mouse_x+=dx;mouse_y+=dy;
    if(mouse_x<0)mouse_x=0;
    if(mouse_x>319)mouse_x=319;
    if(mouse_y<0)mouse_y=0;
    if(mouse_y>199)mouse_y=199;
    if(menu==1 && mouse_x<198 && mouse_y>=38 && mouse_y<148)row=(mouse_y-38)/22;
    if(mouse_y>=166)row=4;
}
int AW_CharacterKey(int key)
{
    int old;
    if(!menu || key_dest!=key_game)return 0;
    if(key==K_ESCAPE)return 0; /* Pause menu, retaining the unfinished choice. */
    if(key=='a' || key=='A')key=K_LEFTARROW;
    if(key=='d' || key=='D')key=K_RIGHTARROW;
    if(key=='w' || key=='W')key=K_UPARROW;
    if(key=='s' || key=='S')key=K_DOWNARROW;
    if(key==K_MOUSE1){
        if(mouse_y>=166 && mouse_y<187)key=K_ENTER;
        else if(menu==1 && mouse_x>=200){rotation+=.4f;return 1;}
        else {change(mouse_x<100?-1:1);return 1;}
    }
    if(menu==4 && (key=='r' || key=='c' || key=='b')){
        review_return=1;menu=key=='r'?1:key=='c'?2:3;row=0;
        if(menu==1)AW_HeadLoad(choice.head,choice.hair);
        return 1;
    }
    if(key==K_LEFTARROW || key==K_RIGHTARROW)change(key==K_LEFTARROW?-1:1);
    if(key=='[')rotation-=.2f;
    if(key==']')rotation+=.2f;
    if(key==K_UPARROW || key==K_DOWNARROW || key==K_TAB){
        if(menu==1)row=(row+(key==K_UPARROW?4:1))%5;
        else change(key==K_UPARROW?-1:1);
    }
    if(key==K_ENTER){
        if(menu==1 && row<4){row++;return 1;}
        if(!AW_CharacterRebuild(&choice))return 1;
        if(review_return){menu=4;review_return=0;page=0;return 1;}
        aw_character=choice;old=menu;menu=0;accepted=old;AW_HeadClear();IN_AWClearButtons();
    }
    return 1;
}
void AW_CharacterDraw(void)
{
    int i,y,index,gold,muted;char line[96];
    if(!menu || key_dest!=key_game)return;
    gold=AW_UIColor(223,199,144);muted=AW_UIColor(120,109,87);
    AW_UIBox(2,2,316,196);
    AW_UITextBox(10,8,300,20,menu==1?"Choose your appearance":menu==2?"Choose your class":menu==3?"Choose your birthsign":"Review your character",gold);
    if(menu==1){
        const char *labels[]={"Race","Sex","Face","Hair"};
        for(i=0;i<4;i++){
            if(i==0)sprintf(line,"%s",aw_races[choice.race].name);
            else if(i==1)sprintf(line,"%s",choice.female?"Female":"Male");
            else {
                int n=0,selected=0;
                for(index=0;index<aw_part_count;index++)if(part_valid(index,&choice,i-2)){
                    n++;
                    if(index==(i==2?choice.head:choice.hair))selected=n;
                }
                sprintf(line,"%s: %ld / %ld",labels[i],(long)selected,(long)n);
            }
            y=38+i*22;
            if(row==i)AW_UIFill(9,y,186,21,AW_UIColor(54,47,32));
            AW_UITextBox(12,y,180,21,line,gold);
        }
        AW_UITextBox(10,133,185,23,"Arrows/WASD: Choose",muted);
        rotation+=host_frametime*.35f;AW_HeadDraw(201,34,108,122,rotation);
    }else if(menu==2){
        AW_UITextBox(12,36,296,22,aw_classes[choice.clas].name,gold);
        AW_UITextBox(12,60,296,18,"Major skills",muted);
        for(i=0;i<5;i++)AW_UITextBox(12+(i/3)*148,80+(i%3)*22,144,20,skills[aw_classes[choice.clas].skills[i*2+1]],gold);
    }else if(menu==3){
        AW_UITextBox(12,35,296,22,aw_births[choice.birth].name,gold);
        AW_BirthArt(choice.birth,209,51);
        AW_UITextBox(12,65,190,20,"Powers and abilities",muted);
        for(i=0;i<aw_births[choice.birth].power_count && i<3;i++)
            AW_UITextBox(12,88+i*22,190,20,aw_births[choice.birth].powers[i],gold);
    }else{
        AW_UITextBox(12,31,296,20,aw_story.name,gold);
        for(i=0;i<8;i++){
            index=(page-1)*8+i;
            if(page && index>=27)break;
            if(!page)sprintf(line,"%s: %ld",attributes[i],(long)(choice.attributes[i]+choice.modifiers[i]));
            else sprintf(line,"%s: %ld",skills[index],(long)choice.skills[index]);
            AW_UITextBox(12+(i/4)*148,53+(i%4)*22,144,20,line,gold);
        }
        AW_UITextBox(12,143,296,19,"R: race  C: class  B: birthsign",muted);
    }
    AW_UITextBox(10,166,300,22,menu==4?"Enter: accept  Arrows/WASD: pages":menu==1?"Enter: next / accept   [ ]: rotate":"Arrows/WASD: Choose  Enter: accept",gold);
    if(mouse_visible){AW_UIFill(mouse_x,mouse_y,2,6,gold);AW_UIFill(mouse_x,mouse_y,6,2,gold);}
}
