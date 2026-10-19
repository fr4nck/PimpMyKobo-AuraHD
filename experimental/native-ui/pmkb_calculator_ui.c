#include "pmkb_calculator_ui.h"
#include <stdio.h>
#include <string.h>

/* The simulator renders visible pixels; all hardware remains behind PMKB-HAL.
 * The top line contains CALC / SCI / AC / DEG controls; line two displays
 * the expression. Result is underneath. The 7-row common keyboard is
 * attached to the bottom; there is no idle refresh thread. */
#define KB_ROW_H 44
#define HEAD_H 48
#define INPUT_H 48
#define RESULT_H 72

static int keyboard_top(const PMKBCalcUI *ui){
    return ui->screen.height-PMKB_KB_ROWS*KB_ROW_H;
}
static void outline(PMKBSurface *s,PMKBRect r){
    pmkb_surface_rect(s,(PMKBRect){r.x,r.y,r.w,2},0);
    pmkb_surface_rect(s,(PMKBRect){r.x,r.y+r.h-2,r.w,2},0);
    pmkb_surface_rect(s,(PMKBRect){r.x,r.y,2,r.h},0);
    pmkb_surface_rect(s,(PMKBRect){r.x+r.w-2,r.y,2,r.h},0);
}
/* Host ASCII renderer has no French glyphs yet. Only the display preview
 * substitutes Unicode codepoints: the UTF-8 expression remains untouched. */
