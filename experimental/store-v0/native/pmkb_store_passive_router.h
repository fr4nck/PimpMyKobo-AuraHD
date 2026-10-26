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
    if (!router || !catalogue) return PMKB_STORE_PAINT_INVALID;
    if (pmkb_store_owner_open(&router->store, &router->host, width, height)
        != PMKB_STORE_PAINT_OK) return PMKB_STORE_PAINT_INVALID;
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
#endif
