-- PMKB Notes native V0: portable, session-only notebook model.
-- KOReader is optional; no filesystem, DOM, device or network dependencies.
local Notes = {}
Notes.FORMAT = "pmkb-notes-v1"
Notes.MAX_NOTES = 100
Notes.MAX_TITLE = 100
Notes.MAX_TEXT = 120000
local function require_valid(condition, message)
    if not condition then error(message, 2) end
end
local function is_id(value)
    return type(value) == "string" and #value >= 6 and #value <= 72
        and value:find("[^a-z0-9_-]") == nil
end
local function timestamp(value)
    return type(value) == "string" and (
        value:match("^%d%d%d%d%-%d%d%-%d%dT%d%d:%d%d:%d%dZ$") or
        value:match("^%d%d%d%d%-%d%d%-%d%dT%d%d:%d%d:%d%d%.%d%d%dZ$")
    ) ~= nil
end
-- Count UTF-16 units, the same public length convention as JS Notes.
local function utf16_units(value)
    local i, count = 1, 0
    while i <= #value do
        local a = value:byte(i)
        local step, units
        if a < 128 then
            step, units = 1, 1
        elseif a >= 194 and a <= 223 then
            step, units = 2, 1
        elseif a >= 224 and a <= 239 then
            step, units = 3, 1
        elseif a >= 240 and a <= 244 then
            step, units = 4, 2
        else
            error("UTF-8 invalide", 2)
        end
        require_valid(i + step - 1 <= #value, "UTF-8 tronque")
        for j = i + 1, i + step - 1 do
            local b = value:byte(j)
            require_valid(b >= 128 and b <= 191, "UTF-8 invalide")
        end
        if step == 3 then
            local b = value:byte(i + 1)
            require_valid(not (a == 224 and b < 160) and
                not (a == 237 and b > 159), "UTF-8 invalide")
        elseif step == 4 then
            local b = value:byte(i + 1)
            require_valid(not (a == 240 and b < 144) and
                not (a == 244 and b > 143), "UTF-8 invalide")
        end
        count = count + units
        i = i + step
    end
    return count
end
local function clone(value)
    if type(value) ~= "table" then return value end
    local copy = {}
    for k, v in pairs(value) do copy[k] = clone(v) end
    return copy
end
local function is_integer(n)
    return type(n) == "number" and n == math.floor(n) and n == n
end
local function validate_note(note)
    require_valid(type(note) == "table" and is_id(note.id), "Identifiant invalide")
    require_valid(type(note.title) == "string" and note.title:match("%S") and
        utf16_units(note.title) <= Notes.MAX_TITLE, "Titre invalide")
    require_valid(type(note.text) == "string" and
        utf16_units(note.text) <= Notes.MAX_TEXT, "Texte invalide")
    require_valid(timestamp(note.created) and timestamp(note.updated), "Date invalide")
    local ty = note.typography
    require_valid(type(ty) == "table" and type(ty.font) == "string" and
        (ty.font == "mono" or ty.font == "sans" or ty.font == "serif" or
        ty.font == "handwriting" or
        (#ty.font == 19 and ty.font:match("^import:[a-f0-9]+$"))) and
        is_integer(ty.size) and ty.size >= 12 and ty.size <= 36 and
        (ty.lineHeight == 1.2 or ty.lineHeight == 1.4 or
         ty.lineHeight == 1.6 or ty.lineHeight == 1.8 or ty.lineHeight == 2),
        "Typographie invalide")
    require_valid(type(note.strokes) == "table" and #note.strokes <= 250,
        "Croquis invalide")
    for _, stroke in ipairs(note.strokes) do
        require_valid(type(stroke) == "table" and
            (stroke.tool == "pen" or stroke.tool == "eraser") and
            (stroke.width == 2 or stroke.width == 5 or stroke.width == 11) and
            type(stroke.points) == "table" and
            #stroke.points >= 1 and #stroke.points <= 1200, "Trait invalide")
        for _, pt in ipairs(stroke.points) do
            require_valid(type(pt) == "table" and #pt == 2 and
                is_integer(pt[1]) and is_integer(pt[2]) and
                pt[1] >= 0 and pt[1] <= 900 and
                pt[2] >= 0 and pt[2] <= 600, "Point invalide")
        end
    end
    return clone(note)
end
function Notes.empty()
    return {format = Notes.FORMAT, notes = {}}
end
function Notes.validate(book)
    require_valid(type(book) == "table" and book.format == Notes.FORMAT and
        type(book.notes) == "table" and #book.notes <= Notes.MAX_NOTES,
        "Format de carnet invalide")
    local seen = {}
    local result = Notes.empty()
    for _, note in ipairs(book.notes) do
        local clean = validate_note(note)
        require_valid(not seen[clean.id], "Identifiant en double")
        seen[clean.id] = true
        result.notes[#result.notes + 1] = clean
    end
    return result
end
function Notes.blank(id, title, now)
    local value = {id = id, title = title, text = "", strokes = {},
        typography = {font = "mono", size = 17, lineHeight = 1.6},
        created = now, updated = now}
    return validate_note(value)
end
function Notes.upsert(book, value)
    local next_book = Notes.validate(book)
    local clean = validate_note(value)
    for i, note in ipairs(next_book.notes) do
        if note.id == clean.id then
            next_book.notes[i] = clean
            return next_book
        end
    end
    require_valid(#next_book.notes < Notes.MAX_NOTES, "Carnet plein")
    next_book.notes[#next_book.notes + 1] = clean
    return next_book
end
function Notes.get(book, id)
    local valid = Notes.validate(book)
    for _, note in ipairs(valid.notes) do
        if note.id == id then return note end
    end
    return nil
end
function Notes.set_text(book, id, text, now)
    local value = Notes.get(book, id)
    require_valid(value ~= nil, "Note absente")
    value.text = text
    value.updated = now
    return Notes.upsert(book, value)
end
function Notes.recent(book, limit)
    local valid = Notes.validate(book)
    table.sort(valid.notes, function(a, b)
        if a.updated ~= b.updated then return a.updated > b.updated end
        return a.id < b.id
    end)
    local found = {}
    for i = 1, math.min(#valid.notes, limit or 6) do
        found[#found + 1] = valid.notes[i]
    end
    return found
end
return Notes
