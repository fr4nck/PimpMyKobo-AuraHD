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
    bool discard_frame, await_release, multiple_contacts;
    int button_value;
    unsigned taps, drops;
} PMKBTouch;

/* Legacy Linux evdev numeric type/code values. EventN is NOT hardwired.
 * Only single-touch taps are decoded; two-finger gestures are cancelled. */
enum {
    PMKB_EV_SYN=0, PMKB_EV_KEY=1, PMKB_EV_ABS=3,
    PMKB_SYN_REPORT=0, PMKB_SYN_DROPPED=3,
    PMKB_ABS_X=0, PMKB_ABS_Y=1,
    PMKB_BTN_TOUCH=330, PMKB_BTN_TOOL_DOUBLETAP=333
};

PMKBStatus pmkb_touch_init(PMKBTouch *touch, PMKBTouchConfig config);
/* PMKB_OK only when a completed, small press-release gesture emitted TAP.
 * PMKB_NO_CHANGE otherwise; never emits motion or a duplicate tap.
 * SYN_DROPPED discards through the next SYN_REPORT, then waits for an
 * explicit clean BTN_TOUCH=0 frame. Two-finger gestures likewise require
 * all contacts released before another tap. No MT gesture is decoded.
 * A future evdev adapter must query EVIOCG* state after loss; this pure
 * decoder cannot do so and may conservatively discard an extra gesture. */
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

/* Power input policy (host-only, no GPIO/IRQ operations).
 * The future evdev adapter MUST classify the input source first:
 * KEY_F1 on an arbitrary keyboard is NOT proof of a Hall event.
 * PMKB_OK means forward to the existing power manager; it is never
 * evidence that suspend or wake was completed by the device. */
typedef enum {
    PMKB_POWER_COVER_CLOSED=0,
    PMKB_POWER_COVER_OPENED=1,
    PMKB_POWER_BUTTON_PRESSED=2,
    PMKB_POWER_BUTTON_RELEASED=3,
    PMKB_POWER_OTHER=4,
    PMKB_POWER_LIGHT_TOGGLE=5 /* Dedicated frontlight button, on release. */
} PMKBPowerEvent;
typedef struct {
    bool cover_enabled; /* false by default, opt-in only */
    bool cover_seen;
    bool cover_closed;
} PMKBPowerPolicy;
void pmkb_power_policy_init(PMKBPowerPolicy *policy);
PMKBStatus pmkb_power_policy_set_cover(PMKBPowerPolicy *policy,bool enabled);
/* Exact versioned configuration bytes; no read/write or settings path here.
 * length excludes a terminating NUL. Invalid imports do not mutate state. */
PMKBStatus pmkb_power_policy_export(const PMKBPowerPolicy *policy,
                                    char *data,size_t capacity,size_t *length);
PMKBStatus pmkb_power_policy_import(PMKBPowerPolicy *policy,
                                    const char *data,size_t length);
/* PMKB_NO_CHANGE = ignore, PMKB_OK = forward. Button events are never
 * suppressed. Repeated identical cover levels are coalesced. */
PMKBStatus pmkb_power_policy_filter(PMKBPowerPolicy *policy,PMKBPowerEvent event);


/* Historical NTX: TLE4913 yields KEY_F1 (customer UI) or KEY_H;
 * never infer the source from an event number or a keycode alone. */
enum { PMKB_KEY_H=35, PMKB_KEY_F1=59, PMKB_KEY_FL=90, PMKB_KEY_POWER=116 };
typedef enum {
    PMKB_POWER_SOURCE_UNQUALIFIED=0,
    PMKB_POWER_SOURCE_NTX_VERIFIED=1,
    PMKB_POWER_SOURCE_EXTERNAL=2
} PMKBPowerInputSource;
typedef struct {
    PMKBPowerPolicy *policy; /* Borrowed; caller owns its lifetime. */
    int cover_code;         /* Exactly one of KEY_F1 and KEY_H. */
    bool qualified,discard_frame,await_cover_release;
    bool light_pressed; /* Ignore stray/double releases; reset on SYN_DROPPED. */
} PMKBPowerEvdev;
/* Pure evdev translator. A future adapter must FIRST verify the actual
 * Netronix input source by identity and key capabilities; passing VERIFIED
 * is the caller's explicit promise, not verification performed here.
 * Failed reinitialization clears an earlier trusted binding. */
