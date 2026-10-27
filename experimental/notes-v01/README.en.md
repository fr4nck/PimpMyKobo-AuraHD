# PMKB Notes V0.1 — text and sketch (PC prototype)

**Status: standalone host-only prototype, not installed on the Kobo.** The first PMKB PDA app combines a full text note with an optional minimalist monochrome sketch palette. It neither depends on nor changes the launcher or FIRST BOOT.

## Implemented features

- Create, select, rename, search and delete notes, with confirmation before deletion.
- Offline UTF-8 text editor; explicit limits (100 notes and 120,000 characters per note).
- Optional **Sketch** tab for every note: pen, eraser, three line widths, undo/redo, confirmed clear action, touch/mouse Pointer Events.
- Editable stroke data preserved in JSON backup; separate PNG export for sharing flattened drawings.
- Autosave in browser-local storage when available, explicit Save button and storage status; entire notebook JSON export, single-note TXT export and validated JSON import with replacement confirmation.
- No account, network, backend, background service, third-party dependencies or hardware operation.

### Browser storage is not a reliable backup

Browser-local storage can be cleared, disabled or isolated between URL origins or browser profiles. **Export JSON backups regularly**; they retain both text and editable strokes. Import deliberately replaces the current notebook after confirmation. The format is strictly checked and versioned (\`pmkb-notes-v1\`); imported text is not executed.

## Run on PC — Debian WSL

Terminal: **Debian WSL**; repository \`fr4nck/PimpMyKobo-AuraHD\`:

\`\`\`bash
cd /home/Deniel/pmkb-test || exit 1
git fetch origin
git switch --detach origin/feat/pmkb-notes-v01-host
python3 -m http.server 8766 --bind 127.0.0.1
\`\`\`

Open on the same PC: http://localhost:8766/experimental/notes-v01/index.html

The Python command serves local files only. Browser-local storage is scoped to the precise local origin (use the same address/port on each visit). Stop with Ctrl+C. Avoid opening via \`file://\` because browser storage may be unavailable.

## Modules, qualification and tests

- \`notes-core.js\`: portable, DOM-free validated data model, imports/exports, note search and drawing strokes.
- \`notes-app.js\`: browser UI, touch/mouse drawing, downloads and browser-local storage.
- \`index.html\`: monochrome adaptive text/sketch interface.
- \`tests/test_notes_core.cjs\`: built-in Node.js tests for text, drawing, export/import and malformed data.
- \`tests/test_notes_host_assets.py\`: Python standard-library contract tests, part of CI.

\`\`\`bash
node --test tests/test_notes_core.cjs
python3 -m unittest discover -s tests -p test_notes_host_assets.py -v
\`\`\`

**Manual browser qualification is still required**, including reliable local saves, file download/import, sketch pointer handling and geometry. No actual Kobo touchscreen, EPDC display, physical keyboard, power or Wi-Fi integration is qualified. A finger is expected to be less precise than an active stylus; the Aura HD is not a pen digitizer. A future Kobo backend must be designed separately and can share the data model across screen sizes and devices.

The V0.6 launcher remains a separate unmerged PR; this prototype does **not** activate the Notes tile. No validated manga art, FIRST BOOT, \`rcS\`, \`pmkb-reader\` or P1/P2/P3 files are touched.
