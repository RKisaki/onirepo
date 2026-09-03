#!/usr/bin/env python3
"""Validate OniRepo's separately signed local-extension repository."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from apk_signature import certificate_sha256
from build_hibon_repo import EXPECTED_SIGNING_KEY, PACKAGE_SOURCES, PUBLIC_BASE_URL
from sync_repo import parse_index


def load_json(path: Path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def validate(root: Path) -> None:
    repo_dir = root / "docs" / "hibon"
    binary_index = parse_index((repo_dir / "index.pb").read_bytes())
    json_index = load_json(repo_dir / "index.json")
    legacy_index = load_json(repo_dir / "index.min.json")
    checksums = load_json(repo_dir / "checksums.json")
    repo_metadata = load_json(repo_dir / "repo.json")

    expected_packages = set(PACKAGE_SOURCES)
    binary_by_package = {item.package_name: item for item in binary_index.extensions}
    modern_by_package = {
        item["packageName"]: item for item in json_index["extensionList"]["extensions"]
    }
    legacy_by_package = {item["pkg"]: item for item in legacy_index}
    if not all(
        packages == expected_packages
        for packages in (
            set(binary_by_package),
            set(modern_by_package),
            set(legacy_by_package),
            set(checksums),
        )
    ):
        raise AssertionError("Local extension package sets do not agree")

    if binary_index.signing_key != EXPECTED_SIGNING_KEY:
        raise AssertionError("Unexpected index signing key")
    if json_index["signingKey"] != EXPECTED_SIGNING_KEY:
        raise AssertionError("JSON index signing key does not agree")
    if repo_metadata["meta"]["signingKeyFingerprint"] != EXPECTED_SIGNING_KEY:
        raise AssertionError("repo.json signing key does not agree")
    if repo_metadata["index_v2"] != f"{PUBLIC_BASE_URL}/index.pb":
        raise AssertionError("Unexpected repo URL")

    expected_apks = set()
    expected_icons = set()
    versions = []
    for package_name in sorted(expected_packages):
        binary = binary_by_package[package_name]
        modern = modern_by_package[package_name]
        legacy = legacy_by_package[package_name]
        checksum = checksums[package_name]
        apk_name = checksum["apk"]
        icon_name = package_name + ".png"
        apk_path = repo_dir / "apk" / apk_name
        icon_path = repo_dir / "icon" / icon_name
        expected_apks.add(apk_name)
        expected_icons.add(icon_name)

        if binary.version_code != int(modern["versionCode"]) or binary.version_code != legacy["code"]:
            raise AssertionError(f"Version codes do not agree for {package_name}")
        if binary.version_name != modern["versionName"] or binary.version_name != legacy["version"]:
            raise AssertionError(f"Version names do not agree for {package_name}")
        if binary.content_warning != 3 or modern["contentWarning"] != "CONTENT_WARNING_NSFW":
            raise AssertionError(f"{package_name} must be marked NSFW")
        if checksum["certificateSha256"] != EXPECTED_SIGNING_KEY:
            raise AssertionError(f"Unexpected checksum certificate for {package_name}")
        if not apk_path.is_file() or not icon_path.is_file():
            raise AssertionError(f"Missing APK or icon for {package_name}")
        if hashlib.sha256(apk_path.read_bytes()).hexdigest() != checksum["sha256"]:
            raise AssertionError(f"APK SHA-256 mismatch for {package_name}")
        if certificate_sha256(apk_path) != EXPECTED_SIGNING_KEY:
            raise AssertionError(f"APK certificate does not match the index for {package_name}")
        if icon_path.read_bytes()[:8] != b"\x89PNG\r\n\x1a\n":
            raise AssertionError(f"Icon is not a PNG for {package_name}")

        expected_apk_url = f"{PUBLIC_BASE_URL}/apk/{apk_name}"
        expected_icon_url = f"{PUBLIC_BASE_URL}/icon/{icon_name}"
        if binary.resources.apk_url != expected_apk_url or modern["resources"]["apkUrl"] != expected_apk_url:
            raise AssertionError(f"Unexpected APK URL for {package_name}")
        if binary.resources.icon_url != expected_icon_url or modern["resources"]["iconUrl"] != expected_icon_url:
            raise AssertionError(f"Unexpected icon URL for {package_name}")
        versions.append(f"{binary.name} {binary.version_name}")

    if {path.name for path in (repo_dir / "apk").glob("*.apk")} != expected_apks:
        raise AssertionError("Local APK directory contains unreferenced files")
    if {path.name for path in (repo_dir / "icon").glob("*.png")} != expected_icons:
        raise AssertionError("Local icon directory contains unreferenced files")

    print(
        f"OK: {', '.join(versions)}; indexes, URLs, checksums, APK v2 certificates, "
        "icons, and signing metadata agree."
    )


if __name__ == "__main__":
    try:
        validate(Path(__file__).resolve().parents[1])
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise
