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
 pmkb_surface_free(&screen);
 CHECK(pmkb_wb_touch(&board,&screen,PMKB_WB_TOUCH_DOWN,1,1,0,1)==PMKB_WB_INVALID);
 if(fails)return 1;
 printf("WHITEBOARD TOUCH: %u assertions PASS, 0 FAIL\n",checks);
 return 0;
}
