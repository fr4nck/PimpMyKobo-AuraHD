/* Native L06-D2 fixture runner: only the runner reads stdin, not the library. */
#include "pmkb_store_view.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define PREFIX "{\"cleanup_pending_count\":"
#define MID ",\"items\":["
#define SUFFIX "],\"schema\":\"pmkb-store-view-v1\",\"scope\":\"synthetic_read_only\"}"
#define ROW(ID,LABEL,NET,VERSION) "{\"id\":\"" ID "\",\"label\":\"" LABEL "\",\"launchable\":false,\"network_declared\":" NET ",\"state\":\"installed_unverified\",\"version\":\"" VERSION "\"}"
static const char empty[]=PREFIX "0" MID SUFFIX;
static const char valid[]=PREFIX "2" MID ROW("org.pmkb.demo","M\\u00e9t\\u00e9o \\ud83d\\ude42", "true","0.1.0") SUFFIX;
static unsigned assertions=0,failures=0;
#define CHECK(X) do { assertions++;if (!(X)) {failures++;fprintf(stderr,"C11 VIEW FAIL line %d: %s\n",__LINE__,#X);}}while(0)

static bool reject(const char *json) {
    PMKBStoreView out;memset(&out,0x77,sizeof(out));
    PMKBStoreViewStatus status=pmkb_store_view_parse((const uint8_t*)json,strlen(json),&out);
    return status!=PMKB_STORE_VIEW_OK && out.count==0 && out.cleanup_pending_count==0;
}
static void selftest(void){
    PMKBStoreView out;
    CHECK(pmkb_store_view_parse((const uint8_t*)empty,strlen(empty),&out)==PMKB_STORE_VIEW_OK);
    CHECK(out.count==0 && out.cleanup_pending_count==0);
    CHECK(pmkb_store_view_parse((const uint8_t*)valid,strlen(valid),&out)==PMKB_STORE_VIEW_OK);
    CHECK(out.count==1 && out.cleanup_pending_count==2);
    CHECK(strcmp(out.items[0].id,"org.pmkb.demo")==0);
    CHECK(strcmp(out.items[0].label,"M\xc3\xa9t\xc3\xa9o \xf0\x9f\x99\x82")==0);
    CHECK(strcmp(out.items[0].version,"0.1.0")==0);
    CHECK(out.items[0].network_declared && !out.items[0].launchable);
    CHECK(reject(PREFIX "0" MID ROW("no-dot","Demo","false","0.1.0") SUFFIX));
    CHECK(reject(PREFIX "0" MID ROW("org.pmkb.demo","","false","0.1.0") SUFFIX));
    CHECK(reject(PREFIX "0" MID ROW("org.pmkb.demo","Label","false","01.1.0") SUFFIX));
    CHECK(reject(PREFIX "0" MID ROW("org.pmkb.demo","Label","false","1.2") SUFFIX));
    CHECK(reject(PREFIX "0" MID ROW("org.pmkb.demo","\\ud83d","false","1.2.3") SUFFIX));
    CHECK(reject(PREFIX "0" MID ROW("org.pmkb.demo","\\ude42","false","1.2.3") SUFFIX));
    CHECK(reject(PREFIX "0" MID ROW("org.pmkb.demo","\\u0000","false","1.2.3") SUFFIX));
    CHECK(reject(PREFIX "0" MID ROW("org.pmkb.demo","\\x","false","1.2.3") SUFFIX));
    CHECK(reject(PREFIX "0" MID ROW("org.pmkb.demo","Demo","false","1.2.3") "," ROW("org.pmkb.demo","Duplicate","false","1.2.3") SUFFIX));
    CHECK(reject(PREFIX "0" MID ROW("org.pmkb.z","Z","false","1.2.3") "," ROW("org.pmkb.a","A","false","1.2.3") SUFFIX));
    CHECK(reject(PREFIX "0" MID "{\"id\":\"org.pmkb.demo\",\"label\":\"Demo\",\"launchable\":true,\"network_declared\":false,\"state\":\"installed_unverified\",\"version\":\"1.2.3\"}" SUFFIX));
    CHECK(reject(PREFIX "513" MID SUFFIX));
    CHECK(reject(PREFIX "01" MID SUFFIX));
    CHECK(reject(PREFIX "0" MID SUFFIX "extra"));
    CHECK(reject("{ \"cleanup_pending_count\":0,\"items\":[],\"schema\":\"pmkb-store-view-v1\",\"scope\":\"synthetic_read_only\"}"));
    CHECK(reject("{\"items\":[],\"cleanup_pending_count\":0,\"schema\":\"pmkb-store-view-v1\",\"scope\":\"synthetic_read_only\"}"));
    CHECK(reject("{\"cleanup_pending_count\":0,\"items\":[],\"schema\":\"other\",\"scope\":\"synthetic_read_only\"}"));
    CHECK(reject(PREFIX "0" MID ROW("org.pmkb.demo","Raw \xc3\xa9","false","1.2.3") SUFFIX));
    CHECK(reject(PREFIX "0" MID ROW("org.pmkb.demo","bad\\ntext","unknown","1.2.3") SUFFIX));
    CHECK(reject(PREFIX "0" MID ROW("org.pmkb.demo","bad\\q","false","1.2.3") SUFFIX));
    CHECK(reject(PREFIX "0" MID ROW("org.pmkb.demo","a\\\"b","false","1.2.3") "," SUFFIX));
    /* Integer bounds, string bounds, exact length and embedded NUL. */
    char large[PMKB_STORE_VIEW_MAX_JSON+2];memset(large,'x',sizeof(large));
    CHECK(pmkb_store_view_parse((const uint8_t*)large,sizeof(large),&out)==PMKB_STORE_VIEW_LIMIT);
    CHECK(out.count==0 && out.cleanup_pending_count==0);
    CHECK(pmkb_store_view_parse((const uint8_t*)empty,strlen(empty)-1,&out)==PMKB_STORE_VIEW_INVALID);
    CHECK(pmkb_store_view_parse(NULL,0,&out)==PMKB_STORE_VIEW_INVALID);
    CHECK(pmkb_store_view_parse((const uint8_t*)empty,strlen(empty),NULL)==PMKB_STORE_VIEW_INVALID);
    char nuls[sizeof(empty)];memcpy(nuls,empty,sizeof(empty));nuls[10]='\0';
    CHECK(pmkb_store_view_parse((const uint8_t*)nuls,strlen(empty),&out)==PMKB_STORE_VIEW_INVALID);
    CHECK(sizeof(out)<=32768u);
    /* End-to-end output, including quotes and escaped newline. */
    const char with_escaped[]=PREFIX "512" MID ROW("org.pmkb.demo","A\\\"B\\nC\\\\D","false","1.2.3") SUFFIX;
    CHECK(pmkb_store_view_parse((const uint8_t*)with_escaped,strlen(with_escaped),&out)==PMKB_STORE_VIEW_OK);
    CHECK(strcmp(out.items[0].label,"A\"B\nC\\D")==0);
    CHECK(out.cleanup_pending_count==512 && !out.items[0].network_declared);
}
int main(int argc,char **argv){
    if(argc>1 && strcmp(argv[1],"--stdin")==0){
        static uint8_t input[PMKB_STORE_VIEW_MAX_JSON+1u];
        size_t n=fread(input,1,sizeof(input),stdin);
        PMKBStoreView view;
        PMKBStoreViewStatus st=pmkb_store_view_parse(input,n,&view);
        if(st!=PMKB_STORE_VIEW_OK)return 3;
        printf("OK %u %u %s\n",view.count,view.cleanup_pending_count,
               view.count?view.items[0].id:"-");
        return 0;
    }
    selftest();
    if(failures)return 1;
    printf("PMKB C11 STORE VIEW: %u assertions PASS, 0 FAIL\n",assertions);
    return 0;
}
