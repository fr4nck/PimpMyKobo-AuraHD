-- Static ARM ABI check only: no framebuffer open, mmap, ioctl or init.
local root = assert(arg[1])
package.path = root .. "/?.lua;" .. package.path
local ffi = require("ffi")
assert(jit.arch == "arm" and ffi.sizeof("void *") == 4)
require("ffi/mxcfb_kobo_h")
-- Aura HD kernel include/linux/mxcfb.h: mxcfb_update_data contains
-- a 16-byte region, five 32-bit scalars and a 32-byte alternate buffer.
assert(ffi.sizeof("struct mxcfb_rect") == 16)
assert(ffi.sizeof("struct mxcfb_alt_buffer_data_ntx") == 32)
assert(ffi.sizeof("struct mxcfb_update_data_v1_ntx") == 68)
assert(ffi.offsetof("struct mxcfb_update_data_v1_ntx", "alt_buffer_data") == 36)
assert(ffi.C.MXCFB_SEND_UPDATE_V1_NTX == 0x4044462e)
assert(ffi.C.MXCFB_WAIT_FOR_UPDATE_COMPLETE_V1 == 0x4004462f)
print("PASS: ARM32 MXCFB layout 68 bytes and classic NTX ioctl encodings match the audited kernel header; no device calls")
