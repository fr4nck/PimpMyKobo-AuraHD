/* L06-D6d: fail-closed Store/Launcher borrowed-surface seam.
 * Include the REAL pmkb_launcher_bridge.h (PR #30) and the passive
 * Store preview (PR #31). Does NOT activate PMKB_APP_STORE. */
#ifndef PMKB_STORE_LAUNCHER_GUARD_H
#define PMKB_STORE_LAUNCHER_GUARD_H
#include "pmkb_launcher_bridge.h"
#include "pmkb_store_ui_preview.h"

/* No owned framebuffer or allocation: Store must supply an independently
 * allocated surface. The host and that surface MUST outlive this guard. */
typedef struct {
    PMKBStoreUIPreview preview;
    PMKBAppHost *host;          /* borrowed; never owns an app */
    PMKBAppId active_on_enter;
    void *instance_on_enter;    /* compared only; never dereferenced */
} PMKBStoreLauncherGuard;

/* Reject the ACTIVE app surface AND a struct copy sharing its gray buffer.
 * Does not establish ownership of arbitrary aliased/overlapping memory:
 * a future host must actually allocate/own the Store buffer separately. */
static inline bool pmkb_store_launcher_surface_separate(
    PMKBAppHost *host, PMKBSurface *candidate) {
    if (!host || !candidate || !candidate->gray) return false;
    if (host->active == PMKB_APP_NONE) return host->instance == NULL;
    if ((host->active != PMKB_APP_NOTES &&
         host->active != PMKB_APP_CALCULATOR) || !host->instance)
        return false;
    PMKBSurface *app = pmkb_app_host_screen(host);
    return app && app->gray && app != candidate &&
           app->gray != candidate->gray;
}
static inline void pmkb_store_launcher_guard_init(PMKBStoreLauncherGuard *g) {
    if (!g) return;
    pmkb_store_ui_preview_init(&g->preview);
    g->host = NULL;
    g->active_on_enter = PMKB_APP_NONE;
    g->instance_on_enter = NULL;
}
static inline void pmkb_store_launcher_guard_leave(PMKBStoreLauncherGuard *g) {
    if (!g) return;
    pmkb_store_ui_preview_leave(&g->preview);
    g->host = NULL;
    g->active_on_enter = PMKB_APP_NONE;
    g->instance_on_enter = NULL;
}
/* A rejection detaches the old surface too: no stale preview survives. */
static inline PMKBStorePaintStatus pmkb_store_launcher_guard_enter(
    PMKBStoreLauncherGuard *g, PMKBAppHost *host, PMKBSurface *dedicated) {
    if (!g) return PMKB_STORE_PAINT_INVALID;
    pmkb_store_launcher_guard_leave(g);
    if (!pmkb_store_launcher_surface_separate(host, dedicated))
        return PMKB_STORE_PAINT_INVALID;
    if (pmkb_store_ui_preview_enter(&g->preview, dedicated)
        != PMKB_STORE_PAINT_OK) return PMKB_STORE_PAINT_INVALID;
    g->host = host;
    g->active_on_enter = host->active;
    g->instance_on_enter = host->instance;
    return PMKB_STORE_PAINT_OK;
}
/* Recheck on EVERY drawing attempt, including a cache hit. A host launch,
 * close, surface alias or unexpected host state clears the preview, without
 * drawing even one pixel. Re-enter explicitly after host transitions. */
static inline PMKBStorePaintStatus pmkb_store_launcher_guard_draw(
    PMKBStoreLauncherGuard *g, const PMKBStoreView *catalogue,
    unsigned page_index) {
    if (!g || !g->host || !g->preview.screen.visible)
        return PMKB_STORE_PAINT_INVALID;
    if (g->active_on_enter != g->host->active ||
        g->instance_on_enter != g->host->instance ||
        !pmkb_store_launcher_surface_separate(g->host, g->preview.target)) {
        pmkb_store_launcher_guard_leave(g);
        return PMKB_STORE_PAINT_INVALID;
    }
    return pmkb_store_ui_preview_draw(&g->preview, catalogue, page_index);
}
/* Owner must call this BEFORE destroying either borrowed object.
 * After detaching, no host or target pointer is dereferenced.  It is safe
 * to call repeatedly, including when no Store preview is active. */
static inline void pmkb_store_launcher_guard_before_destroy(
    PMKBStoreLauncherGuard *g) {
    pmkb_store_launcher_guard_leave(g);
}
/* Mandatory after another writer draws onto the borrowed Store buffer. */
static inline void pmkb_store_launcher_guard_external_draw(
    PMKBStoreLauncherGuard *g) {
    if (g) pmkb_store_ui_preview_external_draw(&g->preview);
}
#endif
