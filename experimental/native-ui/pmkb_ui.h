/* PMKB-UI V0: portable native APIs, no KOReader/Nickel/LVGL dependency. */
#ifndef PMKB_UI_H
#define PMKB_UI_H
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#define PMKB_NOTE_LIMIT 100u
#define PMKB_TITLE_LIMIT 100u       /* UTF-16 code units, matching JS Notes */
#define PMKB_BODY_LIMIT 120000u
#define PMKB_JSON_LIMIT 3000000u
#define PMKB_TOUCH_MIN 44
#define PMKB_KB_ROWS 7
#define PMKB_KB_COLS 6

typedef enum {
    PMKB_OK=0, PMKB_INVALID=-1, PMKB_LIMIT=-2, PMKB_MEMORY=-3,
    PMKB_NOT_FOUND=-4, PMKB_NO_CHANGE=-5
} PMKBStatus;

/* Cursors/selections are UTF-8 byte offsets at valid codepoint boundaries. */
typedef struct {
    char *data;
    size_t bytes, anchor, cursor, max_utf16;
} PMKBText;
PMKBStatus pmkb_utf8_measure(const char *s, size_t bytes, size_t *utf16);
PMKBStatus pmkb_text_init(PMKBText *t, size_t max_utf16, const char *initial);
void pmkb_text_free(PMKBText *t);
PMKBStatus pmkb_text_set(PMKBText *t, const char *value);
PMKBStatus pmkb_text_select(PMKBText *t, size_t anchor, size_t cursor);
PMKBStatus pmkb_text_insert(PMKBText *t, const char *utf8);
PMKBStatus pmkb_text_backspace(PMKBText *t);
PMKBStatus pmkb_text_move(PMKBText *t, int direction);
size_t pmkb_text_utf16_length(const PMKBText *t);

typedef enum { PMKB_KB_AZERTY, PMKB_KB_NUMERIC, PMKB_KB_SYMBOLS } PMKBKeyboardPage;
typedef enum {
    PMKB_KEY_INSERT, PMKB_KEY_SHIFT, PMKB_KEY_MODE, PMKB_KEY_SPACE,
    PMKB_KEY_BACKSPACE, PMKB_KEY_ENTER, PMKB_KEY_LEFT,
    PMKB_KEY_RIGHT, PMKB_KEY_HIDE
} PMKBKeyAction;
typedef struct {
    PMKBKeyAction action;
    const char *label;              /* UTF-8 */
    const char *insert;             /* UTF-8, never user-executable */
    int span;
} PMKBKey;
typedef struct {
    PMKBKeyboardPage page;
    bool shifted, visible;
} PMKBKeyboard;
void pmkb_keyboard_open(PMKBKeyboard *kb, PMKBKeyboardPage page);
void pmkb_keyboard_close(PMKBKeyboard *kb);
PMKBKey pmkb_keyboard_key(const PMKBKeyboard *kb, int row, int col);
PMKBStatus pmkb_keyboard_press(PMKBKeyboard *kb, PMKBText *target,
                                PMKBKey key, bool multiline);

typedef struct {
    char id[24], created[25], updated[25];
    PMKBText title, body;
} PMKBNote;
typedef struct {
    PMKBNote *items[PMKB_NOTE_LIMIT]; /* allocated on demand, not 12 MB upfront */
    size_t count;
    unsigned next_id;
} PMKBNotebook;
bool pmkb_notes_valid_utc(const char *utc);
void pmkb_notebook_init(PMKBNotebook *book);
void pmkb_notebook_free(PMKBNotebook *book);
PMKBStatus pmkb_notebook_new(PMKBNotebook *book, const char *utc,
                              size_t *index);
PMKBStatus pmkb_notebook_find(const PMKBNotebook *book,
                               const char *id, size_t *index);
PMKBStatus pmkb_notebook_export_json(const PMKBNotebook *book,
                                     char **json, size_t *length);

typedef struct { int x,y,w,h; } PMKBRect;
typedef struct {
    int width,height;
    uint8_t *gray;                /* one 8-bit grayscale buffer, host-only */
    PMKBRect dirty;               /* union of changed pixels */
    bool has_dirty;
    size_t changed_pixels;
} PMKBSurface;
PMKBStatus pmkb_surface_init(PMKBSurface *s, int width, int height);
void pmkb_surface_free(PMKBSurface *s);
void pmkb_surface_rect(PMKBSurface *s, PMKBRect rect, uint8_t shade);
void pmkb_surface_text(PMKBSurface *s, int x, int y,
                       const char *utf8, uint8_t shade, int max_width);
bool pmkb_surface_take_dirty(PMKBSurface *s, PMKBRect *out);

typedef enum { PMKB_VIEW_LIST, PMKB_VIEW_EDITOR } PMKBView;
typedef enum { PMKB_FOCUS_TITLE, PMKB_FOCUS_BODY } PMKBFocus;
typedef enum {
    PMKB_EVENT_TAP, PMKB_EVENT_TEXT, PMKB_EVENT_BACKSPACE,
    PMKB_EVENT_LEFT, PMKB_EVENT_RIGHT, PMKB_EVENT_ENTER,
    PMKB_EVENT_TOGGLE_KEYBOARD, PMKB_EVENT_SHOW_LIST
} PMKBEventKind;
typedef struct {
    PMKBEventKind kind;
    int x,y;                     /* for TAP: device-independent logical coords */
    const char *text;            /* for TEXT: UTF-8, not a keycode */
} PMKBEvent;
typedef struct {
    PMKBNotebook notebook;
    PMKBSurface screen;
    PMKBKeyboard keyboard;
    PMKBView view;
    PMKBFocus focus;
    size_t selected;
    bool initial_drawn;
    unsigned render_calls;
} PMKBUI;
PMKBStatus pmkb_ui_init(PMKBUI *ui, int width, int height);
void pmkb_ui_free(PMKBUI *ui);
PMKBStatus pmkb_ui_new_note(PMKBUI *ui, const char *utc);
PMKBStatus pmkb_ui_open_note(PMKBUI *ui, size_t index);
void pmkb_ui_show_list(PMKBUI *ui);
PMKBStatus pmkb_ui_event(PMKBUI *ui, PMKBEvent event, const char *utc);
void pmkb_ui_draw(PMKBUI *ui);

/* Backend adapters intentionally remain outside this portable core:
 * PMKB-HAL must later translate evdev, MXCFB update completion and power. */
#endif
