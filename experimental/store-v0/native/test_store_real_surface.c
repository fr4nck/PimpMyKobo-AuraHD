/* L06-D4b: pinned real PMKB-UI surface linked to the passive Store.
 * No framebuffer present(), touchscreen, filesystem or app launcher. */
#include "pmkb_ui.h"
#include "pmkb_store_paint.h"
#include <stdint.h>
#include <stdio.h>
#include <string.h>
static PMKBStoreView view, previous;
static PMKBStorePage page;
static int failed=0, checks=0;
#define CHECK(x) do{ ++checks; if(!(x)){++failed;fprintf(stderr,"FAIL %d %s\n",__LINE__,#x);}}while(0)
static uint64_t digest(const PMKBSurface *s){
    uint64_t h=UINT64_C(1469598103934665603);
    size_t n=(size_t)s->width*(size_t)s->height;
    for(size_t i=0;i<n;i++){h^=s->gray[i];h*=UINT64_C(1099511628211);}
    return h;
}
static void prepare(unsigned n,unsigned pending){
    memset(&view,0,sizeof(view));view.count=n;view.cleanup_pending_count=pending;
    for(unsigned i=0;i<n;i++){
        (void)snprintf(view.items[i].id,sizeof(view.items[i].id),"org.pmkb.app%02u",i);
        (void)snprintf(view.items[i].label,sizeof(view.items[i].label),"Meteo %02u",i);
        (void)strcpy(view.items[i].version,"0.1.0");
    }
}
static void check_surface(int w,int h,unsigned page_no,unsigned count,
                          unsigned pending,unsigned shown){
    prepare(count,pending);previous=view;
    PMKBSurface surface;PMKBRect dirty;
    CHECK(pmkb_surface_init(&surface,w,h)==PMKB_OK);
    if(!surface.gray)return;
    CHECK(pmkb_surface_take_dirty(&surface,&dirty));
    CHECK(pmkb_store_page_build(&view,w,h,page_no,&page)==PMKB_STORE_PAGE_OK);
    CHECK(page.visible_count==shown);
    PMKBStorePainter painter=pmkb_store_painter_for_ui(&surface);
    CHECK(pmkb_store_paint_page(&view,&page,&painter)==PMKB_STORE_PAINT_OK);
    CHECK(surface.has_dirty && surface.changed_pixels>0);
    CHECK(surface.dirty.x>=0 && surface.dirty.y>=0);
    CHECK(surface.dirty.w>0 && surface.dirty.h>0);
    CHECK(surface.dirty.x+surface.dirty.w<=w && surface.dirty.y+surface.dirty.h<=h);
    size_t black=0,stripes=0,dividers=0;
    for(size_t i=0,n=(size_t)w*(size_t)h;i<n;i++){
        if(surface.gray[i]==0)black++;
        if(surface.gray[i]==240)stripes++;
        if(surface.gray[i]==192)dividers++;
    }
    CHECK(black>0 && dividers>0);
    if(shown>=2)CHECK(stripes>0);
    CHECK(memcmp(&view,&previous,sizeof(view))==0);
    uint64_t image=digest(&surface);
    page.page_index=page.page_count; /* invalid: no partial drawing */
    CHECK(pmkb_store_paint_page(&view,&page,&painter)==PMKB_STORE_PAINT_INVALID);
    CHECK(image==digest(&surface));
    CHECK(pmkb_surface_take_dirty(&surface,&dirty));
    CHECK(!pmkb_surface_take_dirty(&surface,&dirty));
    pmkb_surface_free(&surface);
    CHECK(surface.gray==NULL);
}
int main(void){
    CHECK(pmkb_surface_glyph_supported(0x00e9u));
    check_surface(320,480,0,3,0,3);
    check_surface(1080,1440,0,64,2,12);
    check_surface(1440,1080,7,64,512,1);
    if(failed)return 1;
    printf("PMKB REAL UI STORE: %d assertions PASS, 0 FAIL\n",checks);
    return 0;
}
