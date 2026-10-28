/* PMKB native scientific calculator tests: C11, off-device, no I/O except output. */
#include "../pmkb_calculator_ui.h"
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static unsigned checked=0,groups=0;
#define CHECK(cond) do {checked++;if(!(cond)){ \
    fprintf(stderr,"CALC FAIL %s:%d %s\n",__FILE__,__LINE__,#cond);return 1;\
}}while(0)
#define DEGREES true
#define RADIANS false
static bool approx(double actual,double expected){
    return isfinite(actual) &&
           fabs(actual-expected)<=1e-10*fmax(1.0,fabs(expected));
}
static int math_precedence(void){
    const struct {const char *expr; double expected;} cases[]={
        {"2+3*4",14},{"(2+3)*4",20},{"-2^2",-4},
        {"(-2)^2",4},{"2^3^2",512},{"2^-2",.25},
        {"100*15%",15},{"5-2-1",2},{"8/2/2",2},
        {"1+2+3+4",10},{"100*15%%",.15},{"2*(3+4)",14},
        {"5%+.25",.3},{"2e3",2000},{"1E-2",.01},
        {"1.25e2",125},{"0.00001",.00001},{"00000012.5",12.5},
        {"(2+2)^2",16},{"2/4",.5},{"1+3*5-2",14},
        {"\xe2\x88\x92""2^2",-4},{"2\xc3\x97""3",6},
        {"9\xc3\xb7""3",3},{"Ans*2",14},
        {"1 / 3",1.0/3.0},{"sin(30)^2+cos(30)^2",1}
    };
    for(size_t i=0;i<sizeof(cases)/sizeof(cases[0]);i++){
        double out=-999;
        CHECK(pmkb_calc_evaluate(cases[i].expr,DEGREES,7,&out)==PMKB_CALC_OK);
        CHECK(approx(out,cases[i].expected));
    }
    double result=101;
    CHECK(pmkb_calc_evaluate("1/2",DEGREES,0,&result)==PMKB_CALC_OK);
    CHECK(result==0.5);
    CHECK(pmkb_calc_evaluate("0-0",DEGREES,0,&result)==PMKB_CALC_OK);
    CHECK(result==0.0 && !signbit(result));
    groups++;return 0;
}
static int functions_modes(void){
    const struct { const char *expr; bool degrees;double expected;} cases[]={
        {"sin(30)",DEGREES,.5},{"cos(60)",DEGREES,.5},
        {"tan(45)",DEGREES,1},{"asin(.5)",DEGREES,30},
        {"acos(.5)",DEGREES,60},{"atan(1)",DEGREES,45},
        {"sin(\xcf\x80/2)",RADIANS,1},
        {"cos(\xcf\x80)",RADIANS,-1},
        {"asin(.5)",RADIANS,acos(-1.0)/6.0},
        {"sqrt(9)+log(100)",DEGREES,5},
        {"\xe2\x88\x9a(25)",DEGREES,5},
        {"ln(e)",DEGREES,1},{"abs(-3)",DEGREES,3},
        {"log(1e3)",DEGREES,3},
        {"Ans+1",DEGREES,8},{"sqrt(2)^2",DEGREES,2},
        {"SIN(30)",DEGREES,.5},{"atan(1)",RADIANS,acos(-1.0)/4}
    };
    for(size_t i=0;i<sizeof(cases)/sizeof(cases[0]);i++){
        double value=0;
        CHECK(pmkb_calc_evaluate(cases[i].expr,cases[i].degrees,7,&value)==PMKB_CALC_OK);
        CHECK(approx(value,cases[i].expected));
    }
    char text[40]={0};
    CHECK(pmkb_calc_format(1.0/3.0,text,sizeof(text)));
    CHECK(strcmp(text,"0.333333333333")==0);
    CHECK(pmkb_calc_format(-0.0,text,sizeof(text))&&strcmp(text,"0")==0);
    CHECK(!pmkb_calc_format(INFINITY,text,sizeof(text)));
    CHECK(!pmkb_calc_format(1.0,text,2));
    CHECK(strcmp(pmkb_calc_error(PMKB_CALC_DIV_ZERO),"Division par zero")==0);
    CHECK(strcmp(pmkb_calc_error(PMKB_CALC_OK),"")==0);
    groups++;return 0;
}
static int math_errors(void){
    const struct {const char *expr;PMKBCalcStatus status;} cases[]={
        {"",PMKB_CALC_SYNTAX},{" ",PMKB_CALC_SYNTAX},
        {"1/0",PMKB_CALC_DIV_ZERO},{"0^-1",PMKB_CALC_DIV_ZERO},
        {"sqrt(-1)",PMKB_CALC_DOMAIN},{"ln(0)",PMKB_CALC_DOMAIN},
        {"log(-10)",PMKB_CALC_DOMAIN},{"asin(2)",PMKB_CALC_DOMAIN},
        {"acos(-2)",PMKB_CALC_DOMAIN},{"tan(90)",PMKB_CALC_DOMAIN},
        {"9^999",PMKB_CALC_RANGE},{"1e999",PMKB_CALC_RANGE},
        {"2pi",PMKB_CALC_SYNTAX},{"2\xcf\x80",PMKB_CALC_SYNTAX},
        {"1,5",PMKB_CALC_SYNTAX},{"2 2",PMKB_CALC_SYNTAX},
        {"sin(30",PMKB_CALC_SYNTAX},{"(2+3",PMKB_CALC_SYNTAX},
        {"sin 30",PMKB_CALC_SYNTAX},{"3+",PMKB_CALC_SYNTAX},
        {"pi()",PMKB_CALC_SYNTAX},{"1..2",PMKB_CALC_SYNTAX},
        {"3^(1/0)",PMKB_CALC_DIV_ZERO},
        {"sqrt(1,2)",PMKB_CALC_SYNTAX},
        {"process.exit(1)",PMKB_CALC_SYNTAX},
        {"Math.random()",PMKB_CALC_SYNTAX},
        {"2;alert(1)",PMKB_CALC_SYNTAX},
        {"[1,2]",PMKB_CALC_SYNTAX},
        {"{1}",PMKB_CALC_SYNTAX},
        {"1\xf0\x9f\x98\x80",PMKB_CALC_SYNTAX},
        {"2/(1-1)",PMKB_CALC_DIV_ZERO}
    };
    for(size_t i=0;i<sizeof(cases)/sizeof(cases[0]);i++){
        double unchanged=1234.5;
        CHECK(pmkb_calc_evaluate(cases[i].expr,DEGREES,0,&unchanged)==cases[i].status);
        CHECK(unchanged==1234.5); /* errors may never corrupt caller output */
    }
    double ignored=12;
    CHECK(pmkb_calc_evaluate(NULL,DEGREES,0,&ignored)==PMKB_CALC_ARGUMENT);
    CHECK(pmkb_calc_evaluate("1+1",DEGREES,NAN,&ignored)==PMKB_CALC_ARGUMENT);
    CHECK(pmkb_calc_evaluate("1+1",DEGREES,0,NULL)==PMKB_CALC_ARGUMENT);
    CHECK(ignored==12);
    char nested[110]={0};
    for(int i=0;i<50;i++)nested[i]='(';
    nested[50]='1';
    for(int i=0;i<50;i++)nested[51+i]=')';
    CHECK(pmkb_calc_evaluate(nested,DEGREES,0,&ignored)==PMKB_CALC_LIMIT);
    char tokens[200]={0};
    size_t pos=0;
    for(int i=0;i<70;i++){
        tokens[pos++]='1';
        if(i!=69)tokens[pos++]='+';
    }
    CHECK(pmkb_calc_evaluate(tokens,DEGREES,0,&ignored)==PMKB_CALC_LIMIT);
    char longnum[200]={0};
    memset(longnum,'0',193);
    CHECK(pmkb_calc_evaluate(longnum,DEGREES,0,&ignored)==PMKB_CALC_LIMIT);
    groups++;return 0;
}
static int touch_calculation(void){
    PMKBCalcUI ui={0}; PMKBRect dirty={0};
    CHECK(pmkb_calc_ui_init(&ui,320,480)==PMKB_OK);
    CHECK(ui.keyboard.visible&&ui.keyboard.page==PMKB_KB_SCIENTIFIC);
    CHECK(ui.keyboard.degrees);
    CHECK(ui.render_calls==1&&ui.history_count==0);
    CHECK(pmkb_surface_take_dirty(&ui.screen,&dirty));
    CHECK(!pmkb_surface_take_dirty(&ui.screen,&dirty));
    int top=480-PMKB_KB_ROWS*44;
    const struct {int r,c;} sequence[]={{0,0},{3,2},{4,0},{1,5},{5,5}};
    for(size_t i=0;i<sizeof(sequence)/sizeof(sequence[0]);i++){
        PMKBEvent e={.kind=PMKB_EVENT_TAP,
             .x=sequence[i].c*320/6+5,
             .y=top+sequence[i].r*44+15};
        CHECK(pmkb_calc_ui_event(&ui,e)==PMKB_OK);
    }
    CHECK(strcmp(ui.expression.data,"sin(30)")==0);
    CHECK(strcmp(ui.result,"0.5")==0);
    CHECK(approx(ui.ans,.5)&&ui.has_ans);
    CHECK(ui.history_count==1);
    CHECK(strcmp(ui.history[0].expression,"sin(30)")==0);
    CHECK(ui.history[0].degrees);
    CHECK(pmkb_surface_take_dirty(&ui.screen,&dirty));
    CHECK(dirty.y>=48 && dirty.h<=432);
    /* RAD changes angle unit without affecting Ans. */
    CHECK(pmkb_calc_ui_press(&ui,4,5)==PMKB_OK);
    CHECK(!ui.keyboard.degrees && approx(ui.ans,.5));
    CHECK(pmkb_calc_ui_set_expression(&ui,"sin(\xcf\x80/2)")==PMKB_OK);
    CHECK(pmkb_calc_ui_press(&ui,5,5)==PMKB_OK);
    CHECK(strcmp(ui.result,"1")==0);
    CHECK(approx(ui.ans,1)&&ui.history_count==2);
    CHECK(!ui.history[0].degrees);
    CHECK(pmkb_calc_ui_set_expression(&ui,"Ans*2")==PMKB_OK);
    CHECK(pmkb_calc_ui_press(&ui,5,5)==PMKB_OK);
    CHECK(strcmp(ui.result,"2")==0&&ui.history_count==3);
    /* C retains Ans and history; AC clears both. */
    CHECK(pmkb_calc_ui_press(&ui,5,2)==PMKB_OK);
    CHECK(ui.expression.bytes==0);
    CHECK(ui.has_ans&&ui.history_count==3);
    CHECK(pmkb_calc_ui_set_expression(&ui,"1/0")==PMKB_OK);
    CHECK(pmkb_calc_ui_press(&ui,5,5)==PMKB_INVALID);
    CHECK(ui.math_status==PMKB_CALC_DIV_ZERO);
    CHECK(strstr(ui.message,"Division")!=NULL);
    CHECK(ui.ans==2&&ui.history_count==3);
    CHECK(pmkb_calc_ui_event(&ui,
      (PMKBEvent){.kind=PMKB_EVENT_TAP,.x=320-80,.y=12})==PMKB_OK);
    CHECK(!ui.has_ans&&ui.ans==0&&ui.history_count==0);
    CHECK(ui.expression.bytes==0&&strcmp(ui.result,"0")==0);
    pmkb_calc_ui_free(&ui);groups++;return 0;
}
static int touch_input_and_dirty(void){
    PMKBCalcUI ui={0}; PMKBRect dirty={0};
    CHECK(pmkb_calc_ui_init(&ui,320,480)==PMKB_OK);
    CHECK(pmkb_surface_take_dirty(&ui.screen,&dirty));
    CHECK(pmkb_calc_ui_set_expression(&ui,"3")==PMKB_OK);
    CHECK(pmkb_surface_take_dirty(&ui.screen,&dirty));
    CHECK(dirty.y>=48 && dirty.y<96);
    CHECK(dirty.y+dirty.h<=168);
    CHECK(!pmkb_surface_take_dirty(&ui.screen,&dirty));
    CHECK(pmkb_calc_ui_event(&ui,
          (PMKBEvent){.kind=PMKB_EVENT_TEXT,.text="*4"})==PMKB_OK);
    CHECK(pmkb_calc_ui_event(&ui,(PMKBEvent){.kind=PMKB_EVENT_ENTER})==PMKB_OK);
    CHECK(strcmp(ui.result,"12")==0);
    CHECK(pmkb_calc_ui_event(&ui,
          (PMKBEvent){.kind=PMKB_EVENT_LEFT})==PMKB_OK);
    CHECK(pmkb_calc_ui_event(&ui,
          (PMKBEvent){.kind=PMKB_EVENT_BACKSPACE})==PMKB_OK);
    CHECK(strcmp(ui.expression.data,"34")==0);
    CHECK(pmkb_calc_ui_event(&ui,
          (PMKBEvent){.kind=PMKB_EVENT_TEXT,.text="\xc0\xaf"})==PMKB_INVALID);
    CHECK(strcmp(ui.expression.data,"34")==0);
    CHECK(pmkb_calc_ui_event(&ui,
          (PMKBEvent){.kind=PMKB_EVENT_TAP,.x=-1,.y=12})==PMKB_INVALID);
    CHECK(pmkb_calc_ui_event(&ui,
          (PMKBEvent){.kind=PMKB_EVENT_TAP,.x=999,.y=12})==PMKB_INVALID);
    CHECK(pmkb_calc_ui_event(&ui,
          (PMKBEvent){.kind=PMKB_EVENT_TOGGLE_KEYBOARD})==PMKB_OK);
    CHECK(!ui.keyboard.visible);
    CHECK(pmkb_calc_ui_event(&ui,
          (PMKBEvent){.kind=PMKB_EVENT_TOGGLE_KEYBOARD})==PMKB_OK);
    CHECK(ui.keyboard.visible&&ui.keyboard.page==PMKB_KB_SCIENTIFIC);
    CHECK(pmkb_calc_ui_event(&ui,
          (PMKBEvent){.kind=PMKB_EVENT_TAP,.x=120,.y=12})==PMKB_NO_CHANGE);
    CHECK(pmkb_calc_ui_press(&ui,-1,5)==PMKB_INVALID);
    CHECK(pmkb_calc_ui_press(&ui,7,5)==PMKB_INVALID);
    unsigned prior=ui.render_calls;
    CHECK(pmkb_calc_ui_event(&ui,
          (PMKBEvent){.kind=PMKB_EVENT_SHOW_LIST})==PMKB_INVALID);
    CHECK(ui.render_calls==prior);
    pmkb_calc_ui_free(&ui);groups++;return 0;
}
static int high_resolution_calculator(void){
    PMKBCalcUI ui={0};PMKBRect dirty;
    CHECK(pmkb_calc_ui_init(&ui,1080,1440)==PMKB_OK);
    CHECK(ui.screen.width*ui.screen.height==1555200);
    CHECK(pmkb_surface_take_dirty(&ui.screen,&dirty));
    CHECK(pmkb_calc_ui_set_expression(&ui,"2^3^2")==PMKB_OK);
    CHECK(pmkb_surface_take_dirty(&ui.screen,&dirty));
    CHECK(dirty.h<1440);
    CHECK(pmkb_calc_ui_evaluate(&ui)==PMKB_OK);
    CHECK(strcmp(ui.result,"512")==0);
    CHECK(pmkb_surface_take_dirty(&ui.screen,&dirty));
    CHECK(dirty.y<168);
    unsigned before=ui.render_calls;
    CHECK(pmkb_calc_ui_event(&ui,
           (PMKBEvent){.kind=PMKB_EVENT_TAP,.x=0,.y=470})==PMKB_NO_CHANGE);
    CHECK(ui.render_calls==before);
    pmkb_calc_ui_free(&ui);groups++;return 0;
}
int main(void){
    if(math_precedence()||functions_modes()||math_errors()||
       touch_calculation()||touch_input_and_dirty()||
       high_resolution_calculator())return 1;
    printf("PMKB CALCULATOR: %u assertions PASS, %u groups PASS, 0 FAIL\n",
           checked,groups);
    return 0;
}