PMKBStatus pmkb_power_evdev_init(PMKBPowerEvdev *decoder,
        PMKBPowerPolicy *policy,PMKBPowerInputSource source,int cover_code);
/* KEY_FL=90 is a separate physical light button (GPIO_4_1 in the BSP).
 * Only its matched press -> release pair emits PMKB_POWER_LIGHT_TOGGLE.
 * The downstream frontlight handler owns the actual illumination command.
 * NO_CHANGE leaves output untouched. OK emits a semantic event for the
 * existing policy; no physical I/O, kernel wake manipulation or sleep.
 * SYN_DROPPED quarantines cover edges until a clean release is observed. */
PMKBStatus pmkb_power_evdev_feed(PMKBPowerEvdev *decoder,
        int type,int code,int value,PMKBPowerEvent *event);


/* Inventory of already discovered evdev devices. Both legacy NTX
 * gpio_keys and matrix-keypad paths can advertise the name "mxckpd".
 * BUS_HOST and KEY_F1/KEY_H are hints, never hardware authentication.
 * Older matrix drivers may not advertise KEY_POWER in their key bitmap.
 * The index is an array position, not an assumed /dev/input/eventN. */
enum { PMKB_BUS_HOST=0x19, PMKB_POWER_SCAN_MAX=32 };
typedef struct {
    const char *name;       /* NUL-terminated EVIOCGNAME supplied by caller */
    unsigned int bustype;  /* EVIOCGID, zero if not available */
    bool has_ev_key;
    bool has_key_f1,has_key_h,has_key_power;
} PMKBPowerInputInfo;
typedef enum {
    PMKB_POWER_PROBE_INVALID=0,
    PMKB_POWER_PROBE_NONE=1,
    PMKB_POWER_PROBE_CANDIDATE=2,  /* STILL UNQUALIFIED */
    PMKB_POWER_PROBE_AMBIGUOUS=3
} PMKBPowerProbeResult;
/* Never binds PMKBPowerEvdev and never outputs a cover_code.
 * Only an independently verified live Hall transition can establish which
 * code is actually emitted. The output index changes on CANDIDATE only. */
PMKBPowerProbeResult pmkb_power_probe_inputs(
        const PMKBPowerInputInfo *devices,size_t count,size_t *candidate_index);


/* Board-specific evidence gate for the preserved Aura HD N204 HWCONFIG v1.7:
 * bPCB=28 (E606C0), bPCB_Flags=1 (NO_KeyMatrix), bHallSensor=1.
 * The source branch used by this board is gpio_keys ("mxckpd"), which
 * advertises KEY_POWER, KEY_F1 and KEY_H via its key capability bitmap.
 * This signature is supplied by a caller; it is NOT measured here. */
enum { PMKB_AURA_HD_PCB=28, PMKB_AURA_HD_NO_KEYMATRIX=1 };
typedef struct {
    unsigned int pcb,pcb_flags,hall_sensor;
} PMKBPowerBoardSignature;
/* More selective than pmkb_power_probe_inputs for the *preserved* hardware
 * profile. CANDIDATE is still not authorization to bind/read evdev events.
 * A future read-only live qualification must establish the actual event
 * source, Hall key code and independent physical Power key.
 * Only writes the output index for one unambiguous candidate. */
PMKBPowerProbeResult pmkb_power_probe_aura_hd(
        const PMKBPowerInputInfo *devices,size_t count,
        PMKBPowerBoardSignature hw,size_t *candidate_index);

#endif
