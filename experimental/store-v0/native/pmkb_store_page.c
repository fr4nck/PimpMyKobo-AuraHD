#include "pmkb_store_page.h"
#include <string.h>

static bool terminated(const char *s, size_t capacity) {
    return s[0] != '\0' && memchr(s, '\0', capacity) != NULL;
}

static bool valid_view(const PMKBStoreView *v) {
    if (v == NULL || v->count > PMKB_STORE_VIEW_MAX_APPS ||
        v->cleanup_pending_count > PMKB_STORE_VIEW_MAX_PENDING) return false;
    for (unsigned i = 0; i < v->count; ++i) {
        const PMKBStoreViewItem *entry = &v->items[i];
        if (entry->launchable ||
            !terminated(entry->id, sizeof(entry->id)) ||
            !terminated(entry->label, sizeof(entry->label)) ||
            !terminated(entry->version, sizeof(entry->version))) return false;
    }
    return true;
}

PMKBStorePageStatus pmkb_store_page_build(const PMKBStoreView *view,
                                          int width, int height,
                                          unsigned page_index,
                                          PMKBStorePage *out) {
    if (!out) return PMKB_STORE_PAGE_INVALID;
    memset(out, 0, sizeof(*out));
    if (!valid_view(view)) return PMKB_STORE_PAGE_INVALID;

    int margin, header, footer, gap, row_height, pad;
    if (width == 320 && height == 480) {
        margin = 12; header = 52; footer = 48; gap = 6;
        row_height = 56; pad = 8;
    } else if ((width == 1080 && height == 1440) ||
               (width == 1440 && height == 1080)) {
        margin = (width == 1080) ? 36 : 44;
        header = 88; footer = 72; gap = 10;
        row_height = 84; pad = 24;
    } else return PMKB_STORE_PAGE_GEOMETRY;

    const int body_height = height - header - footer - 2 * pad;
    unsigned capacity = (unsigned)((body_height + gap) / (row_height + gap));
    if (capacity > PMKB_STORE_PAGE_MAX_ROWS) capacity = PMKB_STORE_PAGE_MAX_ROWS;
    if (capacity == 0u) return PMKB_STORE_PAGE_GEOMETRY;
    const unsigned page_count = view->count == 0u ? 1u :
        (view->count + capacity - 1u) / capacity;
    if (page_index >= page_count) return PMKB_STORE_PAGE_OUT_OF_RANGE;

    out->width = width;
    out->height = height;
    out->header = (PMKBStorePageRect){0, 0, width, header};
    out->body = (PMKBStorePageRect){margin, header + pad,
                                    width - margin * 2, body_height};
    out->footer = (PMKBStorePageRect){0, height - footer, width, footer};
    out->ink = PMKB_STORE_PAGE_INK;
    out->background = PMKB_STORE_PAGE_WHITE;
    out->divider = PMKB_STORE_PAGE_DIVIDER;
    out->page_index = page_index;
    out->page_count = page_count;
    out->total_items = view->count;
    out->cleanup_pending_count = view->cleanup_pending_count;

    const unsigned start = page_index * capacity;
    const unsigned remaining = view->count - start;
    const unsigned shown = remaining < capacity ? remaining : capacity;
    out->visible_count = shown;
    for (unsigned i = 0; i < shown; ++i) {
        PMKBStorePageRow *row = &out->rows[i];
        row->source_index = start + i;
        row->bounds = (PMKBStorePageRect){margin,
                                          out->body.y + (int)i * (row_height + gap),
                                          width - 2 * margin, row_height};
        row->title = (PMKBStorePageRect){row->bounds.x + 16,
                                         row->bounds.y + (width == 320 ? 8 : 14),
                                         row->bounds.w - 32,
                                         width == 320 ? 22 : 30};
        row->version = (PMKBStorePageRect){row->bounds.x + 16,
                                           row->bounds.y + (width == 320 ? 32 : 49),
                                           row->bounds.w - 32,
                                           width == 320 ? 16 : 21};
        row->shade = (i % 2u) ? PMKB_STORE_PAGE_ALTERNATE : PMKB_STORE_PAGE_WHITE;
    }
    return PMKB_STORE_PAGE_OK;
}
