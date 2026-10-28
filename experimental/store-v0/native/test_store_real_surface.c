/* L06-D4b: pinned real PMKB-UI surface linked to the passive Store.
 * No framebuffer present(), touchscreen, filesystem or app launcher. */
#include "pmkb_ui.h"
#include "pmkb_store_paint.h"
#include "pmkb_store_screen.h"
#include "pmkb_store_ui_preview.h"
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <time.h>
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

/* L06-D4d: compare legacy unconditional redraw with optional cached redraw
 * on the REAL PMKB-UI pixel surface. No physical E-Ink refresh is performed. */
static void check_duplicate_draw(int w, int h, unsigned count, unsigned pending) {
    prepare(count, pending);
    PMKBSurface surface;
    PMKBRect dirty;
    CHECK(pmkb_surface_init(&surface, w, h) == PMKB_OK);
    if (!surface.gray) return;
    CHECK(pmkb_surface_take_dirty(&surface, &dirty));
    CHECK(pmkb_store_page_build(&view, w, h, 0, &page)
          == PMKB_STORE_PAGE_OK);
    PMKBStorePainter painter = pmkb_store_painter_for_ui(&surface);

    /* Baseline: unchanged data repaints visible glyphs twice. */
    CHECK(pmkb_store_paint_page(&view, &page, &painter)
          == PMKB_STORE_PAINT_OK);
    CHECK(pmkb_surface_take_dirty(&surface, &dirty));
    CHECK(pmkb_store_paint_page(&view, &page, &painter)
          == PMKB_STORE_PAINT_OK);
    const size_t baseline = surface.changed_pixels;
    CHECK(baseline > 0);
    CHECK(surface.has_dirty);
    CHECK(pmkb_surface_take_dirty(&surface, &dirty));

    PMKBStorePaintCache cache = {0};
    CHECK(pmkb_store_paint_page_cached(&view, &page, &painter, &cache)
          == PMKB_STORE_PAINT_OK);
    CHECK(cache.valid);
    CHECK(pmkb_surface_take_dirty(&surface, &dirty));
    const uint64_t unchanged = digest(&surface);
    CHECK(pmkb_store_paint_page_cached(&view, &page, &painter, &cache)
          == PMKB_STORE_PAINT_OK);
    const size_t cached = surface.changed_pixels;
    CHECK(cached == 0 && !surface.has_dirty);
    CHECK(digest(&surface) == unchanged);

    /* An updated label requires a repaint even on the same context. */
    if (count) {
        (void)strcpy(view.items[0].label, "Autre application");
        CHECK(pmkb_store_paint_page_cached(&view, &page, &painter, &cache)
              == PMKB_STORE_PAINT_OK);
        CHECK(surface.changed_pixels > 0 && surface.has_dirty);
        CHECK(pmkb_surface_take_dirty(&surface, &dirty));
    }

    /* Visible footer counts also invalidate the cache correctly. */
    view.cleanup_pending_count = pending ? 0u : 1u;
    CHECK(pmkb_store_page_build(&view, w, h, 0, &page)
          == PMKB_STORE_PAGE_OK);
    CHECK(pmkb_store_paint_page_cached(&view, &page, &painter, &cache)
          == PMKB_STORE_PAINT_OK);
    CHECK(surface.changed_pixels > 0 && surface.has_dirty);
    CHECK(pmkb_surface_take_dirty(&surface, &dirty));

    /* Repainting another screen MUST be followed by explicit reset. */
    pmkb_surface_rect(&surface, (PMKBRect){0, 0, 4, 4}, 0);
    CHECK(surface.changed_pixels > 0);
    CHECK(pmkb_surface_take_dirty(&surface, &dirty));
    pmkb_store_paint_cache_reset(&cache);
    CHECK(!cache.valid);
    CHECK(pmkb_store_paint_page_cached(&view, &page, &painter, &cache)
          == PMKB_STORE_PAINT_OK);
    CHECK(surface.gray[0] == 255);
    CHECK(surface.has_dirty && surface.changed_pixels > 0);
    CHECK(pmkb_surface_take_dirty(&surface, &dirty));

    /* A forged page must never draw, including with a valid cache. */
    uint64_t image = digest(&surface);
    page.page_index = page.page_count;
    CHECK(pmkb_store_paint_page_cached(&view, &page, &painter, &cache)
          == PMKB_STORE_PAINT_INVALID);
    CHECK(!surface.has_dirty && surface.changed_pixels == 0);
    CHECK(image == digest(&surface));
    pmkb_surface_free(&surface);
    printf("PMKB STORE REDRAW %dx%d: baseline=%zu changed_pixels, "
           "cached=%zu changed_pixels\\n", w, h, baseline, cached);
}

