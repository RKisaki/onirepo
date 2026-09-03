#!/usr/bin/env python3
"""Add or update an OniRepo-built extension in the separately signed store."""

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


PACKAGE_SOURCES = {
    "eu.kanade.tachiyomi.extension.es.hibonbl": "extension-src/hibonbl",
    "eu.kanade.tachiyomi.extension.es.qvfamma": "extension-src/qvfamma",
}
PUBLIC_BASE_URL = "https://Pow2105.github.io/onirepo/hibon"
EXPECTED_SIGNING_KEY = "0242522b9f2a8bf0998474e7969b4617cb51b408707c2d04f707d2cd2ab0205c"
STORE_NAME = "OniRepo · Extensiones propias"
BADGE_LABEL = "ONI"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(args: argparse.Namespace) -> None:
    apk_source = Path(args.apk).resolve()
    icon_source = Path(args.icon).resolve()
    source_info = json.loads(Path(args.source_info).read_text(encoding="utf-8"))
    output_dir = Path(args.output).resolve()

    package_name = source_info["packageName"]
    if package_name not in PACKAGE_SOURCES:
        raise ValueError(f"Unexpected package: {package_name}")
    if source_info["contentWarning"] != 3 or source_info["extensionLib"] != "1.6":
        raise ValueError("Local extensions must remain NSFW TachiyomiX 1.6 extensions")
    if len(source_info["sources"]) != 1:
        raise ValueError("Expected exactly one source in the extension")

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
    icon_name = package_name + ".png"
    icon_path = icon_dir / icon_name

    checksums_path = output_dir / "checksums.json"
    checksums = (
        json.loads(checksums_path.read_text(encoding="utf-8"))
        if checksums_path.is_file()
        else {}
    )
    previous = checksums.get(package_name)
    if previous and previous["apk"] != apk_path.name:
        (apk_dir / previous["apk"]).unlink(missing_ok=True)

    shutil.copy2(apk_source, apk_path)
    shutil.copy2(icon_source, icon_path)

    source = source_info["sources"][0]
    extension = Extension(
        name=source_info["name"],
        package_name=package_name,
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
    existing_extensions = []
    index_path = output_dir / "index.pb"
    if index_path.is_file():
        previous_index = parse_index(index_path.read_bytes())
        if previous_index.signing_key != signing_key:
            raise ValueError("Existing store uses a different signing key")
        existing_extensions = [
            item for item in previous_index.extensions if item.package_name != package_name
        ]

    extensions = sorted(existing_extensions + [extension], key=lambda item: item.name.casefold())
    index = Index(
        name=STORE_NAME,
        badge_label=BADGE_LABEL,
        signing_key=signing_key,
        contact=Contact(website="https://Pow2105.github.io/onirepo/"),
        extensions=extensions,
    )

    (output_dir / "index.pb").write_bytes(encode_index(index))
    write_json(
        output_dir / "index.json",
        {
            "name": index.name,
            "badgeLabel": index.badge_label,
            "signingKey": index.signing_key,
            "contact": {"website": index.contact.website},
            "extensionList": {"extensions": [extension_to_v2(item) for item in extensions]},
        },
    )
    write_json(
        output_dir / "index.min.json",
        [
            extension_to_legacy(item, item.resources.apk_url.rsplit("/", 1)[-1])
            for item in extensions
        ],
        compact=True,
    )
    checksums[package_name] = {
        "apk": apk_path.name,
        "sha256": sha256(apk_path),
        "certificateSha256": signing_key,
        "source": args.source_dir or PACKAGE_SOURCES[package_name],
        "upstreamBase": args.upstream_base,
    }
    write_json(checksums_path, dict(sorted(checksums.items())))
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
    print(
        f"Wrote {extension.name} {extension.version_name} to {output_dir}; "
        f"store now contains {len(extensions)} extensions"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apk", required=True)
    parser.add_argument("--icon", required=True)
    parser.add_argument("--source-info", required=True)
    parser.add_argument("--source-dir")
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
