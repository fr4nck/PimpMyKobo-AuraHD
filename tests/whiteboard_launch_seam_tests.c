#include "pmkb_whiteboard_launch_seam.h"
#include <stdio.h>
static unsigned checks,failures;
#define CHECK(x) do {++checks;if(!(x)){++failures;fprintf(stderr,"SEAM FAIL line %u: %s\n",(unsigned)__LINE__,#x);}}while(0)
int main(void) {
 PMKBWhiteboardSession s={0};PMKBRect dirty;
 CHECK(pmkb_wb_session_screen(&s)==NULL);
 CHECK(pmkb_wb_session_close(&s,false)==PMKB_NO_CHANGE);
 CHECK(pmkb_wb_session_open(&s,320,480)==PMKB_OK);
 CHECK(pmkb_wb_session_open(&s,320,480)==PMKB_INVALID);
 CHECK(pmkb_wb_session_screen(&s)!=NULL);
 CHECK(pmkb_surface_take_dirty(pmkb_wb_session_screen(&s),&dirty));
 CHECK(pmkb_wb_session_touch(&s,PMKB_WB_TOUCH_DOWN,12,12)==PMKB_WB_OK);
 CHECK(pmkb_wb_session_close(&s,false)==PMKB_UNSAVED);
 CHECK(s.open && s.app.board->in_stroke);
 CHECK(pmkb_wb_session_touch(&s,PMKB_WB_TOUCH_UP,20,12)==PMKB_WB_OK);
 CHECK(pmkb_wb_session_close(&s,false)==PMKB_UNSAVED);
 CHECK(s.open && s.app.board->visible==1u);
 CHECK(pmkb_wb_session_close(&s,true)==PMKB_OK);
 CHECK(!s.open && s.app.board==NULL && s.app.screen.gray==NULL);
 CHECK(pmkb_wb_session_touch(&s,PMKB_WB_TOUCH_DOWN,12,12)==PMKB_WB_INVALID);
 CHECK(pmkb_wb_session_open(&s,320,480)==PMKB_OK);
 CHECK(s.app.board->total==0u);
 CHECK(pmkb_wb_session_close(&s,false)==PMKB_OK);
 CHECK(pmkb_wb_session_open(&s,100,100)==PMKB_INVALID);
 CHECK(!s.open && s.app.board==NULL);
 if(failures)return 1;
 printf("WHITEBOARD LAUNCH SEAM: %u assertions PASS, 0 FAIL\n",checks);
 return 0;
}
