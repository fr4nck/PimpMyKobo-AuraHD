#include "pmkb_ui.h"
/* Pure callback adapter. No framebuffer, evdev, MXCFB, network or file I/O. */
static size_t rect_area(PMKBRect r){
    return (size_t)r.w*(size_t)r.h;
}
PMKBStatus pmkb_surface_present(PMKBSurface *s,const PMKBBackend *backend){
    if(!s||!s->gray||!backend||!backend->present)return PMKB_INVALID;
    if(!s->has_dirty)return PMKB_NO_CHANGE;
    PMKBRect rectangles[2]={s->dirty,s->dirty};
    unsigned count=1;
    if(s->dirty_island_count==2){
        size_t full=rect_area(s->dirty);
        size_t split=rect_area(s->dirty_islands[0])+
                     rect_area(s->dirty_islands[1]);
        /* A second callback is worthwhile only for massive overdraw.
         * This is a host heuristic, NOT measured panel refresh timing. */
        if(full>split&&full-split>4096u&&full>split*8u){
            rectangles[0]=s->dirty_islands[0];
            rectangles[1]=s->dirty_islands[1];
            count=2;
        }
    }
    size_t changes_before=s->changed_pixels;
    for(unsigned i=0;i<count;i++){
        PMKBStatus result=backend->present(backend->context,s->gray,
                                           s->width,s->height,rectangles[i]);
        if(result!=PMKB_OK)return result;
        if(s->changed_pixels!=changes_before){
            /* A reentrant edit invalidates the split snapshot. Retry the
             * conservative public union, as before this optimization. */
            s->dirty_islands[0]=s->dirty;
            s->dirty_island_count=1;
            return PMKB_OK;
        }
    }
    PMKBRect ignored;
    (void)pmkb_surface_take_dirty(s,&ignored);
    return PMKB_OK;
}
