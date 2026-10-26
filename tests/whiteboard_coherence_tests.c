/* L07-I: host-only framebuffer coherence after journal changes.
 * Reconstruct an independent reference from the visible stroke journal. */
#include "pmkb_whiteboard_touch.h"
#include <stdio.h>
#include <string.h>
static unsigned checks, fails;
#define CHECK(x) do { ++checks; if (!(x)) { ++fails; \
 fprintf(stderr,"COHERENCE FAIL line %u: %s\n",(unsigned)__LINE__,#x); } } while(0)
static void same_pixels(const PMKBWBModel *board,const PMKBSurface *actual) {
    PMKBSurface expected={0};
    CHECK(pmkb_surface_init(&expected,actual->width,actual->height)==PMKB_OK);
    if (!expected.gray)return;
    CHECK(pmkb_wb_render_replay(board,&expected)==PMKB_OK);
    size_t bytes=(size_t)actual->width*(size_t)actual->height;
    CHECK(memcmp(actual->gray,expected.gray,bytes)==0);
    pmkb_surface_free(&expected);
}
int main(void) {
    PMKBWBModel board={0};
    PMKBSurface actual={0};
    PMKBRect dirty;
    CHECK(pmkb_wb_init(&board,320,480)==PMKB_WB_OK);
    CHECK(pmkb_surface_init(&actual,320,480)==PMKB_OK);
    if (!actual.gray)return 1;
    CHECK(pmkb_surface_take_dirty(&actual,&dirty));
    CHECK(pmkb_wb_down(&board,2,25,0,1)==PMKB_WB_OK);
    for (int i=3;i<=97;i++)
        CHECK(pmkb_wb_touch_stream_move(&board,&actual,i,25)==PMKB_WB_OK);
    CHECK(pmkb_wb_touch_stream_move(&board,&actual,98,25)==PMKB_WB_OK);
    CHECK(board.visible==1u && board.in_stroke);
    CHECK(pmkb_wb_touch_interrupt(&board)==PMKB_WB_OK);
    CHECK(board.visible==1u && !board.in_stroke);
    same_pixels(&board,&actual); /* committed chunk remains */
    CHECK(pmkb_wb_undo(&board)==PMKB_WB_OK);
    CHECK(pmkb_wb_render_replay(&board,&actual)==PMKB_OK);
    same_pixels(&board,&actual);
    CHECK(pmkb_wb_redo(&board)==PMKB_WB_OK);
    CHECK(pmkb_wb_render_replay(&board,&actual)==PMKB_OK);
    same_pixels(&board,&actual);
    CHECK(pmkb_wb_down(&board,180,160,9,3)==PMKB_WB_OK);
    CHECK(pmkb_wb_move(&board,190,170)==PMKB_WB_OK);
    CHECK(pmkb_wb_cancel(&board)==PMKB_WB_OK);
    same_pixels(&board,&actual); /* canceled gesture draws nothing */
    CHECK(pmkb_wb_down(&board,200,200,7,3)==PMKB_WB_OK);
    CHECK(pmkb_wb_up(&board,201,200)==PMKB_WB_OK);
    CHECK(pmkb_wb_render_commit(&board,&actual)==PMKB_OK);
    same_pixels(&board,&actual);
    CHECK(pmkb_wb_clear(&board)==PMKB_WB_OK);
    CHECK(pmkb_wb_render_replay(&board,&actual)==PMKB_OK);
    same_pixels(&board,&actual);
    CHECK(pmkb_surface_take_dirty(&actual,&dirty));
    CHECK(dirty.x>=0 && dirty.y>=0 && dirty.w>0 && dirty.h>0);
    CHECK(dirty.x+dirty.w<=320 && dirty.y+dirty.h<=480);
    pmkb_surface_free(&actual);
    if (fails)return 1;
    printf("WHITEBOARD COHERENCE: %u assertions PASS, 0 FAIL\n",checks);
    return 0;
}
