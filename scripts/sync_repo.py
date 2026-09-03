#!/usr/bin/env python3
"""Build OniRepo from a curated subset of Keiyoushi's signed extensions.

The script intentionally uses only Python's standard library. It reads the
TachiyomiX protobuf wire format directly, keeps the upstream package metadata,
downloads the matching APKs and icons, verifies APK SHA-256 checksums, and
emits both the modern TachiyomiX index and the legacy Mihon index.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import sys
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator


UPSTREAM_INDEX_URL = "https://raw.githubusercontent.com/keiyoushi/extensions/repo/index.pb"
UPSTREAM_ASSETS_URL = "https://raw.githubusercontent.com/keiyoushi/extensions/repo/release-assets.json"
UPSTREAM_REPO_URL = "https://raw.githubusercontent.com/keiyoushi/extensions/repo/repo.json"
PUBLIC_BASE_URL = "https://RKisaki.github.io/onirepo/repo"

# A compact, Spanish-focused selection. Multilingual sources are included only
# when Spanish is one of the languages exposed by the extension.
SELECTED_PACKAGES = (
    "eu.kanade.tachiyomi.extension.all.mangadex",
    "eu.kanade.tachiyomi.extension.all.mangaplus",
    "eu.kanade.tachiyomi.extension.all.webtoons",
    "eu.kanade.tachiyomi.extension.es.bibliopanda",
    "eu.kanade.tachiyomi.extension.es.mangacrab",
    "eu.kanade.tachiyomi.extension.es.mangamx",
    "eu.kanade.tachiyomi.extension.es.mangasnosekai",
    "eu.kanade.tachiyomi.extension.es.mangasin",
    "eu.kanade.tachiyomi.extension.es.manhwalatino",
    "eu.kanade.tachiyomi.extension.es.manhwaonline",
    "eu.kanade.tachiyomi.extension.es.mhscans",
    "eu.kanade.tachiyomi.extension.es.mundomanhwa",
)

CONTENT_WARNING_NAMES = {
    0: "CONTENT_WARNING_UNSPECIFIED",
    1: "CONTENT_WARNING_SAFE",
    2: "CONTENT_WARNING_MIXED",
    3: "CONTENT_WARNING_NSFW",
}


@dataclass
class Contact:
    website: str = ""
    discord: str | None = None


@dataclass
class Resources:
    apk_url: str = ""
    icon_url: str = ""


@dataclass
class Source:
    source_id: int = 0
    name: str = ""
    language: str = ""
    home_url: str = ""
    mirror_urls: list[str] = field(default_factory=list)
    message: str | None = None


@dataclass
class Extension:
    name: str = ""
    package_name: str = ""
    resources: Resources = field(default_factory=Resources)
    extension_lib: str = ""
    version_code: int = 0
    version_name: str = ""
    content_warning: int = 0
    sources: list[Source] = field(default_factory=list)


@dataclass
class Index:
    name: str = ""
    badge_label: str = ""
    signing_key: str = ""
    contact: Contact = field(default_factory=Contact)
    extensions: list[Extension] = field(default_factory=list)


def read_varint(data: bytes, offset: int) -> tuple[int, int]:
    result = 0
    shift = 0
    while True:
        if offset >= len(data) or shift >= 70:
            raise ValueError("Invalid protobuf varint")
        byte = data[offset]
        offset += 1
        result |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return result, offset
        shift += 7


def iter_fields(data: bytes) -> Iterator[tuple[int, int, int | bytes]]:
    offset = 0
    while offset < len(data):
        key, offset = read_varint(data, offset)
        number, wire_type = key >> 3, key & 7
        if wire_type == 0:
            value, offset = read_varint(data, offset)
        elif wire_type == 1:
            value = data[offset : offset + 8]
            offset += 8
        elif wire_type == 2:
            length, offset = read_varint(data, offset)
            value = data[offset : offset + length]
            offset += length
        elif wire_type == 5:
            value = data[offset : offset + 4]
            offset += 4
        else:
            raise ValueError(f"Unsupported protobuf wire type: {wire_type}")
        if offset > len(data):
            raise ValueError("Truncated protobuf field")
        yield number, wire_type, value


def decode_text(value: int | bytes) -> str:
    if not isinstance(value, bytes):
        raise ValueError("Expected a length-delimited protobuf string")
    return value.decode("utf-8")


def parse_contact(data: bytes) -> Contact:
    contact = Contact()
    for number, _, value in iter_fields(data):
        if number == 1:
            contact.website = decode_text(value)
        elif number == 2:
            contact.discord = decode_text(value)
    return contact


def parse_resources(data: bytes) -> Resources:
    resources = Resources()
    for number, _, value in iter_fields(data):
        if number == 1:
            resources.apk_url = decode_text(value)
        elif number == 2:
            resources.icon_url = decode_text(value)
    return resources


def parse_source(data: bytes) -> Source:
    source = Source()
    for number, _, value in iter_fields(data):
        if number == 1:
            source.source_id = int(value)
        elif number == 2:
            source.name = decode_text(value)
        elif number == 3:
            source.language = decode_text(value)
        elif number == 4:
            source.home_url = decode_text(value)
        elif number == 5:
            source.mirror_urls.append(decode_text(value))
        elif number == 7:
            source.message = decode_text(value)
    return source


def parse_extension(data: bytes) -> Extension:
    extension = Extension()
    for number, _, value in iter_fields(data):
        if number == 1:
            extension.name = decode_text(value)
        elif number == 2:
            extension.package_name = decode_text(value)
        elif number == 3 and isinstance(value, bytes):
            extension.resources = parse_resources(value)
        elif number == 4:
            extension.extension_lib = decode_text(value)
        elif number == 5:
            extension.version_code = int(value)
        elif number == 6:
            extension.version_name = decode_text(value)
        elif number == 7:
            extension.content_warning = int(value)
        elif number == 8 and isinstance(value, bytes):
            extension.sources.append(parse_source(value))
    return extension


def parse_index(data: bytes) -> Index:
    index = Index()
    for number, _, value in iter_fields(data):
        if number == 1:
            index.name = decode_text(value)
        elif number == 2:
            index.badge_label = decode_text(value)
        elif number == 3:
            index.signing_key = decode_text(value)
        elif number == 4 and isinstance(value, bytes):
            index.contact = parse_contact(value)
        elif number == 101 and isinstance(value, bytes):
            for child_number, _, child_value in iter_fields(value):
                if child_number == 1 and isinstance(child_value, bytes):
                    index.extensions.append(parse_extension(child_value))
        elif number == 102:
            raise ValueError("Upstream index points to a second extension list; unsupported")
    return index


def encode_varint(value: int) -> bytes:
    if value < 0:
        value &= (1 << 64) - 1
    output = bytearray()
    while value > 0x7F:
        output.append((value & 0x7F) | 0x80)
        value >>= 7
    output.append(value)
    return bytes(output)


def encode_key(number: int, wire_type: int) -> bytes:
    return encode_varint((number << 3) | wire_type)


def encode_int(number: int, value: int) -> bytes:
    if value == 0:
        return b""
    return encode_key(number, 0) + encode_varint(value)


def encode_blob(number: int, value: bytes) -> bytes:
    if not value:
        return b""
    return encode_key(number, 2) + encode_varint(len(value)) + value


def encode_text(number: int, value: str | None) -> bytes:
    return encode_blob(number, value.encode("utf-8")) if value else b""


def encode_contact(contact: Contact) -> bytes:
    return encode_text(1, contact.website) + encode_text(2, contact.discord)


def encode_resources(resources: Resources) -> bytes:
    return encode_text(1, resources.apk_url) + encode_text(2, resources.icon_url)


def encode_source(source: Source) -> bytes:
    output = bytearray()
    output += encode_int(1, source.source_id)
    output += encode_text(2, source.name)
    output += encode_text(3, source.language)
    output += encode_text(4, source.home_url)
    for mirror_url in source.mirror_urls:
        output += encode_text(5, mirror_url)
    output += encode_text(7, source.message)
    return bytes(output)


def encode_extension(extension: Extension) -> bytes:
    output = bytearray()
    output += encode_text(1, extension.name)
    output += encode_text(2, extension.package_name)
    output += encode_blob(3, encode_resources(extension.resources))
    output += encode_text(4, extension.extension_lib)
    output += encode_int(5, extension.version_code)
    output += encode_text(6, extension.version_name)
    output += encode_int(7, extension.content_warning)
    for source in extension.sources:
        output += encode_blob(8, encode_source(source))
    return bytes(output)


def encode_index(index: Index) -> bytes:
    extension_list = b"".join(encode_blob(1, encode_extension(item)) for item in index.extensions)
    return b"".join(
        (
            encode_text(1, index.name),
            encode_text(2, index.badge_label),
            encode_text(3, index.signing_key),
            encode_blob(4, encode_contact(index.contact)),
            encode_blob(101, extension_list),
        )
    )


def fetch_bytes(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "OniRepo-sync/1.0"})
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()


def copy_or_fetch(source: str | None, url: str) -> bytes:
    data = Path(source).read_bytes() if source else fetch_bytes(url)
    return gzip.decompress(data) if data.startswith(b"\x1f\x8b") else data


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def source_to_v2(source: Source) -> dict[str, object]:
    result: dict[str, object] = {
        "id": str(source.source_id),
        "name": source.name,
        "language": source.language,
        "homeUrl": source.home_url,
    }
    if source.mirror_urls:
        result["mirrorUrls"] = source.mirror_urls
    if source.message:
        result["message"] = source.message
    return result


def extension_to_v2(extension: Extension) -> dict[str, object]:
    return {
        "name": extension.name,
        "packageName": extension.package_name,
        "resources": {
            "apkUrl": extension.resources.apk_url,
            "iconUrl": extension.resources.icon_url,
        },
        "extensionLib": extension.extension_lib,
        "versionCode": str(extension.version_code),
        "versionName": extension.version_name,
        "contentWarning": CONTENT_WARNING_NAMES[extension.content_warning],
        "sources": [source_to_v2(source) for source in extension.sources],
    }


def extension_to_legacy(extension: Extension, apk_name: str) -> dict[str, object]:
    return {
        "name": extension.name,
        "pkg": extension.package_name,
        "apk": apk_name,
        "lang": _primary_language(extension),
        "code": extension.version_code,
        "version": extension.version_name,
        "nsfw": int(extension.content_warning in (2, 3)),
        "sources": [
            {
                "id": str(source.source_id),
                "lang": source.language,
                "name": source.name,
                "baseUrl": source.home_url,
            }
            for source in extension.sources
        ],
    }


def _primary_language(extension: Extension) -> str:
    package_parts = extension.package_name.split(".")
    package_language = package_parts[-2] if len(package_parts) >= 2 else "all"
    if package_language != "all":
        return package_language
    languages = {source.language for source in extension.sources if source.language}
    return languages.pop() if len(languages) == 1 else "all"


def write_json(path: Path, value: object, *, compact: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if compact:
        text = json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n"
    else:
        text = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    path.write_text(text, encoding="utf-8", newline="\n")


def sync(args: argparse.Namespace) -> None:
    upstream_index = parse_index(copy_or_fetch(args.upstream_index, UPSTREAM_INDEX_URL))
    assets = json.loads(copy_or_fetch(args.upstream_assets, UPSTREAM_ASSETS_URL))
    upstream_repo = json.loads(copy_or_fetch(args.upstream_repo, UPSTREAM_REPO_URL))

    by_package = {item.package_name: item for item in upstream_index.extensions}
    missing = sorted(set(SELECTED_PACKAGES) - set(by_package))
    if missing:
        raise RuntimeError("Packages missing from upstream index: " + ", ".join(missing))

    output_dir = Path(args.output).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    apk_dir = output_dir / "apk"
    icon_dir = output_dir / "icon"
    apk_dir.mkdir(exist_ok=True)
    icon_dir.mkdir(exist_ok=True)

    selected: list[Extension] = []
    legacy: list[dict[str, object]] = []
    manifest: dict[str, dict[str, str]] = {}

    for package_name in SELECTED_PACKAGES:
        extension = by_package[package_name]
        release = assets.get(package_name, {}).get("apk")
        if not release:
            raise RuntimeError(f"No APK checksum metadata for {package_name}")

        apk_name = release["name"]
        expected_hash = release["sha256"].lower()
        upstream_apk_url = extension.resources.apk_url
        if not upstream_apk_url.endswith("/" + apk_name):
            raise RuntimeError(f"APK filename mismatch for {package_name}")

        apk_path = apk_dir / apk_name
        if apk_path.exists() and sha256(apk_path.read_bytes()) == expected_hash:
            apk_data = apk_path.read_bytes()
        else:
            apk_data = fetch_bytes(upstream_apk_url)
            actual_hash = sha256(apk_data)
            if actual_hash != expected_hash:
                raise RuntimeError(
                    f"SHA-256 mismatch for {apk_name}: expected {expected_hash}, got {actual_hash}"
                )
            apk_path.write_bytes(apk_data)

        icon_name = package_name + ".png"
        icon_path = icon_dir / icon_name
        if not icon_path.exists() or args.refresh_icons:
            icon_path.write_bytes(fetch_bytes(extension.resources.icon_url))

        extension.resources = Resources(
            apk_url=f"{PUBLIC_BASE_URL}/apk/{apk_name}",
            icon_url=f"{PUBLIC_BASE_URL}/icon/{icon_name}",
        )
        selected.append(extension)
        legacy.append(extension_to_legacy(extension, apk_name))
        manifest[package_name] = {
            "apk": apk_name,
            "sha256": expected_hash,
            "upstream": upstream_apk_url,
        }

    selected.sort(key=lambda item: item.name.casefold())
    legacy.sort(key=lambda item: str(item["name"]).casefold())

    keep_apks = {entry["apk"] for entry in manifest.values()}
    for path in apk_dir.glob("*.apk"):
        if path.name not in keep_apks:
            path.unlink()
    keep_icons = {package + ".png" for package in manifest}
    for path in icon_dir.glob("*.png"):
        if path.name not in keep_icons:
            path.unlink()

    index = Index(
        name="OniRepo",
        badge_label="ONI",
        signing_key=upstream_index.signing_key,
        contact=Contact(website="https://RKisaki.github.io/onirepo/"),
        extensions=selected,
    )
    (output_dir / "index.pb").write_bytes(encode_index(index))
    write_json(
        output_dir / "index.json",
        {
            "name": index.name,
            "badgeLabel": index.badge_label,
            "signingKey": index.signing_key,
            "contact": {"website": index.contact.website},
            "extensionList": {"extensions": [extension_to_v2(item) for item in selected]},
        },
    )
    write_json(output_dir / "index.min.json", legacy, compact=True)
    write_json(output_dir / "checksums.json", manifest)
    write_json(
        output_dir / "repo.json",
        {
            "index_v2": f"{PUBLIC_BASE_URL}/index.pb",
            "meta": {
                "name": "OniRepo",
                "website": "https://RKisaki.github.io/onirepo/",
                "signingKeyFingerprint": upstream_repo["meta"]["signingKeyFingerprint"],
            },
        },
    )

    # Ensure our encoder can round-trip the generated binary index.
    round_trip = parse_index((output_dir / "index.pb").read_bytes())
    if [item.package_name for item in round_trip.extensions] != [
        item.package_name for item in selected
    ]:
        raise RuntimeError("Generated protobuf index failed round-trip validation")

    print(f"Wrote {len(selected)} verified extensions to {output_dir}")
    for extension in selected:
        print(f"- {extension.name}: {extension.version_name} ({extension.package_name})")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="docs/repo")
    parser.add_argument("--upstream-index")
    parser.add_argument("--upstream-assets")
    parser.add_argument("--upstream-repo")
    parser.add_argument("--refresh-icons", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    try:
        sync(parse_args())
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise
