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
    CHECK(strcmp(text.data,"ca\xc3\xa9" "f")==0);
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

static int scientific_keyboard(void){
    PMKBKeyboard kb={0};PMKBText expr={0};
    CHECK(pmkb_text_init(&expr,192,"")==PMKB_OK);
    pmkb_keyboard_open(&kb,PMKB_KB_SCIENTIFIC);
    CHECK(kb.visible&&kb.page==PMKB_KB_SCIENTIFIC&&kb.degrees);
    for(int r=0;r<PMKB_KB_ROWS;r++)
        for(int c=0;c<PMKB_KB_COLS;c++){
            PMKBKey key=pmkb_keyboard_key(&kb,r,c);
            CHECK(key.span>=1&&key.span<=2);
            CHECK(key.label&&key.label[0]);
            CHECK(key.action!=PMKB_KEY_INSERT||key.insert);
        }
    CHECK(strcmp(pmkb_keyboard_key(&kb,0,5).insert,"sqrt(")==0);
    CHECK(strcmp(pmkb_keyboard_key(&kb,2,5).insert,"\xcf\x80")==0);
    CHECK(strcmp(pmkb_keyboard_key(&kb,4,2).insert,"Ans")==0);
    CHECK(strcmp(pmkb_keyboard_key(&kb,4,4).insert,"abs(")==0);
    CHECK(pmkb_keyboard_press(&kb,&expr,pmkb_keyboard_key(&kb,0,0),false)==PMKB_OK);
    CHECK(pmkb_keyboard_press(&kb,&expr,pmkb_keyboard_key(&kb,3,2),false)==PMKB_OK);
    CHECK(pmkb_keyboard_press(&kb,&expr,pmkb_keyboard_key(&kb,4,0),false)==PMKB_OK);
    CHECK(pmkb_keyboard_press(&kb,&expr,pmkb_keyboard_key(&kb,1,5),false)==PMKB_OK);
    CHECK(strcmp(expr.data,"sin(30)")==0);
    CHECK(pmkb_keyboard_press(&kb,&expr,pmkb_keyboard_key(&kb,5,5),false)==PMKB_EVALUATE);
    CHECK(strcmp(expr.data,"sin(30)")==0);
    CHECK(pmkb_keyboard_press(&kb,&expr,pmkb_keyboard_key(&kb,4,5),false)==PMKB_OK);
    CHECK(!kb.degrees&&strcmp(pmkb_keyboard_key(&kb,4,5).label,"RAD")==0);
    CHECK(pmkb_keyboard_press(&kb,&expr,pmkb_keyboard_key(&kb,4,5),false)==PMKB_OK);
    CHECK(kb.degrees&&strcmp(pmkb_keyboard_key(&kb,4,5).label,"DEG")==0);
    CHECK(pmkb_keyboard_press(&kb,&expr,pmkb_keyboard_key(&kb,5,2),false)==PMKB_OK);
    CHECK(expr.bytes==0&&expr.cursor==0);
    CHECK(pmkb_keyboard_press(&kb,&expr,pmkb_keyboard_key(&kb,5,0),false)==PMKB_OK);
    CHECK(kb.shifted);
    CHECK(strcmp(pmkb_keyboard_key(&kb,0,0).insert,"asin(")==0);
    CHECK(strcmp(pmkb_keyboard_key(&kb,0,1).insert,"acos(")==0);
    CHECK(strcmp(pmkb_keyboard_key(&kb,0,2).insert,"atan(")==0);
    CHECK(pmkb_keyboard_press(&kb,&expr,pmkb_keyboard_key(&kb,0,0),false)==PMKB_OK);
    CHECK(strcmp(expr.data,"asin(")==0&&!kb.shifted);
    CHECK(pmkb_text_set(&expr,"\xcf\x80 + Ans")==PMKB_OK);
    CHECK(pmkb_text_select(&expr,0,2)==PMKB_OK);
    CHECK(pmkb_keyboard_press(&kb,&expr,pmkb_keyboard_key(&kb,2,5),false)==PMKB_NO_CHANGE);
    CHECK(strcmp(expr.data,"\xcf\x80 + Ans")==0);
    CHECK(pmkb_text_select(&expr,0,2)==PMKB_OK);
    CHECK(pmkb_keyboard_press(&kb,&expr,pmkb_keyboard_key(&kb,4,2),false)==PMKB_OK);
    CHECK(strcmp(expr.data,"Ans + Ans")==0);
    CHECK(pmkb_text_set(&expr,"\xcf\x80")==PMKB_OK);
    CHECK(pmkb_keyboard_press(&kb,&expr,pmkb_keyboard_key(&kb,5,4),false)==PMKB_OK);
    CHECK(expr.bytes==0);
    CHECK(pmkb_keyboard_key(&kb,-1,0).span==0);
    CHECK(pmkb_keyboard_key(&kb,0,6).span==0);
    PMKBKeyboard before=kb;
    pmkb_keyboard_open(&kb,(PMKBKeyboardPage)99);
    CHECK(kb.visible==before.visible&&kb.page==before.page);
    CHECK(pmkb_keyboard_press(&kb,&expr,pmkb_keyboard_key(&kb,5,1),false)==PMKB_OK);
    CHECK(kb.page==PMKB_KB_AZERTY);
    CHECK(pmkb_keyboard_press(&kb,&expr,
        (PMKBKey){PMKB_KEY_EVALUATE,"=",NULL,1},false)==PMKB_INVALID);
    pmkb_keyboard_close(&kb);
    CHECK(pmkb_keyboard_press(&kb,&expr,
        (PMKBKey){PMKB_KEY_EVALUATE,"=",NULL,1},false)==PMKB_INVALID);
    pmkb_text_free(&expr);groups++;return 0;
}

