package eu.kanade.tachiyomi.extension.es.hibonbl

import eu.kanade.tachiyomi.source.model.FilterList
import eu.kanade.tachiyomi.source.model.MangasPage
import eu.kanade.tachiyomi.source.model.Page
import eu.kanade.tachiyomi.source.model.SChapter
import eu.kanade.tachiyomi.source.model.SManga
import eu.kanade.tachiyomi.source.model.SMangaUpdate
import keiyoushi.annotation.Source
import keiyoushi.network.get
import keiyoushi.network.rateLimit
import keiyoushi.source.KeiSource
import keiyoushi.utils.parseAs
import keiyoushi.utils.string
import keiyoushi.utils.tryParse
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.put
import okhttp3.HttpUrl
import okhttp3.HttpUrl.Companion.toHttpUrl
import okhttp3.HttpUrl.Companion.toHttpUrlOrNull
import okhttp3.OkHttpClient
import org.jsoup.Jsoup
import java.util.Locale
import kotlin.time.Instant

@Source
abstract class HibonBl : KeiSource() {

    override fun OkHttpClient.Builder.configureClient() = rateLimit(3)

    override suspend fun getPopularManga(page: Int): MangasPage {
        val mangas = fetchCatalogueEntries()
            .sortedByDescending { it.updatedAt() }
            .mapNotNull { entry -> entry.seriesLabel()?.let { label -> entry.toSManga(label) } }
        return mangas.toPage(page)
    }

    override suspend fun getLatestUpdates(page: Int): MangasPage = getPopularManga(page)

    override suspend fun getSearchMangaList(
        page: Int,
        query: String,
        filters: FilterList,
    ): MangasPage {
        val mangas = fetchCatalogueEntries()
            .asSequence()
            .filter { query.isBlank() || it.cleanTitle().contains(query, ignoreCase = true) }
            .sortedBy { it.cleanTitle().lowercase(Locale.ROOT) }
            .mapNotNull { entry -> entry.seriesLabel()?.let { label -> entry.toSManga(label) } }
            .toList()
        return mangas.toPage(page)
    }

    override suspend fun getMangaByUrl(url: HttpUrl): SManga? {
        if (url.host != baseUrl.toHttpUrl().host || !url.encodedPath.endsWith(".html")) return null

        val entry = fetchCatalogueEntries().firstOrNull { it.relativeUrl() == url.encodedPath }
            ?: return null
        val label = entry.seriesLabel() ?: return null
        return entry.toDetailedSManga(label)
    }

    override suspend fun fetchMangaUpdate(
        manga: SManga,
        chapters: List<SChapter>,
        fetchDetails: Boolean,
        fetchChapters: Boolean,
    ): SMangaUpdate {
        val catalogueEntries = fetchCatalogueEntries()
        val storedPostId = manga.memo["postId"]?.string
        val detailsEntry = catalogueEntries.firstOrNull { it.postId() == storedPostId }
            ?: catalogueEntries.firstOrNull { it.relativeUrl() == manga.url }
            ?: throw Exception("No se encontró la ficha de la serie")
        val label = manga.memo["label"]?.string ?: detailsEntry.seriesLabel()
            ?: throw Exception("No se encontró la etiqueta de la serie")

        val updatedManga = if (fetchDetails) detailsEntry.toDetailedSManga(label) else manga
        updatedManga.memo = buildMemo(label, detailsEntry.postId())

        val updatedChapters = if (fetchChapters) {
            fetchLabelEntries(label)
                .filter { it.hasLabel(CHAPTER_CATEGORY) }
                .mapNotNull { it.toSChapter(label) }
                .distinctBy(SChapter::url)
                .sortedByDescending(SChapter::date_upload)
                .ifEmpty { detailsEntry.toEmbeddedChapter(label)?.let(::listOf).orEmpty() }
        } else {
            chapters
        }

        return SMangaUpdate(updatedManga, updatedChapters)
    }

    override suspend fun getPageList(chapter: SChapter): List<Page> {
        val label = chapter.memo["label"]?.string ?: throw Exception("Actualiza la lista de capítulos")
        val postId = chapter.memo["postId"]?.string ?: throw Exception("Actualiza la lista de capítulos")
        val entry = fetchLabelEntries(label).firstOrNull { it.postId() == postId }
            ?: fetchCatalogueEntries().firstOrNull { it.postId() == postId }
            ?: throw Exception("No se encontró el capítulo")
        val document = Jsoup.parseBodyFragment(entry.content?.value.orEmpty(), baseUrl)
        val images = document.select("#imagenes img[src]").ifEmpty {
            document.select("#capitulo-one-shot img[src], .manga-box img[src], div.separator img[src]")
        }.ifEmpty {
            document.select("img[src]").filterNot { image ->
                image.attr("style").replace(" ", "").contains("display:none", ignoreCase = true)
            }
        }

        return images
            .mapNotNull { it.absUrl("src").takeIf(String::isNotBlank) }
            .distinct()
            .mapIndexed { index, imageUrl -> Page(index, imageUrl = imageUrl.toFullSizeImage()) }
    }

    private suspend fun fetchCatalogueEntries(): List<FeedEntryDto> {
        val feed = fetchFeed(SERIES_CATEGORY)
        return feed.entry.orEmpty()
            .filter { it.hasLabel(SERIES_CATEGORY) && it.hasLabel(MANGA_CATEGORY) }
            .filterNot { it.hasLabel(NOVEL_CATEGORY) }
            .distinctBy { it.postId() }
    }

    private suspend fun fetchLabelEntries(label: String): List<FeedEntryDto> = fetchFeed(label).entry.orEmpty().distinctBy { it.postId() }

    private suspend fun fetchFeed(label: String): FeedDto {
        val url = "$baseUrl/feeds/posts/default/-/".toHttpUrl().newBuilder()
            .addPathSegment(label)
            .addQueryParameter("alt", "json")
            .addQueryParameter("orderby", "updated")
            .addQueryParameter("max-results", MAX_FEED_RESULTS.toString())
            .build()
        return client.get(url).parseAs<FeedResponseDto>().feed
    }

    private fun FeedEntryDto.toSManga(label: String): SManga? {
        val mangaUrl = relativeUrl() ?: return null
        return SManga.create().apply {
            url = mangaUrl
            title = cleanTitle()
            thumbnail_url = thumbnailUrl()
            memo = buildMemo(label, postId())
        }
    }

    private fun FeedEntryDto.toDetailedSManga(label: String): SManga {
        val document = Jsoup.parseBodyFragment(content?.value.orEmpty(), baseUrl)
        val info = document.select("#extra-info dl").associate { element ->
            element.select("dt").text().trimEnd(':').lowercase(Locale.ROOT) to
                element.select("dd").text()
        }
        val labels = labels()

        return SManga.create().apply {
            url = relativeUrl().orEmpty()
            title = cleanTitle()
            thumbnail_url = thumbnailUrl()
            author = info["autor"] ?: info["mangaka"]
            artist = info["artista"]
            genre = labels.filter { it.lowercase(Locale.ROOT) in GENRE_LABELS }.joinToString()
            description = document.selectFirst("#synopsis")?.text()
            status = parseStatus(labels)
            memo = buildMemo(label, postId())
        }
    }

    private fun FeedEntryDto.toSChapter(label: String): SChapter? {
        val chapterUrl = relativeUrl() ?: return null
        return SChapter.create().apply {
            url = chapterUrl
            name = title?.value.orEmpty()
            date_upload = publishedAt()
            memo = buildMemo(label, postId())
        }
    }

    private fun FeedEntryDto.toEmbeddedChapter(label: String): SChapter? {
        val document = Jsoup.parseBodyFragment(content?.value.orEmpty(), baseUrl)
        if (document.select("#capitulo-one-shot img[src]").isEmpty()) return null
        return toSChapter(label)
    }

    private fun FeedEntryDto.seriesLabel(): String? {
        val labels = labels()
        val scriptLabel = chapterLabelRegex.find(content?.value.orEmpty())
            ?.groupValues
            ?.getOrNull(1)
            ?.trim()
            ?.takeIf(String::isNotBlank)
        val candidates = labels.filterNot { it.lowercase(Locale.ROOT) in IGNORED_LABELS }

        return candidates.firstOrNull { it.equals(scriptLabel, ignoreCase = true) }
            ?: candidates.singleOrNull()
            ?: scriptLabel
            ?: candidates.firstOrNull()
            ?: cleanTitle().takeIf(String::isNotBlank)
    }

