package eu.kanade.tachiyomi.extension.es.qvfamma

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
import keiyoushi.utils.asJsoup
import keiyoushi.utils.parseAs
import keiyoushi.utils.string
import kotlinx.coroutines.async
import kotlinx.coroutines.awaitAll
import kotlinx.coroutines.coroutineScope
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.put
import okhttp3.HttpUrl
import okhttp3.HttpUrl.Companion.toHttpUrl
import okhttp3.HttpUrl.Companion.toHttpUrlOrNull
import okhttp3.OkHttpClient
import org.jsoup.Jsoup
import org.jsoup.nodes.Document
import java.net.URLDecoder
import java.nio.charset.StandardCharsets
import java.util.Locale
import kotlin.time.Instant

@Source
abstract class QvFamma : KeiSource() {

    override fun OkHttpClient.Builder.configureClient() = rateLimit(3)

    override suspend fun getPopularManga(page: Int): MangasPage {
        val entries = fetchCatalogueEntries()
            .sortedByDescending { it.latestUpdate }
            .map { it.entry.toSManga() }
        return entries.toPage(page)
    }

    override suspend fun getLatestUpdates(page: Int): MangasPage = getPopularManga(page)

    override suspend fun getSearchMangaList(
        page: Int,
        query: String,
        filters: FilterList,
    ): MangasPage {
        val entries = fetchCatalogueEntries()
            .asSequence()
            .filter { query.isBlank() || it.entry.cleanTitle().contains(query, ignoreCase = true) }
            .sortedBy { it.entry.cleanTitle().lowercase(Locale.ROOT) }
            .map { it.entry.toSManga() }
            .toList()
        return entries.toPage(page)
    }

    override suspend fun getMangaByUrl(url: HttpUrl): SManga? {
        if (url.host != baseUrl.toHttpUrl().host || !url.encodedPath.endsWith(".html")) return null

        val document = client.get(url).asJsoup()
        val label = extractLabel(document) ?: return null
        val entry = fetchLabelEntries(label)
            .firstOrNull { it.relativeUrl() == url.encodedPath }
            ?: return null

        return entry.toDetailedSManga(label)
    }

    override suspend fun fetchMangaUpdate(
        manga: SManga,
        chapters: List<SChapter>,
        fetchDetails: Boolean,
        fetchChapters: Boolean,
    ): SMangaUpdate {
        val storedLabel = manga.memo["label"]?.string
        val label = storedLabel ?: client.get(getMangaUrl(manga)).asJsoup().let(::extractLabel)
            ?: throw Exception("No se encontró la etiqueta de la serie")
        val entries = fetchLabelEntries(label)
        val storedPostId = manga.memo["postId"]?.string
        val detailsEntry = entries.firstOrNull { it.postId() == storedPostId }
            ?: entries.firstOrNull { it.isInfoPost() }
            ?: throw Exception("No se encontró la ficha de la serie")

        val updatedManga = if (fetchDetails) detailsEntry.toDetailedSManga(label) else manga
        updatedManga.memo = buildMemo(label, detailsEntry.postId())

        val updatedChapters = if (fetchChapters) {
            entries.filterNot { it.isInfoPost() }
                .mapNotNull { it.toSChapter(label) }
                .sortedByDescending(SChapter::date_upload)
        } else {
            chapters
        }

        return SMangaUpdate(updatedManga, updatedChapters)
    }

    override suspend fun getPageList(chapter: SChapter): List<Page> {
        val label = chapter.memo["label"]?.string ?: throw Exception("Actualiza la lista de capítulos")
        val postId = chapter.memo["postId"]?.string ?: throw Exception("Actualiza la lista de capítulos")
        val entry = fetchLabelEntries(label).firstOrNull { it.postId() == postId }
            ?: throw Exception("No se encontró el capítulo")
        val document = Jsoup.parse(entry.content?.value.orEmpty(), baseUrl)

        return document.select("img[src]")
            .mapNotNull { it.absUrl("src").takeIf(String::isNotBlank) }
            .distinct()
            .mapIndexed { index, imageUrl -> Page(index, imageUrl = imageUrl.toFullSizeImage()) }
    }

