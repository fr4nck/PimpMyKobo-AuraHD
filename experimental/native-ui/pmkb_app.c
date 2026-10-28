#include "pmkb_ui.h"
#include <string.h>
#include <stdio.h>

#define TOP 48
#define TITLE_ROW 48
#define BODY_START 96
#define ROW 44

static PMKBNote *selected(PMKBUI *ui){
    return ui && ui->selected<ui->notebook.count?
           ui->notebook.items[ui->selected]:NULL;
}
static PMKBText *active(PMKBUI *ui){
    PMKBNote *note=selected(ui);
    return !note?NULL:ui->focus==PMKB_FOCUS_TITLE?&note->title:&note->body;
}
static void bar(PMKBSurface *s,PMKBRect rect,uint8_t shade){
    pmkb_surface_rect(s,rect,shade);
    pmkb_surface_rect(s,(PMKBRect){rect.x,rect.y+rect.h-2,rect.w,2},0);
}
static void border(PMKBSurface *s,PMKBRect rect,uint8_t shade){
    pmkb_surface_rect(s,(PMKBRect){rect.x,rect.y,rect.w,2},shade);
    pmkb_surface_rect(s,(PMKBRect){rect.x,rect.y+rect.h-2,rect.w,2},shade);
    pmkb_surface_rect(s,(PMKBRect){rect.x,rect.y,2,rect.h},shade);
    pmkb_surface_rect(s,(PMKBRect){rect.x+rect.w-2,rect.y,2,rect.h},shade);
}
static int keyboard_row_height(const PMKBUI *ui){
    return ui->screen.width>=680?94:ROW;
}
static int keyboard_top(const PMKBUI *ui){
    int top=ui->screen.height-PMKB_KB_ROWS*keyboard_row_height(ui);
    return top<BODY_START?BODY_START:top;
}
static void draw_top(PMKBUI *ui){
    PMKBSurface *s=&ui->screen;
    bar(s,(PMKBRect){0,0,s->width,TOP},238);
    pmkb_surface_text(s,14,13,"+",0,40);
    pmkb_surface_text(s,53,13,"MENU",0,45);
    pmkb_surface_text(s,103,13,"KB",0,41);
    if(ui->view==PMKB_VIEW_LIST)
        pmkb_surface_text(s,170,13,"MES NOTES",0,s->width-175);
}
static void draw_second(PMKBUI *ui){
    PMKBSurface *s=&ui->screen;
    bar(s,(PMKBRect){0,TITLE_ROW,s->width,TOP},247);
    if(ui->view==PMKB_VIEW_EDITOR){
        PMKBNote *n=selected(ui);
        if(!n)return;
        pmkb_surface_text(s,7,61,"TITRE",0,64);
        pmkb_surface_text_box(s,70,61,n->title.data,0,s->width-172,33);
        pmkb_surface_text(s,s->width-84,61,"TEXTE",0,78);
        if(ui->focus==PMKB_FOCUS_TITLE)
            border(s,(PMKBRect){65,50,s->width-150,44},0);
        else border(s,(PMKBRect){s->width-86,50,85,44},0);
    }else pmkb_surface_text(s,8,62,"CARNET / RAM",0,s->width-18);
}
static void draw_body(PMKBUI *ui){
    PMKBSurface *s=&ui->screen;
    int bottom=ui->keyboard.visible?keyboard_top(ui):s->height;
    if(bottom<=BODY_START)return;
    pmkb_surface_rect(s,(PMKBRect){0,BODY_START,s->width,bottom-BODY_START},255);
    if(ui->view==PMKB_VIEW_LIST){
        if(!ui->notebook.count){
            pmkb_surface_text(s,12,BODY_START+18,"CARNET VIDE",0,s->width-24);
            pmkb_surface_text(s,12,BODY_START+46,"+ POUR CREER",0,s->width-24);
        }else{
            for(size_t i=0;i<ui->notebook.count && i<6;i++){
                int y=BODY_START+8+(int)i*52;
                if(y+50>bottom)break;
                PMKBNote *n=ui->notebook.items[ui->notebook.count-1-i];
                pmkb_surface_text(s,10,y+10,n->title.data,0,s->width-20);
                pmkb_surface_rect(s,(PMKBRect){8,y+43,s->width-16,1},110);
            }
        }
        return;
    }
    PMKBNote *n=selected(ui);
    if(!n)return;
    int width=s->width-24;
    pmkb_surface_text_box(s,12,BODY_START+12,n->body.data,0,
                          width,bottom-BODY_START-18);
    if(ui->focus==PMKB_FOCUS_BODY && bottom-BODY_START>=10)
        border(s,(PMKBRect){3,BODY_START+2,s->width-6,bottom-BODY_START-4},135);
}
static void draw_keyboard(PMKBUI *ui){
    if(!ui->keyboard.visible)return;
    PMKBSurface *s=&ui->screen;
    int y0=keyboard_top(ui);
    pmkb_surface_rect(s,(PMKBRect){0,y0,s->width,s->height-y0},230);
    int row_height=keyboard_row_height(ui);
    for(int row=0;row<PMKB_KB_ROWS;row++){
        int seen=-1;
        for(int col=0;col<PMKB_KB_COLS;col++){
            PMKBKey key=pmkb_keyboard_key(&ui->keyboard,row,col);
            int left=col*s->width/PMKB_KB_COLS;
            int right=(col+1)*s->width/PMKB_KB_COLS;
            /* Duplicate span cells remain one touch target. */
            if(col==3&&row==5)continue;
            if(col==1&&row==6)continue;
            if(col==3&&row==6)continue;
            if(col==5&&row==6)continue;
            if(key.span==2)right=(col+2)*s->width/PMKB_KB_COLS;
            int y=y0+row*row_height;
            if(y>=s->height)break;
            int h=row_height<s->height-y?row_height:s->height-y;
            PMKBRect cell={left+2,y+2,right-left-4,h-4};
            if(cell.w<=0||cell.h<=0)continue;
            pmkb_surface_rect(s,cell,255);
            border(s,cell,0);
            const char *label=key.action==PMKB_KEY_ENTER?"OK":
                key.action==PMKB_KEY_BACKSPACE?"DEL":
                key.action==PMKB_KEY_SPACE?"SPC":
                key.action==PMKB_KEY_LEFT?"<":
                key.action==PMKB_KEY_RIGHT?">":
                key.action==PMKB_KEY_HIDE?"X":key.label;
            pmkb_surface_text(s,left+7,y+11,label,0,right-left-10);
            seen=col;
        }
        (void)seen;
    }
}
void pmkb_ui_draw(PMKBUI *ui){
    if(!ui||!ui->screen.gray||ui->initial_drawn)return;
    draw_top(ui);draw_second(ui);draw_body(ui);draw_keyboard(ui);
    ui->initial_drawn=true;ui->render_calls++;
}
PMKBStatus pmkb_ui_init(PMKBUI *ui,int width,int height){
    if(!ui)return PMKB_INVALID;
    memset(ui,0,sizeof(*ui));
    pmkb_notebook_init(&ui->notebook);
    PMKBStatus rc=pmkb_surface_init(&ui->screen,width,height);
    if(rc!=PMKB_OK)return rc;
    ui->view=PMKB_VIEW_LIST;ui->focus=PMKB_FOCUS_BODY;
    pmkb_ui_draw(ui);return PMKB_OK;
}
void pmkb_ui_free(PMKBUI *ui){
    if(!ui)return;
    pmkb_notebook_free(&ui->notebook);
    pmkb_surface_free(&ui->screen);memset(ui,0,sizeof(*ui));
}
/* ADR-005: a blank title is legal during editing, but never on exit.
 * Reuse the JSON exporter's exact Unicode whitespace predicate. */