    private fun FeedEntryDto.thumbnailUrl(): String? {
        val document = Jsoup.parseBodyFragment(content?.value.orEmpty(), baseUrl)
        return document.selectFirst(".tab-content img[src]")?.absUrl("src")?.toFullSizeImage()
            ?: thumbnail?.url?.toFullSizeImage()
            ?: document.selectFirst("img[src]")?.absUrl("src")?.toFullSizeImage()
    }

    private fun FeedEntryDto.cleanTitle(): String = title?.value.orEmpty().trim()

    private fun FeedEntryDto.hasLabel(label: String): Boolean = labels().any { it.equals(label, ignoreCase = true) }

    private fun FeedEntryDto.labels(): List<String> = category.orEmpty().mapNotNull(CategoryDto::term)

    private fun FeedEntryDto.relativeUrl(): String? {
        val absoluteUrl = link.orEmpty().firstOrNull { it.rel == "alternate" }?.href ?: return null
        val parsed = absoluteUrl.toHttpUrlOrNull() ?: return null
        if (parsed.host != baseUrl.toHttpUrl().host) return null
        return parsed.encodedPath
    }

    private fun FeedEntryDto.postId(): String = id?.value.orEmpty().substringAfterLast("post-")

    private fun FeedEntryDto.updatedAt(): Long = parseDate(updated?.value ?: published?.value)

    private fun FeedEntryDto.publishedAt(): Long = parseDate(published?.value)

    private fun parseDate(value: String?): Long = Instant.tryParse(value)

    private fun parseStatus(labels: List<String>): Int = when {
        labels.any { it.equals("Completado", ignoreCase = true) } -> SManga.COMPLETED
        labels.any { it.equals("Pausado", ignoreCase = true) } -> SManga.ON_HIATUS
        labels.any { it.equals("Cancelado", ignoreCase = true) } -> SManga.CANCELLED
        labels.any { it.equals("Activo", ignoreCase = true) } -> SManga.ONGOING
        else -> SManga.UNKNOWN
    }

    private fun String.toFullSizeImage(): String = when {
        !contains("googleusercontent.com", ignoreCase = true) -> this
        bloggerEqualsSizeRegex.containsMatchIn(this) -> replace(bloggerEqualsSizeRegex, "=s16000")
        bloggerPathSizeRegex.containsMatchIn(this) -> replace(bloggerPathSizeRegex, "/s16000/")
        else -> this
    }

    private fun List<SManga>.toPage(page: Int): MangasPage {
        val fromIndex = (page - 1) * MANGA_PAGE_SIZE
        if (fromIndex >= size) return MangasPage(emptyList(), false)
        val toIndex = minOf(fromIndex + MANGA_PAGE_SIZE, size)
        return MangasPage(subList(fromIndex, toIndex), toIndex < size)
    }

    private fun buildMemo(label: String, postId: String) = buildJsonObject {
        put("label", label)
        put("postId", postId)
    }

    companion object {
        private const val SERIES_CATEGORY = "Series"
        private const val MANGA_CATEGORY = "Manga"
        private const val NOVEL_CATEGORY = "Novela"
        private const val CHAPTER_CATEGORY = "Capitulo"
        private const val MAX_FEED_RESULTS = 150
        private const val MANGA_PAGE_SIZE = 20

        private val chapterLabelRegex = Regex("""clwd\.run\(\s*['\"]([^'\"]+)['\"]""", RegexOption.IGNORE_CASE)
        private val GENRE_LABELS = setOf(
            "accion", "aventura", "ciencia ficcion", "comedia", "deportes", "drama", "escolar",
            "fantasia", "misterio", "one-shot", "policial", "psicologico", "recuentos de la vida",
            "romance", "sobrenatural", "terror", "tragedia",
        )
        private val IGNORED_LABELS = GENRE_LABELS + setOf(
            "activo", "avisos", "cancelado", "capitulo", "completado", "futuro", "licenciado",
            "manga", "novela", "pausado", "project", "series", "video",
        )
        private val bloggerEqualsSizeRegex = Regex("""=s\d+(?:-[^/?]+)?(?=$|[?#])""", RegexOption.IGNORE_CASE)
        private val bloggerPathSizeRegex = Regex("""/s\d+(?:-[^/]+)?/""", RegexOption.IGNORE_CASE)
    }
}