/* ADR-005: "Sans titre" is restored on blur, never mid-entry.
 * No browser storage, material device or manga assets are touched. */
static int empty_title_blur(void){
    PMKBUI ui={0};char *json=NULL;size_t length=0;
    CHECK(pmkb_ui_init(&ui,320,480)==PMKB_OK);
    for(int method=0;method<3;method++){
        CHECK(pmkb_ui_new_note(&ui,UTC)==PMKB_OK);
        PMKBNote *note=ui.notebook.items[ui.selected];
        CHECK(ui.focus==PMKB_FOCUS_TITLE);
        CHECK(pmkb_ui_event(&ui,(PMKBEvent){.kind=PMKB_EVENT_BACKSPACE},UTC)==PMKB_OK);
        CHECK(note->title.bytes==0&&strcmp(note->title.data,"")==0);
        CHECK(ui.focus==PMKB_FOCUS_TITLE); /* no premature normalization */
        CHECK(pmkb_notebook_export_json(&ui.notebook,&json,&length)==PMKB_INVALID);
        CHECK(json==NULL); /* current empty title cannot be exported */
        if(method==0){
            CHECK(pmkb_ui_event(&ui,(PMKBEvent){.kind=PMKB_EVENT_ENTER},UTC)==PMKB_OK);
        }else if(method==1){
            CHECK(pmkb_ui_event(&ui,(PMKBEvent){
                .kind=PMKB_EVENT_TAP,.x=20,.y=108},UTC)==PMKB_OK);
        }else{
            CHECK(pmkb_ui_event(&ui,(PMKBEvent){
                .kind=PMKB_EVENT_TOGGLE_KEYBOARD},UTC)==PMKB_OK);
            int top=ui.screen.height-PMKB_KB_ROWS*44;
            CHECK(pmkb_ui_event(&ui,(PMKBEvent){
                .kind=PMKB_EVENT_TAP,.x=310,.y=top+5*44+10},UTC)==PMKB_OK);
        }
        CHECK(ui.focus==PMKB_FOCUS_BODY);
        char expected[32];
        (void)snprintf(expected,sizeof(expected),"Sans titre %d",method+1);
        CHECK(strcmp(note->title.data,expected)==0);
        CHECK(pmkb_notebook_export_json(&ui.notebook,&json,&length)==PMKB_OK);
        CHECK(json!=NULL&&strstr(json,expected)!=NULL);
        free(json);json=NULL;length=0;
    }
    pmkb_ui_free(&ui);groups++;return 0;
}