/* L06-D4e: explicit ownership rules for invalidation. The optional cache
 * cannot observe unrelated writes to PMKBSurface. This test demonstrates
 * that limitation, and that a deliberate reset restores the correct frame.
 * It does not validate any Kobo E-Ink/EPDC behavior. */
static void check_cache_lifecycle(void) {
    prepare(12, 0); /* 3 pages on the 320x480 host geometry */
    PMKBSurface first, other;
    PMKBRect dirty;
    CHECK(pmkb_surface_init(&first, 320, 480) == PMKB_OK);
    if (!first.gray) return;
    CHECK(pmkb_surface_take_dirty(&first, &dirty));
    CHECK(pmkb_store_page_build(&view, 320, 480, 0, &page)
          == PMKB_STORE_PAGE_OK);
    PMKBStorePainter painter = pmkb_store_painter_for_ui(&first);
    PMKBStorePaintCache cache = {0};
    CHECK(pmkb_store_paint_page_cached(&view, &page, &painter, &cache)
          == PMKB_STORE_PAINT_OK);
    CHECK(cache.valid);
    CHECK(pmkb_surface_take_dirty(&first, &dirty));
    const uint64_t original = digest(&first);
    CHECK(first.gray[0] == 255);

    /* Another view dirties exactly the same surface. Cache is unaware. */
    pmkb_surface_rect(&first, (PMKBRect){0, 0, 4, 4}, 0);
    CHECK(first.gray[0] == 0 && first.has_dirty);
    CHECK(pmkb_surface_take_dirty(&first, &dirty));
    CHECK(pmkb_store_paint_page_cached(&view, &page, &painter, &cache)
          == PMKB_STORE_PAINT_OK);
    CHECK(first.gray[0] == 0); /* stale WITHOUT explicit reset: known limit */
    CHECK(!first.has_dirty && first.changed_pixels == 0);

    /* Caller-owned reset restores pixels and generates a dirty rectangle. */
    pmkb_store_paint_cache_reset(&cache);
    CHECK(!cache.valid);
    CHECK(pmkb_store_paint_page_cached(&view, &page, &painter, &cache)
          == PMKB_STORE_PAINT_OK);
    CHECK(first.gray[0] == 255 && first.has_dirty);
    CHECK(digest(&first) == original);
    CHECK(pmkb_surface_take_dirty(&first, &dirty));

    /* Navigation between pages must repaint even on the same buffer. */
    CHECK(pmkb_store_page_build(&view, 320, 480, 1, &page)
          == PMKB_STORE_PAGE_OK);
    CHECK(pmkb_store_paint_page_cached(&view, &page, &painter, &cache)
          == PMKB_STORE_PAINT_OK);
    CHECK(first.has_dirty && first.changed_pixels > 0);
    CHECK(pmkb_surface_take_dirty(&first, &dirty));
    CHECK(pmkb_store_page_build(&view, 320, 480, 0, &page)
          == PMKB_STORE_PAGE_OK);

    /* A different surface pointer must miss the cache automatically. */
    CHECK(pmkb_surface_init(&other, 320, 480) == PMKB_OK);
    if (other.gray) {
        CHECK(pmkb_surface_take_dirty(&other, &dirty));
        PMKBStorePainter other_painter = pmkb_store_painter_for_ui(&other);
        CHECK(pmkb_store_paint_page_cached(&view, &page, &other_painter, &cache)
              == PMKB_STORE_PAINT_OK);
        CHECK(other.has_dirty && other.changed_pixels > 0);
        CHECK(digest(&other) == original);
        pmkb_surface_free(&other);
    }
    pmkb_surface_free(&first);
}
static void measure_host_cache_cost(void) {
    CHECK(sizeof(PMKBStorePaintCache) <= 64u);
    CHECK(sizeof(PMKBStorePage) <= 2048u);
    CHECK(sizeof(PMKBStoreView) <= 65536u);
    printf("PMKB CACHE RAM host: cache=%zu bytes, page=%zu bytes, "
           "catalogue=%zu bytes, surface_header=%zu bytes\n",
           sizeof(PMKBStorePaintCache), sizeof(PMKBStorePage),
           sizeof(PMKBStoreView), sizeof(PMKBSurface));

    prepare(5, 0);
    PMKBSurface surface;
    PMKBRect dirty;
    CHECK(pmkb_surface_init(&surface, 320, 480) == PMKB_OK);
    if (!surface.gray) return;
    CHECK(pmkb_surface_take_dirty(&surface, &dirty));
    CHECK(pmkb_store_page_build(&view, 320, 480, 0, &page)
          == PMKB_STORE_PAGE_OK);
    PMKBStorePainter painter = pmkb_store_painter_for_ui(&surface);
    PMKBStorePaintCache cache = {0};

    /* CPU timing is informative, not a flaky pass/fail speed threshold. */
    const unsigned full_count = 48u, hit_count = 2048u;
    unsigned full_errors = 0, hit_errors = 0;
    clock_t start_full = clock();
    for (unsigned i = 0; i < full_count; ++i)
        if (pmkb_store_paint_page(&view, &page, &painter) != PMKB_STORE_PAINT_OK)
            ++full_errors;
    clock_t end_full = clock();
    CHECK(full_errors == 0);
    CHECK(pmkb_surface_take_dirty(&surface, &dirty));

    CHECK(pmkb_store_paint_page_cached(&view, &page, &painter, &cache)
          == PMKB_STORE_PAINT_OK);
    CHECK(pmkb_surface_take_dirty(&surface, &dirty));
    clock_t start_hit = clock();
    for (unsigned i = 0; i < hit_count; ++i)
        if (pmkb_store_paint_page_cached(&view, &page, &painter, &cache)
                != PMKB_STORE_PAINT_OK)
            ++hit_errors;
    clock_t end_hit = clock();
    CHECK(hit_errors == 0);
    CHECK(!surface.has_dirty && surface.changed_pixels == 0);
    if (start_full != (clock_t)-1 && end_full != (clock_t)-1 &&
        start_hit != (clock_t)-1 && end_hit != (clock_t)-1 &&
        end_full >= start_full && end_hit >= start_hit) {
        const double full_ms = 1000.0 * (double)(end_full-start_full) /
                               ((double)CLOCKS_PER_SEC * full_count);
        const double hit_ms = 1000.0 * (double)(end_hit-start_hit) /
                              ((double)CLOCKS_PER_SEC * hit_count);
        printf("PMKB CACHE CPU host 320x480: full_ms_per_call=%.6f, "
               "hit_ms_per_call=%.6f (%u full / %u hits; diagnostic only)\n",
               full_ms, hit_ms, full_count, hit_count);
    } else {
        puts("PMKB CACHE CPU host: clock unavailable (NON MESURE)");
    }
    pmkb_surface_free(&surface);
}

