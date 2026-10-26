/* L06-D3 passive page layout fixtures: the test runner alone uses stdio. */
#include "pmkb_store_page.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static unsigned checks, failures;
#define CHECK(x) do { checks++; if (!(x)) { failures++; \
    fprintf(stderr,"PMKB PAGE FAIL %u: %s\n",__LINE__,#x); } } while (0)

static PMKBStoreView view; /* 64 * ~500 bytes: static, not on stack */
static PMKBStorePage page;

static void make_view(unsigned count, unsigned pending) {
    memset(&view, 0, sizeof(view));
    view.count = count;
    view.cleanup_pending_count = pending;
    for (unsigned i = 0; i < count && i < PMKB_STORE_VIEW_MAX_APPS; ++i) {
        PMKBStoreViewItem *item = &view.items[i];
        snprintf(item->id, sizeof(item->id), "org.pmkb.app%02u", i);
        snprintf(item->label, sizeof(item->label), "Application %02u", i);
        strcpy(item->version, "0.1.0");
    }
}
static bool inside(PMKBStorePageRect outer, PMKBStorePageRect inner) {
    return inner.w > 0 && inner.h > 0 &&
           inner.x >= outer.x && inner.y >= outer.y &&
           inner.x + inner.w <= outer.x + outer.w &&
           inner.y + inner.h <= outer.y + outer.h;
}
static void check_rects(const PMKBStorePage *p) {
    CHECK(p->header.y == 0 && p->header.w == p->width);
    CHECK(p->footer.y + p->footer.h == p->height);
    CHECK(p->header.y + p->header.h <= p->body.y);
    CHECK(p->body.y + p->body.h <= p->footer.y);
    for (unsigned i = 0; i < p->visible_count; ++i) {
        const PMKBStorePageRow *r = &p->rows[i];
        CHECK(inside(p->body, r->bounds));
        CHECK(inside(r->bounds, r->title));
        CHECK(inside(r->bounds, r->version));
        CHECK(r->bounds.h >= 44); /* PMKB-UI touch target baseline */
        CHECK(r->title.y + r->title.h <= r->version.y);
        if (i) CHECK(p->rows[i-1].bounds.y + p->rows[i-1].bounds.h < r->bounds.y);
    }
}
static void tests(void) {
    make_view(0, 0);
    CHECK(pmkb_store_page_build(&view, 320, 480, 0, &page) == PMKB_STORE_PAGE_OK);
    CHECK(page.page_count == 1 && page.visible_count == 0);
    CHECK(page.header.h == 52 && page.footer.h == 48);
    CHECK(page.ink == 0 && page.background == 255 && page.divider == 192);
    check_rects(&page);

    make_view(64, 512);
    PMKBStoreView snapshot = view;
    CHECK(pmkb_store_page_build(&view, 320, 480, 0, &page) == PMKB_STORE_PAGE_OK);
    CHECK(page.page_count == 13 && page.visible_count == 5);
    CHECK(page.rows[0].source_index == 0 && page.rows[4].source_index == 4);
    CHECK(page.rows[0].shade == 255 && page.rows[1].shade == 240);
    CHECK(page.cleanup_pending_count == 512 && page.total_items == 64);
    check_rects(&page);
    CHECK(pmkb_store_page_build(&view, 320, 480, 12, &page) == PMKB_STORE_PAGE_OK);
    CHECK(page.visible_count == 4 && page.rows[3].source_index == 63);
    check_rects(&page);
    CHECK(pmkb_store_page_build(&view, 1080, 1440, 0, &page) == PMKB_STORE_PAGE_OK);
    CHECK(page.page_count == 6 && page.visible_count == 12);
    CHECK(page.header.h == 88 && page.footer.h == 72);
    check_rects(&page);
    CHECK(pmkb_store_page_build(&view, 1080, 1440, 5, &page) == PMKB_STORE_PAGE_OK);
    CHECK(page.visible_count == 4 && page.rows[3].source_index == 63);
    check_rects(&page);
    CHECK(pmkb_store_page_build(&view, 1440, 1080, 0, &page) == PMKB_STORE_PAGE_OK);
    CHECK(page.page_count == 8 && page.visible_count == 9);
    check_rects(&page);
    CHECK(pmkb_store_page_build(&view, 1440, 1080, 7, &page) == PMKB_STORE_PAGE_OK);
    CHECK(page.visible_count == 1 && page.rows[0].source_index == 63);
    check_rects(&page);
    CHECK(memcmp(&snapshot, &view, sizeof(view)) == 0);
    CHECK(sizeof(page) < 2048u);

    memset(&page, 0xaa, sizeof(page));
    CHECK(pmkb_store_page_build(&view, 320, 480, 13, &page) == PMKB_STORE_PAGE_OUT_OF_RANGE);
    CHECK(page.width == 0 && page.visible_count == 0 && page.rows[0].source_index == 0);
    CHECK(pmkb_store_page_build(&view, 321, 480, 0, &page) == PMKB_STORE_PAGE_GEOMETRY);
    CHECK(pmkb_store_page_build(&view, 1440, 1440, 0, &page) == PMKB_STORE_PAGE_GEOMETRY);
    CHECK(pmkb_store_page_build(&view, 1440, 1080, 0, NULL) == PMKB_STORE_PAGE_INVALID);
    CHECK(pmkb_store_page_build(NULL, 1440, 1080, 0, &page) == PMKB_STORE_PAGE_INVALID);
    CHECK(page.width == 0 && page.visible_count == 0);
    make_view(64, 0);
    view.items[7].launchable = true;
    CHECK(pmkb_store_page_build(&view, 320, 480, 0, &page) == PMKB_STORE_PAGE_INVALID);
    view.items[7].launchable = false;
    view.items[7].label[0] = 0;
    CHECK(pmkb_store_page_build(&view, 320, 480, 0, &page) == PMKB_STORE_PAGE_INVALID);
    make_view(0, 513);
    CHECK(pmkb_store_page_build(&view, 320, 480, 0, &page) == PMKB_STORE_PAGE_INVALID);
    memset(&view, 0, sizeof(view));view.count = 65;
    CHECK(pmkb_store_page_build(&view, 320, 480, 0, &page) == PMKB_STORE_PAGE_INVALID);
}
#ifdef PMKB_STORE_WITH_PARSER
static int parse_stdin(int argc, char **argv) {
    if (argc != 5) return 2;
    const int width = atoi(argv[2]), height = atoi(argv[3]);
    const unsigned index = (unsigned)atoi(argv[4]);
    static unsigned char input[PMKB_STORE_VIEW_MAX_JSON + 1u];
    size_t length = fread(input, 1, sizeof(input), stdin);
    if (pmkb_store_view_parse(input, length, &view) != PMKB_STORE_VIEW_OK) return 3;
    if (pmkb_store_page_build(&view, width, height, index, &page) != PMKB_STORE_PAGE_OK)
        return 4;
    printf("OK %u/%u %u %u %u %u\n", page.page_index, page.page_count,
           page.visible_count, page.total_items, page.cleanup_pending_count,
           page.visible_count ? page.rows[0].source_index : 0u);
    return 0;
}
#endif
int main(int argc, char **argv) {
#ifdef PMKB_STORE_WITH_PARSER
    if (argc > 1 && strcmp(argv[1], "--stdin") == 0)
        return parse_stdin(argc, argv);
#else
    (void)argc;(void)argv;
#endif
    tests();
    if (failures) return 1;
    printf("PMKB STORE PAGE: %u assertions PASS, 0 FAIL\n", checks);
    return 0;
}
