/* L06-D6c: real pinned launcher bridge, Notes/Calculator lifecycle DOUBLES.
 * Store uses a dedicated synthetic surface. No app route is activated. */
#include "pmkb_launcher_bridge.h"
#include "pmkb_store_ui_preview.h"
#include "pmkb_store_launcher_guard.h"
#include "pmkb_store_surface_owner.h"
#include "pmkb_store_passive_router.h"
#include "pmkb_store_eink_sim.h"
#include "pmkb_store_eink_pending.h"
#include "pmkb_store_eink_async.h"
#include "pmkb_store_eink_lifecycle.h"
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
    /* D6w: invalid app kind also fails in the pre-allocation path. */
    invalid_host.instance = NULL;
    invalid_host.active = PMKB_APP_STORE;
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
    /* D6z: turn real pages in the same owned framebuffer. */
    PMKBStoreView many = catalog;
    many.count = PMKB_STORE_VIEW_MAX_APPS;
    for (unsigned i=1; i<many.count; ++i) {
        many.items[i] = catalog.items[0];
        (void)snprintf(many.items[i].id,sizeof(many.items[i].id),
                       "org.pmkb.preview.%u",i);
    }
    CHECK(pmkb_store_router_preview(&router,320,480,&many,0)
          == PMKB_STORE_PAINT_OK);
    uint8_t *page_gray = router.store.surface.gray;
    CHECK(pmkb_store_router_preview(&router,320,480,&many,1)
          == PMKB_STORE_PAINT_OK);
    CHECK(router.store.surface.gray == page_gray);
    CHECK(pmkb_store_owner_pixel_bytes(&router.store) == 153600u);
    /* D7a: page switch has a bounded host dirty rectangle. */
    PMKBRect dirty = {0};
    CHECK(pmkb_surface_take_dirty(&router.store.surface, &dirty));
    CHECK(dirty.w > 0 && dirty.h > 0);
    CHECK(dirty.x >= 0 && dirty.y >= 0);
    CHECK(dirty.x + dirty.w <= router.store.surface.width);
    CHECK(dirty.y + dirty.h <= router.store.surface.height);
    CHECK(!pmkb_surface_take_dirty(&router.store.surface, &dirty));
    CHECK(pmkb_store_router_preview(&router,320,480,&many,0)
          == PMKB_STORE_PAINT_OK);
    CHECK(router.store.surface.gray == page_gray);
    uint8_t *first_gray = router.store.surface.gray;
    CHECK(pmkb_store_router_preview(&router, 320, 480, &catalog, 0)
          == PMKB_STORE_PAINT_OK);
    CHECK(router.store.surface.gray == first_gray);
    CHECK(pmkb_store_owner_pixel_bytes(&router.store) == 153600u);
    /* D6y: invalid page discards the current surface and cache. */
    CHECK(pmkb_store_router_preview(&router, 320, 480, &catalog, 9999u)
          == PMKB_STORE_PAINT_INVALID);
    CHECK(router.store.surface.gray == NULL);
    CHECK(!router.store.guard.preview.screen.cache.valid);
    CHECK(pmkb_store_owner_pixel_bytes(&router.store) == 0u);
    CHECK(pmkb_store_router_preview(&router, 320, 480, &catalog, 0)
          == PMKB_STORE_PAINT_OK);
    CHECK(pmkb_store_owner_pixel_bytes(&router.store) == 153600u);
    CHECK(pmkb_store_router_preview(&router, 1080, 1440, &catalog, 0)
          == PMKB_STORE_PAINT_OK);
    CHECK(pmkb_store_owner_pixel_bytes(&router.store) == 1555200u);
    CHECK(pmkb_store_router_preview(&router, 320, 480, &catalog, 0)
          == PMKB_STORE_PAINT_OK);
    CHECK(pmkb_store_owner_pixel_bytes(&router.store) == 153600u);

    CHECK(pmkb_store_router_preview(&router, 320, 480, NULL, 0)
          == PMKB_STORE_PAINT_INVALID);
    CHECK(pmkb_store_owner_pixel_bytes(&router.store) == 0u);
    CHECK(router.store.surface.gray == NULL);
    CHECK(router.store.guard.host == NULL);
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
typedef struct { unsigned calls; bool fail; PMKBRect last; } D7bBackend;
static PMKBStatus d7b_present(void *ctx, const uint8_t *gray,
                              int width, int height, PMKBRect rect) {
    D7bBackend *mock = (D7bBackend *)ctx;
    ++mock->calls;
    mock->last = rect;
    if (!gray || rect.w <= 0 || rect.h <= 0 ||
        rect.x < 0 || rect.y < 0 ||
        rect.x + rect.w > width || rect.y + rect.h > height)
        return PMKB_INVALID;
    return mock->fail ? PMKB_INVALID : PMKB_OK;
}
static void verify_router_presentation(void) {
    PMKBStorePassiveRouter router;
    pmkb_store_router_init(&router);
    CHECK(pmkb_store_router_preview(&router,320,480,&catalog,0)
          == PMKB_STORE_PAINT_OK);
    D7bBackend mock = {0};
    PMKBBackend backend = {&mock,d7b_present};
    mock.fail = true;
    CHECK(pmkb_surface_present(&router.store.surface,&backend)==PMKB_INVALID);
    CHECK(mock.calls >= 1u);
    CHECK(router.store.surface.has_dirty);
    mock.fail = false;
    unsigned before = mock.calls;
    CHECK(pmkb_surface_present(&router.store.surface,&backend)==PMKB_OK);
    CHECK(mock.calls > before);
    CHECK(!router.store.surface.has_dirty);
    CHECK(pmkb_surface_present(&router.store.surface,&backend)==PMKB_NO_CHANGE);
    pmkb_store_router_dismiss(&router);
}
/* D7c: force the two-region optimization in the REAL surface presenter. */
typedef struct { unsigned calls, fail_on; } D7cBackend;
static PMKBStatus d7c_present(void *ctx, const uint8_t *gray,
                             int width, int height, PMKBRect rect) {
    D7cBackend *mock=(D7cBackend *)ctx;
    ++mock->calls;
    if (!gray || width != 320 || height != 480 ||
        rect.x < 0 || rect.y < 0 || rect.w <= 0 || rect.h <= 0 ||
        rect.x + rect.w > width || rect.y + rect.h > height)
        return PMKB_INVALID;
    return mock->calls == mock->fail_on ? PMKB_INVALID : PMKB_OK;
}
static void verify_split_present_failure(void) {
    PMKBStorePassiveRouter router;
    pmkb_store_router_init(&router);
    CHECK(pmkb_store_router_preview(&router,320,480,&catalog,0)
          == PMKB_STORE_PAINT_OK);
    PMKBSurface *surface=&router.store.surface;
    /* Consume first-draw dirty state, then create distant islands. */
    PMKBRect previous;
    CHECK(pmkb_surface_take_dirty(surface,&previous));
    pmkb_surface_rect(surface,(PMKBRect){2,2,6,6},0);
    pmkb_surface_rect(surface,(PMKBRect){308,462,6,6},0);
    CHECK(surface->has_dirty);
    CHECK(surface->dirty_island_count==2);
    D7cBackend mock={0,2};
    PMKBBackend backend={&mock,d7c_present};
    CHECK(pmkb_surface_present(surface,&backend)==PMKB_INVALID);
    CHECK(mock.calls==2u);
    CHECK(surface->has_dirty);
    mock.calls=0; mock.fail_on=0;
    CHECK(pmkb_surface_present(surface,&backend)==PMKB_OK);
    CHECK(mock.calls==2u);
    CHECK(!surface->has_dirty);
    CHECK(pmkb_surface_present(surface,&backend)==PMKB_NO_CHANGE);
    pmkb_store_router_dismiss(&router);
}
typedef struct { PMKBSurface *surface; unsigned calls; bool edited; } D7dBackend;
static PMKBStatus d7d_present(void *ctx, const uint8_t *gray,
                             int width, int height, PMKBRect rect) {
    D7dBackend *mock=(D7dBackend *)ctx;
    ++mock->calls;
    if (!gray || width != 320 || height != 480 || rect.w <= 0)
        return PMKB_INVALID;
    /* Synchronous simulated host edit while the callback is running. */
    if (!mock->edited) {
        mock->edited = true;
        pmkb_surface_rect(mock->surface,(PMKBRect){0,0,9,9},123);
    }
    return PMKB_OK;
}
static void verify_reentrant_present(void) {
    PMKBStorePassiveRouter router;
    pmkb_store_router_init(&router);
    CHECK(pmkb_store_router_preview(&router,320,480,&catalog,0)
          == PMKB_STORE_PAINT_OK);
    PMKBSurface *surface=&router.store.surface;
    PMKBRect ignored;
    CHECK(pmkb_surface_take_dirty(surface,&ignored));
    pmkb_surface_rect(surface,(PMKBRect){300,450,8,8},0);
    D7dBackend mock={surface,0,false};
    PMKBBackend backend={&mock,d7d_present};
    CHECK(pmkb_surface_present(surface,&backend)==PMKB_OK);
    CHECK(mock.calls==1u);
    CHECK(surface->has_dirty);
    CHECK(pmkb_surface_present(surface,&backend)==PMKB_OK);
    CHECK(mock.calls>=2u);
    CHECK(!surface->has_dirty);
    pmkb_store_router_dismiss(&router);
}
/* D7e: invalid backend must never consume a pending dirty region. */
static void verify_backend_absent(void) {
    PMKBStorePassiveRouter router;
    pmkb_store_router_init(&router);
    CHECK(pmkb_store_router_preview(&router,320,480,&catalog,0)
          == PMKB_STORE_PAINT_OK);
    PMKBSurface *surface=&router.store.surface;
    CHECK(surface->has_dirty);
    CHECK(pmkb_store_router_present(&router,NULL)==PMKB_INVALID);
    CHECK(surface->has_dirty);
    PMKBBackend missing={0};
    CHECK(pmkb_store_router_present(&router,&missing)==PMKB_INVALID);
    CHECK(surface->has_dirty);
    D7bBackend mock={0};
    PMKBBackend backend={&mock,d7b_present};
    CHECK(pmkb_store_router_present(&router,&backend)==PMKB_OK);
    CHECK(mock.calls>=1u);
    CHECK(!surface->has_dirty);
    pmkb_store_router_dismiss(&router);
}
/* D7g: a host identity transition without going through the router
 * must fail closed before presentation, without calling the backend. */
