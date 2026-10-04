#include <assert.h>
#include "aw_render_ranges.h"
int main(void)
{
    aw_render_range_t ranges[4];
    assert(AW_ParseRenderRanges("0:3,7:2",10,ranges,4)==2);
    assert(ranges[0].start==0 && ranges[0].count==3 && ranges[1].start==7 && ranges[1].count==2);
    assert(AW_ParseRenderRanges("9:1",10,ranges,4)==1);
    assert(AW_ParseRenderRanges("9:2",10,ranges,4)==-1);
    assert(AW_ParseRenderRanges("-1:1",10,ranges,4)==-1);
    assert(AW_ParseRenderRanges("0:0",10,ranges,4)==-1);
    assert(AW_ParseRenderRanges("2147483648:1",10,ranges,4)==-1);
    assert(AW_ParseRenderRanges("0:99999999999999999999999",10,ranges,4)==-1);
    assert(AW_ParseRenderRanges("0:1,",10,ranges,4)==-1);
    assert(AW_ParseRenderRanges("0:1,1:1",10,ranges,1)==-1);
    assert(AW_ParseRenderRanges("0:1junk",10,ranges,4)==-1);
    assert(AW_ParseRenderRanges("",10,ranges,4)==-1);
    return 0;
}
