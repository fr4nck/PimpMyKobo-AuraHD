-- PMKB status bar V0.3: pure Lua, host simulation only.
-- No hardware probes, process launch, network or file operations.
local M = {}
local CONTROLS = {"battery", "wifi", "frontlight", "contrast", "refresh", "sleep", "settings"}
local LABELS = {
  battery = "BATT", wifi = "WIFI", frontlight = "LED", contrast = "CONTR",
  refresh = "RAF", sleep = "VEILLE", settings = "REG",
}

function M.defaults()
  -- nil means unknown, never fabricate measurements.
  return {wifi = "unknown", contrast = "unknown"}
end

local function clone(state)
  local result = {}
  for _, name in ipairs({"battery", "charging", "wifi", "frontlight", "contrast"}) do
    result[name] = state[name]
  end
  return result
end

local function percentage(value)
  return type(value) == "number" and value == math.floor(value)
    and value >= 0 and value <= 100
end

-- Inputs are externally supplied sample telemetry. No implicit hardware access.
function M.patch(status, sample)
  assert(type(status) == "table" and type(sample) == "table", "invalid status sample")
  local next_status = clone(status)
  for name, value in pairs(sample) do
    if name == "battery" or name == "frontlight" then
      assert(value == false or percentage(value), "invalid " .. name)
      if value == false then next_status[name] = nil else next_status[name] = value end
    elseif name == "charging" then
      assert(type(value) == "boolean", "invalid charging")
      next_status.charging = value
    elseif name == "wifi" then
      assert(value == "unknown" or value == "off" or value == "connecting"
        or value == "connected", "invalid wifi")
      next_status.wifi = value
    elseif name == "contrast" then
      assert(value == "unknown" or value == "normal" or value == "high"
        or value == "inverse", "invalid contrast")
      next_status.contrast = value
    else
      error("unsupported telemetry: " .. tostring(name))
    end
  end
  return next_status
end

function M.controls(state)
  local w, h = state.width, state.height
  local side = math.floor(w * 0.045)
  local top = math.floor(h * 0.881)
  local height = math.max(25, math.floor(h * 0.042))
  local width = w - 2 * side
  local result = {}
  for i, id in ipairs(CONTROLS) do
    local x0 = side + math.floor((i - 1) * width / #CONTROLS)
    local x1 = side + math.floor(i * width / #CONTROLS)
    result[i] = {id=id, x=x0, y=top, width=x1-x0, height=height}
  end
  return result
end

function M.hit(state, x, y)
  if type(x) ~= "number" or type(y) ~= "number" or x ~= x or y ~= y then
    return nil
  end
  for _, slot in ipairs(M.controls(state)) do
    if x >= slot.x and x < slot.x + slot.width
      and y >= slot.y and y < slot.y + slot.height then
      return slot.id
    end
  end
  return nil
end

local function text_for(id, s)
  if id == "battery" then
    if s.battery == nil then return "BATT --" end
    return "BATT " .. s.battery .. (s.charging and "+" or "%")
  elseif id == "wifi" then
    local text = {unknown="?", off="OFF", connecting="...", connected="OK"}
    return "WIFI " .. (text[s.wifi] or "?")
  elseif id == "frontlight" then
    return s.frontlight == nil and "LED --" or ("LED " .. s.frontlight .. "%")
  elseif id == "contrast" then
    local text = {unknown="?", normal="NORM", high="HAUT", inverse="INV"}
    return "CTR " .. (text[s.contrast] or "?")
  end
  return LABELS[id]
end

function M.labels(state)
  local result = {}
  for i, id in ipairs(CONTROLS) do result[i] = text_for(id, state.status or M.defaults()) end
  return result
end

-- The returned XML is an inert group for embedding in a host SVG preview.
function M.render_svg(state)
  local slots = M.controls(state)
  local labels = M.labels(state)
  local x, y = slots[1].x, slots[1].y
  local last = slots[#slots]
  local width = last.x + last.width - x
  local height = slots[1].height
  local font = math.max(9, math.floor(math.min(state.width * 0.016, state.height * 0.016)))
  local out = {'<g data-pmkb-status="host-simulation">',
    string.format('<rect x="%d" y="%d" width="%d" height="%d" fill="#ffffff" stroke="#000000" stroke-width="2"/>', x,y,width,height)}
  for i, slot in ipairs(slots) do
    if i > 1 then
      out[#out+1] = string.format('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="#000000" stroke-width="1"/>', slot.x,y,slot.x,y+height)
    end
    out[#out+1] = string.format('<text data-status-id="%s" x="%d" y="%d" fill="#000000" text-anchor="middle" font-family="monospace" font-size="%d">%s</text>',
      slot.id,slot.x + math.floor(slot.width / 2),y+math.floor(height*0.64),font,labels[i])
  end
  out[#out+1] = '</g>'
  return table.concat(out, "\n")
end

return M
