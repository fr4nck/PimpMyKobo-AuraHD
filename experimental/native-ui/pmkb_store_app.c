#include "pmkb_store_app.h"
#include "pmkb_store_page.h"
#include "pmkb_store_paint.h"
#include <string.h>

PMKBStatus pmkb_store_app_draw(PMKBStoreApp *app) {
    if (!app || !app->screen.gray) return PMKB_INVALID;
    PMKBStorePage page;
    if (pmkb_store_page_build(&app->catalogue, app->screen.width,
                              app->screen.height, app->page_index, &page)
        != PMKB_STORE_PAGE_OK) return PMKB_INVALID;
    PMKBStorePainter painter = pmkb_store_painter_for_ui(&app->screen);
    if (pmkb_store_paint_page(&app->catalogue, &page, &painter)
        != PMKB_STORE_PAINT_OK) return PMKB_INVALID;
    app->initial_drawn = true;
    app->render_calls++;
    return PMKB_OK;
}

PMKBStatus pmkb_store_app_init(PMKBStoreApp *app, int width, int height) {
    if (!app) return PMKB_INVALID;
    memset(app, 0, sizeof(*app));
    PMKBStatus status = pmkb_surface_init(&app->screen, width, height);
    if (status != PMKB_OK) return status;
    status = pmkb_store_app_draw(app);
    if (status != PMKB_OK) {
        pmkb_surface_free(&app->screen);
        memset(app, 0, sizeof(*app));
    }
    return status;
}

void pmkb_store_app_free(PMKBStoreApp *app) {
    if (!app) return;
    pmkb_surface_free(&app->screen);
    memset(app, 0, sizeof(*app));
}

PMKBStatus pmkb_store_app_load_snapshot(PMKBStoreApp *app,
                                        const uint8_t *json, size_t length) {
    if (!app || !app->screen.gray) return PMKB_INVALID;
    PMKBStoreView next;
    PMKBStoreViewStatus parsed = pmkb_store_view_parse(json, length, &next);
    if (parsed == PMKB_STORE_VIEW_LIMIT) return PMKB_LIMIT;
    if (parsed != PMKB_STORE_VIEW_OK) return PMKB_INVALID;
    PMKBStorePage check;
    if (pmkb_store_page_build(&next, app->screen.width, app->screen.height,
                              0u, &check) != PMKB_STORE_PAGE_OK)
        return PMKB_INVALID;
    app->catalogue = next;
    app->page_index = 0u;
    return pmkb_store_app_draw(app);
}

PMKBStatus pmkb_store_app_event(PMKBStoreApp *app, PMKBEvent event) {
    if (!app || !app->screen.gray) return PMKB_INVALID;
    PMKBStorePage page;
    if (pmkb_store_page_build(&app->catalogue, app->screen.width,
                              app->screen.height, app->page_index, &page)
        != PMKB_STORE_PAGE_OK) return PMKB_INVALID;
    unsigned next = app->page_index;
    if (event.kind == PMKB_EVENT_LEFT) {
        if (next > 0u) next--;
    } else if (event.kind == PMKB_EVENT_RIGHT) {
        if (next + 1u < page.page_count) next++;
    } else if (event.kind == PMKB_EVENT_SHOW_LIST) {
        next = 0u;
    } else if (event.kind == PMKB_EVENT_TAP) {
        if (event.x < 0 || event.x >= app->screen.width ||
            event.y < page.footer.y || event.y >= app->screen.height)
            return PMKB_NO_CHANGE;
        if (event.x < app->screen.width / 2) {
            if (next > 0u) next--;
        } else if (next + 1u < page.page_count) next++;
    } else {
        return PMKB_NO_CHANGE;
    }
    if (next == app->page_index) return PMKB_NO_CHANGE;
    app->page_index = next;
    return pmkb_store_app_draw(app);
}