    private suspend fun fetchCatalogueEntries(): List<CatalogueEntry> {
        val entries = fetchAllSummaryEntries()
        val latestByLabel = mutableMapOf<String, Long>()
        entries.forEach { entry ->
            val date = entry.updatedAt()
            entry.labels().forEach { label ->
                val key = label.lowercase(Locale.ROOT)
                latestByLabel[key] = maxOf(latestByLabel[key] ?: 0L, date)
            }
        }

        return entries.asSequence()
            .filter { it.isInfoPost() }
            .mapNotNull { entry ->
                val label = entry.primaryLabel() ?: return@mapNotNull null
                CatalogueEntry(entry, latestByLabel[label.lowercase(Locale.ROOT)] ?: entry.updatedAt())
            }
            .distinctBy { it.entry.relativeUrl() }
            .toList()
    }

    private suspend fun fetchAllSummaryEntries(): List<FeedEntryDto> {
        val firstFeed = fetchSummaryFeed(1)
        val totalResults = firstFeed.totalResults?.value?.toIntOrNull() ?: firstFeed.entry.orEmpty().size
        val remainingFeeds = coroutineScope {
            generateSequence(FEED_PAGE_SIZE + 1) { it + FEED_PAGE_SIZE }
                .takeWhile { it <= totalResults }
                .map { startIndex -> async { fetchSummaryFeed(startIndex) } }
                .toList()
                .awaitAll()
        }

        return (listOf(firstFeed) + remainingFeeds)
            .flatMap { it.entry.orEmpty() }
            .distinctBy { it.postId() }
    }

    private suspend fun fetchSummaryFeed(startIndex: Int): FeedDto {
        val url = "$baseUrl/feeds/posts/summary".toHttpUrl().newBuilder()
            .addQueryParameter("alt", "json")
            .addQueryParameter("orderby", "updated")
            .addQueryParameter("max-results", FEED_PAGE_SIZE.toString())
            .addQueryParameter("start-index", startIndex.toString())
            .build()
        return client.get(url).parseAs<FeedResponseDto>().feed
    }

    private suspend fun fetchLabelEntries(label: String): List<FeedEntryDto> {
        val url = "$baseUrl/feeds/posts/default/-/".toHttpUrl().newBuilder()
            .addPathSegment(label)
            .addQueryParameter("alt", "json")
            .addQueryParameter("orderby", "published")
            .addQueryParameter("max-results", MAX_LABEL_RESULTS.toString())
            .build()
        return client.get(url).parseAs<FeedResponseDto>().feed.entry.orEmpty()
    }

    private fun FeedEntryDto.toSManga(): SManga? {
        val label = primaryLabel() ?: return null
        val mangaUrl = relativeUrl() ?: return null
        return SManga.create().apply {
            url = mangaUrl
            title = cleanTitle()
            thumbnail_url = thumbnail?.url?.toFullSizeImage()
            memo = buildMemo(label, postId())
        }
    }

