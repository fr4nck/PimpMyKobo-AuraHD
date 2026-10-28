#include "pmkb_store_paint.h"
#include <stdio.h>
#include <string.h>

static bool equal_rect(PMKBStorePageRect a, PMKBStorePageRect b) {
    return a.x == b.x && a.y == b.y && a.w == b.w && a.h == b.h;
}

/* Never trust caller-supplied geometry or source indices without checking. */
static bool valid_page(const PMKBStoreView *view, const PMKBStorePage *page) {
    PMKBStorePage expected;
    if (pmkb_store_page_build(view, page->width, page->height,
                              page->page_index, &expected) != PMKB_STORE_PAGE_OK)
        return false;
    if (page->page_count != expected.page_count ||
        page->total_items != expected.total_items ||
        page->cleanup_pending_count != expected.cleanup_pending_count ||
        page->visible_count != expected.visible_count ||
        page->ink != expected.ink || page->background != expected.background ||
        page->divider != expected.divider ||
        !equal_rect(page->header, expected.header) ||
        !equal_rect(page->body, expected.body) ||
        !equal_rect(page->footer, expected.footer)) return false;
    for (unsigned i = 0; i < expected.visible_count; ++i) {
        const PMKBStorePageRow *a = &page->rows[i];
        const PMKBStorePageRow *b = &expected.rows[i];
        if (a->source_index != b->source_index || a->shade != b->shade ||
            !equal_rect(a->bounds, b->bounds) ||
            !equal_rect(a->title, b->title) ||
            !equal_rect(a->version, b->version)) return false;
    }
    return true;
}

PMKBStorePaintStatus pmkb_store_paint_page(const PMKBStoreView *view,
                                           const PMKBStorePage *page,
                                           const PMKBStorePainter *painter) {
    if (!view || !page || !painter || !painter->context ||
        !painter->rect || !painter->text_box || !valid_page(view,page))
        return PMKB_STORE_PAINT_INVALID;

    void *ctx = painter->context;
    painter->rect(ctx, 0, 0, page->width, page->height, page->background);
    painter->rect(ctx, 0, page->header.h - 2, page->width, 2, page->divider);
    painter->rect(ctx, 0, page->footer.y, page->width, 2, page->divider);

    const int margin = page->body.x;
    const int scale_height = (page->width == 320) ? 20 : 30;
    const int title_y = (page->width == 320) ? 12 : 26;
    painter->text_box(ctx, margin, title_y, "STORE - APERCU", page->ink,
                      page->width - 2 * margin, scale_height);

    for (unsigned i = 0; i < page->visible_count; ++i) {
        const PMKBStorePageRow *row = &page->rows[i];
        const PMKBStoreViewItem *item = &view->items[row->source_index];
        painter->rect(ctx, row->bounds.x, row->bounds.y, row->bounds.w,
                      row->bounds.h, row->shade);
        painter->text_box(ctx, row->title.x, row->title.y, item->label,
                          page->ink, row->title.w, row->title.h);
        painter->text_box(ctx, row->version.x, row->version.y, item->version,
                          page->ink, row->version.w, row->version.h);
    }

    char footer[48];
    (void)snprintf(footer, sizeof(footer), "Page %u/%u - %u apps",
                   page->page_index + 1u, page->page_count, page->total_items);
    const int footer_y = page->footer.y + (page->width == 320 ? 4 : 8);
    painter->text_box(ctx, margin, footer_y, footer, page->ink,
                      page->width - 2 * margin, scale_height);
    if (page->cleanup_pending_count) {
        char pending[48];
        (void)snprintf(pending, sizeof(pending), "%u retraits a verifier",
                       page->cleanup_pending_count);
        painter->text_box(ctx, margin,
                          page->footer.y + (page->width == 320 ? 26 : 40),
                          pending, page->ink, page->width - 2 * margin,
                          scale_height);
    }
    return PMKB_STORE_PAINT_OK;
}

/* L06-D4d: cheap content fingerprint; no heap, I/O or platform dependencies.
 * A caller must invalidate the cache if OTHER UI drawing touches the buffer.
 * All inputs have been validated by pmkb_store_page_build before stamping. */
static uint64_t stamp_byte(uint64_t h, uint8_t value) {
    return (h ^ (uint64_t)value) * UINT64_C(1099511628211);
}
static uint64_t stamp_int(uint64_t h, uint32_t value) {
    for (unsigned n = 0; n < 4; ++n)
        h = stamp_byte(h, (uint8_t)(value >> (n * 8u)));
    return h;
}
static uint64_t stamp_string(uint64_t h, const char *text) {
    const unsigned char *p = (const unsigned char *)text;
    while (*p) h = stamp_byte(h, *p++);
    return stamp_byte(h, 0); /* unambiguous field boundary */
}
static uint64_t stamp_page(const PMKBStoreView *view,
                            const PMKBStorePage *page) {
    uint64_t h = UINT64_C(1469598103934665603);
    h = stamp_int(h, (uint32_t)page->width);
    h = stamp_int(h, (uint32_t)page->height);
    h = stamp_int(h, page->page_index);
    h = stamp_int(h, page->page_count);
    h = stamp_int(h, page->visible_count);
    h = stamp_int(h, page->total_items);
    h = stamp_int(h, page->cleanup_pending_count);
    for (unsigned i = 0; i < page->visible_count; ++i) {
        const PMKBStorePageRow *row = &page->rows[i];
        const PMKBStoreViewItem *entry = &view->items[row->source_index];
        h = stamp_int(h, row->source_index);
        h = stamp_string(h, entry->id);
        h = stamp_string(h, entry->label);
        h = stamp_string(h, entry->version);
        h = stamp_byte(h, entry->network_declared ? 1u : 0u);
    }
    return h;
}
void pmkb_store_paint_cache_reset(PMKBStorePaintCache *cache) {
    if (cache) memset(cache, 0, sizeof(*cache));
}
PMKBStorePaintStatus pmkb_store_paint_page_cached(
    const PMKBStoreView *view, const PMKBStorePage *page,
    const PMKBStorePainter *painter, PMKBStorePaintCache *cache) {
    if (!cache || !view || !page || !painter || !painter->context ||
        !painter->rect || !painter->text_box || !valid_page(view, page))
        return PMKB_STORE_PAINT_INVALID;
    uint64_t stamp = stamp_page(view, page);
    if (cache->valid && cache->stamp == stamp &&
        cache->context == painter->context &&
        cache->rect == painter->rect &&
        cache->text_box == painter->text_box)
        return PMKB_STORE_PAINT_OK; /* ZERO draw calls and invalidations */
    PMKBStorePaintStatus result = pmkb_store_paint_page(view, page, painter);
    if (result == PMKB_STORE_PAINT_OK) {
        cache->stamp = stamp;
        cache->context = painter->context;
        cache->rect = painter->rect;
        cache->text_box = painter->text_box;
        cache->valid = true;
    }
    return result;
}
