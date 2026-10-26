/* One active app, no unauthorized exit from unsaved Notes, HAL retries. */
#include "../pmkb_launcher_bridge.h"
#include <math.h>
#include <stdio.h>
#include <string.h>

#define UTC "2026-10-19T18:00:00.000Z"
static unsigned passed=0,groups=0;
#define CHECK(c) do{passed++;if(!(c)){ \
    fprintf(stderr,"BRIDGE FAIL %s:%d: %s\n",__FILE__,__LINE__,#c);return 1; \
}}while(0)
typedef struct { int calls; bool fail; PMKBRect last; } FakeBackend;
static PMKBStatus present(void *context,const uint8_t *data,
                           int width,int height,PMKBRect dirty){
    FakeBackend *mock=(FakeBackend*)context;
    if(!data||width<240||height<320)return PMKB_INVALID;
    mock->calls++;mock->last=dirty;
    return mock->fail?PMKB_INVALID:PMKB_OK;
}
static int catalog(void){
    const PMKBAppInfo *notes=pmkb_app_info(PMKB_APP_NOTES);
    const PMKBAppInfo *calc=pmkb_app_info(PMKB_APP_CALCULATOR);
    const PMKBAppInfo *store=pmkb_app_info(PMKB_APP_STORE);
    CHECK(notes&&calc&&store);
    CHECK(notes->runnable&&calc->runnable&&!store->runnable);
    CHECK(strcmp(notes->id,"notes")==0);
    CHECK(strcmp(calc->id,"calculator")==0);
    CHECK(strcmp(store->id,"store")==0);
    CHECK(pmkb_app_info(PMKB_APP_NONE)==NULL);
    CHECK(pmkb_app_info((PMKBAppId)99)==NULL);
    groups++;return 0;
}
static int safe_lifecycle(void){
    PMKBAppHost host;pmkb_app_host_init(&host);
    CHECK(host.generation==0u);
    CHECK(pmkb_app_host_launch(&host,PMKB_APP_STORE,320,480)==PMKB_NOT_FOUND);
    CHECK(host.instance==NULL && host.active==PMKB_APP_NONE);
    CHECK(host.generation==0u);
    CHECK(pmkb_app_host_launch(&host,PMKB_APP_NOTES,320,480)==PMKB_OK);
    CHECK(host.active==PMKB_APP_NOTES && host.instance);
    CHECK(host.generation==1u);
    CHECK(pmkb_app_host_launch(&host,PMKB_APP_CALCULATOR,320,480)==PMKB_INVALID);
    CHECK(pmkb_app_host_event(&host,
          (PMKBEvent){.kind=PMKB_EVENT_TAP,.x=14,.y=14},UTC)==PMKB_OK);
    PMKBUI *notes=(PMKBUI*)host.instance;
    CHECK(notes->notebook.count==1);
    CHECK(pmkb_app_host_close(&host,false)==PMKB_UNSAVED);
    CHECK(host.active==PMKB_APP_NOTES && host.instance==notes);
    CHECK(host.generation==1u);
    CHECK(pmkb_app_host_event(&host,(PMKBEvent){.kind=PMKB_EVENT_TEXT,
          .text="Saisie gard\xc3\xa9""e"},UTC)==PMKB_OK);
    CHECK(strcmp(notes->notebook.items[0]->title.data,"Saisie gard\xc3\xa9""e")==0);
    FakeBackend mock={0};PMKBBackend adapter={.context=&mock,.present=present};
    mock.fail=true;
    CHECK(pmkb_app_host_present(&host,&adapter)==PMKB_INVALID);
    CHECK(notes->screen.has_dirty && mock.calls==1);
    mock.fail=false;
    CHECK(pmkb_app_host_present(&host,&adapter)==PMKB_OK);
    CHECK(!notes->screen.has_dirty && mock.calls==2);
    CHECK(pmkb_app_host_present(&host,&adapter)==PMKB_NO_CHANGE);
    CHECK(pmkb_app_host_close(&host,true)==PMKB_OK);
    CHECK(host.active==PMKB_APP_NONE&&host.instance==NULL);
    CHECK(host.generation==2u);
    CHECK(pmkb_app_host_event(&host,
          (PMKBEvent){.kind=PMKB_EVENT_ENTER},UTC)==PMKB_NOT_FOUND);
    CHECK(pmkb_app_host_close(&host,false)==PMKB_NO_CHANGE);
    CHECK(host.generation==2u);
    groups++;return 0;
}
static int calculator_via_launcher(void){
    PMKBAppHost host;pmkb_app_host_init(&host);
    CHECK(pmkb_app_host_launch(&host,PMKB_APP_CALCULATOR,320,480)==PMKB_OK);
    PMKBCalcUI *calc=(PMKBCalcUI*)host.instance;
    CHECK(calc->keyboard.page==PMKB_KB_SCIENTIFIC);
    CHECK(pmkb_app_host_event(&host,
          (PMKBEvent){.kind=PMKB_EVENT_TEXT,.text="sin(30)"},NULL)==PMKB_OK);
    CHECK(pmkb_app_host_event(&host,
          (PMKBEvent){.kind=PMKB_EVENT_ENTER},NULL)==PMKB_OK);
    CHECK(fabs(calc->ans-.5)<1e-12&&calc->history_count==1);
    FakeBackend mock={0};PMKBBackend adapter={.context=&mock,.present=present};
    CHECK(pmkb_app_host_present(&host,&adapter)==PMKB_OK);
    CHECK(mock.calls==1&&!calc->screen.has_dirty);
    CHECK(pmkb_app_host_close(&host,false)==PMKB_OK);
    CHECK(host.instance==NULL);
    CHECK(pmkb_app_host_launch(&host,PMKB_APP_NOTES,1080,1440)==PMKB_OK);
    CHECK(((PMKBUI*)host.instance)->notebook.count==0);
    CHECK(pmkb_app_host_close(&host,false)==PMKB_OK);
    groups++;return 0;
}
static int font_and_clipping(void){
    PMKBSurface a={0},b={0}; PMKBRect dirty={0};
    CHECK(pmkb_surface_glyph_supported(0xe9));
    CHECK(pmkb_surface_glyph_supported(0x03c0));
    CHECK(pmkb_surface_glyph_supported(0x221a));
    CHECK(pmkb_surface_glyph_supported(0x00e7));
    CHECK(pmkb_surface_glyph_supported(0x0301));
    CHECK(!pmkb_surface_glyph_supported(0x1f600));
    CHECK(pmkb_surface_init(&a,320,480)==PMKB_OK);
    CHECK(pmkb_surface_init(&b,320,480)==PMKB_OK);
    CHECK(pmkb_surface_take_dirty(&a,&dirty));
    CHECK(pmkb_surface_take_dirty(&b,&dirty));
    pmkb_surface_text_box(&a,10,10,"e",0,40,20);
    pmkb_surface_text_box(&b,10,10,"\xc3\xa9",0,40,20);
    CHECK(memcmp(a.gray,b.gray,320u*480u)!=0);
    pmkb_surface_rect(&a,(PMKBRect){0,0,320,480},255);
    pmkb_surface_rect(&b,(PMKBRect){0,0,320,480},255);
    CHECK(pmkb_surface_take_dirty(&a,&dirty));
    CHECK(pmkb_surface_take_dirty(&b,&dirty));
    pmkb_surface_text_box(&a,10,10,"?",0,40,20);
    pmkb_surface_text_box(&b,10,10,"\xcf\x80",0,40,20);
    CHECK(memcmp(a.gray,b.gray,320u*480u)!=0);
    pmkb_surface_rect(&a,(PMKBRect){0,0,320,480},255);
    CHECK(pmkb_surface_take_dirty(&a,&dirty));
    pmkb_surface_text_box(&a,10,10,"\xe2\x88\x9a",0,30,20);
    CHECK(pmkb_surface_take_dirty(&a,&dirty));
    CHECK(dirty.x>=10 && dirty.y>=10 && dirty.y+dirty.h<=30);
    pmkb_surface_rect(&a,(PMKBRect){0,0,320,480},255);
    CHECK(pmkb_surface_take_dirty(&a,&dirty));
    pmkb_surface_text_box(&a,10,10,"123456789",0,12,20);
    CHECK(pmkb_surface_take_dirty(&a,&dirty));
    CHECK(dirty.x>=10 && dirty.x+dirty.w<=22);
    CHECK(dirty.y+dirty.h<=30);
    pmkb_surface_free(&a);pmkb_surface_free(&b);
    groups++;return 0;
}
int main(void){
    if(catalog()||safe_lifecycle()||calculator_via_launcher()||
       font_and_clipping())return 1;
    printf("PMKB LAUNCHER/RENDER: %u assertions PASS, %u groups PASS, 0 FAIL\n",
           passed,groups);
    return 0;
}
