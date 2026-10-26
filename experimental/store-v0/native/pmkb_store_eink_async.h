/* D7p: asynchronous Store presentation seam, host-only.
 * Never call pmkb_surface_present: submit is not an acknowledgement. */
#ifndef PMKB_STORE_EINK_ASYNC_H
#define PMKB_STORE_EINK_ASYNC_H
#include "pmkb_store_eink_pending.h"
typedef struct {
    PMKBStoreEinkPending markers;
    PMKBSurface *surface;
    size_t submitted_changes;
} PMKBStoreEinkAsync;
static inline PMKBStatus pmkb_store_eink_async_submit(
    PMKBStoreEinkAsync *state, PMKBSurface *surface, unsigned *marker) {
    if (!state || !surface || !surface->gray || !marker) return PMKB_INVALID;
    if (state->markers.pending) return PMKB_LIMIT;
    if (!surface->has_dirty) return PMKB_NO_CHANGE;
    PMKBStatus status=pmkb_store_eink_begin(&state->markers,marker);
    if (status!=PMKB_OK) return status;
    state->surface=surface;
    state->submitted_changes=surface->changed_pixels;
    return PMKB_OK;
}
/* Cancel BEFORE the caller dismisses or reallocates the surface.
 * A late completion for this marker must not touch freed/reused pixels. */
static inline PMKBStatus pmkb_store_eink_async_cancel(
    PMKBStoreEinkAsync *state) {
    if (!state) return PMKB_INVALID;
    if (!state->markers.pending) return PMKB_NO_CHANGE;
    state->markers.pending=false;
    state->markers.pending_marker=0;
    state->surface=NULL;
    state->submitted_changes=0;
    return PMKB_OK;
}
static inline PMKBStatus pmkb_store_eink_async_complete(
    PMKBStoreEinkAsync *state, PMKBSurface *live_surface,
    unsigned marker, bool success) {
    if (!state || !state->markers.pending ||
        marker!=state->markers.pending_marker) return PMKB_INVALID;
    PMKBStatus result=pmkb_store_eink_complete(&state->markers,marker,success);
    /* No completion or a changed surface means no dirty acknowledgement. */
    if (result==PMKB_OK && live_surface &&
        live_surface==state->surface && live_surface->gray &&
        live_surface->changed_pixels==state->submitted_changes) {
        PMKBRect ignored;
        (void)pmkb_surface_take_dirty(live_surface,&ignored);
    }
    state->surface=NULL;
    return result;
}
#endif
