-- Exercise upstream settings functions, with no device initialization or real
-- config access. Run only with the pinned upstream files checked by Python.
local root, proposal = assert(arg[1]), assert(arg[2])
local function class(parent, values)
    return setmetatable(values or {}, { __index = parent })
end
local Base = {}
function Base:extend(values) return class(self, values) end
function Base:new(values) return class(self, values) end
package.loaded["device/generic/powerd"] = Base
package.loaded["luasettings"] = Base
package.loaded["optmath"] = { round = function(n) return math.floor(n + 0.5) end }
package.loaded["device/sysfs_light"] = {}
package.loaded["ffi/rtc"] = {}
package.loaded["logger"] = { warn = function() end }
package.loaded["dbg"] = { guard = function() end }
package.loaded["dump"] = {}
package.loaded["util"] = {}
package.loaded["libs/libkoreader-lfs"] = { attributes = function() return nil end }
package.loaded["datastorage"] = { getDataDir = function() error("Unexpected data directory access") end }

local attempts = {}
local original_open = io.open
io.open = function(path, mode)
    assert(path == "/mnt/onboard/.kobo/Kobo/Kobo eReader.conf", "Unexpected file access: " .. path)
    attempts[#attempts + 1] = mode
    return nil, "Read-only file system (synthetic)", 30
end
package.loaded["device/kobo/nickel_conf"] = dofile(root .. "/frontend/device/kobo/nickel_conf.lua")
local PowerD = dofile(root .. "/frontend/device/kobo/powerd.lua")
local Defaults = dofile(root .. "/frontend/luadefaults.lua")
local upstream = dofile(root .. "/defaults.lua")
local override = dofile(proposal)
G_reader_settings = {
    values = {},
    readSetting = function(self, key) return self.values[key] end,
    saveSetting = function(self, key, value) self.values[key] = value end,
}
local function instance(custom)
    G_defaults = Defaults:extend{ ro = upstream, rw = custom }
    return PowerD:new{
        device = { hasFrontlight = function() return true end },
        hw_intensity = 20, initial_is_fl_on = true,
        fl_min = 0, fl_intensity = 20, is_fl_on = true,
    }
end
local function attempted_write()
    for _, mode in ipairs(attempts) do if mode == "w" then return true end end
    return false
end
-- Baseline: a missing FrontLightLevel triggers a write even while reading.
local stock = instance({})
local ok, err = pcall(stock._syncKoboLightOnStart, stock)
assert(not ok and tostring(err):find("Read%-only file system"))
assert(attempted_write())
attempts = {}
ok, err = pcall(stock.saveSettings, stock)
assert(not ok and tostring(err):find("Read%-only file system"))
assert(attempted_write())

-- The actual LuaDefaults reader must preserve a false override.
attempts = {}
G_reader_settings.values = {}
local independent = instance(override)
assert(G_defaults:readSetting("KOBO_SYNC_BRIGHTNESS_WITH_NICKEL") == false)
independent:_syncKoboLightOnStart()
assert(independent.hw_intensity == 20 and independent.initial_is_fl_on == true)
independent:saveSettings()
assert(#attempts == 0, "Staged settings still access the Nickel configuration")
assert(G_reader_settings.values.frontlight_intensity == 20)
assert(G_reader_settings.values.is_frontlight_on == true)
G_reader_settings.values.frontlight_intensity = 37
G_reader_settings.values.is_frontlight_on = false
independent:_syncKoboLightOnStart()
assert(independent.hw_intensity == 37 and independent.initial_is_fl_on == false)
assert(#attempts == 0)
io.open = original_open
print("PASS: upstream defaults fail against synthetic read-only Nickel config; staged overrides avoid all Nickel config access and retain KOReader settings")
