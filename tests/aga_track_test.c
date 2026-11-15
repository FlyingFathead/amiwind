/* SPDX-License-Identifier: GPL-2.0-or-later */
/* Native check of engine/aga/src/aw_track.c (tests/test_track_native.py): reads a record file and prints what the
 * engine would play.
 *   aga_track_test RECORD info              -> "movers M frames F rate R seconds S" and one "mover N NAME" line each
 *   aga_track_test RECORD sample M SECONDS  -> "x y z w qx qy qz" and the row-vector matrix
 *   aga_track_test RECORD sounds FROM TO    -> one sound id per line
 * Exit 2 when the record is refused. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "aw_track.h"

int main(int argc,char **argv) {
    static unsigned char buf[1<<20];
    FILE *f;int n;aw_track_t t;
    if(argc<3)return 1;
    if(!(f=fopen(argv[1],"rb")))return 1;
    n=(int)fread(buf,1,sizeof(buf),f);fclose(f);
    if(!AW_TrackParse(buf,n,&t)){printf("refused\n");return 2;}
    if(!strcmp(argv[2],"info")){
        int m;char name[AW_TRACK_NAME];
        printf("movers %d frames %d rate %g seconds %g\n",t.movers,t.frames,t.rate,AW_TrackSeconds(&t));
        for(m=0;m<t.movers;m++){int node=AW_TrackMover(&t,m,name,sizeof(name));printf("mover %d %s\n",node,name);}
        return 0;
    }
    if(!strcmp(argv[2],"sample") && argc>=5){
        float p[3],q[4],mat[3][3];int i;
        if(!AW_TrackSample(&t,atoi(argv[3]),(float)atof(argv[4]),p,q))return 3;
        AW_TrackMatrix(q,mat);
        printf("%.6f %.6f %.6f %.6f %.6f %.6f %.6f\n",p[0],p[1],p[2],q[0],q[1],q[2],q[3]);
        for(i=0;i<3;i++)printf("%.6f %.6f %.6f\n",mat[i][0],mat[i][1],mat[i][2]);
        return 0;
    }
    if(!strcmp(argv[2],"sounds") && argc>=5){
        char ids[8][AW_TRACK_SOUND_NAME];int k,c=AW_TrackSoundsBetween(&t,(float)atof(argv[3]),(float)atof(argv[4]),ids,8);
        for(k=0;k<c;k++)printf("%s\n",ids[k]);
        return 0;
    }
    return 1;
}
