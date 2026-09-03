# QV Famma extension source

This directory contains the site-specific module used to build the QV Famma
Mihon extension. It reads Blogger summary feeds for the catalogue and full
label feeds for metadata, chapters, and page images. Reading through the feed
also avoids Blogger's browser-only sensitive-content interstitial.

## Rebuild

1. Clone `https://github.com/keiyoushi/extensions-source`.
2. Copy this directory to `src/es/qvfamma` in that checkout.
3. Run `./gradlew :src:es:qvfamma:assembleRelease :src:es:qvfamma:lintRelease`.
4. Run `scripts/build_hibon_repo.py` in OniRepo with the generated APK,
   icon, and `keiyoushi-source-info.json`.

The published `1.6.1` APK was built against commit
`2063590a39622a68075a4cb8834edec8b11d0986` of the upstream source tree.
It uses the same local Android debug signing key as Hibon BL; keep that exact
key for every update or Mihon will reject the replacement APK.
