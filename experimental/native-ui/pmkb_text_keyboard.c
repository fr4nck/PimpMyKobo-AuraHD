#include "pmkb_ui.h"
#include <limits.h>
#include <stdlib.h>
#include <string.h>

/* Decode one Unicode scalar value. Reject overlongs, surrogates and invalid tails. */
static PMKBStatus utf8_one(const unsigned char *p, size_t n, size_t *used,
                           uint32_t *scalar) {
    uint32_t value; size_t size;
    if (!n) return PMKB_INVALID;
    if (p[0] <= 0x7f) { value=p[0]; size=1; }
    else if (p[0]>=0xc2 && p[0]<=0xdf) { value=p[0]&31u; size=2; }
    else if (p[0]>=0xe0 && p[0]<=0xef) { value=p[0]&15u; size=3; }
    else if (p[0]>=0xf0 && p[0]<=0xf4) { value=p[0]&7u; size=4; }
    else return PMKB_INVALID;
    if (n<size) return PMKB_INVALID;
    for (size_t i=1;i<size;i++) {
        if ((p[i]&0xc0u)!=0x80u) return PMKB_INVALID;
        value=(value<<6)|(p[i]&0x3fu);
    }
    if ((size==2 && value<128) || (size==3 && value<2048) ||
        (size==4 && value<65536) || value>0x10ffff ||
        (value>=0xd800 && value<=0xdfff) || value==0)
        return PMKB_INVALID;
    *used=size; *scalar=value; return PMKB_OK;
}
PMKBStatus pmkb_utf8_measure(const char *s, size_t bytes, size_t *utf16) {
    if (!s || !utf16) return PMKB_INVALID;
    size_t result=0;
    for (size_t i=0;i<bytes;) {
        size_t consumed; uint32_t cp;
        PMKBStatus rc=utf8_one((const unsigned char*)s+i,bytes-i,&consumed,&cp);
        if(rc!=PMKB_OK) return rc;
        /* Allow ordinary whitespace, but reject script/control characters. */
        if ((cp<32 && cp!=10 && cp!=9) || cp==127) return PMKB_INVALID;
        if (result>SIZE_MAX-(cp>0xffff?2u:1u)) return PMKB_LIMIT;
        result+=(cp>0xffff?2u:1u);
        i+=consumed;
    }
    *utf16=result;
    return PMKB_OK;
}
static bool boundary(const PMKBText *t, size_t pos) {
    return pos<=t->bytes && (pos==0 || pos==t->bytes ||
                             (((unsigned char)t->data[pos]&0xc0u)!=0x80u));
}
PMKBStatus pmkb_text_init(PMKBText *t, size_t max_utf16, const char *initial) {
    if(!t || max_utf16==0 || max_utf16>PMKB_BODY_LIMIT) return PMKB_INVALID;
    memset(t,0,sizeof(*t));t->max_utf16=max_utf16;
    PMKBStatus rc=pmkb_text_set(t,initial?initial:"");
    if(rc!=PMKB_OK) memset(t,0,sizeof(*t));
    return rc;
}
void pmkb_text_free(PMKBText *t){
    if(!t) return;
    free(t->data);memset(t,0,sizeof(*t));
}
PMKBStatus pmkb_text_set(PMKBText *t, const char *value){
    if(!t || !value || !t->max_utf16) return PMKB_INVALID;
    size_t n=strlen(value),units=0;
    if (n>t->max_utf16*4u) return PMKB_LIMIT;
    PMKBStatus rc=pmkb_utf8_measure(value,n,&units);
    if(rc!=PMKB_OK) return rc;
    if(units>t->max_utf16) return PMKB_LIMIT;
    char *next=(char*)malloc(n+1);
    if(!next) return PMKB_MEMORY;
    memcpy(next,value,n+1);
    free(t->data);t->data=next;t->bytes=n;
    t->anchor=t->cursor=n;
    return PMKB_OK;
}
PMKBStatus pmkb_text_select(PMKBText *t,size_t a,size_t b){
    if(!t||!t->data||!boundary(t,a)||!boundary(t,b))return PMKB_INVALID;
    t->anchor=a;t->cursor=b;return PMKB_OK;
}
size_t pmkb_text_utf16_length(const PMKBText *t){
    size_t units=0;
    if(!t||!t->data)return 0;
    if(pmkb_utf8_measure(t->data,t->bytes,&units)!=PMKB_OK)return 0;
    return units;
}
PMKBStatus pmkb_text_insert(PMKBText *t,const char *insert){
    if(!t||!t->data||!insert||!boundary(t,t->anchor)||!boundary(t,t->cursor))
        return PMKB_INVALID;
    size_t n=strlen(insert),units=0;
    if(n>PMKB_BODY_LIMIT*4u)return PMKB_LIMIT;
    PMKBStatus rc=pmkb_utf8_measure(insert,n,&units);
    if(rc!=PMKB_OK)return rc;
    size_t a=t->anchor<t->cursor?t->anchor:t->cursor;
    size_t b=t->anchor>t->cursor?t->anchor:t->cursor;
    size_t removed=0,old=pmkb_text_utf16_length(t);
    if(pmkb_utf8_measure(t->data+a,b-a,&removed)!=PMKB_OK)return PMKB_INVALID;
    if(units>t->max_utf16-(old-removed)) return PMKB_LIMIT;
    if(t->bytes-(b-a)>SIZE_MAX-n-1)return PMKB_LIMIT;
    size_t length=t->bytes-(b-a)+n;
    char *next=(char*)malloc(length+1);if(!next)return PMKB_MEMORY;
    memcpy(next,t->data,a);
    memcpy(next+a,insert,n);
    memcpy(next+a+n,t->data+b,t->bytes-b);
    next[length]=0;
    if(length==t->bytes && strcmp(next,t->data)==0) {
        free(next);t->anchor=t->cursor=a+n;return PMKB_NO_CHANGE;
    }
    free(t->data);t->data=next;t->bytes=length;t->anchor=t->cursor=a+n;
    return PMKB_OK;
}
static size_t prior(const PMKBText *t,size_t pos){
    if(!pos)return 0;
    size_t i=pos-1;
    while(i>0&&(((unsigned char)t->data[i]&0xc0u)==0x80u))i--;
    return i;
}
static size_t next(const PMKBText *t,size_t pos){
    if(pos>=t->bytes)return t->bytes;
    size_t i=pos+1;
    while(i<t->bytes&&(((unsigned char)t->data[i]&0xc0u)==0x80u))i++;
    return i;
}
PMKBStatus pmkb_text_backspace(PMKBText *t){
    if(!t||!t->data||!boundary(t,t->anchor)||!boundary(t,t->cursor))
        return PMKB_INVALID;
    if(t->anchor!=t->cursor)return pmkb_text_insert(t,"");
    if(t->cursor==0)return PMKB_NO_CHANGE;
    size_t b=t->cursor;
    t->anchor=prior(t,b);
    PMKBStatus rc=pmkb_text_insert(t,"");
    if(rc!=PMKB_OK && rc!=PMKB_NO_CHANGE)t->anchor=b;
    return rc;
}
PMKBStatus pmkb_text_move(PMKBText *t,int direction){
    if(!t||!t->data||!boundary(t,t->anchor)||!boundary(t,t->cursor)||
       (direction!=1&&direction!=-1))return PMKB_INVALID;
    size_t a=t->anchor<t->cursor?t->anchor:t->cursor;
    size_t b=t->anchor>t->cursor?t->anchor:t->cursor;
    size_t target=(a!=b)?(direction<0?a:b):
                 (direction<0?prior(t,t->cursor):next(t,t->cursor));
    if(target==t->cursor&&a==b)return PMKB_NO_CHANGE;
    t->anchor=t->cursor=target;return PMKB_OK;
}