    private fun FeedEntryDto.toDetailedSManga(label: String): SManga {
        val document = Jsoup.parse(content?.value.orEmpty(), baseUrl)
        val text = document.body().text().replace(whitespaceRegex, " ").trim()
        val creator = extractField(text, authorRegex)

        return SManga.create().apply {
            url = relativeUrl().orEmpty()
            title = cleanTitle()
            thumbnail_url = document.selectFirst("img[src]")?.absUrl("src")?.toFullSizeImage()
                ?: thumbnail?.url?.toFullSizeImage()
            author = creator
            artist = creator
            genre = extractField(text, genreRegex)
            description = extractField(text, synopsisRegex)
            status = parseStatus(extractField(text, statusRegex))
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

    private fun extractLabel(document: Document): String? {
        val src = document.selectFirst("#related-posts script[src*='/feeds/posts/default/-/']")?.attr("src")
            ?: return null
        val encoded = src.substringAfter("/-/", missingDelimiterValue = "").substringBefore("?")
        return encoded.takeIf(String::isNotBlank)
            ?.let { URLDecoder.decode(it, StandardCharsets.UTF_8.name()) }
    }

    private fun extractField(text: String, regex: Regex): String? = regex.find(text)
        ?.groupValues
        ?.getOrNull(1)
        ?.trim()
        ?.takeIf(String::isNotBlank)

    private fun parseStatus(value: String?): Int = when {
        value == null -> SManga.UNKNOWN
        value.contains("final", ignoreCase = true) || value.contains("complet", ignoreCase = true) -> SManga.COMPLETED
        value.contains("paus", ignoreCase = true) || value.contains("hiatus", ignoreCase = true) -> SManga.ON_HIATUS
        value.contains("activo", ignoreCase = true) || value.contains("curso", ignoreCase = true) -> SManga.ONGOING
        else -> SManga.UNKNOWN
    }

    private fun FeedEntryDto.cleanTitle(): String = title?.value.orEmpty()
        .replace(infoSuffixRegex, "")
        .trim()

    private fun FeedEntryDto.isInfoPost(): Boolean = title?.value?.contains("informaci", ignoreCase = true) == true

    private fun FeedEntryDto.labels(): List<String> = category.orEmpty().mapNotNull(CategoryDto::term)

    private fun FeedEntryDto.primaryLabel(): String? = labels().firstOrNull()

    private fun FeedEntryDto.relativeUrl(): String? {
        val absoluteUrl = link.orEmpty().firstOrNull { it.rel == "alternate" }?.href ?: return null
        val parsed = absoluteUrl.toHttpUrlOrNull() ?: return null
        if (parsed.host != baseUrl.toHttpUrl().host) return null
        return parsed.encodedPath
    }

    private fun FeedEntryDto.postId(): String = id?.value.orEmpty().substringAfterLast("post-")

    private fun FeedEntryDto.updatedAt(): Long = parseDate(updated?.value ?: published?.value)

    private fun FeedEntryDto.publishedAt(): Long = parseDate(published?.value)

    private fun parseDate(value: String?): Long = value?.let(Instant::parseOrNull)?.toEpochMilliseconds() ?: 0L

    private fun String.toFullSizeImage(): String = when {
        !contains("googleusercontent.com", ignoreCase = true) -> this
        bloggerEqualsSizeRegex.containsMatchIn(this) -> replace(bloggerEqualsSizeRegex, "=s16000")
        bloggerPathSizeRegex.containsMatchIn(this) -> replace(bloggerPathSizeRegex, "/s16000/")
        else -> this
    }

    private fun List<SManga?>.toPage(page: Int): MangasPage {
        val mangas = filterNotNull()
        val fromIndex = (page - 1) * MANGA_PAGE_SIZE
        if (fromIndex >= mangas.size) return MangasPage(emptyList(), false)
        val toIndex = minOf(fromIndex + MANGA_PAGE_SIZE, mangas.size)
        return MangasPage(mangas.subList(fromIndex, toIndex), toIndex < mangas.size)
    }

    private fun buildMemo(label: String, postId: String) = buildJsonObject {
        put("label", label)
        put("postId", postId)
    }

    private class CatalogueEntry(
        val entry: FeedEntryDto,
        val latestUpdate: Long,
    )

    companion object {
        private const val FEED_PAGE_SIZE = 150
        private const val MAX_LABEL_RESULTS = 150
        private const val MANGA_PAGE_SIZE = 20

        private val whitespaceRegex = Regex("""\s+""")
        private val infoSuffixRegex = Regex(
            """\s*(?:\[|\()\s*informaci[oó]n\s*(?:]|\))\s*$""",
            RegexOption.IGNORE_CASE,
        )
        private val nextField = """(?=\s+(?:Estado(?:\s*\([^)]*\))?|Serializaci[oó]n|G[eé]nero|Año|Sinopsis|MANGAS RELACIONADOS)\s*:|$)"""
        private val authorRegex = Regex("""Autor(?:/arte)?\s*:\s*(.*?)$nextField""", RegexOption.IGNORE_CASE)
        private val statusRegex = Regex("""Estado(?:\s*\([^)]*\))?\s*:\s*(.*?)$nextField""", RegexOption.IGNORE_CASE)
        private val genreRegex = Regex("""G[eé]nero\s*:\s*(.*?)$nextField""", RegexOption.IGNORE_CASE)
        private val synopsisRegex = Regex("""Sinopsis\s*:\s*(.*?)(?=\s+MANGAS RELACIONADOS\s*:|$)""", RegexOption.IGNORE_CASE)
        private val bloggerEqualsSizeRegex = Regex("""=s\d+(?:-[^/?]+)?(?=$|[?#])""", RegexOption.IGNORE_CASE)
        private val bloggerPathSizeRegex = Regex("""/s\d+(?:-[^/]+)?/""", RegexOption.IGNORE_CASE)
    }
}
