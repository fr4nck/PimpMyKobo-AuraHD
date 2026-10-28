/* L07-D7n: host-only E-Ink transport seam. No ioctl, file or device access. */
#ifndef PMKB_STORE_EINK_SIM_H
#define PMKB_STORE_EINK_SIM_H
#include "pmkb_store_passive_router.h"
typedef PMKBStatus (*PMKBStoreEinkSubmit)(void *context, const uint8_t *gray,
                                         int width, int height, PMKBRect dirty);
typedef struct {
    void *context;
    PMKBStoreEinkSubmit submit;
    unsigned submissions;
    unsigned acknowledgements;
} PMKBStoreEinkSim;
static inline PMKBStatus pmkb_store_eink_sim_present(
    void *context, const uint8_t *gray, int width, int height, PMKBRect dirty) {
    PMKBStoreEinkSim *sim=(PMKBStoreEinkSim *)context;
    if (!sim || !sim->submit || !gray || width<=0 || height<=0 ||
        dirty.w<=0 || dirty.h<=0 || dirty.x<0 || dirty.y<0 ||
        dirty.x>width-dirty.w || dirty.y>height-dirty.h)
        return PMKB_INVALID;
    ++sim->submissions;
    PMKBStatus status=sim->submit(sim->context,gray,width,height,dirty);
    if (status==PMKB_OK) ++sim->acknowledgements;
    return status;
}
static inline PMKBBackend pmkb_store_eink_sim_backend(PMKBStoreEinkSim *sim) {
    PMKBBackend backend={sim,pmkb_store_eink_sim_present};
    return backend;
}
#endif
