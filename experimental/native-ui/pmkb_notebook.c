#include "pmkb_ui.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static bool iso8601(const char *s) {
    if(!s) return false;
    size_t n=strlen(s);
    if(n!=20 && n!=24) return false;
    const int cuts[]={4,7,10,13,16};
    for(int i=0;i<5;i++)
        if(s[cuts[i]]!=(i<2?'-':i==2?'T':':'))return false;
    for(size_t i=0;i<n;i++){
        if(i==4||i==7||i==10||i==13||i==16)continue;
        if((n==20&&i==19)||(n==24&&i==23)){
            if(s[i]!='Z')return false;continue;
        }
        if(n==24&&i==19){if(s[i]!='.')return false;continue;}
        if(s[i]<'0'||s[i]>'9')return false;
    }
    int year=0,month=0,day=0,hour=0,minute=0,second=0;
    if(sscanf(s,"%4d-%2d-%2dT%2d:%2d:%2d",
              &year,&month,&day,&hour,&minute,&second)!=6)return false;
    if(month<1||month>12||hour>23||minute>59||second>59)return false;
    const int lengths[]={31,28,31,30,31,30,31,31,30,31,30,31};
    int last=lengths[month-1];
    if(month==2&&(year%4==0&&(year%100!=0||year%400==0)))last=29;
    return day>=1&&day<=last;
}
void pmkb_notebook_init(PMKBNotebook *book){
    if(book)memset(book,0,sizeof(*book));
}
void pmkb_notebook_free(PMKBNotebook *book){
    if(!book)return;
    for(size_t i=0;i<book->count;i++){
        PMKBNote *note=book->items[i];
        if(note){
            pmkb_text_free(&note->title);
            pmkb_text_free(&note->body);
            free(note);
        }
    }
    memset(book,0,sizeof(*book));
}
PMKBStatus pmkb_notebook_new(PMKBNotebook *book,const char *utc,size_t *index){
    if(!book||!index||!iso8601(utc))return PMKB_INVALID;
    if(book->count>=PMKB_NOTE_LIMIT)return PMKB_LIMIT;
    if(book->next_id>=999999u)return PMKB_LIMIT;
    PMKBNote *n=(PMKBNote*)calloc(1,sizeof(*n));
    if(!n)return PMKB_MEMORY;
    PMKBStatus rc=pmkb_text_init(&n->title,PMKB_TITLE_LIMIT,"Sans titre");
    if(rc==PMKB_OK)rc=pmkb_text_init(&n->body,PMKB_BODY_LIMIT,"");
    if(rc!=PMKB_OK){
        pmkb_text_free(&n->title);pmkb_text_free(&n->body);free(n);
        return rc;
    }
    unsigned next=book->next_id+1u;
    (void)snprintf(n->id,sizeof(n->id),"pmkb_%06u",next);
    memcpy(n->created,utc,strlen(utc)+1);
    memcpy(n->updated,utc,strlen(utc)+1);
    book->items[book->count]=n;
    *index=book->count++;
    book->next_id=next;
    return PMKB_OK;
}
PMKBStatus pmkb_notebook_find(const PMKBNotebook *book,const char *id,
                               size_t *index){
    if(!book||!id||!index)return PMKB_INVALID;
    for(size_t i=0;i<book->count;i++){
        if(book->items[i]&&strcmp(id,book->items[i]->id)==0){
            *index=i;return PMKB_OK;
        }
    }
    return PMKB_NOT_FOUND;
}
typedef struct { char *data;size_t len,cap; } Json;
static PMKBStatus reserve(Json *j,size_t add){
    if(add>PMKB_JSON_LIMIT || j->len>PMKB_JSON_LIMIT-add)return PMKB_LIMIT;
    size_t want=j->len+add+1;
    if(want<=j->cap)return PMKB_OK;
    size_t cap=j->cap?j->cap:256;
    while(cap<want){
        if(cap>PMKB_JSON_LIMIT/2){cap=PMKB_JSON_LIMIT+1;break;}
        cap*=2;
    }
    if(cap<want)return PMKB_LIMIT;
    char *tmp=(char*)realloc(j->data,cap);
    if(!tmp)return PMKB_MEMORY;
    j->data=tmp;j->cap=cap;return PMKB_OK;
}
static PMKBStatus append(Json *j,const char *text,size_t len){
    PMKBStatus rc=reserve(j,len);if(rc!=PMKB_OK)return rc;
    memcpy(j->data+j->len,text,len);
    j->len+=len;j->data[j->len]=0;return PMKB_OK;
}
static PMKBStatus literal(Json *j,const char *text){
    return append(j,text,strlen(text));
}
static PMKBStatus quoted(Json *j,const char *text){
    PMKBStatus rc=literal(j,"\"");if(rc!=PMKB_OK)return rc;
    for(const unsigned char *p=(const unsigned char*)text;*p;p++){
        char escaped[7]={0};
        const char *substitute=NULL;
        switch(*p){
        case '"':substitute="\\\"";break;
        case '\\':substitute="\\\\";break;
        case '\n':substitute="\\n";break;
        case '\r':substitute="\\r";break;
        case '\t':substitute="\\t";break;
        case '\b':substitute="\\b";break;
        case '\f':substitute="\\f";break;
        default:
            if(*p<32){(void)snprintf(escaped,sizeof(escaped),"\\u%04x",*p);
                       substitute=escaped;}
        }
        if(substitute)rc=literal(j,substitute);
        else rc=append(j,(const char*)p,1);
        if(rc!=PMKB_OK)return rc;
    }
    return literal(j,"\"");
}
PMKBStatus pmkb_notebook_export_json(const PMKBNotebook *book,
                                      char **json,size_t *length){
    if(!book||!json||!length||book->count>PMKB_NOTE_LIMIT)return PMKB_INVALID;
    *json=NULL;*length=0;
    Json j={0};PMKBStatus rc=literal(&j,"{\"format\":\"pmkb-notes-v1\",\"notes\":[");
    for(size_t i=0;rc==PMKB_OK&&i<book->count;i++){
        const PMKBNote *n=book->items[i];
        if(!n||!n->title.data||!n->body.data)return free(j.data),PMKB_INVALID;
        if(i)rc=literal(&j,",");
        if(rc==PMKB_OK)rc=literal(&j,"{\"id\":");
        if(rc==PMKB_OK)rc=quoted(&j,n->id);
        if(rc==PMKB_OK)rc=literal(&j,",\"title\":");
        if(rc==PMKB_OK)rc=quoted(&j,n->title.data);
        if(rc==PMKB_OK)rc=literal(&j,",\"text\":");
        if(rc==PMKB_OK)rc=quoted(&j,n->body.data);
        if(rc==PMKB_OK)rc=literal(&j,
          ",\"strokes\":[],\"typography\":{\"font\":\"mono\",\"size\":17,\"lineHeight\":1.6},\"created\":");
        if(rc==PMKB_OK)rc=quoted(&j,n->created);
        if(rc==PMKB_OK)rc=literal(&j,",\"updated\":");
        if(rc==PMKB_OK)rc=quoted(&j,n->updated);
        if(rc==PMKB_OK)rc=literal(&j,"}");
    }
    if(rc==PMKB_OK)rc=literal(&j,"]}");
    if(rc!=PMKB_OK){free(j.data);return rc;}
    *json=j.data;*length=j.len;return PMKB_OK;
}
