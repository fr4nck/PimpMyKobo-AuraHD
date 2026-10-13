-- PMKB Launcher V0: pure Lua menu model + SVG host-side preview.
-- No framebuffer, input device, filesystem, process or network access.
local M = {}

local ITEMS = {
  {id = "books", label = "LIVRES", detail = "KOReader", enabled = true},
  {id = "apps", label = "APPLICATIONS", detail = "A VENIR", enabled = false},
  {id = "games", label = "JEUX", detail = "A VENIR", enabled = false},
  {id = "store", label = "BOUTIQUE", detail = "A VENIR", enabled = false},
  {id = "web", label = "WEB", detail = "A VENIR", enabled = false},
  {id = "notes", label = "NOTES", detail = "A VENIR", enabled = false},
  {id = "recipes", label = "RECETTES", detail = "A VENIR", enabled = false},
  {id = "settings", label = "REGLAGES", detail = "A VENIR", enabled = false},
}

local function valid_size(value)
  return type(value) == "number" and value == math.floor(value) and value >= 480 and value <= 4096
end

function M.new(width, height)
  width, height = width or 1080, height or 1440
  assert(valid_size(width) and valid_size(height), "invalid logical screen size")
  return {width = width, height = height, selected = 1}
end

function M.items()
  local copy = {}
  for i, item in ipairs(ITEMS) do
    copy[i] = {id = item.id, label = item.label, detail = item.detail, enabled = item.enabled}
  end
  return copy
end

