/* PMKB-HAL V0 offline tests: source simulated, not a real driver. */
#include "../pmkb_hal.h"
#include "../pmkb_launcher_bridge.h"
#include <stdint.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#ifdef __linux__
#include <linux/input.h>
_Static_assert(PMKB_EV_SYN==EV_SYN,"Linux EV_SYN mismatch");
_Static_assert(PMKB_EV_KEY==EV_KEY,"Linux EV_KEY mismatch");
_Static_assert(PMKB_EV_ABS==EV_ABS,"Linux EV_ABS mismatch");
_Static_assert(PMKB_SYN_REPORT==SYN_REPORT,"Linux SYN_REPORT mismatch");
_Static_assert(PMKB_SYN_DROPPED==SYN_DROPPED,"Linux SYN_DROPPED mismatch");
_Static_assert(PMKB_ABS_X==ABS_X,"Linux ABS_X mismatch");
_Static_assert(PMKB_ABS_Y==ABS_Y,"Linux ABS_Y mismatch");
_Static_assert(PMKB_BTN_TOUCH==BTN_TOUCH,"Linux BTN_TOUCH mismatch");
_Static_assert(PMKB_BTN_TOOL_DOUBLETAP==BTN_TOOL_DOUBLETAP,"Linux doubletap mismatch");
#endif

static unsigned assertions=0,groups=0;
#define CHECK(c) do {assertions++;if(!(c)){ \
    fprintf(stderr,"PMKB-HAL FAIL %s:%d: %s\n",__FILE__,__LINE__,#c);return 1; \
}} while(0)

