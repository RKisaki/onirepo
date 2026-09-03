import io.github.keiyoushi.gradle.api.ContentWarning

plugins {
    alias(kei.plugins.extension)
}

keiyoushi {
    name = "QV Famma"
    versionCode = 1
    contentWarning = ContentWarning.NSFW
    libVersion = "1.6"

    source {
        baseUrl = "https://qvfammaonline.blogspot.com"
        lang = "es"
    }

    deeplink {
        path("/..*")
    }
}
