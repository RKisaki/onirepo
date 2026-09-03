#!/usr/bin/env python3
"""Build the separately signed Hibon BL TachiyomiX repository."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

from apk_signature import certificate_sha256
from sync_repo import (
    Contact,
    Extension,
    Index,
    Resources,
    Source,
    encode_index,
    extension_to_legacy,
    extension_to_v2,
    parse_index,
    write_json,
)


PACKAGE_NAME = "eu.kanade.tachiyomi.extension.es.hibonbl"
PUBLIC_BASE_URL = "https://Pow2105.github.io/onirepo/hibon"
EXPECTED_SIGNING_KEY = "0242522b9f2a8bf0998474e7969b4617cb51b408707c2d04f707d2cd2ab0205c"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(args: argparse.Namespace) -> None:
    apk_source = Path(args.apk).resolve()
    icon_source = Path(args.icon).resolve()
    source_info = json.loads(Path(args.source_info).read_text(encoding="utf-8"))
    output_dir = Path(args.output).resolve()

    if source_info["packageName"] != PACKAGE_NAME:
        raise ValueError(f"Unexpected package: {source_info['packageName']}")
    if source_info["contentWarning"] != 3 or source_info["extensionLib"] != "1.6":
        raise ValueError("Hibon BL must remain an NSFW TachiyomiX 1.6 extension")
    if len(source_info["sources"]) != 1:
        raise ValueError("Expected exactly one Hibon BL source")

    signing_key = certificate_sha256(apk_source)
    if signing_key != EXPECTED_SIGNING_KEY:
        raise ValueError(
            "APK was signed with a different key; updates must use the original signing key"
        )

    apk_dir = output_dir / "apk"
    icon_dir = output_dir / "icon"
    apk_dir.mkdir(parents=True, exist_ok=True)
    icon_dir.mkdir(parents=True, exist_ok=True)
    apk_path = apk_dir / apk_source.name
    icon_name = PACKAGE_NAME + ".png"
    icon_path = icon_dir / icon_name
    shutil.copy2(apk_source, apk_path)
    shutil.copy2(icon_source, icon_path)

    source = source_info["sources"][0]
    extension = Extension(
        name=source_info["name"],
        package_name=PACKAGE_NAME,
        resources=Resources(
            apk_url=f"{PUBLIC_BASE_URL}/apk/{apk_path.name}",
            icon_url=f"{PUBLIC_BASE_URL}/icon/{icon_name}",
        ),
        extension_lib=source_info["extensionLib"],
        version_code=int(source_info["versionCode"]),
        version_name=source_info["versionName"],
        content_warning=int(source_info["contentWarning"]),
        sources=[
            Source(
                source_id=int(source["id"]),
                name=source["name"],
                language=source["lang"],
                home_url=source["baseUrl"],
                mirror_urls=source.get("mirrorUrls", []),
            )
        ],
    )
    index = Index(
        name="OniRepo · Hibon BL",
        badge_label="HIBON",
        signing_key=signing_key,
        contact=Contact(website="https://Pow2105.github.io/onirepo/"),
        extensions=[extension],
    )

    (output_dir / "index.pb").write_bytes(encode_index(index))
    write_json(
        output_dir / "index.json",
        {
            "name": index.name,
            "badgeLabel": index.badge_label,
            "signingKey": index.signing_key,
            "contact": {"website": index.contact.website},
            "extensionList": {"extensions": [extension_to_v2(extension)]},
        },
    )
    write_json(
        output_dir / "index.min.json",
        [extension_to_legacy(extension, apk_path.name)],
        compact=True,
    )
    write_json(
        output_dir / "checksums.json",
        {
            PACKAGE_NAME: {
                "apk": apk_path.name,
                "sha256": sha256(apk_path),
                "certificateSha256": signing_key,
                "source": "extension-src/hibonbl",
                "upstreamBase": args.upstream_base,
            }
        },
    )
    write_json(
        output_dir / "repo.json",
        {
            "index_v2": f"{PUBLIC_BASE_URL}/index.pb",
            "meta": {
                "name": index.name,
                "website": index.contact.website,
                "signingKeyFingerprint": signing_key,
            },
        },
    )

    if parse_index((output_dir / "index.pb").read_bytes()).signing_key != signing_key:
        raise RuntimeError("Generated protobuf index failed round-trip validation")
    print(f"Wrote {extension.name} {extension.version_name} to {output_dir}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apk", required=True)
    parser.add_argument("--icon", required=True)
    parser.add_argument("--source-info", required=True)
    parser.add_argument("--output", default="docs/hibon")
    parser.add_argument(
        "--upstream-base",
        default="keiyoushi/extensions-source@2063590a39622a68075a4cb8834edec8b11d0986",
    )
    return parser.parse_args()


if __name__ == "__main__":
    try:
        build(parse_args())
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise
