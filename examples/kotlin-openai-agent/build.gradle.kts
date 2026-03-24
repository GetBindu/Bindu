plugins {
    kotlin("jvm") version "1.9.22"
    application
}

group = "com.getbindu.examples"
version = "1.0.0"

repositories {
    mavenCentral()
}

dependencies {
    implementation(project(":"))  // bindu-sdk
    implementation("com.google.code.gson:gson:2.10.1")
}

application {
    mainClass.set("MainKt")
}

kotlin {
    jvmToolchain(17)
}
