-- PMKB Notes native smoke test: host mocks, no hardware and no file writes.
local prefix = "experimental/native-notes/pmkbnotes.koplugin/"
package.path = prefix .. "?.lua;" .. package.path
local Model = require("note_core")
local date = "2026-10-18T20:00:00.000Z"
local book = Model.empty()
assert(book.format == "pmkb-notes-v1" and #book.notes == 0)
local first = Model.blank("n000001", "Bonjour ecran", date)
assert(first.typography.font == "mono" and first.typography.lineHeight == 1.6)
book = Model.upsert(book, first)
local original = book
local edited = Model.set_text(book, first.id, "Un texte avec retour\nA bientot", date)
assert(Model.get(original, first.id).text == "", "must not mutate prior model")
assert(Model.get(edited, first.id).text:find("\n", 1, true), "UTF-8 text preserved")
assert(#edited.notes == 1)
local duplicate = Model.blank("n000002", "Titre reserve", date)
edited = Model.upsert(edited, duplicate)
assert(#Model.recent(edited, 1) == 1)
assert(Model.recent(edited, 2)[1].id == "n000001")
local invalid = {id="n000003",title="",text="",created=date,updated=date,
    typography={font="mono",size=17,lineHeight=1.6},strokes={}}
assert(not pcall(Model.upsert, edited, invalid), "invalid title must fail")
assert(not pcall(Model.blank, "BAD ID", "Valid", date), "invalid id must fail")
assert(not pcall(Model.blank, "n000005", "x", "bad"), "invalid date must fail")
assert(not pcall(Model.set_text, edited, "missing", "text", date))
assert(not pcall(Model.set_text, edited, first.id,
    string.rep("x", Model.MAX_TEXT + 1), date), "max text")
local accented = Model.blank("n000004", "Cahier ecole", date)
accented.strokes = {{tool="pen",width=5,points={{1,2},{3,4}}}}
edited = Model.upsert(edited, accented)
local clone = Model.get(edited, accented.id)
clone.strokes[1].points[1][1] = 800
assert(Model.get(edited, accented.id).strokes[1].points[1][1] == 1,
    "croquis must not be mutated by editing")
local too_many = Model.empty()
for i = 1, Model.MAX_NOTES do
    too_many = Model.upsert(too_many, Model.blank("n" .. string.format("%05d",i), "Note", date))
end
assert(not pcall(Model.upsert, too_many,
    Model.blank("n100001", "Extra", date)), "limit 100")
-- Stub the exact KOReader widget APIs used by main.lua.
local shown, closed, keyboards = {}, {}, 0
package.preload["gettext"] = function() return function(x) return x end end
package.preload["ui/widget/container/widgetcontainer"] = function()
    return {extend=function(_, t) return t end}
end
local function widget(t)
    t.onShowKeyboard = function() keyboards = keyboards + 1 end
    t.getInputText = function(self) return self.input end
    return t
end
package.preload["ui/widget/inputdialog"] = function()
    return {new=function(_, t) return widget(t) end}
end
package.preload["ui/widget/buttondialog"] = function()
    return {new=function(_, t) return widget(t) end}
end
package.preload["ui/widget/infomessage"] = function()
    return {new=function(_, t) return widget(t) end}
end
package.preload["ui/uimanager"] = function()
    return {show=function(_, value) shown[#shown+1]=value end,
        close=function(_, value) closed[#closed+1]=value end}
end
local Plugin = dofile(prefix .. "main.lua")
local menu_registered
local instance = setmetatable({
    ui = {menu = {registerToMainMenu=function(_, plugin) menu_registered=plugin end}},
}, {__index=Plugin})
instance:init()
assert(menu_registered == instance and #instance.book.notes == 0)
local entries = {}
instance:addToMainMenu(entries)
assert(entries.pmkb_notes.sorting_hint == "more_tools")
-- The whole flow is a virtual KOReader dialog and its built-in keyboard.
entries.pmkb_notes.callback()
assert(#shown == 1 and shown[1].buttons[1][1].text == "Nouvelle note")
local notebook = shown[#shown]
notebook.buttons[1][1].callback()
local title = shown[#shown]
assert(keyboards == 1 and title.title == "Titre de la nouvelle note")
title.input = "Journal"
title.buttons[1][2].callback()
local editor = shown[#shown]
assert(editor.fullscreen == true and editor.allow_newline == true and
    editor.add_nav_bar == true, "native KOReader editor settings")
assert(keyboards == 2)
local success, message = editor.save_callback("Bonjour Kobo")
assert(success and message:find("session"), "save must warn session-only")
assert(#instance.book.notes == 1 and instance.book.notes[1].text == "Bonjour Kobo")
assert(#closed == 2, "close notebook and title")
local updated_text = instance.book.notes[1].text
instance:showNotebook()
local reopened_menu = shown[#shown]
reopened_menu.buttons[2][1].callback()
assert(shown[#shown].input == updated_text, "reopen session note")
-- None of the plugin flows may create a local file.
print("PMKB native Notes: PASS (portable model, KOReader UI mocks, keyboard, RAM only)")