local function geometry(state)
  local w, h = state.width, state.height
  local landscape = w > h
  local columns = landscape and 4 or 2
  local rows = math.ceil(#ITEMS / columns)
  local side = math.floor(w * 0.045)
  local gap = math.floor(w * (landscape and 0.012 or 0.020))
  local top = math.floor(h * (landscape and 0.145 or 0.125))
  local bottom = math.floor(h * 0.090)
  local tile_w = math.floor((w - 2 * side - (columns - 1) * gap) / columns)
  local tile_h = math.floor((h - top - bottom - (rows - 1) * gap) / rows)
  return columns, side, gap, top, tile_w, tile_h
end

function M.tiles(state)
  local columns, side, gap, top, tile_w, tile_h = geometry(state)
  local result = {}
  for i, item in ipairs(ITEMS) do
    local col = (i - 1) % columns
    local row = math.floor((i - 1) / columns)
    result[i] = {
      id = item.id, label = item.label, detail = item.detail,
      enabled = item.enabled, x = side + col * (tile_w + gap),
      y = top + row * (tile_h + gap), width = tile_w, height = tile_h,
      selected = state.selected == i,
    }
  end
  return result
end

local function updated(state, selected)
  return {width = state.width, height = state.height, selected = selected}
end

-- Inert intent only. The caller must decide whether/how to run KOReader.
-- There is no shell command, runner or arbitrary app path in this module.
local function activate(state, index)
  local item = ITEMS[index]
  if not item then return state, {kind = "ignored"} end
  local next_state = updated(state, index)
  if item.id == "books" and item.enabled then
    return next_state, {kind = "intent", name = "open_reader", id = "books"}
  end
  return next_state, {kind = "unavailable", id = item.id}
end

function M.handle(state, event)
  assert(type(state) == "table" and valid_size(state.width) and valid_size(state.height)
    and type(state.selected) == "number" and state.selected >= 1
    and state.selected <= #ITEMS and state.selected == math.floor(state.selected), "invalid state")
  if type(event) ~= "table" then return state, {kind = "ignored"} end
  if event.type == "tap" then
    local x, y = event.x, event.y
    if type(x) ~= "number" or type(y) ~= "number"
      or x ~= x or y ~= y or x < 0 or y < 0
      or x >= state.width or y >= state.height then
      return state, {kind = "ignored"}
    end
    for i, tile in ipairs(M.tiles(state)) do
      if x >= tile.x and x < tile.x + tile.width
        and y >= tile.y and y < tile.y + tile.height then
        return activate(state, i)
      end
    end
    return state, {kind = "ignored"}
  end
  if event.type == "select" then
    return activate(state, state.selected)
  end
  if event.type == "key" then
    local columns = state.width > state.height and 4 or 2
    local delta = ({left = -1, right = 1, up = -columns, down = columns})[event.key]
    if not delta then return state, {kind = "ignored"} end
    local target = state.selected + delta
    if target < 1 or target > #ITEMS then return state, {kind = "ignored"} end
    if (event.key == "left" or event.key == "right")
      and math.floor((target - 1) / columns) ~= math.floor((state.selected - 1) / columns) then
      return state, {kind = "ignored"}
    end
    return updated(state, target), {kind = "moved", id = ITEMS[target].id}
  end
  return state, {kind = "ignored"}
end

local function xml_escape(value)
  return tostring(value):gsub("&", "&amp;"):gsub("<", "&lt;")
    :gsub(">", "&gt;"):gsub('"', "&quot;")
end

local function tag(name, attributes, text)
  local fields = {"<", name}
  for key, value in pairs(attributes) do
    fields[#fields + 1] = " " .. key .. '= "' .. xml_escape(value) .. '"'
  end
  if text == nil then
    fields[#fields + 1] = "/>"
  else
    fields[#fields + 1] = ">" .. xml_escape(text) .. "</" .. name .. ">"
  end
  return table.concat(fields)
end

-- Preview only; SVG is not an Aura HD framebuffer backend.
function M.render_svg(state)
  local out = {
    '<?xml version="1.0" encoding="UTF-8"?>',
    string.format('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d">',
      state.width, state.height, state.width, state.height),
    tag("rect", {x=0, y=0, width=state.width, height=state.height, fill="#ffffff"}),
    tag("text", {x = math.floor(state.width * 0.045), y = math.floor(state.height * 0.080),
      fill="#000000", ["font-family"]="sans-serif", ["font-size"]=math.floor(state.height * 0.045),
      ["font-weight"]="bold"}, "PMKB"),
    tag("line", {x1=math.floor(state.width * 0.045), x2=math.floor(state.width * 0.955),
      y1=math.floor(state.height * 0.105), y2=math.floor(state.height * 0.105),
      stroke="#000000", ["stroke-width"]=3}),
  }
  for i, tile in ipairs(M.tiles(state)) do
    local cx = tile.x + math.floor(tile.width / 2)
    local primary = tile.selected and "#ffffff" or "#000000"
    local fill = tile.selected and "#000000" or "#ffffff"
    out[#out + 1] = tag("rect", {x=tile.x,y=tile.y,width=tile.width,height=tile.height,
      fill=fill,stroke="#000000",["stroke-width"]=tile.selected and 6 or 3})
    out[#out + 1] = tag("text", {x=cx,y=tile.y+math.floor(tile.height * 0.36),
      fill=primary,["text-anchor"]="middle",["font-family"]="monospace",
      ["font-size"]=math.floor(tile.height * 0.18)}, string.format("%02d", i))
    out[#out + 1] = tag("text", {x=cx,y=tile.y+math.floor(tile.height * 0.60),
      fill=primary,["text-anchor"]="middle",["font-family"]="sans-serif",
      ["font-size"]=math.floor(math.min(tile.height * 0.12,tile.width * 0.075)),
      ["font-weight"]="bold"},tile.label)
    out[#out + 1] = tag("text", {x=cx,y=tile.y+math.floor(tile.height * 0.78),
      fill=primary,["text-anchor"]="middle",["font-family"]="sans-serif",
      ["font-size"]=math.floor(math.min(tile.height * 0.08,tile.width * 0.056))},tile.detail)
  end
  out[#out + 1] = tag("text", {x=math.floor(state.width * 0.045),
    y=math.floor(state.height * 0.965),fill="#000000",["font-family"]="sans-serif",
    ["font-size"]=math.floor(state.height * 0.019)}, "EXPERIMENTAL / OFFLINE / NO HARDWARE ACCESS")
  out[#out + 1] = "</svg>"
  return table.concat(out, "\n") .. "\n"
end

return M
