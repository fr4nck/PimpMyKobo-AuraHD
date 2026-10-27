#include "pmkb_launcher_bridge.h"
#include <stdlib.h>
#include <string.h>

static void pmkb_app_host_advance_generation(PMKBAppHost *host){
    if(host->generation<UINT64_MAX)host->generation++;
}

static const PMKBAppInfo catalog[]={
    {PMKB_APP_NOTES,"notes","Mes notes",true},
    {PMKB_APP_CALCULATOR,"calculator","Calculatrice",true},
    {PMKB_APP_STORE,"store","Store",true},
    {PMKB_APP_WHITEBOARD,"whiteboard","Tableau blanc",true}
};
const PMKBAppInfo *pmkb_app_info(PMKBAppId kind){
    for(size_t i=0;i<sizeof(catalog)/sizeof(catalog[0]);i++)
        if(catalog[i].kind==kind)return &catalog[i];
    return NULL;
}
void pmkb_app_host_init(PMKBAppHost *host){
    if(host)memset(host,0,sizeof(*host));
}
PMKBStatus pmkb_app_host_launch(PMKBAppHost *host,PMKBAppId kind,
                                int width,int height){
    if(!host)return PMKB_INVALID;
    /* The caller must explicitly close/discard the prior app.
     * Never free a Notes session because the user tapped another tile. */
    if(host->active!=PMKB_APP_NONE || host->instance)return PMKB_INVALID;
    const PMKBAppInfo *info=pmkb_app_info(kind);
    if(!info || !info->runnable)return PMKB_NOT_FOUND;
    if(kind==PMKB_APP_NOTES){
        PMKBUI *notes=(PMKBUI*)calloc(1,sizeof(*notes));
        if(!notes)return PMKB_MEMORY;
        PMKBStatus rc=pmkb_ui_init(notes,width,height);
        if(rc!=PMKB_OK){free(notes);return rc;}
        host->instance=notes;
    }else if(kind==PMKB_APP_CALCULATOR){
        PMKBCalcUI *calc=(PMKBCalcUI*)calloc(1,sizeof(*calc));
        if(!calc)return PMKB_MEMORY;
        PMKBStatus rc=pmkb_calc_ui_init(calc,width,height);
        if(rc!=PMKB_OK){free(calc);return rc;}
        host->instance=calc;
    }else if(kind==PMKB_APP_STORE){
        PMKBStoreApp *store=(PMKBStoreApp*)calloc(1,sizeof(*store));
        if(!store)return PMKB_MEMORY;
        PMKBStatus rc=pmkb_store_app_init(store,width,height);
        if(rc!=PMKB_OK){free(store);return rc;}
        host->instance=store;
    }else if(kind==PMKB_APP_WHITEBOARD){
        PMKBWhiteboardSession *wb=(PMKBWhiteboardSession*)calloc(1,sizeof(*wb));
        if(!wb)return PMKB_MEMORY;
        PMKBStatus rc=pmkb_wb_session_open(wb,width,height);
        if(rc!=PMKB_OK){free(wb);return rc;}
        host->instance=wb;
    }else return PMKB_NOT_FOUND;
    host->active=kind;
    pmkb_app_host_advance_generation(host);
    return PMKB_OK;
}
PMKBStatus pmkb_app_host_notes_export_snapshot(const PMKBAppHost *host,
        uint64_t expected_generation,char **json,size_t *length){
    if(!host||!json||!length)return PMKB_INVALID;
    if(host->active!=PMKB_APP_NOTES||!host->instance)return PMKB_NOT_FOUND;
    if(expected_generation==0||expected_generation==UINT64_MAX||
       host->generation!=expected_generation)return PMKB_INVALID;
    const PMKBUI *notes=(const PMKBUI*)host->instance;
    return pmkb_notebook_export_json(&notes->notebook,json,length);
}
PMKBStatus pmkb_app_host_store_load(PMKBAppHost *host,
                                    const uint8_t *json,size_t length){
    if(!host||host->active!=PMKB_APP_STORE||!host->instance)
        return PMKB_NOT_FOUND;
    return pmkb_store_app_load_snapshot((PMKBStoreApp*)host->instance,
                                        json,length);
}
PMKBWBStatus pmkb_app_host_whiteboard_touch(PMKBAppHost *host,
        PMKBWBTouchKind kind,int x,int y){
    if(!host||host->active!=PMKB_APP_WHITEBOARD||!host->instance)
        return PMKB_WB_INVALID;
    return pmkb_wb_session_touch((PMKBWhiteboardSession*)host->instance,kind,x,y);
}
PMKBWBStatus pmkb_app_host_whiteboard_undo(PMKBAppHost *host){
    if(!host||host->active!=PMKB_APP_WHITEBOARD||!host->instance)
        return PMKB_WB_INVALID;
    return pmkb_wb_app_undo(&((PMKBWhiteboardSession*)host->instance)->app);
}
PMKBStatus pmkb_app_host_close(PMKBAppHost *host,bool discard){
    if(!host)return PMKB_INVALID;
    if(!host->instance||host->active==PMKB_APP_NONE)return PMKB_NO_CHANGE;
    if(host->active==PMKB_APP_NOTES){
        PMKBUI *notes=(PMKBUI*)host->instance;
        if(notes->notebook.count!=0 && !discard)return PMKB_UNSAVED;
        pmkb_ui_free(notes);
    }else if(host->active==PMKB_APP_CALCULATOR){
        pmkb_calc_ui_free((PMKBCalcUI*)host->instance);
    }else if(host->active==PMKB_APP_STORE){
        pmkb_store_app_free((PMKBStoreApp*)host->instance);
    }else if(host->active==PMKB_APP_WHITEBOARD){
        PMKBStatus rc=pmkb_wb_session_close(
            (PMKBWhiteboardSession*)host->instance,discard);
        if(rc!=PMKB_OK)return rc;
    }else return PMKB_INVALID;
    free(host->instance);
    host->instance=NULL;
    host->active=PMKB_APP_NONE;
    pmkb_app_host_advance_generation(host);
    return PMKB_OK;
}
PMKBSurface *pmkb_app_host_screen(PMKBAppHost *host){
    if(!host||!host->instance)return NULL;
    if(host->active==PMKB_APP_NOTES)
        return &((PMKBUI*)host->instance)->screen;
    if(host->active==PMKB_APP_CALCULATOR)
        return &((PMKBCalcUI*)host->instance)->screen;
    if(host->active==PMKB_APP_STORE)
        return &((PMKBStoreApp*)host->instance)->screen;
    if(host->active==PMKB_APP_WHITEBOARD)
        return pmkb_wb_session_screen((PMKBWhiteboardSession*)host->instance);
    return NULL;
}
PMKBStatus pmkb_app_host_event(PMKBAppHost *host,
                                PMKBEvent event,const char *utc){
    if(!host||!host->instance)return PMKB_NOT_FOUND;
    if(host->active==PMKB_APP_NOTES)
        return pmkb_ui_event((PMKBUI*)host->instance,event,utc);
    if(host->active==PMKB_APP_CALCULATOR)
        return pmkb_calc_ui_event((PMKBCalcUI*)host->instance,event);
    if(host->active==PMKB_APP_STORE)
        return pmkb_store_app_event((PMKBStoreApp*)host->instance,event);
    return PMKB_NOT_FOUND;
}
PMKBStatus pmkb_app_host_present(PMKBAppHost *host,
                                  const PMKBBackend *backend){
    PMKBSurface *screen=pmkb_app_host_screen(host);
    if(!screen)return PMKB_NOT_FOUND;
    return pmkb_surface_present(screen,backend);
}
