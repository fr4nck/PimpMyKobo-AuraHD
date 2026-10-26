/* PMKB Store application V0: bounded offline catalogue on PMKB-UI. */
#ifndef PMKB_STORE_APP_H
#define PMKB_STORE_APP_H
#include "pmkb_ui.h"
#include "pmkb_store_view.h"

typedef struct {
    PMKBSurface screen;
    PMKBStoreView catalogue;
    unsigned page_index;
    bool initial_drawn;
    unsigned render_calls;
} PMKBStoreApp;

PMKBStatus pmkb_store_app_init(PMKBStoreApp *app, int width, int height);
void pmkb_store_app_free(PMKBStoreApp *app);
PMKBStatus pmkb_store_app_load_snapshot(PMKBStoreApp *app,
                                        const uint8_t *json, size_t length);
PMKBStatus pmkb_store_app_event(PMKBStoreApp *app, PMKBEvent event);
PMKBStatus pmkb_store_app_draw(PMKBStoreApp *app);
#endif