/* L06-D5: simulate Store screen ownership with the REAL pinned UI surface.
 * No launcher integration; the external writer notification is deliberate. */
static void check_store_screen_session(void) {
    prepare(3, 0);
    PMKBSurface surface;
    PMKBRect dirty;
    CHECK(pmkb_surface_init(&surface, 320, 480) == PMKB_OK);
    if (!surface.gray) return;
    CHECK(pmkb_surface_take_dirty(&surface, &dirty));
    CHECK(pmkb_store_page_build(&view, 320, 480, 0, &page)
          == PMKB_STORE_PAGE_OK);
    PMKBStorePainter painter = pmkb_store_painter_for_ui(&surface);

    PMKBStoreScreen screen;
    memset(&screen, 0xa5, sizeof(screen));
    pmkb_store_screen_init(&screen);
    CHECK(!screen.visible && !screen.cache.valid);
    CHECK(sizeof(PMKBStoreScreen) <= 64u);
    const uint64_t empty = digest(&surface);
    CHECK(pmkb_store_screen_paint(&screen, &view, &page, &painter)
          == PMKB_STORE_PAINT_INVALID);
    CHECK(!surface.has_dirty && digest(&surface) == empty);

    pmkb_store_screen_enter(&screen);
    CHECK(screen.visible && !screen.cache.valid);
    CHECK(pmkb_store_screen_paint(&screen, &view, &page, &painter)
          == PMKB_STORE_PAINT_OK);
    CHECK(surface.has_dirty && screen.cache.valid);
    CHECK(pmkb_surface_take_dirty(&surface, &dirty));
    const uint64_t desired = digest(&surface);
    CHECK(pmkb_store_screen_paint(&screen, &view, &page, &painter)
          == PMKB_STORE_PAINT_OK);
    CHECK(!surface.has_dirty && surface.changed_pixels == 0);
    CHECK(digest(&surface) == desired);

    /* A status-widget write is signalled before Store is rendered again. */
    pmkb_surface_rect(&surface, (PMKBRect){0, 0, 4, 4}, 0);
    CHECK(surface.gray[0] == 0);
    CHECK(pmkb_surface_take_dirty(&surface, &dirty));
    pmkb_store_screen_external_draw(&screen);
    CHECK(screen.visible && !screen.cache.valid);
    CHECK(pmkb_store_screen_paint(&screen, &view, &page, &painter)
          == PMKB_STORE_PAINT_OK);
    CHECK(surface.gray[0] == 255 && surface.has_dirty);
    CHECK(digest(&surface) == desired);
    CHECK(pmkb_surface_take_dirty(&surface, &dirty));

    /* An exited screen must not redraw, regardless of its old contents. */
    pmkb_store_screen_leave(&screen);
    CHECK(!screen.visible && !screen.cache.valid);
    pmkb_surface_rect(&surface, (PMKBRect){0, 0, 4, 4}, 0);
    CHECK(pmkb_surface_take_dirty(&surface, &dirty));
    const uint64_t other_view = digest(&surface);
    CHECK(pmkb_store_screen_paint(&screen, &view, &page, &painter)
          == PMKB_STORE_PAINT_INVALID);
    CHECK(!surface.has_dirty && digest(&surface) == other_view);

    /* Re-entry automatically resets cache: same Store contents repaint. */
    pmkb_store_screen_enter(&screen);
    CHECK(screen.visible && !screen.cache.valid);
    CHECK(pmkb_store_screen_paint(&screen, &view, &page, &painter)
          == PMKB_STORE_PAINT_OK);
    CHECK(surface.gray[0] == 255 && surface.has_dirty);
    CHECK(digest(&surface) == desired);
    CHECK(pmkb_surface_take_dirty(&surface, &dirty));

    /* Page navigation is detected by the existing content fingerprint. */
    CHECK(pmkb_store_page_build(&view, 320, 480, 1, &page)
          == PMKB_STORE_PAGE_OUT_OF_RANGE);
    CHECK(pmkb_store_page_build(&view, 320, 480, 0, &page)
          == PMKB_STORE_PAGE_OK);
    CHECK(pmkb_store_screen_paint(&screen, &view, &page, &painter)
          == PMKB_STORE_PAINT_OK);
    CHECK(!surface.has_dirty);

    /* Forged geometry must not dirty the real surface. */
    uint64_t prior = digest(&surface);
    page.page_index = page.page_count;
    CHECK(pmkb_store_screen_paint(&screen, &view, &page, &painter)
          == PMKB_STORE_PAINT_INVALID);
    CHECK(!surface.has_dirty && digest(&surface) == prior);
    CHECK(pmkb_store_screen_paint(NULL, &view, &page, &painter)
          == PMKB_STORE_PAINT_INVALID);
    pmkb_store_screen_leave(&screen);
    pmkb_surface_free(&surface);
    printf("PMKB STORE SCREEN: lifecycle PASS, cache_limit=%zu bytes\n",
           sizeof(PMKBStoreScreen));
}

