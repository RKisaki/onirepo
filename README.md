# 🔱 OniRepo — extensiones en español para Mihon

Repositorio compacto de extensiones para **Mihon 0.20.1 o posterior**. Los APK se espejan desde [Keiyoushi](https://github.com/keiyoushi/extensions), conservan su firma original y se publican únicamente cuando su SHA-256 coincide con el manifiesto del distribuidor.

## Añadir a Mihon

Usa esta URL:

```text
https://Pow2105.github.io/onirepo/repo/index.pb
```

1. Abre **Mihon → Más → Ajustes → Explorar**.
2. Entra en **Repositorios/Tiendas de extensiones** y pulsa **＋**.
3. Pega la URL y confirma.
4. Vuelve a **Explorar → Extensiones** e instala la fuente que quieras.

La página del catálogo está en <https://Pow2105.github.io/onirepo/>. El índice heredado `index.min.json` se mantiene para clientes compatibles, pero las extensiones TachiyomiX 1.6 requieren una versión actual de Mihon.

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
└── repo/
    ├── repo.json               # metadatos de la tienda
    ├── index.pb                # índice TachiyomiX actual
    ├── index.json              # equivalente legible del índice actual
    ├── index.min.json          # índice heredado
    ├── checksums.json          # procedencia y SHA-256 de cada APK
    ├── apk/                    # APK firmados
    └── icon/                   # iconos del catálogo
scripts/
├── sync_repo.py               # sincronización reproducible desde Keiyoushi
└── validate_repo.py           # validación cruzada de todos los artefactos
```

## Seguridad y procedencia

- Cada APK se descarga desde una release de Keiyoushi y se compara con el SHA-256 de `release-assets.json` antes de guardarlo.
- El índice conserva el identificador de la clave de firma de Keiyoushi: `9add655a78e96c4ec7a53ef89dccb557cb5d767489fac5e785d671a5a75d4da2`.
- `checksums.json` registra para cada paquete el archivo, el hash esperado y la URL exacta de origen.
- `validate_repo.py` comprueba índices, versiones, URLs, archivos, iconos, hashes y metadatos de firma.

Los APK son software de terceros. El código fuente y sus licencias están en [keiyoushi/extensions-source](https://github.com/keiyoushi/extensions-source). OniRepo no modifica ni vuelve a firmar los binarios.

## Actualizar el catálogo

Con Python 3.10 o posterior:

```bash
python scripts/sync_repo.py
python scripts/validate_repo.py
```

El flujo `sync.yml` ejecuta esos mismos pasos semanalmente y también puede lanzarse manualmente desde GitHub Actions.

## Publicación

En **Settings → Pages**, selecciona **Deploy from a branch**, rama `main` y carpeta `/docs`. Después de publicar, comprueba que responden estas dos rutas:

- `https://Pow2105.github.io/onirepo/repo/index.pb`
- `https://Pow2105.github.io/onirepo/repo/apk/<archivo>.apk`

## Aviso

OniRepo no está afiliado con Mihon, Keiyoushi ni con los sitios incluidos y no aloja mangas. La disponibilidad de cada fuente depende de su web. Para informar de una fuente rota, abre un [issue](https://github.com/Pow2105/onirepo/issues).