static void preview(const char *input,char *out,size_t capacity){
    if(!out||capacity<2)return;
    size_t length=0;
    for(const unsigned char *p=(const unsigned char*)input;*p;p++){
        if((*p&0xc0u)==0x80u)continue;
        char c=(*p>=32&&*p<127)?(char)*p:'?';
        if(length>=capacity-1){
            memmove(out,out+1,capacity-2);
            length=capacity-2;
        }
        out[length++]=c;
    }
    out[length]=0;
}
static void draw_header(PMKBCalcUI *ui){
    PMKBSurface *s=&ui->screen;
    pmkb_surface_rect(s,(PMKBRect){0,0,s->width,HEAD_H},235);
    outline(s,(PMKBRect){0,0,s->width,HEAD_H});
    pmkb_surface_text(s,10,12,"PMKB CALC",0,s->width/2-24);
    pmkb_surface_text(s,s->width-148,12,"SCI",0,43);
    pmkb_surface_text(s,s->width-98,12,"AC",0,43);
    pmkb_surface_text(s,s->width-45,12,
                      ui->keyboard.degrees?"DEG":"RAD",0,43);
}
static void draw_expression(PMKBCalcUI *ui){
    PMKBSurface *s=&ui->screen;
    pmkb_surface_rect(s,(PMKBRect){0,HEAD_H,s->width,INPUT_H},255);
    outline(s,(PMKBRect){0,HEAD_H,s->width,INPUT_H});
    char text[35]={0};
    preview(ui->expression.data?ui->expression.data:"",text,sizeof(text));
    pmkb_surface_text(s,8,HEAD_H+15,text,0,s->width-16);
}
static void draw_result(PMKBCalcUI *ui){
    PMKBSurface *s=&ui->screen;
    int y=HEAD_H+INPUT_H;
    pmkb_surface_rect(s,(PMKBRect){0,y,s->width,RESULT_H},255);
    pmkb_surface_text(s,9,y+8,ui->math_status==PMKB_CALC_OK?"RESULT":"ERREUR",
                      0,s->width-18);
    const char *shown=ui->math_status==PMKB_CALC_OK?
                      ui->result:ui->message;
    pmkb_surface_text(s,9,y+35,shown,0,s->width-18);
    pmkb_surface_rect(s,(PMKBRect){0,y+RESULT_H-2,s->width,2},0);
}
static void draw_keyboard(PMKBCalcUI *ui){
    PMKBSurface *s=&ui->screen;
    int y0=keyboard_top(ui);
    pmkb_surface_rect(s,(PMKBRect){0,y0,s->width,s->height-y0},232);
    if(!ui->keyboard.visible)return;
    for(int row=0;row<PMKB_KB_ROWS;row++){
        for(int col=0;col<PMKB_KB_COLS;col++){
            /* Both halves of a two-column key map to the same action. */
            if(row==5&&col==3)continue;
            if(row==6&&(col==1||col==3||col==5))continue;
            PMKBKey key=pmkb_keyboard_key(&ui->keyboard,row,col);
            if(key.span<=0)continue;
            int x=col*s->width/PMKB_KB_COLS;
            int right=(col+key.span)*s->width/PMKB_KB_COLS;
            int y=y0+row*KB_ROW_H;
            if(y>=s->height)break;
            int height=KB_ROW_H<s->height-y?KB_ROW_H:s->height-y;
            PMKBRect cell={x+2,y+2,right-x-4,height-4};
            if(cell.w<5||cell.h<5)continue;
            pmkb_surface_rect(s,cell,255);
            outline(s,cell);
            /* Use short aliases until a real font backend is qualified. */
            const char *name=key.label;
            if(key.action==PMKB_KEY_HIDE)name="X";
            else if(key.action==PMKB_KEY_LEFT)name="<";
            else if(key.action==PMKB_KEY_RIGHT)name=">";
            else if(key.action==PMKB_KEY_BACKSPACE)name="DEL";
            pmkb_surface_text(s,x+5,y+12,name,0,right-x-10);
        }
    }
}
static void redraw(PMKBCalcUI *ui,bool head,bool expr,bool result,bool keys){
    if(head)draw_header(ui);
    if(expr)draw_expression(ui);
    if(result)draw_result(ui);
    if(keys)draw_keyboard(ui);
    ui->render_calls++;
}
PMKBStatus pmkb_calc_ui_init(PMKBCalcUI *ui,int width,int height){
    if(!ui)return PMKB_INVALID;
    memset(ui,0,sizeof(*ui));
    PMKBStatus rc=pmkb_text_init(&ui->expression,PMKB_CALC_MAX_UNITS,"");
    if(rc!=PMKB_OK)return rc;
    rc=pmkb_surface_init(&ui->screen,width,height);
    if(rc!=PMKB_OK){
        pmkb_text_free(&ui->expression);return rc;
    }
    pmkb_keyboard_open(&ui->keyboard,PMKB_KB_SCIENTIFIC);
    memcpy(ui->result,"0",2);
    ui->math_status=PMKB_CALC_OK;
    redraw(ui,true,true,true,true);
    return PMKB_OK;
}
void pmkb_calc_ui_free(PMKBCalcUI *ui){
    if(!ui)return;
    pmkb_text_free(&ui->expression);
    pmkb_surface_free(&ui->screen);
    memset(ui,0,sizeof(*ui));
}
PMKBStatus pmkb_calc_ui_set_expression(PMKBCalcUI *ui,const char *expression){
    if(!ui||!ui->screen.gray)return PMKB_INVALID;
    PMKBStatus rc=pmkb_text_set(&ui->expression,expression);
    if(rc!=PMKB_OK)return rc;
    ui->math_status=PMKB_CALC_OK;ui->message[0]=0;
    redraw(ui,false,true,true,false);
    return PMKB_OK;
}
PMKBStatus pmkb_calc_ui_evaluate(PMKBCalcUI *ui){
    if(!ui||!ui->screen.gray)return PMKB_INVALID;
    double value=0;
    PMKBCalcStatus rc=pmkb_calc_evaluate(ui->expression.data,
                           ui->keyboard.degrees,ui->ans,&value);
    ui->math_status=rc;
    if(rc!=PMKB_CALC_OK){
        (void)snprintf(ui->message,sizeof(ui->message),"%s",
                       pmkb_calc_error(rc));
        redraw(ui,false,false,true,false);
        return PMKB_INVALID;
    }
    if(!pmkb_calc_format(value,ui->result,sizeof(ui->result))){
        ui->math_status=PMKB_CALC_RANGE;
        (void)snprintf(ui->message,sizeof(ui->message),"%s",
                       pmkb_calc_error(ui->math_status));
        redraw(ui,false,false,true,false);
        return PMKB_INVALID;
    }
    /* Only a successful calculation changes Ans and the history. */
    ui->ans=value;ui->has_ans=true;ui->message[0]=0;
    for(size_t n=PMKB_CALC_HISTORY_LIMIT-1;n>0;n--)
        ui->history[n]=ui->history[n-1];
    PMKBCalcHistory *entry=&ui->history[0];
    (void)snprintf(entry->expression,sizeof(entry->expression),"%s",
                   ui->expression.data);
    (void)snprintf(entry->result,sizeof(entry->result),"%s",ui->result);
    entry->degrees=ui->keyboard.degrees;
    if(ui->history_count<PMKB_CALC_HISTORY_LIMIT)ui->history_count++;
    redraw(ui,false,false,true,false);
    return PMKB_OK;
}
void pmkb_calc_ui_clear(PMKBCalcUI *ui,bool all){
    if(!ui||!ui->screen.gray)return;
    (void)pmkb_text_set(&ui->expression,"");
    memcpy(ui->result,"0",2);
    ui->message[0]=0;ui->math_status=PMKB_CALC_OK;
    if(all){
        ui->ans=0;ui->has_ans=false;
        memset(ui->history,0,sizeof(ui->history));
        ui->history_count=0;
    }
    redraw(ui,false,true,true,false);
}
PMKBStatus pmkb_calc_ui_press(PMKBCalcUI *ui,int row,int col){
    if(!ui||!ui->screen.gray||!ui->keyboard.visible||
       row<0||row>=PMKB_KB_ROWS||col<0||col>=PMKB_KB_COLS)return PMKB_INVALID;
    PMKBKey key=pmkb_keyboard_key(&ui->keyboard,row,col);
    if(!key.span)return PMKB_INVALID;
    bool was_shift=ui->keyboard.shifted;
    PMKBKeyboardPage page=ui->keyboard.page;
    PMKBStatus rc=pmkb_keyboard_press(&ui->keyboard,&ui->expression,key,false);
    if(rc==PMKB_EVALUATE)return pmkb_calc_ui_evaluate(ui);
    if(rc!=PMKB_OK)return rc;
    if(key.action==PMKB_KEY_ANGLE||key.action==PMKB_KEY_SHIFT||
       key.action==PMKB_KEY_MODE||key.action==PMKB_KEY_HIDE){
        redraw(ui,key.action==PMKB_KEY_ANGLE,false,false,true);
    }else{
        ui->math_status=PMKB_CALC_OK;ui->message[0]=0;
        if(key.action==PMKB_KEY_CLEAR){
            memcpy(ui->result,"0",2);
            redraw(ui,false,true,true,false);
        }else{
            bool redraw_keys=was_shift!=ui->keyboard.shifted||
                             page!=ui->keyboard.page;
            redraw(ui,false,true,true,redraw_keys);
        }
    }
    return PMKB_OK;
}
PMKBStatus pmkb_calc_ui_event(PMKBCalcUI *ui,PMKBEvent event){
    if(!ui||!ui->screen.gray)return PMKB_INVALID;
    if(event.kind==PMKB_EVENT_TAP){
        int x=event.x,y=event.y;
        if(x<0||y<0||x>=ui->screen.width||y>=ui->screen.height)
            return PMKB_INVALID;
        if(ui->keyboard.visible&&y>=keyboard_top(ui)){
            int row=(y-keyboard_top(ui))/KB_ROW_H;
            int col=x*PMKB_KB_COLS/ui->screen.width;
            return pmkb_calc_ui_press(ui,row,col);
        }
        if(y<HEAD_H){
            if(x>=ui->screen.width-51){
                ui->keyboard.degrees=!ui->keyboard.degrees;
                redraw(ui,true,false,false,ui->keyboard.visible);
                return PMKB_OK;
            }
            if(x>=ui->screen.width-103){
                pmkb_calc_ui_clear(ui,true);return PMKB_OK;
            }
            if(x>=ui->screen.width-154){
                bool degrees=ui->keyboard.degrees;
                pmkb_keyboard_open(&ui->keyboard,PMKB_KB_SCIENTIFIC);
                ui->keyboard.degrees=degrees;
                redraw(ui,true,false,false,true);return PMKB_OK;
            }
        }
        return PMKB_NO_CHANGE;
    }
    if(event.kind==PMKB_EVENT_TOGGLE_KEYBOARD){
        if(ui->keyboard.visible)pmkb_keyboard_close(&ui->keyboard);
        else {
            bool degrees=ui->keyboard.degrees;
            pmkb_keyboard_open(&ui->keyboard,PMKB_KB_SCIENTIFIC);
            ui->keyboard.degrees=degrees;
        }
        redraw(ui,false,false,false,true);
        return PMKB_OK;
    }
    if(event.kind==PMKB_EVENT_ENTER)return pmkb_calc_ui_evaluate(ui);
    if(event.kind==PMKB_EVENT_TEXT&&!event.text)return PMKB_INVALID;
    PMKBStatus rc=PMKB_INVALID;
    switch(event.kind){
    case PMKB_EVENT_TEXT:
        rc=pmkb_text_insert(&ui->expression,event.text);break;
    case PMKB_EVENT_BACKSPACE:
        rc=pmkb_text_backspace(&ui->expression);break;
    case PMKB_EVENT_LEFT:rc=pmkb_text_move(&ui->expression,-1);break;
    case PMKB_EVENT_RIGHT:rc=pmkb_text_move(&ui->expression,1);break;
    default:return PMKB_INVALID;
    }
    if(rc==PMKB_OK){
        ui->math_status=PMKB_CALC_OK;ui->message[0]=0;
        redraw(ui,false,true,true,false);
    }
    return rc;
}
