/* Reproducible C11 host rendering, explicitly writes a user-selected PGM.
 * No device nodes, screen drivers, network or dependencies. */
#include "../pmkb_launcher_bridge.h"
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int dimension(const char *s){
    if(!s||!*s)return 0;
    errno=0;char *end=NULL;long value=strtol(s,&end,10);
    if(errno||!*s||*end||value<240||value>2500)return 0;
    return (int)value;
}
static int write_pgm(const char *file,const PMKBSurface *s){
    if(!s||!s->gray)return 1;
    FILE *output=fopen(file,"wb");
    if(!output)return 1;
    size_t pixels=(size_t)s->width*(size_t)s->height;
    int header=fprintf(output,"P5\n%d %d\n255\n",s->width,s->height);
    size_t written=header>0?fwrite(s->gray,1,pixels,output):0;
    int closed=fclose(output);
    return written!=pixels||closed!=0?1:0;
}
static int application(const char *name,int width,int height,const char *file){
    PMKBAppHost host;
    pmkb_app_host_init(&host);
    PMKBAppId kind=strcmp(name,"notes")==0?PMKB_APP_NOTES:
                   strcmp(name,"calculator")==0?PMKB_APP_CALCULATOR:
                   (!strcmp(name,"store")||!strcmp(name,"store-detail"))
                       ?PMKB_APP_STORE:PMKB_APP_NONE;
    if(pmkb_app_host_launch(&host,kind,width,height)!=PMKB_OK)return 1;
    PMKBStatus rc=PMKB_OK;
    if(kind==PMKB_APP_STORE){
        static const uint8_t snapshot[] =
            "{\"cleanup_pending_count\":1,\"items\":["
            "{\"id\":\"org.pmkb.calculator\",\"label\":\"Calculatrice\",\"launchable\":false,\"network_declared\":false,\"state\":\"installed_unverified\",\"version\":\"0.1.0\"},"
            "{\"id\":\"org.pmkb.notes\",\"label\":\"Mes notes\",\"launchable\":false,\"network_declared\":false,\"state\":\"installed_unverified\",\"version\":\"0.2.0\"},"
            "{\"id\":\"org.pmkb.weather\",\"label\":\"Meteo locale\",\"launchable\":false,\"network_declared\":true,\"state\":\"installed_unverified\",\"version\":\"0.1.0\"}],"
            "\"schema\":\"pmkb-store-view-v1\",\"scope\":\"synthetic_read_only\"}";
        if(pmkb_app_host_store_load(&host,snapshot,sizeof(snapshot)-1u)!=PMKB_OK)
            rc=PMKB_INVALID;
        if(rc==PMKB_OK&&!strcmp(name,"store-detail")&&
           pmkb_app_host_event(&host,(PMKBEvent){.kind=PMKB_EVENT_TAP,
                               .x=20,.y=70},NULL)!=PMKB_OK)
            rc=PMKB_INVALID;
    }else if(kind==PMKB_APP_CALCULATOR){
        PMKBCalcUI *calc=(PMKBCalcUI*)host.instance;
        if(pmkb_calc_ui_set_expression(calc,"sin(30)")!=PMKB_OK||
           pmkb_calc_ui_evaluate(calc)!=PMKB_OK||
           pmkb_calc_ui_set_expression(calc,"\xe2\x88\x9a(9)+\xcf\x80")!=PMKB_OK||
           pmkb_calc_ui_evaluate(calc)!=PMKB_OK||
           pmkb_calc_ui_set_expression(calc,"sin(30)+\xe2\x88\x9a(4)+\xcf\x80")!=PMKB_OK||
           pmkb_calc_ui_evaluate(calc)!=PMKB_OK)rc=PMKB_INVALID;
    }else if(kind==PMKB_APP_NOTES){
        PMKBUI *notes=(PMKBUI*)host.instance;
        const char *utc="2026-10-19T19:00:00.000Z";
        if(pmkb_ui_new_note(notes,utc)!=PMKB_OK)rc=PMKB_INVALID;
        if(rc==PMKB_OK){
            PMKBNote *note=notes->notebook.items[0];
            if(pmkb_text_set(&note->title,"Journal d'\xc3\xa9t\xc3\xa9")!=PMKB_OK ||
               pmkb_ui_event(notes,(PMKBEvent){.kind=PMKB_EVENT_TAP,
                             .x=width-15,.y=70},utc)!=PMKB_OK ||
               pmkb_ui_event(notes,(PMKBEvent){.kind=PMKB_EVENT_TEXT,
                             .text="Caf\xc3\xa9, \xc3\xa9t\xc3\xa9 et \xcf\x80.\n"
                                   "\xe2\x88\x9a(9) = 3"},utc)!=PMKB_OK ||
               pmkb_ui_event(notes,(PMKBEvent){.kind=PMKB_EVENT_TOGGLE_KEYBOARD},
                             utc)!=PMKB_OK)rc=PMKB_INVALID;
        }
    }
    int status=rc==PMKB_OK?write_pgm(file,pmkb_app_host_screen(&host)):1;
    /* This is a synthetic fixture, so explicitly allow discarding RAM only. */
    if(pmkb_app_host_close(&host,true)!=PMKB_OK)return 1;
    return status;
}
static int fonts(int width,int height,const char *file){
    PMKBSurface s={0};
    if(pmkb_surface_init(&s,width,height)!=PMKB_OK)return 1;
    pmkb_surface_text(&s,12,24,"CAFE: Caf\xc3\xa9, \xc3\x89T\xc3\x89, fa\xc3\xa7on",0,width-24);
    pmkb_surface_text(&s,12,72,"SCIENCE: \xcf\x80 \xe2\x88\x9a \xc3\x97 \xc3\xb7 \xc2\xb0",0,width-24);
    pmkb_surface_text(&s,12,120,"CURSEUR: \xe2\x86\x90 \xe2\x86\x92",0,width-24);
    pmkb_surface_text(&s,12,168,"DECOMPOSE: e\xcc\x81 t\xcc\x80",0,width-24);
    int status=write_pgm(file,&s);
    pmkb_surface_free(&s);
    return status;
}
int main(int argc,char **argv){
    if(argc!=5){
        fputs("Usage: pmkb-host-preview notes|calculator|store|store-detail|glyphs WIDTH HEIGHT OUTPUT.pgm\n",
              stderr);
        return 2;
    }
    int width=dimension(argv[2]),height=dimension(argv[3]);
    if(!width||height<320||width>2000||height>2500)return 2;
    if(strcmp(argv[1],"glyphs")==0)return fonts(width,height,argv[4]);
    if(strcmp(argv[1],"notes")&&strcmp(argv[1],"calculator")&&
       strcmp(argv[1],"store")&&strcmp(argv[1],"store-detail"))return 2;
    return application(argv[1],width,height,argv[4]);
}
