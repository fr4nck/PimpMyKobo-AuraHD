/* L06-D4a: simulate the exact PMKB-UI surface signatures of PR #30.
 * This is a host test adapter, not a second renderer or an E-Ink backend. */
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <stdbool.h>
#define PMKB_UI_H

typedef struct { int x,y,w,h; } PMKBRect;
typedef struct {
    unsigned rect_calls, text_calls;
    unsigned version_texts, pending_texts;
    bool header_seen, pending_names_leaked;
    uint8_t last_shade;
    int min_text_height;
} PMKBSurface;
void pmkb_surface_rect(PMKBSurface *s, PMKBRect r, uint8_t shade);
void pmkb_surface_text_box(PMKBSurface *s, int x, int y,
                            const char *utf8, uint8_t shade,
                            int max_width, int max_height);
#include "pmkb_store_paint.h"

static unsigned assertions, failures;
#define CHECK(x) do { assertions++; if (!(x)) { failures++; \
    fprintf(stderr,"D4a FAIL line %u: %s\n", (unsigned)__LINE__,#x); } } while (0)

void pmkb_surface_rect(PMKBSurface *s, PMKBRect r, uint8_t shade) {
    CHECK(s && r.w > 0 && r.h > 0);
    s->rect_calls++;
    s->last_shade = shade;
}
void pmkb_surface_text_box(PMKBSurface *s, int x, int y,
                            const char *utf8, uint8_t shade,
                            int max_width, int max_height) {
    CHECK(s && x >= 0 && y >= 0 && utf8 && utf8[0] && max_width > 0);
    CHECK(shade == 0 && max_height >= 20);
    s->text_calls++;
    if (strcmp(utf8, "STORE - APERCU") == 0) s->header_seen = true;
    if (strcmp(utf8, "0.1.0") == 0) s->version_texts++;
    if (strstr(utf8, "retraits a verifier") != NULL) s->pending_texts++;
    if (strstr(utf8, ".pmkb-remove-") != NULL) s->pending_names_leaked = true;
    if (!s->min_text_height || max_height < s->min_text_height)
        s->min_text_height = max_height;
}

static PMKBStoreView view;
static PMKBStorePage page;
static PMKBSurface surface;

static void fill_view(unsigned count, unsigned pending) {
    memset(&view, 0, sizeof(view));
    view.count = count;
    view.cleanup_pending_count = pending;
    for (unsigned i = 0; i < count && i < 64; ++i) {
        (void)snprintf(view.items[i].id,sizeof(view.items[i].id),
                       "org.pmkb.app%02u", i);
        (void)snprintf(view.items[i].label,sizeof(view.items[i].label),
                       "Application %02u",i);
        (void)strcpy(view.items[i].version,"0.1.0");
    }
}
static void reset_calls(void) { memset(&surface,0,sizeof(surface)); }
static PMKBStorePainter painter(void) { return pmkb_store_painter_for_ui(&surface); }

static void render(int w, int h, unsigned page_no, unsigned rows,
                   unsigned pending) {
    CHECK(pmkb_store_page_build(&view,w,h,page_no,&page) == PMKB_STORE_PAGE_OK);
    CHECK(page.visible_count == rows);
    reset_calls();
    PMKBStorePainter p = painter();
    CHECK(pmkb_store_paint_page(&view,&page,&p) == PMKB_STORE_PAINT_OK);
    CHECK(surface.rect_calls == rows + 3u);
    CHECK(surface.text_calls == rows * 2u + 2u + (pending ? 1u : 0u));
    CHECK(surface.version_texts == rows);
    CHECK(surface.header_seen);
    CHECK(surface.pending_texts == (pending ? 1u : 0u));
    CHECK(!surface.pending_names_leaked);
    CHECK(surface.min_text_height >= 20);
}

static void tests(void) {
    fill_view(0,0);
    render(320,480,0,0,0);
    fill_view(64,512);
    render(320,480,0,5,512);
    CHECK(page.rows[0].version.h == 20);
    render(320,480,12,4,512);
    render(1080,1440,0,12,512);
    CHECK(page.rows[0].version.h == 30);
    render(1440,1080,7,1,512);
    CHECK(page.rows[0].version.h == 30);

    /* Fully validate before painting: never half-paint a forged page. */
    reset_calls();
    page.rows[0].source_index = 65;
    PMKBStorePainter p = painter();
    CHECK(pmkb_store_paint_page(&view,&page,&p) == PMKB_STORE_PAINT_INVALID);
    CHECK(surface.rect_calls == 0 && surface.text_calls == 0);
    CHECK(pmkb_store_page_build(&view,1440,1080,0,&page) == PMKB_STORE_PAGE_OK);
    page.header.h++;
    CHECK(pmkb_store_paint_page(&view,&page,&p) == PMKB_STORE_PAINT_INVALID);
    CHECK(surface.rect_calls == 0 && surface.text_calls == 0);
    CHECK(pmkb_store_page_build(&view,1440,1080,0,&page) == PMKB_STORE_PAGE_OK);
    view.items[0].launchable = true;
    CHECK(pmkb_store_paint_page(&view,&page,&p) == PMKB_STORE_PAINT_INVALID);
    CHECK(surface.rect_calls == 0 && surface.text_calls == 0);
    view.items[0].launchable = false;
    CHECK(pmkb_store_paint_page(NULL,&page,&p) == PMKB_STORE_PAINT_INVALID);
    CHECK(pmkb_store_paint_page(&view,NULL,&p) == PMKB_STORE_PAINT_INVALID);
    CHECK(pmkb_store_paint_page(&view,&page,NULL) == PMKB_STORE_PAINT_INVALID);
    PMKBStorePainter invalid = p;
    invalid.text_box = NULL;
    CHECK(pmkb_store_paint_page(&view,&page,&invalid) == PMKB_STORE_PAINT_INVALID);
    CHECK(surface.rect_calls == 0 && surface.text_calls == 0);
    CHECK(pmkb_store_page_build(&view,320,480,0,&page) == PMKB_STORE_PAGE_OK);
    PMKBStorePage before = page;
    PMKBStoreView initial = view;
    CHECK(pmkb_store_paint_page(&view,&page,&p) == PMKB_STORE_PAINT_OK);
    CHECK(memcmp(&before,&page,sizeof(page)) == 0);
    CHECK(memcmp(&initial,&view,sizeof(view)) == 0);
}
int main(void) {
    tests();
    if (failures) return 1;
    printf("PMKB STORE PAINT: %u assertions PASS, 0 FAIL\n",assertions);
    return 0;
}
