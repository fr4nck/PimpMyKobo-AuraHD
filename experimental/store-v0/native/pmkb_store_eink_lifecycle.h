/* D7r: optional host-only lifecycle wrapper for pending simulated refreshes.
 * The original passive router remains unchanged and synchronous. */
#ifndef PMKB_STORE_EINK_LIFECYCLE_H
#define PMKB_STORE_EINK_LIFECYCLE_H
#include "pmkb_store_eink_async.h"
typedef struct {
    PMKBStorePassiveRouter router;
    PMKBStoreEinkAsync async;
} PMKBStoreEinkLifecycle;
static inline void pmkb_store_eink_lifecycle_init(PMKBStoreEinkLifecycle *owner) {
    if (!owner) return;
    pmkb_store_router_init(&owner->router);
    owner->async=(PMKBStoreEinkAsync){0};
}
/* Reset an initialized owner without recycling old marker IDs.
 * Use init only once; this reset preserves the marker sequence. */
static inline void pmkb_store_eink_lifecycle_reset(
    PMKBStoreEinkLifecycle *owner) {
    if (!owner) return;
    (void)pmkb_store_eink_async_cancel(&owner->async);
    pmkb_store_router_dismiss(&owner->router);
    (void)pmkb_app_host_close(&owner->router.host,true);
    pmkb_app_host_init(&owner->router.host);
    pmkb_store_owner_init(&owner->router.store);
}
static inline void pmkb_store_eink_lifecycle_dismiss(PMKBStoreEinkLifecycle *owner) {
    if (!owner) return;
    (void)pmkb_store_eink_async_cancel(&owner->async);
    pmkb_store_router_dismiss(&owner->router);
}
/* App changes must invalidate the pending Store marker BEFORE
 * the underlying router frees the Store surface. An abandoned completion
 * must not affect the newly active application's pixels. */
static inline PMKBStatus pmkb_store_eink_lifecycle_launch_app(
    PMKBStoreEinkLifecycle *owner, PMKBAppId kind, int width, int height) {
    if (!owner) return PMKB_INVALID;
    pmkb_store_eink_lifecycle_dismiss(owner);
    return pmkb_store_router_launch_app(&owner->router,kind,width,height);
}
/* Keep the Launcher contract: non-discarded Notes may refuse to close.
 * The transient Store is still detached, even when Notes is preserved. */
static inline PMKBStatus pmkb_store_eink_lifecycle_close_app(
    PMKBStoreEinkLifecycle *owner, bool discard) {
    if (!owner) return PMKB_INVALID;
    pmkb_store_eink_lifecycle_dismiss(owner);
    return pmkb_store_router_close_app(&owner->router,discard);
}
static inline PMKBStorePaintStatus pmkb_store_eink_lifecycle_preview(
    PMKBStoreEinkLifecycle *owner,int width,int height,
    const PMKBStoreView *view,unsigned page) {
    if (!owner) return PMKB_STORE_PAINT_INVALID;
    /* Even same-sized redraws must cancel outstanding snapshots. */
    (void)pmkb_store_eink_async_cancel(&owner->async);
    return pmkb_store_router_preview(&owner->router,width,height,view,page);
}
/* The Launcher may be called directly, bypassing this wrapper.
 * Fail closed unless this Store surface is still owned and guarded under
 * the exact host identity captured at preview entry. */
static inline bool pmkb_store_eink_lifecycle_surface_valid(
    PMKBStoreEinkLifecycle *owner) {
    if (!owner || !owner->router.store.allocated)
        return false;
    PMKBStorePassiveRouter *router=&owner->router;
    PMKBStoreLauncherGuard *guard=&router->store.guard;
    return router->store.surface.gray != NULL &&
           guard->host == &router->host &&
           guard->preview.screen.visible &&
           guard->preview.target == &router->store.surface &&
           guard->generation_on_enter == router->host.generation &&
           guard->active_on_enter == router->host.active &&
           guard->instance_on_enter == router->host.instance &&
           pmkb_store_launcher_surface_separate(
               &router->host,&router->store.surface);
}
static inline PMKBStatus pmkb_store_eink_lifecycle_submit(
    PMKBStoreEinkLifecycle *owner,unsigned *marker) {
    if (!owner) return PMKB_INVALID;
    if (!pmkb_store_eink_lifecycle_surface_valid(owner)) {
        pmkb_store_eink_lifecycle_dismiss(owner);
        return PMKB_INVALID;
    }
    return pmkb_store_eink_async_submit(
        &owner->async,&owner->router.store.surface,marker);
}
static inline PMKBStatus pmkb_store_eink_lifecycle_complete(
    PMKBStoreEinkLifecycle *owner,unsigned marker,bool success) {
    if (!owner) return PMKB_INVALID;
    if (!pmkb_store_eink_lifecycle_surface_valid(owner)) {
        pmkb_store_eink_lifecycle_dismiss(owner);
        return PMKB_INVALID;
    }
    return pmkb_store_eink_async_complete(
        &owner->async,&owner->router.store.surface,marker,success);
}
static inline PMKBStatus pmkb_store_eink_lifecycle_shutdown(
    PMKBStoreEinkLifecycle *owner,bool discard) {
    if (!owner) return PMKB_INVALID;
    pmkb_store_eink_lifecycle_dismiss(owner);
    return pmkb_store_router_shutdown(&owner->router,discard);
}
#endif
