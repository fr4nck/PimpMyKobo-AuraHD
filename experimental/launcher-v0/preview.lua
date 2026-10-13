-- Usage from repo root:
-- lua experimental/launcher-v0/preview.lua [width [height [left|right|up|down ...]]] > launcher.svg
-- Host-side only: state previews without input devices, shell or real launches.
local launcher = dofile("experimental/launcher-v0/launcher.lua")
local width = arg[1] and tonumber(arg[1]) or 1080
local height = arg[2] and tonumber(arg[2]) or 1440
local state = launcher.new(width, height)
local keys = {left=true, right=true, up=true, down=true}
for i = 3, #arg do
  local key = arg[i]
  assert(keys[key], "unknown preview key: " .. tostring(key))
  state = launcher.handle(state, {type="key", key=key})
end
io.write(launcher.render_svg(state))
