-- Standalone host-only V0.3 checks; no hardware access.
local bar = dofile("experimental/launcher-v0/statusbar.lua")
local function expect(condition, label) assert(condition, label) end
local defaults = bar.defaults()
expect(defaults.battery == nil and defaults.wifi == "unknown", "unknown defaults")
local sample = bar.patch(defaults, {battery=87, charging=true, wifi="off", frontlight=25, contrast="normal"})
expect(defaults.battery == nil and defaults.wifi == "unknown", "patch cannot mutate defaults")
local s = {width=1080, height=1440, status=sample}
local labels = bar.labels(s)
expect(labels[1]=="BATT 87+" and labels[2]=="WIFI OFF", "battery and wifi labels")
expect(labels[3]=="LED 25%" and labels[4]=="CTR NORM", "light/contrast")
for _, dims in ipairs({{1080,1440},{1440,1080},{600,800}}) do
  s.width, s.height = dims[1],dims[2]
  local slots = bar.controls(s)
  expect(#slots==7, "7 status slots")
  for i,slot in ipairs(slots) do
    expect(slot.x >= 0 and slot.y >= 0 and slot.x+slot.width <= s.width
      and slot.y+slot.height < s.height*0.932, "bar below tiles and above focus")
    expect(bar.hit(s,slot.x+1,slot.y+1)==slot.id, "tap maps to quick slot")
    if i>1 then expect(slots[i-1].x+slots[i-1].width == slot.x, "no gaps") end
  end
  local svg=bar.render_svg(s)
  expect(svg:find('data-pmkb-status="host-simulation"',1,true), "simulation marked")
  expect(svg:find('data-status-id="battery"',1,true), "rendered battery status")
end
expect(bar.hit(s,0/0,0)==nil and bar.hit(s,-1,800)==nil, "reject invalid tap")
for _, bad in ipairs({-1, 101, 0.5, "55"}) do
  local ok = pcall(bar.patch, defaults, {battery=bad})
  expect(not ok, "battery rejects invalid")
end
expect(not pcall(bar.patch, defaults, {wifi="connected_now"}), "wifi enum")
expect(not pcall(bar.patch, defaults, {voltage=99}), "no uncontrolled telemetry")
local reset=bar.patch(sample,{frontlight=false,wifi="unknown"})
expect(reset.frontlight == nil and reset.wifi=="unknown", "unknown samples")
expect(sample.frontlight==25 and sample.wifi=="off", "unchanged original sample")
print("launcher-statusbar-v0.3: PASS (sample validation, unknown defaults, 7 slots)")
