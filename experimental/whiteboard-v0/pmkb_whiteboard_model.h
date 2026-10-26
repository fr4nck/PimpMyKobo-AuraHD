/* PMKB Tableau blanc TB0: bounded C11 stroke journal, host model only.
 * No framebuffer, input device, filesystem, networking or allocations. */
#ifndef PMKB_WHITEBOARD_MODEL_H
#define PMKB_WHITEBOARD_MODEL_H
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>

#define PMKB_WB_MAX_AXIS 1440
#define PMKB_WB_MAX_STROKES 64u
#define PMKB_WB_MAX_POINTS_PER_STROKE 96u
#define PMKB_WB_MAX_THICKNESS 25u

typedef enum {
    PMKB_WB_OK=0, PMKB_WB_INVALID=-1, PMKB_WB_LIMIT=-2,
    PMKB_WB_NO_CHANGE=-3
} PMKBWBStatus;

typedef struct { uint16_t x, y; } PMKBWBPoint;
typedef struct {
    PMKBWBPoint points[PMKB_WB_MAX_POINTS_PER_STROKE];
    uint16_t count;
    uint8_t shade;          /* 0..15, 16 fixed e-ink grayscale levels */
    uint8_t thickness;      /* 1..25 logical pixels; no pressure input */
    uint8_t continuation;   /* this chunk follows the previous same gesture */
} PMKBWBStroke;
typedef struct {
    PMKBWBStroke strokes[PMKB_WB_MAX_STROKES];
    PMKBWBStroke working;   /* incomplete stroke, not committed to undo */
    int width, height;
    unsigned total, visible; /* visible <= total <= capacity */
    bool in_stroke;
} PMKBWBModel;

/* Fixed and predictable footprint on 32-bit and 64-bit C11 hosts. */
_Static_assert(sizeof(PMKBWBModel) < 32768u, "whiteboard model too large");

static inline PMKBWBStatus pmkb_wb_init(PMKBWBModel *board,int w,int h) {
    if (!board || w<=0 || h<=0 ||
        w>PMKB_WB_MAX_AXIS || h>PMKB_WB_MAX_AXIS)
        return PMKB_WB_INVALID;
    memset(board,0,sizeof(*board));
    board->width=w; board->height=h;
    return PMKB_WB_OK;
}
static inline bool pmkb_wb_in_bounds(const PMKBWBModel *board,int x,int y) {
    return board && x>=0 && y>=0 && x<board->width && y<board->height;
}
static inline PMKBWBStatus pmkb_wb_append(
    PMKBWBStroke *stroke,int x,int y) {
    if (!stroke) return PMKB_WB_INVALID;
    if (stroke->count) {
        PMKBWBPoint previous=stroke->points[stroke->count-1u];
        if (previous.x==(uint16_t)x && previous.y==(uint16_t)y)
            return PMKB_WB_NO_CHANGE;
    }
    if (stroke->count==PMKB_WB_MAX_POINTS_PER_STROKE)
        return PMKB_WB_LIMIT;
    stroke->points[stroke->count++]=(PMKBWBPoint){(uint16_t)x,(uint16_t)y};
    return PMKB_WB_OK;
}
static inline PMKBWBStatus pmkb_wb_down(
    PMKBWBModel *board,int x,int y,unsigned shade,unsigned thickness) {
    if (!pmkb_wb_in_bounds(board,x,y) || board->in_stroke ||
        shade>15u || thickness==0 || thickness>PMKB_WB_MAX_THICKNESS)
        return PMKB_WB_INVALID;
    if (board->visible==PMKB_WB_MAX_STROKES) return PMKB_WB_LIMIT;
    board->working=(PMKBWBStroke){0};
    board->working.shade=(uint8_t)shade;
    board->working.thickness=(uint8_t)thickness;
    (void)pmkb_wb_append(&board->working,x,y);
    board->in_stroke=true;
    return PMKB_WB_OK;
}
static inline PMKBWBStatus pmkb_wb_move(PMKBWBModel *board,int x,int y) {
    if (!pmkb_wb_in_bounds(board,x,y) || !board->in_stroke)
        return PMKB_WB_INVALID;
    return pmkb_wb_append(&board->working,x,y);
}
static inline PMKBWBStatus pmkb_wb_up(PMKBWBModel *board,int x,int y) {
    if (!pmkb_wb_in_bounds(board,x,y) || !board->in_stroke)
        return PMKB_WB_INVALID;
    PMKBWBStatus rc=pmkb_wb_append(&board->working,x,y);
    if (rc==PMKB_WB_LIMIT) return rc; /* still active, can cancel */
    /* Commit atomically: only now does a new stroke discard redo history. */
    board->strokes[board->visible]=board->working;
    ++board->visible;
    board->total=board->visible;
    board->in_stroke=false;
    memset(&board->working,0,sizeof(board->working));
    return PMKB_WB_OK;
}
static inline PMKBWBStatus pmkb_wb_cancel(PMKBWBModel *board) {
    if (!board || !board->in_stroke) return PMKB_WB_INVALID;
    board->in_stroke=false;
    memset(&board->working,0,sizeof(board->working));
    return PMKB_WB_OK;
}
static inline PMKBWBStatus pmkb_wb_undo(PMKBWBModel *board) {
    if (!board || board->in_stroke) return PMKB_WB_INVALID;
    if (!board->visible) return PMKB_WB_NO_CHANGE;
    do {
        --board->visible;
    } while (board->visible>0u &&
             board->strokes[board->visible].continuation);
    return PMKB_WB_OK;
}
static inline PMKBWBStatus pmkb_wb_redo(PMKBWBModel *board) {
    if (!board || board->in_stroke) return PMKB_WB_INVALID;
    if (board->visible==board->total) return PMKB_WB_NO_CHANGE;
    do {
        ++board->visible;
    } while (board->visible<board->total &&
             board->strokes[board->visible].continuation);
    return PMKB_WB_OK;
}
static inline PMKBWBStatus pmkb_wb_clear(PMKBWBModel *board) {
    if (!board || board->in_stroke) return PMKB_WB_INVALID;
    if (!board->total) return PMKB_WB_NO_CHANGE;
    memset(board->strokes,0,sizeof(board->strokes));
    board->total=board->visible=0u;
    return PMKB_WB_OK;
}
static inline size_t pmkb_wb_visible_points(const PMKBWBModel *board) {
    if (!board) return 0u;
    size_t points=0u;
    for (unsigned i=0u;i<board->visible;i++)
        points+=board->strokes[i].count;
    return points;
}
#endif