static const char *letters[5][6]={
    {"a","z","e","r","t","y"},
    {"u","i","o","p","q","s"},
    {"d","f","g","h","j","k"},
    {"l","m","w","x","c","v"},
    {"b","n","\xc3\xa9","\xc3\xa8","\xc3\xa0","\xc3\xa7"}
};
static const char *caps[5][6]={
    {"A","Z","E","R","T","Y"},
    {"U","I","O","P","Q","S"},
    {"D","F","G","H","J","K"},
    {"L","M","W","X","C","V"},
    {"B","N","\xc3\x89","\xc3\x88","\xc3\x80","\xc3\x87"}
};
static const char *digits[5][6]={
    {"1","2","3","4","5","6"},{"7","8","9","0",".",","},
    {"+","-","*","/","=","%"},{"(",")","[","]",":",";"},
    {"!","?","@","#","_","\xe2\x82\xac"}
};
static const char *symbols[5][6]={
    {"!","?","@","#","_","&"},{"(",")","[","]","{","}"},
    {"<",">","=","+","-","*"},{"~","|","/","\\","^","%"},
    {";",":","'", "\"",",","."}
};
/* Compact labels for E-Ink. Insertions follow the parser in the browser
 * calculator prototype; "=" and DEG/RAD are semantic actions, not text. */
