/* L07-J: reproducible 320x480 grayscale PGM from the real C11 model.
 * Synthetic fixture only. Writes to stdout, never to the Kobo or P3. */
#include "pmkb_whiteboard_touch.h"
#include <stdio.h>
#ifdef _WIN32
#include <fcntl.h>
#include <io.h>
#endif
int main(void) {
#ifdef _WIN32
    if (_setmode(_fileno(stdout), _O_BINARY) == -1) return 5;
#endif
    PMKBWBModel board={0};
    PMKBSurface surface={0};
    PMKBRect dirty;
    if(pmkb_wb_init(&board,320,480)!=PMKB_WB_OK ||
       pmkb_surface_init(&surface,320,480)!=PMKB_OK)return 1;
    (void)pmkb_surface_take_dirty(&surface,&dirty);
    if(pmkb_wb_touch(&board,&surface,PMKB_WB_TOUCH_DOWN,20,20,0,3)!=PMKB_WB_OK ||
       pmkb_wb_touch_stream_move(&board,&surface,120,20)!=PMKB_WB_OK ||
       pmkb_wb_touch(&board,&surface,PMKB_WB_TOUCH_UP,120,130,0,3)!=PMKB_WB_OK ||
       pmkb_wb_touch(&board,&surface,PMKB_WB_TOUCH_DOWN,25,150,8,5)!=PMKB_WB_OK ||
       pmkb_wb_touch(&board,&surface,PMKB_WB_TOUCH_UP,170,150,8,5)!=PMKB_WB_OK) {
        pmkb_surface_free(&surface);return 2;
    }
    if(fprintf(stdout,"P5\n320 480\n255\n")<0 ||
       fwrite(surface.gray,1,320u*480u,stdout)!=320u*480u) {
        pmkb_surface_free(&surface);return 3;
    }
    pmkb_surface_free(&surface);
    return fflush(stdout)==0?0:4;
}
