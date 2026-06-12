# 🔱 OniRepo — Repositorio de Extensiones para Mihon

Repositorio de extensiones compatible con **Mihon** (antes Tachiyomi) enfocado en contenido en **español**: manhwa, manhua, manga y más.

## 📲 Agregar el repositorio en Mihon

```
https://TU_USUARIO.github.io/onirepo/repo/index.min.json
```

**Pasos:**
1. Abre Mihon
2. Ve a **Más → Configuración → Extensiones**
3. Toca **"Repositorios de extensiones"**
4. Pega la URL de arriba
5. Confirma y luego ve a **Extensiones** para instalar las que quieras

---

## 📁 Estructura del repositorio

```
onirepo/
├── docs/
│   └── index.html          ← Página web del repo (GitHub Pages)
├── repo/
│   ├── index.min.json      ← Índice que lee Mihon
│   └── *.apk               ← Archivos APK de cada extensión
└── README.md
```

---

## 🚀 Subir a GitHub Pages (paso a paso)

### 1. Crear el repositorio en GitHub
- Ve a [github.com/new](https://github.com/new)
- Nombre: `onirepo`
- Público ✅
- Crea el repo

### 2. Subir los archivos
```bash
git clone https://github.com/TU_USUARIO/onirepo.git
cd onirepo
# copia aquí los archivos de este proyecto
git add .
git commit -m "Initial release"
git push
```

### 3. Activar GitHub Pages
- Settings → Pages
- Source: **Deploy from branch**
- Branch: `main` / carpeta: `/docs`
- Guarda

### 4. Actualiza las URLs
En `docs/index.html` y `repo/index.min.json`, reemplaza `TU_USUARIO` con tu usuario de GitHub.

---

## 📦 Extensiones incluidas

| Nombre | Tipo | Versión | Estado |
|--------|------|---------|--------|
| AsuraScans | Manhwa | 1.4.0 | ✅ |
| FlameScans | Manhwa | 1.3.0 | ✅ |
| ReaperScans | Manhwa | 1.5.0 | ✅ |
| LuminousScans | Manhwa | 1.2.0 | ✅ |
| ZinManga | Manhua | 1.0.0 | ✅ |
| ManhuaFast | Manhua | 1.1.0 | ✅ |
| Mangatoon | Multi | 1.2.0 | ✅ |
| Bilibili Comics | Manhua | 1.3.0 | ✅ |
| MangaDex | Multi | 1.8.0 | ✅ |
| MangaPlus | Manga | 1.9.0 | ✅ |
| MangaFire | Manga | 1.6.0 | ✅ |
| Webtoon | Manhwa | 2.1.0 | ✅ |

---

## ➕ Agregar una nueva extensión

### En `repo/index.min.json`, añade un objeto nuevo:

```json
{
  "name": "NombreFuente",
  "pkg": "eu.kanade.tachiyomi.extension.es.nombrefuente",
  "apk": "tachiyomi-es.nombrefuente-v1.0.apk",
  "lang": "es",
  "code": 10,
  "version": "1.0.0",
  "nsfw": 0,
  "hasReadme": 0,
  "hasChangelog": 0,
  "sources": [
    {
      "id": "6000000000000099",
      "lang": "es",
      "name": "NombreFuente ES",
      "baseUrl": "https://la-pagina.com",
      "versionId": 1
    }
  ]
}
```

> ⚠️ El campo `id` debe ser único. Usa un número de 19 dígitos que no repitas.

---

## ⚠️ Aviso

Este repositorio es solo para uso personal y educativo. No estamos afiliados a Mihon, Tachiyomi ni a ninguno de los sitios listados.

---

## 🤝 Contribuir

¿Una fuente está rota? ¿Quieres agregar una?
Abre un [Issue](https://github.com/TU_USUARIO/onirepo/issues) o un Pull Request.
