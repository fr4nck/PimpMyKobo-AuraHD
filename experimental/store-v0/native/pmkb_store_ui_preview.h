/* PMKB L06-D6a: passive preview adapter to an existing PMKB-UI surface.
 * Requires the TRUE pmkb_ui.h before inclusion. Does not own the surface,
 * launch applications, present to EPDC, read files or access the network.
 * This header is compiled only in the cross-PR native surface test. */
#ifndef PMKB_STORE_UI_PREVIEW_H
#define PMKB_STORE_UI_PREVIEW_H
#ifndef PMKB_UI_H
#error "include pmkb_ui.h before pmkb_store_ui_preview.h"
#endif
#include "pmkb_store_screen.h"

typedef struct {
    PMKBStoreScreen screen;
    PMKBSurface *target; /* borrowed: owner retains and manages dirty regions */
} PMKBStoreUIPreview;

static inline void pmkb_store_ui_preview_init(PMKBStoreUIPreview *preview) {
    if (!preview) return;
    pmkb_store_screen_init(&preview->screen);
    preview->target = NULL;
}

/* Attach only one of the already-supported logical host sizes.
 * Every entry, including re-entry to the SAME surface, flushes the cache. */
static inline PMKBStorePaintStatus pmkb_store_ui_preview_enter(
    PMKBStoreUIPreview *preview, PMKBSurface *surface) {
    if (!preview) return PMKB_STORE_PAINT_INVALID;
    if (!surface || !surface->gray ||
        !((surface->width == 320 && surface->height == 480) ||
          (surface->width == 1080 && surface->height == 1440) ||
          (surface->width == 1440 && surface->height == 1080))) {
        pmkb_store_screen_leave(&preview->screen);
        preview->target = NULL;
        return PMKB_STORE_PAINT_INVALID;
    }
    preview->target = surface;
    pmkb_store_screen_enter(&preview->screen);
    return PMKB_STORE_PAINT_OK;
}

/* Hosts must call after ANY other writer touches the borrowed surface.
 * No automatic detection of out-of-band writes is claimed. */
static inline void pmkb_store_ui_preview_external_draw(
    PMKBStoreUIPreview *preview) {
    if (preview) pmkb_store_screen_external_draw(&preview->screen);
}

static inline void pmkb_store_ui_preview_leave(PMKBStoreUIPreview *preview) {
    if (!preview) return;
    pmkb_store_screen_leave(&preview->screen);
    preview->target = NULL;
}

/* No presentation, installation, touch handlers, launch or state persistence.
 * Build/validate first; failures cannot call a drawing primitive. */
static inline PMKBStorePaintStatus pmkb_store_ui_preview_draw(
    PMKBStoreUIPreview *preview, const PMKBStoreView *catalogue,
    unsigned page_index) {
    if (!preview || !preview->screen.visible || !preview->target ||
        !preview->target->gray || !catalogue)
        return PMKB_STORE_PAINT_INVALID;
    PMKBStorePage page;
    if (pmkb_store_page_build(catalogue, preview->target->width,
                              preview->target->height, page_index, &page)
        != PMKB_STORE_PAGE_OK)
        return PMKB_STORE_PAINT_INVALID;
    PMKBStorePainter painter = pmkb_store_painter_for_ui(preview->target);
    return pmkb_store_screen_paint(&preview->screen, catalogue, &page, &painter);
}
#endif
