# PMKB Store L06-D3: passive native page layout

`pmkb_store_page_build(view, width, height, page_index, &page)` builds one
**non-interactive**, fixed-capacity list page for a previously validated
`pmkb-store-view-v1` model. No screen is drawn. The result is geometry and
metadata only, ready for the future PMKB-UI rendering primitives.

Supported logical host profiles (the actual Aura HD needs hardware QA):

| Profile | Rows per page | Header | Footer | Row height |
| --- | ---: | ---: | ---: | ---: |
| 320x480 | 5 | 52 | 48 | 56 |
| 1080x1440 | 12 | 88 | 72 | 84 |
| 1440x1080 | 9 | 88 | 72 | 84 |

Each row references an index in `PMKBStoreView`, not a cloned string.
The source model must outlive the page. Each row has bounded title/version
rectangles within the row, 16-grayscale-compatible constants (0, 192, 240,
255), and a height of at least 44 pixels. `cleanup_pending_count` and
`page_count` are presented as **inert status numbers** only. No buttons,
touch callback, executable path, filesystem I/O, malloc, network access,
application install/uninstall, or app launch.

The module refuses unknown resolutions, page indexes outside the computed
range, invalid item data and `launchable=true`. An error resets the output.
It does not replace FBInk, PMKB-UI or any framebuffer driver. In particular,
**no actual text glyphs, partial refresh or EPDC operation** happen in D3.

Host tests: compile `pmkb_store_page.c` with `test_store_page.c` using an
existing C11 compiler; assertions verify geometry, bounds, pagination, empty
pages and refusal. The Python `test_store_page_c11.py` suite also compiles
with `pmkb_store_view.c` and passes canonical JSON from the real Python
`encode_store_view()` through the actual C11 reader to this layout module.
Without an installed C compiler the Python suite reports SKIP, never PASS.

Follow-up L06-D4: optional read-only draw bridge to existing PMKB-UI surface
primitives after checking PR #30/#31 isolation. Preserve Notes ADR-005,
the eight illustrations, FIRST BOOT and P2. The Store must remain non-runnable.
