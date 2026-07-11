#!/usr/bin/env python3
"""Strict structural validation for the OneGrid HUD resource pack."""

from __future__ import annotations

import hashlib
import json
import struct
import zlib
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "pack"
OUTPUT = ROOT / "onegrid-hud.zip"
PANEL_REFERENCE = ROOT / "sources" / "hud_panel_reference.png"
EXPECTED_FORMAT = 84
EXPECTED_PANELS = (48, 64, 80, 96, 112, 128, 144, 160, 176, 192, 224, 256, 288, 320)
EXPECTED_PANEL_HEIGHT = 15
EXPECTED_PANEL_ASCENT = 11
EXPECTED_PANEL_FILL = (0x35, 0x35, 0x35, 115)
EXPECTED_PANEL_BORDER = (0x48, 0x48, 0x48, 64)
EXPECTED_REFERENCE_SHA256 = "d6b5ee408156e4775179783808e9d11e87fda00cf42967e8d9f2317550e66faf"
TRANSPARENT = (0, 0, 0, 0)


def png_size(data: bytes) -> tuple[int, int]:
    if data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
        raise ValueError("Invalid PNG signature")
    return struct.unpack(">II", data[16:24])


def rgba_pixels(data: bytes) -> tuple[int, int, list[tuple[int, int, int, int]]]:
    width, height = png_size(data)
    chunks: list[bytes] = []
    offset = 8
    while offset < len(data):
        length = struct.unpack(">I", data[offset : offset + 4])[0]
        kind = data[offset + 4 : offset + 8]
        payload = data[offset + 8 : offset + 8 + length]
        if kind == b"IHDR":
            bit_depth, color_type = payload[8], payload[9]
            require(bit_depth == 8 and color_type == 6, "Panel PNG must use 8-bit RGBA")
        elif kind == b"IDAT":
            chunks.append(payload)
        elif kind == b"IEND":
            break
        offset += 12 + length

    raw = zlib.decompress(b"".join(chunks))
    stride = width * 4
    require(len(raw) == height * (stride + 1), "Unexpected panel PNG payload size")
    pixels: list[tuple[int, int, int, int]] = []
    for y in range(height):
        row = raw[y * (stride + 1) : (y + 1) * (stride + 1)]
        require(row[0] == 0, "Panel PNG rows must use the deterministic filter 0")
        pixels.extend(tuple(row[index : index + 4]) for index in range(1, len(row), 4))
    return width, height, pixels


def expected_panel_pixel(x: int, y: int, width: int, height: int) -> tuple[int, int, int, int]:
    if y == 0:
        return EXPECTED_PANEL_BORDER if 1 <= x < width - 2 else TRANSPARENT
    if y == 1:
        if x < 2:
            return EXPECTED_PANEL_BORDER
        return EXPECTED_PANEL_FILL if x < width - 1 else TRANSPARENT
    if y == height - 2:
        if x == 0:
            return TRANSPARENT
        return EXPECTED_PANEL_FILL if x < width - 2 else EXPECTED_PANEL_BORDER
    if y == height - 1:
        return EXPECTED_PANEL_BORDER if 2 <= x < width - 1 else TRANSPARENT
    if x == 0 or x == width - 1:
        return EXPECTED_PANEL_BORDER
    return EXPECTED_PANEL_FILL


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> None:
    require(PANEL_REFERENCE.is_file(), "Missing original HUD panel reference")
    reference_data = PANEL_REFERENCE.read_bytes()
    require(png_size(reference_data) == (210, 30), "HUD panel reference must remain 210x30")
    require(
        hashlib.sha256(reference_data).hexdigest() == EXPECTED_REFERENCE_SHA256,
        "HUD panel reference differs from the approved Frame 63 source",
    )

    metadata = json.loads((PACK / "pack.mcmeta").read_text(encoding="utf-8"))["pack"]
    require(metadata.get("min_format") == EXPECTED_FORMAT, "min_format must be 84")
    require(metadata.get("max_format") == EXPECTED_FORMAT, "max_format must be 84")
    require("supported_formats" not in metadata, "supported_formats is invalid for pack format 84")

    font = json.loads((PACK / "assets" / "onegrid" / "font" / "hud.json").read_text(encoding="utf-8"))
    bitmap_providers = [provider for provider in font["providers"] if provider.get("type") == "bitmap"]
    bitmap_files = [provider["file"] for provider in bitmap_providers]
    require(len(bitmap_files) == len(set(bitmap_files)), "Duplicate bitmap provider")
    panel_providers = [provider for provider in bitmap_providers if "panel_" in provider["file"]]
    require(len(panel_providers) == len(EXPECTED_PANELS), "Unexpected number of panel providers")
    require(
        all(
            provider.get("height") == EXPECTED_PANEL_HEIGHT
            and provider.get("ascent") == EXPECTED_PANEL_ASCENT
            for provider in panel_providers
        ),
        "Panel providers must render at height 15 and ascent 11",
    )

    for width in EXPECTED_PANELS:
        path = PACK / "assets" / "onegrid" / "textures" / "font" / f"panel_{width}.png"
        require(path.is_file(), f"Missing {path.relative_to(ROOT)}")
        panel_width, panel_height, pixels = rgba_pixels(path.read_bytes())
        require(
            (panel_width, panel_height) == (width, EXPECTED_PANEL_HEIGHT),
            f"Invalid panel dimensions: {path.name}",
        )
        expected = [
            expected_panel_pixel(x, y, panel_width, panel_height)
            for y in range(panel_height)
            for x in range(panel_width)
        ]
        require(pixels == expected, f"Invalid panel palette or geometry: {path.name}")

    bossbar_dir = PACK / "assets" / "minecraft" / "textures" / "gui" / "sprites" / "boss_bar"
    bossbar_files = sorted(bossbar_dir.glob("*.png"))
    require(bool(bossbar_files), "Missing reserved HUD bossbar sprites")
    require(all(path.name.startswith("white_") for path in bossbar_files), "Only white bossbars may be overridden")
    require(all(png_size(path.read_bytes()) == (182, 5) for path in bossbar_files), "Invalid bossbar sprite dimensions")
    require(not (PACK / "assets" / "minecraft" / "font" / "default.json").exists(), "minecraft:default must not be overridden")

    with zipfile.ZipFile(OUTPUT) as archive:
        names = archive.namelist()
        require("pack.mcmeta" in names, "pack.mcmeta must be at ZIP root")
        require("pack.png" in names, "pack.png must be at ZIP root")
        require(all(not name.startswith("pack/") for name in names), "ZIP contains an extra pack/ directory")
        require(len(names) == len(set(names)), "ZIP contains duplicate entries")

    sha1 = hashlib.sha1(OUTPUT.read_bytes()).hexdigest()
    sha256 = hashlib.sha256(OUTPUT.read_bytes()).hexdigest()
    print(f"OK files={len(names)} sha1={sha1} sha256={sha256}")


if __name__ == "__main__":
    main()