static const PMKBKey scientific[5][6]={
    {
        {PMKB_KEY_INSERT,"sin","sin(",1},
        {PMKB_KEY_INSERT,"cos","cos(",1},
        {PMKB_KEY_INSERT,"tan","tan(",1},
        {PMKB_KEY_INSERT,"ln","ln(",1},
        {PMKB_KEY_INSERT,"log","log(",1},
        {PMKB_KEY_INSERT,"sqrt","sqrt(",1}
    },{
        {PMKB_KEY_INSERT,"7","7",1},{PMKB_KEY_INSERT,"8","8",1},
        {PMKB_KEY_INSERT,"9","9",1},{PMKB_KEY_INSERT,"/","/",1},
        {PMKB_KEY_INSERT,"(","(",1},{PMKB_KEY_INSERT,")",")",1}
    },{
        {PMKB_KEY_INSERT,"4","4",1},{PMKB_KEY_INSERT,"5","5",1},
        {PMKB_KEY_INSERT,"6","6",1},{PMKB_KEY_INSERT,"*","*",1},
        {PMKB_KEY_INSERT,"^","^",1},{PMKB_KEY_INSERT,"pi","\xcf\x80",1}
    },{
        {PMKB_KEY_INSERT,"1","1",1},{PMKB_KEY_INSERT,"2","2",1},
        {PMKB_KEY_INSERT,"3","3",1},{PMKB_KEY_INSERT,"-","-",1},
        {PMKB_KEY_INSERT,"%","%",1},{PMKB_KEY_INSERT,"e","e",1}
    },{
        {PMKB_KEY_INSERT,"0","0",1},{PMKB_KEY_INSERT,".",".",1},
        {PMKB_KEY_INSERT,"Ans","Ans",1},{PMKB_KEY_INSERT,"+","+",1},
        {PMKB_KEY_INSERT,"abs","abs(",1},{PMKB_KEY_ANGLE,"DEG",NULL,1}
    }
};
static const PMKBKey scientific_inverse[3]={
    {PMKB_KEY_INSERT,"asin","asin(",1},
    {PMKB_KEY_INSERT,"acos","acos(",1},
    {PMKB_KEY_INSERT,"atan","atan(",1}
};
static const PMKBKey scientific_actions[6]={
    {PMKB_KEY_SHIFT,"INV",NULL,1},
    {PMKB_KEY_MODE,"ABC",NULL,1},
    {PMKB_KEY_CLEAR,"C",NULL,2},
    {PMKB_KEY_CLEAR,"C",NULL,2},
    {PMKB_KEY_BACKSPACE,"DEL",NULL,1},
    {PMKB_KEY_EVALUATE,"=",NULL,1}
};

