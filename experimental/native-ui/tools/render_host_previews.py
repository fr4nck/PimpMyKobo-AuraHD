#!/usr/bin/env python3
"""Generate and validate actual C raster previews; stdlib only, no downloads."""
import argparse
import hashlib
from pathlib import Path
import re
import struct
import subprocess
import tempfile
import zlib

def load_pgm(path: Path):
    raw = path.read_bytes()
    header = re.match(rb"P5\n([0-9]+) ([0-9]+)\n255\n", raw)
    if not header:
        raise AssertionError("Invalid P5 PGM header")
    width, height = (int(value) for value in header.groups())
    pixels = raw[header.end():]
    if len(pixels) != width * height:
        raise AssertionError("Image pixel count mismatch")
    return width, height, pixels

def png_chunk(kind: bytes, data: bytes):
    return (struct.pack(">I", len(data)) + kind + data +
            struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff))

def convert_png(width: int, height: int, pixels: bytes):
    filtered = b"".join(b"\x00" + pixels[y*width:(y+1)*width]
                        for y in range(height))
    return (b"\x89PNG\r\n\x1a\n" +
            png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height,
                      8, 0, 0, 0, 0)) +
            png_chunk(b"IDAT", zlib.compress(filtered, level=9)) +
            png_chunk(b"IEND", b""))

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, default=Path("./pmkb-host-preview"))
    parser.add_argument("--output-dir", type=Path, help="Write PNG images here; default temporary QA only")
    args = parser.parse_args()
    output_dir = args.output_dir
    temp = tempfile.TemporaryDirectory(prefix="pmkb-preview-") if output_dir is None else None
    try:
        destination = output_dir or Path(temp.name)
        destination.mkdir(parents=True, exist_ok=True)
        checks = 0
        signatures = set()
        for mode in ("notes", "calculator", "store", "store-detail", "glyphs", "whiteboard"):
            for width, height in ((320, 480), (1080, 1440)):
                stem = f"pmkb-{mode}-{width}x{height}"
                pgm = destination / f"{stem}.pgm"
                png = destination / f"{stem}.png"
                subprocess.run([str(args.binary.resolve()), mode, str(width),
                                str(height), str(pgm)], check=True, timeout=20)
                pw, ph, pixels = load_pgm(pgm)
                assert (pw, ph) == (width, height)
                assert min(pixels) == 0 and max(pixels) == 255
                # Glyph reference is intentionally 1-bit: black and white only.
                assert len(set(pixels)) >= (2 if mode in ("glyphs", "whiteboard") else 3)
                assert sum(value < 30 for value in pixels) > width * 2
                if mode not in ("glyphs", "whiteboard"):
                    # The bottom navigation area retains visible black and white pixels.
                    bottom = pixels[(height-44)*width:]
                    assert any(value == 0 for value in bottom)
                    assert any(value == 255 for value in bottom)
                signature = hashlib.sha256(pixels).hexdigest()
                assert signature not in signatures
                signatures.add(signature)
                data = convert_png(width, height, pixels)
                assert data[:8] == b"\x89PNG\r\n\x1a\n"
                png.write_bytes(data)
                assert png.stat().st_size > 200
                print(f"SNAPSHOT PASS {stem}: {width*height} pixels, SHA256 {signature[:12]}")
                checks += 1
                # No need to retain duplicate PGM once the host PNG was checked.
                pgm.unlink()
        assert checks == 12
        print(f"PMKB HOST SNAPSHOTS: {checks}/12 PASS, 0 FAIL")
    finally:
        if temp is not None:
            temp.cleanup()

if __name__ == "__main__":
    main()
