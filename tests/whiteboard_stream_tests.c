#include "pmkb_whiteboard_touch.h"
#include <stdio.h>
static unsigned checks,fails;
#define CHECK(x) do { ++checks; if(!(x)){ ++fails; fprintf(stderr,"STREAM FAIL %u: %s\n",(unsigned)__LINE__,#x); }}while(0)
int main(void) {
 PMKBWBModel board={0}; PMKBSurface screen={0}; PMKBRect dirty;
 CHECK(pmkb_wb_init(&board,320,480)==PMKB_WB_OK);
 CHECK(pmkb_surface_init(&screen,320,480)==PMKB_OK);
 if(!screen.gray)return 1;
 CHECK(pmkb_surface_take_dirty(&screen,&dirty));
 CHECK(pmkb_wb_down(&board,0,100,0,1)==PMKB_WB_OK);
 for(int i=1;i<96;i++) CHECK(pmkb_wb_touch_stream_move(&board,&screen,i,100)==PMKB_WB_OK);
 CHECK(board.visible==0u && board.in_stroke && !screen.has_dirty);
 CHECK(pmkb_wb_touch_stream_move(&board,&screen,96,100)==PMKB_WB_OK);
 CHECK(board.visible==1u && board.total==1u && board.in_stroke);
 CHECK(board.strokes[0].count==96u && board.working.count==2u);
 CHECK(board.strokes[0].points[95].x==95u && board.working.points[0].x==95u);
 CHECK(board.working.points[1].x==96u && screen.gray[(size_t)100*320u+95u]==0);
 CHECK(screen.gray[(size_t)100*320u+96u]==255);
 CHECK(pmkb_wb_touch(&board,&screen,PMKB_WB_TOUCH_UP,97,100,0,1)==PMKB_WB_OK);
 CHECK(board.visible==2u && !board.in_stroke);
 CHECK(screen.gray[(size_t)100*320u+97u]==0);
 CHECK(pmkb_surface_take_dirty(&screen,&dirty));
 CHECK(dirty.x==0 && dirty.y==100 && dirty.w==98 && dirty.h==1);
 CHECK(pmkb_wb_undo(&board)==PMKB_WB_OK);
 CHECK(pmkb_wb_render_replay(&board,&screen)==PMKB_OK);
 CHECK(screen.gray[(size_t)100*320u+95u]==0);
 CHECK(screen.gray[(size_t)100*320u+97u]==255);
 pmkb_surface_free(&screen);
 if(fails)return 1;
 printf("WHITEBOARD STREAM: %u assertions PASS, 0 FAIL\n",checks);
 return 0;
}