static PMKBStatus normalize_title_on_leave(PMKBUI *ui){
    if(ui->view!=PMKB_VIEW_EDITOR||ui->focus!=PMKB_FOCUS_TITLE)
        return PMKB_OK;
    PMKBNote *n=selected(ui);
    if(!n)return PMKB_NOT_FOUND;
    if(pmkb_notes_meaningful_title(n->title.data))return PMKB_OK;
    unsigned number=0;
    if(sscanf(n->id,"pmkb_%u",&number)!=1 || number==0)
        return PMKB_INVALID;
    char fallback[32];
    (void)snprintf(fallback,sizeof(fallback),"Sans titre %u",number);
    return pmkb_text_set(&n->title,fallback);
}
PMKBStatus pmkb_ui_new_note(PMKBUI *ui,const char *utc){
    if(!ui||!ui->screen.gray||!pmkb_notes_valid_utc(utc))return PMKB_INVALID;
    PMKBStatus rc=normalize_title_on_leave(ui);
    if(rc!=PMKB_OK)return rc;
    size_t index=0;
    rc=pmkb_notebook_new(&ui->notebook,utc,&index);
    if(rc!=PMKB_OK)return rc;
    ui->selected=index;ui->view=PMKB_VIEW_EDITOR;ui->focus=PMKB_FOCUS_TITLE;
    PMKBText *title=&ui->notebook.items[index]->title;
    (void)pmkb_text_select(title,0,title->bytes); /* overwrite default Sans titre */
    pmkb_keyboard_close(&ui->keyboard);
    draw_top(ui);draw_second(ui);draw_body(ui);ui->render_calls++;
    return PMKB_OK;
}
PMKBStatus pmkb_ui_open_note(PMKBUI *ui,size_t index){
    if(!ui||!ui->screen.gray||index>=ui->notebook.count)return PMKB_NOT_FOUND;
    PMKBStatus rc=normalize_title_on_leave(ui);
    if(rc!=PMKB_OK)return rc;
    ui->selected=index;ui->view=PMKB_VIEW_EDITOR;ui->focus=PMKB_FOCUS_BODY;
    pmkb_keyboard_close(&ui->keyboard);
    draw_top(ui);draw_second(ui);draw_body(ui);ui->render_calls++;
    return PMKB_OK;
}
PMKBStatus pmkb_ui_show_list(PMKBUI *ui){
    if(!ui||!ui->screen.gray)return PMKB_INVALID;
    PMKBStatus rc=normalize_title_on_leave(ui);
    if(rc!=PMKB_OK)return rc;
    ui->view=PMKB_VIEW_LIST;
    pmkb_keyboard_close(&ui->keyboard);
    draw_top(ui);draw_second(ui);draw_body(ui);ui->render_calls++;
    return PMKB_OK;
}
static void redraw_focus(PMKBUI *ui){
    draw_second(ui);draw_body(ui);ui->render_calls++;
}
/* ADR-005: keep an empty title editable, restore "Sans titre" only
 * when leaving that field for the body. Never rewrite while typing. */
