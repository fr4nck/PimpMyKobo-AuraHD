#include "pmkb_whiteboard_render.h"
#include <stdio.h>
static unsigned checks, fails;
#define CHECK(x) do { ++checks; if(!(x)) { ++fails; \
 fprintf(stderr,"RENDER FAIL line %u: %s\n",(unsigned)__LINE__,#x); } }while(0)
static uint8_t pixel(const PMKBSurface *s,int x,int y) {
 return s->gray[(size_t)y*(size_t)s->width+(size_t)x];
}
int main(void) {
 PMKBWBModel board={0};
 PMKBSurface surface={0};
 PMKBRect dirty={0};
 CHECK(pmkb_wb_init(&board,320,480)==PMKB_WB_OK);
 CHECK(pmkb_surface_init(&surface,320,480)==PMKB_OK);
 if(!surface.gray)return 1;
 CHECK(pmkb_surface_take_dirty(&surface,&dirty));
 CHECK(!surface.has_dirty);
 CHECK(pmkb_wb_down(&board,20,20,0,1)==PMKB_WB_OK);
 CHECK(pmkb_wb_up(&board,30,20)==PMKB_WB_OK);
 CHECK(pmkb_wb_render_commit(&board,&surface)==PMKB_OK);
 for(int x=20;x<=30;x++)CHECK(pixel(&surface,x,20)==0);
 CHECK(pixel(&surface,19,20)==255 && pixel(&surface,31,20)==255);
 CHECK(pmkb_surface_take_dirty(&surface,&dirty));
 CHECK(dirty.x==20 && dirty.y==20 && dirty.w==11 && dirty.h==1);
 CHECK(!pmkb_surface_take_dirty(&surface,&dirty));
 CHECK(pmkb_wb_down(&board,100,100,8,3)==PMKB_WB_OK);
 CHECK(pmkb_wb_move(&board,104,104)==PMKB_WB_OK);
 CHECK(pmkb_wb_up(&board,110,110)==PMKB_WB_OK);
 CHECK(pmkb_wb_render_commit(&board,&surface)==PMKB_OK);
 CHECK(pixel(&surface,100,100)==136 && pixel(&surface,110,110)==136);
 CHECK(pixel(&surface,20,20)==0);
 CHECK(pmkb_surface_take_dirty(&surface,&dirty));
 CHECK(dirty.x>=0 && dirty.y>=0 && dirty.x+dirty.w<=320 &&
       dirty.y+dirty.h<=480);
 CHECK(pmkb_wb_undo(&board)==PMKB_WB_OK);
 CHECK(pmkb_wb_render_replay(&board,&surface)==PMKB_OK);
 CHECK(pixel(&surface,100,100)==255 && pixel(&surface,20,20)==0);
 CHECK(pmkb_surface_take_dirty(&surface,&dirty));
 CHECK(pmkb_wb_redo(&board)==PMKB_WB_OK);
 CHECK(pmkb_wb_render_replay(&board,&surface)==PMKB_OK);
 CHECK(pixel(&surface,110,110)==136);
 CHECK(pmkb_wb_clear(&board)==PMKB_WB_OK);
 CHECK(pmkb_wb_render_replay(&board,&surface)==PMKB_OK);
 CHECK(pixel(&surface,20,20)==255 && pixel(&surface,110,110)==255);
 CHECK(pmkb_wb_render_commit(&board,&surface)==PMKB_INVALID);
 CHECK(pmkb_wb_init(&board,1080,1440)==PMKB_WB_OK);
 CHECK(pmkb_wb_render_replay(&board,&surface)==PMKB_INVALID);
 pmkb_surface_free(&surface);
 if(fails)return 1;
 printf("WHITEBOARD RENDER: %u assertions PASS, 0 FAIL\n",checks);
 return 0;
}
