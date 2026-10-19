#include "pmkb_hal.h"
#include <limits.h>
#include <string.h>

PMKBStatus pmkb_touch_init(PMKBTouch *t,PMKBTouchConfig c){
    if(!t||c.width<240||c.width>2000||c.height<320||c.height>2500||
       c.x_min>=c.x_max||c.y_min>=c.y_max||
       c.tap_slop<0||c.tap_slop>100||
       (c.rotation!=PMKB_ROT_0&&c.rotation!=PMKB_ROT_90&&
        c.rotation!=PMKB_ROT_180&&c.rotation!=PMKB_ROT_270))
        return PMKB_INVALID;
    memset(t,0,sizeof(*t));
    t->config=c;
    return PMKB_OK;
}
static bool coordinates(const PMKBTouch *t,int *x,int *y){
    PMKBTouchConfig c=t->config;
    if(!t->have_x||!t->have_y||
       t->raw_x<c.x_min||t->raw_x>c.x_max||
       t->raw_y<c.y_min||t->raw_y>c.y_max)return false;
    /* Rational scaling in int64 avoids overflow / floating-point rounding.
     * Transform normalized axes before orientation; the dragon-specific
     * mirror and rotate profile MUST be qualified against real corners. */
    int64_t ux=((int64_t)(t->raw_x-c.x_min)*1000000)/(c.x_max-c.x_min);
    int64_t uy=((int64_t)(t->raw_y-c.y_min)*1000000)/(c.y_max-c.y_min);
    if(c.mirror_x)ux=1000000-ux;
    if(c.mirror_y)uy=1000000-uy;
    int64_t fx=ux,fy=uy;
    switch(c.rotation){
    case PMKB_ROT_90: fx=1000000-uy;fy=ux;break;
    case PMKB_ROT_180:fx=1000000-ux;fy=1000000-uy;break;
    case PMKB_ROT_270:fx=uy;fy=1000000-ux;break;
    case PMKB_ROT_0:break;
    }
    *x=(int)((fx*(c.width-1)+500000)/1000000);
    *y=(int)((fy*(c.height-1)+500000)/1000000);
    return true;
}
static bool wandered(const PMKBTouch *t,int x,int y){
    int dx=x-t->down_x,dy=y-t->down_y;
    if(dx<0)dx=-dx;
    if(dy<0)dy=-dy;
    return dx>t->config.tap_slop||dy>t->config.tap_slop;
}
PMKBStatus pmkb_touch_feed(PMKBTouch *t,int type,int code,int value,
                           PMKBEvent *event){
    if(!t||!event)return PMKB_INVALID;
    if(type==PMKB_EV_ABS){
        if(code==PMKB_ABS_X){
            t->raw_x=value;t->have_x=true;
        }else if(code==PMKB_ABS_Y){
            t->raw_y=value;t->have_y=true;
        }
        return PMKB_NO_CHANGE;
    }
    if(type==PMKB_EV_KEY){
        if(code==PMKB_BTN_TOUCH&&(value==0||value==1)){
            t->pending_button=true;t->button_value=value;
        }
        return PMKB_NO_CHANGE;
    }
    if(type!=PMKB_EV_SYN)return PMKB_NO_CHANGE;
    if(code==PMKB_SYN_DROPPED){
        /* Missing events invalidate gesture, not a request to invent one. */
        t->down=false;t->candidate=false;t->pending_button=false;
        t->have_x=false;t->have_y=false;t->drops++;
        return PMKB_NO_CHANGE;
    }
    if(code!=PMKB_SYN_REPORT)return PMKB_NO_CHANGE;
    int x=0,y=0;
    bool valid=coordinates(t,&x,&y);
    if(t->pending_button&&t->button_value==1&&!t->down){
        t->down=true;t->candidate=valid;
        if(valid){t->down_x=x;t->down_y=y;}
    }else if(t->down){
        if(!valid || wandered(t,x,y))t->candidate=false;
        if(t->pending_button&&t->button_value==0){
            bool emit=t->candidate&&valid;
            t->down=false;t->candidate=false;
            t->have_x=false;t->have_y=false;
            t->pending_button=false;
            if(emit){
                *event=(PMKBEvent){.kind=PMKB_EVENT_TAP,.x=x,.y=y,.text=NULL};
                t->taps++;
                return PMKB_OK;
            }
            return PMKB_NO_CHANGE;
        }
    }
    t->pending_button=false;
    return PMKB_NO_CHANGE;
}
PMKBStatus pmkb_eink_init(PMKBEink *e,int width,int height,
                           PMKBEinkOps ops){
    if(!e||width<240||height<320||width>2000||height>2500||
       !ops.copy||!ops.send||!ops.wait)return PMKB_INVALID;
    memset(e,0,sizeof(*e));
    e->width=width;e->height=height;e->ops=ops;
    e->mode=PMKB_EINK_UPDATE_PARTIAL;
    return PMKB_OK;
}
PMKBStatus pmkb_eink_set_update(PMKBEink *e,PMKBEinkUpdate mode){
    if(!e||(mode!=PMKB_EINK_UPDATE_PARTIAL&&
            mode!=PMKB_EINK_UPDATE_FULL))return PMKB_INVALID;
    e->mode=mode;
    return PMKB_OK;
}
static bool rectangle_valid(const PMKBEink *e,PMKBRect r){
    return r.x>=0&&r.y>=0&&r.w>0&&r.h>0&&
           r.x<=e->width-r.w&&r.y<=e->height-r.h;
}
static bool same(PMKBRect a,PMKBRect b){
    return a.x==b.x&&a.y==b.y&&a.w==b.w&&a.h==b.h;
}
static uint64_t digest(const uint8_t *gray,int width,PMKBRect r){
    uint64_t hash=UINT64_C(14695981039346656037);
    for(int y=r.y;y<r.y+r.h;y++)
        for(int x=r.x;x<r.x+r.w;x++){
            hash^=gray[(size_t)y*(size_t)width+(size_t)x];
            hash*=UINT64_C(1099511628211);
        }
    return hash;
}
PMKBStatus pmkb_eink_present(void *context,const uint8_t *gray,
                             int width,int height,PMKBRect dirty){
    PMKBEink *e=(PMKBEink*)context;
    if(!e||!gray||!e->ops.copy||!e->ops.send||!e->ops.wait||
       width!=e->width||height!=e->height||!rectangle_valid(e,dirty))
        return PMKB_INVALID;
    if(e->in_flight){
        PMKBStatus done=e->ops.wait(e->ops.context,e->pending_marker);
        if(done!=PMKB_OK){e->wait_failures++;return done;}
        e->completed++;e->in_flight=false;
        /* If an edit happened during uncertainty, the new dirty rectangle
         * (or the content of the same rectangle) must not be acknowledged. */
        if(same(dirty,e->pending_rect)&&
           digest(gray,width,dirty)==e->pending_digest)return PMKB_OK;
    }
    PMKBStatus rc=e->ops.copy(e->ops.context,gray,width,height,dirty);
    if(rc!=PMKB_OK)return rc;
    uint32_t marker=e->sequence+1u;
    if(marker==0)marker=1;
    rc=e->ops.send(e->ops.context,dirty,marker,e->mode);
    if(rc!=PMKB_OK)return rc;
    e->sequence=marker;e->in_flight=true;
    e->pending_marker=marker;e->pending_rect=dirty;
    e->pending_digest=digest(gray,width,dirty);
    e->submitted++;
    rc=e->ops.wait(e->ops.context,marker);
    if(rc!=PMKB_OK){e->wait_failures++;return rc;}
    e->completed++;e->in_flight=false;
    return PMKB_OK;
}
