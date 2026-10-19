/* PMKB-HAL V0 — portable input/E-Ink contracts, host-only.
 * Deliberately NO linux/ioctl.h, device access, kernel structs, or sysfs. */
#ifndef PMKB_HAL_H
#define PMKB_HAL_H
#include "pmkb_ui.h"

typedef enum {
    PMKB_ROT_0=0, PMKB_ROT_90=90, PMKB_ROT_180=180, PMKB_ROT_270=270
} PMKBRotation;
typedef struct {
    int width, height;
    int x_min, x_max, y_min, y_max; /* measured ABS_X / ABS_Y ranges */
    bool mirror_x, mirror_y;       /* explicit dragon profile, not guessed */
    PMKBRotation rotation;
    int tap_slop;                  /* logical pixels: movement cancellation */
} PMKBTouchConfig;
typedef struct {
    PMKBTouchConfig config;
    int raw_x, raw_y;
    int down_x, down_y;
    bool have_x, have_y, down, candidate;
    bool pending_button;
    int button_value;
    unsigned taps, drops;
} PMKBTouch;

/* Legacy Linux evdev numeric type/code values. EventN is NOT hardwired.
 * Only the safe, explicitly-supported single-touch subset is handled. */
enum {
    PMKB_EV_SYN=0, PMKB_EV_KEY=1, PMKB_EV_ABS=3,
    PMKB_SYN_REPORT=0, PMKB_SYN_DROPPED=3,
    PMKB_ABS_X=0, PMKB_ABS_Y=1,
    PMKB_BTN_TOUCH=330
};

PMKBStatus pmkb_touch_init(PMKBTouch *touch, PMKBTouchConfig config);
/* PMKB_OK only when a completed, small press-release gesture emitted TAP.
 * PMKB_NO_CHANGE otherwise; never emits motion or a duplicate tap. */
PMKBStatus pmkb_touch_feed(PMKBTouch *touch,int type,int code,int value,
                           PMKBEvent *event);

/* Transport callbacks have to be implemented by a separately qualified
 * physical backend, or by a fully synthetic test fixture.
 * copy : copy gray pixels for dirty into the framebuffer staging area
 * send : submit update with a unique nonzero marker
 * wait : report driver completion for that SAME marker, or failure
 * Nothing in this file picks an unverified MXCFB ABI or waveform. */
typedef enum {
    PMKB_EINK_UPDATE_PARTIAL=0,
    PMKB_EINK_UPDATE_FULL=1
} PMKBEinkUpdate;
typedef PMKBStatus (*PMKBEinkCopy)(void *context,
            const uint8_t *gray,int width,int height,PMKBRect dirty);
typedef PMKBStatus (*PMKBEinkSend)(void *context,
            PMKBRect dirty,uint32_t marker,PMKBEinkUpdate mode);
typedef PMKBStatus (*PMKBEinkWait)(void *context,uint32_t marker);
typedef struct {
    void *context;
    PMKBEinkCopy copy;
    PMKBEinkSend send;
    PMKBEinkWait wait;
} PMKBEinkOps;
typedef struct {
    PMKBEinkOps ops;
    int width,height;
    PMKBEinkUpdate mode;       /* explicit policy set by the caller */
    uint32_t sequence;
    bool in_flight;
    uint32_t pending_marker;
    PMKBRect pending_rect;
    uint64_t pending_digest;
    unsigned submitted,completed,wait_failures;
} PMKBEink;

PMKBStatus pmkb_eink_init(PMKBEink *eink,int width,int height,
                           PMKBEinkOps operations);
/* To connect to PMKBBackend, use PMKBBackend{ .present=pmkb_eink_present }.
 * The host holds mutable state so this interface is deliberately synchronous.
 * A failed wait keeps the same marker pending and prevents double-send.
 * If the surface changed meanwhile, a new region is submitted after the
 * outstanding marker completes; never acknowledge pixels not submitted. */
PMKBStatus pmkb_eink_present(void *context,const uint8_t *gray,
                             int width,int height,PMKBRect dirty);
PMKBStatus pmkb_eink_set_update(PMKBEink *eink,PMKBEinkUpdate mode);
#endif