static PMKBTouchConfig config(PMKBRotation rotation){
    PMKBTouchConfig c={
        .width=1080,.height=1440,
        .x_min=0,.x_max=1440,.y_min=0,.y_max=1080,
        .mirror_x=false,.mirror_y=false,
        .rotation=rotation,.tap_slop=15
    };
    return c;
}
static void raw_coord(PMKBTouch *t,int x,int y,PMKBEvent *ev){
    (void)pmkb_touch_feed(t,PMKB_EV_ABS,PMKB_ABS_X,x,ev);
    (void)pmkb_touch_feed(t,PMKB_EV_ABS,PMKB_ABS_Y,y,ev);
}
static PMKBStatus sync_frame(PMKBTouch *t,PMKBEvent *ev){
    return pmkb_touch_feed(t,PMKB_EV_SYN,PMKB_SYN_REPORT,0,ev);
}
static PMKBStatus tap_press(PMKBTouch *t,int x,int y,PMKBEvent *event){
    raw_coord(t,x,y,event);
    (void)pmkb_touch_feed(t,PMKB_EV_KEY,PMKB_BTN_TOUCH,1,event);
    return sync_frame(t,event);
}
static PMKBStatus tap_release(PMKBTouch *t,int x,int y,PMKBEvent *event){
    raw_coord(t,x,y,event);
    (void)pmkb_touch_feed(t,PMKB_EV_KEY,PMKB_BTN_TOUCH,0,event);
    return sync_frame(t,event);
}
static int decode_taps(void){
    PMKBTouch t={0};
    PMKBEvent ev={.kind=PMKB_EVENT_TEXT,.x=777,.y=888,.text="stable"};
    CHECK(pmkb_touch_init(&t,config(PMKB_ROT_0))==PMKB_OK);
    CHECK(pmkb_touch_feed(&t,PMKB_EV_SYN,PMKB_SYN_REPORT,0,&ev)==PMKB_NO_CHANGE);
    CHECK(ev.kind==PMKB_EVENT_TEXT);
    CHECK(tap_press(&t,720,540,&ev)==PMKB_NO_CHANGE);
    CHECK(t.down&&t.candidate);
    CHECK(tap_release(&t,720,540,&ev)==PMKB_OK);
    CHECK(ev.kind==PMKB_EVENT_TAP);
    CHECK(ev.x==540&&ev.y==720&&ev.text==NULL);
    CHECK(t.taps==1&&!t.down);
    CHECK(sync_frame(&t,&ev)==PMKB_NO_CHANGE);
    CHECK(t.taps==1);
    /* Tiny jitter is a tap; large gesture is not. */
    CHECK(tap_press(&t,100,100,&ev)==PMKB_NO_CHANGE);
    CHECK(tap_release(&t,104,102,&ev)==PMKB_OK);
    CHECK(t.taps==2);
    CHECK(tap_press(&t,100,100,&ev)==PMKB_NO_CHANGE);
    raw_coord(&t,700,700,&ev);
    CHECK(sync_frame(&t,&ev)==PMKB_NO_CHANGE);
    raw_coord(&t,100,100,&ev);
    CHECK(sync_frame(&t,&ev)==PMKB_NO_CHANGE);
    CHECK(tap_release(&t,100,100,&ev)==PMKB_NO_CHANGE);
    CHECK(t.taps==2);
    /* BTN_TOUCH repeats are not interpreted as new presses. */
    CHECK(tap_press(&t,300,300,&ev)==PMKB_NO_CHANGE);
    (void)pmkb_touch_feed(&t,PMKB_EV_KEY,PMKB_BTN_TOUCH,1,&ev);
    CHECK(sync_frame(&t,&ev)==PMKB_NO_CHANGE);
    CHECK(tap_release(&t,300,300,&ev)==PMKB_OK);
    CHECK(t.taps==3);
    groups++;return 0;
}
static int rotate_mirror(void){
    struct {PMKBRotation angle;int x,y;} positions[]={
        {PMKB_ROT_0,0,0},
        {PMKB_ROT_90,1079,0},
        {PMKB_ROT_180,1079,1439},
        {PMKB_ROT_270,0,1439}
    };
    for(size_t i=0;i<sizeof(positions)/sizeof(positions[0]);i++){
        PMKBTouch t={0}; PMKBEvent event={0};
        CHECK(pmkb_touch_init(&t,config(positions[i].angle))==PMKB_OK);
        CHECK(tap_press(&t,0,0,&event)==PMKB_NO_CHANGE);
        CHECK(tap_release(&t,0,0,&event)==PMKB_OK);
        CHECK(event.x==positions[i].x&&event.y==positions[i].y);
    }
    PMKBTouch t={0};PMKBEvent event={0};
    PMKBTouchConfig c=config(PMKB_ROT_0);
    c.mirror_x=true;c.mirror_y=true;
    CHECK(pmkb_touch_init(&t,c)==PMKB_OK);
    CHECK(tap_press(&t,0,0,&event)==PMKB_NO_CHANGE);
    CHECK(tap_release(&t,0,0,&event)==PMKB_OK);
    CHECK(event.x==1079&&event.y==1439);
    c=config(PMKB_ROT_90);c.mirror_y=true;
    CHECK(pmkb_touch_init(&t,c)==PMKB_OK);
    CHECK(tap_press(&t,0,1080,&event)==PMKB_NO_CHANGE);
    CHECK(tap_release(&t,0,1080,&event)==PMKB_OK);
    CHECK(event.x==1079&&event.y==0);
    CHECK(pmkb_touch_init(&t,(PMKBTouchConfig){0})==PMKB_INVALID);
    c=config(PMKB_ROT_0);c.rotation=(PMKBRotation)45;
    CHECK(pmkb_touch_init(&t,c)==PMKB_INVALID);
    c=config(PMKB_ROT_0);c.x_max=c.x_min;
    CHECK(pmkb_touch_init(&t,c)==PMKB_INVALID);
    groups++;return 0;
}

/* Synthetic range/rotation matrix: mathematical transform, not a real dragon
 * calibration. Also guards against int overflow before the int64 scaling. */
static int extreme_abs_corner_matrix(void){
    static const PMKBRotation rotations[]={
        PMKB_ROT_0,PMKB_ROT_90,PMKB_ROT_180,PMKB_ROT_270
    };
    for(int layout=0;layout<2;layout++)
        for(size_t r=0;r<sizeof(rotations)/sizeof(rotations[0]);r++)
            for(int mirror=0;mirror<4;mirror++)
                for(int corner=0;corner<4;corner++){
                    PMKBTouch t={0};PMKBEvent event={0};
                    PMKBTouchConfig c=config(rotations[r]);
                    c.width=layout?1440:1080;
                    c.height=layout?1080:1440;
                    c.x_min=INT_MIN;c.x_max=INT_MAX;
                    c.y_min=INT_MIN;c.y_max=INT_MAX;
                    c.mirror_x=(mirror&1)!=0;
                    c.mirror_y=(mirror&2)!=0;
                    CHECK(pmkb_touch_init(&t,c)==PMKB_OK);
                    int raw_x=(corner&1)?INT_MAX:INT_MIN;
                    int raw_y=(corner&2)?INT_MAX:INT_MIN;
                    CHECK(tap_press(&t,raw_x,raw_y,&event)==PMKB_NO_CHANGE);
                    CHECK(tap_release(&t,raw_x,raw_y,&event)==PMKB_OK);
                    int ux=((corner&1)!=0)^c.mirror_x;
                    int uy=((corner&2)!=0)^c.mirror_y;
                    int ex=ux,ey=uy;
                    if(rotations[r]==PMKB_ROT_90){ex=!uy;ey=ux;}
                    else if(rotations[r]==PMKB_ROT_180){ex=!ux;ey=!uy;}
                    else if(rotations[r]==PMKB_ROT_270){ex=uy;ey=!ux;}
                    CHECK(event.kind==PMKB_EVENT_TAP&&
                          event.x==(ex?c.width-1:0)&&
                          event.y==(ey?c.height-1:0));
                }
    groups++;return 0;
}

