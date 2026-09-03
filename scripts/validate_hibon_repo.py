#!/usr/bin/env python3
"""Validate the separately signed Hibon BL extension repository."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from apk_signature import certificate_sha256
from build_hibon_repo import EXPECTED_SIGNING_KEY, PACKAGE_NAME, PUBLIC_BASE_URL
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

    if len(binary_index.extensions) != 1 or len(json_index["extensionList"]["extensions"]) != 1:
        raise AssertionError("Hibon repository must contain exactly one extension")
    binary = binary_index.extensions[0]
    modern = json_index["extensionList"]["extensions"][0]
    legacy = legacy_index[0]
    checksum = checksums[PACKAGE_NAME]
    apk_name = checksum["apk"]
    icon_name = PACKAGE_NAME + ".png"
    apk_path = repo_dir / "apk" / apk_name
    icon_path = repo_dir / "icon" / icon_name

    if {binary.package_name, modern["packageName"], legacy["pkg"]} != {PACKAGE_NAME}:
        raise AssertionError("Package names do not agree")
    if binary.version_code != int(modern["versionCode"]) or binary.version_code != legacy["code"]:
        raise AssertionError("Version codes do not agree")
    if binary.version_name != modern["versionName"] or binary.version_name != legacy["version"]:
        raise AssertionError("Version names do not agree")
    if binary.content_warning != 3 or modern["contentWarning"] != "CONTENT_WARNING_NSFW":
        raise AssertionError("Hibon BL must be marked NSFW")
    if binary_index.signing_key != EXPECTED_SIGNING_KEY:
        raise AssertionError("Unexpected index signing key")
    if json_index["signingKey"] != EXPECTED_SIGNING_KEY:
        raise AssertionError("JSON index signing key does not agree")
    if repo_metadata["meta"]["signingKeyFingerprint"] != EXPECTED_SIGNING_KEY:
        raise AssertionError("repo.json signing key does not agree")
    if repo_metadata["index_v2"] != f"{PUBLIC_BASE_URL}/index.pb":
        raise AssertionError("Unexpected repo URL")

    if not apk_path.is_file() or not icon_path.is_file():
        raise AssertionError("Missing Hibon APK or icon")
    if hashlib.sha256(apk_path.read_bytes()).hexdigest() != checksum["sha256"]:
        raise AssertionError("Hibon APK SHA-256 mismatch")
    if certificate_sha256(apk_path) != EXPECTED_SIGNING_KEY:
        raise AssertionError("Hibon APK certificate does not match the index")
    if icon_path.read_bytes()[:8] != b"\x89PNG\r\n\x1a\n":
        raise AssertionError("Hibon icon is not a PNG")

    expected_apk_url = f"{PUBLIC_BASE_URL}/apk/{apk_name}"
    expected_icon_url = f"{PUBLIC_BASE_URL}/icon/{icon_name}"
    if binary.resources.apk_url != expected_apk_url or modern["resources"]["apkUrl"] != expected_apk_url:
        raise AssertionError("Unexpected Hibon APK URL")
    if binary.resources.icon_url != expected_icon_url or modern["resources"]["iconUrl"] != expected_icon_url:
        raise AssertionError("Unexpected Hibon icon URL")
    if {path.name for path in (repo_dir / "apk").glob("*.apk")} != {apk_name}:
        raise AssertionError("Hibon APK directory contains unreferenced files")
    if {path.name for path in (repo_dir / "icon").glob("*.png")} != {icon_name}:
        raise AssertionError("Hibon icon directory contains unreferenced files")

    print(
        f"OK: Hibon BL {binary.version_name}; index, URLs, checksum, "
        "APK v2 certificate, icon, and signing metadata agree."
    )


if __name__ == "__main__":
    try:
        validate(Path(__file__).resolve().parents[1])
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise
