#include "pmkb_store_app.h"
#include "pmkb_store_page.h"
#include "pmkb_store_paint.h"
#include <stdio.h>
#include <string.h>

static PMKBStatus pmkb_store_app_draw_detail(PMKBStoreApp *app) {
    if (!app || !app->screen.gray ||
        app->selected_index >= app->catalogue.count)
        return PMKB_INVALID;
    const PMKBStoreViewItem *item =
        &app->catalogue.items[app->selected_index];
    const int compact = app->screen.width == 320;
    const int margin = compact ? 12 : (app->screen.width == 1080 ? 36 : 44);
    const int line = compact ? 24 : 40;
    const int header = compact ? 52 : 88;
    const int footer = compact ? 48 : 72;
    PMKBSurface *screen = &app->screen;
    pmkb_surface_rect(screen,
                      (PMKBRect){0,0,screen->width,screen->height},255);
    pmkb_surface_rect(screen,(PMKBRect){0,header-2,screen->width,2},192);
    pmkb_surface_rect(screen,
                      (PMKBRect){0,screen->height-footer,screen->width,2},192);
    pmkb_surface_text_box(screen,margin,compact?12:26,"STORE - DETAILS",0,
                          screen->width-2*margin,line);
    int y=header+(compact?20:42);
    pmkb_surface_text_box(screen,margin,y,item->label,0,
                          screen->width-2*margin,line);
    char version[64];
    (void)snprintf(version,sizeof(version),"Version %s",item->version);
    y+=compact?42:66;
    pmkb_surface_text_box(screen,margin,y,version,0,
                          screen->width-2*margin,line);
    y+=compact?34:56;
    pmkb_surface_text_box(screen,margin,y,item->id,0,
                          screen->width-2*margin,line);
    y+=compact?40:64;
    pmkb_surface_text_box(screen,margin,y,
                          item->network_declared
                              ? "Reseau declare: oui"
                              : "Reseau declare: non",
                          0,screen->width-2*margin,line);
    y+=compact?40:64;
    pmkb_surface_text_box(screen,margin,y,
                          "Installee - lancement non active",0,
                          screen->width-2*margin,line);
    pmkb_surface_text_box(screen,margin,
                          screen->height-footer+(compact?12:20),
                          "Retour: gauche ou liste",0,
                          screen->width-2*margin,line);
    app->initial_drawn=true;
    app->render_calls++;
    return PMKB_OK;
}

PMKBStatus pmkb_store_app_draw(PMKBStoreApp *app) {
    if (!app || !app->screen.gray) return PMKB_INVALID;
    if (app->showing_detail) return pmkb_store_app_draw_detail(app);
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
    app->selected_index = 0u;
    app->showing_detail = false;
    return pmkb_store_app_draw(app);
}

PMKBStatus pmkb_store_app_event(PMKBStoreApp *app, PMKBEvent event) {
    if (!app || !app->screen.gray) return PMKB_INVALID;
    if (app->showing_detail) {
        const int footer = app->screen.width == 320 ? 48 : 72;
        const bool footer_back =
            event.kind == PMKB_EVENT_TAP &&
            event.x >= 0 && event.x < app->screen.width / 2 &&
            event.y >= app->screen.height-footer &&
            event.y < app->screen.height;
        if (event.kind != PMKB_EVENT_LEFT &&
            event.kind != PMKB_EVENT_SHOW_LIST && !footer_back)
            return PMKB_NO_CHANGE;
        app->showing_detail = false;
        return pmkb_store_app_draw(app);
    }
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
            event.y < 0 || event.y >= app->screen.height)
            return PMKB_NO_CHANGE;
        for (unsigned i=0;i<page.visible_count;i++) {
            const PMKBStorePageRect row=page.rows[i].bounds;
            if (event.x>=row.x && event.x<row.x+row.w &&
                event.y>=row.y && event.y<row.y+row.h) {
                app->selected_index=page.rows[i].source_index;
                app->showing_detail=true;
                return pmkb_store_app_draw(app);
            }
        }
        if (event.y < page.footer.y) return PMKB_NO_CHANGE;
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
