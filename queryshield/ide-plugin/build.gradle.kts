plugins {
    id("org.jetbrains.intellij.platform") version "2.1.0"
    kotlin("jvm") version "1.9.25"
}

repositories {
    mavenCentral()
    intellijPlatform.defaultRepositories()
}

intellijPlatform {
    // Target PyCharm Community; adjust as needed
    platformType.set("PY")
    platformVersion.set("2025.2")
    plugins.set(listOf("PythonCore", "com.intellij.json"))
}

dependencies {
    intellijPlatform.platform("PY", "2025.2")
    intellijPlatform.plugins(listOf("PythonCore", "com.intellij.json"))
}

tasks {
    patchPluginXml {
        sinceBuild.set("252")
        untilBuild.set(null as String?)
    }
}

