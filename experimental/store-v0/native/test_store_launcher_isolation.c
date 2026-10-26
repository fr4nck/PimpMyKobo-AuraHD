/* L06-D6c: real pinned launcher bridge, Notes/Calculator lifecycle DOUBLES.
 * Store uses a dedicated synthetic surface. No app route is activated. */
#include "pmkb_launcher_bridge.h"
#include "pmkb_store_ui_preview.h"
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
int main(void) {
    memset(&catalog,0,sizeof(catalog));
    catalog.count=1;
    (void)strcpy(catalog.items[0].id,"org.pmkb.preview");
    (void)strcpy(catalog.items[0].label,"Store preview");
    (void)strcpy(catalog.items[0].version,"0.1.0");
    verify_reserved();
    verify_notes_isolation();
    verify_calculator_isolation();
    CHECK(note_inits==note_frees && calc_inits==calc_frees);
    if(fails)return 1;
    printf("PMKB REAL LAUNCHER ISOLATION: %u assertions PASS, 0 FAIL\n",checks);
    return 0;
}
