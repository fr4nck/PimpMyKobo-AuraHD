/* L06-D6c: real pinned launcher bridge, Notes/Calculator lifecycle DOUBLES.
 * Store uses a dedicated synthetic surface. No app route is activated. */
#include "pmkb_launcher_bridge.h"
#include "pmkb_store_ui_preview.h"
#include "pmkb_store_launcher_guard.h"
#include "pmkb_store_surface_owner.h"
#include "pmkb_store_passive_router.h"
#include <stdint.h>
#include <stdio.h>
#include <string.h>

static unsigned checks, fails, note_inits, note_frees, note_events;
static unsigned calc_inits, calc_frees, calc_events;
static PMKBStoreView catalog;
#define CHECK(x) do { ++checks; if (!(x)) { ++fails; \
    fprintf(stderr,"LAUNCHER ISOLATION FAIL line %u: %s\n", \
            (unsigned)__LINE__,#x); } } while (0)

/* Deliberate doubles ONLY for Notes/Calculator implementations. */
PMKBStatus pmkb_ui_init(PMKBUI *u,int w,int h) {
    ++note_inits; return pmkb_surface_init(&u->screen,w,h);
}
void pmkb_ui_free(PMKBUI *u) {
    ++note_frees; pmkb_surface_free(&u->screen);
}
PMKBStatus pmkb_ui_event(PMKBUI *u,PMKBEvent ev,const char *utc) {
    (void)utc; ++note_events;
    if(ev.kind==PMKB_EVENT_TAP)
        pmkb_surface_rect(&u->screen,(PMKBRect){10,10,6,6},0);
    return PMKB_OK;
}
PMKBStatus pmkb_calc_ui_init(PMKBCalcUI *u,int w,int h) {
    ++calc_inits; return pmkb_surface_init(&u->screen,w,h);
}
void pmkb_calc_ui_free(PMKBCalcUI *u) {
    ++calc_frees; pmkb_surface_free(&u->screen);
}
PMKBStatus pmkb_calc_ui_event(PMKBCalcUI *u,PMKBEvent ev) {
    ++calc_events;
    if(ev.kind==PMKB_EVENT_TAP)
        pmkb_surface_rect(&u->screen,(PMKBRect){20,20,6,6},0);
    return PMKB_OK;
}
static uint64_t hash_frame(const PMKBSurface *s) {
    uint64_t h=UINT64_C(1469598103934665603);
    size_t n=(size_t)s->width*(size_t)s->height;
    for(size_t i=0;i<n;i++) {
        h^=s->gray[i]; h*=UINT64_C(1099511628211);
    }
    return h;
}
typedef struct { const uint8_t *expected; unsigned count; } Probe;
static PMKBStatus probe_present(void *ctx,const uint8_t *gray,
                                 int w,int h,PMKBRect rect) {
    Probe *p=(Probe *)ctx; ++p->count;
    CHECK(gray==p->expected);
    CHECK(w==320 && h==480);
    CHECK(rect.x>=0 && rect.y>=0 && rect.w>0 && rect.h>0);
    CHECK(rect.x+rect.w<=w && rect.y+rect.h<=h);
    return PMKB_OK;
}
static void verify_reserved(void) {
    PMKBAppHost host;pmkb_app_host_init(&host);
    const PMKBAppInfo *info=pmkb_app_info(PMKB_APP_STORE);
    CHECK(info && info->kind==PMKB_APP_STORE && !info->runnable);
    if(!info)return;
    CHECK(strcmp(info->id,"store")==0);
    const unsigned n=note_inits,c=calc_inits;
    CHECK(pmkb_app_host_launch(&host,PMKB_APP_STORE,320,480)==PMKB_NOT_FOUND);
    CHECK(note_inits==n && calc_inits==c);
    CHECK(host.active==PMKB_APP_NONE && host.instance==NULL);
    CHECK(pmkb_app_host_screen(&host)==NULL);
    CHECK(pmkb_app_host_present(&host,NULL)==PMKB_NOT_FOUND);
    CHECK(pmkb_app_host_event(&host,(PMKBEvent){.kind=PMKB_EVENT_TAP},
                              NULL)==PMKB_NOT_FOUND);
    CHECK(pmkb_app_host_close(&host,false)==PMKB_NO_CHANGE);
}
static void verify_notes_isolation(void) {
    PMKBAppHost host;pmkb_app_host_init(&host);
    CHECK(pmkb_app_host_launch(&host,PMKB_APP_NOTES,320,480)==PMKB_OK);
    if(host.active!=PMKB_APP_NOTES || !host.instance)return;
    PMKBUI *note=(PMKBUI *)host.instance;
    note->notebook.count=1; /* synthetic unsaved gate, NOT actual Notes data */
    PMKBSurface *ns=pmkb_app_host_screen(&host);
    CHECK(ns==&note->screen && ns->gray!=NULL);
    CHECK(pmkb_app_host_event(&host,
          (PMKBEvent){.kind=PMKB_EVENT_TAP,.x=10,.y=10},NULL)==PMKB_OK);
    CHECK(note_events>0);
    Probe probe={ns->gray,0};
    PMKBBackend backend={&probe,probe_present};
    CHECK(pmkb_app_host_present(&host,&backend)==PMKB_OK);
    CHECK(probe.count>=1);
    uint64_t before=hash_frame(ns);

    PMKBSurface dedicated={0};PMKBRect dirty;
    CHECK(pmkb_surface_init(&dedicated,320,480)==PMKB_OK);
    if(!dedicated.gray)return;
    CHECK(pmkb_surface_take_dirty(&dedicated,&dirty));
    PMKBStoreUIPreview preview;
    pmkb_store_ui_preview_init(&preview);
    CHECK(pmkb_store_ui_preview_enter(&preview,&dedicated)==PMKB_STORE_PAINT_OK);
    CHECK(preview.target==&dedicated && preview.target!=ns);
    CHECK(pmkb_store_ui_preview_draw(&preview,&catalog,0)==PMKB_STORE_PAINT_OK);
    CHECK(dedicated.has_dirty && dedicated.changed_pixels>0);
    CHECK(hash_frame(ns)==before && note->notebook.count==1);
    unsigned freed=note_frees;
    CHECK(pmkb_app_host_launch(&host,PMKB_APP_STORE,320,480)==PMKB_INVALID);
    CHECK(host.active==PMKB_APP_NOTES && host.instance==note);
    CHECK(note_frees==freed);
    CHECK(pmkb_app_host_close(&host,false)==PMKB_UNSAVED);
    CHECK(host.active==PMKB_APP_NOTES && host.instance==note);
    CHECK(note->notebook.count==1 && hash_frame(ns)==before);

    uint64_t dedicated_hash=hash_frame(&dedicated);
    pmkb_store_ui_preview_leave(&preview);
    CHECK(pmkb_app_host_close(&host,true)==PMKB_OK);
    CHECK(host.active==PMKB_APP_NONE && host.instance==NULL);
    CHECK(note_frees==freed+1u);
    CHECK(dedicated.gray && hash_frame(&dedicated)==dedicated_hash);
    CHECK(pmkb_app_host_launch(&host,PMKB_APP_STORE,320,480)==PMKB_NOT_FOUND);
    pmkb_surface_free(&dedicated);
}
static void verify_calculator_isolation(void) {
    PMKBAppHost host;pmkb_app_host_init(&host);
    CHECK(pmkb_app_host_launch(&host,PMKB_APP_CALCULATOR,320,480)==PMKB_OK);
    if(host.active!=PMKB_APP_CALCULATOR || !host.instance)return;
    PMKBSurface *s=pmkb_app_host_screen(&host);
    CHECK(s && s->gray);
    CHECK(pmkb_app_host_event(&host,
          (PMKBEvent){.kind=PMKB_EVENT_TAP,.x=20,.y=20},NULL)==PMKB_OK);
    CHECK(calc_events>0);
    const uint64_t before=hash_frame(s);
    CHECK(pmkb_app_host_launch(&host,PMKB_APP_STORE,320,480)==PMKB_INVALID);
    CHECK(pmkb_app_host_screen(&host)==s && hash_frame(s)==before);
    unsigned freed=calc_frees;
    CHECK(pmkb_app_host_close(&host,false)==PMKB_OK);
    CHECK(calc_frees==freed+1u);
    CHECK(host.active==PMKB_APP_NONE && host.instance==NULL);
    CHECK(pmkb_app_host_launch(&host,PMKB_APP_STORE,320,480)==PMKB_NOT_FOUND);
}

/* L06-D6d: real Launcher bridge, fail-closed guard, independent Store pixels.
 * Notes/Calc business logic is deliberately supplied by the doubles above. */
static void verify_guarded_surface_ownership(void) {
    PMKBAppHost host; pmkb_app_host_init(&host);
    PMKBStoreLauncherGuard guard;
    memset(&guard, 0xa5, sizeof(guard));
    pmkb_store_launcher_guard_init(&guard);
    CHECK(!guard.preview.screen.visible && guard.host == NULL);
    CHECK(sizeof(PMKBStoreLauncherGuard) <= 96u);

    PMKBSurface dedicated = {0};
    PMKBRect dirty;
    CHECK(pmkb_surface_init(&dedicated, 320, 480) == PMKB_OK);
    if (!dedicated.gray) return;
    CHECK(pmkb_surface_take_dirty(&dedicated, &dirty));
    CHECK(pmkb_store_launcher_guard_draw(&guard, &catalog, 0)
          == PMKB_STORE_PAINT_INVALID);
    CHECK(pmkb_store_launcher_guard_enter(&guard, NULL, &dedicated)
          == PMKB_STORE_PAINT_INVALID);
    CHECK(pmkb_store_launcher_guard_enter(&guard, &host, &dedicated)
          == PMKB_STORE_PAINT_OK);
    CHECK(pmkb_store_launcher_guard_draw(&guard, &catalog, 0)
          == PMKB_STORE_PAINT_OK);
    CHECK(pmkb_surface_take_dirty(&dedicated, &dirty));
    uint64_t initial = hash_frame(&dedicated);
    CHECK(pmkb_store_launcher_guard_draw(&guard, &catalog, 0)
          == PMKB_STORE_PAINT_OK);
    CHECK(!dedicated.has_dirty && dedicated.changed_pixels == 0);

    /* Starting Notes changes the host lifecycle; fail closed on draw. */
    CHECK(pmkb_app_host_launch(&host, PMKB_APP_NOTES, 320, 480) == PMKB_OK);
    if (host.active != PMKB_APP_NOTES || !host.instance) {
        pmkb_surface_free(&dedicated);
        return;
    }
    PMKBSurface *notes = pmkb_app_host_screen(&host);
    CHECK(notes && notes->gray);
    CHECK(pmkb_store_launcher_guard_draw(&guard, &catalog, 0)
          == PMKB_STORE_PAINT_INVALID);
    CHECK(guard.host == NULL && guard.preview.target == NULL);
    CHECK(hash_frame(&dedicated) == initial && !dedicated.has_dirty);

    const uint64_t note_hash = hash_frame(notes);
    CHECK(pmkb_store_launcher_guard_enter(&guard, &host, notes)
          == PMKB_STORE_PAINT_INVALID);
    CHECK(guard.host == NULL && !guard.preview.screen.visible);
    PMKBSurface alias = *notes; /* same pixels despite different struct */
    CHECK(&alias != notes && alias.gray == notes->gray);
    CHECK(pmkb_store_launcher_guard_enter(&guard, &host, &alias)
          == PMKB_STORE_PAINT_INVALID);
    CHECK(hash_frame(notes) == note_hash);

    /* Overlap regression: offset alias is not a separate allocation. */
    PMKBSurface overlap = *notes;
    overlap.gray = notes->gray + 1;
    CHECK(pmkb_store_launcher_guard_enter(&guard, &host, &overlap)
          == PMKB_STORE_PAINT_INVALID);
    /* D6l: an interior offset near the end is still overlapping. */
    overlap.gray = notes->gray + (size_t)notes->width *
                                  (size_t)notes->height - 1u;
    CHECK(pmkb_store_launcher_guard_enter(&guard, &host, &overlap)
          == PMKB_STORE_PAINT_INVALID);
    CHECK(guard.host == NULL && guard.preview.target == NULL);
    CHECK(hash_frame(notes) == note_hash);

    CHECK(pmkb_store_launcher_guard_enter(&guard, &host, &dedicated)
          == PMKB_STORE_PAINT_OK);
    CHECK(pmkb_store_launcher_guard_draw(&guard, &catalog, 0)
          == PMKB_STORE_PAINT_OK);
    CHECK(hash_frame(notes) == note_hash);
    CHECK(pmkb_surface_take_dirty(&dedicated, &dirty));
    pmkb_surface_rect(&dedicated, (PMKBRect){0,0,3,3}, 0);
    CHECK(dedicated.gray[0] == 0);
    CHECK(pmkb_surface_take_dirty(&dedicated, &dirty));
    pmkb_store_launcher_guard_external_draw(&guard);
    CHECK(pmkb_store_launcher_guard_draw(&guard, &catalog, 0)
          == PMKB_STORE_PAINT_OK);
    CHECK(dedicated.gray[0] == 255 && hash_frame(&dedicated) == initial);
    CHECK(hash_frame(notes) == note_hash);
    CHECK(pmkb_surface_take_dirty(&dedicated, &dirty));

    /* Closing Notes changes the host; a stale guarded draw is refused. */
    CHECK(pmkb_app_host_close(&host, true) == PMKB_OK);
    CHECK(host.active == PMKB_APP_NONE && host.instance == NULL);
    CHECK(pmkb_store_launcher_guard_draw(&guard, &catalog, 0)
          == PMKB_STORE_PAINT_INVALID);
    CHECK(!guard.preview.screen.visible && guard.host == NULL);
    CHECK(!dedicated.has_dirty && hash_frame(&dedicated) == initial);

    CHECK(pmkb_app_host_launch(&host, PMKB_APP_CALCULATOR, 320, 480)
          == PMKB_OK);
    if (host.active == PMKB_APP_CALCULATOR && host.instance) {
        PMKBSurface *calculator = pmkb_app_host_screen(&host);
        CHECK(calculator && calculator->gray);
        CHECK(pmkb_store_launcher_guard_enter(&guard, &host, calculator)
              == PMKB_STORE_PAINT_INVALID);
        PMKBSurface duplicate = *calculator;
        CHECK(pmkb_store_launcher_guard_enter(&guard, &host, &duplicate)
              == PMKB_STORE_PAINT_INVALID);
        uint64_t calc_hash = hash_frame(calculator);
        CHECK(pmkb_store_launcher_guard_enter(&guard, &host, &dedicated)
              == PMKB_STORE_PAINT_OK);
        CHECK(pmkb_store_launcher_guard_draw(&guard, &catalog, 0)
              == PMKB_STORE_PAINT_OK);
        CHECK(hash_frame(calculator) == calc_hash);
        CHECK(pmkb_surface_take_dirty(&dedicated, &dirty));
        CHECK(pmkb_app_host_close(&host, false) == PMKB_OK);
        CHECK(pmkb_store_launcher_guard_draw(&guard, &catalog, 0)
              == PMKB_STORE_PAINT_INVALID);
        CHECK(!dedicated.has_dirty && hash_frame(&dedicated) == initial);
    }
    /* L06-D6e: repeated lifecycle transitions using the real host bridge.
     * Every stale draw must detach before painting, and the dedicated buffer
     * remains owned by this test for the entire guard lifetime. */
    for (unsigned round = 0; round < 3; ++round) {
        const PMKBAppId next = (round & 1u)
            ? PMKB_APP_CALCULATOR : PMKB_APP_NOTES;
        CHECK(host.active == PMKB_APP_NONE && host.instance == NULL);
        CHECK(pmkb_store_launcher_guard_enter(&guard, &host, &dedicated)
              == PMKB_STORE_PAINT_OK);
        CHECK(pmkb_store_launcher_guard_draw(&guard, &catalog, 0)
              == PMKB_STORE_PAINT_OK);
        CHECK(pmkb_surface_take_dirty(&dedicated, &dirty) ||
              !dedicated.has_dirty);
        const uint64_t store_before = hash_frame(&dedicated);
        CHECK(pmkb_app_host_launch(&host, next, 320, 480) == PMKB_OK);
        PMKBSurface *app_surface = pmkb_app_host_screen(&host);
        CHECK(app_surface && app_surface->gray);
        if (app_surface && app_surface->gray) {
            const uint64_t app_before = hash_frame(app_surface);
            CHECK(pmkb_store_launcher_guard_draw(&guard, &catalog, 0)
                  == PMKB_STORE_PAINT_INVALID);
            CHECK(guard.host == NULL && guard.preview.target == NULL);
            CHECK(hash_frame(app_surface) == app_before);
            CHECK(hash_frame(&dedicated) == store_before);
            CHECK(pmkb_store_launcher_guard_enter(&guard, &host, &dedicated)
                  == PMKB_STORE_PAINT_OK);
            CHECK(pmkb_store_launcher_guard_draw(&guard, &catalog, 0)
                  == PMKB_STORE_PAINT_OK);
            CHECK(hash_frame(app_surface) == app_before);
        }
        pmkb_store_launcher_guard_before_destroy(&guard);
        CHECK(guard.host == NULL && guard.preview.target == NULL);
        pmkb_store_launcher_guard_before_destroy(&guard); /* idempotent */
        CHECK(!guard.preview.screen.visible);
        CHECK(pmkb_app_host_close(&host, true) == PMKB_OK);
        CHECK(pmkb_store_launcher_guard_draw(&guard, &catalog, 0)
              == PMKB_STORE_PAINT_INVALID);
    }
    /* L06-D6g: detached guards may not draw until explicit re-entry. */
    pmkb_store_launcher_guard_before_destroy(&guard);
    CHECK(pmkb_store_launcher_guard_draw(&guard, &catalog, 0)
          == PMKB_STORE_PAINT_INVALID);
    CHECK(pmkb_store_launcher_guard_enter(&guard, &host, &dedicated)
          == PMKB_STORE_PAINT_OK);
    CHECK(pmkb_store_launcher_guard_draw(&guard, &catalog, 0)
          == PMKB_STORE_PAINT_OK);
    pmkb_store_launcher_guard_before_destroy(&guard);
    CHECK(guard.host == NULL && guard.preview.target == NULL);
    /* D6h: closing a borrowed surface is safe only after detach.
     * Verify the guard stays inert when the dedicated pixels are released,
     * then restore the surface for the remaining cleanup checks. */
    pmkb_store_launcher_guard_before_destroy(&guard);
    pmkb_surface_free(&dedicated);
    CHECK(dedicated.gray == NULL);
    CHECK(pmkb_store_launcher_guard_draw(&guard, &catalog, 0)
          == PMKB_STORE_PAINT_INVALID);
    CHECK(pmkb_surface_init(&dedicated, 320, 480) == PMKB_OK);
    CHECK(dedicated.gray != NULL);
    /* D6j negative seam contract: inconsistent inactive host is refused,
     * and a failed enter must discard the previous borrowed surface. */
    host.active = PMKB_APP_NONE;
    host.instance = (void *)&dedicated; /* deliberately inconsistent */
    CHECK(pmkb_store_launcher_guard_enter(&guard, &host, &dedicated)
          == PMKB_STORE_PAINT_INVALID);
    CHECK(guard.host == NULL && guard.preview.target == NULL);
    host.instance = NULL;
    CHECK(pmkb_store_launcher_guard_enter(&guard, &host, &dedicated)
          == PMKB_STORE_PAINT_OK);
    CHECK(pmkb_store_launcher_guard_draw(&guard, &catalog, 0)
          == PMKB_STORE_PAINT_OK);
    host.instance = (void *)&dedicated; /* invalidated between draws */
    CHECK(pmkb_store_launcher_guard_draw(&guard, &catalog, 0)
          == PMKB_STORE_PAINT_INVALID);
    CHECK(guard.host == NULL && guard.preview.target == NULL);
    host.instance = NULL;
    pmkb_store_launcher_guard_leave(&guard);
    pmkb_store_launcher_guard_leave(NULL);
    pmkb_store_launcher_guard_external_draw(NULL);
    CHECK(guard.host == NULL && !guard.preview.screen.visible);
    pmkb_surface_free(&dedicated);
    CHECK(dedicated.gray == NULL);
    printf("PMKB STORE LAUNCHER GUARD: %zu bytes, isolation PASS\n",
           sizeof(PMKBStoreLauncherGuard));
}
static void verify_surface_owner(void) {
    PMKBAppHost host;
    pmkb_app_host_init(&host);
    PMKBStoreSurfaceOwner owner;
    pmkb_store_owner_init(&owner);
    CHECK(pmkb_store_owner_pixel_bytes(&owner) == 0u);
    CHECK(pmkb_store_owner_open(&owner, &host, 1, 1)
          == PMKB_STORE_PAINT_INVALID);
    CHECK(pmkb_store_owner_pixel_bytes(&owner) == 0u);
    CHECK(pmkb_store_owner_open(&owner, &host, 320, 480)
          == PMKB_STORE_PAINT_OK);
    CHECK(pmkb_store_owner_pixel_bytes(&owner) == 153600u);
    CHECK(pmkb_store_launcher_guard_draw(&owner.guard, &catalog, 0)
          == PMKB_STORE_PAINT_OK);
    CHECK(pmkb_app_host_launch(&host, PMKB_APP_NOTES, 320, 480) == PMKB_OK);
    CHECK(pmkb_store_launcher_guard_draw(&owner.guard, &catalog, 0)
          == PMKB_STORE_PAINT_INVALID);
    CHECK(pmkb_store_owner_open(&owner, &host, 320, 480)
          == PMKB_STORE_PAINT_OK);
    CHECK(pmkb_store_owner_pixel_bytes(&owner) == 153600u);
    /* D6p: host rejected after framebuffer allocation must free it. */
    PMKBAppHost invalid_host;
    pmkb_app_host_init(&invalid_host);
    invalid_host.instance = (void *)&owner; /* incoherent inactive host */
    CHECK(pmkb_store_owner_open(&owner, &invalid_host, 320, 480)
          == PMKB_STORE_PAINT_INVALID);
    CHECK(!owner.allocated && owner.surface.gray == NULL);
    CHECK(owner.guard.host == NULL && owner.guard.preview.target == NULL);
    CHECK(pmkb_store_owner_pixel_bytes(&owner) == 0u);
    CHECK(pmkb_store_owner_open(&owner, &host, 320, 480)
          == PMKB_STORE_PAINT_OK);
    CHECK(pmkb_store_owner_pixel_bytes(&owner) == 153600u);
    /* D6o: reopening with invalid dimensions must detach and free. */
    CHECK(pmkb_store_owner_open(&owner, &host, 319, 480)
          == PMKB_STORE_PAINT_INVALID);
    CHECK(owner.surface.gray == NULL && !owner.allocated);
    CHECK(owner.guard.host == NULL && owner.guard.preview.target == NULL);
    CHECK(pmkb_store_owner_pixel_bytes(&owner) == 0u);
    CHECK(pmkb_store_owner_open(&owner, &host, 320, 480)
          == PMKB_STORE_PAINT_OK);
    CHECK(pmkb_store_owner_pixel_bytes(&owner) == 153600u);
    pmkb_store_owner_close(&owner);
    pmkb_store_owner_close(&owner);
    CHECK(owner.surface.gray == NULL);
    CHECK(pmkb_store_owner_pixel_bytes(&owner) == 0u);
    CHECK(pmkb_app_host_close(&host, true) == PMKB_OK);
    CHECK(pmkb_store_owner_open(&owner, &host, 1080, 1440)
          == PMKB_STORE_PAINT_OK);
    CHECK(pmkb_store_owner_pixel_bytes(&owner) == 1555200u);
    pmkb_store_owner_close(&owner);
    /* D6q: repeated allocation/free cycles with bounded pixel accounting. */
    for (unsigned cycle = 0; cycle < 16; ++cycle) {
        const int w = (cycle & 1u) ? 1080 : 320;
        const int h = (cycle & 1u) ? 1440 : 480;
        const size_t expected = (size_t)w * (size_t)h;
        CHECK(pmkb_store_owner_open(&owner, &host, w, h)
              == PMKB_STORE_PAINT_OK);
        CHECK(pmkb_store_owner_pixel_bytes(&owner) == expected);
        CHECK(owner.surface.gray != NULL);
        pmkb_store_owner_close(&owner);
        CHECK(owner.surface.gray == NULL && !owner.allocated);
        CHECK(owner.guard.host == NULL && owner.guard.preview.target == NULL);
        CHECK(pmkb_store_owner_pixel_bytes(&owner) == 0u);
    }
}
static void verify_passive_router(void) {
    PMKBStorePassiveRouter router;
    pmkb_store_router_init(&router);
    CHECK(pmkb_store_router_preview(&router, 320, 480, &catalog, 0)
          == PMKB_STORE_PAINT_OK);
    CHECK(pmkb_store_owner_pixel_bytes(&router.store) == 153600u);
    CHECK(pmkb_store_router_launch_app(&router, PMKB_APP_STORE, 320, 480)
          == PMKB_NOT_FOUND);
    CHECK(pmkb_store_owner_pixel_bytes(&router.store) == 0u);
    CHECK(pmkb_store_router_launch_app(&router, PMKB_APP_NOTES, 320, 480)
          == PMKB_OK);
    PMKBUI *notes = (PMKBUI *)router.host.instance;
    CHECK(notes != NULL);
    if (notes) notes->notebook.count = 1;
    CHECK(pmkb_store_router_preview(&router, 320, 480, &catalog, 0)
          == PMKB_STORE_PAINT_OK);
    /* D6t: an attempted switch must preserve the unsaved Notes session. */
    CHECK(pmkb_store_router_launch_app(&router, PMKB_APP_CALCULATOR, 320, 480)
          == PMKB_INVALID);
    CHECK(router.host.active == PMKB_APP_NOTES);
    CHECK(router.host.instance == notes);
    CHECK(notes->notebook.count == 1);
    CHECK(pmkb_store_owner_pixel_bytes(&router.store) == 0u);
    CHECK(pmkb_store_router_close_app(&router, false) == PMKB_UNSAVED);
    CHECK(router.host.active == PMKB_APP_NOTES);
    CHECK(pmkb_store_owner_pixel_bytes(&router.store) == 0u);
    CHECK(pmkb_store_router_close_app(&router, true) == PMKB_OK);
    CHECK(router.host.active == PMKB_APP_NONE);
    CHECK(pmkb_store_router_preview(&router, 319, 480, &catalog, 0)
          == PMKB_STORE_PAINT_INVALID);
    CHECK(pmkb_store_owner_pixel_bytes(&router.store) == 0u);
    pmkb_store_router_dismiss(&router);
}
int main(void) {
    memset(&catalog,0,sizeof(catalog));
    catalog.count=1;
    (void)strcpy(catalog.items[0].id,"org.pmkb.preview");
    (void)strcpy(catalog.items[0].label,"Store preview");
    (void)strcpy(catalog.items[0].version,"0.1.0");
    verify_reserved();
    verify_notes_isolation();
    verify_calculator_isolation();
    verify_guarded_surface_ownership();
    verify_surface_owner();
    verify_passive_router();
    CHECK(note_inits==note_frees && calc_inits==calc_frees);
    if(fails)return 1;
    printf("PMKB REAL LAUNCHER ISOLATION: %u assertions PASS, 0 FAIL\n",checks);
    return 0;
}
