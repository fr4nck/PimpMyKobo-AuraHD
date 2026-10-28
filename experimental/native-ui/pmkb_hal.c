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
    /* Extend both operands before subtraction: ABS spans can exceed INT_MAX. */
    int64_t x_span=(int64_t)c.x_max-(int64_t)c.x_min;
    int64_t y_span=(int64_t)c.y_max-(int64_t)c.y_min;
    int64_t ux=(((int64_t)t->raw_x-(int64_t)c.x_min)*1000000)/x_span;
    int64_t uy=(((int64_t)t->raw_y-(int64_t)c.y_min)*1000000)/y_span;
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
static void cancel_touch(PMKBTouch *t){
    t->down=false;t->candidate=false;t->pending_button=false;
    t->have_x=false;t->have_y=false;
}
PMKBStatus pmkb_touch_feed(PMKBTouch *t,int type,int code,int value,
                           PMKBEvent *event){
    if(!t||!event)return PMKB_INVALID;
    if(type==PMKB_EV_SYN&&code==PMKB_SYN_DROPPED){
        cancel_touch(t);
        t->discard_frame=true;t->await_release=true;
        t->multiple_contacts=false;t->drops++;
        return PMKB_NO_CHANGE;
    }
    if(t->discard_frame){
        /* evdev overflow: discard up to AND including SYN_REPORT.
         * State recovery belongs to the future EVIOCG* adapter. */
        if(type==PMKB_EV_SYN&&code==PMKB_SYN_REPORT)t->discard_frame=false;
        return PMKB_NO_CHANGE;
    }
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
        }else if(code==PMKB_BTN_TOOL_DOUBLETAP&&(value==0||value==1)){
            t->multiple_contacts=value!=0;
            if(value==1){t->await_release=true;t->candidate=false;}
        }
        return PMKB_NO_CHANGE;
    }
    if(type!=PMKB_EV_SYN)return PMKB_NO_CHANGE;
    if(code!=PMKB_SYN_REPORT)return PMKB_NO_CHANGE;
    if(t->await_release){
        /* Never turn a two-to-one transition or unknown state into TAP. */
        if(t->pending_button&&t->button_value==0&&!t->multiple_contacts)
            t->await_release=false;
        cancel_touch(t);
        return PMKB_NO_CHANGE;
    }
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


/* Magnetic cover policy: pure C11, no timers, threads, sysfs or device I/O. */
static const char pmkb_cover_off[]="pmkb-cover-v1\nmagnetic_cover=off\n";
static const char pmkb_cover_on[] ="pmkb-cover-v1\nmagnetic_cover=on\n";

void pmkb_power_policy_init(PMKBPowerPolicy *policy){
    if(policy)memset(policy,0,sizeof(*policy));
}
PMKBStatus pmkb_power_policy_set_cover(PMKBPowerPolicy *policy,bool enabled){
    if(!policy)return PMKB_INVALID;
    if(policy->cover_enabled==enabled)return PMKB_NO_CHANGE;
    policy->cover_enabled=enabled;
    /* Do not replay the last observed cover position on opt-in. */
    return PMKB_OK;
}
PMKBStatus pmkb_power_policy_export(const PMKBPowerPolicy *policy,
                                    char *data,size_t capacity,size_t *length){
    if(!policy||!data||!length)return PMKB_INVALID;
    const char *source=policy->cover_enabled?pmkb_cover_on:pmkb_cover_off;
    size_t bytes=policy->cover_enabled?sizeof(pmkb_cover_on)-1u:
                                       sizeof(pmkb_cover_off)-1u;
    if(capacity<bytes)return PMKB_LIMIT;
    memcpy(data,source,bytes);
    *length=bytes;
    return PMKB_OK;
}
PMKBStatus pmkb_power_policy_import(PMKBPowerPolicy *policy,
                                    const char *data,size_t length){
    if(!policy||!data)return PMKB_INVALID;
    bool enabled;
    if(length==sizeof(pmkb_cover_off)-1u&&
       memcmp(data,pmkb_cover_off,length)==0)enabled=false;
    else if(length==sizeof(pmkb_cover_on)-1u&&
            memcmp(data,pmkb_cover_on,length)==0)enabled=true;
    else return PMKB_INVALID;
    policy->cover_enabled=enabled;
    /* Retain event history: reconfiguring cannot invent an input edge. */
    return PMKB_OK;
}
PMKBStatus pmkb_power_policy_filter(PMKBPowerPolicy *policy,PMKBPowerEvent event){
    if(!policy)return PMKB_INVALID;
    if(event==PMKB_POWER_COVER_CLOSED||event==PMKB_POWER_COVER_OPENED){
        bool closed=event==PMKB_POWER_COVER_CLOSED;
        if(policy->cover_seen&&policy->cover_closed==closed)
            return PMKB_NO_CHANGE;
        policy->cover_seen=true;
        policy->cover_closed=closed;
        return policy->cover_enabled?PMKB_OK:PMKB_NO_CHANGE;
    }
    if(event==PMKB_POWER_BUTTON_PRESSED||
       event==PMKB_POWER_BUTTON_RELEASED||event==PMKB_POWER_OTHER)
        return PMKB_OK;
    return PMKB_INVALID;
}