static void verify_stale_host_before_present(void) {
    PMKBStorePassiveRouter router;
    pmkb_store_router_init(&router);
    CHECK(pmkb_store_router_preview(&router,320,480,&catalog,0)
          == PMKB_STORE_PAINT_OK);
    D7bBackend mock={0};
    PMKBBackend backend={&mock,d7b_present};
    CHECK(pmkb_app_host_launch(&router.host,PMKB_APP_CALCULATOR,320,480)
          == PMKB_OK);
    CHECK(pmkb_store_router_present(&router,&backend)==PMKB_INVALID);
    CHECK(mock.calls==0u);
    CHECK(router.store.surface.gray==NULL);
    CHECK(pmkb_store_owner_pixel_bytes(&router.store)==0u);
    CHECK(pmkb_app_host_close(&router.host,true)==PMKB_OK);
}
/* D7h: dismissal invalidates presentation until an explicit new preview. */
static void verify_dismiss_before_present(void) {
    PMKBStorePassiveRouter router;
    pmkb_store_router_init(&router);
    CHECK(pmkb_store_router_preview(&router,320,480,&catalog,0)
          == PMKB_STORE_PAINT_OK);
    D7bBackend mock={0};
    PMKBBackend backend={&mock,d7b_present};
    pmkb_store_router_dismiss(&router);
    CHECK(pmkb_store_router_present(&router,&backend)==PMKB_INVALID);
    CHECK(mock.calls==0u);
    CHECK(pmkb_store_owner_pixel_bytes(&router.store)==0u);
    CHECK(pmkb_store_router_preview(&router,320,480,&catalog,0)
          == PMKB_STORE_PAINT_OK);
    CHECK(pmkb_store_router_present(&router,&backend)==PMKB_OK);
    CHECK(mock.calls>=1u);
    pmkb_store_router_dismiss(&router);
}
/* D7i: resizing requires the owned surface and backend dimensions to match. */
typedef struct { unsigned calls; int expected_w, expected_h; } D7iBackend;
static PMKBStatus d7i_present(void *context, const uint8_t *gray,
                             int width, int height, PMKBRect dirty) {
    D7iBackend *m=(D7iBackend *)context;
    ++m->calls;
    return gray && width==m->expected_w && height==m->expected_h &&
           dirty.w>0 && dirty.h>0 &&
           dirty.x>=0 && dirty.y>=0 &&
           dirty.x+dirty.w<=width && dirty.y+dirty.h<=height
           ? PMKB_OK : PMKB_INVALID;
}
static void verify_resize_before_present(void) {
    PMKBStorePassiveRouter router;
    pmkb_store_router_init(&router);
    CHECK(pmkb_store_router_preview(&router,320,480,&catalog,0)
          == PMKB_STORE_PAINT_OK);
    CHECK(pmkb_store_router_preview(&router,1080,1440,&catalog,0)
          == PMKB_STORE_PAINT_OK);
    CHECK(pmkb_store_owner_pixel_bytes(&router.store)==1555200u);
    D7iBackend mock={0,1080,1440};
    PMKBBackend backend={&mock,d7i_present};
    CHECK(pmkb_store_router_present(&router,&backend)==PMKB_OK);
    CHECK(mock.calls>=1u);
    CHECK(!router.store.surface.has_dirty);
    pmkb_store_router_dismiss(&router);
    CHECK(pmkb_store_router_present(&router,&backend)==PMKB_INVALID);
    CHECK(mock.calls>=1u);
}
/* D7j: failed resized present retains dirty and can retry. */
static void verify_resize_present_retry(void) {
    PMKBStorePassiveRouter router;
    pmkb_store_router_init(&router);
    CHECK(pmkb_store_router_preview(&router,320,480,&catalog,0)
          == PMKB_STORE_PAINT_OK);
    CHECK(pmkb_store_router_preview(&router,1080,1440,&catalog,0)
          == PMKB_STORE_PAINT_OK);
    D7bBackend mock={0};
    PMKBBackend backend={&mock,d7b_present};
    mock.fail=true;
    CHECK(pmkb_store_router_present(&router,&backend)==PMKB_INVALID);
    CHECK(mock.calls>=1u);
    CHECK(router.store.surface.has_dirty);
    CHECK(pmkb_store_owner_pixel_bytes(&router.store)==1555200u);
    mock.fail=false;
    unsigned before=mock.calls;
    CHECK(pmkb_store_router_present(&router,&backend)==PMKB_OK);
    CHECK(mock.calls>before);
    CHECK(!router.store.surface.has_dirty);
    CHECK(pmkb_store_router_present(&router,&backend)==PMKB_NO_CHANGE);
    pmkb_store_router_dismiss(&router);
}
/* D7k: failed present followed by dismissal must release all Store pixels. */
static void verify_failed_present_then_dismiss(void) {
    PMKBStorePassiveRouter router;
    pmkb_store_router_init(&router);
    CHECK(pmkb_store_router_preview(&router,320,480,&catalog,0)
          == PMKB_STORE_PAINT_OK);
    D7bBackend mock={0};
    PMKBBackend backend={&mock,d7b_present};
    mock.fail=true;
    CHECK(pmkb_store_router_present(&router,&backend)==PMKB_INVALID);
    CHECK(router.store.surface.has_dirty);
    pmkb_store_router_dismiss(&router);
    CHECK(router.store.surface.gray==NULL);
    CHECK(pmkb_store_owner_pixel_bytes(&router.store)==0u);
    unsigned old_calls=mock.calls;
    CHECK(pmkb_store_router_present(&router,&backend)==PMKB_INVALID);
    CHECK(mock.calls==old_calls);
    mock.fail=false;
    CHECK(pmkb_store_router_preview(&router,320,480,&catalog,0)
          == PMKB_STORE_PAINT_OK);
    CHECK(pmkb_store_router_present(&router,&backend)==PMKB_OK);
    CHECK(!router.store.surface.has_dirty);
    pmkb_store_router_dismiss(&router);
}
/* D7l: a failed present must not clear dirty during a repeated failure. */
static void verify_repeated_present_failure(void) {
    PMKBStorePassiveRouter router;
    pmkb_store_router_init(&router);
    CHECK(pmkb_store_router_preview(&router,320,480,&catalog,0)
          == PMKB_STORE_PAINT_OK);
    D7bBackend mock={0};
    PMKBBackend backend={&mock,d7b_present};
    mock.fail=true;
    for (unsigned attempt=0;attempt<3;attempt++) {
        unsigned before=mock.calls;
        CHECK(pmkb_store_router_present(&router,&backend)==PMKB_INVALID);
        CHECK(mock.calls>before);
        CHECK(router.store.surface.has_dirty);
        CHECK(pmkb_store_owner_pixel_bytes(&router.store)==153600u);
    }
    mock.fail=false;
    CHECK(pmkb_store_router_present(&router,&backend)==PMKB_OK);
    CHECK(!router.store.surface.has_dirty);
    CHECK(pmkb_store_router_present(&router,&backend)==PMKB_NO_CHANGE);
    pmkb_store_router_dismiss(&router);
}
/* D7m: complete passive Store presentation lifecycle with one backend. */
static void verify_full_present_lifecycle(void) {
    PMKBStorePassiveRouter router;
    pmkb_store_router_init(&router);
    D7bBackend mock={0};
    PMKBBackend backend={&mock,d7b_present};
    CHECK(pmkb_store_router_preview(&router,320,480,&catalog,0)
          == PMKB_STORE_PAINT_OK);
    mock.fail=true;
    CHECK(pmkb_store_router_present(&router,&backend)==PMKB_INVALID);
    CHECK(router.store.surface.has_dirty);
    mock.fail=false;
    CHECK(pmkb_store_router_present(&router,&backend)==PMKB_OK);
    CHECK(pmkb_store_router_present(&router,&backend)==PMKB_NO_CHANGE);
    pmkb_store_router_dismiss(&router);
    CHECK(pmkb_store_owner_pixel_bytes(&router.store)==0u);
    CHECK(pmkb_store_router_present(&router,&backend)==PMKB_INVALID);
    CHECK(pmkb_store_router_preview(&router,320,480,&catalog,0)
          == PMKB_STORE_PAINT_OK);
    CHECK(pmkb_store_router_present(&router,&backend)==PMKB_OK);
    CHECK(pmkb_store_router_shutdown(&router,true)==PMKB_NO_CHANGE);
    CHECK(pmkb_store_owner_pixel_bytes(&router.store)==0u);
}
/* D7n: injected transport tracks submissions vs acknowledgements. */
static void verify_eink_sim_transport(void) {
    PMKBStorePassiveRouter router;
    pmkb_store_router_init(&router);
    CHECK(pmkb_store_router_preview(&router,320,480,&catalog,0)
          == PMKB_STORE_PAINT_OK);
    D7bBackend transport={0};
    PMKBStoreEinkSim sim={&transport,d7b_present,0,0};
    PMKBBackend backend=pmkb_store_eink_sim_backend(&sim);
    transport.fail=true;
    CHECK(pmkb_store_router_present(&router,&backend)==PMKB_INVALID);
    CHECK(sim.submissions>=1u && sim.acknowledgements==0u);
    CHECK(router.store.surface.has_dirty);
    transport.fail=false;
    CHECK(pmkb_store_router_present(&router,&backend)==PMKB_OK);
    CHECK(sim.acknowledgements>=1u);
    CHECK(sim.submissions==transport.calls);
    CHECK(!router.store.surface.has_dirty);
    unsigned before=sim.submissions;
    CHECK(pmkb_store_router_present(&router,&backend)==PMKB_NO_CHANGE);
    CHECK(sim.submissions==before);
    pmkb_store_router_dismiss(&router);
}
/* D7o: acceptance, stale marker rejection and completion are distinct. */
static void verify_eink_pending_marker(void) {
    PMKBStoreEinkPending state={0};
    unsigned first=0,second=0;
    CHECK(pmkb_store_eink_begin(&state,&first)==PMKB_OK);
    CHECK(first!=0 && state.pending);
    CHECK(state.completions==0u);
    CHECK(pmkb_store_eink_begin(&state,&second)==PMKB_LIMIT);
    CHECK(pmkb_store_eink_complete(&state,first+1u,true)==PMKB_INVALID);
    CHECK(state.pending && state.completions==0u);
    CHECK(pmkb_store_eink_complete(&state,first,false)==PMKB_INVALID);
    CHECK(!state.pending && state.failures==1u);
    CHECK(pmkb_store_eink_begin(&state,&second)==PMKB_OK);
    CHECK(second!=first && state.pending);
    CHECK(pmkb_store_eink_complete(&state,second,true)==PMKB_OK);
    CHECK(!state.pending && state.completions==1u);
    CHECK(pmkb_store_eink_complete(&state,second,true)==PMKB_INVALID);
}
/* D7p: submission retains dirty; completion clears only unchanged pixels. */
static void verify_async_dirty_contract(void) {
    PMKBStorePassiveRouter router;
    pmkb_store_router_init(&router);
    CHECK(pmkb_store_router_preview(&router,320,480,&catalog,0)
          == PMKB_STORE_PAINT_OK);
    PMKBSurface *surface=&router.store.surface;
    PMKBStoreEinkAsync state={0};
    unsigned first=0,second=0,third=0;
    CHECK(pmkb_store_eink_async_submit(&state,surface,&first)==PMKB_OK);
    CHECK(surface->has_dirty);
    CHECK(pmkb_store_eink_async_submit(&state,surface,&second)==PMKB_LIMIT);
    CHECK(pmkb_store_eink_async_complete(&state,surface,first+1u,true)==PMKB_INVALID);
    CHECK(surface->has_dirty && state.markers.pending);
    CHECK(pmkb_store_eink_async_complete(&state,surface,first,false)==PMKB_INVALID);
    CHECK(surface->has_dirty);
    CHECK(pmkb_store_eink_async_submit(&state,surface,&second)==PMKB_OK);
    pmkb_surface_rect(surface,(PMKBRect){0,0,3,3},127);
    CHECK(pmkb_store_eink_async_complete(&state,surface,second,true)==PMKB_OK);
    CHECK(surface->has_dirty);
    CHECK(pmkb_store_eink_async_submit(&state,surface,&third)==PMKB_OK);
    CHECK(pmkb_store_eink_async_complete(&state,surface,third,true)==PMKB_OK);
    CHECK(!surface->has_dirty);
    CHECK(pmkb_store_eink_async_submit(&state,surface,&third)==PMKB_NO_CHANGE);
    pmkb_store_router_dismiss(&router);
}
/* D7q: cancel before dismissal, then reject a delayed completion. */
static void verify_async_cancel_before_dismiss(void) {
    PMKBStorePassiveRouter router;
    pmkb_store_router_init(&router);
    CHECK(pmkb_store_router_preview(&router,320,480,&catalog,0)
          == PMKB_STORE_PAINT_OK);
    PMKBStoreEinkAsync state={0};
    unsigned stale=0,fresh=0;
    CHECK(pmkb_store_eink_async_submit(
        &state,&router.store.surface,&stale)==PMKB_OK);
    CHECK(router.store.surface.has_dirty);
    CHECK(pmkb_store_eink_async_cancel(&state)==PMKB_OK);
    pmkb_store_router_dismiss(&router);
    CHECK(pmkb_store_owner_pixel_bytes(&router.store)==0u);
    CHECK(pmkb_store_eink_async_complete(&state,NULL,stale,true)==PMKB_INVALID);
    CHECK(pmkb_store_router_preview(&router,320,480,&catalog,0)
          == PMKB_STORE_PAINT_OK);
    CHECK(router.store.surface.has_dirty);
    CHECK(pmkb_store_eink_async_submit(
        &state,&router.store.surface,&fresh)==PMKB_OK);
    CHECK(fresh!=stale);
    CHECK(pmkb_store_eink_async_complete(
        &state,&router.store.surface,stale,true)==PMKB_INVALID);
    CHECK(router.store.surface.has_dirty && state.markers.pending);
    CHECK(pmkb_store_eink_async_complete(
        &state,&router.store.surface,fresh,true)==PMKB_OK);
    CHECK(!router.store.surface.has_dirty);
    CHECK(pmkb_store_eink_async_cancel(&state)==PMKB_NO_CHANGE);
    pmkb_store_router_dismiss(&router);
}
/* D7r: lifecycle owner cancels before resize, redraw and shutdown. */
static void verify_async_lifecycle_owner(void) {
    PMKBStoreEinkLifecycle owner={0};
    pmkb_store_eink_lifecycle_init(&owner);
    unsigned old=0,next=0;
    CHECK(pmkb_store_eink_lifecycle_preview(&owner,320,480,&catalog,0)
          == PMKB_STORE_PAINT_OK);
    CHECK(pmkb_store_eink_lifecycle_submit(&owner,&old)==PMKB_OK);
    CHECK(owner.async.markers.pending);
    CHECK(pmkb_store_eink_lifecycle_preview(&owner,1080,1440,&catalog,0)
          == PMKB_STORE_PAINT_OK);
    CHECK(!owner.async.markers.pending);
    CHECK(pmkb_store_eink_lifecycle_complete(&owner,old,true)==PMKB_INVALID);
    CHECK(owner.router.store.surface.has_dirty);
    CHECK(pmkb_store_eink_lifecycle_submit(&owner,&next)==PMKB_OK);
    CHECK(next!=old);
    pmkb_store_eink_lifecycle_dismiss(&owner);
    CHECK(!owner.async.markers.pending);
    CHECK(pmkb_store_owner_pixel_bytes(&owner.router.store)==0u);
    CHECK(pmkb_store_eink_lifecycle_complete(&owner,next,true)==PMKB_INVALID);
    CHECK(pmkb_store_eink_lifecycle_preview(&owner,320,480,&catalog,0)
          == PMKB_STORE_PAINT_OK);
    CHECK(pmkb_store_eink_lifecycle_submit(&owner,&next)==PMKB_OK);
    CHECK(pmkb_store_eink_lifecycle_complete(&owner,next,true)==PMKB_OK);
    CHECK(!owner.router.store.surface.has_dirty);
    CHECK(pmkb_store_eink_lifecycle_shutdown(&owner,true)==PMKB_NO_CHANGE);
    CHECK(pmkb_store_owner_pixel_bytes(&owner.router.store)==0u);
}
/* D7s: lifecycle reset must not reuse a canceled marker. */
static void verify_async_reset_stale_marker(void) {
    PMKBStoreEinkLifecycle owner={0};
    pmkb_store_eink_lifecycle_init(&owner);
    unsigned stale=0,fresh=0;
    CHECK(pmkb_store_eink_lifecycle_preview(&owner,320,480,&catalog,0)
          == PMKB_STORE_PAINT_OK);
    CHECK(pmkb_store_eink_lifecycle_submit(&owner,&stale)==PMKB_OK);
    pmkb_store_eink_lifecycle_reset(&owner);
    CHECK(!owner.async.markers.pending);
    CHECK(pmkb_store_owner_pixel_bytes(&owner.router.store)==0u);
    CHECK(pmkb_store_eink_lifecycle_complete(&owner,stale,true)==PMKB_INVALID);
    CHECK(pmkb_store_eink_lifecycle_preview(&owner,320,480,&catalog,0)
          == PMKB_STORE_PAINT_OK);
    CHECK(pmkb_store_eink_lifecycle_submit(&owner,&fresh)==PMKB_OK);
    CHECK(fresh!=stale);
    CHECK(pmkb_store_eink_lifecycle_complete(&owner,stale,true)==PMKB_INVALID);
    CHECK(owner.async.markers.pending && owner.router.store.surface.has_dirty);
    CHECK(pmkb_store_eink_lifecycle_complete(&owner,fresh,true)==PMKB_OK);
    CHECK(!owner.router.store.surface.has_dirty);
    pmkb_store_eink_lifecycle_reset(&owner);
}
/* D7t: marker exhaustion must fail closed without wraparound. */
static void verify_eink_marker_exhaustion(void) {
    PMKBStoreEinkPending state={0};
    unsigned marker=0;
    state.next_marker=(unsigned)-2;
    CHECK(pmkb_store_eink_begin(&state,&marker)==PMKB_OK);
    CHECK(marker==(unsigned)-1 && state.pending);
    CHECK(pmkb_store_eink_begin(&state,&marker)==PMKB_LIMIT);
    CHECK(pmkb_store_eink_complete(&state,marker,true)==PMKB_OK);
    CHECK(!state.pending);
    CHECK(pmkb_store_eink_begin(&state,&marker)==PMKB_LIMIT);
    CHECK(state.next_marker==(unsigned)-1);
    CHECK(!state.pending);
    CHECK(pmkb_store_eink_complete(&state,marker,true)==PMKB_INVALID);

    PMKBStorePassiveRouter router;
    pmkb_store_router_init(&router);
    CHECK(pmkb_store_router_preview(&router,320,480,&catalog,0)
          == PMKB_STORE_PAINT_OK);
    PMKBStoreEinkAsync async={0};
    async.markers.next_marker=(unsigned)-1;
    unsigned refused=123u;
    CHECK(pmkb_store_eink_async_submit(
        &async,&router.store.surface,&refused)==PMKB_LIMIT);
    CHECK(refused==123u);
    CHECK(router.store.surface.has_dirty);
    CHECK(!async.markers.pending);
    pmkb_store_router_dismiss(&router);
}
/* D7u: diagnostic counters saturate while markers still complete. */
static void verify_eink_counter_saturation(void) {
    PMKBStoreEinkPending state={0};
    unsigned marker=0;
    state.completions=(unsigned)-2;
    state.failures=(unsigned)-2;
    CHECK(pmkb_store_eink_begin(&state,&marker)==PMKB_OK);
    CHECK(pmkb_store_eink_complete(&state,marker,true)==PMKB_OK);
    CHECK(state.completions==(unsigned)-1);
    CHECK(pmkb_store_eink_begin(&state,&marker)==PMKB_OK);
    CHECK(pmkb_store_eink_complete(&state,marker,true)==PMKB_OK);
    CHECK(state.completions==(unsigned)-1);
    CHECK(pmkb_store_eink_begin(&state,&marker)==PMKB_OK);
    CHECK(pmkb_store_eink_complete(&state,marker,false)==PMKB_INVALID);
    CHECK(state.failures==(unsigned)-1);
    CHECK(pmkb_store_eink_begin(&state,&marker)==PMKB_OK);
    CHECK(pmkb_store_eink_complete(&state,marker,false)==PMKB_INVALID);
    CHECK(state.failures==(unsigned)-1);
    CHECK(!state.pending);
}
/* D7v: stale/duplicate completions must not affect counters or dirty. */
static void verify_async_completion_invariants(void) {
    PMKBStorePassiveRouter router;
    pmkb_store_router_init(&router);
    CHECK(pmkb_store_router_preview(&router,320,480,&catalog,0)
          == PMKB_STORE_PAINT_OK);
    PMKBStoreEinkAsync state={0};
    unsigned first=0,second=0;
    PMKBSurface *surface=&router.store.surface;
    CHECK(pmkb_store_eink_async_submit(&state,surface,&first)==PMKB_OK);
    CHECK(pmkb_store_eink_async_complete(&state,surface,0u,true)==PMKB_INVALID);
    CHECK(pmkb_store_eink_async_complete(&state,surface,first+1u,true)==PMKB_INVALID);
    CHECK(state.markers.pending && surface->has_dirty);
    CHECK(state.markers.completions==0u && state.markers.failures==0u);
    CHECK(pmkb_store_eink_async_complete(&state,surface,first,true)==PMKB_OK);
    CHECK(!surface->has_dirty && state.markers.completions==1u);
    CHECK(pmkb_store_eink_async_complete(&state,surface,first,false)==PMKB_INVALID);
    CHECK(state.markers.completions==1u && state.markers.failures==0u);
    pmkb_surface_rect(surface,(PMKBRect){0,0,5,5},127);
    CHECK(surface->has_dirty);
    CHECK(pmkb_store_eink_async_submit(&state,surface,&second)==PMKB_OK);
    CHECK(second!=first);
    CHECK(pmkb_store_eink_async_complete(&state,surface,first,true)==PMKB_INVALID);
    CHECK(state.markers.pending && surface->has_dirty);
    CHECK(pmkb_store_eink_async_complete(&state,surface,second,false)==PMKB_INVALID);
    CHECK(surface->has_dirty && state.markers.failures==1u);
    CHECK(state.markers.completions==1u);
    pmkb_store_router_dismiss(&router);
}
/* D7w: two edits during pending refresh require a second submission. */
static void verify_async_edits_during_pending(void) {
    PMKBStorePassiveRouter router;
    pmkb_store_router_init(&router);
    CHECK(pmkb_store_router_preview(&router,320,480,&catalog,0)
          == PMKB_STORE_PAINT_OK);
    PMKBSurface *surface=&router.store.surface;
    PMKBStoreEinkAsync async={0};
    unsigned original=0,retry=0;
    CHECK(pmkb_store_eink_async_submit(&async,surface,&original)==PMKB_OK);
    CHECK(surface->has_dirty);
    pmkb_surface_rect(surface,(PMKBRect){0,0,4,4},123);
    pmkb_surface_rect(surface,(PMKBRect){310,470,4,4},231);
    CHECK(surface->has_dirty);
    CHECK(pmkb_store_eink_async_submit(&async,surface,&retry)==PMKB_LIMIT);
    CHECK(pmkb_store_eink_async_complete(&async,surface,original,true)==PMKB_OK);
    CHECK(surface->has_dirty);
    CHECK(async.markers.completions==1u);
    CHECK(pmkb_store_eink_async_submit(&async,surface,&retry)==PMKB_OK);
    CHECK(retry!=original);
    CHECK(pmkb_store_eink_async_complete(&async,surface,retry,true)==PMKB_OK);
    CHECK(!surface->has_dirty);
    CHECK(pmkb_store_eink_async_submit(&async,surface,&retry)==PMKB_NO_CHANGE);
    pmkb_store_router_dismiss(&router);
}
/* D7x: cancelling a refresh after edits must preserve dirty pixels. */
static void verify_async_cancel_after_edits(void) {
    PMKBStorePassiveRouter router;
    pmkb_store_router_init(&router);
    CHECK(pmkb_store_router_preview(&router,320,480,&catalog,0)
          == PMKB_STORE_PAINT_OK);
    PMKBSurface *surface=&router.store.surface;
    PMKBStoreEinkAsync async={0};
    unsigned cancelled=0,retry=0;
    CHECK(pmkb_store_eink_async_submit(&async,surface,&cancelled)==PMKB_OK);
    pmkb_surface_rect(surface,(PMKBRect){0,0,7,7},115);
    CHECK(surface->has_dirty);
    CHECK(pmkb_store_eink_async_cancel(&async)==PMKB_OK);
    CHECK(!async.markers.pending && surface->has_dirty);
    CHECK(pmkb_store_eink_async_complete(&async,surface,cancelled,true)
          == PMKB_INVALID);
    CHECK(surface->has_dirty && async.markers.completions==0u);
    CHECK(pmkb_store_eink_async_submit(&async,surface,&retry)==PMKB_OK);
    CHECK(retry!=cancelled);
    CHECK(pmkb_store_eink_async_complete(&async,surface,cancelled,true)
          == PMKB_INVALID);
    CHECK(surface->has_dirty && async.markers.pending);
    CHECK(pmkb_store_eink_async_complete(&async,surface,retry,true)==PMKB_OK);
    CHECK(!surface->has_dirty);
    pmkb_store_router_dismiss(&router);
}
/* D7y: app transitions must cancel pending Store updates first. */
static void verify_async_transition_to_notes(void) {
    PMKBStoreEinkLifecycle owner={0};
    pmkb_store_eink_lifecycle_init(&owner);
    unsigned stale=0, again=0;
    CHECK(pmkb_store_eink_lifecycle_preview(&owner,320,480,&catalog,0)
          == PMKB_STORE_PAINT_OK);
    CHECK(pmkb_store_eink_lifecycle_submit(&owner,&stale)==PMKB_OK);
    CHECK(owner.async.markers.pending);
    CHECK(pmkb_store_eink_lifecycle_launch_app(
          &owner,PMKB_APP_NOTES,320,480)==PMKB_OK);
    CHECK(!owner.async.markers.pending);
    CHECK(pmkb_store_owner_pixel_bytes(&owner.router.store)==0u);
    CHECK(owner.router.host.active==PMKB_APP_NOTES);
    CHECK(pmkb_store_eink_lifecycle_complete(&owner,stale,true)==PMKB_INVALID);
    CHECK(pmkb_store_eink_lifecycle_submit(&owner,&again)==PMKB_INVALID);
    PMKBUI *notes=(PMKBUI *)owner.router.host.instance;
    CHECK(notes!=NULL);
    if (!notes) {
        pmkb_store_eink_lifecycle_reset(&owner);
        return;
    }
    notes->notebook.count=1;
    CHECK(pmkb_store_eink_lifecycle_preview(&owner,320,480,&catalog,0)
          == PMKB_STORE_PAINT_OK);
    CHECK(pmkb_store_eink_lifecycle_submit(&owner,&again)==PMKB_OK);
    CHECK(again!=stale);
    CHECK(pmkb_store_eink_lifecycle_close_app(&owner,false)==PMKB_UNSAVED);
    CHECK(!owner.async.markers.pending);
    CHECK(pmkb_store_owner_pixel_bytes(&owner.router.store)==0u);
    CHECK(owner.router.host.active==PMKB_APP_NOTES);
    CHECK(owner.router.host.instance==notes && notes->notebook.count==1);
    CHECK(pmkb_store_eink_lifecycle_complete(&owner,again,true)==PMKB_INVALID);
    CHECK(pmkb_store_eink_lifecycle_close_app(&owner,true)==PMKB_OK);
    CHECK(owner.router.host.active==PMKB_APP_NONE &&
          owner.router.host.instance==NULL);
}
static void verify_async_transition_to_calculator(void) {
    PMKBStoreEinkLifecycle owner={0};
    pmkb_store_eink_lifecycle_init(&owner);
    unsigned stale=0;
    CHECK(pmkb_store_eink_lifecycle_preview(&owner,320,480,&catalog,0)
          == PMKB_STORE_PAINT_OK);
    CHECK(pmkb_store_eink_lifecycle_submit(&owner,&stale)==PMKB_OK);
    CHECK(pmkb_store_eink_lifecycle_launch_app(
          &owner,PMKB_APP_CALCULATOR,320,480)==PMKB_OK);
    CHECK(!owner.async.markers.pending);
    CHECK(pmkb_store_owner_pixel_bytes(&owner.router.store)==0u);
    CHECK(owner.router.host.active==PMKB_APP_CALCULATOR);
    CHECK(pmkb_store_eink_lifecycle_complete(&owner,stale,true)==PMKB_INVALID);
    PMKBSurface *calc_screen=pmkb_app_host_screen(&owner.router.host);
    CHECK(calc_screen!=NULL && calc_screen->gray!=NULL);
    CHECK(pmkb_store_eink_lifecycle_close_app(&owner,false)==PMKB_OK);
    CHECK(owner.router.host.active==PMKB_APP_NONE);
    CHECK(owner.router.host.instance==NULL);
    CHECK(pmkb_store_eink_lifecycle_launch_app(
          &owner,PMKB_APP_STORE,320,480)==PMKB_NOT_FOUND);
    CHECK(owner.router.host.active==PMKB_APP_NONE);
}
/* D7z: a direct Launcher change must invalidate any pending Store marker
 * before an old refresh completion can consume the Store dirty region. */
