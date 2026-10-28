/* One active app, no unauthorized exit from unsaved Notes, HAL retries. */
#include "../pmkb_launcher_bridge.h"
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
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
    CHECK(notes->runnable&&calc->runnable&&store->runnable);
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
    CHECK(pmkb_app_host_store_load(&host,(const uint8_t*)"{}",2u)
          ==PMKB_NOT_FOUND);
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
static int notes_snapshot_handoff(void){
    PMKBAppHost host;pmkb_app_host_init(&host);
    char *json=NULL;size_t length=0;
    CHECK(pmkb_app_host_notes_export_snapshot(&host,1,&json,&length)==PMKB_NOT_FOUND);
    CHECK(json==NULL&&length==0);
    CHECK(pmkb_app_host_launch(&host,PMKB_APP_NOTES,320,480)==PMKB_OK);
    const uint64_t generation=host.generation;
    CHECK(generation>0&&generation<UINT64_MAX);
    CHECK(pmkb_app_host_notes_export_snapshot(&host,0,&json,&length)==PMKB_INVALID);
    CHECK(pmkb_app_host_notes_export_snapshot(&host,UINT64_MAX,&json,&length)==PMKB_INVALID);
    CHECK(pmkb_app_host_notes_export_snapshot(&host,generation+1,&json,&length)==PMKB_INVALID);
    CHECK(json==NULL&&length==0);
    CHECK(pmkb_app_host_notes_export_snapshot(&host,generation,&json,&length)==PMKB_OK);
    CHECK(json!=NULL&&length==strlen(json));
    CHECK(strstr(json,"\"format\":\"pmkb-notes-v1\"")!=NULL);
    CHECK(strstr(json,"\"notes\":[]")!=NULL);
    free(json);json=NULL;length=0;

    CHECK(pmkb_app_host_event(&host,
          (PMKBEvent){.kind=PMKB_EVENT_TAP,.x=14,.y=14},UTC)==PMKB_OK);
    PMKBUI *notes=(PMKBUI*)host.instance;
    CHECK(notes->notebook.count==1);
    /* ADR-005: an empty title is legal while editing, but not in JSON. */
    CHECK(pmkb_text_set(&notes->notebook.items[0]->title,"")==PMKB_OK);
    CHECK(pmkb_app_host_notes_export_snapshot(&host,generation,&json,&length)
          ==PMKB_INVALID);
    CHECK(json==NULL&&length==0);
    CHECK(pmkb_app_host_event(&host,(PMKBEvent){.kind=PMKB_EVENT_ENTER},UTC)
          ==PMKB_OK);
    CHECK(pmkb_app_host_event(&host,(PMKBEvent){.kind=PMKB_EVENT_TEXT,
          .text="Rendez-vous \xc3\xa0 15h"},UTC)==PMKB_OK);
    CHECK(pmkb_app_host_notes_export_snapshot(&host,generation,&json,&length)
          ==PMKB_OK);
    CHECK(json&&length==strlen(json));
    CHECK(strstr(json,"Sans titre 1")!=NULL);
    CHECK(strstr(json,"Rendez-vous \xc3\xa0 15h")!=NULL);
    free(json);json=NULL;length=0;
    CHECK(host.generation==generation);
    /* Exporting a RAM snapshot does not confirm durable persistence. */
    CHECK(pmkb_app_host_close(&host,false)==PMKB_UNSAVED);
    CHECK(host.active==PMKB_APP_NOTES&&host.instance==notes);
    CHECK(host.generation==generation);
    CHECK(pmkb_app_host_close(&host,true)==PMKB_OK);
    CHECK(host.instance==NULL&&host.generation==generation+1);
    CHECK(pmkb_app_host_notes_export_snapshot(&host,generation,&json,&length)
          ==PMKB_NOT_FOUND);
    CHECK(pmkb_app_host_launch(&host,PMKB_APP_NOTES,320,480)==PMKB_OK);
    CHECK(host.generation==generation+2);
    CHECK(pmkb_app_host_notes_export_snapshot(&host,generation,&json,&length)
          ==PMKB_INVALID);
    CHECK(pmkb_app_host_notes_export_snapshot(&host,host.generation,&json,&length)
          ==PMKB_OK);
    CHECK(json&&strstr(json,"\"notes\":[]")!=NULL);
    free(json);json=NULL;length=0;
    CHECK(pmkb_app_host_close(&host,false)==PMKB_OK);
    CHECK(pmkb_app_host_launch(&host,PMKB_APP_CALCULATOR,320,480)==PMKB_OK);
    CHECK(pmkb_app_host_notes_export_snapshot(&host,host.generation,&json,&length)
          ==PMKB_NOT_FOUND);
    CHECK(pmkb_app_host_notes_export_snapshot(&host,host.generation,NULL,&length)
          ==PMKB_INVALID);
    CHECK(pmkb_app_host_notes_export_snapshot(NULL,1,&json,&length)==PMKB_INVALID);
    CHECK(pmkb_app_host_close(&host,false)==PMKB_OK);
    groups++;return 0;
}
static int notes_import_from_verified_memory(void){
    PMKBAppHost host;pmkb_app_host_init(&host);
    CHECK(pmkb_app_host_launch(&host,PMKB_APP_NOTES,320,480)==PMKB_OK);
    uint64_t source_generation=host.generation;
    CHECK(pmkb_app_host_event(&host,
          (PMKBEvent){.kind=PMKB_EVENT_TAP,.x=14,.y=14},UTC)==PMKB_OK);
    PMKBUI *notes=(PMKBUI*)host.instance;
    CHECK(notes->notebook.count==1u);
    CHECK(pmkb_text_set(&notes->notebook.items[0]->title,
                        "Carnet restaur\xc3\xa9")==PMKB_OK);
    CHECK(pmkb_text_set(&notes->notebook.items[0]->body,
                        "Bonjour \xce\xa9\nSuite")==PMKB_OK);
    char *snapshot=NULL,*copy=NULL;size_t length=0,copy_len=0;
    CHECK(pmkb_app_host_notes_export_snapshot(
          &host,source_generation,&snapshot,&length)==PMKB_OK);
    CHECK(snapshot!=NULL&&length==strlen(snapshot));
    CHECK(pmkb_app_host_close(&host,false)==PMKB_UNSAVED);
    CHECK(pmkb_app_host_close(&host,true)==PMKB_OK);
    CHECK(pmkb_app_host_launch(&host,PMKB_APP_NOTES,320,480)==PMKB_OK);
    const uint64_t new_generation=host.generation;
    CHECK(new_generation>source_generation);
    CHECK(pmkb_app_host_notes_import_snapshot(&host,source_generation,
          (const uint8_t*)snapshot,length,true)==PMKB_INVALID);
    CHECK(((PMKBUI*)host.instance)->notebook.count==0u);
    CHECK(pmkb_app_host_event(&host,
          (PMKBEvent){.kind=PMKB_EVENT_TAP,.x=14,.y=14},UTC)==PMKB_OK);
    PMKBUI *current=(PMKBUI*)host.instance;
    PMKBNote *before=current->notebook.items[0];
    CHECK(pmkb_app_host_notes_import_snapshot(&host,new_generation,
          (const uint8_t*)snapshot,length,false)==PMKB_UNSAVED);
    CHECK(current->notebook.items[0]==before&&host.generation==new_generation);
    static const uint8_t malformed[]="{\"format\":\"broken\"}";
    CHECK(pmkb_app_host_notes_import_snapshot(&host,new_generation,
          malformed,sizeof(malformed)-1u,true)==PMKB_INVALID);
    CHECK(current->notebook.items[0]==before&&host.generation==new_generation);
    CHECK(pmkb_app_host_notes_import_snapshot(&host,new_generation,
          (const uint8_t*)snapshot,length,true)==PMKB_OK);
    CHECK(host.generation==new_generation+1u);
    CHECK(current->notebook.count==1u);
    CHECK(current->view==PMKB_VIEW_LIST);
    CHECK(!current->keyboard.visible);
    CHECK(strcmp(current->notebook.items[0]->title.data,
                 "Carnet restaur\xc3\xa9")==0);
    CHECK(strcmp(current->notebook.items[0]->body.data,
                 "Bonjour \xce\xa9\nSuite")==0);
    CHECK(pmkb_app_host_notes_export_snapshot(
          &host,new_generation,&copy,&copy_len)==PMKB_INVALID);
    CHECK(copy==NULL&&copy_len==0u);
    CHECK(pmkb_app_host_notes_export_snapshot(
          &host,host.generation,&copy,&copy_len)==PMKB_OK);
    CHECK(copy_len==length&&memcmp(copy,snapshot,length)==0);
    free(copy);free(snapshot);
    CHECK(pmkb_app_host_close(&host,false)==PMKB_UNSAVED);
    CHECK(pmkb_app_host_close(&host,true)==PMKB_OK);
    CHECK(pmkb_app_host_launch(&host,PMKB_APP_CALCULATOR,320,480)==PMKB_OK);
    CHECK(pmkb_app_host_notes_import_snapshot(&host,host.generation,
          malformed,sizeof(malformed)-1u,true)==PMKB_NOT_FOUND);
    CHECK(pmkb_app_host_close(&host,false)==PMKB_OK);
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
static int store_via_launcher(void){
    static const uint8_t one[] =
        "{\"cleanup_pending_count\":1,\"items\":["
        "{\"id\":\"org.pmkb.demo\",\"label\":\"Demo\",\"launchable\":false,"
        "\"network_declared\":false,\"state\":\"installed_unverified\","
        "\"version\":\"1.2.3\"}],\"schema\":\"pmkb-store-view-v1\","
        "\"scope\":\"synthetic_read_only\"}";
    static const uint8_t many[] =
        "{\"cleanup_pending_count\":0,\"items\":["
        "{\"id\":\"org.pmkb.app0\",\"label\":\"App 0\",\"launchable\":false,\"network_declared\":false,\"state\":\"installed_unverified\",\"version\":\"1.0.0\"},"
        "{\"id\":\"org.pmkb.app1\",\"label\":\"App 1\",\"launchable\":false,\"network_declared\":false,\"state\":\"installed_unverified\",\"version\":\"1.0.0\"},"
        "{\"id\":\"org.pmkb.app2\",\"label\":\"App 2\",\"launchable\":false,\"network_declared\":false,\"state\":\"installed_unverified\",\"version\":\"1.0.0\"},"
        "{\"id\":\"org.pmkb.app3\",\"label\":\"App 3\",\"launchable\":false,\"network_declared\":false,\"state\":\"installed_unverified\",\"version\":\"1.0.0\"},"
        "{\"id\":\"org.pmkb.app4\",\"label\":\"App 4\",\"launchable\":false,\"network_declared\":false,\"state\":\"installed_unverified\",\"version\":\"1.0.0\"},"
        "{\"id\":\"org.pmkb.app5\",\"label\":\"App 5\",\"launchable\":false,\"network_declared\":false,\"state\":\"installed_unverified\",\"version\":\"1.0.0\"}],"
        "\"schema\":\"pmkb-store-view-v1\",\"scope\":\"synthetic_read_only\"}";
    PMKBAppHost host;pmkb_app_host_init(&host);
    CHECK(pmkb_app_host_launch(&host,PMKB_APP_STORE,320,480)==PMKB_OK);
    CHECK(host.active==PMKB_APP_STORE&&host.instance&&host.generation==1u);
    PMKBStoreApp *store=(PMKBStoreApp*)host.instance;
    CHECK(store->catalogue.count==0u&&store->page_index==0u);
    CHECK(store->render_calls==1u&&pmkb_app_host_screen(&host)==&store->screen);
    const unsigned renders=store->render_calls;
    CHECK(pmkb_app_host_store_load(&host,(const uint8_t*)"{}",2u)==PMKB_INVALID);
    CHECK(store->catalogue.count==0u&&store->render_calls==renders);
    CHECK(pmkb_app_host_store_load(&host,one,sizeof(one)-1u)==PMKB_OK);
    CHECK(store->catalogue.count==1u&&store->catalogue.cleanup_pending_count==1u);
    CHECK(strcmp(store->catalogue.items[0].label,"Demo")==0);
    FakeBackend mock={0};PMKBBackend adapter={.context=&mock,.present=present};
    CHECK(pmkb_app_host_present(&host,&adapter)==PMKB_OK);
    CHECK(mock.calls>=1&&!store->screen.has_dirty);
    CHECK(pmkb_app_host_store_load(&host,many,sizeof(many)-1u)==PMKB_OK);
    CHECK(store->catalogue.count==6u&&store->page_index==0u);
    CHECK(!store->showing_detail);
    CHECK(pmkb_app_host_event(&host,
          (PMKBEvent){.kind=PMKB_EVENT_TAP,.x=20,.y=70},NULL)==PMKB_OK);
    CHECK(store->showing_detail&&store->selected_index==0u);
    CHECK(pmkb_app_host_event(&host,(PMKBEvent){.kind=PMKB_EVENT_RIGHT},NULL)
          ==PMKB_NO_CHANGE);
    CHECK(pmkb_app_host_event(&host,(PMKBEvent){.kind=PMKB_EVENT_SHOW_LIST},NULL)
          ==PMKB_OK);
    CHECK(!store->showing_detail&&store->page_index==0u);
    CHECK(pmkb_app_host_event(&host,(PMKBEvent){.kind=PMKB_EVENT_RIGHT},NULL)
          ==PMKB_OK);
    CHECK(store->page_index==1u);
    CHECK(pmkb_app_host_event(&host,(PMKBEvent){.kind=PMKB_EVENT_RIGHT},NULL)
          ==PMKB_NO_CHANGE);
    CHECK(pmkb_app_host_event(&host,(PMKBEvent){.kind=PMKB_EVENT_LEFT},NULL)
          ==PMKB_OK);
    CHECK(store->page_index==0u);
    CHECK(pmkb_app_host_event(&host,
          (PMKBEvent){.kind=PMKB_EVENT_TAP,.x=300,.y=470},NULL)==PMKB_OK);
    CHECK(store->page_index==1u);
    CHECK(pmkb_app_host_event(&host,(PMKBEvent){.kind=PMKB_EVENT_SHOW_LIST},NULL)
          ==PMKB_OK);
    CHECK(store->page_index==0u);
    CHECK(pmkb_app_host_event(&host,(PMKBEvent){.kind=PMKB_EVENT_SHOW_LIST},NULL)
          ==PMKB_NO_CHANGE);
    CHECK(pmkb_app_host_close(&host,false)==PMKB_OK);
    CHECK(host.active==PMKB_APP_NONE&&host.instance==NULL&&host.generation==2u);
    CHECK(pmkb_app_host_store_load(&host,one,sizeof(one)-1u)==PMKB_NOT_FOUND);
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
static int whiteboard_via_launcher(void){
    PMKBAppHost host;pmkb_app_host_init(&host);
    const PMKBAppInfo *info=pmkb_app_info(PMKB_APP_WHITEBOARD);
    CHECK(info && info->runnable && strcmp(info->id,"whiteboard")==0);
    CHECK(pmkb_app_host_launch(&host,PMKB_APP_WHITEBOARD,320,480)==PMKB_OK);
    CHECK(pmkb_app_host_screen(&host)!=NULL);
    CHECK(pmkb_app_host_launch(&host,PMKB_APP_STORE,320,480)==PMKB_INVALID);
    CHECK(pmkb_app_host_whiteboard_touch(&host,PMKB_WB_TOUCH_DOWN,12,12)==PMKB_WB_OK);
    CHECK(pmkb_app_host_whiteboard_touch(&host,PMKB_WB_TOUCH_UP,20,12)==PMKB_WB_OK);
    CHECK(pmkb_app_host_close(&host,false)==PMKB_UNSAVED);
    CHECK(host.active==PMKB_APP_WHITEBOARD && host.instance!=NULL);
    CHECK(pmkb_app_host_whiteboard_undo(&host)==PMKB_WB_OK);
    CHECK(pmkb_app_host_close(&host,true)==PMKB_OK);
    CHECK(host.instance==NULL && host.active==PMKB_APP_NONE);
    CHECK(pmkb_app_host_launch(&host,PMKB_APP_STORE,320,480)==PMKB_OK);
    CHECK(pmkb_app_host_screen(&host)!=NULL);
    CHECK(pmkb_app_host_close(&host,true)==PMKB_OK);
    groups++;return 0;
}
int main(void){
    if(catalog()||safe_lifecycle()||notes_snapshot_handoff()||
       notes_import_from_verified_memory()||
       calculator_via_launcher()||
       store_via_launcher()||whiteboard_via_launcher()||font_and_clipping())return 1;
    printf("PMKB LAUNCHER/RENDER: %u assertions PASS, %u groups PASS, 0 FAIL\n",
           passed,groups);
    return 0;
}
