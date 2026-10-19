/* PMKB application launch seam V0 — no assumption about the HTML launcher.
 * These stable app IDs may be mapped to PR #25 when launcher becomes native. */
#ifndef PMKB_LAUNCHER_BRIDGE_H
#define PMKB_LAUNCHER_BRIDGE_H
#include "pmkb_ui.h"
#include "pmkb_calculator_ui.h"

typedef enum {
    PMKB_APP_NONE=0,
    PMKB_APP_NOTES,
    PMKB_APP_CALCULATOR,
    PMKB_APP_STORE
} PMKBAppId;

typedef struct {
    PMKBAppId kind;
    const char *id;       /* stable opaque ID for a future native launcher */
    const char *label;    /* user-facing UTF-8 */
    bool runnable;        /* Store reserved, not runnable in this version */
} PMKBAppInfo;

/* Owns exactly one application at a time, created on launch.
 * There is no resident clipboard, app service, KOReader or browser. */
typedef struct {
    PMKBAppId active;
    void *instance;
} PMKBAppHost;

const PMKBAppInfo *pmkb_app_info(PMKBAppId kind);
void pmkb_app_host_init(PMKBAppHost *host);
PMKBStatus pmkb_app_host_launch(PMKBAppHost *host,PMKBAppId kind,
                                int width,int height);
/* Notes RAM is unsaved by definition: unless discard=true, leaving a
 * populated notebook must be refused to prevent silent data loss. */
PMKBStatus pmkb_app_host_close(PMKBAppHost *host,bool discard);
PMKBSurface *pmkb_app_host_screen(PMKBAppHost *host);
PMKBStatus pmkb_app_host_event(PMKBAppHost *host,
                                PMKBEvent event,const char *utc);
PMKBStatus pmkb_app_host_present(PMKBAppHost *host,
                                  const PMKBBackend *backend);
#endif
