#include "pmkb_ui.h"
/* Pure callback adapter. No framebuffer, evdev, MXCFB, network or file I/O. */
PMKBStatus pmkb_surface_present(PMKBSurface *s,const PMKBBackend *backend){
    if(!s||!s->gray||!backend||!backend->present)return PMKB_INVALID;
    if(!s->has_dirty)return PMKB_NO_CHANGE;
    PMKBRect before=s->dirty;
    PMKBStatus result=backend->present(backend->context,s->gray,
                                       s->width,s->height,before);
    if(result==PMKB_OK) {
        PMKBRect ignored;
        (void)pmkb_surface_take_dirty(s,&ignored);
    }
    /* Failed callbacks must keep the dirty rectangle for a safe retry. */
    return result;
}
