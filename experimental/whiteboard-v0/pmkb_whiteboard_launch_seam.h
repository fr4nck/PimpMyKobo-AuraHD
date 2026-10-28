/* L07-L: integration seam for a future PMKBAppHost whiteboard case.
 * Deliberately independent of the stale Launcher bridge on this PR branch.
 * The actual host bridge must be reconciled with main (Store runnable). */
#ifndef PMKB_WHITEBOARD_LAUNCH_SEAM_H
#define PMKB_WHITEBOARD_LAUNCH_SEAM_H
#include "pmkb_whiteboard_app.h"

typedef struct {
    PMKBWhiteboardApp app;
    bool open;
} PMKBWhiteboardSession;

static inline PMKBStatus pmkb_wb_session_open(
    PMKBWhiteboardSession *session,int width,int height) {
    if(!session || session->open)return PMKB_INVALID;
    PMKBStatus status=pmkb_wb_app_init(&session->app,width,height);
    if(status==PMKB_OK)session->open=true;
    return status;
}
static inline PMKBStatus pmkb_wb_session_close(
    PMKBWhiteboardSession *session,bool discard) {
    if(!session || !session->open)return PMKB_NO_CHANGE;
    if(!discard && session->app.board &&
       (session->app.board->total>0 || session->app.board->in_stroke))
        return PMKB_UNSAVED;
    pmkb_wb_app_free(&session->app);
    session->open=false;
    return PMKB_OK;
}
static inline PMKBSurface *pmkb_wb_session_screen(
    PMKBWhiteboardSession *session) {
    if(!session || !session->open)return NULL;
    return &session->app.screen;
}
static inline PMKBWBStatus pmkb_wb_session_touch(
    PMKBWhiteboardSession *session,PMKBWBTouchKind kind,int x,int y) {
    if(!session || !session->open)return PMKB_WB_INVALID;
    return pmkb_wb_app_touch(&session->app,kind,x,y);
}
#endif
