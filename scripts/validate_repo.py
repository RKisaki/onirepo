#!/usr/bin/env python3
"""Validate that OniRepo's indexes, APKs, icons, and checksums agree."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from sync_repo import PUBLIC_BASE_URL, SELECTED_PACKAGES, parse_index


def load_json(path: Path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def fail(message: str) -> None:
    raise AssertionError(message)


def validate(root: Path) -> None:
    repo_dir = root / "docs" / "repo"
    binary_index = parse_index((repo_dir / "index.pb").read_bytes())
    json_index = load_json(repo_dir / "index.json")
    legacy_index = load_json(repo_dir / "index.min.json")
    checksums = load_json(repo_dir / "checksums.json")
    repo_metadata = load_json(repo_dir / "repo.json")

    binary_packages = {item.package_name for item in binary_index.extensions}
    json_extensions = json_index["extensionList"]["extensions"]
    json_packages = {item["packageName"] for item in json_extensions}
    legacy_packages = {item["pkg"] for item in legacy_index}
    expected_packages = set(SELECTED_PACKAGES)

    if binary_packages != expected_packages:
        fail("index.pb package set does not match SELECTED_PACKAGES")
    if json_packages != expected_packages:
        fail("index.json package set does not match SELECTED_PACKAGES")
    if legacy_packages != expected_packages:
        fail("index.min.json package set does not match SELECTED_PACKAGES")
    if set(checksums) != expected_packages:
        fail("checksums.json package set does not match SELECTED_PACKAGES")
    if binary_index.signing_key != repo_metadata["meta"]["signingKeyFingerprint"]:
        fail("repo.json fingerprint does not match the signing key in index.pb")
    if json_index["signingKey"] != binary_index.signing_key:
        fail("index.json signing key does not match index.pb")
    if repo_metadata["index_v2"] != f"{PUBLIC_BASE_URL}/index.pb":
        fail("repo.json has an unexpected index_v2 URL")

    binary_by_package = {item.package_name: item for item in binary_index.extensions}
    json_by_package = {item["packageName"]: item for item in json_extensions}
    legacy_by_package = {item["pkg"]: item for item in legacy_index}

    referenced_apks: set[str] = set()
    referenced_icons: set[str] = set()
    for package_name in SELECTED_PACKAGES:
        binary = binary_by_package[package_name]
        modern = json_by_package[package_name]
        legacy = legacy_by_package[package_name]
        checksum = checksums[package_name]
        apk_name = checksum["apk"]
        icon_name = package_name + ".png"

        referenced_apks.add(apk_name)
        referenced_icons.add(icon_name)
        apk_path = repo_dir / "apk" / apk_name
        icon_path = repo_dir / "icon" / icon_name
        if not apk_path.is_file():
            fail(f"Missing APK: {apk_name}")
        if not icon_path.is_file():
            fail(f"Missing icon: {icon_name}")
        actual_hash = hashlib.sha256(apk_path.read_bytes()).hexdigest()
        if actual_hash != checksum["sha256"]:
            fail(f"SHA-256 mismatch: {apk_name}")
        if apk_path.read_bytes()[:2] != b"PK":
            fail(f"APK is not a ZIP archive: {apk_name}")
        if icon_path.read_bytes()[:8] != b"\x89PNG\r\n\x1a\n":
            fail(f"Icon is not a PNG file: {icon_name}")

        expected_apk_url = f"{PUBLIC_BASE_URL}/apk/{apk_name}"
        expected_icon_url = f"{PUBLIC_BASE_URL}/icon/{icon_name}"
        if binary.resources.apk_url != expected_apk_url:
            fail(f"Unexpected APK URL in index.pb: {package_name}")
        if binary.resources.icon_url != expected_icon_url:
            fail(f"Unexpected icon URL in index.pb: {package_name}")
        if modern["resources"]["apkUrl"] != expected_apk_url:
            fail(f"Unexpected APK URL in index.json: {package_name}")
        if modern["resources"]["iconUrl"] != expected_icon_url:
            fail(f"Unexpected icon URL in index.json: {package_name}")
        if legacy["apk"] != apk_name:
            fail(f"Unexpected APK filename in legacy index: {package_name}")
        if str(legacy["version"]) != binary.version_name:
            fail(f"Version mismatch in legacy index: {package_name}")
        if int(legacy["code"]) != binary.version_code:
            fail(f"Version code mismatch in legacy index: {package_name}")

    actual_apks = {path.name for path in (repo_dir / "apk").glob("*.apk")}
    actual_icons = {path.name for path in (repo_dir / "icon").glob("*.png")}
    if actual_apks != referenced_apks:
        fail("APK directory contains missing or unreferenced files")
    if actual_icons != referenced_icons:
        fail("Icon directory contains missing or unreferenced files")

    print(
        f"OK: {len(expected_packages)} extensions; all indexes, URLs, "
        "checksums, APKs, icons, and signing metadata agree."
    )


if __name__ == "__main__":
    try:
        validate(Path(__file__).resolve().parents[1])
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise
