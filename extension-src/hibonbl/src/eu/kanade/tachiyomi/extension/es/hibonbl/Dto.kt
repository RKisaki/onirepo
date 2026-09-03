package eu.kanade.tachiyomi.extension.es.hibonbl

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
class FeedResponseDto(
    val feed: FeedDto,
)

@Serializable
class FeedDto(
    val entry: List<FeedEntryDto>? = null,
)

@Serializable
class FeedEntryDto(
    val id: TextDto? = null,
    val title: TextDto? = null,
    val content: TextDto? = null,
    val published: TextDto? = null,
    val updated: TextDto? = null,
    val link: List<LinkDto>? = null,
    val category: List<CategoryDto>? = null,
    @SerialName("media\$thumbnail") val thumbnail: ThumbnailDto? = null,
)

@Serializable
class TextDto(
    @SerialName("\$t") val value: String? = null,
)

@Serializable
class LinkDto(
    val rel: String? = null,
    val href: String? = null,
)

@Serializable
class CategoryDto(
    val term: String? = null,
)

@Serializable
class ThumbnailDto(
    val url: String? = null,
)