/* Host-only translation from already classified NTX evdev key events. */
PMKBStatus pmkb_power_evdev_init(PMKBPowerEvdev *decoder,
        PMKBPowerPolicy *policy,PMKBPowerInputSource source,int cover_code){
    if(!decoder)return PMKB_INVALID;
    memset(decoder,0,sizeof(*decoder));
    if(!policy||source!=PMKB_POWER_SOURCE_NTX_VERIFIED||
       (cover_code!=PMKB_KEY_F1&&cover_code!=PMKB_KEY_H))
        return PMKB_INVALID;
    decoder->policy=policy;
    decoder->cover_code=cover_code;
    decoder->qualified=true;
    policy->cover_seen=false; /* Never inherit a stale level across sources. */
    return PMKB_OK;
}
PMKBStatus pmkb_power_evdev_feed(PMKBPowerEvdev *decoder,
        int type,int code,int value,PMKBPowerEvent *event){
    if(!decoder||!event||!decoder->qualified||!decoder->policy)
        return PMKB_INVALID;
    if(type==PMKB_EV_SYN&&code==PMKB_SYN_DROPPED){
        decoder->discard_frame=true;
        decoder->await_cover_release=true;
        return PMKB_NO_CHANGE;
    }
    if(decoder->discard_frame){
        /* Discard through the terminating SYN_REPORT. */
        if(type==PMKB_EV_SYN&&code==PMKB_SYN_REPORT)
            decoder->discard_frame=false;
        return PMKB_NO_CHANGE;
    }
    if(type!=PMKB_EV_KEY||(value!=0&&value!=1))
        return PMKB_NO_CHANGE; /* Ignore repeats (value 2). */
    PMKBPowerEvent semantic;
    if(code==PMKB_KEY_POWER){
        semantic=value?PMKB_POWER_BUTTON_PRESSED:PMKB_POWER_BUTTON_RELEASED;
    }else if(code==decoder->cover_code){
        if(decoder->await_cover_release){
            if(value==0){
                decoder->await_cover_release=false;
                decoder->policy->cover_seen=true;
                decoder->policy->cover_closed=false;
            }
            /* Resynchronize without emitting a phantom wake event. */
            return PMKB_NO_CHANGE;
        }
        semantic=value?PMKB_POWER_COVER_CLOSED:PMKB_POWER_COVER_OPENED;
    }else{
        return PMKB_NO_CHANGE;
    }
    PMKBStatus rc=pmkb_power_policy_filter(decoder->policy,semantic);
    if(rc==PMKB_OK)*event=semantic;
    return rc;
}


/* Read-only metadata classifier: no evdev device or sysfs is accessed here.
 * Output means "possible NTX keyboard", never "verified Hall event source". */
PMKBPowerProbeResult pmkb_power_probe_inputs(
        const PMKBPowerInputInfo *devices,size_t count,size_t *candidate_index){
    if(!candidate_index||count>PMKB_POWER_SCAN_MAX||
       (count!=0&&!devices))return PMKB_POWER_PROBE_INVALID;
    size_t found=0;
    bool have_candidate=false;
    for(size_t i=0;i<count;i++){
        const PMKBPowerInputInfo *d=&devices[i];
        /* Key capabilities alone would accept external USB keyboards. */
        if(!d->name||strcmp(d->name,"mxckpd")!=0||
           d->bustype!=PMKB_BUS_HOST||!d->has_ev_key||
           (!d->has_key_f1&&!d->has_key_h))continue;
        if(have_candidate)return PMKB_POWER_PROBE_AMBIGUOUS;
        found=i;
        have_candidate=true;
    }
    if(!have_candidate)return PMKB_POWER_PROBE_NONE;
    *candidate_index=found;
    return PMKB_POWER_PROBE_CANDIDATE;
}


/* HWCONFIG-correlated but still UNVERIFIED input metadata, host-only. */
PMKBPowerProbeResult pmkb_power_probe_aura_hd(
        const PMKBPowerInputInfo *devices,size_t count,
        PMKBPowerBoardSignature hw,size_t *candidate_index){
    if(!candidate_index||count>PMKB_POWER_SCAN_MAX||
       (count!=0&&!devices))return PMKB_POWER_PROBE_INVALID;
    /* This exact profile comes from the E606C0 backup, not a live probe. */
    if(hw.pcb!=PMKB_AURA_HD_PCB||
       hw.pcb_flags!=PMKB_AURA_HD_NO_KEYMATRIX||
       hw.hall_sensor!=1u)return PMKB_POWER_PROBE_NONE;
    size_t found=0;
    bool have_candidate=false;
    for(size_t i=0;i<count;i++){
        const PMKBPowerInputInfo *d=&devices[i];
        if(!d->name||strcmp(d->name,"mxckpd")!=0||
           d->bustype!=PMKB_BUS_HOST||!d->has_ev_key||
           !d->has_key_f1||!d->has_key_h||!d->has_key_power)
            continue;
        if(have_candidate)return PMKB_POWER_PROBE_AMBIGUOUS;
        found=i;
        have_candidate=true;
    }
    if(!have_candidate)return PMKB_POWER_PROBE_NONE;
    *candidate_index=found;
    return PMKB_POWER_PROBE_CANDIDATE;
}

