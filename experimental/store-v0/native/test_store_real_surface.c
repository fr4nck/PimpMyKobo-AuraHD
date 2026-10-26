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
/* L06-D4c: check the actual pixels, not just the painter's call count.
 * All checks use the pinned PR #30 surface compiled by CI (D4b). */
static uint8_t pixel(const PMKBSurface *s, int x, int y) {
    return s->gray[(size_t)y * (size_t)s->width + (size_t)x];
}
static void check_real_pixels(int w, int h, unsigned page_no,
                              unsigned count, unsigned pending) {
    prepare(count, pending);
    previous = view;
    PMKBSurface first, second;
    PMKBRect dirty;
    CHECK(pmkb_surface_init(&first, w, h) == PMKB_OK);
    if (!first.gray) return;
    CHECK(pmkb_surface_take_dirty(&first, &dirty));
    CHECK(pmkb_store_page_build(&view, w, h, page_no, &page)
          == PMKB_STORE_PAGE_OK);
    PMKBStorePainter painter = pmkb_store_painter_for_ui(&first);
    CHECK(pmkb_store_paint_page(&view, &page, &painter)
          == PMKB_STORE_PAINT_OK);

    /* The area outside the page furniture remains white. */
    CHECK(pixel(&first, 0, 0) == 255);
    CHECK(pixel(&first, 0, h - 1) == 255);
    CHECK(pixel(&first, 0, page.header.h - 1) == 192);
    CHECK(pixel(&first, 0, page.footer.y) == 192);
    unsigned invalid_shades = 0, dark_in_body = 0;
    const size_t size = (size_t)w * (size_t)h;
    for (size_t i = 0; i < size; ++i) {
        uint8_t v = first.gray[i];
        if (v != 0 && v != 192 && v != 240 && v != 255)
            ++invalid_shades;
    }
    for (int y = page.body.y; y < page.body.y + page.body.h; ++y) {
        for (int x = page.body.x; x < page.body.x + page.body.w; ++x)
            if (pixel(&first, x, y) == 0) ++dark_in_body;
    }
    CHECK(invalid_shades == 0);
    if (count) CHECK(dark_in_body > 0);
    else CHECK(dark_in_body == 0);
    for (unsigned i = 0; i < page.visible_count; ++i) {
        PMKBStorePageRow row = page.rows[i];
        /* Text starts at x+16: left margin samples MUST keep row shade. */
        CHECK(pixel(&first, row.bounds.x + 1, row.bounds.y + 1)
              == row.shade);
        CHECK(pixel(&first, row.bounds.x + 1,
                    row.bounds.y + row.bounds.h - 1) == row.shade);
        if (i + 1 < page.visible_count) {
            CHECK(pixel(&first, row.bounds.x + 1,
                        row.bounds.y + row.bounds.h + 1) == 255);
        }
    }
    /* Two independent fresh surfaces must produce exactly the same pixels. */
    CHECK(pmkb_surface_init(&second, w, h) == PMKB_OK);
    if (second.gray) {
        CHECK(pmkb_surface_take_dirty(&second, &dirty));
        PMKBStorePainter second_painter = pmkb_store_painter_for_ui(&second);
        CHECK(pmkb_store_paint_page(&view, &page, &second_painter)
              == PMKB_STORE_PAINT_OK);
        CHECK(memcmp(first.gray, second.gray, size) == 0);
        CHECK(digest(&first) == digest(&second));
        pmkb_surface_free(&second);
    }
    CHECK(memcmp(&view, &previous, sizeof(view)) == 0);

    /* Page tampering must not dirty or modify the already drawn frame. */
    CHECK(pmkb_surface_take_dirty(&first, &dirty));
    uint64_t image = digest(&first);
    if (page.visible_count) page.rows[0].title.x++;
    else page.header.h++;
    CHECK(pmkb_store_paint_page(&view, &page, &painter)
          == PMKB_STORE_PAINT_INVALID);
    CHECK(digest(&first) == image);
    CHECK(!first.has_dirty && first.changed_pixels == 0);
    pmkb_surface_free(&first);
}
/* Check that a real accented French glyph is not silently rendered
 * exactly like the plain ASCII fallback. */
static void check_french_glyph_pixels(void) {
    prepare(1, 0);
    PMKBSurface surface;
    PMKBRect dirty;
    CHECK(pmkb_surface_init(&surface, 320, 480) == PMKB_OK);
    if (!surface.gray) return;
    CHECK(pmkb_surface_take_dirty(&surface, &dirty));
    CHECK(pmkb_store_page_build(&view, 320, 480, 0, &page)
          == PMKB_STORE_PAGE_OK);
    PMKBStorePainter painter = pmkb_store_painter_for_ui(&surface);
    (void)strcpy(view.items[0].label, "Meteo");
    CHECK(pmkb_store_paint_page(&view, &page, &painter)
          == PMKB_STORE_PAINT_OK);
    uint64_t unaccented = digest(&surface);
    (void)strcpy(view.items[0].label, "M\xC3\xA9" "t\xC3\xA9" "o");
    CHECK(pmkb_store_paint_page(&view, &page, &painter)
          == PMKB_STORE_PAINT_OK);
    CHECK(digest(&surface) != unaccented);
    pmkb_surface_free(&surface);
}
int main(void){
    CHECK(pmkb_surface_glyph_supported(0x00e9u));
    check_surface(320,480,0,3,0,3);
    check_surface(1080,1440,0,64,2,12);
    check_surface(1440,1080,7,64,512,1);
    check_real_pixels(320,480,0,0,0);
    check_real_pixels(320,480,0,3,0);
    check_real_pixels(1080,1440,0,64,2);
    check_real_pixels(1440,1080,7,64,512);
    check_french_glyph_pixels();
    if(failed)return 1;
    printf("PMKB REAL UI STORE: %d assertions PASS, 0 FAIL\n",checks);
    return 0;
}
