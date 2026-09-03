"""Small APK Signature Scheme v2 certificate reader.

Only the DER certificate bytes are extracted; no cryptographic verification is
performed here. Android's apksigner is still used during the release build.
"""

from __future__ import annotations

import hashlib
import struct
from pathlib import Path


APK_SIG_BLOCK_MAGIC = b"APK Sig Block 42"
APK_SIGNATURE_SCHEME_V2_ID = 0x7109871A


def _read_length_prefixed(data: bytes, offset: int) -> tuple[bytes, int]:
    if offset + 4 > len(data):
        raise ValueError("Truncated APK signing structure")
    length = struct.unpack_from("<I", data, offset)[0]
    offset += 4
    end = offset + length
    if end > len(data):
        raise ValueError("Invalid APK signing length")
    return data[offset:end], end


def certificate_sha256(path: Path) -> str:
    data = path.read_bytes()
    eocd = data.rfind(b"PK\x05\x06")
    if eocd < 0 or eocd + 20 > len(data):
        raise ValueError("APK has no valid ZIP end record")

    central_directory_offset = struct.unpack_from("<I", data, eocd + 16)[0]
    footer_offset = central_directory_offset - 24
    if footer_offset < 0 or data[footer_offset + 8 : central_directory_offset] != APK_SIG_BLOCK_MAGIC:
        raise ValueError("APK has no v2 signing block")

    block_size = struct.unpack_from("<Q", data, footer_offset)[0]
    block_offset = central_directory_offset - block_size - 8
    if block_offset < 0 or struct.unpack_from("<Q", data, block_offset)[0] != block_size:
        raise ValueError("APK signing block sizes do not agree")

    pairs_offset = block_offset + 8
    while pairs_offset < footer_offset:
        if pairs_offset + 8 > footer_offset:
            raise ValueError("Truncated APK signing pair")
        pair_size = struct.unpack_from("<Q", data, pairs_offset)[0]
        pairs_offset += 8
        pair_end = pairs_offset + pair_size
        if pair_size < 4 or pair_end > footer_offset:
            raise ValueError("Invalid APK signing pair size")
        pair_id = struct.unpack_from("<I", data, pairs_offset)[0]
        value = data[pairs_offset + 4 : pair_end]
        pairs_offset = pair_end
        if pair_id != APK_SIGNATURE_SCHEME_V2_ID:
            continue

        signers, _ = _read_length_prefixed(value, 0)
        signer, _ = _read_length_prefixed(signers, 0)
        signed_data, _ = _read_length_prefixed(signer, 0)
        _, signed_offset = _read_length_prefixed(signed_data, 0)
        certificates, _ = _read_length_prefixed(signed_data, signed_offset)
        certificate, _ = _read_length_prefixed(certificates, 0)
        return hashlib.sha256(certificate).hexdigest()

    raise ValueError("APK has no Signature Scheme v2 signer")
