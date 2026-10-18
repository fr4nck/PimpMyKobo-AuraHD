/* Native host-only regression: C11, no external packages or device access. */
#include "../pmkb_ui.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define UTC "2026-10-19T01:04:00.000Z"
static unsigned checked=0,groups=0;
#define CHECK(cond) do { checked++; if(!(cond)){ \
    fprintf(stderr,"FAIL %s:%d: %s\n",__FILE__,__LINE__,#cond);return 1; \
} } while(0)

static int utf8_edit(void){
    PMKBText text={0};size_t units=0;
    CHECK(pmkb_text_init(&text,PMKB_TITLE_LIMIT,"caf\xc3\xa9") == PMKB_OK);
    CHECK(text.bytes==5 && pmkb_text_utf16_length(&text)==4);
    CHECK(pmkb_text_select(&text,3,4)==PMKB_INVALID);
    CHECK(pmkb_text_select(&text,3,5)==PMKB_OK);
    CHECK(pmkb_text_insert(&text,"e\xcc\x81")==PMKB_OK);
    CHECK(strcmp(text.data,"cafe\xcc\x81")==0);
    CHECK(pmkb_text_backspace(&text)==PMKB_OK);
    CHECK(strcmp(text.data,"cafe")==0); /* never split combining UTF-8 */
    CHECK(pmkb_text_backspace(&text)==PMKB_OK);
    CHECK(strcmp(text.data,"caf")==0);
    CHECK(pmkb_text_move(&text,-1)==PMKB_OK);
    CHECK(pmkb_text_insert(&text,"\xc3\xa9")==PMKB_OK);
    CHECK(strcmp(text.data,"ca\xc3\xa9f")==0);
    CHECK(pmkb_utf8_measure("\xf0\x9f\x98\x80",4,&units)==PMKB_OK&&units==2);
    PMKBText small={0};
    CHECK(pmkb_text_init(&small,1,"a")==PMKB_OK);
    CHECK(pmkb_text_insert(&small,"\xf0\x9f\x98\x80")==PMKB_LIMIT);
    CHECK(strcmp(small.data,"a")==0);
    CHECK(pmkb_text_set(&small,"")==PMKB_OK);
    CHECK(pmkb_text_insert(&small,"\xc3\xa9")==PMKB_OK);
    CHECK(pmkb_text_backspace(&small)==PMKB_OK && small.bytes==0);
    for(size_t i=0;i<4;i++){
        const char *broken[]={"\xc0\xaf","\xed\xa0\x80","\xf4\x90\x80\x80","\x01"};
        CHECK(pmkb_text_set(&small,broken[i])==PMKB_INVALID);
        CHECK(strcmp(small.data,"")==0);
    }
    CHECK(pmkb_text_select(&small,0,1)==PMKB_INVALID);
    CHECK(pmkb_text_backspace(&small)==PMKB_NO_CHANGE);
    pmkb_text_free(&small);pmkb_text_free(&text);
    groups++;return 0;
}
static int keyboard_actions(void){
    PMKBKeyboard kb={0};PMKBText field={0};
    CHECK(pmkb_text_init(&field,100,"")==PMKB_OK);
    pmkb_keyboard_open(&kb,PMKB_KB_AZERTY);
    CHECK(kb.visible && kb.page==PMKB_KB_AZERTY);
    PMKBKey azerty=pmkb_keyboard_key(&kb,0,0);
    CHECK(strcmp(azerty.insert,"a")==0);
    CHECK(pmkb_keyboard_key(&kb,4,2).insert!=NULL);
    CHECK(pmkb_keyboard_press(&kb,&field,azerty,true)==PMKB_OK);
    CHECK(strcmp(field.data,"a")==0);
    CHECK(pmkb_keyboard_press(&kb,&field,pmkb_keyboard_key(&kb,5,0),true)==PMKB_OK);
    CHECK(kb.shifted);
    CHECK(pmkb_keyboard_press(&kb,&field,pmkb_keyboard_key(&kb,0,1),true)==PMKB_OK);
    CHECK(strcmp(field.data,"aZ")==0&&!kb.shifted);
    CHECK(pmkb_keyboard_press(&kb,&field,pmkb_keyboard_key(&kb,6,0),true)==PMKB_OK);
    CHECK(field.cursor==1);
    CHECK(pmkb_keyboard_press(&kb,&field,pmkb_keyboard_key(&kb,5,2),true)==PMKB_OK);
    CHECK(strcmp(field.data,"a Z")==0);
    CHECK(pmkb_keyboard_press(&kb,&field,pmkb_keyboard_key(&kb,5,4),true)==PMKB_OK);
    CHECK(strcmp(field.data,"aZ")==0);
    CHECK(pmkb_keyboard_press(&kb,&field,pmkb_keyboard_key(&kb,5,1),true)==PMKB_OK);
    CHECK(kb.page==PMKB_KB_NUMERIC);
    CHECK(strcmp(pmkb_keyboard_key(&kb,0,0).insert,"1")==0);
    CHECK(pmkb_keyboard_press(&kb,&field,pmkb_keyboard_key(&kb,5,1),true)==PMKB_OK);
    CHECK(kb.page==PMKB_KB_SYMBOLS);
    CHECK(strcmp(pmkb_keyboard_key(&kb,0,0).insert,"!")==0);
    CHECK(pmkb_keyboard_press(&kb,&field,pmkb_keyboard_key(&kb,5,1),true)==PMKB_OK);
    CHECK(kb.page==PMKB_KB_AZERTY);
    CHECK(pmkb_keyboard_press(&kb,&field,pmkb_keyboard_key(&kb,5,1),true)==PMKB_OK);
    CHECK(pmkb_keyboard_press(&kb,&field,pmkb_keyboard_key(&kb,0,0),true)==PMKB_OK);
    CHECK(strcmp(field.data,"a1Z")==0);
    CHECK(pmkb_keyboard_press(&kb,&field,pmkb_keyboard_key(&kb,6,4),true)==PMKB_OK);
    CHECK(!kb.visible);
    CHECK(pmkb_keyboard_press(&kb,&field,pmkb_keyboard_key(&kb,0,0),true)==PMKB_INVALID);
    pmkb_text_free(&field);groups++;return 0;
}
static int notebook_memory(void){
    PMKBNotebook book;pmkb_notebook_init(&book);
    size_t idx=99;
    CHECK(pmkb_notebook_new(&book,"2026-02-30T00:00:00.000Z",&idx)==PMKB_INVALID);
    CHECK(pmkb_notebook_new(&book,UTC,&idx)==PMKB_OK);
    CHECK(idx==0&&book.count==1);
    CHECK(strcmp(book.items[0]->title.data,"Sans titre")==0);
    CHECK(strcmp(book.items[0]->id,"pmkb_000001")==0);
    CHECK(pmkb_text_set(&book.items[0]->title,"Cahier \xc3\xa9t\xc3\xa9")==PMKB_OK);
    CHECK(pmkb_text_set(&book.items[0]->body,"Une ligne\nEt une \"citation\".")==PMKB_OK);
    size_t match=99;
    CHECK(pmkb_notebook_find(&book,"pmkb_000001",&match)==PMKB_OK && match==0);
    CHECK(pmkb_notebook_find(&book,"not-found",&match)==PMKB_NOT_FOUND);
    char *json=NULL;size_t len=0;
    CHECK(pmkb_notebook_export_json(&book,&json,&len)==PMKB_OK);
    CHECK(json!=NULL && len==strlen(json));
    CHECK(strstr(json,"\"format\":\"pmkb-notes-v1\"")!=NULL);
    CHECK(strstr(json,"\"strokes\":[]")!=NULL);
    CHECK(strstr(json,"\"typography\":{\"font\":\"mono\",\"size\":17,\"lineHeight\":1.6}")!=NULL);
    CHECK(strstr(json,"Une ligne\\nEt une \\\"citation\\\"")!=NULL);
    free(json);
    for(size_t i=1;i<PMKB_NOTE_LIMIT;i++)
        CHECK(pmkb_notebook_new(&book,UTC,&idx)==PMKB_OK);
    CHECK(book.count==100);
    CHECK(pmkb_notebook_new(&book,UTC,&idx)==PMKB_LIMIT);
    pmkb_notebook_free(&book);
    groups++;return 0;
}
static int dirty_canvas(void){
    PMKBSurface s={0};PMKBRect r;
    CHECK(pmkb_surface_init(&s,320,480)==PMKB_OK);
    CHECK(s.gray!=NULL && s.width==320);
    CHECK(pmkb_surface_take_dirty(&s,&r));
    CHECK(r.x==0&&r.y==0&&r.w==320&&r.h==480);
    CHECK(!pmkb_surface_take_dirty(&s,&r));
    pmkb_surface_rect(&s,(PMKBRect){12,14,20,40},0);
    CHECK(pmkb_surface_take_dirty(&s,&r));
    CHECK(r.x==12&&r.y==14&&r.w==20&&r.h==40);
    pmkb_surface_rect(&s,(PMKBRect){12,14,20,40},0);
    CHECK(!pmkb_surface_take_dirty(&s,&r)); /* unchanged pixels -> no refresh */
    pmkb_surface_text(&s,3,60,"AZERTY",0,180);
    CHECK(pmkb_surface_take_dirty(&s,&r));
    CHECK(r.y>=60&&r.y<80);
    pmkb_surface_rect(&s,(PMKBRect){-200,-200,201,201},100);
    CHECK(pmkb_surface_take_dirty(&s,&r));
    CHECK(r.x==0 && r.y==0 && r.w==1 && r.h==1);
    pmkb_surface_free(&s);
    groups++;return 0;
}
static int ui_flow(void){
    PMKBUI ui={0};PMKBRect dirty;
    CHECK(pmkb_ui_init(&ui,320,480)==PMKB_OK);
    CHECK(ui.view==PMKB_VIEW_LIST&&ui.render_calls==1);
    CHECK(pmkb_surface_take_dirty(&ui.screen,&dirty));
    CHECK(!pmkb_surface_take_dirty(&ui.screen,&dirty));
    CHECK(pmkb_ui_new_note(&ui,UTC)==PMKB_OK);
    CHECK(ui.view==PMKB_VIEW_EDITOR&&ui.focus==PMKB_FOCUS_TITLE);
    CHECK(!ui.keyboard.visible);
    CHECK(pmkb_surface_take_dirty(&ui.screen,&dirty));
    CHECK(pmkb_ui_event(&ui,(PMKBEvent){.kind=PMKB_EVENT_TOGGLE_KEYBOARD},UTC)==PMKB_OK);
    CHECK(ui.keyboard.visible);
    CHECK(pmkb_surface_take_dirty(&ui.screen,&dirty));
    /* Virtual touch: AZERTY first row, first key 'a'. */
    int keyboard_y=ui.screen.height-PMKB_KB_ROWS*44;
    CHECK(pmkb_ui_event(&ui,(PMKBEvent){.kind=PMKB_EVENT_TAP,.x=10,.y=keyboard_y+10},UTC)==PMKB_OK);
    CHECK(strcmp(ui.notebook.items[0]->title.data,"a")==0);
    CHECK(ui.focus==PMKB_FOCUS_TITLE);
    CHECK(pmkb_surface_take_dirty(&ui.screen,&dirty));
    CHECK(dirty.y>=48); /* keyboard typing never repaints entire toolbar */
    CHECK(pmkb_ui_event(&ui,(PMKBEvent){.kind=PMKB_EVENT_TAP,.x=310,.y=keyboard_y+5*44+10},UTC)==PMKB_OK);
    CHECK(ui.focus==PMKB_FOCUS_BODY);
    CHECK(pmkb_ui_event(&ui,(PMKBEvent){.kind=PMKB_EVENT_TEXT,.text="Bonjour \xc3\xa9t\xc3\xa9"},UTC)==PMKB_OK);
    CHECK(strcmp(ui.notebook.items[0]->body.data,"Bonjour \xc3\xa9t\xc3\xa9")==0);
    CHECK(pmkb_ui_event(&ui,(PMKBEvent){.kind=PMKB_EVENT_ENTER},UTC)==PMKB_OK);
    CHECK(pmkb_ui_event(&ui,(PMKBEvent){.kind=PMKB_EVENT_TEXT,.text="PMKB"},UTC)==PMKB_OK);
    CHECK(strstr(ui.notebook.items[0]->body.data,"\nPMKB")!=NULL);
    CHECK(pmkb_ui_event(&ui,(PMKBEvent){.kind=PMKB_EVENT_BACKSPACE},UTC)==PMKB_OK);
    CHECK(strstr(ui.notebook.items[0]->body.data,"\nPMK")!=NULL);
    CHECK(pmkb_ui_event(&ui,(PMKBEvent){.kind=PMKB_EVENT_SHOW_LIST},UTC)==PMKB_OK);
    CHECK(ui.view==PMKB_VIEW_LIST&&!ui.keyboard.visible);
    CHECK(pmkb_ui_event(&ui,(PMKBEvent){.kind=PMKB_EVENT_TAP,.x=20,.y=96+15},UTC)==PMKB_OK);
    CHECK(ui.view==PMKB_VIEW_EDITOR&&ui.focus==PMKB_FOCUS_BODY);
    CHECK(strcmp(ui.notebook.items[0]->title.data,"a")==0);
    CHECK(strstr(ui.notebook.items[0]->body.data,"\nPMK")!=NULL);
    CHECK(pmkb_ui_event(&ui,(PMKBEvent){.kind=PMKB_EVENT_TEXT,.text="\xc0\xaf"},UTC)==PMKB_INVALID);
    CHECK(strstr(ui.notebook.items[0]->body.data,"\nPMK")!=NULL);
    CHECK(pmkb_ui_event(&ui,(PMKBEvent){.kind=PMKB_EVENT_TAP,.x=-1,.y=10},UTC)==PMKB_INVALID);
    char *json=NULL;size_t len=0;
    CHECK(pmkb_notebook_export_json(&ui.notebook,&json,&len)==PMKB_OK);
    CHECK(strstr(json,"\"title\":\"a\"")!=NULL);
    CHECK(strstr(json,"\"format\":\"pmkb-notes-v1\"")!=NULL);
    free(json);
    unsigned before=ui.render_calls;
    pmkb_ui_draw(&ui);
    CHECK(ui.render_calls==before); /* no permanent render loop */
    pmkb_ui_free(&ui);
    groups++;return 0;
}
static int high_resolution_budget(void){
    PMKBUI ui={0};PMKBRect dirty;
    CHECK(pmkb_ui_init(&ui,1080,1440)==PMKB_OK);
    CHECK(ui.screen.gray!=NULL&&ui.screen.width*ui.screen.height==1555200);
    CHECK(pmkb_surface_take_dirty(&ui.screen,&dirty));
    CHECK(pmkb_ui_new_note(&ui,UTC)==PMKB_OK);
    CHECK(pmkb_surface_take_dirty(&ui.screen,&dirty));
    CHECK(dirty.h<1440); /* updating widgets need not dirty entire frame */
    pmkb_ui_free(&ui);
    groups++;return 0;
}
static int dump_fixture(void){
    PMKBNotebook book;pmkb_notebook_init(&book);
    size_t index=0;char *out=NULL;size_t length=0;
    if(pmkb_notebook_new(&book,UTC,&index)!=PMKB_OK)return 1;
    if(pmkb_text_set(&book.items[index]->title,"Journal \xc3\xa9t\xc3\xa9")!=PMKB_OK)return 1;
    if(pmkb_text_set(&book.items[index]->body,"Bonjour\n\xce\xa9 \"test\"")!=PMKB_OK)return 1;
    if(pmkb_notebook_export_json(&book,&out,&length)!=PMKB_OK)return 1;
    (void)fwrite(out,1,length,stdout);
    (void)fputc('\n',stdout);
    free(out);pmkb_notebook_free(&book);
    return 0;
}
int main(int argc,char **argv){
    if(argc==2&&strcmp(argv[1],"--json-fixture")==0)return dump_fixture();
    if(argc!=1)return 2;
    if(utf8_edit()||keyboard_actions()||notebook_memory()||
       dirty_canvas()||ui_flow()||high_resolution_budget())return 1;
    printf("PMKB NATIVE: %u assertions PASS, %u groups PASS, 0 FAIL\n",
           checked,groups);
    return 0;
}
