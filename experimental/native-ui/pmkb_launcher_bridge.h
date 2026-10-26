/* PMKB application launch seam V0 — no assumption about the HTML launcher.
 * These stable app IDs may be mapped to PR #25 when launcher becomes native. */
#ifndef PMKB_LAUNCHER_BRIDGE_H
#define PMKB_LAUNCHER_BRIDGE_H
#include "pmkb_ui.h"
#include "pmkb_calculator_ui.h"
#include "pmkb_store_app.h"
#include "../whiteboard-v0/pmkb_whiteboard_launch_seam.h"
#include <stdint.h>

typedef enum {
    PMKB_APP_NONE=0,
    PMKB_APP_NOTES,
    PMKB_APP_CALCULATOR,
    PMKB_APP_STORE,
    PMKB_APP_WHITEBOARD
} PMKBAppId;

typedef struct {
    PMKBAppId kind;
    const char *id;       /* stable opaque ID for a future native launcher */
    const char *label;    /* user-facing UTF-8 */
    bool runnable;        /* registered for launch by this native host */
} PMKBAppInfo;

/* Owns exactly one application at a time, created on launch.
 * There is no resident clipboard, app service, KOReader or browser. */
typedef struct {
    PMKBAppId active;
    void *instance;
    /* Monotonic lifecycle token. It changes after each successful launch or
     * close and never wraps; passive borrowers must reject UINT64_MAX. */
    uint64_t generation;
} PMKBAppHost;

const PMKBAppInfo *pmkb_app_info(PMKBAppId kind);
void pmkb_app_host_init(PMKBAppHost *host);
PMKBStatus pmkb_app_host_launch(PMKBAppHost *host,PMKBAppId kind,
                                int width,int height);
/* Notes RAM is unsaved by definition: unless discard=true, leaving a
 * populated notebook must be refused to prevent silent data loss. */
/* Load a bounded read-only Store snapshot. Only valid while Store is active. */
PMKBStatus pmkb_app_host_store_load(PMKBAppHost *host,
                                    const uint8_t *json,size_t length);
/* Whiteboard receives logical coordinates; generic PMKBEvent is not a pen event. */
PMKBWBStatus pmkb_app_host_whiteboard_touch(PMKBAppHost *host,
        PMKBWBTouchKind kind,int x,int y);
PMKBWBStatus pmkb_app_host_whiteboard_undo(PMKBAppHost *host);
PMKBStatus pmkb_app_host_close(PMKBAppHost *host,bool discard);
PMKBSurface *pmkb_app_host_screen(PMKBAppHost *host);
PMKBStatus pmkb_app_host_event(PMKBAppHost *host,
                                PMKBEvent event,const char *utc);
PMKBStatus pmkb_app_host_present(PMKBAppHost *host,
                                  const PMKBBackend *backend);
#endif
