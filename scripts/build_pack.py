#!/usr/bin/env python3
"""Build the OneGrid HUD resource pack with deterministic PNG and ZIP output."""

from __future__ import annotations

import json
import shutil
import struct
import zlib
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "pack"
SOURCES = ROOT / "sources"
OUTPUT = ROOT / "onegrid-hud.zip"

PANEL_WIDTHS = (48, 64, 80, 96, 112, 128, 144, 160, 176, 192, 224, 256, 288, 320)
NOTCHES = (6, 10, 12, 20)


def png_chunk(kind: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)


def write_rgba_png(path: Path, width: int, height: int, pixels: list[tuple[int, int, int, int]]) -> None:
    if len(pixels) != width * height:
        raise ValueError(f"Invalid pixel count for {path}: {len(pixels)}")

    raw = bytearray()
    for y in range(height):
        raw.append(0)
        for pixel in pixels[y * width : (y + 1) * width]:
            raw.extend(pixel)

    payload = b"\x89PNG\r\n\x1a\n"
    payload += png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
    payload += png_chunk(b"IDAT", zlib.compress(bytes(raw), level=9))
    payload += png_chunk(b"IEND", b"")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def panel_pixels(width: int, height: int = 12) -> list[tuple[int, int, int, int]]:
    transparent = (0, 0, 0, 0)
    highlight = (180, 190, 208, 132)
    edge = (104, 119, 143, 138)
    fill = (24, 32, 46, 136)
    shadow = (10, 14, 22, 168)

    pixels: list[tuple[int, int, int, int]] = []
    for y in range(height):
        for x in range(width):
            if (x, y) in {(0, 0), (width - 1, 0), (0, height - 1), (width - 1, height - 1)}:
                pixels.append(transparent)
            elif y == 0:
                pixels.append(highlight)
            elif y == height - 1:
                pixels.append(shadow)
            elif x == 0:
                pixels.append(edge)
            elif x == width - 1:
                pixels.append(shadow)
            else:
                pixels.append(fill)
    return pixels


def transparent_pixels(width: int, height: int) -> list[tuple[int, int, int, int]]:
    return [(0, 0, 0, 0)] * (width * height)


def coin_pixels() -> list[tuple[int, int, int, int]]:
    palette = {
        ".": (0, 0, 0, 0),
        "d": (118, 65, 5, 255),
        "o": (223, 132, 13, 255),
        "y": (255, 193, 26, 255),
        "l": (255, 235, 105, 255),
    }
    rows = (
        "...ddd...",
        "..dyyyd..",
        ".dylyyyd.",
        ".dlyyyyd.",
        ".dyyyyyd.",
        ".dyyoyyd.",
        "..dyyyd..",
        "...ddd...",
        ".........",
    )
    return [palette[value] for row in rows for value in row]


def copy_brand_assets() -> None:
    texture_dir = PACK / "assets" / "onegrid" / "textures" / "font"
    texture_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(SOURCES / "icons.png", texture_dir / "icons.png")
    shutil.copyfile(SOURCES / "logo.png", texture_dir / "logo.png")
    shutil.copyfile(SOURCES / "pack.png", PACK / "pack.png")


def generate_panels() -> None:
    texture_dir = PACK / "assets" / "onegrid" / "textures" / "font"
    for width in PANEL_WIDTHS:
        write_rgba_png(texture_dir / f"panel_{width}.png", width, 12, panel_pixels(width))
    write_rgba_png(texture_dir / "coin.png", 9, 9, coin_pixels())


def generate_reserved_bossbar_sprites() -> None:
    sprite_dir = PACK / "assets" / "minecraft" / "textures" / "gui" / "sprites" / "boss_bar"
    names = ["white_background.png", "white_progress.png"]
    for notch in NOTCHES:
        names.extend((f"white_notched_{notch}_background.png", f"white_notched_{notch}_progress.png"))
    for name in names:
        write_rgba_png(sprite_dir / name, 182, 5, transparent_pixels(182, 5))


def validate_font_manifest() -> None:
    manifest = json.loads((PACK / "assets" / "onegrid" / "font" / "hud.json").read_text(encoding="utf-8"))
    panel_files = {
        provider["file"].split(":", 1)[1]
        for provider in manifest["providers"]
        if provider.get("type") == "bitmap" and "panel_" in provider.get("file", "")
    }
    expected = {f"font/panel_{width}.png" for width in PANEL_WIDTHS}
    if panel_files != expected:
        raise RuntimeError(f"Font manifest panels differ: expected={expected}, actual={panel_files}")


def build_zip() -> None:
    files = sorted(
        (path for path in PACK.rglob("*") if path.is_file()),
        key=lambda path: path.relative_to(PACK).as_posix(),
    )
    with zipfile.ZipFile(OUTPUT, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in files:
            relative = path.relative_to(PACK).as_posix()
            info = zipfile.ZipInfo(relative, date_time=(2026, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)


def main() -> None:
    copy_brand_assets()
    generate_panels()
    generate_reserved_bossbar_sprites()
    validate_font_manifest()
    build_zip()
    print(f"Built {OUTPUT} ({OUTPUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
