# 🔱 OniRepo — extensiones en español para Mihon

Repositorio compacto de extensiones para **Mihon 0.20.1 o posterior**. El catálogo general espeja APK de [Keiyoushi](https://github.com/keiyoushi/extensions) sin modificar su firma. Hibon BL y QV Famma se compilan como extensiones propias, con código fuente incluido y una firma independiente.

## Añadir a Mihon

Agrega las dos tiendas para ver todo el catálogo:

```text
https://RKisaki.github.io/onirepo/repo/index.pb
https://RKisaki.github.io/onirepo/hibon/index.pb
```

1. Abre **Mihon → Más → Ajustes → Explorar**.
2. Entra en **Repositorios/Tiendas de extensiones** y pulsa **＋**.
3. Pega una URL y confirma; repite el proceso con la segunda.
4. Vuelve a **Explorar → Extensiones** e instala la fuente que quieras.

La página del catálogo está en <https://RKisaki.github.io/onirepo/>. Los índices heredados `index.min.json` se mantienen para clientes compatibles, pero las extensiones TachiyomiX 1.6 requieren una versión actual de Mihon.

## Hibon BL

- APK: `tachiyomi-es.hibonbl-v1.6.16.apk`
- Paquete: `eu.kanade.tachiyomi.extension.es.hibonbl`
- Fuente: <https://hibon-bl.blogspot.com/>
- Contenido: manga en español; las novelas de texto se excluyen del catálogo.
- Certificado de firma SHA-256: `0242522b9f2a8bf0998474e7969b4617cb51b408707c2d04f707d2cd2ab0205c`

La extensión usa los feeds públicos de Blogger para buscar series y capítulos, y extrae las páginas del lector estático. La versión 1.6.16 deja de depender del cargador JavaScript irregular de la web para que Mihon pueda mostrar los capítulos. Está marcada como 18+ porque el sitio contiene material adulto. También puedes [descargar el APK directamente](https://RKisaki.github.io/onirepo/hibon/apk/tachiyomi-es.hibonbl-v1.6.16.apk).

## QV Famma

- APK: `tachiyomi-es.qvfamma-v1.6.1.apk`
- Paquete: `eu.kanade.tachiyomi.extension.es.qvfamma`
- Fuente: <https://qvfammaonline.blogspot.com/>
- Catálogo detectado: 98 fichas de manga en español.
- Certificado de firma SHA-256: `0242522b9f2a8bf0998474e7969b4617cb51b408707c2d04f707d2cd2ab0205c`

QV Famma usa los feeds públicos de Blogger para el catálogo, los capítulos y las páginas. Esto permite leer desde Mihon aunque la versión web muestre una advertencia de contenido sensible que exige iniciar sesión. Está marcada como 18+. También puedes [descargar el APK directamente](https://RKisaki.github.io/onirepo/hibon/apk/tachiyomi-es.qvfamma-v1.6.1.apk).

## Extensiones incluidas

- Biblio Panda
- Manga Crab
- MANGA Plus by SHUEISHA (incluye español)
- MangaDex (incluye español)
- MangaOni
- Mangas No Sekai
- Mangas.in
- Manhwa-Latino
- ManhwaOnline (18+)
- MHScans
- Mundo Manhwa (18+)
- Webtoons.com (incluye español)

Mihon puede ocultar las fuentes marcadas como mixtas o 18+ según la configuración de contenido del dispositivo.

## Estructura

```text
docs/
├── index.html                  # página de catálogo de GitHub Pages
├── repo/
│   ├── repo.json               # metadatos de la tienda
│   ├── index.pb                # índice TachiyomiX actual
│   ├── index.json              # equivalente legible del índice actual
│   ├── index.min.json          # índice heredado
│   ├── checksums.json          # procedencia y SHA-256 de cada APK
│   ├── apk/                    # APK firmados
│   └── icon/                   # iconos del catálogo
└── hibon/                      # URL histórica de la tienda de extensiones propias
    ├── index.pb, index.json    # índice TachiyomiX y copia legible
    ├── index.min.json          # índice heredado
    ├── checksums.json          # hash y procedencia de la compilación
    ├── apk/                    # APK de Hibon BL y QV Famma
    └── icon/                   # icono de la extensión
extension-src/
├── hibonbl/                    # módulo reproducible de Hibon BL
└── qvfamma/                    # módulo reproducible de QV Famma
scripts/
├── sync_repo.py               # sincronización reproducible desde Keiyoushi
├── build_hibon_repo.py        # añade compilaciones propias al índice secundario
├── apk_signature.py           # lee el certificado v2 del APK
├── validate_hibon_repo.py     # valida la tienda y la firma local
└── validate_repo.py           # validación cruzada de ambas tiendas
```

## Seguridad y procedencia

- Cada APK se descarga desde una release de Keiyoushi y se compara con el SHA-256 de `release-assets.json` antes de guardarlo.
- El índice conserva el identificador de la clave de firma de Keiyoushi: `9add655a78e96c4ec7a53ef89dccb557cb5d767489fac5e785d671a5a75d4da2`.
- `checksums.json` registra para cada paquete el archivo, el hash esperado y la URL exacta de origen.
- `validate_repo.py` comprueba índices, versiones, URLs, archivos, iconos, hashes y metadatos de firma.
- Las extensiones propias usan una tienda separada porque un índice TachiyomiX admite una única clave de firma. Su validador extrae el certificado v2 de cada APK y exige que coincida con la huella del índice.
- Las compilaciones actuales de Hibon BL y QV Famma están firmadas con la misma clave Android local de desarrollo. No es la firma de Keiyoushi; las actualizaciones deben conservar exactamente esa clave o Mihon las rechazará.

Los APK del catálogo general son software de terceros. El código fuente y sus licencias están en [keiyoushi/extensions-source](https://github.com/keiyoushi/extensions-source). OniRepo no modifica ni vuelve a firmar esos binarios. Los módulos propios están en `extension-src/`; Hibon BL y QV Famma implementan directamente los feeds de Blogger.

## Actualizar el catálogo

Con Python 3.10 o posterior:

```bash
python scripts/sync_repo.py
python scripts/validate_repo.py
```

El flujo `sync.yml` actualiza semanalmente el catálogo general y valida también las extensiones propias. Para recompilarlas, sigue el README del módulo correspondiente y ejecuta `build_hibon_repo.py` con el APK, el icono y `keiyoushi-source-info.json` generados.

## Publicación

En **Settings → Pages**, selecciona **Deploy from a branch**, rama `main` y carpeta `/docs`. Después de publicar, comprueba estas rutas:

- `https://RKisaki.github.io/onirepo/repo/index.pb`
- `https://RKisaki.github.io/onirepo/repo/apk/<archivo>.apk`
- `https://RKisaki.github.io/onirepo/hibon/index.pb`
- `https://RKisaki.github.io/onirepo/hibon/apk/tachiyomi-es.hibonbl-v1.6.16.apk`
- `https://RKisaki.github.io/onirepo/hibon/apk/tachiyomi-es.qvfamma-v1.6.1.apk`

## Aviso

OniRepo no está afiliado con Mihon, Keiyoushi ni con los sitios incluidos y no aloja mangas. La disponibilidad de cada fuente depende de su web. Para informar de una fuente rota, abre un [issue](https://github.com/RKisaki/onirepo/issues).
