/* L07-K: native launcher-ready Whiteboard app owner, no host mutation. */
#ifndef PMKB_WHITEBOARD_APP_H
#define PMKB_WHITEBOARD_APP_H
#include "pmkb_whiteboard_touch.h"
#include <stdlib.h>

typedef struct {
    PMKBWBModel *board; /* bounded model allocated on launch only */
    PMKBSurface screen;
    unsigned shade,thickness;
} PMKBWhiteboardApp;

static inline PMKBStatus pmkb_wb_app_init(PMKBWhiteboardApp *app,int w,int h) {
    if(!app)return PMKB_INVALID;
    *app=(PMKBWhiteboardApp){0};
    app->board=(PMKBWBModel*)calloc(1,sizeof(PMKBWBModel));
    if(!app->board)return PMKB_MEMORY;
    if(pmkb_wb_init(app->board,w,h)!=PMKB_WB_OK) {
        free(app->board);app->board=NULL;return PMKB_INVALID;
    }
    PMKBStatus rc=pmkb_surface_init(&app->screen,w,h);
    if(rc!=PMKB_OK){free(app->board);app->board=NULL;return rc;}
    app->shade=0u;app->thickness=2u;
    return PMKB_OK;
}
static inline void pmkb_wb_app_free(PMKBWhiteboardApp *app) {
    if(!app)return;
    pmkb_surface_free(&app->screen);
    free(app->board);
    *app=(PMKBWhiteboardApp){0};
}
static inline PMKBWBStatus pmkb_wb_app_touch(
    PMKBWhiteboardApp *app,PMKBWBTouchKind kind,int x,int y) {
    if(!app||!app->board)return PMKB_WB_INVALID;
    if(kind==PMKB_WB_TOUCH_MOVE)
        return pmkb_wb_touch_stream_move(app->board,&app->screen,x,y);
    return pmkb_wb_touch(app->board,&app->screen,kind,x,y,
                         app->shade,app->thickness);
}
static inline PMKBWBStatus pmkb_wb_app_undo(PMKBWhiteboardApp *app) {
    if(!app||!app->board)return PMKB_WB_INVALID;
    PMKBWBStatus rc=pmkb_wb_undo(app->board);
    if(rc==PMKB_WB_OK && pmkb_wb_render_replay(app->board,&app->screen)!=PMKB_OK)
        return PMKB_WB_INVALID;
    return rc;
}
static inline PMKBWBStatus pmkb_wb_app_redo(PMKBWhiteboardApp *app) {
    if(!app||!app->board)return PMKB_WB_INVALID;
    PMKBWBStatus rc=pmkb_wb_redo(app->board);
    if(rc==PMKB_WB_OK && pmkb_wb_render_replay(app->board,&app->screen)!=PMKB_OK)
        return PMKB_WB_INVALID;
    return rc;
}
static inline PMKBWBStatus pmkb_wb_app_clear(PMKBWhiteboardApp *app) {
    if(!app||!app->board)return PMKB_WB_INVALID;
    PMKBWBStatus rc=pmkb_wb_clear(app->board);
    if(rc==PMKB_WB_OK && pmkb_wb_render_replay(app->board,&app->screen)!=PMKB_OK)
        return PMKB_WB_INVALID;
    return rc;
}
#endif
