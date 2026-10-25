#include "pmkb_ui.h"
/* Pure callback adapter. No framebuffer, evdev, MXCFB, network or file I/O. */
PMKBStatus pmkb_surface_present(PMKBSurface *s,const PMKBBackend *backend){
    if(!s||!s->gray||!backend||!backend->present)return PMKB_INVALID;
    if(!s->has_dirty)return PMKB_NO_CHANGE;
    PMKBRect before=s->dirty;
    /* A synchronous callback may edit pixels during presentation. */
    size_t changes_before=s->changed_pixels;
    PMKBStatus result=backend->present(backend->context,s->gray,
                                       s->width,s->height,before);
    if(result==PMKB_OK && s->changed_pixels==changes_before) {
        PMKBRect ignored;
        (void)pmkb_surface_take_dirty(s,&ignored);
    }
    /* Failed callbacks must keep the dirty rectangle for a safe retry. */
    return result;
}