static PMKBStatus focus_body(PMKBUI *ui){
    PMKBNote *note=selected(ui);
    if(!note)return PMKB_NOT_FOUND;
    PMKBStatus rc=normalize_title_on_leave(ui);
    if(rc!=PMKB_OK)return rc;
    ui->focus=PMKB_FOCUS_BODY;redraw_focus(ui);
    return PMKB_OK;
}
static PMKBStatus changed(PMKBUI *ui,PMKBStatus rc,const char *utc){
    if(rc==PMKB_OK){
        if(ui->view==PMKB_VIEW_EDITOR){
            PMKBNote *n=selected(ui);
            if(n){
                /* The native host owns time and must supply a real UTC ISO timestamp. */
                memcpy(n->updated,utc,strlen(utc)+1);
            }
        }
        redraw_focus(ui);
    }
    return rc;
}
static PMKBStatus press_keyboard(PMKBUI *ui,int row,int col,const char *utc){
    PMKBText *text=active(ui);
    if(!text)return PMKB_NOT_FOUND;
    PMKBKey key=pmkb_keyboard_key(&ui->keyboard,row,col);
    if(!key.span)return PMKB_INVALID;
    if(key.action==PMKB_KEY_ENTER&&ui->focus==PMKB_FOCUS_TITLE)
        return focus_body(ui);
    if((key.action==PMKB_KEY_INSERT||key.action==PMKB_KEY_SPACE||
        key.action==PMKB_KEY_BACKSPACE||key.action==PMKB_KEY_ENTER||
        key.action==PMKB_KEY_CLEAR) &&
       !pmkb_notes_valid_utc(utc))return PMKB_INVALID;
    bool current=ui->keyboard.visible;
    PMKBStatus rc=pmkb_keyboard_press(&ui->keyboard,text,key,
                                       ui->focus==PMKB_FOCUS_BODY);
    if(current && !ui->keyboard.visible){
        draw_body(ui);ui->render_calls++;
        return PMKB_OK;
    }
    if(key.action==PMKB_KEY_SHIFT||key.action==PMKB_KEY_MODE||
       key.action==PMKB_KEY_ANGLE){
        draw_keyboard(ui);ui->render_calls++;
        return rc;
    }
    if(rc==PMKB_OK && (key.action==PMKB_KEY_INSERT||
                       key.action==PMKB_KEY_SPACE||
                       key.action==PMKB_KEY_BACKSPACE||
                       key.action==PMKB_KEY_ENTER||
                       key.action==PMKB_KEY_CLEAR)){
        rc=changed(ui,rc,utc);
        if(ui->keyboard.shifted==false)draw_keyboard(ui);
        return rc;
    }
    if(rc==PMKB_OK)redraw_focus(ui); /* caret move */
    return rc;
}
static PMKBStatus tap(PMKBUI *ui,int x,int y,const char *utc){
    if(x<0||y<0||x>=ui->screen.width||y>=ui->screen.height)return PMKB_INVALID;
    if(ui->keyboard.visible&&y>=keyboard_top(ui)){
        int row=(y-keyboard_top(ui))/keyboard_row_height(ui);
        int col=x*PMKB_KB_COLS/ui->screen.width;
        return press_keyboard(ui,row,col,utc);
    }
    if(y<TOP){
        if(x<48)return pmkb_ui_new_note(ui,utc);
        if(x<96)return pmkb_ui_show_list(ui);
        if(x<144&&ui->view==PMKB_VIEW_EDITOR){
            if(ui->keyboard.visible){
                pmkb_keyboard_close(&ui->keyboard);
                draw_body(ui);
            }else{
                pmkb_keyboard_open(&ui->keyboard,PMKB_KB_AZERTY);
                draw_body(ui);draw_keyboard(ui);
            }
            ui->render_calls++;return PMKB_OK;
        }
        return PMKB_NO_CHANGE;
    }
    if(y<BODY_START){
        if(ui->view==PMKB_VIEW_EDITOR){
            if(x>=ui->screen.width-90)return focus_body(ui);
            ui->focus=PMKB_FOCUS_TITLE;redraw_focus(ui);return PMKB_OK;
        }
        return PMKB_NO_CHANGE;
    }
    if(ui->view==PMKB_VIEW_LIST){
        int row=(y-BODY_START-8)/52;
        if(y>=BODY_START+8&&row>=0&&(size_t)row<ui->notebook.count&&row<6)
            return pmkb_ui_open_note(ui,ui->notebook.count-1u-(size_t)row);
        return PMKB_NO_CHANGE;
    }
    if(ui->focus!=PMKB_FOCUS_BODY)return focus_body(ui);
    return PMKB_OK;
}
PMKBStatus pmkb_ui_event(PMKBUI *ui,PMKBEvent ev,const char *utc){
    if(!ui||!ui->screen.gray)return PMKB_INVALID;
    if(ev.kind==PMKB_EVENT_TAP)return tap(ui,ev.x,ev.y,utc);
    if(ev.kind==PMKB_EVENT_SHOW_LIST)return pmkb_ui_show_list(ui);
    if(ev.kind==PMKB_EVENT_TOGGLE_KEYBOARD){
        if(ui->view!=PMKB_VIEW_EDITOR)return PMKB_NOT_FOUND;
        if(ui->keyboard.visible){
            pmkb_keyboard_close(&ui->keyboard);draw_body(ui);
        }else{
            pmkb_keyboard_open(&ui->keyboard,PMKB_KB_AZERTY);
            draw_body(ui);draw_keyboard(ui);
        }
        ui->render_calls++;return PMKB_OK;
    }
    if(ui->view!=PMKB_VIEW_EDITOR)return PMKB_NOT_FOUND;
    PMKBText *text=active(ui);if(!text)return PMKB_NOT_FOUND;
    if((ev.kind==PMKB_EVENT_TEXT||ev.kind==PMKB_EVENT_BACKSPACE||
        ev.kind==PMKB_EVENT_ENTER) && !pmkb_notes_valid_utc(utc))
        return PMKB_INVALID; /* Reject bad metadata BEFORE changing the text. */
    PMKBStatus rc=PMKB_NO_CHANGE;
    switch(ev.kind){
    case PMKB_EVENT_TEXT:
        if(!ev.text)return PMKB_INVALID;
        if(ui->focus==PMKB_FOCUS_TITLE &&
           (strchr(ev.text,'\n')||strchr(ev.text,'\t')))return PMKB_INVALID;
        rc=pmkb_text_insert(text,ev.text);break;
    case PMKB_EVENT_BACKSPACE:rc=pmkb_text_backspace(text);break;
    case PMKB_EVENT_LEFT:rc=pmkb_text_move(text,-1);break;
    case PMKB_EVENT_RIGHT:rc=pmkb_text_move(text,1);break;
    case PMKB_EVENT_ENTER:
        if(ui->focus==PMKB_FOCUS_TITLE)return focus_body(ui);
        rc=pmkb_text_insert(text,"\n");break;
    default:return PMKB_INVALID;
    }
    return changed(ui,rc,utc);
}
