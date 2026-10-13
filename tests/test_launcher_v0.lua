-- Host-only smoke test; lua/luajit/texlua, no Kobo hardware.
local launcher = dofile("experimental/launcher-v0/launcher.lua")
local function expect(value, message) assert(value, message) end
local items = launcher.items()
expect(#items == 8, "8 stable launcher entries")
expect(items[1].id == "books" and items[1].enabled, "only books active")
for i = 2, #items do expect(not items[i].enabled, "future features inactive") end
items[1].id = "tampered"
expect(launcher.items()[1].id == "books", "catalog cannot be changed via copy")
for _, dims in ipairs({{1080,1440}, {1440,1080}, {600,800}}) do
  local s = launcher.new(dims[1],dims[2])
  local tiles = launcher.tiles(s)
  expect(#tiles == 8, "all entries laid out")
  for i, t in ipairs(tiles) do
    expect(t.x >= 0 and t.y >= 0 and t.width > 0 and t.height > 0, "positive tile")
    expect(t.x + t.width <= s.width and t.y + t.height <= s.height, "within viewport")
    for j = 1,i-1 do
      local u = tiles[j]
      expect(t.x >= u.x + u.width or u.x >= t.x + t.width or
        t.y >= u.y + u.height or u.y >= t.y + t.height, "no tile overlap")
    end
  end
  local first = tiles[1]
  local t, action = launcher.handle(s,{type="tap",x=first.x + 5,y=first.y+5})
  expect(t.selected == 1 and action.kind == "intent" and action.name == "open_reader", "books inert intent")
  local disabled = tiles[2]
  _, action = launcher.handle(s,{type="tap",x=disabled.x+5,y=disabled.y+5})
  expect(action.kind == "unavailable" and action.id == "apps", "disabled category")
  _, action = launcher.handle(s,{type="tap",x=0,y=0})
  expect(action.kind == "ignored", "background tap safe")
  _, action = launcher.handle(s,{type="tap",x=0/0,y=0})
  expect(action.kind == "ignored", "nan tap safe")
  local svg = launcher.render_svg(s)
  expect(svg:find("<svg",1,true) ~= nil and svg:find("LIVRES",1,true) ~= nil, "preview")
end
local s = launcher.new(1080,1440)
local s2, a = launcher.handle(s,{type="key",key="right"})
expect(s.selected == 1 and s2.selected == 2 and a.kind == "moved", "pure state change")
local s3, b = launcher.handle(s2,{type="select"})
expect(s3.selected == 2 and b.kind == "unavailable", "keyboard never launches disabled")
local s4, c = launcher.handle(s2,{type="key",key="right"})
expect(s4.selected == 2 and c.kind == "ignored", "no wrap across row")
local s5, d = launcher.handle(s2,{type="key",key="down"})
expect(s5.selected == 4 and d.kind == "moved", "grid navigation")
local s6, e = launcher.handle(s,{type="key",key="bogus"})
expect(s6 == s and e.kind == "ignored", "unrecognized key no side effects")
print("launcher-v0: PASS (menu, touch, keyboard, geometry, disabled entries, preview)")
