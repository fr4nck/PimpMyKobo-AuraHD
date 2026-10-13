-- Usage from repository root:
-- lua experimental/launcher-v0/preview.lua [1080 [1440]] > launcher.svg
-- Under environments with texlua: texlua experimental/launcher-v0/preview.lua ...
local launcher = dofile("experimental/launcher-v0/launcher.lua")
local width = tonumber(arg[1]) or 1080
local height = tonumber(arg[2]) or 1440
io.write(launcher.render_svg(launcher.new(width, height)))
