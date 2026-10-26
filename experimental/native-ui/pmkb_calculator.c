#include "pmkb_calculator.h"
#include <math.h>
#include <stdio.h>
#include <string.h>

/* Token-limited Pratt parser. Never execute strings as code.
 * Number conversion is decimal-point/locale independent. */
typedef enum {
    END, NUM, NAME, LP, RP, PLUS, MINUS, MUL, DIV, POWER, PERCENT
} Kind;
typedef struct { Kind kind; double value; char name[8]; } Token;
typedef struct {
    Token items[PMKB_CALC_MAX_TOKENS+1];
    size_t count, current;
    PMKBCalcStatus error;
    bool degrees;
    double ans;
} Parser;

static bool space(unsigned char c){
    return c==' '||c=='\t'||c=='\n'||c=='\r';
}
static bool digit(unsigned char c){return c>='0'&&c<='9';}
static bool letter(unsigned char c){
    return (c>='a'&&c<='z')||(c>='A'&&c<='Z');
}
static bool op(Parser *p, Kind kind, double value, const char *name){
    if(p->count>=PMKB_CALC_MAX_TOKENS){
        p->error=PMKB_CALC_LIMIT;return false;
    }
    Token *t=&p->items[p->count++];
    t->kind=kind;t->value=value;t->name[0]=0;
    if(name){
        size_t n=strlen(name);
        if(n>=sizeof(t->name)){p->error=PMKB_CALC_SYNTAX;return false;}
        memcpy(t->name,name,n+1);
    }
    return true;
}
/* Scan up to 16 significant decimal digits; track skipped low digits in
 * base-10 exponent rather than accumulating into an overflowing integer. */
static bool scan_number(const char *s,size_t length,size_t *cursor,
                        double *result,PMKBCalcStatus *error){
    size_t i=*cursor;
    unsigned long long mantissa=0;
    int significant=0,after_dot=0,skipped=0,explicit_exp=0;
    bool dot=false,seen=false;
    while(i<length && (digit((unsigned char)s[i])||s[i]=='.')){
        if(s[i]=='.'){
            if(dot)break;
            dot=true;i++;continue;
        }
        unsigned d=(unsigned)(s[i]-'0');
        seen=true;
        if(dot)after_dot++;
        if(significant||d){
            if(significant<16){
                mantissa=mantissa*10u+d;
                significant++;
            }else skipped++;
        }
        i++;
    }
    if(!seen){*error=PMKB_CALC_SYNTAX;return false;}
    if(i<length && (s[i]=='e'||s[i]=='E')){
        size_t next=i+1;
        bool negative=false;
        if(next<length&&(s[next]=='+'||s[next]=='-')){
            negative=(s[next]=='-');next++;
        }
        if(next<length && digit((unsigned char)s[next])){
            i=next;
            while(i<length && digit((unsigned char)s[i])){
                if(explicit_exp>2000){*error=PMKB_CALC_RANGE;return false;}
                explicit_exp=explicit_exp*10+(s[i]-'0');i++;
            }
            if(negative)explicit_exp=-explicit_exp;
        }
    }
    *cursor=i;
    if(mantissa==0){*result=0;return true;}
    int exponent=explicit_exp-after_dot+skipped+significant-1;
    if(exponent>308||exponent< -324){
        *error=PMKB_CALC_RANGE;return false;
    }
    double normalized=(double)mantissa/pow(10.0,(double)(significant-1));
    double value=normalized*pow(10.0,(double)exponent);
    if(!isfinite(value)||value==0){
        *error=PMKB_CALC_RANGE;return false;
    }
    *result=value;
    return true;
}
static void tokenize(Parser *p,const char *expression){
    if(!expression){p->error=PMKB_CALC_ARGUMENT;return;}
    size_t n=0;
    while(n<=PMKB_CALC_MAX_BYTES&&expression[n])n++;
    if(!n){p->error=PMKB_CALC_SYNTAX;return;}
    if(n>PMKB_CALC_MAX_BYTES){p->error=PMKB_CALC_LIMIT;return;}
    size_t i=0,units=0;
    while(i<n && p->error==PMKB_CALC_OK){
        unsigned char c=(unsigned char)expression[i];
        if(space(c)){i++;continue;}
        if(digit(c)||c=='.'){
            size_t before=i;
            double value=0;
            if(!scan_number(expression,n,&i,&value,&p->error))break;
            if(!op(p,NUM,value,NULL))break;
            units+=i-before;
            if(units>PMKB_CALC_MAX_UNITS)p->error=PMKB_CALC_LIMIT;
            continue;
        }
        if(letter(c)){
            char name[8];size_t j=0;
            while(i<n&&letter((unsigned char)expression[i])){
                if(j+1>=sizeof(name)){p->error=PMKB_CALC_SYNTAX;return;}
                unsigned char letter_case=(unsigned char)expression[i++];
                name[j++]=(char)(letter_case>='A'&&letter_case<='Z'?
                    letter_case+('a'-'A'):letter_case);
            }
            name[j]=0;
            if(!op(p,NAME,0,name))break;
            units+=j;continue;
        }
        /* Unicode tokens accepted in the browser prototype. */
        if(i+1<n && c==0xcf && (unsigned char)expression[i+1]==0x80){
            if(!op(p,NAME,0,"pi"))break;
            i+=2;units++;continue;
        }
        if(i+2<n && c==0xe2 &&
           (unsigned char)expression[i+1]==0x88 &&
           (unsigned char)expression[i+2]==0x9a){
            if(!op(p,NAME,0,"sqrt"))break;
            i+=3;units++;continue;
        }
        Kind kind=END;
        switch(c){
        case '(':kind=LP;break;
        case ')':kind=RP;break;
        case '+':kind=PLUS;break;
        case '-':kind=MINUS;break;
        case '*':kind=MUL;break;
        case '/':kind=DIV;break;
        case '^':kind=POWER;break;
        case '%':kind=PERCENT;break;
        default:break;
        }
        size_t consumed=1;
        if(i+1<n && c==0xc3 && (unsigned char)expression[i+1]==0x97){
            kind=MUL;consumed=2;
        }else if(i+1<n && c==0xc3 && (unsigned char)expression[i+1]==0xb7){
            kind=DIV;consumed=2;
        }else if(i+2<n && c==0xe2 &&
                 (unsigned char)expression[i+1]==0x88 &&
                 (unsigned char)expression[i+2]==0x92){
            kind=MINUS;consumed=3;
        }
        if(kind==END){p->error=PMKB_CALC_SYNTAX;break;}
        if(!op(p,kind,0,NULL))break;
        i+=consumed;units++;
        if(units>PMKB_CALC_MAX_UNITS){
            p->error=PMKB_CALC_LIMIT;break;
        }
    }
    if(p->error==PMKB_CALC_OK){
        p->items[p->count]=(Token){.kind=END,.value=0,.name={0}};
    }
}
static Kind peek(Parser *p){
    return p->items[p->current].kind;
}
static Token take(Parser *p){
    Token t=p->items[p->current];
    if(t.kind!=END)p->current++;
    return t;
}
static double fail(Parser *p,PMKBCalcStatus code){
    if(p->error==PMKB_CALC_OK)p->error=code;
    return 0;
}
static double checked(Parser *p,double value){
    if(!isfinite(value))return fail(p,PMKB_CALC_RANGE);
    return value;
}
static double function_value(Parser *p,const char *name,double value){
    const double pi=acos(-1.0);
    double radians=p->degrees?value*pi/180.0:value;
    if(strcmp(name,"sin")==0)return checked(p,sin(radians));
    if(strcmp(name,"cos")==0)return checked(p,cos(radians));
    if(strcmp(name,"tan")==0){
        if(!isfinite(radians))return fail(p,PMKB_CALC_RANGE);
        if(fabs(cos(radians))<1e-12)return fail(p,PMKB_CALC_DOMAIN);
        return checked(p,tan(radians));
    }
    if(strcmp(name,"asin")==0||strcmp(name,"acos")==0){
        if(value< -1.0 || value>1.0)return fail(p,PMKB_CALC_DOMAIN);
        double r=strcmp(name,"asin")==0?asin(value):acos(value);
        return checked(p,p->degrees?r*180.0/pi:r);
    }
    if(strcmp(name,"atan")==0){
        double r=atan(value);
        return checked(p,p->degrees?r*180.0/pi:r);
    }
    if(strcmp(name,"ln")==0){
        if(value<=0)return fail(p,PMKB_CALC_DOMAIN);
        return checked(p,log(value));
    }
    if(strcmp(name,"log")==0){
        if(value<=0)return fail(p,PMKB_CALC_DOMAIN);
        return checked(p,log10(value));
    }
    if(strcmp(name,"sqrt")==0){
        if(value<0)return fail(p,PMKB_CALC_DOMAIN);
        return checked(p,sqrt(value));
    }
    if(strcmp(name,"abs")==0)return checked(p,fabs(value));
    return fail(p,PMKB_CALC_SYNTAX);
}
static double parse(Parser *p,int min_binding,unsigned depth){
    if(depth>PMKB_CALC_MAX_DEPTH)return fail(p,PMKB_CALC_LIMIT);
    if(p->error!=PMKB_CALC_OK)return 0;
    Token token=take(p);
    double left=0;
    if(token.kind==NUM)left=token.value;
    else if(token.kind==LP){
        left=parse(p,0,depth+1);
        if(peek(p)!=RP)return fail(p,PMKB_CALC_SYNTAX);
        (void)take(p);
    }else if(token.kind==PLUS||token.kind==MINUS){
        left=parse(p,35,depth+1);
        if(token.kind==MINUS)left=-left;
    }else if(token.kind==NAME){
        if(strcmp(token.name,"pi")==0)left=acos(-1.0);
        else if(strcmp(token.name,"e")==0)left=exp(1.0);
        else if(strcmp(token.name,"ans")==0)left=p->ans;
        else {
            if(peek(p)!=LP)return fail(p,PMKB_CALC_SYNTAX);
            (void)take(p);
            double arg=parse(p,0,depth+1);
            if(peek(p)!=RP)return fail(p,PMKB_CALC_SYNTAX);
            (void)take(p);
            if(p->error!=PMKB_CALC_OK)return 0;
            left=function_value(p,token.name,arg);
        }
    }else return fail(p,PMKB_CALC_SYNTAX);
    if(p->error!=PMKB_CALC_OK)return 0;
    left=checked(p,left);
    while(p->error==PMKB_CALC_OK){
        Kind kind=peek(p);
        if(kind==PERCENT){
            if(45<min_binding)break;
            (void)take(p);
            left=checked(p,left/100.0);
            continue;
        }
        int binding=0,right_binding=0;
        if(kind==PLUS||kind==MINUS){binding=10;right_binding=11;}
        else if(kind==MUL||kind==DIV){binding=20;right_binding=21;}
        else if(kind==POWER){binding=40;right_binding=40;}
        else break;
        if(binding<min_binding)break;
        (void)take(p);
        double right=parse(p,right_binding,depth+1);
        if(p->error!=PMKB_CALC_OK)return 0;
        if(kind==PLUS)left=checked(p,left+right);
        else if(kind==MINUS)left=checked(p,left-right);
        else if(kind==MUL)left=checked(p,left*right);
        else if(kind==DIV){
            if(right==0)return fail(p,PMKB_CALC_DIV_ZERO);
            left=checked(p,left/right);
        }else{
            if(left==0&&right<0)return fail(p,PMKB_CALC_DIV_ZERO);
            if(left<0&&right!=floor(right))return fail(p,PMKB_CALC_DOMAIN);
            left=checked(p,pow(left,right));
        }
    }
    return left;
}
PMKBCalcStatus pmkb_calc_evaluate(const char *expression,bool degrees,
                                   double ans,double *result){
    if(!result||!expression||!isfinite(ans))return PMKB_CALC_ARGUMENT;
    Parser p={0};
    p.error=PMKB_CALC_OK;p.degrees=degrees;p.ans=ans;
    tokenize(&p,expression);
    if(p.error!=PMKB_CALC_OK)return p.error;
    double value=parse(&p,0,0);
    if(p.error!=PMKB_CALC_OK)return p.error;
    if(peek(&p)!=END)return PMKB_CALC_SYNTAX;
    if(!isfinite(value))return PMKB_CALC_RANGE;
    *result=(value==0.0)?0.0:value;
    return PMKB_CALC_OK;
}
bool pmkb_calc_format(double value,char *buffer,size_t size){
    if(!buffer||size<24||!isfinite(value))return false;
    if(value==0)value=0; /* normalize IEEE -0 */
    int n=snprintf(buffer,size,"%.12g",value);
    if(n<0||(size_t)n>=size)return false;
    /* Decimal point must not depend on the user's host locale. */
    for(size_t i=0;i<(size_t)n;i++)
        if(buffer[i]==',')buffer[i]='.';
    return true;
}
const char *pmkb_calc_error(PMKBCalcStatus error){
    switch(error){
    case PMKB_CALC_OK:return "";
    case PMKB_CALC_SYNTAX:return "Expression incorrecte";
    case PMKB_CALC_DOMAIN:return "Domaine mathematique";
    case PMKB_CALC_DIV_ZERO:return "Division par zero";
    case PMKB_CALC_RANGE:return "Resultat hors limites";
    case PMKB_CALC_LIMIT:return "Expression trop complexe";
    default:return "Parametres invalides";
    }
}
