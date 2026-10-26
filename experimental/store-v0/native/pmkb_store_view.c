#include "pmkb_store_view.h"
#include <string.h>

/* D1 emits sorted JSON keys and ASCII-only escaped JSON with no whitespace.
 * A deliberately narrow parser avoids a general JSON engine on i.MX50. */
typedef struct { const uint8_t *s; size_t n, i; } Reader;

static bool take(Reader *r, char c) {
    if (r->i >= r->n || r->s[r->i] != (uint8_t)c) return false;
    r->i++;
    return true;
}
static bool literal(Reader *r, const char *s) {
    size_t n=strlen(s);
    if (n > r->n-r->i || memcmp(r->s+r->i,s,n)!=0) return false;
    r->i+=n;
    return true;
}
static bool decimal(Reader *r, unsigned max, unsigned *out) {
    unsigned v=0; size_t start=r->i;
    if (r->i>=r->n || r->s[r->i]<'0' || r->s[r->i]>'9') return false;
    if (r->s[r->i]=='0') r->i++;
    else while(r->i<r->n && r->s[r->i]>='0' && r->s[r->i]<='9') {
        unsigned digit=(unsigned)(r->s[r->i++]-'0');
        if (v>(max-digit)/10u) return false;
        v=v*10u+digit;
    }
    if (r->i==start) return false;
    *out=v;
    return true;
}
static int hex4(Reader *r) {
    unsigned v=0;
    for (int i=0;i<4;i++) {
        if (r->i==r->n) return -1;
        uint8_t c=r->s[r->i++];
        int d=(c>='0'&&c<='9')?c-'0':(c>='a'&&c<='f')?c-'a'+10:
              (c>='A'&&c<='F')?c-'A'+10:-1;
        if (d<0) return -1;
        v=(v<<4)|(unsigned)d;
    }
    return (int)v;
}
static bool scalar(char *out, size_t cap, size_t *used, unsigned *scalars,
                   unsigned limit, unsigned cp) {
    unsigned char bytes[4]; size_t len;
    if (cp==0 || cp>0x10FFFFu || (cp>=0xD800u&&cp<=0xDFFFu)
        || *scalars>=limit) return false;
    if (cp<0x80u) {bytes[0]=(unsigned char)cp;len=1;}
    else if (cp<0x800u) {
        bytes[0]=(unsigned char)(0xC0u|(cp>>6));bytes[1]=(unsigned char)(0x80u|(cp&63));len=2;
    } else if (cp<0x10000u) {
        bytes[0]=(unsigned char)(0xE0u|(cp>>12));bytes[1]=(unsigned char)(0x80u|((cp>>6)&63));
        bytes[2]=(unsigned char)(0x80u|(cp&63));len=3;
    } else {
        bytes[0]=(unsigned char)(0xF0u|(cp>>18));bytes[1]=(unsigned char)(0x80u|((cp>>12)&63));
        bytes[2]=(unsigned char)(0x80u|((cp>>6)&63));bytes[3]=(unsigned char)(0x80u|(cp&63));len=4;
    }
    if (len>=cap-*used) return false; /* reserve terminating NUL */
    memcpy(out+*used,bytes,len);*used+=len;(*scalars)++;
    return true;
}
static bool json_string(Reader *r, char *out, size_t cap, unsigned limit) {
    size_t used=0;unsigned scalars=0;
    if (!take(r,'"') || cap==0) return false;
    while(r->i<r->n) {
        unsigned cp=r->s[r->i++];
        if (cp=='"') {out[used]='\0';return true;}
        if (cp=='\\') {
            if (r->i>=r->n) return false;
            uint8_t e=r->s[r->i++];
            switch(e) {
            case '"':cp='"';break;case '\\':cp='\\';break;case '/':cp='/';break;
            case 'b':cp='\b';break;case 'f':cp='\f';break;case 'n':cp='\n';break;
            case 'r':cp='\r';break;case 't':cp='\t';break;
            case 'u':{
                int hi=hex4(r);
                if (hi<0) return false;
                cp=(unsigned)hi;
                if (cp>=0xD800u&&cp<=0xDBFFu) {
                    if (!literal(r,"\\u")) return false;
                    int lo=hex4(r);
                    if (lo<0xDC00 || lo>0xDFFF) return false;
                    cp=0x10000u+((cp-0xD800u)<<10)+((unsigned)lo-0xDC00u);
                } else if (cp>=0xDC00u&&cp<=0xDFFFu) return false;
                break;
            }
            default:return false;
            }
        } else if (cp<32 || cp>126) return false; /* D1 always emits ASCII */
        if (!scalar(out,cap,&used,&scalars,limit,cp)) return false;
    }
    return false;
}
static bool valid_id(const char *s) {
    size_t total=0,part=0; unsigned dots=0;
    for(;*s;s++,total++) {
        unsigned char c=(unsigned char)*s;
        if (c=='.') {if(!part)return false;part=0;dots++;continue;}
        if (part==0) {if(c<'a'||c>'z')return false;}
        else if(!((c>='a'&&c<='z')||(c>='0'&&c<='9')||c=='-'))return false;
        if (++part>31 || total>=120) return false;
    }
    return dots>0 && part>0;
}
static bool valid_version(const char *s) {
    unsigned parts=0;
    while(*s) {
        unsigned n=0;
        if (*s=='0') {s++;if(*s>='0'&&*s<='9')return false;}
        else {
            if(*s<'1'||*s>'9')return false;
            while(*s>='0'&&*s<='9') {if(++n>6)return false;s++;}
        }
        parts++;
        if(!*s)break;
        if(*s++!='.')return false;
    }
    return parts==3;
}
static bool item(Reader *r, PMKBStoreViewItem *v) {
    if (!literal(r,"{\"id\":")) return false;
    if (!json_string(r,v->id,sizeof(v->id),120)||!valid_id(v->id)) return false;
    if (!literal(r,",\"label\":")) return false;
    if (!json_string(r,v->label,sizeof(v->label),80)||!v->label[0])return false;
    if (!literal(r,",\"launchable\":false,\"network_declared\":"))return false;
    if (literal(r,"true"))v->network_declared=true;
    else if (literal(r,"false"))v->network_declared=false;
    else return false;
    if (!literal(r,",\"state\":\"installed_unverified\",\"version\":"))return false;
    if (!json_string(r,v->version,sizeof(v->version),24)||!valid_version(v->version))return false;
    v->launchable=false;
    return take(r,'}');
}
PMKBStoreViewStatus pmkb_store_view_parse(const uint8_t *json, size_t length,
                                          PMKBStoreView *out) {
    if (!out) return PMKB_STORE_VIEW_INVALID;
    memset(out,0,sizeof(*out));
    if (!json || length==0) return PMKB_STORE_VIEW_INVALID;
    if (length>PMKB_STORE_VIEW_MAX_JSON)return PMKB_STORE_VIEW_LIMIT;
    Reader r={json,length,0}; unsigned pending=0;
    if (!literal(&r,"{\"cleanup_pending_count\":"))goto invalid;
    if (!decimal(&r,PMKB_STORE_VIEW_MAX_PENDING,&pending))goto invalid;
    out->cleanup_pending_count=pending;
    if (!literal(&r,",\"items\":["))goto invalid;
    if (!take(&r,']')) {
        do {
            if(out->count>=PMKB_STORE_VIEW_MAX_APPS)goto limit;
            PMKBStoreViewItem *current=&out->items[out->count];
            if(!item(&r,current))goto invalid;
            if(out->count>0 && strcmp(out->items[out->count-1].id,current->id)>=0)
                goto invalid;
            out->count++;
            if(take(&r,']')) break;
            if(!take(&r,','))goto invalid;
        } while(1);
    }
    if (!literal(&r,",\"schema\":\"pmkb-store-view-v1\",\"scope\":\"synthetic_read_only\"}")) goto invalid;
    if (r.i!=r.n)goto invalid;
    return PMKB_STORE_VIEW_OK;
limit:
    memset(out,0,sizeof(*out));return PMKB_STORE_VIEW_LIMIT;
invalid:
    memset(out,0,sizeof(*out));return PMKB_STORE_VIEW_INVALID;
}
