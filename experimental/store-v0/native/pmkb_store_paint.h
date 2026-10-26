/* PMKB Store L06-D4a: passive paint calls for the existing PMKB-UI surface. */
#ifndef PMKB_STORE_PAINT_H
#define PMKB_STORE_PAINT_H
#include "pmkb_store_page.h"

/* The painter callbacks have the same semantic parameters as PMKB-UI's
 * pmkb_surface_rect and pmkb_surface_text_box. They never present the display. */
typedef struct {
    void *context;
    void (*rect)(void *context, int x, int y, int w, int h, uint8_t shade);
    void (*text_box)(void *context, int x, int y, const char *utf8,
                     uint8_t shade, int max_width, int max_height);
} PMKBStorePainter;

typedef enum {
    PMKB_STORE_PAINT_OK = 0,
    PMKB_STORE_PAINT_INVALID = -1
} PMKBStorePaintStatus;

/* Validate the entire page against the original view BEFORE any callback.
 * Does not perform input handling, launch, persistence, refresh or network. */
PMKBStorePaintStatus pmkb_store_paint_page(const PMKBStoreView *view,
                                           const PMKBStorePage *page,
                                           const PMKBStorePainter *painter);


/* Optional caller-owned, ~40-byte hint for an unchanged on-screen Store page.
 * The caller MUST reset it when any other drawing changes the target surface,
 * including UI navigation, full refresh, surface re-init and framebuffer
 * repaint. A 64-bit content stamp is NOT an authentication/integrity proof.
 * The uncached function above stays the default and retains its semantics. */
typedef struct {
    uint64_t stamp;
    void *context;
    void (*rect)(void *context, int x, int y, int w, int h, uint8_t shade);
    void (*text_box)(void *context, int x, int y, const char *utf8,
                     uint8_t shade, int max_width, int max_height);
    bool valid;
} PMKBStorePaintCache;

void pmkb_store_paint_cache_reset(PMKBStorePaintCache *cache);
PMKBStorePaintStatus pmkb_store_paint_page_cached(
    const PMKBStoreView *view, const PMKBStorePage *page,
    const PMKBStorePainter *painter, PMKBStorePaintCache *cache);

/* Optional compile-time seam. Include pmkb_ui.h from PR #30 BEFORE this
 * header when both branches are integrated; no clone or UI vendoring here.
 * C11 wrappers prevent function-pointer casts between PMKBSurface* and void*. */
#ifdef PMKB_UI_H
static inline void pmkb_store_ui_fill(void *ctx, int x, int y, int w, int h,
                                      uint8_t shade) {
    pmkb_surface_rect((PMKBSurface *)ctx, (PMKBRect){x,y,w,h}, shade);
}
static inline void pmkb_store_ui_text(void *ctx, int x, int y,
                                      const char *utf8, uint8_t shade,
                                      int max_width, int max_height) {
    pmkb_surface_text_box((PMKBSurface *)ctx, x, y, utf8, shade,
                          max_width, max_height);
}
static inline PMKBStorePainter pmkb_store_painter_for_ui(PMKBSurface *surface) {
    return (PMKBStorePainter){surface, pmkb_store_ui_fill, pmkb_store_ui_text};
}
#endif
#endif