/* L06-D6a: real PMKB-UI surface integration, but NO AppHost/Launcher route.
 * The preview borrows an existing host surface and must be entered explicitly.
 * All test pixels are produced by pinned PR #30 pmkb_surface.c. */
static void check_store_ui_preview_bridge(void) {
    prepare(7, 2); /* two pages on 320x480 */
    previous = view;
    PMKBSurface surface;
    PMKBRect dirty;
    CHECK(pmkb_surface_init(&surface, 320, 480) == PMKB_OK);
    if (!surface.gray) return;
    CHECK(pmkb_surface_take_dirty(&surface, &dirty));
    PMKBStoreUIPreview preview;
    memset(&preview, 0xa5, sizeof(preview));
    pmkb_store_ui_preview_init(&preview);
    CHECK(sizeof(PMKBStoreUIPreview) <= 72u);
    CHECK(preview.target == NULL && !preview.screen.visible);
    CHECK(pmkb_store_ui_preview_draw(&preview, &view, 0)
          == PMKB_STORE_PAINT_INVALID);
    CHECK(!surface.has_dirty);

    CHECK(pmkb_store_ui_preview_enter(&preview, &surface)
          == PMKB_STORE_PAINT_OK);
    CHECK(preview.target == &surface && preview.screen.visible);
    CHECK(pmkb_store_ui_preview_draw(&preview, &view, 0)
          == PMKB_STORE_PAINT_OK);
    CHECK(surface.has_dirty && surface.changed_pixels > 0);
    CHECK(pmkb_surface_take_dirty(&surface, &dirty));
    const uint64_t page0 = digest(&surface);
    CHECK(pmkb_store_ui_preview_draw(&preview, &view, 0)
          == PMKB_STORE_PAINT_OK);
    CHECK(!surface.has_dirty && surface.changed_pixels == 0);

    /* A borrowed surface can also be written to by another view/widget. */
    pmkb_surface_rect(&surface, (PMKBRect){0, 0, 4, 4}, 0);
    CHECK(surface.gray[0] == 0);
    CHECK(pmkb_surface_take_dirty(&surface, &dirty));
    pmkb_store_ui_preview_external_draw(&preview);
    CHECK(!preview.screen.cache.valid);
    CHECK(pmkb_store_ui_preview_draw(&preview, &view, 0)
          == PMKB_STORE_PAINT_OK);
    CHECK(surface.gray[0] == 255 && surface.has_dirty);
    CHECK(digest(&surface) == page0);
    CHECK(pmkb_surface_take_dirty(&surface, &dirty));

    CHECK(pmkb_store_ui_preview_draw(&preview, &view, 1)
          == PMKB_STORE_PAINT_OK);
    CHECK(surface.has_dirty && surface.changed_pixels > 0);
    CHECK(digest(&surface) != page0);
    CHECK(pmkb_surface_take_dirty(&surface, &dirty));
    const uint64_t page1 = digest(&surface);
    CHECK(pmkb_store_ui_preview_draw(&preview, &view, 99)
          == PMKB_STORE_PAINT_INVALID);
    CHECK(!surface.has_dirty && digest(&surface) == page1);

    /* Exit prevents drawing or resurrecting a detached buffer. */
    pmkb_store_ui_preview_leave(&preview);
    CHECK(!preview.screen.visible && preview.target == NULL);
    CHECK(pmkb_store_ui_preview_draw(&preview, &view, 0)
          == PMKB_STORE_PAINT_INVALID);
    CHECK(!surface.has_dirty && digest(&surface) == page1);
    CHECK(pmkb_store_ui_preview_enter(&preview, &surface)
          == PMKB_STORE_PAINT_OK);
    CHECK(!preview.screen.cache.valid);
    CHECK(pmkb_store_ui_preview_draw(&preview, &view, 0)
          == PMKB_STORE_PAINT_OK);
    CHECK(digest(&surface) == page0);
    CHECK(pmkb_surface_take_dirty(&surface, &dirty));
    CHECK(memcmp(&view, &previous, sizeof(view)) == 0);

    /* An invalid target fails closed, including when one was active. */
    PMKBSurface invalid_surface = {0};
    uint8_t sample = 255;
    invalid_surface.gray = &sample;
    invalid_surface.width = 1;
    invalid_surface.height = 1;
    CHECK(pmkb_store_ui_preview_enter(&preview, &invalid_surface)
          == PMKB_STORE_PAINT_INVALID);
    CHECK(!preview.screen.visible && preview.target == NULL);
    CHECK(pmkb_store_ui_preview_enter(&preview, NULL)
          == PMKB_STORE_PAINT_INVALID);
    CHECK(pmkb_store_ui_preview_draw(&preview, &view, 0)
          == PMKB_STORE_PAINT_INVALID);
    CHECK(pmkb_store_ui_preview_enter(NULL, &surface)
          == PMKB_STORE_PAINT_INVALID);
    pmkb_store_ui_preview_leave(NULL);
    pmkb_store_ui_preview_external_draw(NULL);
    pmkb_surface_free(&surface);
    CHECK(surface.gray == NULL);
    printf("PMKB STORE UI PREVIEW: passive bridge PASS, size=%zu bytes\n",
           sizeof(PMKBStoreUIPreview));
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
    check_duplicate_draw(320,480,3,0);
    check_duplicate_draw(1080,1440,64,2);
    check_duplicate_draw(1440,1080,64,0);
    check_cache_lifecycle();
    measure_host_cache_cost();
    check_store_screen_session();
    check_store_ui_preview_bridge();
    if(failed)return 1;
    printf("PMKB REAL UI STORE: %d assertions PASS, 0 FAIL\n",checks);
    return 0;
}
