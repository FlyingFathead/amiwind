/* SPDX-License-Identifier: GPL-3.0-only
 * dbg give weapons (DBG-GIVE-WEAPONS-59): the real kit rules of aw_inventory.c on the table the builder wrote
 * (argument 1, tools/prepare_weapon_kit.py from synthetic records): parse, room, all-or-nothing grant, console lines. */
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "aw_inventory.h"
static aw_state_t state,prior;
static aw_kit_row_t rows[AW_WEAPON_KIT_ROWS];
static int widest(const char *text){
    int best=0,n=0;
    for(;;text++){if(!*text || *text=='\n'){if(n>best)best=n;n=0;if(!*text)break;}else n++;}
    return best;
}
static int parse(const char *text){return AW_WeaponKitParse(text,(int)strlen(text),rows,AW_WEAPON_KIT_ROWS);}
int main(int argc,char **argv){
    FILE *f;char text[8192],out[512],name[16];long size;int n,i,width,lines;
    assert(argc==2 && (f=fopen(argv[1],"rb")));
    size=(long)fread(text,1,sizeof(text)-1,f);fclose(f);text[size]=0;
    n=AW_WeaponKitParse(text,(int)size,rows,AW_WEAPON_KIT_ROWS);
    assert(n==4);
    assert(!strcmp(rows[0].id,"iron dagger") && rows[0].count==1 && rows[0].kind=='W' && !strcmp(rows[0].type,"short blade"));
    assert(!strcmp(rows[0].stat[0],"4-5") && !strcmp(rows[0].stat[3],"2.5") && !strcmp(rows[0].stat[9],"-"));
    assert(!strcmp(rows[1].id,"chitin short bow") && rows[1].kind=='R');
    assert(!strcmp(rows[2].id,"iron arrow") && rows[2].count==50 && rows[2].kind=='A');
    assert(rows[3].kind=='S' && !strcmp(rows[3].stat[9],"10"));
    /* console lines: every token on its line, no line past the width, the id quoted for aw_inventory equip */
    for(width=28;width<=80;width++)for(i=0;i<n;i++){   /* the longest token here, indented, is 26 */
        lines=AW_WeaponKitLines(&rows[i],i==0,width,out,sizeof(out));
        assert(lines>=1 && widest(out)<=width);
        assert(strstr(out,rows[i].name) && strstr(out,rows[i].id));
    }
    lines=AW_WeaponKitLines(&rows[0],1,38,out,sizeof(out));
    printf("%s\n",out);
    assert(lines>=2 && strstr(out,"Iron Dagger (short blade)") && strstr(out,"chop 4-5") && strstr(out,"slash 4-5") &&
           strstr(out,"thrust 5-5") && strstr(out,"speed 2.5") && strstr(out,"reach 1") && strstr(out,"weight 3") &&
           strstr(out,"value 10") && strstr(out,"health 400") && strstr(out,"ench 20") && strstr(out,"equip \"iron dagger\"") &&
           !strstr(out,"armour"));
    lines=AW_WeaponKitLines(&rows[1],0,38,out,sizeof(out));printf("%s\n",out);
    assert(strstr(out,"damage 1-10") && strstr(out,"speed 1") && strstr(out,"health 500") && !strstr(out,"reach") &&
           !strstr(out,"slash"));
    lines=AW_WeaponKitLines(&rows[2],0,38,out,sizeof(out));printf("%s\n",out);
    assert(strstr(out,"Iron Arrow x50") && strstr(out,"damage 2-3") && !strstr(out,"chop") && !strstr(out,"health") &&
           strstr(out,"carry \"iron arrow\""));
    lines=AW_WeaponKitLines(&rows[3],1,38,out,sizeof(out));printf("%s\n",out);
    assert(strstr(out,"armour 10") && !strstr(out,"chop") && !strstr(out,"damage"));
    assert(AW_WeaponKitLines(&rows[0],1,38,out,16)==-1);
    /* the grant: all of it, then again on top (counts add, no new kinds); refused whole when the kinds do not fit */
    assert(AW_WeaponKitNeeds(&state,rows,n)==4);
    assert(AW_WeaponKitGrant(&state,rows,n));
    assert(AW_StateGet(&state,AW_ITEM,"iron dagger")==1 && AW_StateGet(&state,AW_ITEM,"iron arrow")==50);
    assert(AW_WeaponKitNeeds(&state,rows,n)==0 && AW_WeaponKitGrant(&state,rows,n));
    assert(AW_StateGet(&state,AW_ITEM,"iron arrow")==100 && AW_ItemCount(&state)==4);
    /* INVENTORY-ORIGINAL-LIMITS-61: no kind limit: with 400 kinds carried the kit is given (128 refused it) */
    AW_ItemsFree(&state);memset(&state,0,sizeof(state));
    for(i=0;i<400;i++){sprintf(name,"misc_%d",i);assert(AW_ItemAdd(&state,name,1));}
    assert(AW_WeaponKitNeeds(&state,rows,n)==4 && AW_WeaponKitGrant(&state,rows,n) && AW_ItemCount(&state)==404);
    /* a kind whose count fell to 0 takes a kit row in its place */
    AW_ItemsFree(&state);memset(&state,0,sizeof(state));
    for(i=0;i<400;i++){sprintf(name,"misc_%d",i);assert(AW_ItemAdd(&state,name,1));}
    assert(AW_ItemAdd(&state,"misc_9",-1) && AW_ItemAdd(&state,"iron dagger",1));   /* one kind already carried */
    assert(AW_WeaponKitNeeds(&state,rows,n)==3 && AW_WeaponKitGrant(&state,rows,n) && AW_ItemCount(&state)==403);
    AW_ItemsFree(&state);memset(&state,0,sizeof(state));assert(AW_ItemAdd(&state,"iron arrow",2147483647-10));
    prior=state;assert(AW_WeaponKitNeeds(&state,rows,n)==-1 && !AW_WeaponKitGrant(&state,rows,n));
    assert(!memcmp(&state,&prior,sizeof(state)));
    AW_ItemsFree(&state);
    /* malformed tables are refused whole */
    assert(parse("AWKIT1\n")==-1);
    assert(parse("AWKIT2\na|1|W|t|N|-|-|-|-|-|-|-|-|-|-\n")==-1);
    assert(parse("AWKIT1\n# comment\r\na|1|W|t|N|1-2|-|-|-|-|-|-|-|-|-\r\n")==1);
    assert(parse("AWKIT1\na|1|W|t|N|1-2|-|-|-|-|-|-|-|-\n")==-1);              /* 14 fields */
    assert(parse("AWKIT1\na|1|W|t|N|1-2|-|-|-|-|-|-|-|-|-|x\n")==-1);         /* 16 fields */
    assert(parse("AWKIT1\nA|1|W|t|N|1-2|-|-|-|-|-|-|-|-|-\n")==-1);           /* upper case id */
    assert(parse("AWKIT1\na|0|W|t|N|1-2|-|-|-|-|-|-|-|-|-\n")==-1);           /* count 0 */
    assert(parse("AWKIT1\na|1000|W|t|N|1-2|-|-|-|-|-|-|-|-|-\n")==-1);        /* count past 999 */
    assert(parse("AWKIT1\na|1|X|t|N|1-2|-|-|-|-|-|-|-|-|-\n")==-1);           /* unknown kind */
    assert(parse("AWKIT1\na|1|W|t|N|1 2|-|-|-|-|-|-|-|-|-\n")==-1);           /* space in a stat */
    assert(parse("AWKIT1\na|1|W|t|N|1-2||-|-|-|-|-|-|-|-\n")==-1);            /* empty stat */
    assert(parse("AWKIT1\na\"b|1|W|t|N|1-2|-|-|-|-|-|-|-|-|-\n")==-1);        /* quote in an id */
    assert(parse("AWKIT1\na|1|W|t|N|1-2|-|-|-|-|-|-|-|-|-\na|1|W|t|N|1-2|-|-|-|-|-|-|-|-|-\n")==-1);   /* twice */
    assert(parse("AWKIT1\na|1|W|t|N|123456789012|-|-|-|-|-|-|-|-|-\n")==-1); /* stat too long */
    printf("weapon kit rules: ok\n");
    {   /* dbg weapon / dbg gear (WEAPONS-57): the box, the order and the line of a catalogue row */
        aw_inventory_item_t it;char line[64];
        memset(&it,0,sizeof(it));strcpy(it.id,"steel claymore");strcpy(it.name,"Steel Claymore");
        it.category=AW_INV_WEAPON;it.subtype=2;it.flags=AW_INV_EQUIP|AW_INV_EQUIP_SUPPORTED;
        assert(AW_GearBoxKind(&it)==AW_GEARBOX_WEAPON && AW_GearBoxOrder(&it)==2);
        assert(AW_GearBoxLabel(&it,line,sizeof(line))>0 && !strncmp(line,"Long blade 2H",13) && strstr(line,"Steel Claymore") &&
               !strstr(line,"carry only"));
        it.subtype=9;it.flags=0;                                     /* a bow: not equippable in this engine yet */
        assert(AW_GearBoxLabel(&it,line,sizeof(line))>0 && !strncmp(line,"Bow",3) && strstr(line,"(carry only)"));
        it.subtype=14;assert(AW_GearBoxKind(&it)==AW_GEARBOX_NONE && AW_GearBoxLabel(&it,line,sizeof(line))==-1);
        it.category=AW_INV_ARMOUR;it.subtype=8;it.shield_class=2;  /* a heavy shield: in the weapon box, after the weapons */
        assert(AW_GearBoxKind(&it)==AW_GEARBOX_WEAPON && AW_GearBoxOrder(&it)==16);
        assert(AW_GearBoxLabel(&it,line,sizeof(line))>0 && !strncmp(line,"Shield heavy",12));
        it.subtype=5;it.shield_class=0;                              /* light boots: the gear box */
        assert(AW_GearBoxKind(&it)==AW_GEARBOX_GEAR && AW_GearBoxOrder(&it)==15);
        it.category=AW_INV_CLOTHING;it.subtype=4;assert(AW_GearBoxKind(&it)==AW_GEARBOX_GEAR && AW_GearBoxOrder(&it)==44);
        it.name[0]=0;assert(AW_GearBoxLabel(&it,line,sizeof(line))>0 && strstr(line,"steel claymore"));   /* no name: the id */
        assert(AW_GearBoxLabel(&it,line,4)==-1 && AW_GearBoxLabel(NULL,line,sizeof(line))==-1);
        it.category=AW_INV_POTION;assert(AW_GearBoxKind(&it)==AW_GEARBOX_NONE && AW_GearBoxOrder(&it)==-1);
        it.category=AW_INV_WEAPON;it.subtype=1;strcpy(it.name,"A name long enough to be cut at the box's line width, past it");
        assert(AW_GearBoxLabel(&it,line,sizeof(line))==63 && strlen(line)==63);
        printf("gear box rules: ok\n");
    }
    return 0;
}
