/* L07-C: strictly sequential synthetic touch dispatcher, host-only.
 * Model and pixels must have identical geometry; no evdev access. */
#ifndef PMKB_WHITEBOARD_TOUCH_H
#define PMKB_WHITEBOARD_TOUCH_H
#include "pmkb_whiteboard_render.h"

typedef enum {
    PMKB_WB_TOUCH_DOWN, PMKB_WB_TOUCH_MOVE,
    PMKB_WB_TOUCH_UP, PMKB_WB_TOUCH_CANCEL,
    PMKB_WB_TOUCH_INTERRUPT
} PMKBWBTouchKind;

/* Explicit input-stream loss: discard an uncommitted gesture even if the
 * framebuffer was already released. Never redraw or fabricate a final UP. */
static inline PMKBWBStatus pmkb_wb_touch_interrupt(PMKBWBModel *board) {
    if (!board) return PMKB_WB_INVALID;
    if (!board->in_stroke) return PMKB_WB_NO_CHANGE;
    return pmkb_wb_cancel(board);
}
static inline PMKBWBStatus pmkb_wb_touch(
    PMKBWBModel *board, PMKBSurface *surface, PMKBWBTouchKind kind,
    int x, int y, unsigned shade, unsigned thickness) {
    if (kind==PMKB_WB_TOUCH_INTERRUPT)
        return pmkb_wb_touch_interrupt(board);
    if (!board || !surface || !surface->gray ||
        board->width!=surface->width || board->height!=surface->height)
        return PMKB_WB_INVALID;
    switch(kind) {
    case PMKB_WB_TOUCH_DOWN:
        return pmkb_wb_down(board,x,y,shade,thickness);
    case PMKB_WB_TOUCH_MOVE:
        return pmkb_wb_move(board,x,y);
    case PMKB_WB_TOUCH_CANCEL:
        return pmkb_wb_cancel(board);
    case PMKB_WB_TOUCH_UP: {
        PMKBWBStatus result=pmkb_wb_up(board,x,y);
        if(result!=PMKB_WB_OK)return result;
        /* Only a committed stroke may change the framebuffer. */
        return pmkb_wb_render_commit(board,surface)==PMKB_OK ?
            PMKB_WB_OK : PMKB_WB_INVALID;
    }
    default: return PMKB_WB_INVALID;
    }
}
/* L07-F opt-in streaming MOVE: at 96 points, commit a chunk and
 * restart at its terminal point to preserve the connecting segment.
 * Never split unless room remains for both the committed and active chunks. */
static inline PMKBWBStatus pmkb_wb_touch_stream_move(
    PMKBWBModel *board, PMKBSurface *surface, int x, int y) {
    if (!board || !surface || !surface->gray ||
        board->width!=surface->width || board->height!=surface->height ||
        !board->in_stroke || !pmkb_wb_in_bounds(board,x,y))
        return PMKB_WB_INVALID;
    PMKBWBStatus result=pmkb_wb_move(board,x,y);
    if (result!=PMKB_WB_LIMIT) return result;
    if (board->visible+1u>=PMKB_WB_MAX_STROKES)
        return PMKB_WB_LIMIT; /* no partial split at journal capacity */
    PMKBWBStroke *active=&board->working;
    PMKBWBPoint last=active->points[active->count-1u];
    const unsigned shade=active->shade, thickness=active->thickness;
    /* Prevalidated: this UP duplicates the last point and cannot overflow. */
    if (pmkb_wb_up(board,last.x,last.y)!=PMKB_WB_OK)
        return PMKB_WB_INVALID;
    (void)pmkb_wb_render_commit(board,surface);
    if (pmkb_wb_down(board,last.x,last.y,shade,thickness)!=PMKB_WB_OK)
        return PMKB_WB_INVALID;
    return pmkb_wb_move(board,x,y);
}
#endif
