/* PMKB Store L06-D3: passive grayscale page geometry, no renderer or I/O. */
#ifndef PMKB_STORE_PAGE_H
#define PMKB_STORE_PAGE_H
#include "pmkb_store_view.h"
#include <stdint.h>

#define PMKB_STORE_PAGE_MAX_ROWS 12u
#define PMKB_STORE_PAGE_INK 0u
#define PMKB_STORE_PAGE_WHITE 255u
#define PMKB_STORE_PAGE_ALTERNATE 240u
#define PMKB_STORE_PAGE_DIVIDER 192u

typedef enum {
    PMKB_STORE_PAGE_OK = 0,
    PMKB_STORE_PAGE_INVALID = -1,
    PMKB_STORE_PAGE_GEOMETRY = -2,
    PMKB_STORE_PAGE_OUT_OF_RANGE = -3
} PMKBStorePageStatus;

typedef struct { int x, y, w, h; } PMKBStorePageRect;

typedef struct {
    unsigned source_index;  /* index into the read-only PMKBStoreView */
    PMKBStorePageRect bounds;
    PMKBStorePageRect title;
    PMKBStorePageRect version;
    uint8_t shade;         /* white or very light gray; no touch action */
} PMKBStorePageRow;

typedef struct {
    int width, height;
    PMKBStorePageRect header, body, footer;
    unsigned page_index, page_count, total_items;
    unsigned cleanup_pending_count, visible_count;
    uint8_t ink, background, divider;
    PMKBStorePageRow rows[PMKB_STORE_PAGE_MAX_ROWS];
} PMKBStorePage;

/* Supported logical host geometries: 320x480, 1080x1440, 1440x1080.
 * No framebuffer, fonts, allocation, input or application launching.
 * Row indices refer to the supplied view, which must outlive the page.
 * On any error the output is reset to all-zero bytes. */
PMKBStorePageStatus pmkb_store_page_build(const PMKBStoreView *view,
                                          int width, int height,
                                          unsigned page_index,
                                          PMKBStorePage *out);
#endif