void pmkb_keyboard_open(PMKBKeyboard *kb,PMKBKeyboardPage page){
    if(!kb)return;
    if((unsigned)page>(unsigned)PMKB_KB_SCIENTIFIC)return;
    kb->page=page;kb->shifted=false;kb->visible=true;
    kb->degrees=true;
}
void pmkb_keyboard_close(PMKBKeyboard *kb){
    if(kb)kb->visible=false;
}
PMKBKey pmkb_keyboard_key(const PMKBKeyboard *kb,int row,int col){
    PMKBKey none={PMKB_KEY_HIDE,"",NULL,0};
    if(!kb||row<0||row>=PMKB_KB_ROWS||col<0||col>=PMKB_KB_COLS||
       (unsigned)kb->page>(unsigned)PMKB_KB_SCIENTIFIC)return none;
    if(kb->page==PMKB_KB_SCIENTIFIC){
        if(row<5){
            if(row==0&&col<3&&kb->shifted)return scientific_inverse[col];
            PMKBKey key=scientific[row][col];
            if(row==4&&col==5)key.label=kb->degrees?"DEG":"RAD";
            return key;
        }
        if(row==5)return scientific_actions[col];
        /* Row six uses the common navigation and close controls. */
    }
    if(row<5){
        const char *v=kb->page==PMKB_KB_AZERTY?
            (kb->shifted?caps[row][col]:letters[row][col]):
            (kb->page==PMKB_KB_NUMERIC?digits[row][col]:symbols[row][col]);
        PMKBKey k={PMKB_KEY_INSERT,v,v,1};return k;
    }
    if(row==5){
        static const PMKBKey actions[6]={
            {PMKB_KEY_SHIFT,"^",NULL,1},
            {PMKB_KEY_MODE,"123",NULL,1},
            {PMKB_KEY_SPACE,"ESPACE"," ",2},
            {PMKB_KEY_SPACE,"ESPACE"," ",2},
            {PMKB_KEY_BACKSPACE,"<",NULL,1},
            {PMKB_KEY_ENTER,"ENTREE",NULL,1}
        };
        PMKBKey k=actions[col];
        if(col==1&&kb->page==PMKB_KB_NUMERIC)k.label="SYM";
        if(col==1&&kb->page==PMKB_KB_SYMBOLS)k.label="ABC";
        return k;
    }
    static const PMKBKey navigation[6]={
        {PMKB_KEY_LEFT,"GAUCHE",NULL,2},{PMKB_KEY_LEFT,"GAUCHE",NULL,2},
        {PMKB_KEY_RIGHT,"DROITE",NULL,2},{PMKB_KEY_RIGHT,"DROITE",NULL,2},
        {PMKB_KEY_HIDE,"FERMER",NULL,2},{PMKB_KEY_HIDE,"FERMER",NULL,2}
    };
    return navigation[col];
}
PMKBStatus pmkb_keyboard_press(PMKBKeyboard *kb,PMKBText *target,
                               PMKBKey key,bool multiline){
    if(!kb||!kb->visible||!target)return PMKB_INVALID;
    PMKBStatus rc=PMKB_NO_CHANGE;
    switch(key.action){
    case PMKB_KEY_SHIFT:kb->shifted=!kb->shifted;return PMKB_OK;
    case PMKB_KEY_ANGLE:
        if(kb->page!=PMKB_KB_SCIENTIFIC)return PMKB_INVALID;
        kb->degrees=!kb->degrees;return PMKB_OK;
    case PMKB_KEY_CLEAR:
        return kb->page==PMKB_KB_SCIENTIFIC?
               pmkb_text_set(target,""):PMKB_INVALID;
    case PMKB_KEY_EVALUATE:
        return kb->page==PMKB_KB_SCIENTIFIC?PMKB_EVALUATE:PMKB_INVALID;
    case PMKB_KEY_MODE:
        kb->page=(kb->page==PMKB_KB_AZERTY)?PMKB_KB_NUMERIC:
                 (kb->page==PMKB_KB_NUMERIC)?PMKB_KB_SYMBOLS:PMKB_KB_AZERTY;
        kb->shifted=false;return PMKB_OK;
    case PMKB_KEY_HIDE:pmkb_keyboard_close(kb);return PMKB_OK;
    case PMKB_KEY_BACKSPACE:return pmkb_text_backspace(target);
    case PMKB_KEY_LEFT:return pmkb_text_move(target,-1);
    case PMKB_KEY_RIGHT:return pmkb_text_move(target,1);
    case PMKB_KEY_ENTER:
        return multiline?pmkb_text_insert(target,"\n"):PMKB_NO_CHANGE;
    case PMKB_KEY_SPACE:return pmkb_text_insert(target," ");
    case PMKB_KEY_INSERT:
        if(!key.insert)return PMKB_INVALID;
        rc=pmkb_text_insert(target,key.insert);
        if(rc==PMKB_OK && kb->shifted)kb->shifted=false;
        return rc;
    default:return PMKB_INVALID;
    }
}
