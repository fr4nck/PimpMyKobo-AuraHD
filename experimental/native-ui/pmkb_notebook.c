#include "pmkb_ui.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

bool pmkb_notes_valid_utc(const char *s) {
    if(!s) return false;
    size_t n=strlen(s);
    if(n!=20 && n!=24) return false;
    const int cuts[]={4,7,10,13,16};
    for(int i=0;i<5;i++)
        if(s[cuts[i]]!=(i<2?'-':i==2?'T':':'))return false;
    for(size_t i=0;i<n;i++){
        if(i==4||i==7||i==10||i==13||i==16)continue;
        if((n==20&&i==19)||(n==24&&i==23)){
            if(s[i]!='Z')return false;
            continue;
        }
        if(n==24&&i==19){
            if(s[i]!='.')return false;
            continue;
        }
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
/* A title can be temporarily empty during editing, but must not be
 * serialized if the JS Notes importer would reject it. */
bool pmkb_notes_meaningful_title(const char *s){
    if(!s)return false;
    const unsigned char *p=(const unsigned char*)s;
    while(*p){
        uint32_t cp=*p;
        int count=1;
        if(*p>=0xf0){cp=*p&7u;count=4;}
        else if(*p>=0xe0){cp=*p&15u;count=3;}
        else if(*p>=0xc0){cp=*p&31u;count=2;}
        for(int i=1;i<count;i++)cp=(cp<<6)|(p[i]&63u);
        if(!((cp>=9&&cp<=13)||cp==32||cp==0x85||cp==0xa0||
             cp==0x1680||(cp>=0x2000&&cp<=0x200a)||
             cp==0x2028||cp==0x2029||cp==0x202f||
             cp==0x205f||cp==0x3000||cp==0xfeff))
            return true;
        p+=count;
    }
    return false;
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
    if(!book||!index||!pmkb_notes_valid_utc(utc))return PMKB_INVALID;
    if(book->count>=PMKB_NOTE_LIMIT)return PMKB_LIMIT;
    if(book->next_id>=999999u)return PMKB_LIMIT;
    PMKBNote *n=(PMKBNote*)calloc(1,sizeof(*n));
    if(!n)return PMKB_MEMORY;
    unsigned next=book->next_id+1u;
    char fallback[32];
    (void)snprintf(fallback,sizeof(fallback),"Sans titre %u",next);
    PMKBStatus rc=pmkb_text_init(&n->title,PMKB_TITLE_LIMIT,fallback);
    if(rc==PMKB_OK)rc=pmkb_text_init(&n->body,PMKB_BODY_LIMIT,"");
    if(rc!=PMKB_OK){
        pmkb_text_free(&n->title);pmkb_text_free(&n->body);free(n);
        return rc;
    }
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
        if(!n||!n->title.data||!n->body.data)
            return free(j.data),PMKB_INVALID;
        size_t title_units=0,body_units=0;
        if(pmkb_utf8_measure(n->title.data,n->title.bytes,&title_units)!=PMKB_OK ||
           pmkb_utf8_measure(n->body.data,n->body.bytes,&body_units)!=PMKB_OK ||
           !pmkb_notes_meaningful_title(n->title.data) ||
           title_units>PMKB_TITLE_LIMIT||body_units>PMKB_BODY_LIMIT ||
           !pmkb_notes_valid_utc(n->created)||!pmkb_notes_valid_utc(n->updated))
            return free(j.data),PMKB_INVALID;
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


/* L09-B: narrow, canonical C11-generated pmkb-notes-v1 importer.
 * A general browser JSON parser is NOT implied. All allocations and
 * validation happen in a temporary notebook before replacing the caller.
 * No filesystem, clock, network, mount, or physical device access. */
typedef struct {const uint8_t *bytes;size_t length,pos;} NotesReader;

static bool notes_take(NotesReader *r,unsigned char ch){
    if(r->pos>=r->length||r->bytes[r->pos]!=ch)return false;
    r->pos++;return true;
}
static bool notes_literal(NotesReader *r,const char *literal){
    size_t n=strlen(literal);
    if(n>r->length-r->pos||memcmp(r->bytes+r->pos,literal,n)!=0)
        return false;
    r->pos+=n;return true;
}
static int notes_hex(unsigned char c){
    if(c>='0'&&c<='9')return c-'0';
    if(c>='a'&&c<='f')return c-'a'+10;
    if(c>='A'&&c<='F')return c-'A'+10;
    return -1;
}
static PMKBStatus notes_quoted(NotesReader *r,size_t units_limit,char **value){
    if(!value||!notes_take(r,'"'))return PMKB_INVALID;
    *value=NULL;
    size_t cap=64u,used=0u;
    char *buffer=(char*)malloc(cap);
    if(!buffer)return PMKB_MEMORY;
    const size_t max_bytes=units_limit*4u;
    PMKBStatus rc=PMKB_INVALID;
    while(r->pos<r->length){
        unsigned char ch=r->bytes[r->pos++];
        if(ch=='"'){
            buffer[used]=0;
            size_t units=0;
            rc=pmkb_utf8_measure(buffer,used,&units);
            if(rc!=PMKB_OK||units>units_limit){rc=PMKB_INVALID;break;}
            *value=buffer;
            return PMKB_OK;
        }
        if(ch=='\\'){
            if(r->pos>=r->length)break;
            unsigned char escaped=r->bytes[r->pos++];
            switch(escaped){
            case '"':ch='"';break;
            case '\\':ch='\\';break;
            case 'n':ch='\n';break;
            case 'r':ch='\r';break;
            case 't':ch='\t';break;
            case 'b':ch='\b';break;
            case 'f':ch='\f';break;
            case 'u':{
                /* C11 exports control bytes only as \u00XX.
                 * Reject browser-style unicode escape forms for now. */
                if(r->length-r->pos<4u||
                   r->bytes[r->pos]!='0'||
                   r->bytes[r->pos+1u]!='0')goto fail;
                int high=notes_hex(r->bytes[r->pos+2u]);
                int low=notes_hex(r->bytes[r->pos+3u]);
                if(high<0||low<0)goto fail;
                int cp=high*16+low;
                if(cp<1||cp>31)goto fail;
                ch=(unsigned char)cp;
                r->pos+=4u;
                break;
            }
            default:goto fail;
            }
        }else if(ch<32u)goto fail;
        if(ch==0u)goto fail;
        if(used>=max_bytes){rc=PMKB_LIMIT;break;}
        if(used+1u>=cap){
            size_t target=cap*2u;
            if(target>max_bytes+1u)target=max_bytes+1u;
            if(target<=cap){rc=PMKB_LIMIT;break;}
            char *grown=(char*)realloc(buffer,target);
            if(!grown){rc=PMKB_MEMORY;break;}
            buffer=grown;cap=target;
        }
        buffer[used++]=(char)ch;
    }
fail:
    free(buffer);
    return rc;
}
static PMKBStatus notes_import_one(NotesReader *r,PMKBNotebook *staged){
    char *id=NULL,*title=NULL,*body=NULL,*created=NULL,*updated=NULL;
    PMKBNote *note=NULL;
    PMKBStatus rc=PMKB_INVALID;
    if(!notes_literal(r,"{\"id\":"))goto done;
    rc=notes_quoted(r,24u,&id);if(rc!=PMKB_OK)goto done;
    if(strlen(id)!=11u||memcmp(id,"pmkb_",5u)!=0){rc=PMKB_INVALID;goto done;}
    unsigned number=0;
    for(size_t i=5u;i<11u;i++){
        if(id[i]<'0'||id[i]>'9'){rc=PMKB_INVALID;goto done;}
        number=number*10u+(unsigned)(id[i]-'0');
    }
    if(number==0u){rc=PMKB_INVALID;goto done;}
    for(size_t i=0;i<staged->count;i++){
        if(strcmp(staged->items[i]->id,id)==0){rc=PMKB_INVALID;goto done;}
    }
    if(!notes_literal(r,",\"title\":")){rc=PMKB_INVALID;goto done;}
    rc=notes_quoted(r,PMKB_TITLE_LIMIT,&title);if(rc!=PMKB_OK)goto done;
    if(!pmkb_notes_meaningful_title(title)){rc=PMKB_INVALID;goto done;}
    if(!notes_literal(r,",\"text\":")){rc=PMKB_INVALID;goto done;}
    rc=notes_quoted(r,PMKB_BODY_LIMIT,&body);if(rc!=PMKB_OK)goto done;
    if(!notes_literal(r,
      ",\"strokes\":[],\"typography\":{\"font\":\"mono\",\"size\":17,\"lineHeight\":1.6},\"created\":")){
        rc=PMKB_INVALID;goto done;
    }
    rc=notes_quoted(r,24u,&created);if(rc!=PMKB_OK)goto done;
    if(!pmkb_notes_valid_utc(created)){rc=PMKB_INVALID;goto done;}
    if(!notes_literal(r,",\"updated\":")){rc=PMKB_INVALID;goto done;}
    rc=notes_quoted(r,24u,&updated);if(rc!=PMKB_OK)goto done;
    if(!pmkb_notes_valid_utc(updated)||!notes_take(r,'}')){
        rc=PMKB_INVALID;goto done;
    }
    note=(PMKBNote*)calloc(1,sizeof(*note));
    if(!note){rc=PMKB_MEMORY;goto done;}
    rc=pmkb_text_init(&note->title,PMKB_TITLE_LIMIT,title);
    if(rc!=PMKB_OK)goto done;
    rc=pmkb_text_init(&note->body,PMKB_BODY_LIMIT,body);
    if(rc!=PMKB_OK)goto done;
    memcpy(note->id,id,12u);
    memcpy(note->created,created,strlen(created)+1u);
    memcpy(note->updated,updated,strlen(updated)+1u);
    staged->items[staged->count++]=note;
    if(number>staged->next_id)staged->next_id=number;
    note=NULL;
    rc=PMKB_OK;
done:
    if(note){
        pmkb_text_free(&note->title);
        pmkb_text_free(&note->body);
        free(note);
    }
    free(id);free(title);free(body);free(created);free(updated);
    return rc;
}
PMKBStatus pmkb_notebook_import_native_json(PMKBNotebook *book,
                                              const uint8_t *json,size_t length){
    if(!book||!json||length==0u)return PMKB_INVALID;
    if(length>PMKB_JSON_LIMIT)return PMKB_LIMIT;
    NotesReader reader={json,length,0};
    PMKBNotebook staged;
    pmkb_notebook_init(&staged);
    PMKBStatus rc=PMKB_INVALID;
    if(!notes_literal(&reader,"{\"format\":\"pmkb-notes-v1\",\"notes\":["))
        goto done;
    if(!notes_take(&reader,']')){
        do{
            if(staged.count>=PMKB_NOTE_LIMIT){rc=PMKB_LIMIT;goto done;}
            rc=notes_import_one(&reader,&staged);
            if(rc!=PMKB_OK)goto done;
            if(notes_take(&reader,']'))break;
            if(!notes_take(&reader,',')){rc=PMKB_INVALID;goto done;}
        }while(1);
    }
    if(!notes_take(&reader,'}')||reader.pos!=reader.length){
        rc=PMKB_INVALID;goto done;
    }
    pmkb_notebook_free(book);
    *book=staged;
    return PMKB_OK;
done:
    pmkb_notebook_free(&staged);
    return rc;
}
