/* PMKB Store L06-D5: opt-in screen lifecycle for the passive Store.
 * Header-only C11: no malloc, I/O, framework or permanent service.
 * The host MUST notify external drawing; silent writes cannot be detected. */
#ifndef PMKB_STORE_SCREEN_H
#define PMKB_STORE_SCREEN_H
#include "pmkb_store_paint.h"

typedef struct {
    PMKBStorePaintCache cache;
    bool visible;
} PMKBStoreScreen;

/* Call once before first use. No repaint or framebuffer access. */
static inline void pmkb_store_screen_init(PMKBStoreScreen *screen) {
    if (screen) {
        pmkb_store_paint_cache_reset(&screen->cache);
        screen->visible = false;
    }
}

/* Every entry/re-entry forces one real draw, even if contents are identical. */
static inline void pmkb_store_screen_enter(PMKBStoreScreen *screen) {
    if (screen) {
        pmkb_store_paint_cache_reset(&screen->cache);
        screen->visible = true;
    }
}

/* Leaving Store clears the cache and rejects any further Store painting. */
static inline void pmkb_store_screen_leave(PMKBStoreScreen *screen) {
    if (screen) {
        pmkb_store_paint_cache_reset(&screen->cache);
        screen->visible = false;
    }
}

/* Mandatory host notification AFTER any external writer touches the
 * Store surface: status widgets, navigation, complete redraw, re-init, etc.
 * No automatic detection is claimed: bypassing this contract can be stale.
 * If the host is leaving Store, call leave() instead. */
static inline void pmkb_store_screen_external_draw(PMKBStoreScreen *screen) {
    if (screen) pmkb_store_paint_cache_reset(&screen->cache);
}

/* The only cached paint entrypoint a future Store screen should use.
 * Rejects drawing while hidden, without mutating a page or surface. */
static inline PMKBStorePaintStatus pmkb_store_screen_paint(
    PMKBStoreScreen *screen, const PMKBStoreView *view,
    const PMKBStorePage *page, const PMKBStorePainter *painter) {
    if (!screen || !screen->visible) return PMKB_STORE_PAINT_INVALID;
    return pmkb_store_paint_page_cached(view, page, painter, &screen->cache);
}
#endif
