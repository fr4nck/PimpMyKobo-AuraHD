#include "pmkb_ui.h"
#include <ctype.h>
#include <stdlib.h>
#include <string.h>

static void mark(PMKBSurface *s,int x,int y,int w,int h){
    if(w<=0||h<=0)return;
    if(!s->has_dirty){s->dirty=(PMKBRect){x,y,w,h};s->has_dirty=true;return;}
    int left=s->dirty.x<x?s->dirty.x:x;
    int top=s->dirty.y<y?s->dirty.y:y;
    int right=(s->dirty.x+s->dirty.w)>(x+w)?
              (s->dirty.x+s->dirty.w):(x+w);
    int bottom=(s->dirty.y+s->dirty.h)>(y+h)?
               (s->dirty.y+s->dirty.h):(y+h);
    s->dirty=(PMKBRect){left,top,right-left,bottom-top};
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
    s->changed_pixels=0;return true;
}
/* Host diagnostic 5x7 bitmap glyphs, NOT a production French font renderer.
 * LVGL adapter must eventually provide glyphs, shaping and e-ink submission. */
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
static uint8_t column(char c,int col){
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
    return col==0||col==4?0x7f:0x41;
}
void pmkb_surface_text(PMKBSurface *s,int x,int y,const char *utf8,
                       uint8_t shade,int max_width){
    if(!s||!s->gray||!utf8||max_width<5)return;
    int scale=s->width>=680?3:2;
    int advance=6*scale,origin=x,limit=x+max_width;
    for(const unsigned char *p=(const unsigned char*)utf8;*p;p++){
        if(*p=='\n'){x=origin;y+=9*scale;continue;}
        if(x+5*scale>limit){x=origin;y+=9*scale;}
        if(y>=s->height-8*scale)break;
        if(*p>=128){ /* one placeholder per Unicode codepoint in host mock */
            if((*p&0xc0u)==0x80u)continue;
        }
        char c=*p>=128?'?':(char)*p;
        for(int cx=0;cx<5;cx++){
            uint8_t bits=column(c,cx);
            for(int cy=0;cy<7;cy++){
                if((bits>>cy)&1u){
                    pmkb_surface_rect(s,(PMKBRect){x+cx*scale,y+cy*scale,scale,scale},shade);
                }
            }
        }
        x+=advance;
    }
}
