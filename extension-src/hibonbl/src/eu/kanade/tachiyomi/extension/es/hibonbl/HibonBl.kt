package eu.kanade.tachiyomi.extension.es.hibonbl

import eu.kanade.tachiyomi.multisrc.zeistmanga.ZeistManga
import keiyoushi.annotation.Source
import keiyoushi.network.rateLimit
import okhttp3.OkHttpClient

@Source
abstract class HibonBl : ZeistManga() {

    override val supportsLatest = false

    override val chapterCategory = "Capitulo"

    override val mangaDetailsSelector = "body"
    override val mangaDetailsSelectorThumbnail = "#post-body .tab-content img"
    override val mangaDetailsSelectorDescription = "#post-body #synopsis"
    override val mangaDetailsSelectorGenres = "#cabecera-post aside dl:has(dt:contains(Genero)) a[rel=tag]"
    override val mangaDetailsSelectorAuthor =
        "#post-body #extra-info dl:has(dt:contains(Autor)) dd, " +
            "#post-body #extra-info dl:has(dt:contains(Mangaka)) dd"
    override val mangaDetailsSelectorArtist = "#post-body #extra-info dl:has(dt:contains(Artista)) dd"
    override val mangaDetailsSelectorAltName = "#cabecera-post h1 + p"
    override val mangaDetailsSelectorStatus = "#cabecera-post [data-status]"
    override val mangaDetailsSelectorInfo = "#post-body #extra-info dl"
    override val mangaDetailsSelectorInfoTitle = "dt"
    override val mangaDetailsSelectorInfoDescription = "dd"

    override val pageListSelector = "article#reader .manga-box #imagenes"

    override val statusCompletedList = super.statusCompletedList + "completado"

    override fun OkHttpClient.Builder.configureClient() = rateLimit(3)
}
