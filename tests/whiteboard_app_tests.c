#include "pmkb_whiteboard_app.h"
#include <stdio.h>
static unsigned checks,fails;
#define CHECK(x) do {++checks;if(!(x)){++fails;fprintf(stderr,"APP FAIL %u: %s\n",(unsigned)__LINE__,#x);}}while(0)
int main(void) {
 PMKBWhiteboardApp app={0};PMKBRect dirty;
 CHECK(pmkb_wb_app_init(&app,320,480)==PMKB_OK);
 CHECK(app.board!=NULL && app.screen.gray!=NULL);
 CHECK(pmkb_surface_take_dirty(&app.screen,&dirty));
 CHECK(pmkb_wb_app_touch(&app,PMKB_WB_TOUCH_DOWN,10,10)==PMKB_WB_OK);
 CHECK(pmkb_wb_app_touch(&app,PMKB_WB_TOUCH_MOVE,20,10)==PMKB_WB_OK);
 CHECK(pmkb_wb_app_touch(&app,PMKB_WB_TOUCH_UP,30,10)==PMKB_WB_OK);
 CHECK(app.board->visible==1u && app.screen.has_dirty);
 CHECK(pmkb_wb_app_undo(&app)==PMKB_WB_OK);
 CHECK(app.board->visible==0u);
 CHECK(app.screen.gray[(size_t)10*320u+20u]==255);
 CHECK(pmkb_wb_app_redo(&app)==PMKB_WB_OK);
 CHECK(app.screen.gray[(size_t)10*320u+20u]==0);
 CHECK(pmkb_wb_app_clear(&app)==PMKB_WB_OK);
 CHECK(app.board->visible==0u && app.board->total==0u);
 CHECK(app.screen.gray[(size_t)10*320u+20u]==255);
 pmkb_wb_app_free(&app);
 CHECK(app.board==NULL && app.screen.gray==NULL);
 pmkb_wb_app_free(&app);
 CHECK(pmkb_wb_app_init(&app,100,100)==PMKB_INVALID);
 CHECK(app.board==NULL);
 if(fails)return 1;
 printf("WHITEBOARD APP: %u assertions PASS, 0 FAIL\n",checks);
 return 0;
}
