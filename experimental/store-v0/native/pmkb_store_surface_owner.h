/* L06-D6n: synthetic owner of one passive Store gray surface.
 * The host is borrowed; no Store app route, process or background service. */
#ifndef PMKB_STORE_SURFACE_OWNER_H
#define PMKB_STORE_SURFACE_OWNER_H
#include "pmkb_store_launcher_guard.h"

typedef struct {
    PMKBSurface surface;
    PMKBStoreLauncherGuard guard;
    bool allocated;
} PMKBStoreSurfaceOwner;

/* Initialize once before use. Do not copy an initialized owner. */
static inline void pmkb_store_owner_init(PMKBStoreSurfaceOwner *owner) {
    if (!owner) return;
    owner->surface = (PMKBSurface){0};
    owner->allocated = false;
    pmkb_store_launcher_guard_init(&owner->guard);
}
static inline void pmkb_store_owner_close(PMKBStoreSurfaceOwner *owner) {
    if (!owner) return;
    pmkb_store_launcher_guard_before_destroy(&owner->guard);
    if (owner->allocated) pmkb_surface_free(&owner->surface);
    owner->allocated = false;
}
static inline PMKBStorePaintStatus pmkb_store_owner_open(
    PMKBStoreSurfaceOwner *owner, PMKBAppHost *host, int width, int height) {
    if (!owner || !host) return PMKB_STORE_PAINT_INVALID;
    pmkb_store_owner_close(owner);
    /* Only preview-tested sizes. Never allocate before validating. */
    if (!((width == 320 && height == 480) ||
          (width == 1080 && height == 1440) ||
          (width == 1440 && height == 1080)))
        return PMKB_STORE_PAINT_INVALID;
    if (pmkb_surface_init(&owner->surface, width, height) != PMKB_OK)
        return PMKB_STORE_PAINT_INVALID;
    owner->allocated = true;
    if (pmkb_store_launcher_guard_enter(&owner->guard, host,
                                        &owner->surface) != PMKB_STORE_PAINT_OK) {
        pmkb_store_owner_close(owner);
        return PMKB_STORE_PAINT_INVALID;
    }
    return PMKB_STORE_PAINT_OK;
}
static inline size_t pmkb_store_owner_pixel_bytes(
    const PMKBStoreSurfaceOwner *owner) {
    return owner && owner->allocated ?
        (size_t)owner->surface.width * (size_t)owner->surface.height : 0u;
}
#endif
