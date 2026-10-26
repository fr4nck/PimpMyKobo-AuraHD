/* TB0: deterministic host-only tests of the frugal stroke journal. */
#include "pmkb_whiteboard_model.h"
#include <stdio.h>

static unsigned checks, fails;
static PMKBWBModel board;
#define CHECK(expr) do { ++checks; if (!(expr)) { ++fails; \
    fprintf(stderr,"WHITEBOARD FAIL line %u: %s\n", \
            (unsigned)__LINE__, #expr); } } while (0)

static void test_geometry_and_input(void) {
    CHECK(sizeof(PMKBWBModel)<32768u);
    CHECK(pmkb_wb_init(NULL,320,480)==PMKB_WB_INVALID);
    CHECK(pmkb_wb_init(&board,0,480)==PMKB_WB_INVALID);
    CHECK(pmkb_wb_init(&board,320,1441)==PMKB_WB_INVALID);
    CHECK(pmkb_wb_init(&board,1080,1440)==PMKB_WB_OK);
    CHECK(board.total==0u && board.visible==0u && !board.in_stroke);
    CHECK(pmkb_wb_move(&board,0,0)==PMKB_WB_INVALID);
    CHECK(pmkb_wb_up(&board,0,0)==PMKB_WB_INVALID);
    CHECK(pmkb_wb_down(&board,-1,0,0,1)==PMKB_WB_INVALID);
    CHECK(pmkb_wb_down(&board,1080,0,0,1)==PMKB_WB_INVALID);
    CHECK(pmkb_wb_down(&board,0,1440,0,1)==PMKB_WB_INVALID);
    CHECK(pmkb_wb_down(&board,0,0,16,1)==PMKB_WB_INVALID);
    CHECK(pmkb_wb_down(&board,0,0,0,0)==PMKB_WB_INVALID);
    CHECK(pmkb_wb_down(&board,0,0,0,26)==PMKB_WB_INVALID);
    CHECK(board.visible==0u && !board.in_stroke);
}
static void test_dot_and_undo_redo(void) {
    CHECK(pmkb_wb_down(&board,1079,1439,15,25)==PMKB_WB_OK);
    CHECK(pmkb_wb_move(&board,1079,1439)==PMKB_WB_NO_CHANGE);
    CHECK(pmkb_wb_up(&board,1079,1439)==PMKB_WB_OK);
    CHECK(board.total==1u && board.visible==1u);
    CHECK(board.strokes[0].count==1u);
    CHECK(board.strokes[0].points[0].x==1079);
    CHECK(board.strokes[0].points[0].y==1439);
    CHECK(board.strokes[0].shade==15u && board.strokes[0].thickness==25u);
    CHECK(pmkb_wb_visible_points(&board)==1u);
    CHECK(pmkb_wb_redo(&board)==PMKB_WB_NO_CHANGE);
    CHECK(pmkb_wb_undo(&board)==PMKB_WB_OK);
    CHECK(board.visible==0u && board.total==1u);
    CHECK(pmkb_wb_undo(&board)==PMKB_WB_NO_CHANGE);
    CHECK(pmkb_wb_redo(&board)==PMKB_WB_OK);
    CHECK(board.visible==1u);
}
static void test_working_and_redo_history(void) {
    CHECK(pmkb_wb_down(&board,100,200,8,2)==PMKB_WB_OK);
    CHECK(pmkb_wb_down(&board,10,10,0,1)==PMKB_WB_INVALID);
    CHECK(pmkb_wb_undo(&board)==PMKB_WB_INVALID);
    CHECK(pmkb_wb_clear(&board)==PMKB_WB_INVALID);
    CHECK(pmkb_wb_move(&board,-1,200)==PMKB_WB_INVALID);
    CHECK(pmkb_wb_move(&board,110,210)==PMKB_WB_OK);
    CHECK(pmkb_wb_up(&board,120,220)==PMKB_WB_OK);
    CHECK(board.total==2u && board.visible==2u);
    CHECK(board.strokes[1].count==3u);
    CHECK(pmkb_wb_visible_points(&board)==4u);
    CHECK(pmkb_wb_undo(&board)==PMKB_WB_OK);
    CHECK(board.visible==1u && board.total==2u);
    CHECK(pmkb_wb_down(&board,4,4,0,1)==PMKB_WB_OK);
    CHECK(pmkb_wb_move(&board,8,8)==PMKB_WB_OK);
    CHECK(pmkb_wb_cancel(&board)==PMKB_WB_OK);
    CHECK(pmkb_wb_cancel(&board)==PMKB_WB_INVALID);
    CHECK(board.visible==1u && board.total==2u);
    CHECK(pmkb_wb_redo(&board)==PMKB_WB_OK); /* cancel preserves redo */
    CHECK(pmkb_wb_undo(&board)==PMKB_WB_OK);
    CHECK(pmkb_wb_down(&board,7,7,0,1)==PMKB_WB_OK);
    CHECK(board.total==2u); /* no redo truncation before UP */
    CHECK(pmkb_wb_up(&board,8,8)==PMKB_WB_OK);
    CHECK(board.visible==2u && board.total==2u);
    CHECK(board.strokes[1].points[0].x==7u);
    CHECK(pmkb_wb_redo(&board)==PMKB_WB_NO_CHANGE);
    CHECK(pmkb_wb_clear(&board)==PMKB_WB_OK);
    CHECK(board.visible==0u && board.total==0u);
    CHECK(pmkb_wb_clear(&board)==PMKB_WB_NO_CHANGE);
}
static void test_stroke_capacity(void) {
    CHECK(pmkb_wb_init(&board,320,480)==PMKB_WB_OK);
    for (unsigned i=0;i<PMKB_WB_MAX_STROKES;i++) {
        CHECK(pmkb_wb_down(&board,(int)i,0,0,1)==PMKB_WB_OK);
        CHECK(pmkb_wb_up(&board,(int)i,0)==PMKB_WB_OK);
    }
    CHECK(board.visible==PMKB_WB_MAX_STROKES);
    CHECK(board.total==PMKB_WB_MAX_STROKES);
    CHECK(pmkb_wb_down(&board,100,0,0,1)==PMKB_WB_LIMIT);
    CHECK(!board.in_stroke);
    CHECK(pmkb_wb_undo(&board)==PMKB_WB_OK);
    CHECK(pmkb_wb_down(&board,100,0,0,1)==PMKB_WB_OK);
    CHECK(pmkb_wb_up(&board,100,0)==PMKB_WB_OK);
    CHECK(board.visible==PMKB_WB_MAX_STROKES);
    CHECK(board.strokes[PMKB_WB_MAX_STROKES-1u].points[0].x==100u);
    CHECK(pmkb_wb_redo(&board)==PMKB_WB_NO_CHANGE);
}
static void test_point_capacity_and_cancel(void) {
    CHECK(pmkb_wb_init(&board,320,480)==PMKB_WB_OK);
    CHECK(pmkb_wb_down(&board,0,0,0,1)==PMKB_WB_OK);
    for (unsigned x=1;x<PMKB_WB_MAX_POINTS_PER_STROKE;x++)
        CHECK(pmkb_wb_move(&board,(int)x,0)==PMKB_WB_OK);
    CHECK(board.working.count==PMKB_WB_MAX_POINTS_PER_STROKE);
    CHECK(pmkb_wb_move(&board,95,0)==PMKB_WB_NO_CHANGE);
    CHECK(pmkb_wb_move(&board,96,0)==PMKB_WB_LIMIT);
    CHECK(pmkb_wb_up(&board,96,0)==PMKB_WB_LIMIT);
    CHECK(board.in_stroke && board.total==0u && board.visible==0u);
    CHECK(pmkb_wb_cancel(&board)==PMKB_WB_OK);
    CHECK(!board.in_stroke && board.total==0u);
    CHECK(pmkb_wb_up(&board,0,0)==PMKB_WB_INVALID);
    CHECK(pmkb_wb_down(&board,0,0,3,1)==PMKB_WB_OK);
    CHECK(pmkb_wb_up(&board,1,1)==PMKB_WB_OK);
    CHECK(board.strokes[0].count==2u);
}
int main(void) {
    test_geometry_and_input();
    test_dot_and_undo_redo();
    test_working_and_redo_history();
    test_stroke_capacity();
    test_point_capacity_and_cancel();
    if (fails) {
        fprintf(stderr,"WHITEBOARD TB0: %u checks, %u FAIL\n",checks,fails);
        return 1;
    }
    printf("WHITEBOARD TB0: %u assertions PASS, 0 FAIL\n",checks);
    return 0;
}