static void verify_async_external_launch_before_complete(void) {
    PMKBStoreEinkLifecycle owner={0};
    pmkb_store_eink_lifecycle_init(&owner);
    unsigned stale=0, fresh=0;
    CHECK(pmkb_store_eink_lifecycle_preview(&owner,320,480,&catalog,0)
          == PMKB_STORE_PAINT_OK);
    CHECK(pmkb_store_eink_lifecycle_submit(&owner,&stale)==PMKB_OK);
    CHECK(owner.async.markers.pending);
    /* Deliberately bypass pmkb_store_eink_lifecycle_launch_app. */
    CHECK(pmkb_app_host_launch(&owner.router.host,PMKB_APP_CALCULATOR,320,480)
          == PMKB_OK);
    PMKBSurface *calc_screen=pmkb_app_host_screen(&owner.router.host);
    CHECK(calc_screen!=NULL && calc_screen->gray!=NULL);
    CHECK(pmkb_store_eink_lifecycle_complete(&owner,stale,true)==PMKB_INVALID);
    CHECK(!owner.async.markers.pending);
    CHECK(owner.async.markers.completions==0u);
    CHECK(pmkb_store_owner_pixel_bytes(&owner.router.store)==0u);
    CHECK(owner.router.host.active==PMKB_APP_CALCULATOR);
    CHECK(pmkb_app_host_screen(&owner.router.host)==calc_screen);
    CHECK(pmkb_store_eink_lifecycle_preview(&owner,320,480,&catalog,0)
          == PMKB_STORE_PAINT_OK);
    CHECK(pmkb_store_eink_lifecycle_submit(&owner,&fresh)==PMKB_OK);
    CHECK(fresh!=stale);
    CHECK(pmkb_store_eink_lifecycle_complete(&owner,stale,true)==PMKB_INVALID);
    CHECK(owner.async.markers.pending && owner.router.store.surface.has_dirty);
    CHECK(pmkb_store_eink_lifecycle_complete(&owner,fresh,true)==PMKB_OK);
    CHECK(!owner.router.store.surface.has_dirty);
    CHECK(pmkb_store_eink_lifecycle_close_app(&owner,true)==PMKB_OK);
    CHECK(pmkb_store_owner_pixel_bytes(&owner.router.store)==0u);
}
static void verify_async_external_launch_before_submit(void) {
    PMKBStoreEinkLifecycle owner={0};
    pmkb_store_eink_lifecycle_init(&owner);
    unsigned refused=77u;
    CHECK(pmkb_store_eink_lifecycle_preview(&owner,320,480,&catalog,0)
          == PMKB_STORE_PAINT_OK);
    /* Direct host launch invalidates the preview even without a marker. */
    CHECK(pmkb_app_host_launch(&owner.router.host,PMKB_APP_NOTES,320,480)
          == PMKB_OK);
    CHECK(pmkb_store_eink_lifecycle_submit(&owner,&refused)==PMKB_INVALID);
    CHECK(refused==77u);
    CHECK(!owner.async.markers.pending);
    CHECK(pmkb_store_owner_pixel_bytes(&owner.router.store)==0u);
    CHECK(owner.router.host.active==PMKB_APP_NOTES);
    CHECK(pmkb_store_eink_lifecycle_close_app(&owner,true)==PMKB_OK);
}
static void verify_async_external_store_dismiss(void) {
    PMKBStoreEinkLifecycle owner={0};
    pmkb_store_eink_lifecycle_init(&owner);
    unsigned stale=0;
    CHECK(pmkb_store_eink_lifecycle_preview(&owner,320,480,&catalog,0)
          == PMKB_STORE_PAINT_OK);
    CHECK(pmkb_store_eink_lifecycle_submit(&owner,&stale)==PMKB_OK);
    /* Direct router dismissal bypasses the async cancellation contract. */
    pmkb_store_router_dismiss(&owner.router);
    CHECK(pmkb_store_owner_pixel_bytes(&owner.router.store)==0u);
    CHECK(pmkb_store_eink_lifecycle_complete(&owner,stale,true)==PMKB_INVALID);
    CHECK(!owner.async.markers.pending);
    CHECK(owner.async.markers.completions==0u);
    CHECK(pmkb_store_eink_lifecycle_shutdown(&owner,true)==PMKB_NO_CHANGE);
}
static void verify_router_shutdown(void) {
    PMKBStorePassiveRouter router;
    pmkb_store_router_init(&router);
    CHECK(pmkb_store_router_launch_app(&router, PMKB_APP_NOTES, 320, 480)
          == PMKB_OK);
    PMKBUI *notes = (PMKBUI *)router.host.instance;
    CHECK(notes != NULL);
    if (!notes) return;
    notes->notebook.count = 1;
    CHECK(pmkb_store_router_preview(&router, 320, 480, &catalog, 0)
          == PMKB_STORE_PAINT_OK);
    CHECK(pmkb_store_router_shutdown(&router, false) == PMKB_UNSAVED);
    CHECK(router.host.active == PMKB_APP_NOTES && router.host.instance == notes);
    CHECK(notes->notebook.count == 1);
    CHECK(pmkb_store_owner_pixel_bytes(&router.store) == 0u);
    CHECK(pmkb_store_router_shutdown(&router, true) == PMKB_OK);
    CHECK(router.host.active == PMKB_APP_NONE && router.host.instance == NULL);
    CHECK(pmkb_store_router_shutdown(&router, false) == PMKB_NO_CHANGE);
    CHECK(pmkb_store_owner_pixel_bytes(&router.store) == 0u);
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
    verify_router_shutdown();
    verify_router_presentation();
    verify_split_present_failure();
    verify_reentrant_present();
    verify_backend_absent();
    verify_stale_host_before_present();
    verify_dismiss_before_present();
    verify_resize_before_present();
    verify_resize_present_retry();
    verify_failed_present_then_dismiss();
    verify_repeated_present_failure();
    verify_full_present_lifecycle();
    verify_eink_sim_transport();
    verify_eink_pending_marker();
    verify_async_dirty_contract();
    verify_async_cancel_before_dismiss();
    verify_async_lifecycle_owner();
    verify_async_reset_stale_marker();
    verify_eink_marker_exhaustion();
    verify_eink_counter_saturation();
    verify_async_completion_invariants();
    verify_async_edits_during_pending();
    verify_async_cancel_after_edits();
    verify_async_transition_to_notes();
    verify_async_transition_to_calculator();
    verify_async_external_launch_before_complete();
    verify_async_external_launch_before_submit();
    verify_async_external_store_dismiss();
    CHECK(note_inits==note_frees && calc_inits==calc_frees);
    if(fails)return 1;
    printf("PMKB REAL LAUNCHER ISOLATION: %u assertions PASS, 0 FAIL\n",checks);
    return 0;
}
