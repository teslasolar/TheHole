pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}

dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
    }
}

rootProject.name = "the-hole-browser"

include(":app")

val tauriProjects = File(settingsDir, ".tauri/tauri.settings.gradle.kts")
if (tauriProjects.exists()) {
    apply(from = tauriProjects)
} else {
    include(":tauri-android")
    project(":tauri-android").projectDir = File("../../Cargo/build/tauri-android")
}
