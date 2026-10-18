-- PMKB Native Notes V0: KOReader v2026.07.1 session-only UI bridge.
-- WARNING: this proof of concept does NOT save to disk or touch Kobo hardware.
local ButtonDialog = require("ui/widget/buttondialog")
local InfoMessage = require("ui/widget/infomessage")
local InputDialog = require("ui/widget/inputdialog")
local UIManager = require("ui/uimanager")
local WidgetContainer = require("ui/widget/container/widgetcontainer")
local _ = require("gettext")
local Notes = require("note_core")

local PMKBNotes = WidgetContainer:extend{
    name = "pmkbnotes",
    is_doc_only = false,
    fullname = _("PMKB Notes (essai natif)"),
}

function PMKBNotes:init()
    self.book = Notes.empty()
    self.serial = 0
    self.ui.menu:registerToMainMenu(self)
end

function PMKBNotes:addToMainMenu(menu_items)
    menu_items.pmkb_notes = {
        text = self.fullname,
        sorting_hint = "more_tools",
        callback = function() self:showNotebook() end,
    }
end

function PMKBNotes:utcNow()
    return os.date("!%Y-%m-%dT%H:%M:%S.000Z")
end

function PMKBNotes:nextId()
    local id
    repeat
        self.serial = self.serial + 1
        id = "n" .. tostring(os.time()) .. "-" .. tostring(self.serial)
    until not Notes.get(self.book, id)
    return id
end

function PMKBNotes:alert(message)
    UIManager:show(InfoMessage:new{text = message})
end

function PMKBNotes:editNote(id)
    local item = Notes.get(self.book, id)
    if not item then self:alert(_("Note introuvable")); return end
    local editor
    editor = InputDialog:new{
        title = item.title .. _(" (RAM uniquement)"),
        input = item.text,
        fullscreen = true,
        condensed = true,
        allow_newline = true,
        add_nav_bar = true,
        save_callback = function(content)
            local ok, next_book = pcall(Notes.set_text, self.book, id, content, self:utcNow())
            if not ok then return false, tostring(next_book) end
            self.book = next_book
            return true, _("En memoire pour cette session seulement")
        end,
    }
    UIManager:show(editor)
    editor:onShowKeyboard()
end

function PMKBNotes:newNote()
    if #self.book.notes >= Notes.MAX_NOTES then
        self:alert(_("Limite de notes atteinte"))
        return
    end
    local title_dialog
    title_dialog = InputDialog:new{
        title = _("Titre de la nouvelle note"),
        input = "",
        buttons = {{
            {
                text = _("Annuler"),
                id = "close",
                callback = function() UIManager:close(title_dialog) end,
            },
            {
                text = _("Creer"),
                callback = function()
                    local title = title_dialog:getInputText()
                    local now = self:utcNow()
                    local ok, note = pcall(Notes.blank, self:nextId(), title, now)
                    if not ok then
                        self:alert(_("Titre invalide ou trop long"))
                        return
                    end
                    self.book = Notes.upsert(self.book, note)
                    UIManager:close(title_dialog)
                    self:editNote(note.id)
                end,
            },
        }},
    }
    UIManager:show(title_dialog)
    title_dialog:onShowKeyboard()
end

function PMKBNotes:showNotebook()
    local dialog
    local buttons = {
        {{text = _("Nouvelle note"), callback = function()
            UIManager:close(dialog)
            self:newNote()
        end}},
    }
    for _, note in ipairs(Notes.recent(self.book, 6)) do
        local id = note.id
        buttons[#buttons + 1] = {{
            text = note.title,
            callback = function()
                UIManager:close(dialog)
                self:editNote(id)
            end,
        }}
    end
    buttons[#buttons + 1] = {{
        text = _("Fermer"),
        callback = function() UIManager:close(dialog) end,
    }}
    dialog = ButtonDialog:new{
        title = _("PMKB Notes : saisie de qualification en RAM uniquement"),
        buttons = buttons,
    }
    UIManager:show(dialog)
end

return PMKBNotes
