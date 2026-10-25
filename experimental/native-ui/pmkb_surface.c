#include "pmkb_ui.h"
#include <ctype.h>
#include <stdlib.h>
#include <string.h>

/* Small, fixed invalidation budget: keep the public dirty union unchanged.
 * Two candidate rectangles are tracked without an additional framebuffer. */
static PMKBRect rect_union(PMKBRect a,PMKBRect b){
    int left=a.x<b.x?a.x:b.x,top=a.y<b.y?a.y:b.y;
    int right=a.x+a.w>b.x+b.w?a.x+a.w:b.x+b.w;
    int bottom=a.y+a.h>b.y+b.h?a.y+a.h:b.y+b.h;
    return (PMKBRect){left,top,right-left,bottom-top};
}
static size_t rect_area(PMKBRect r){
    return (size_t)r.w*(size_t)r.h;
}
static void mark(PMKBSurface *s,int x,int y,int w,int h){
    if(w<=0||h<=0)return;
    PMKBRect added={x,y,w,h};
    if(!s->has_dirty){
        s->dirty=added;s->has_dirty=true;
        s->dirty_islands[0]=added;s->dirty_island_count=1;
        return;
    }
    s->dirty=rect_union(s->dirty,added);
    if(s->dirty_island_count==0){
        s->dirty_islands[0]=s->dirty;s->dirty_island_count=1;
    }else if(s->dirty_island_count==1){
        s->dirty_islands[1]=added;s->dirty_island_count=2;
    }else{
        PMKBRect a=s->dirty_islands[0],b=s->dirty_islands[1];
        PMKBRect ab=rect_union(a,b),ac=rect_union(a,added);
        PMKBRect bc=rect_union(b,added);
        /* Merge the least expensive pair; count never exceeds two. */
        size_t cost_ab=rect_area(ab)+rect_area(added);
        size_t cost_ac=rect_area(ac)+rect_area(b);
        size_t cost_bc=rect_area(a)+rect_area(bc);
        if(cost_ab<=cost_ac&&cost_ab<=cost_bc){
            s->dirty_islands[0]=ab;s->dirty_islands[1]=added;
        }else if(cost_ac<=cost_bc){
            s->dirty_islands[0]=ac;
        }else{
            s->dirty_islands[1]=bc;
        }
    }
}
PMKBStatus pmkb_surface_init(PMKBSurface *s,int width,int height){
    if(!s||width<240||height<320||width>2000||height>2500)
        return PMKB_INVALID;
    memset(s,0,sizeof(*s));
    if((size_t)width>SIZE_MAX/(size_t)height)return PMKB_LIMIT;
    size_t n=(size_t)width*(size_t)height;
    s->gray=(uint8_t*)malloc(n);
    if(!s->gray)return PMKB_MEMORY;
    s->width=width;s->height=height;
    memset(s->gray,255,n);
    mark(s,0,0,width,height);
    s->changed_pixels=n;
    return PMKB_OK;
}
void pmkb_surface_free(PMKBSurface *s){
    if(!s)return;
    free(s->gray);memset(s,0,sizeof(*s));
}
void pmkb_surface_rect(PMKBSurface *s,PMKBRect r,uint8_t shade){
    if(!s||!s->gray||r.w<=0||r.h<=0)return;
    long long x0=r.x,y0=r.y,x1=(long long)r.x+r.w,y1=(long long)r.y+r.h;
    if(x0<0)x0=0;
    if(y0<0)y0=0;
    if(x1>s->width)x1=s->width;
    if(y1>s->height)y1=s->height;
    if(x1<=x0||y1<=y0)return;
    int left=s->width,top=s->height,right=-1,bottom=-1;
    for(int y=(int)y0;y<(int)y1;y++){
        for(int x=(int)x0;x<(int)x1;x++){
            size_t pos=(size_t)y*(size_t)s->width+(size_t)x;
            if(s->gray[pos]!=shade){
                s->gray[pos]=shade;s->changed_pixels++;
                if(x<left)left=x;
                if(y<top)top=y;
                if(x>right)right=x;
                if(y>bottom)bottom=y;
            }
        }
    }
    if(right>=left)mark(s,left,top,right-left+1,bottom-top+1);
}
bool pmkb_surface_take_dirty(PMKBSurface *s,PMKBRect *out){
    if(!s||!out||!s->has_dirty)return false;
    *out=s->dirty;s->has_dirty=false;s->dirty=(PMKBRect){0,0,0,0};
    s->changed_pixels=0;s->dirty_island_count=0;return true;
}
/* Portable 5 x 10 pixel glyphs for the host-only black-and-white preview.
 * The repertoire is intentionally small but covers French Notes, pi/root,
 * arrows and common mathematical operators without external font downloads.
 * It is NOT a full Unicode font, combining/shaping engine or LVGL adapter. */
static const uint8_t letters[26][5]={
    {0x7e,0x11,0x11,0x11,0x7e},{0x7f,0x49,0x49,0x49,0x36},
    {0x3e,0x41,0x41,0x41,0x22},{0x7f,0x41,0x41,0x22,0x1c},
    {0x7f,0x49,0x49,0x49,0x41},{0x7f,0x09,0x09,0x09,0x01},
    {0x3e,0x41,0x49,0x49,0x7a},{0x7f,0x08,0x08,0x08,0x7f},
    {0x00,0x41,0x7f,0x41,0x00},{0x20,0x40,0x41,0x3f,0x01},
    {0x7f,0x08,0x14,0x22,0x41},{0x7f,0x40,0x40,0x40,0x40},
    {0x7f,0x02,0x0c,0x02,0x7f},{0x7f,0x04,0x08,0x10,0x7f},
    {0x3e,0x41,0x41,0x41,0x3e},{0x7f,0x09,0x09,0x09,0x06},
    {0x3e,0x41,0x51,0x21,0x5e},{0x7f,0x09,0x19,0x29,0x46},
    {0x46,0x49,0x49,0x49,0x31},{0x01,0x01,0x7f,0x01,0x01},
    {0x3f,0x40,0x40,0x40,0x3f},{0x1f,0x20,0x40,0x20,0x1f},
    {0x3f,0x40,0x38,0x40,0x3f},{0x63,0x14,0x08,0x14,0x63},
    {0x03,0x04,0x78,0x04,0x03},{0x61,0x51,0x49,0x45,0x43}
};
static const uint8_t digits[10][5]={
    {0x3e,0x51,0x49,0x45,0x3e},{0x00,0x42,0x7f,0x40,0x00},
    {0x42,0x61,0x51,0x49,0x46},{0x21,0x41,0x45,0x4b,0x31},
    {0x18,0x14,0x12,0x7f,0x10},{0x27,0x45,0x45,0x45,0x39},
    {0x3c,0x4a,0x49,0x49,0x30},{0x01,0x71,0x09,0x05,0x03},
    {0x36,0x49,0x49,0x49,0x36},{0x06,0x49,0x49,0x29,0x1e}
};
static uint8_t ascii_column(char c,int col){
    unsigned char ch=(unsigned char)c;
    if(ch>='a'&&ch<='z')ch=(unsigned char)toupper(ch);
    if(ch>='A'&&ch<='Z')return letters[ch-'A'][col];
    if(ch>='0'&&ch<='9')return digits[ch-'0'][col];
    if(c==' ')return 0;
    if(c=='-')return col==2?0x08:0;
    if(c=='_')return 0x40;
    if(c=='=')return col==2?0x14:0;
    if(c=='.')return col==2?0x60:0;
    if(c==':')return col==2?0x36:0;
    if(c=='/')return (uint8_t)(1u<<(4-col));
    if(c=='+')return col==2?0x1c:0x08;
    if(c=='(')return col==1?0x3e:0;
    if(c==')')return col==3?0x3e:0;
    if(c=='?')return (uint8_t[]){0x02,0x01,0x51,0x09,0x06}[col];
    if(c=='!')return col==2?0x5f:0;
    if(c=='%')return (uint8_t[]){0x23,0x13,0x08,0x64,0x62}[col];
    if(c=='*')return (uint8_t[]){0x14,0x08,0x3e,0x08,0x14}[col];
    if(c=='^')return (uint8_t[]){0x04,0x02,0x01,0x02,0x04}[col];
    if(c=='<')return (uint8_t[]){0x08,0x14,0x22,0x41,0}[col];
    if(c=='>')return (uint8_t[]){0,0x41,0x22,0x14,0x08}[col];
    if(c==',')return col==2?0x60:col==1?0x40:0;
    if(c=='"')return col==1||col==3?0x03:0;
    if(c=='\'')return col==2?0x03:0;
    return (col==0||col==4)?0x7f:0x41;
}
typedef enum { NO_ACCENT, ACUTE, GRAVE, CIRCUMFLEX, DIAERESIS, CEDILLA } Accent;
static char accent_base(uint32_t code,Accent *mark){
    *mark=NO_ACCENT;
    switch(code){
    case 0xe9:case 0xc9:*mark=ACUTE;return code==0xe9?'e':'E';
    case 0xe8:case 0xc8:*mark=GRAVE;return code==0xe8?'e':'E';
    case 0xea:case 0xca:*mark=CIRCUMFLEX;return code==0xea?'e':'E';
    case 0xeb:case 0xcb:*mark=DIAERESIS;return code==0xeb?'e':'E';
    case 0xe0:case 0xc0:*mark=GRAVE;return code==0xe0?'a':'A';
    case 0xe2:case 0xc2:*mark=CIRCUMFLEX;return code==0xe2?'a':'A';
    case 0xe4:case 0xc4:*mark=DIAERESIS;return code==0xe4?'a':'A';
    case 0xf9:case 0xd9:*mark=GRAVE;return code==0xf9?'u':'U';
    case 0xfb:case 0xdb:*mark=CIRCUMFLEX;return code==0xfb?'u':'U';
    case 0xfc:case 0xdc:*mark=DIAERESIS;return code==0xfc?'u':'U';
    case 0xee:case 0xce:*mark=CIRCUMFLEX;return code==0xee?'i':'I';
    case 0xef:case 0xcf:*mark=DIAERESIS;return code==0xef?'i':'I';
    case 0xf4:case 0xd4:*mark=CIRCUMFLEX;return code==0xf4?'o':'O';
    case 0xf6:case 0xd6:*mark=DIAERESIS;return code==0xf6?'o':'O';
    case 0xe7:case 0xc7:*mark=CEDILLA;return code==0xe7?'c':'C';
    default:return 0;
    }
}
bool pmkb_surface_glyph_supported(uint32_t code){
    if(code>=32 && code<=126)return true;
    Accent accent;
    if(accent_base(code,&accent))return true;
    switch(code){
    case 0x03c0:case 0x03a9:case 0x221a:case 0x00d7:
    case 0x00f7:case 0x00b0:case 0x2190:case 0x2192:
    case 0x00a0:case 0x0300:case 0x0301:case 0x0302:
    case 0x0308:return true;
    default:return false;
    }
}
/* A glyph uses a 5-column, 10-row bitmap; columns are vertical bitfields.
 * Ordinary ASCII occupies bits 2..8; accents occupy 0..1 or cedilla 9. */
static void glyph(uint32_t code,uint16_t out[5]){
    for(int i=0;i<5;i++)out[i]=0;
    if(code==0x00a0)return;
    if(code==0x03c0){ /* π */
        out[0]=1u<<2;
        out[1]=0x7fu<<2;
        out[2]=1u<<2;
        out[3]=0x7fu<<2;
        out[4]=1u<<2;
        return;
    }
    if(code==0x221a){ /* √ */
        out[0]=1u<<6;out[1]=1u<<7;out[2]=1u<<8;
        out[3]=(1u<<7)|(1u<<6)|(1u<<5)|(1u<<4);
        out[4]=(1u<<2)|(1u<<3);
        return;
    }
    if(code==0x00d7||code==0x00f7){ /* ×, ÷ */
        for(int i=0;i<5;i++)
            out[i]=code==0x00d7 ?
                (uint16_t)((1u<<(i+2))|(1u<<(6-i))) :
                (uint16_t)((1u<<4)|(i==2?((1u<<2)|(1u<<6)):0u));
        return;
    }
    if(code==0x03a9){ /* Ω */
        const uint16_t omega[5]={0x1e0,0x104,0x104,0x104,0x1e0};
        memcpy(out,omega,sizeof(omega));return;
    }
    if(code==0x2190||code==0x2192){
        const uint16_t arrow[5]={0x10,0x38,0x54,0x10,0x10};
        for(int i=0;i<5;i++)
            out[i]=arrow[code==0x2190?i:4-i]<<2;
        return;
    }
    if(code==0x00b0){
        out[1]=0x3;out[2]=0x5;out[3]=0x3;return;
    }
    Accent mark=NO_ACCENT;
    char base=accent_base(code,&mark);
    if(!base)base=code<=127?(char)code:'?';
    for(int i=0;i<5;i++)out[i]=(uint16_t)ascii_column(base,i)<<2;
    if(mark==ACUTE){out[2]|=1u<<1;out[3]|=1u<<0;}
    else if(mark==GRAVE){out[1]|=1u<<0;out[2]|=1u<<1;}
    else if(mark==CIRCUMFLEX){
        out[1]|=1u<<1;out[2]|=1u<<0;out[3]|=1u<<1;
    }else if(mark==DIAERESIS){
        out[1]|=1u<<0;out[3]|=1u<<0;
    }else if(mark==CEDILLA){
        out[2]|=1u<<9;out[1]|=1u<<8;
    }
}
static uint32_t next_utf8(const unsigned char **reader){
    const unsigned char *p=*reader;
    if(!*p)return 0;
    uint32_t value;int length=1;
    if(p[0]<0x80){value=p[0];}
    else if(p[0]>=0xc2&&p[0]<=0xdf){value=p[0]&31u;length=2;}
    else if(p[0]>=0xe0&&p[0]<=0xef){value=p[0]&15u;length=3;}
    else if(p[0]>=0xf0&&p[0]<=0xf4){value=p[0]&7u;length=4;}
    else {(*reader)++;return '?';}
    for(int i=1;i<length;i++){
        if(!p[i]||(p[i]&0xc0)!=0x80){(*reader)++;return '?';}
        value=(value<<6)|(p[i]&63u);
    }
    *reader+=length;
    if((length==2&&value<128)||(length==3&&value<2048)||
       (length==4&&value<65536)||value>0x10ffff||
       (value>=0xd800&&value<=0xdfff))return '?';
    return value;
}
static void paint(PMKBSurface *s,int x,int y,uint16_t bits[5],
                  uint8_t shade,int scale,int max_x,int max_y){
    for(int cx=0;cx<5;cx++){
        for(int cy=0;cy<10;cy++){
            if(((bits[cx]>>cy)&1u)!=0){
                int px=x+cx*scale,py=y+cy*scale;
                if(px+scale<=max_x&&py+scale<=max_y)
                    pmkb_surface_rect(s,(PMKBRect){px,py,scale,scale},shade);
            }
        }
    }
}
void pmkb_surface_text_box(PMKBSurface *s,int x,int y,const char *utf8,
                            uint8_t shade,int max_width,int max_height){
    if(!s||!s->gray||!utf8||max_width<10||max_height<20)return;
    int scale=s->width>=680?3:2;
    int advance=6*scale,line=12*scale,origin=x;
    int max_x=x+max_width,max_y=y+max_height;
    const unsigned char *p=(const unsigned char*)utf8;
    while(*p){
        uint32_t code=next_utf8(&p);
        if(code=='\n'){
            x=origin;y+=line;
            if(y+10*scale>max_y)break;
            continue;
        }
        /* Decomposed French accents modify the preceding glyph without
         * consuming an extra character cell. */
        if(code>=0x0300 && code<=0x0308 &&
           (code==0x0300||code==0x0301||code==0x0302||code==0x0308)){
            uint16_t combining[5]={0};
            if(code==0x0301){combining[2]=2;combining[3]=1;}
            if(code==0x0300){combining[1]=1;combining[2]=2;}
            if(code==0x0302){combining[1]=2;combining[2]=1;combining[3]=2;}
            if(code==0x0308){combining[1]=1;combining[3]=1;}
            if(x>origin)
                paint(s,x-advance,y,combining,shade,scale,max_x,max_y);
            continue;
        }
        if(x+5*scale>max_x){x=origin;y+=line;}
        if(y+10*scale>max_y)break;
        uint16_t rows[5];
        glyph(code,rows);
        paint(s,x,y,rows,shade,scale,max_x,max_y);
        x+=advance;
    }
}
void pmkb_surface_text(PMKBSurface *s,int x,int y,const char *utf8,
                       uint8_t shade,int max_width){
    if(!s)return;
    pmkb_surface_text_box(s,x,y,utf8,shade,max_width,s->height-y);
}
