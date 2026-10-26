/* PMKB L06-D6b: native Store surface + TRUE pinned PMKB backend.
 * Host-only dirty region and present contract, no hardware/EPDC writes. */
#include "pmkb_ui.h"
#include "pmkb_store_ui_preview.h"
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

static unsigned assertions, failures;
#define CHECK(x) do { ++assertions; if (!(x)) { ++failures; \
    fprintf(stderr, "STORE PRESENT FAIL line %u: %s\n", \
            (unsigned)__LINE__, #x); } } while (0)

typedef struct {
    PMKBSurface *surface;
    PMKBRect rectangles[4];
    unsigned calls;
    PMKBStatus failure;
    bool mutate_once;
    bool mutated;
} BackendProbe;

static bool contains(PMKBRect r, int x, int y) {
    return r.w > 0 && r.h > 0 && x >= r.x && y >= r.y &&
           x < r.x + r.w && y < r.y + r.h;
}
static PMKBStatus record_present(void *context, const uint8_t *gray,
                                  int width, int height, PMKBRect rect) {
    BackendProbe *probe = (BackendProbe *)context;
    CHECK(probe != NULL);
    if (!probe) return PMKB_INVALID;
    CHECK(probe->surface != NULL && gray == probe->surface->gray);
    CHECK(width == probe->surface->width && height == probe->surface->height);
    CHECK(rect.x >= 0 && rect.y >= 0 && rect.w > 0 && rect.h > 0);
    CHECK(rect.x + rect.w <= width && rect.y + rect.h <= height);
    if (probe->calls < 4) probe->rectangles[probe->calls] = rect;
    ++probe->calls;
    if (probe->failure != PMKB_OK) return probe->failure;
    if (probe->mutate_once && !probe->mutated) {
        probe->mutated = true;
        /* Callback writes back into the same buffer during presentation. */
        pmkb_surface_rect(probe->surface, (PMKBRect){0, 0, 3, 3}, 0);
    }
    return PMKB_OK;
}
static PMKBBackend backend_for(BackendProbe *probe) {
    PMKBBackend backend = {probe, record_present};
    return backend;
}
static PMKBStoreView catalog;
static void setup(unsigned n) {
    memset(&catalog, 0, sizeof(catalog));
    catalog.count = n;
    for (unsigned i = 0; i < n; ++i) {
        (void)snprintf(catalog.items[i].id, sizeof(catalog.items[i].id),
                       "org.pmkb.demo%02u", i);
        (void)snprintf(catalog.items[i].label, sizeof(catalog.items[i].label),
                       "Demo %02u", i);
        (void)strcpy(catalog.items[i].version, "0.1.0");
    }
}
static bool all_marked_pixels_covered(const PMKBSurface *surface,
                                     const BackendProbe *probe) {
    /* Surface began white. Every changed (non-white) pixel must be
     * covered by at least one region presented to the backend. */
    for (int y = 0; y < surface->height; ++y) {
        for (int x = 0; x < surface->width; ++x) {
            if (surface->gray[(size_t)y * (size_t)surface->width+(size_t)x]
                == 255) continue;
            bool covered = false;
            for (unsigned i = 0; i < probe->calls && i < 4; ++i)
                if (contains(probe->rectangles[i], x, y)) {
                    covered = true; break;
                }
            if (!covered) return false;
        }
    }
    return true;
}
static bool same_rect(PMKBRect a, PMKBRect b) {
    return a.x == b.x && a.y == b.y && a.w == b.w && a.h == b.h;
}
static void preview_present_success(int width, int height) {
    setup(7);
    PMKBSurface surface = {0};
    PMKBRect discarded;
    CHECK(pmkb_surface_init(&surface, width, height) == PMKB_OK);
    if (!surface.gray) return;
    CHECK(pmkb_surface_take_dirty(&surface, &discarded));
    PMKBStoreUIPreview preview;
    pmkb_store_ui_preview_init(&preview);
    CHECK(pmkb_store_ui_preview_enter(&preview, &surface)
          == PMKB_STORE_PAINT_OK);
    CHECK(pmkb_store_ui_preview_draw(&preview, &catalog, 0)
          == PMKB_STORE_PAINT_OK);
    CHECK(surface.has_dirty && surface.changed_pixels > 0);
    const PMKBRect before = surface.dirty;
    BackendProbe probe = {0}; probe.surface = &surface;
    PMKBBackend backend = backend_for(&probe);
    CHECK(pmkb_surface_present(&surface, &backend) == PMKB_OK);
    CHECK(probe.calls >= 1 && probe.calls <= 2);
    CHECK(all_marked_pixels_covered(&surface, &probe));
    CHECK(!surface.has_dirty && surface.changed_pixels == 0);
    CHECK(surface.dirty_island_count == 0);
    /* The public union is stable until successful acknowledgement. */
    CHECK(before.w > 0 && before.h > 0);

    const unsigned previous_calls = probe.calls;
    CHECK(pmkb_store_ui_preview_draw(&preview, &catalog, 0)
          == PMKB_STORE_PAINT_OK); /* cache hit: no dirty region */
    CHECK(!surface.has_dirty && surface.changed_pixels == 0);
    CHECK(pmkb_surface_present(&surface, &backend) == PMKB_NO_CHANGE);
    CHECK(probe.calls == previous_calls);

    /* Explicit external draw notification + full restore and present. */
    pmkb_surface_rect(&surface, (PMKBRect){0, 0, 3, 3}, 0);
    CHECK(surface.has_dirty);
    pmkb_store_ui_preview_external_draw(&preview);
    CHECK(pmkb_store_ui_preview_draw(&preview, &catalog, 0)
          == PMKB_STORE_PAINT_OK);
    CHECK(surface.gray[0] == 255 && surface.has_dirty);
    CHECK(pmkb_surface_present(&surface, &backend) == PMKB_OK);
    CHECK(!surface.has_dirty);
    pmkb_store_ui_preview_leave(&preview);
    pmkb_surface_free(&surface);
}
static void present_error_and_retry(void) {
    setup(2);
    PMKBSurface surface = {0};
    PMKBRect discarded;
    CHECK(pmkb_surface_init(&surface, 320, 480) == PMKB_OK);
    if (!surface.gray) return;
    CHECK(pmkb_surface_take_dirty(&surface, &discarded));
    PMKBStoreUIPreview preview;
    pmkb_store_ui_preview_init(&preview);
    CHECK(pmkb_store_ui_preview_enter(&preview, &surface)
          == PMKB_STORE_PAINT_OK);
    CHECK(pmkb_store_ui_preview_draw(&preview, &catalog, 0)
          == PMKB_STORE_PAINT_OK);
    const size_t changed = surface.changed_pixels;
    const PMKBRect dirty = surface.dirty;
    BackendProbe probe = {0};
    probe.surface = &surface;
    probe.failure = PMKB_MEMORY;
    PMKBBackend backend = backend_for(&probe);
    CHECK(pmkb_surface_present(&surface, &backend) == PMKB_MEMORY);
    CHECK(probe.calls == 1);
    CHECK(surface.has_dirty && surface.changed_pixels == changed);
    CHECK(same_rect(surface.dirty, dirty));
    CHECK(pmkb_surface_present(&surface, NULL) == PMKB_INVALID);
    CHECK(surface.has_dirty); /* invalid backend must not acknowledge */
    probe.failure = PMKB_OK;
    probe.calls = 0;
    CHECK(pmkb_surface_present(&surface, &backend) == PMKB_OK);
    CHECK(probe.calls >= 1 && probe.calls <= 2);
    CHECK(!surface.has_dirty && surface.changed_pixels == 0);
    pmkb_store_ui_preview_leave(&preview);
    pmkb_surface_free(&surface);
}
static void split_dirty_regions(void) {
    PMKBSurface surface = {0};
    PMKBRect discarded;
    CHECK(pmkb_surface_init(&surface, 320, 480) == PMKB_OK);
    if (!surface.gray) return;
    CHECK(pmkb_surface_take_dirty(&surface, &discarded));
    PMKBRect a = {7, 9, 12, 12}, b = {292, 445, 13, 12};
    pmkb_surface_rect(&surface, a, 0);
    pmkb_surface_rect(&surface, b, 0);
    CHECK(surface.dirty_island_count == 2);
    BackendProbe probe = {0};
    probe.surface = &surface;
    PMKBBackend backend = backend_for(&probe);
    CHECK(pmkb_surface_present(&surface, &backend) == PMKB_OK);
    CHECK(probe.calls == 2); /* two distant dirty islands -> two callbacks */
    CHECK(same_rect(probe.rectangles[0], a));
    CHECK(same_rect(probe.rectangles[1], b));
    CHECK(!surface.has_dirty && surface.dirty_island_count == 0);
    pmkb_surface_free(&surface);
}
static void reentrant_present_preserves_dirty(void) {
    setup(2);
    PMKBSurface surface = {0};
    PMKBRect discarded;
    CHECK(pmkb_surface_init(&surface, 320, 480) == PMKB_OK);
    if (!surface.gray) return;
    CHECK(pmkb_surface_take_dirty(&surface, &discarded));
    PMKBStoreUIPreview preview;
    pmkb_store_ui_preview_init(&preview);
    CHECK(pmkb_store_ui_preview_enter(&preview, &surface)
          == PMKB_STORE_PAINT_OK);
    CHECK(pmkb_store_ui_preview_draw(&preview, &catalog, 0)
          == PMKB_STORE_PAINT_OK);
    BackendProbe probe = {0};
    probe.surface = &surface; probe.mutate_once = true;
    PMKBBackend backend = backend_for(&probe);
    CHECK(pmkb_surface_present(&surface, &backend) == PMKB_OK);
    CHECK(probe.mutated);
    CHECK(surface.gray[0] == 0);
    CHECK(surface.has_dirty && surface.dirty_island_count == 1);
    CHECK(surface.changed_pixels > 0);
    probe.mutate_once = false; probe.calls = 0;
    CHECK(pmkb_surface_present(&surface, &backend) == PMKB_OK);
    CHECK(probe.calls == 1);
    CHECK(!surface.has_dirty);
    pmkb_store_ui_preview_external_draw(&preview);
    CHECK(pmkb_store_ui_preview_draw(&preview, &catalog, 0)
          == PMKB_STORE_PAINT_OK);
    CHECK(surface.gray[0] == 255 && surface.has_dirty);
    CHECK(pmkb_surface_present(&surface, &backend) == PMKB_OK);
    CHECK(!surface.has_dirty);
    pmkb_store_ui_preview_leave(&preview);
    pmkb_surface_free(&surface);
}
int main(void) {
    preview_present_success(320, 480);
    preview_present_success(1080, 1440);
    preview_present_success(1440, 1080);
    present_error_and_retry();
    split_dirty_regions();
    reentrant_present_preserves_dirty();
    if (failures) return 1;
    printf("PMKB REAL STORE PRESENT: %u assertions PASS, 0 FAIL\n", assertions);
    return 0;
}
