# Hibon BL extension source

This directory contains the site-specific module used to build the Hibon BL
Mihon extension. It targets the current `zeistmanga` multisrc implementation
from `keiyoushi/extensions-source`.

## Rebuild

1. Clone `https://github.com/keiyoushi/extensions-source`.
2. Copy this directory to `src/es/hibonbl` in that checkout.
3. Run `./gradlew :src:es:hibonbl:assembleRelease :src:es:hibonbl:lintRelease`.
4. Run `scripts/build_hibon_repo.py` in OniRepo with the generated APK,
   icon, and `keiyoushi-source-info.json`.

The published `1.6.15` APK was built against commit
`2063590a39622a68075a4cb8834edec8b11d0986` of the upstream source tree.
The current APK uses the local Android debug signing key. Keep that exact key
for every update (or migrate deliberately before publishing), otherwise Mihon
will reject the replacement APK.
