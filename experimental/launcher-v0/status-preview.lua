-- Host-only preview of simulated telemetry. No hardware access.
-- Run from repository root: lua experimental/launcher-v0/status-preview.lua > /tmp/pmkb-status.svg
local launcher = dofile("experimental/launcher-v0/launcher.lua")
local state = launcher.new(1080, 1440)
state = launcher.with_status(state, {
  battery=87, charging=true, wifi="off", frontlight=25, contrast="normal",
})
io.write(launcher.render_svg(state))
