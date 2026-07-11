#!/usr/bin/env python3
"""Strict structural validation for the OneGrid HUD resource pack."""

from __future__ import annotations

import hashlib
import json
import struct
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "pack"
OUTPUT = ROOT / "onegrid-hud.zip"
EXPECTED_FORMAT = 84
EXPECTED_PANELS = (48, 64, 80, 96, 112, 128, 144, 160, 176, 192, 224, 256, 288, 320)


def png_size(data: bytes) -> tuple[int, int]:
    if data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
        raise ValueError("Invalid PNG signature")
    return struct.unpack(">II", data[16:24])


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> None:
    metadata = json.loads((PACK / "pack.mcmeta").read_text(encoding="utf-8"))["pack"]
    require(metadata.get("min_format") == EXPECTED_FORMAT, "min_format must be 84")
    require(metadata.get("max_format") == EXPECTED_FORMAT, "max_format must be 84")
    require("supported_formats" not in metadata, "supported_formats is invalid for pack format 84")

    font = json.loads((PACK / "assets" / "onegrid" / "font" / "hud.json").read_text(encoding="utf-8"))
    bitmap_files = [provider["file"] for provider in font["providers"] if provider.get("type") == "bitmap"]
    require(len(bitmap_files) == len(set(bitmap_files)), "Duplicate bitmap provider")

    for width in EXPECTED_PANELS:
        path = PACK / "assets" / "onegrid" / "textures" / "font" / f"panel_{width}.png"
        require(path.is_file(), f"Missing {path.relative_to(ROOT)}")
        require(png_size(path.read_bytes()) == (width, 13), f"Invalid panel dimensions: {path.name}")

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
