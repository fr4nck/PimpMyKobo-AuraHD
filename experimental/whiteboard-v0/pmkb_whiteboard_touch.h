/* L07-C: strictly sequential synthetic touch dispatcher, host-only.
 * Model and pixels must have identical geometry; no evdev access. */
#ifndef PMKB_WHITEBOARD_TOUCH_H
#define PMKB_WHITEBOARD_TOUCH_H
#include "pmkb_whiteboard_render.h"

typedef enum {
    PMKB_WB_TOUCH_DOWN, PMKB_WB_TOUCH_MOVE,
    PMKB_WB_TOUCH_UP, PMKB_WB_TOUCH_CANCEL
} PMKBWBTouchKind;

static inline PMKBWBStatus pmkb_wb_touch(
    PMKBWBModel *board, PMKBSurface *surface, PMKBWBTouchKind kind,
    int x, int y, unsigned shade, unsigned thickness) {
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
#endif
