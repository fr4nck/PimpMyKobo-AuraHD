/* L06-D6s: passive route prototype. No Store app launch/registration.
 * Owns a host and Store pixels. Explicitly initialized and never copied. */
#ifndef PMKB_STORE_PASSIVE_ROUTER_H
#define PMKB_STORE_PASSIVE_ROUTER_H
#include "pmkb_store_surface_owner.h"

typedef struct {
    PMKBAppHost host;
    PMKBStoreSurfaceOwner store;
} PMKBStorePassiveRouter;

static inline void pmkb_store_router_init(PMKBStorePassiveRouter *router) {
    if (!router) return;
    pmkb_app_host_init(&router->host);
    pmkb_store_owner_init(&router->store);
}
static inline PMKBStorePaintStatus pmkb_store_router_preview(
    PMKBStorePassiveRouter *router, int width, int height,
    const PMKBStoreView *catalogue, unsigned page) {
    if (!router) return PMKB_STORE_PAINT_INVALID;
    if (!catalogue) {
        pmkb_store_owner_close(&router->store);
        return PMKB_STORE_PAINT_INVALID;
    }
    /* Reuse an existing owned buffer of identical dimensions. Re-enter
     * the guard to validate the current app identity and memory ranges. */
    PMKBStorePaintStatus opened;
    if (router->store.allocated &&
        router->store.surface.width == width &&
        router->store.surface.height == height) {
        opened = pmkb_store_launcher_guard_enter(
            &router->store.guard, &router->host, &router->store.surface);
        if (opened != PMKB_STORE_PAINT_OK)
            pmkb_store_owner_close(&router->store);
    } else {
        opened = pmkb_store_owner_open(&router->store, &router->host,
                                       width, height);
    }
    if (opened != PMKB_STORE_PAINT_OK) return PMKB_STORE_PAINT_INVALID;
    PMKBStorePaintStatus status =
        pmkb_store_launcher_guard_draw(&router->store.guard, catalogue, page);
    if (status != PMKB_STORE_PAINT_OK) pmkb_store_owner_close(&router->store);
    return status;
}
/* Store is transient: no pixels remain when it is dismissed. */
static inline void pmkb_store_router_dismiss(PMKBStorePassiveRouter *router) {
    if (router) pmkb_store_owner_close(&router->store);
}
/* Close Store BEFORE touching the host lifecycle. Do not override the
 * unsaved Notes protection: forward the actual return status. */
static inline PMKBStatus pmkb_store_router_close_app(
    PMKBStorePassiveRouter *router, bool discard) {
    if (!router) return PMKB_INVALID;
    pmkb_store_router_dismiss(router);
    return pmkb_app_host_close(&router->host, discard);
}
static inline PMKBStatus pmkb_store_router_launch_app(
    PMKBStorePassiveRouter *router, PMKBAppId kind, int width, int height) {
    if (!router) return PMKB_INVALID;
    pmkb_store_router_dismiss(router);
    return pmkb_app_host_launch(&router->host, kind, width, height);
}
/* Shutdown is explicit, not a destructor: refusal preserves Notes.
 * The Store surface is always detached before touching app lifetime. */
static inline PMKBStatus pmkb_store_router_shutdown(
    PMKBStorePassiveRouter *router, bool discard) {
    if (!router) return PMKB_INVALID;
    pmkb_store_router_dismiss(router);
    return pmkb_app_host_close(&router->host, discard);
}
#endif