/* ADR-005 L05-B: restore whitespace-only titles on ALL editor exits,
 * never during editing. Reuses the notebook export predicate. */
static int title_blur_navigation(void){
    static const char *blanks[]={" ","\xc2\xa0","\xe3\x80\x80",""};
    for(int method=0;method<5;method++){
        PMKBUI ui={0};char *json=NULL;size_t length=0;
        CHECK(pmkb_ui_init(&ui,320,480)==PMKB_OK);
        CHECK(pmkb_ui_new_note(&ui,UTC)==PMKB_OK);
        if(method==4)CHECK(pmkb_ui_new_note(&ui,UTC)==PMKB_OK);
        PMKBNote *old=ui.notebook.items[ui.selected];
        const char *blank=blanks[method%4];
        CHECK(pmkb_text_set(&old->title,blank)==PMKB_OK);
        CHECK(old->title.bytes==strlen(blank)&&ui.focus==PMKB_FOCUS_TITLE);
        CHECK(!pmkb_notes_meaningful_title(old->title.data));
        CHECK(pmkb_notebook_export_json(&ui.notebook,&json,&length)==PMKB_INVALID);
        CHECK(json==NULL); /* never normalize during editing */
        PMKBStatus status=PMKB_INVALID;
        if(method==0)status=pmkb_ui_event(&ui,
            (PMKBEvent){.kind=PMKB_EVENT_SHOW_LIST},UTC);
        else if(method==1)status=pmkb_ui_event(&ui,
            (PMKBEvent){.kind=PMKB_EVENT_TAP,.x=72,.y=10},UTC);
        else if(method==2)status=pmkb_ui_event(&ui,
            (PMKBEvent){.kind=PMKB_EVENT_TAP,.x=12,.y=10},UTC);
        else if(method==3)status=pmkb_ui_new_note(&ui,UTC);
        else status=pmkb_ui_open_note(&ui,0);
        CHECK(status==PMKB_OK);
        CHECK(strcmp(old->title.data,method==4?"Sans titre 2":"Sans titre 1")==0);
        if(method<=1)CHECK(ui.view==PMKB_VIEW_LIST);
        else CHECK(ui.view==PMKB_VIEW_EDITOR);
        CHECK(pmkb_notebook_export_json(&ui.notebook,&json,&length)==PMKB_OK);
        CHECK(json!=NULL&&strstr(json,method==4?"Sans titre 2":"Sans titre 1")!=NULL);
        free(json);
        pmkb_ui_free(&ui);
    }
    PMKBUI ui={0};
    CHECK(pmkb_ui_init(&ui,320,480)==PMKB_OK);
    CHECK(pmkb_ui_new_note(&ui,UTC)==PMKB_OK);
    PMKBNote *n=ui.notebook.items[0];
    CHECK(pmkb_text_set(&n->title," \xc2\xa0 ")==PMKB_OK);
    CHECK(pmkb_ui_event(&ui,(PMKBEvent){.kind=PMKB_EVENT_ENTER},UTC)==PMKB_OK);
    CHECK(strcmp(n->title.data,"Sans titre 1")==0);
    CHECK(pmkb_ui_event(&ui,(PMKBEvent){
        .kind=PMKB_EVENT_TAP,.x=15,.y=75},UTC)==PMKB_OK);
    CHECK(pmkb_text_set(&n->title,"  Projet  ")==PMKB_OK);
    CHECK(pmkb_ui_event(&ui,(PMKBEvent){.kind=PMKB_EVENT_ENTER},UTC)==PMKB_OK);
    CHECK(strcmp(n->title.data,"  Projet  ")==0);
    pmkb_ui_free(&ui);
    groups++;return 0;
}

static int notebook_memory(void){
    PMKBNotebook book;pmkb_notebook_init(&book);
    size_t idx=99;
    CHECK(pmkb_notebook_new(&book,"2026-02-30T00:00:00.000Z",&idx)==PMKB_INVALID);
    CHECK(pmkb_notebook_new(&book,UTC,&idx)==PMKB_OK);
    CHECK(idx==0&&book.count==1);
    CHECK(strcmp(book.items[0]->title.data,"Sans titre 1")==0);
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
    CHECK(pmkb_text_set(&book.items[0]->title," ")==PMKB_OK);
    json=NULL;len=0;
    CHECK(pmkb_notebook_export_json(&book,&json,&len)==PMKB_INVALID);
    CHECK(json==NULL && strcmp(book.items[0]->title.data," ")==0);
    CHECK(pmkb_text_set(&book.items[0]->title,"\xc2\xa0")==PMKB_OK);
    CHECK(pmkb_notebook_export_json(&book,&json,&len)==PMKB_INVALID);
    CHECK(json==NULL);
    CHECK(pmkb_text_set(&book.items[0]->title,"Carnet valide")==PMKB_OK);
    CHECK(pmkb_notebook_export_json(&book,&json,&len)==PMKB_OK);
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

/* L03-B host-only reference: mathematically nearest of 16 linear grays.
 * Not a calibrated E606C0 waveform, framebuffer format or packed driver. */
static uint8_t gray16_reference(uint8_t gray){
    return (uint8_t)(((unsigned)gray*15u+127u)/255u);
}
static int gray16_invalidation_budget(void){
    unsigned seen=0;
    for(unsigned v=0;v<256u;v++){
        unsigned level=gray16_reference((uint8_t)v);
        CHECK(level<=15u);
        int error=(int)level*17-(int)v;
        CHECK(error>=-8&&error<=8);
        if(v>0u)CHECK(level>=gray16_reference((uint8_t)(v-1u)));
        seen|=1u<<level;
    }
    CHECK(seen==0xffffu); /* all 16 levels reachable, monotone */

    PMKBSurface s={0};PMKBRect r={0};
    CHECK(pmkb_surface_init(&s,1080,1440)==PMKB_OK);
    CHECK(pmkb_surface_take_dirty(&s,&r));
    CHECK(r.x==0&&r.y==0&&r.w==1080&&r.h==1440);
    /* 16 reference gray swatches. White-on-white should not invalidate. */
    for(unsigned i=0;i<16u;i++){
        int x=12+(int)i*8;
        uint8_t shade=(uint8_t)(i*17u);
        CHECK(gray16_reference(shade)==i);
        pmkb_surface_rect(&s,(PMKBRect){x,24,2,2},shade);
        CHECK(s.gray[(size_t)24u*1080u+(size_t)x]==shade);
    }
    CHECK(s.has_dirty&&s.changed_pixels==60u); /* 15 swatches x 4 px */
    CHECK(pmkb_surface_take_dirty(&s,&r));
    CHECK(r.x==12&&r.y==24&&r.w==114&&r.h==2);
    size_t clustered_area=(size_t)r.w*(size_t)r.h;
    CHECK(clustered_area==228u);
    for(unsigned i=0;i<16u;i++){
        int x=12+(int)i*8;
        pmkb_surface_rect(&s,(PMKBRect){x,24,2,2},
                          (uint8_t)(i*17u));
    }
    CHECK(!s.has_dirty&&s.changed_pixels==0u); /* no-op repaints */
    pmkb_surface_rect(&s,(PMKBRect){0,0,1,1},0);
    pmkb_surface_rect(&s,(PMKBRect){1079,1439,1,1},0);
    CHECK(s.has_dirty&&s.changed_pixels==2u);
    CHECK(pmkb_surface_take_dirty(&s,&r));
    CHECK(r.x==0&&r.y==0&&r.w==1080&&r.h==1440);
    size_t distant_area=(size_t)r.w*(size_t)r.h;
    CHECK(distant_area==1555200u);
    CHECK(distant_area/2u==777600u);
    CHECK(!pmkb_surface_take_dirty(&s,&r));
    pmkb_surface_free(&s);
    printf("PMKB EINK HOST: 16 grays, max gray error 8, "
           "clustered_dirty=%zu for 60 pixel writes, "
           "distant_dirty=%zu for 2 pixel writes\n",
           clustered_area,distant_area);
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
    CHECK(pmkb_ui_event(&ui,(PMKBEvent){.kind=PMKB_EVENT_TEXT,.text="X"},"bad-time")==PMKB_INVALID);
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
typedef struct { int calls; bool fail; PMKBRect last; } FakeHal;
static PMKBStatus mock_present(void *context,const uint8_t *pixels,
                               int width,int height,PMKBRect changed){
    FakeHal *mock=(FakeHal*)context;
    if(!pixels||width<=0||height<=0)return PMKB_INVALID;
    mock->calls++;mock->last=changed;
    return mock->fail?PMKB_INVALID:PMKB_OK;
}
static int backend_retry(void){
    PMKBSurface s={0};
    FakeHal mock={0};PMKBRect rect={0};
    PMKBBackend backend={.context=&mock,.present=mock_present};
    CHECK(pmkb_surface_init(&s,320,480)==PMKB_OK);
    CHECK(pmkb_surface_present(&s,NULL)==PMKB_INVALID);
    mock.fail=true;
    CHECK(pmkb_surface_present(&s,&backend)==PMKB_INVALID);
    CHECK(s.has_dirty && mock.calls==1);
    CHECK(mock.last.w==320 && mock.last.h==480);
    mock.fail=false;
    CHECK(pmkb_surface_present(&s,&backend)==PMKB_OK);
    CHECK(mock.calls==2 && !s.has_dirty);
    CHECK(pmkb_surface_present(&s,&backend)==PMKB_NO_CHANGE);
    pmkb_surface_rect(&s,(PMKBRect){12,20,16,10},0);
    CHECK(pmkb_surface_present(&s,&backend)==PMKB_OK);
    CHECK(mock.calls==3 && mock.last.x==12 && mock.last.y==20);
    CHECK(!pmkb_surface_take_dirty(&s,&rect));
    pmkb_surface_free(&s);groups++;return 0;
}

/* Edits performed inside a presentation callback must survive its ACK,
 * including edits inside the very same dirty rectangle. */
typedef struct {
    PMKBSurface *surface;
    unsigned calls;
    PMKBRect last;
    bool same_rect;
} InflightEdit;
static PMKBStatus mutate_while_presenting(void *context,const uint8_t *pixels,
                                          int width,int height,PMKBRect dirty){
    InflightEdit *edit=(InflightEdit*)context;
    if(!pixels||width!=320||height!=480)return PMKB_INVALID;
    edit->calls++;
    edit->last=dirty;
    if(edit->calls==1){
        PMKBRect r=edit->same_rect?(PMKBRect){12,20,1,1}:
                                   (PMKBRect){100,120,1,1};
        pmkb_surface_rect(edit->surface,r,200);
    }
    return PMKB_OK;
}
static int backend_edits_during_present(void){
    for(int same=0;same<2;same++){
        PMKBSurface s={0};PMKBRect old_dirty={0};
        CHECK(pmkb_surface_init(&s,320,480)==PMKB_OK);
        CHECK(pmkb_surface_take_dirty(&s,&old_dirty));
        pmkb_surface_rect(&s,(PMKBRect){12,20,2,2},0);
        CHECK(s.changed_pixels==4u);
        InflightEdit edit={.surface=&s,.same_rect=same!=0};
        PMKBBackend backend={.context=&edit,.present=mutate_while_presenting};
        CHECK(pmkb_surface_present(&s,&backend)==PMKB_OK);
        CHECK(edit.calls==1&&s.has_dirty&&s.changed_pixels==5u);
        CHECK(edit.last.x==12&&edit.last.y==20&&
              edit.last.w==2&&edit.last.h==2);
        CHECK(s.dirty.x==12&&s.dirty.y==20);
        CHECK(s.dirty.w==(same?2:89)&&s.dirty.h==(same?2:101));
        CHECK(pmkb_surface_present(&s,&backend)==PMKB_OK);
        CHECK(edit.calls==2&&!s.has_dirty&&s.changed_pixels==0);
        CHECK(edit.last.x==12&&edit.last.y==20&&
              edit.last.w==(same?2:89)&&edit.last.h==(same?2:101));
        CHECK(pmkb_surface_present(&s,&backend)==PMKB_NO_CHANGE);
        pmkb_surface_free(&s);
    }
    groups++;return 0;
}


/* L03-C: fixed two-island invalidation; callback counts are synthetic.
 * No EPDC latency or waveform behavior is claimed by this host test. */
typedef struct {
    unsigned calls,fail_on;
    PMKBRect sent[8];
    size_t pixels;
} DirtyProbe;
static PMKBStatus count_rectangles(void *context,const uint8_t *gray,
                                   int w,int h,PMKBRect dirty){
    DirtyProbe *probe=(DirtyProbe*)context;
    if(!gray||w<1||h<1)return PMKB_INVALID;
    if(probe->calls>=8)return PMKB_LIMIT;
    probe->sent[probe->calls++]=dirty;
    if(probe->fail_on==probe->calls)return PMKB_INVALID;
    probe->pixels+=(size_t)dirty.w*(size_t)dirty.h;
    return PMKB_OK;
}
static int bounded_dirty_presentation(void){
    PMKBSurface s={0};PMKBRect union_rect={0};
    CHECK(pmkb_surface_init(&s,1080,1440)==PMKB_OK);
    CHECK(pmkb_surface_take_dirty(&s,&union_rect));
    CHECK(s.dirty_island_count==0);
    DirtyProbe probe={0};
    PMKBBackend backend={.context=&probe,.present=count_rectangles};
    pmkb_surface_rect(&s,(PMKBRect){0,0,1,1},0);
    pmkb_surface_rect(&s,(PMKBRect){1079,1439,1,1},0);
    CHECK(s.changed_pixels==2u&&s.dirty_island_count==2u);
    CHECK(s.dirty.w==1080&&s.dirty.h==1440);
    CHECK(pmkb_surface_present(&s,&backend)==PMKB_OK);
    CHECK(probe.calls==2&&probe.pixels==2u&&!s.has_dirty);
    CHECK(probe.sent[0].w==1&&probe.sent[0].h==1&&
          probe.sent[1].w==1&&probe.sent[1].h==1);
    CHECK(s.dirty_island_count==0u);
    printf("PMKB EINK SPLIT: 2 pixels sent in 2 callbacks "
           "instead of 1555200 pixels in 1 callback\n");

    /* Clustered swatches remain one callback: 60 changed, 228 sent. */
    probe=(DirtyProbe){0};
    for(int i=0;i<15;i++)
        pmkb_surface_rect(&s,(PMKBRect){12+i*8,24,2,2},(uint8_t)(17*i));
    CHECK(s.changed_pixels==60u);
    CHECK(pmkb_surface_present(&s,&backend)==PMKB_OK);
    CHECK(probe.calls==1&&!s.has_dirty&&probe.pixels==228u);

    /* The third island merges with an existing one, never gets lost. */
    probe=(DirtyProbe){0};
    pmkb_surface_rect(&s,(PMKBRect){0,0,1,1},200);
    pmkb_surface_rect(&s,(PMKBRect){1079,0,1,1},200);
    pmkb_surface_rect(&s,(PMKBRect){1079,1439,1,1},200);
    CHECK(s.dirty_island_count==2u);
    CHECK(pmkb_surface_present(&s,&backend)==PMKB_OK);
    CHECK(probe.calls==2&&!s.has_dirty&&probe.pixels<1555200u);

    /* A failed second callback keeps both islands until a full retry. */
    probe=(DirtyProbe){.fail_on=2};
    pmkb_surface_rect(&s,(PMKBRect){0,0,1,1},80);
    pmkb_surface_rect(&s,(PMKBRect){1079,1439,1,1},80);
    CHECK(pmkb_surface_present(&s,&backend)==PMKB_INVALID);
    CHECK(probe.calls==2&&s.has_dirty&&s.dirty_island_count==2u);
    probe=(DirtyProbe){0};
    CHECK(pmkb_surface_present(&s,&backend)==PMKB_OK);
    CHECK(probe.calls==2&&!s.has_dirty);
    pmkb_surface_free(&s);
    groups++;return 0;
}


/* L05-C: logical hitboxes of the shared keyboard on three host layouts.
 * The two Notes header rows stay 48 px; no panel mm/calibration assumed. */
static int keyboard_touch_geometry(void){
    static const int sizes[3][2]={{320,480},{1080,1440},{1440,1080}};
    for(size_t i=0;i<3;i++){
        PMKBUI ui={0};
        int w=sizes[i][0],h=sizes[i][1];
        CHECK(pmkb_ui_init(&ui,w,h)==PMKB_OK);
        CHECK(pmkb_ui_new_note(&ui,UTC)==PMKB_OK);
        PMKBNote *n=ui.notebook.items[ui.selected];
        /* Exactly two upper bars, with body starting on logical row 96. */
        int cx=w/2;
        CHECK(ui.screen.gray[(size_t)47*w+cx]==0);
        CHECK(ui.screen.gray[(size_t)48*w+cx]==247);
        CHECK(ui.screen.gray[(size_t)95*w+cx]==0);
        CHECK(ui.screen.gray[(size_t)96*w+cx]==255);
        CHECK(pmkb_ui_event(&ui,(PMKBEvent){
            .kind=PMKB_EVENT_TOGGLE_KEYBOARD},UTC)==PMKB_OK);
        CHECK(ui.keyboard.visible);
        int rowh=w>=680?94:44;
        int top=h-PMKB_KB_ROWS*rowh;
        CHECK(top>=96 && top+PMKB_KB_ROWS*rowh==h);
        CHECK(rowh>=PMKB_TOUCH_MIN);
        /* Row zero: character at the centre of its full touch column. */
        int x=(2*0+1)*w/(2*PMKB_KB_COLS);
        CHECK(pmkb_ui_event(&ui,(PMKBEvent){
            .kind=PMKB_EVENT_TAP,.x=x,.y=top+rowh/2},UTC)==PMKB_OK);
        CHECK(strcmp(n->title.data,"a")==0);
        /* Row five, last cell: Enter moves to body without closing KB. */
        x=(2*5+1)*w/(2*PMKB_KB_COLS);
        CHECK(pmkb_ui_event(&ui,(PMKBEvent){
            .kind=PMKB_EVENT_TAP,.x=x,.y=top+5*rowh+rowh/2},UTC)==PMKB_OK);
        CHECK(ui.focus==PMKB_FOCUS_BODY&&ui.keyboard.visible);
        /* SPACE is rendered across two columns: both halves must work. */
        for(int col=2;col<=3;col++){
            x=(2*col+1)*w/(2*PMKB_KB_COLS);
            CHECK(pmkb_ui_event(&ui,(PMKBEvent){
                .kind=PMKB_EVENT_TAP,.x=x,.y=top+5*rowh+rowh/2},UTC)==PMKB_OK);
        }
        CHECK(strcmp(n->body.data,"  ")==0&&n->body.cursor==2);
        /* The two halves of LEFT and RIGHT are both real tap targets. */
        for(int col=0;col<4;col++){
            x=(2*col+1)*w/(2*PMKB_KB_COLS);
            CHECK(pmkb_ui_event(&ui,(PMKBEvent){
                .kind=PMKB_EVENT_TAP,.x=x,.y=top+6*rowh+rowh/2},UTC)==PMKB_OK);
            CHECK(n->body.cursor==(size_t)(col==0?1:col==1?0:col==2?1:2));
        }
        /* The right half of the shared HIDE target must close keyboard. */
        x=(2*5+1)*w/(2*PMKB_KB_COLS);
        CHECK(pmkb_ui_event(&ui,(PMKBEvent){
            .kind=PMKB_EVENT_TAP,.x=x,.y=top+6*rowh+rowh/2},UTC)==PMKB_OK);
        CHECK(!ui.keyboard.visible);
        pmkb_ui_free(&ui);
    }
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
    if(utf8_edit()||keyboard_actions()||scientific_keyboard()||
       empty_title_blur()||title_blur_navigation()||notebook_memory()||
       dirty_canvas()||gray16_invalidation_budget()||
       ui_flow()||keyboard_touch_geometry()||high_resolution_budget()||
       backend_retry()||backend_edits_during_present()||
       bounded_dirty_presentation())return 1;
    printf("PMKB NATIVE: %u assertions PASS, %u groups PASS, 0 FAIL\n",
           checked,groups);
    return 0;
}
