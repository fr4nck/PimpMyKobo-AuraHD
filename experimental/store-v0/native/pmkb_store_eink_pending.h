/* D7o: host-only model of a single pending E-Ink refresh marker.
 * Acceptance is NOT completion and NEVER clears PMKBSurface dirty. */
#ifndef PMKB_STORE_EINK_PENDING_H
#define PMKB_STORE_EINK_PENDING_H
#include "pmkb_store_eink_sim.h"
typedef struct {
    unsigned next_marker;
    unsigned pending_marker;
    bool pending;
    unsigned completions;
    unsigned failures;
} PMKBStoreEinkPending;
static inline PMKBStatus pmkb_store_eink_begin(
    PMKBStoreEinkPending *state, unsigned *marker) {
    if (!state || !marker) return PMKB_INVALID;
    if (state->pending) return PMKB_LIMIT;
    if (state->next_marker == (unsigned)-1) return PMKB_LIMIT;
    unsigned next=++state->next_marker;
    state->pending_marker=next;
    state->pending=true;
    *marker=next;
    return PMKB_OK;
}
static inline PMKBStatus pmkb_store_eink_complete(
    PMKBStoreEinkPending *state, unsigned marker, bool success) {
    if (!state || !state->pending || !marker ||
        marker!=state->pending_marker) return PMKB_INVALID;
    state->pending=false;
    state->pending_marker=0;
    if (success) { ++state->completions; return PMKB_OK; }
    ++state->failures;
    return PMKB_INVALID;
}
#endif
