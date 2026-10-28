/* PMKB Store V0 L06-D2: bounded, passive C11 view model; no I/O. */
#ifndef PMKB_STORE_VIEW_H
#define PMKB_STORE_VIEW_H
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#define PMKB_STORE_VIEW_MAX_JSON 32768u
#define PMKB_STORE_VIEW_MAX_APPS 64u
#define PMKB_STORE_VIEW_MAX_PENDING 512u

typedef enum {
    PMKB_STORE_VIEW_OK=0,
    PMKB_STORE_VIEW_INVALID=-1,
    PMKB_STORE_VIEW_LIMIT=-2
} PMKBStoreViewStatus;

typedef struct {
    char id[121];
    char label[321];   /* 80 Unicode scalars, at most 4 UTF-8 bytes each */
    char version[25];
    bool network_declared;
    bool launchable;   /* invariant: always false */
} PMKBStoreViewItem;

typedef struct {
    unsigned count;
    unsigned cleanup_pending_count;
    PMKBStoreViewItem items[PMKB_STORE_VIEW_MAX_APPS];
} PMKBStoreView;

/* Accept only the canonical v1 JSON emitted by store_view_contract.py.
 * Input need not be NUL terminated. Rejects unknown fields/extra bytes.
 * Output is reset on failure. No malloc, filesystem, process or network. */
PMKBStoreViewStatus pmkb_store_view_parse(const uint8_t *json, size_t length,
                                          PMKBStoreView *out);
#endif
