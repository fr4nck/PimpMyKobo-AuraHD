/* L07-B: deterministic host renderer on the existing PMKB-UI gray surface. */
#ifndef PMKB_WHITEBOARD_RENDER_H
#define PMKB_WHITEBOARD_RENDER_H
#include "pmkb_whiteboard_model.h"
#include "pmkb_ui.h"

static inline void pmkb_wb_stamp(PMKBSurface *surface,int x,int y,
                                 unsigned thickness,uint8_t shade) {
    int radius=(int)thickness/2;
    pmkb_surface_rect(surface,
        (PMKBRect){x-radius,y-radius,(int)thickness,(int)thickness},shade);
}
static inline void pmkb_wb_segment(PMKBSurface *surface,PMKBWBPoint a,
                                   PMKBWBPoint b,unsigned thickness,
                                   uint8_t shade) {
    int x=(int)a.x,y=(int)a.y;
    int dx=(int)b.x-x,dy=(int)b.y-y;
    int sx=dx>=0?1:-1,sy=dy>=0?1:-1;
    if(dx<0)dx=-dx;
    if(dy<0)dy=-dy;
    int err=dx-dy;
    for (;;) {
        pmkb_wb_stamp(surface,x,y,thickness,shade);
        if(x==(int)b.x && y==(int)b.y)break;
        int twice=2*err;
        if(twice>-dy){err-=dy;x+=sx;}
        if(twice<dx){err+=dx;y+=sy;}
    }
}
static inline void pmkb_wb_render_stroke(PMKBSurface *surface,
                                         const PMKBWBStroke *stroke) {
    if(!surface || !surface->gray || !stroke || !stroke->count)return;
    uint8_t shade=(uint8_t)(stroke->shade*17u);
    pmkb_wb_stamp(surface,(int)stroke->points[0].x,
                  (int)stroke->points[0].y,stroke->thickness,shade);
    for(unsigned i=1;i<stroke->count;i++)
        pmkb_wb_segment(surface,stroke->points[i-1],stroke->points[i],
                        stroke->thickness,shade);
}
/* Full replay is reserved for undo/redo/clear. Incremental UP only renders
 * the committed stroke; PMKB surface tracks the real changed rectangles. */
static inline PMKBStatus pmkb_wb_render_commit(const PMKBWBModel *board,
                                              PMKBSurface *surface) {
    if(!board || !surface || !surface->gray || board->in_stroke ||
       board->width!=surface->width || board->height!=surface->height ||
       !board->visible || board->visible>PMKB_WB_MAX_STROKES)
        return PMKB_INVALID;
    pmkb_wb_render_stroke(surface,&board->strokes[board->visible-1]);
    return PMKB_OK;
}
static inline PMKBStatus pmkb_wb_render_replay(const PMKBWBModel *board,
                                              PMKBSurface *surface) {
    if(!board || !surface || !surface->gray || board->in_stroke ||
       board->width!=surface->width || board->height!=surface->height ||
       board->visible>board->total || board->total>PMKB_WB_MAX_STROKES)
        return PMKB_INVALID;
    pmkb_surface_rect(surface,(PMKBRect){0,0,surface->width,surface->height},255);
    for(unsigned i=0;i<board->visible;i++)
        pmkb_wb_render_stroke(surface,&board->strokes[i]);
    return PMKB_OK;
}
#endif