static int missing_and_invalid_events(void){
    PMKBTouch t={0};PMKBEvent event={.kind=PMKB_EVENT_TEXT};
    CHECK(pmkb_touch_init(&t,config(PMKB_ROT_0))==PMKB_OK);
    /* A button with no measured axes cannot fabricate a screen tap. */
    (void)pmkb_touch_feed(&t,PMKB_EV_KEY,PMKB_BTN_TOUCH,1,&event);
    CHECK(sync_frame(&t,&event)==PMKB_NO_CHANGE);
    (void)pmkb_touch_feed(&t,PMKB_EV_KEY,PMKB_BTN_TOUCH,0,&event);
    CHECK(sync_frame(&t,&event)==PMKB_NO_CHANGE);
    CHECK(t.taps==0);
    CHECK(tap_press(&t,30,30,&event)==PMKB_NO_CHANGE);
    CHECK(pmkb_touch_feed(&t,PMKB_EV_SYN,PMKB_SYN_DROPPED,0,&event)==PMKB_NO_CHANGE);
    CHECK(t.drops==1&&!t.down);
    CHECK(tap_release(&t,30,30,&event)==PMKB_NO_CHANGE);
    CHECK(t.taps==0);
    CHECK(tap_press(&t,1600,30,&event)==PMKB_NO_CHANGE);
    CHECK(tap_release(&t,1600,30,&event)==PMKB_NO_CHANGE);
    CHECK(t.taps==0);
    CHECK(tap_press(&t,5,5,&event)==PMKB_NO_CHANGE);
    raw_coord(&t,-100,5,&event);
    CHECK(sync_frame(&t,&event)==PMKB_NO_CHANGE);
    CHECK(tap_release(&t,5,5,&event)==PMKB_NO_CHANGE);
    CHECK(t.taps==0);
    CHECK(pmkb_touch_feed(&t,99,99,100,&event)==PMKB_NO_CHANGE);
    CHECK(pmkb_touch_feed(&t,PMKB_EV_ABS,3000,3,&event)==PMKB_NO_CHANGE);
    CHECK(pmkb_touch_feed(&t,PMKB_EV_KEY,PMKB_BTN_TOUCH,2,&event)==PMKB_NO_CHANGE);
    CHECK(pmkb_touch_feed(NULL,0,0,0,&event)==PMKB_INVALID);
    CHECK(pmkb_touch_feed(&t,0,0,0,NULL)==PMKB_INVALID);
    groups++;return 0;
}
static int lost_frame_quarantine(void){
    PMKBTouch t={0};
    PMKBEvent ev={.kind=PMKB_EVENT_TEXT,.x=777,.y=888,.text="stable"};
    CHECK(pmkb_touch_init(&t,config(PMKB_ROT_0))==PMKB_OK);
    CHECK(tap_press(&t,100,100,&ev)==PMKB_NO_CHANGE);
    CHECK(pmkb_touch_feed(&t,PMKB_EV_SYN,PMKB_SYN_DROPPED,0,&ev)==PMKB_NO_CHANGE);
    /* Everything through this SYN_REPORT is lost, even a plausible press. */
    CHECK(tap_press(&t,100,100,&ev)==PMKB_NO_CHANGE);
    CHECK(tap_release(&t,100,100,&ev)==PMKB_NO_CHANGE);
    CHECK(t.taps==0&&t.drops==1);
    CHECK(ev.kind==PMKB_EVENT_TEXT&&ev.x==777&&ev.y==888);
    CHECK(strcmp(ev.text,"stable")==0);
    CHECK(tap_press(&t,100,100,&ev)==PMKB_NO_CHANGE);
    CHECK(tap_release(&t,100,100,&ev)==PMKB_OK);
    CHECK(t.taps==1);
    /* An up in the discarded frame is not evidence of a clean release. */
    CHECK(pmkb_touch_feed(&t,PMKB_EV_SYN,PMKB_SYN_DROPPED,0,&ev)==PMKB_NO_CHANGE);
    CHECK(pmkb_touch_feed(&t,PMKB_EV_SYN,PMKB_SYN_DROPPED,0,&ev)==PMKB_NO_CHANGE);
    CHECK(tap_release(&t,100,100,&ev)==PMKB_NO_CHANGE);
    CHECK(tap_press(&t,100,100,&ev)==PMKB_NO_CHANGE);
    CHECK(tap_release(&t,100,100,&ev)==PMKB_NO_CHANGE);
    CHECK(t.taps==1&&t.drops==3);
    /* Quarantine must also discard the axes; button-only input cannot tap. */
    (void)pmkb_touch_feed(&t,PMKB_EV_KEY,PMKB_BTN_TOUCH,1,&ev);
    CHECK(sync_frame(&t,&ev)==PMKB_NO_CHANGE);
    (void)pmkb_touch_feed(&t,PMKB_EV_KEY,PMKB_BTN_TOUCH,0,&ev);
    CHECK(sync_frame(&t,&ev)==PMKB_NO_CHANGE);
    CHECK(t.taps==1);
    CHECK(tap_press(&t,100,100,&ev)==PMKB_NO_CHANGE);
    CHECK(tap_release(&t,100,100,&ev)==PMKB_OK);
    CHECK(t.taps==2);
    groups++;return 0;
}
static int two_fingers_are_not_taps(void){
    for(int order=0;order<2;order++){
        PMKBTouch t={0};PMKBEvent ev={.kind=PMKB_EVENT_TEXT,.text="stable"};
        CHECK(pmkb_touch_init(&t,config(PMKB_ROT_0))==PMKB_OK);
        raw_coord(&t,100,100,&ev);
        if(order==0)(void)pmkb_touch_feed(&t,PMKB_EV_KEY,PMKB_BTN_TOUCH,1,&ev);
        (void)pmkb_touch_feed(&t,PMKB_EV_KEY,PMKB_BTN_TOOL_DOUBLETAP,1,&ev);
        if(order==1)(void)pmkb_touch_feed(&t,PMKB_EV_KEY,PMKB_BTN_TOUCH,1,&ev);
        CHECK(sync_frame(&t,&ev)==PMKB_NO_CHANGE);
        /* Two becomes one: BTN_TOUCH remains down, no new gesture. */
        (void)pmkb_touch_feed(&t,PMKB_EV_KEY,PMKB_BTN_TOOL_DOUBLETAP,0,&ev);
        CHECK(sync_frame(&t,&ev)==PMKB_NO_CHANGE);
        CHECK(tap_release(&t,100,100,&ev)==PMKB_NO_CHANGE);
        CHECK(t.taps==0&&ev.kind==PMKB_EVENT_TEXT);
        CHECK(strcmp(ev.text,"stable")==0);
        CHECK(tap_press(&t,100,100,&ev)==PMKB_NO_CHANGE);
        CHECK(tap_release(&t,100,100,&ev)==PMKB_OK);
        CHECK(t.taps==1);
    }
    PMKBTouch t={0};PMKBEvent ev={0};
    CHECK(pmkb_touch_init(&t,config(PMKB_ROT_0))==PMKB_OK);
    CHECK(tap_press(&t,100,100,&ev)==PMKB_NO_CHANGE);
    /* A second finger arriving later cancels the original candidate. */
    (void)pmkb_touch_feed(&t,PMKB_EV_KEY,PMKB_BTN_TOOL_DOUBLETAP,1,&ev);
    CHECK(sync_frame(&t,&ev)==PMKB_NO_CHANGE);
    /* A release is insufficient while the two-finger key remains set. */
    CHECK(tap_release(&t,100,100,&ev)==PMKB_NO_CHANGE);
    CHECK(tap_press(&t,100,100,&ev)==PMKB_NO_CHANGE);
    CHECK(tap_release(&t,100,100,&ev)==PMKB_NO_CHANGE);
    CHECK(t.taps==0);
    (void)pmkb_touch_feed(&t,PMKB_EV_KEY,PMKB_BTN_TOOL_DOUBLETAP,0,&ev);
    (void)pmkb_touch_feed(&t,PMKB_EV_KEY,PMKB_BTN_TOUCH,0,&ev);
    CHECK(sync_frame(&t,&ev)==PMKB_NO_CHANGE);
    /* Even an on/off two-finger key within one frame cancels that gesture. */
    raw_coord(&t,100,100,&ev);
    (void)pmkb_touch_feed(&t,PMKB_EV_KEY,PMKB_BTN_TOUCH,1,&ev);
    (void)pmkb_touch_feed(&t,PMKB_EV_KEY,PMKB_BTN_TOOL_DOUBLETAP,1,&ev);
    (void)pmkb_touch_feed(&t,PMKB_EV_KEY,PMKB_BTN_TOOL_DOUBLETAP,0,&ev);
    CHECK(sync_frame(&t,&ev)==PMKB_NO_CHANGE);
    CHECK(tap_release(&t,100,100,&ev)==PMKB_NO_CHANGE);
    CHECK(t.taps==0);
    CHECK(tap_press(&t,100,100,&ev)==PMKB_NO_CHANGE);
    CHECK(tap_release(&t,100,100,&ev)==PMKB_OK);
    CHECK(t.taps==1);
    groups++;return 0;
}
typedef struct {
    int width,height,copies,sends,waits;
    bool fail_copy,fail_send,fail_wait;
    uint8_t image[320u*480u];
    PMKBRect last_rect;
    uint32_t marker,last_wait;
    PMKBEinkUpdate last_mode;
} FakeEink;
static PMKBStatus fake_copy(void *context,const uint8_t *gray,
                            int width,int height,PMKBRect dirty){
    FakeEink *f=(FakeEink*)context;f->copies++;
    if(f->fail_copy)return PMKB_INVALID;
    if(!gray||width!=f->width||height!=f->height)return PMKB_INVALID;
    for(int y=dirty.y;y<dirty.y+dirty.h;y++){
        size_t pos=(size_t)y*(size_t)width+(size_t)dirty.x;
        memcpy(f->image+pos,gray+pos,(size_t)dirty.w);
    }
    f->last_rect=dirty;
    return PMKB_OK;
}
static PMKBStatus fake_send(void *context,PMKBRect dirty,
                            uint32_t marker,PMKBEinkUpdate mode){
    FakeEink *f=(FakeEink*)context;f->sends++;
    if(f->fail_send)return PMKB_INVALID;
    f->marker=marker;f->last_rect=dirty;f->last_mode=mode;
    return PMKB_OK;
}
static PMKBStatus fake_wait(void *context,uint32_t marker){
    FakeEink *f=(FakeEink*)context;f->waits++;f->last_wait=marker;
    if(f->fail_wait)return PMKB_INVALID;
    return f->marker==marker?PMKB_OK:PMKB_INVALID;
}
static PMKBEinkOps fake_ops(FakeEink *f){
    PMKBEinkOps o={
        .context=f,.copy=fake_copy,.send=fake_send,.wait=fake_wait
    };
    return o;
}
static int eink_partial_and_policy(void){
    FakeEink f={.width=320,.height=480};
    memset(f.image,0xa5,sizeof(f.image));
    PMKBEink e={0};PMKBSurface s={0};PMKBRect rect={0};
    CHECK(pmkb_eink_init(&e,320,480,fake_ops(&f))==PMKB_OK);
    CHECK(e.mode==PMKB_EINK_UPDATE_PARTIAL);
    CHECK(pmkb_surface_init(&s,320,480)==PMKB_OK);
    CHECK(pmkb_surface_take_dirty(&s,&rect));
    pmkb_surface_rect(&s,(PMKBRect){15,30,11,7},0);
    PMKBBackend backend={.context=&e,.present=pmkb_eink_present};
    CHECK(pmkb_surface_present(&s,&backend)==PMKB_OK);
    CHECK(f.copies==1&&f.sends==1&&f.waits==1);
    CHECK(e.submitted==1&&e.completed==1&&!e.in_flight);
    CHECK(f.marker==1&&f.last_wait==1);
    CHECK(f.last_mode==PMKB_EINK_UPDATE_PARTIAL);
    CHECK(f.last_rect.x==15&&f.last_rect.y==30);
    CHECK(f.last_rect.w==11&&f.last_rect.h==7);
    CHECK(f.image[30*320+15]==0);
    CHECK(f.image[0]==0xa5);
    CHECK(!s.has_dirty);
    CHECK(pmkb_surface_present(&s,&backend)==PMKB_NO_CHANGE);
    CHECK(f.copies==1);
    CHECK(pmkb_eink_set_update(&e,PMKB_EINK_UPDATE_FULL)==PMKB_OK);
    pmkb_surface_rect(&s,(PMKBRect){88,90,2,2},0);
    CHECK(pmkb_surface_present(&s,&backend)==PMKB_OK);
    CHECK(f.marker==2&&f.last_mode==PMKB_EINK_UPDATE_FULL);
    CHECK(e.completed==2);
    CHECK(pmkb_eink_set_update(&e,(PMKBEinkUpdate)55)==PMKB_INVALID);
    pmkb_surface_free(&s);
    groups++;return 0;
}
static int retry_and_marker(void){
    FakeEink f={.width=320,.height=480};
    PMKBEink e={0};PMKBSurface s={0};PMKBRect ignored={0};
    CHECK(pmkb_eink_init(&e,320,480,fake_ops(&f))==PMKB_OK);
    CHECK(pmkb_surface_init(&s,320,480)==PMKB_OK);
    CHECK(pmkb_surface_take_dirty(&s,&ignored));
    PMKBBackend backend={.context=&e,.present=pmkb_eink_present};
    pmkb_surface_rect(&s,(PMKBRect){4,4,10,10},0);
    f.fail_copy=true;
    CHECK(pmkb_surface_present(&s,&backend)==PMKB_INVALID);
    CHECK(s.has_dirty&&f.copies==1&&f.sends==0&&!e.in_flight);
    f.fail_copy=false;f.fail_send=true;
    CHECK(pmkb_surface_present(&s,&backend)==PMKB_INVALID);
    CHECK(f.copies==2&&f.sends==1&&f.waits==0&&!e.in_flight);
    f.fail_send=false;f.fail_wait=true;
    CHECK(pmkb_surface_present(&s,&backend)==PMKB_INVALID);
    CHECK(f.copies==3&&f.sends==2&&f.waits==1);
    CHECK(e.in_flight&&e.pending_marker==1&&e.submitted==1);
    CHECK(s.has_dirty&&e.wait_failures==1);
    CHECK(pmkb_surface_present(&s,&backend)==PMKB_INVALID);
    CHECK(f.copies==3&&f.sends==2&&f.waits==2);
    CHECK(e.in_flight&&e.wait_failures==2);
    f.fail_wait=false;
    CHECK(pmkb_surface_present(&s,&backend)==PMKB_OK);
    CHECK(f.copies==3&&f.sends==2&&f.waits==3);
    CHECK(!e.in_flight&&e.completed==1&&!s.has_dirty);
    CHECK(pmkb_surface_present(&s,&backend)==PMKB_NO_CHANGE);
    /* Wrap markers to nonzero; caller may explicitly choose waveform. */
    e.sequence=UINT32_MAX;
    pmkb_surface_rect(&s,(PMKBRect){10,10,2,2},240);
    CHECK(pmkb_surface_present(&s,&backend)==PMKB_OK);
    CHECK(f.marker==1 && !e.in_flight);
    pmkb_surface_free(&s);
    groups++;return 0;
}
static int retry_with_intervening_edit(void){
    FakeEink f={.width=320,.height=480,.fail_wait=true};
    PMKBEink e={0};PMKBSurface s={0};PMKBRect ignored={0};
    CHECK(pmkb_eink_init(&e,320,480,fake_ops(&f))==PMKB_OK);
    CHECK(pmkb_surface_init(&s,320,480)==PMKB_OK);
    CHECK(pmkb_surface_take_dirty(&s,&ignored));
    PMKBBackend adapter={.context=&e,.present=pmkb_eink_present};
    pmkb_surface_rect(&s,(PMKBRect){8,8,4,4},0);
    CHECK(pmkb_surface_present(&s,&adapter)==PMKB_INVALID);
    CHECK(e.in_flight&&e.submitted==1&&f.sends==1);
    /* State changes before the uncertain completion is confirmed. */
    pmkb_surface_rect(&s,(PMKBRect){60,60,6,6},0);
    CHECK(s.has_dirty);
    f.fail_wait=false;
    CHECK(pmkb_surface_present(&s,&adapter)==PMKB_OK);
    CHECK(e.submitted==2&&e.completed==2&&f.sends==2);
    CHECK(f.last_rect.x==8&&f.last_rect.y==8);
    CHECK(f.last_rect.w==58&&f.last_rect.h==58);
    CHECK(f.image[8*320+8]==0&&f.image[60*320+60]==0);
    CHECK(!s.has_dirty);
    /* Same rectangle, changed pixel values: checksum still forces resend. */
    pmkb_surface_rect(&s,(PMKBRect){5,5,4,4},0);
    f.fail_wait=true;
    CHECK(pmkb_surface_present(&s,&adapter)==PMKB_INVALID);
    pmkb_surface_rect(&s,(PMKBRect){5,5,4,4},100);
    f.fail_wait=false;
    unsigned old=e.submitted;
    CHECK(pmkb_surface_present(&s,&adapter)==PMKB_OK);
    CHECK(e.submitted==old+1&&f.image[5*320+5]==100);
    CHECK(!e.in_flight&&!s.has_dirty);
    pmkb_surface_free(&s);
    groups++;return 0;
}
static int invalid_hal_calls(void){
    PMKBEink e={0};FakeEink f={.width=320,.height=480};
    PMKBEinkOps bad=fake_ops(&f);bad.wait=NULL;
    CHECK(pmkb_eink_init(&e,320,480,bad)==PMKB_INVALID);
    CHECK(pmkb_eink_init(&e,320,480,fake_ops(&f))==PMKB_OK);
    uint8_t dummy=255;
    CHECK(pmkb_eink_present(&e,&dummy,320,480,
                           (PMKBRect){-1,0,10,10})==PMKB_INVALID);
    CHECK(pmkb_eink_present(&e,&dummy,320,480,
                           (PMKBRect){0,0,321,10})==PMKB_INVALID);
    CHECK(pmkb_eink_present(&e,&dummy,320,480,
                           (PMKBRect){0,0,0,10})==PMKB_INVALID);
    CHECK(pmkb_eink_present(&e,&dummy,480,320,
                           (PMKBRect){0,0,1,1})==PMKB_INVALID);
    CHECK(pmkb_eink_present(NULL,&dummy,320,480,
                           (PMKBRect){0,0,1,1})==PMKB_INVALID);
    CHECK(pmkb_eink_present(&e,NULL,320,480,
                           (PMKBRect){0,0,1,1})==PMKB_INVALID);
    CHECK(f.copies==0&&f.sends==0&&f.waits==0);
    groups++;return 0;
}
static PMKBStatus simulated_tap(PMKBTouch *t,PMKBAppHost *host,
                                int x,int y){
    PMKBEvent event={0};
    if(tap_press(t,x,y,&event)!=PMKB_NO_CHANGE)return PMKB_INVALID;
    if(tap_release(t,x,y,&event)!=PMKB_OK)return PMKB_INVALID;
    return pmkb_app_host_event(host,event,"2026-10-19T20:00:00.000Z");
}
static int end_to_end_legacy_touch(void){
    PMKBAppHost host;pmkb_app_host_init(&host);
    CHECK(pmkb_app_host_launch(&host,PMKB_APP_NOTES,320,480)==PMKB_OK);
    PMKBTouchConfig c={
        .width=320,.height=480,.x_min=0,.x_max=319,
        .y_min=0,.y_max=479,.rotation=PMKB_ROT_0,.tap_slop=10
    };
    PMKBTouch t={0};
    CHECK(pmkb_touch_init(&t,c)==PMKB_OK);
    PMKBUI *notes=(PMKBUI*)host.instance;
    PMKBEvent rejected={0};
    /* Corrupted and two-finger taps on '+' must not create any note. */
    raw_coord(&t,14,14,&rejected);
    (void)pmkb_touch_feed(&t,PMKB_EV_KEY,PMKB_BTN_TOUCH,1,&rejected);
    (void)pmkb_touch_feed(&t,PMKB_EV_KEY,PMKB_BTN_TOOL_DOUBLETAP,1,&rejected);
    CHECK(sync_frame(&t,&rejected)==PMKB_NO_CHANGE);
    (void)pmkb_touch_feed(&t,PMKB_EV_KEY,PMKB_BTN_TOOL_DOUBLETAP,0,&rejected);
    CHECK(tap_release(&t,14,14,&rejected)==PMKB_NO_CHANGE);
    CHECK(notes->notebook.count==0&&t.taps==0);
    CHECK(pmkb_touch_feed(&t,PMKB_EV_SYN,PMKB_SYN_DROPPED,0,&rejected)==PMKB_NO_CHANGE);
    CHECK(tap_press(&t,14,14,&rejected)==PMKB_NO_CHANGE);
    CHECK(tap_release(&t,14,14,&rejected)==PMKB_NO_CHANGE);
    CHECK(notes->notebook.count==0&&t.taps==0);
    CHECK(simulated_tap(&t,&host,14,14)==PMKB_OK); /* + */
    CHECK(notes->view==PMKB_VIEW_EDITOR&&notes->notebook.count==1);
    CHECK(simulated_tap(&t,&host,110,14)==PMKB_OK); /* keyboard toggle */
    CHECK(notes->keyboard.visible);
    CHECK(simulated_tap(&t,&host,10,184)==PMKB_OK); /* "a" on AZERTY */
    CHECK(strcmp(notes->notebook.items[0]->title.data,"a")==0);
    CHECK(t.taps==3);
    CHECK(pmkb_app_host_close(&host,false)==PMKB_UNSAVED);
    CHECK(pmkb_app_host_close(&host,true)==PMKB_OK);
    groups++;return 0;
}
int main(void){
    if(decode_taps()||rotate_mirror()||extreme_abs_corner_matrix()||
       missing_and_invalid_events()||
       lost_frame_quarantine()||two_fingers_are_not_taps()||
       eink_partial_and_policy()||retry_and_marker()||
       retry_with_intervening_edit()||invalid_hal_calls()||
       end_to_end_legacy_touch())return 1;
    printf("PMKB HAL: %u assertions PASS, %u groups PASS, 0 FAIL\n",
           assertions,groups);
    return 0;
}
