#include "pmkb_whiteboard_touch.h"
#include <stdio.h>
static unsigned checks, fails;
#define CHECK(x) do { ++checks; if(!(x)){ ++fails; \
 fprintf(stderr,"TOUCH FAIL line %u: %s\n",(unsigned)__LINE__,#x); }}while(0)
int main(void) {
 PMKBWBModel board={0}; PMKBSurface screen={0}; PMKBRect dirty;
 CHECK(pmkb_wb_init(&board,320,480)==PMKB_WB_OK);
 CHECK(pmkb_surface_init(&screen,320,480)==PMKB_OK);
 if(!screen.gray)return 1;
 CHECK(pmkb_surface_take_dirty(&screen,&dirty));
 CHECK(pmkb_wb_touch(&board,&screen,PMKB_WB_TOUCH_MOVE,10,10,0,1)==PMKB_WB_INVALID);
 CHECK(pmkb_wb_touch(&board,&screen,PMKB_WB_TOUCH_DOWN,10,10,0,1)==PMKB_WB_OK);
 CHECK(pmkb_wb_touch(&board,&screen,PMKB_WB_TOUCH_DOWN,20,20,0,1)==PMKB_WB_INVALID);
 CHECK(pmkb_wb_touch(&board,&screen,PMKB_WB_TOUCH_MOVE,11,10,0,1)==PMKB_WB_OK);
 CHECK(pmkb_wb_touch(&board,&screen,PMKB_WB_TOUCH_MOVE,-1,10,0,1)==PMKB_WB_INVALID);
 CHECK(!screen.has_dirty && board.in_stroke);
 CHECK(pmkb_wb_touch(&board,&screen,PMKB_WB_TOUCH_CANCEL,0,0,0,1)==PMKB_WB_OK);
 CHECK(!screen.has_dirty && board.total==0u && !board.in_stroke);
 CHECK(pmkb_wb_touch(&board,&screen,PMKB_WB_TOUCH_UP,11,10,0,1)==PMKB_WB_INVALID);
 CHECK(pmkb_wb_touch(&board,&screen,PMKB_WB_TOUCH_DOWN,15,15,0,1)==PMKB_WB_OK);
 CHECK(pmkb_wb_touch(&board,&screen,PMKB_WB_TOUCH_MOVE,16,15,0,1)==PMKB_WB_OK);
 CHECK(pmkb_wb_touch(&board,&screen,PMKB_WB_TOUCH_UP,18,15,0,1)==PMKB_WB_OK);
 CHECK(screen.has_dirty && board.visible==1u && !board.in_stroke);
 CHECK(screen.gray[(size_t)15*320u+15u]==0);
 CHECK(screen.gray[(size_t)15*320u+18u]==0);
 CHECK(pmkb_surface_take_dirty(&screen,&dirty));
 CHECK(dirty.x==15 && dirty.y==15 && dirty.w==4 && dirty.h==1);
 CHECK(pmkb_wb_touch(&board,&screen,PMKB_WB_TOUCH_UP,18,15,0,1)==PMKB_WB_INVALID);
 CHECK(!screen.has_dirty);
 CHECK(pmkb_wb_touch(&board,&screen,(PMKBWBTouchKind)99,0,0,0,1)==PMKB_WB_INVALID);
 CHECK(pmkb_wb_touch(&board,&screen,PMKB_WB_TOUCH_DOWN,319,479,15,1)==PMKB_WB_OK);
 CHECK(pmkb_wb_touch(&board,&screen,PMKB_WB_TOUCH_UP,319,479,15,1)==PMKB_WB_OK);
 CHECK(board.visible==2u);
 CHECK(pmkb_wb_touch(&board,&screen,PMKB_WB_TOUCH_DOWN,320,479,0,1)==PMKB_WB_INVALID);
 /* White-on-white is no pixel change: do not require a dirty region. */
 CHECK(!screen.has_dirty);
 /* LOST-UP: interruption never commits the unfinished gesture. */
 CHECK(pmkb_wb_touch(&board,&screen,PMKB_WB_TOUCH_DOWN,40,40,0,1)==PMKB_WB_OK);
 CHECK(pmkb_wb_touch(&board,&screen,PMKB_WB_TOUCH_MOVE,41,41,0,1)==PMKB_WB_OK);
 CHECK(pmkb_wb_touch(&board,&screen,PMKB_WB_TOUCH_INTERRUPT,-1,-1,0,0)==PMKB_WB_OK);
 CHECK(!board.in_stroke && board.visible==2u && !screen.has_dirty);
 CHECK(pmkb_wb_touch(&board,&screen,PMKB_WB_TOUCH_UP,42,42,0,1)==PMKB_WB_INVALID);
 CHECK(pmkb_wb_touch_interrupt(&board)==PMKB_WB_NO_CHANGE);
 CHECK(pmkb_wb_touch(&board,&screen,PMKB_WB_TOUCH_DOWN,50,50,0,1)==PMKB_WB_OK);
 CHECK(pmkb_wb_touch_interrupt(&board)==PMKB_WB_OK);
 CHECK(board.visible==2u && !screen.has_dirty);
 /* L07-E: limit must never truncate the 97th point silently. */
 CHECK(pmkb_wb_init(&board,320,480)==PMKB_WB_OK);
 CHECK(pmkb_wb_touch(&board,&screen,PMKB_WB_TOUCH_DOWN,0,100,0,1)==PMKB_WB_OK);
 for(int x=1;x<96;x++)
     CHECK(pmkb_wb_touch(&board,&screen,PMKB_WB_TOUCH_MOVE,x,100,0,1)==PMKB_WB_OK);
 CHECK(board.working.count==PMKB_WB_MAX_POINTS_PER_STROKE);
 CHECK(pmkb_wb_touch(&board,&screen,PMKB_WB_TOUCH_MOVE,96,100,0,1)==PMKB_WB_LIMIT);
 CHECK(pmkb_wb_touch(&board,&screen,PMKB_WB_TOUCH_UP,96,100,0,1)==PMKB_WB_LIMIT);
 CHECK(board.in_stroke && board.visible==0u && board.working.count==96u);
 CHECK(pmkb_wb_touch(&board,&screen,PMKB_WB_TOUCH_UP,95,100,0,1)==PMKB_WB_OK);
 CHECK(board.visible==1u && !board.in_stroke && board.strokes[0].count==96u);
 CHECK(screen.gray[(size_t)100*320u+95u]==0);
 CHECK(screen.gray[(size_t)100*320u+96u]==255);
 CHECK(pmkb_wb_touch(&board,&screen,PMKB_WB_TOUCH_DOWN,95,100,0,1)==PMKB_WB_OK);
 CHECK(pmkb_wb_touch(&board,&screen,PMKB_WB_TOUCH_UP,96,100,0,1)==PMKB_WB_OK);
 CHECK(board.visible==2u && board.strokes[1].count==2u);
 CHECK(screen.gray[(size_t)100*320u+96u]==0);
 pmkb_surface_free(&screen);
 CHECK(pmkb_wb_touch_interrupt(NULL)==PMKB_WB_INVALID);
 CHECK(pmkb_wb_touch_interrupt(&board)==PMKB_WB_NO_CHANGE);
 CHECK(pmkb_wb_touch(&board,&screen,PMKB_WB_TOUCH_DOWN,1,1,0,1)==PMKB_WB_INVALID);
 if(fails)return 1;
 printf("WHITEBOARD TOUCH: %u assertions PASS, 0 FAIL\n",checks);
 return 0;
}
